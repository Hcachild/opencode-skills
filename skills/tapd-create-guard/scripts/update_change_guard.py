#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tapd-create-guard —— 修改前的「变更安全校验」

用途：任何 update_story_or_task 之前，把【当前值】与【拟改值】比对，列出实际会被改动的字段，
      并按风险分级：

        ⛔ BLOCK —— 系统自动写入的字段（实际时间 / 工时类），禁止手工改
        ⚠️ WARN  —— 目标字段当前**已有值**，属于"覆盖"，必须用户明确确认
        ✅ OK    —— 当前为空，属于"补空"，安全

用法:
  python update_change_guard.py --current <回读的当前数据.json> --target <拟修改的数据.json>

  两个文件都支持 TAPD 落盘格式（含 data[].Story）或纯数组；按 id 配对。
  target 里必须带 id（修改必须指定对象）。

退出码: 0 = 只有补空（可直接改） / 1 = 存在覆盖或自动字段（必须先让用户确认） / 2 = 输入错误
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from validate_required_fields import is_blank, norm_item  # noqa: E402

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 由状态流转 / 系统自动写入的字段 —— 手工改会污染时效与工时统计
AUTO_FIELDS = {
    "custom_field_23": "实际需求评审时间",
    "custom_field_27": "实际开发开始时间",
    "custom_field_25": "实际提测时间",
    "custom_field_29": "实际测试开始时间",
    "custom_field_26": "实际测试完成时间",
    "custom_field_seven": "实际上线时间",
    "effort_completed": "完成工时",
    "exceed": "超出工时",
    "remain": "剩余工时",
    "completed": "完成时间",
}

# 不属于"用户可改字段"的元信息
META = {"type", "workitem_type", "类型", "workitem_type_id"}


def load_by_id(paths):
    out = {}
    for p in paths:
        try:
            raw = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            raise SystemExit("读取失败 %s：%s" % (p, e))
        rows = raw.get("data") if isinstance(raw, dict) else raw
        if not isinstance(rows, list):
            raise SystemExit("文件格式无法识别：%s" % p)
        for r in rows:
            s = r.get("Story") if isinstance(r, dict) else None
            if s is None:
                s = r if isinstance(r, dict) else None
            if s and s.get("id"):
                out[str(s["id"])] = s
    return out


def norm(v):
    if v is None:
        return ""
    return str(v).strip().rstrip(";").rstrip("；").strip()


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--current", nargs="+", required=True, help="当前值（回读数据）")
    ap.add_argument("--target", nargs="+", required=True, help="拟修改的值")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    cur = load_by_id(args.current)
    tgt = load_by_id(args.target)
    if not tgt:
        print("拟修改数据里没解析到任何带 id 的工作项", file=sys.stderr)
        return 2

    items, block_total, warn_total = [], 0, 0
    for iid, t_raw in tgt.items():
        t = norm_item(t_raw)
        c = cur.get(iid)
        rows = []
        if c is None:
            rows.append({"field": "-", "label": "（未找到当前值）", "level": "warn",
                         "old": "", "new": "", "note": "回读数据里没有 id=%s，无法比对，请先回读" % iid})
            warn_total += 1
        else:
            for fid, nv in t.items():
                if fid in META or fid == "id":
                    continue
                ov = c.get(fid)
                if norm(ov) == norm(nv):
                    continue                      # 值没变，不算改动
                if fid in AUTO_FIELDS:
                    lvl, note = "block", "系统自动字段（%s），禁止手工改" % AUTO_FIELDS[fid]
                    block_total += 1
                elif not is_blank(ov):
                    lvl, note = "warn", "当前已有值，属于覆盖"
                    warn_total += 1
                else:
                    lvl, note = "ok", "当前为空，补空"
                rows.append({"field": fid, "label": AUTO_FIELDS.get(fid, fid),
                             "level": lvl, "old": norm(ov), "new": norm(nv), "note": note})
        if rows:
            items.append({"id": iid, "name": t.get("name") or (c or {}).get("name") or iid,
                          "changes": rows})

    ok = (block_total == 0 and warn_total == 0)
    report = {"ok": ok, "block": block_total, "warn": warn_total, "items": items}

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    print("修改前变更安全校验")
    print("=" * 50)
    if not items:
        print("没有任何字段会发生变化 —— 无需调用 update。")
        return 0
    icon = {"block": "⛔", "warn": "⚠️ ", "ok": "✅"}
    for it in items:
        print("\n【%s】%s" % (it["id"], it["name"]))
        for r in it["changes"]:
            if r["level"] == "ok":
                print("  ✅ %-18s （空） → %s" % (r["label"], r["new"]))
            elif r["level"] == "warn":
                print("  ⚠️  %-18s %s → %s      %s" % (r["label"], r["old"], r["new"], r["note"]))
            else:
                print("  ⛔ %-18s %s → %s      %s" % (r["label"], r["old"], r["new"], r["note"]))
    print("\n" + "-" * 50)
    if ok:
        print("结论：全部是「补空」，可以直接执行 ✅")
    else:
        print("结论：存在 %d 处系统自动字段改动、%d 处已有值覆盖 ❌" % (block_total, warn_total))
        print("→ **不得直接执行**：先逐条向用户确认；系统自动字段默认不动。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
