# -*- coding: utf-8 -*-
"""
split_data.py —— 通用数据分片工具

将任意结构化数据文件切成若干个块（chunk），每个块交给一个 Agent 独立处理。
支持 xlsx / csv / tsv / txt / jsonl 五种输入格式。

用法示例:
  # xlsx：跳过表头，按 Excel 行号生成 ID
  python split_data.py --input data.xlsx --chunk-size 10 --out-dir chunks --id-prefix 仓库

  # csv：默认首行表头
  python split_data.py --input data.csv --chunk-size 5 --out-dir chunks

  # txt：每行一条记录，行号即 ID
  python split_data.py --input items.txt --chunk-size 20 --out-dir chunks --format txt

  # jsonl：每条 JSON 对象一条记录
  python split_data.py --input data.jsonl --chunk-size 10 --out-dir chunks --format jsonl

  # 只取指定列（从 0 开始），列间用 | 分隔
  python split_data.py --input data.xlsx --chunk-size 10 --out-dir chunks --columns 1,2

参数说明:
  --input        输入文件路径（必填）
  --chunk-size   每块条数，即每个 Agent 处理的数量（默认 10）
  --out-dir      输出目录（默认 ./chunks）
  --format       xlsx | csv | tsv | txt | jsonl（默认按扩展名推断）
  --id-prefix    ID 前缀，生成形如 <prefix>:R<行号> 的 ID（默认取输入文件名主干）
  --columns      要输出的列索引，逗号分隔（xlsx/csv/tsv 适用；默认全部列）
  --no-header    输入文件没有表头（xlsx/csv/tsv 适用）
"""
import argparse
import csv
import json
import os
import sys


def read_xlsx(path, columns, has_header):
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.worksheets[0]
    records = []
    for i, row in enumerate(ws.iter_rows(values_only=True), 1):
        if has_header and i == 1:
            continue
        values = [str(v) if v is not None else '' for v in row]
        if columns:
            values = [values[c] if c < len(values) else '' for c in columns]
        text = ' | '.join(values)
        if text.strip():
            records.append((i, text))  # (Excel 行号, 文本)
    wb.close()
    return records


def read_csv(path, columns, delimiter, has_header):
    records = []
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f, delimiter=delimiter)
        for i, row in enumerate(reader, 1):
            if has_header and i == 1:
                continue
            values = [v if v is not None else '' for v in row]
            if columns:
                values = [values[c] if c < len(values) else '' for c in columns]
            text = ' | '.join(values)
            if text.strip():
                records.append((i, text))
    return records


def read_txt(path):
    records = []
    with open(path, encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.rstrip('\r\n')
            if line.strip():
                records.append((i, line))
    return records


def read_jsonl(path):
    records = []
    with open(path, encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                records.append((i, line))
                continue
            if isinstance(obj, dict):
                text = ' | '.join(f'{k}: {v}' for k, v in obj.items())
            else:
                text = str(obj)
            records.append((i, text))
    return records


def main():
    ap = argparse.ArgumentParser(description='通用数据分片工具')
    ap.add_argument('--input', required=True)
    ap.add_argument('--chunk-size', type=int, default=10)
    ap.add_argument('--out-dir', default='chunks')
    ap.add_argument('--format', choices=['xlsx', 'csv', 'tsv', 'txt', 'jsonl'])
    ap.add_argument('--id-prefix')
    ap.add_argument('--columns')
    ap.add_argument('--no-header', action='store_true')
    args = ap.parse_args()

    if not os.path.exists(args.input):
        sys.exit(f'输入文件不存在: {args.input}')

    fmt = args.format or os.path.splitext(args.input)[1].lstrip('.').lower()
    columns = [int(c) for c in args.columns.split(',')] if args.columns else None
    prefix = args.id_prefix or os.path.splitext(os.path.basename(args.input))[0]
    has_header = not args.no_header

    if fmt == 'xlsx':
        records = read_xlsx(args.input, columns, has_header)
    elif fmt == 'csv':
        records = read_csv(args.input, columns, ',', has_header)
    elif fmt == 'tsv':
        records = read_csv(args.input, columns, '\t', has_header)
    elif fmt == 'txt':
        records = read_txt(args.input)
    elif fmt == 'jsonl':
        records = read_jsonl(args.input)
    else:
        sys.exit(f'不支持的格式: {fmt}')

    if not records:
        sys.exit('未读取到任何有效数据')

    os.makedirs(args.out_dir, exist_ok=True)
    items = [{'id': f'{prefix}:R{row}', 'row': row, 'text': text} for row, text in records]

    chunks = [items[i:i + args.chunk_size] for i in range(0, len(items), args.chunk_size)]
    for idx, chunk in enumerate(chunks, 1):
        with open(os.path.join(args.out_dir, f'chunk_{idx:03d}.txt'), 'w', encoding='utf-8') as f:
            for it in chunk:
                f.write(f"ID: {it['id']}\n")
                f.write(f"TEXT: {it['text']}\n")
                f.write('---\n')

    manifest = {
        'input': args.input,
        'format': fmt,
        'chunk_size': args.chunk_size,
        'total_items': len(items),
        'total_chunks': len(chunks),
        'items': items,
    }
    with open(os.path.join(args.out_dir, 'manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f'共 {len(items)} 条 / 每块 {args.chunk_size} 条 / {len(chunks)} 个分片')
    print(f'分片输出: {os.path.abspath(args.out_dir)}')


if __name__ == '__main__':
    main()