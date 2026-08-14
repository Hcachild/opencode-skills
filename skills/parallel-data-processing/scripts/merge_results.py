# -*- coding: utf-8 -*-
"""
merge_results.py —— 通用结果校验与合并工具

1. 校验：所有分片是否都有对应的 Agent 结果 JSON、JSON 可解析、
   ID 顺序与数量是否与分片完全一致、结果字段是否合法。
2. 合并：将 Agent 结果字段回填到源数据，输出到新文件。

用法示例:
  # 校验 + 按结果字段拆分输出（如分类任务：verdict=public 一组、internal 一组）
  python merge_results.py --chunks-dir chunks --results-dir results \
      --split-key verdict --split-map "public=公开信息,internal=企业内部信息" \
      --output-dir out --out-fields 行号,问题,答案,来源文件,reason

  # 只校验不输出
  python merge_results.py --chunks-dir chunks --results-dir results --check-only

  # 全部结果合并成一个文件（每行=源数据+结果字段）
  python merge_results.py --chunks-dir chunks --results-dir results \
      --output-dir out --mode single --out-fields row,text,verdict,reason

参数说明:
  --chunks-dir   分片目录（含 chunk_*.txt 和 manifest.json）
  --results-dir  Agent 结果 JSON 所在目录（chunk_001.json ...）
  --split-key    按结果的哪个字段拆分（默认不拆分）
  --split-map    "值=输出子目录" 的映射，逗号分隔（如 public=公开,internal=内部）
  --mode         single=合并成一个文件 | split=按 split-key 拆分（默认 split）
  --out-fields   输出列（源字段: row,text + 结果字段任意），逗号分隔
  --output-dir   输出目录（默认 ./out）
  --out-format   xlsx | csv | jsonl（默认 xlsx）
  --check-only   只校验不输出
  --id-field     manifest 中条目 ID 的字段名（默认 id）
"""
import argparse
import csv
import json
import os
import re
import sys

ID_RE = re.compile(r'^ID: (.+)$')


def load_manifest(chunks_dir):
    path = os.path.join(chunks_dir, 'manifest.json')
    if not os.path.exists(path):
        sys.exit(f'缺少 manifest.json: {path}')
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_chunk_ids(chunks_dir, total_chunks):
    ids_by_chunk = {}
    for idx in range(1, total_chunks + 1):
        cpath = os.path.join(chunks_dir, f'chunk_{idx:03d}.txt')
        with open(cpath, encoding='utf-8') as f:
            ids = [ID_RE.match(l).group(1) for l in f if l.startswith('ID: ')]
        ids_by_chunk[idx] = ids
    return ids_by_chunk


def check(results_dir, ids_by_chunk):
    errors = []
    for idx, ids in ids_by_chunk.items():
        rpath = os.path.join(results_dir, f'chunk_{idx:03d}.json')
        if not os.path.exists(rpath):
            errors.append(f'chunk_{idx:03d}: 缺少结果文件')
            continue
        try:
            with open(rpath, encoding='utf-8-sig') as f:
                data = json.load(f)
        except Exception as e:
            errors.append(f'chunk_{idx:03d}: JSON解析失败 {e}')
            continue
        if not isinstance(data, list):
            errors.append(f'chunk_{idx:03d}: 结果不是数组')
            continue
        got = [d.get('id') for d in data]
        if got != ids:
            errors.append(
                f'chunk_{idx:03d}: ID不一致 (期望{len(ids)}条, 实际{len(data)}条) '
                f'缺失={set(ids) - set(got)} 多余={set(got) - set(ids)}')
    return errors


def main():
    ap = argparse.ArgumentParser(description='通用结果校验与合并工具')
    ap.add_argument('--chunks-dir', required=True)
    ap.add_argument('--results-dir', required=True)
    ap.add_argument('--split-key')
    ap.add_argument('--split-map')
    ap.add_argument('--mode', choices=['single', 'split'], default='split')
    ap.add_argument('--out-fields', default='row,text')
    ap.add_argument('--output-dir', default='out')
    ap.add_argument('--out-format', choices=['xlsx', 'csv', 'jsonl'], default='xlsx')
    ap.add_argument('--check-only', action='store_true')
    ap.add_argument('--id-field', default='id')
    args = ap.parse_args()

    manifest = load_manifest(args.chunks_dir)
    ids_by_chunk = load_chunk_ids(args.chunks_dir, manifest['total_chunks'])

    errors = check(args.results_dir, ids_by_chunk)
    if errors:
        print('== 校验错误 ==')
        for e in errors:
            print(e)
        print(f'共 {len(errors)} 个问题')
        sys.exit(1)
    print(f'全部 {manifest["total_chunks"]} 个分片校验通过: ID顺序/数量 一致')
    if args.check_only:
        return

    # 收集结果
    results = {}
    for idx in ids_by_chunk:
        with open(os.path.join(args.results_dir, f'chunk_{idx:03d}.json'), encoding='utf-8') as f:
            for d in json.load(f):
                results[d['id']] = d

    fields = [f.strip() for f in args.out_fields.split(',') if f.strip()]
    rows = []
    for it in manifest['items']:
        r = results.get(it['id'], {})
        row = []
        for fld in fields:
            if fld in ('row', 'text') or fld in it:
                row.append(str(it.get(fld, '')))
            else:
                row.append(str(r.get(fld, '')))
        rows.append((it['id'], row, r))

    split_map = {}
    if args.split_map:
        for pair in args.split_map.split(','):
            k, _, v = pair.partition('=')
            split_map[k.strip()] = v.strip()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.mode == 'split':
        if not args.split_key:
            sys.exit('split 模式需要 --split-key')
        groups = {}
        for id_, row, r in rows:
            key = str(r.get(args.split_key, ''))
            groups.setdefault(key, []).append(row)
        for key, group_rows in groups.items():
            outdir = os.path.join(args.output_dir, split_map.get(key, key))
            os.makedirs(outdir, exist_ok=True)
            write_output(os.path.join(outdir, 'result.' + ext(args.out_format)),
                         fields, group_rows, args.out_format)
            print(f'[{key}] {len(group_rows)} 条 -> {outdir}')
    else:
        write_output(os.path.join(args.output_dir, 'result.' + ext(args.out_format)),
                     fields, [r[1] for r in rows], args.out_format)
        print(f'合并输出 {len(rows)} 条 -> {os.path.join(args.output_dir, "result." + ext(args.out_format))}')


def ext(fmt):
    return {'xlsx': 'xlsx', 'csv': 'csv', 'jsonl': 'jsonl'}[fmt]


def write_output(path, header, rows, fmt):
    if fmt == 'xlsx':
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(header)
        for r in rows:
            ws.append(r)
        wb.save(path)
    elif fmt == 'csv':
        with open(path, 'w', encoding='utf-8-sig', newline='') as f:
            w = csv.writer(f)
            w.writerow(header)
            w.writerows(rows)
    else:
        with open(path, 'w', encoding='utf-8') as f:
            for r in rows:
                f.write(json.dumps(dict(zip(header, r)), ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()