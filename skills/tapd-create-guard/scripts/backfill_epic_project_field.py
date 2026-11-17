#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tapd-create-guard —— 「Epic归属项目或系统」(custom_field_36) 存量回填计算器

用途
  扫描 TAPD 工作项数据，找出 Feature / Story / Task 中 custom_field_36 为空的条目，
  沿 parent_id 链向上逐级查找第一个非空值，输出「id → 应填值」的回填清单。

  ⚠️ 本脚本只做计算，不写 TAPD。拿到清单后由 AI 通过 MCP 的
     update_story_or_task 接口逐条回填（或交用户确认后执行）。

用法
  python backfill_epic_project_field.py --items <文件1> [文件2 ...] [--out <清单.json>]

  输入文件支持两种格式（自动识别）：
    · TAPD get_stories_or_tasks 的落盘 JSON —— 含 data[].Story
    · 纯数组 —— [{"id":...,"workitem_type_id":...,"parent_id":...,"custom_field_36":...}, ...]
  （分页拉取时可以把多个文件一起传进来，脚本会按 id 去重合并）

退出码
  0 = 无空缺    1 = 存在可回填项（需处理）    2 = 输入错误
"""
import argparse
import json
import os
import sys
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TYPE_MAP = {
    "1132496738001000033": "epic",
    "1132496738001000032": "feature",
    "1132496738001000031": "story",
    "1132496738001000035": "task",
}
TARGET_TYPES = ("feature", "story", "task")   # Epic 是继承源头，不处理
FIELD = "custom_field_36"


def load_items(paths):
    """读取并合并多个输入文件，按 id 去重。"""
    items = {}
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
            if not s or not s.get("id"):
                continue
            tid = str(s.get("workitem_type_id") or "")
            items[str(s["id"])] = {
                "id": str(s["id"]),
                "name": s.get("name") or "",
                "type": TYPE_MAP.get(tid, "other"),
                "parent_id": str(s.get("parent_id") or "0"),
                FIELD: (s.get(FIELD) or "").strip(),
            }
    return items


def resolve(items, start_parent, max_depth):
    """从 start_parent 起沿 parent 链向上找第一个非空 custom_field_36。"""
    pid = start_parent
    depth = 0
    while pid and pid != "0" and depth < max_depth:
        p = items.get(pid)
        if p is None:
            return None, "父级 %s 不在数据范围内" % pid
        if p[FIELD]:
            return p[FIELD], None
        pid = p["parent_id"]
        depth += 1
    return None, "父链上（最多上溯 %d 层）找不到非空值" % max_depth


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--items", nargs="+", required=True, help="一个或多个工作项 JSON 文件")
    ap.add_argument("--out", help="回填清单输出路径（JSON）")
    ap.add_argument("--max-depth", type=int, default=5, help="向上查找最大层数，默认 5")
    ap.add_argument("--format", choices=["text", "json"], default="text", help="stdout 输出格式")
    args = ap.parse_args()

    items = load_items(args.items)
    if not items:
        print("未解析到任何工作项", file=sys.stderr)
        return 2

    empty = [it for it in items.values() if it["type"] in TARGET_TYPES and not it[FIELD]]
    fillable, unfillable = [], []
    for it in empty:
        value, reason = resolve(items, it["parent_id"], args.max_depth)
        rec = {"id": it["id"], "name": it["name"], "type": it["type"],
               "parent_id": it["parent_id"]}
        if value:
            rec["value"] = value
            fillable.append(rec)
        else:
            rec["reason"] = reason
            unfillable.append(rec)

    by_type = Counter(it["type"] for it in empty)
    by_value = Counter(r["value"] for r in fillable)

    report = {
        "total_items": len(items),
        "empty_count": len(empty),
        "by_type": {t: by_type.get(t, 0) for t in TARGET_TYPES},
        "fillable_count": len(fillable),
        "unfillable_count": len(unfillable),
        "by_value": dict(by_value.most_common()),
        "fillable": fillable,
        "unfillable": unfillable,
    }

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print("「Epic归属项目或系统」存量回填计算")
        print("=" * 46)
        print("扫描工作项：%d 条" % len(items))
        print("发现空缺（Feature/Story/Task）：%d 条" % len(empty))
        print("   Feature %d / Story %d / Task %d"
              % (by_type.get("feature", 0), by_type.get("story", 0), by_type.get("task", 0)))
        print("可回填：%d 条    无法推断：%d 条" % (len(fillable), len(unfillable)))
        if by_value:
            print("\n将回填的值分布：")
            for v, n in by_value.most_common():
                print("   %s × %d" % (v, n))
        if fillable:
            print("\n回填清单（前 20 条）：")
            for r in fillable[:20]:
                print("   %s  [%s]  %s  →  %s" % (r["id"], r["type"], r["name"][:28], r["value"]))
        if unfillable:
            print("\n无法推断（需人工确认）：")
            for r in unfillable[:20]:
                print("   %s  [%s]  %s  ——  %s" % (r["id"], r["type"], r["name"][:28], r["reason"]))
        if args.out:
            print("\n清单已写入：%s" % args.out)
        print("\n下一步：用 MCP 的 update_story_or_task 逐条回填（entity_type=stories, id=..., %s=<value>）。" % FIELD)

    return 1 if fillable else 0


if __name__ == "__main__":
    sys.exit(main())
