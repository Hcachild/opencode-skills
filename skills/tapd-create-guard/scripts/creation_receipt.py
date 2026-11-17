#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
tapd-create-guard —— 创建结果核对回执

用途：工作项创建完成后，**按类型逐条展示「必填字段」实际填写的内容**，并把
      （可选的）提交预期值一起比对，明确指出"哪条有哪个字段缺失或不一致"。

用法:
  # 1) 只看实际值是否都填上了
  python creation_receipt.py --actual <回读数据.json>

  # 2) 期望值 vs 实际值 比对（推荐，能抓出"传了中文却写成 0"这类静默失败）
  python creation_receipt.py --expected <提交数据.json> --actual <回读数据.json>

输入文件支持（自动识别）：
  · TAPD get_stories_or_tasks 的落盘 JSON（含 data[].Story）
  · 纯数组 [{"id":..,"type":..,"name":..,"priority":..}, ...]
  · expected 里可带可选 `id`（创建后补上）——有则按 id 匹配，无则按「标题」匹配

退出码: 0 = 全部正确 / 1 = 存在缺失或不一致 / 2 = 输入错误
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from validate_required_fields import (  # noqa: E402
    REQUIRED, TYPE_LABELS, is_blank, norm_item, norm_type, strip_html,
)

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass


def load_rows(paths):
    """读取一个或多个文件，返回标准化后的列表。"""
    out = []
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
                out.append(s)
    return out


def norm(v):
    """值归一化，便于比较（去空、去尾部分号）。"""
    if v is None:
        return ""
    return str(v).strip().rstrip(";").rstrip("；").strip()


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--actual", nargs="+", required=True, help="创建后回读的数据文件")
    ap.add_argument("--expected", nargs="*", help="创建时提交的数据文件（可选，用于比对）")
    ap.add_argument("--workspace", default="32496738", help="TAPD workspace_id，默认 32496738")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    actual_rows = load_rows(args.actual)
    if not actual_rows:
        print("未解析到任何工作项", file=sys.stderr)
        return 2

    # 预期数据索引
    exp_by_id, exp_by_name = {}, {}
    for e in (load_rows(args.expected) if args.expected else []):
        e2 = norm_item(e)
        if e2.get("id"):
            exp_by_id[str(e2["id"])] = e2
        if e2.get("name"):
            exp_by_name.setdefault(str(e2["name"]).strip(), e2)

    results, bad_total, overall_ok = [], 0, True
    skipped = []
    for i, a_raw in enumerate(actual_rows, 1):
        a = a_raw
        t = norm_type(a.get("workitem_type_id") or a.get("type"))
        if not t:
            skipped.append(str(a.get("name") or a.get("id") or ("第 %d 条" % i)))
            continue
        label = TYPE_LABELS[t]
        aid = str(a.get("id") or "")
        aname = str(a.get("name") or "")
        exp = exp_by_id.get(aid) or exp_by_name.get(aname.strip())

        rows, bad = [], 0
        for fid, flabel, kind, _hint in REQUIRED[t]:
            av = a.get(fid)
            if kind == "richtext":
                plain = strip_html(av)
                missing = is_blank(plain)
                av_disp = ("(已填写 %d 字)" % len(plain)) if not missing else ""
                exp_ok = bool(exp) and not is_blank(strip_html(exp.get(fid)))
                ev_disp = ("(已填写)" if exp_ok else "") if exp else None
                mismatch = bool(exp) and not exp_ok and not missing
            else:
                av_disp = norm(av)
                missing = is_blank(av)
                ev_disp = norm(exp.get(fid)) if exp else None
                mismatch = bool(exp) and bool(ev_disp) and ev_disp != av_disp and not missing

            if missing:
                if exp and ev_disp:
                    status, note = "mismatch", "预期「%s」→ 实际未写入（%s）" % (ev_disp, av_disp or "空")
                else:
                    status, note = "missing", "**缺失**（未填上）"
                bad += 1
            elif mismatch:
                status, note = "mismatch", "预期「%s」→ 实际「%s」" % (ev_disp, av_disp)
                bad += 1
            else:
                status, note = "ok", ""

            rows.append({"field": fid, "label": flabel, "status": status,
                         "actual": av_disp, "expected": ev_disp, "note": note})

        if bad:
            overall_ok = False
            bad_total += bad
        results.append({
            "index": i, "type": t, "type_label": label,
            "id": aid, "name": aname,
            "url": "https://www.tapd.cn/%s/prong/stories/view/%s" % (args.workspace, aid),
            "fields": rows, "bad": bad,
        })

    report = {"ok": overall_ok, "total": len(results), "bad_total": bad_total,
              "skipped": skipped, "results": results}

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if (overall_ok and results) else 1

    if not results:
        print("❌ 未能核对任何条目：回读数据里缺少 `workitem_type_id`（或 `type`），无法判定工作项类型。", file=sys.stderr)
        if skipped:
            print("   受影响的条目：%s" % "、".join(skipped), file=sys.stderr)
        print("   请在回读时带上 `workitem_type_id` 字段后重跑。", file=sys.stderr)
        return 2

    print("TAPD 创建结果核对回执")
    print("=" * 50)
    print("本次核对 %d 条，逐条列出必填字段的实际填写内容：\n" % len(results))
    if skipped:
        print("⚠️ 另有 %d 条被跳过（缺 workitem_type_id，无法判定类型）：%s\n"
              % (len(skipped), "、".join(skipped)))
    for r in results:
        mark = "✅" if r["bad"] == 0 else "❌"
        print("%s【%d】%s「%s」" % (mark, r["index"], r["type_label"], r["name"]))
        print("     ID: %s" % r["id"])
        print("     链接: %s" % r["url"])
        for f in r["fields"]:
            if f["status"] == "ok":
                print("     ✓ %-16s %s" % (f["label"], f["actual"]))
            elif f["status"] == "missing":
                print("     ✗ %-16s **缺失**（未填上）" % f["label"])
            else:
                print("     ✗ %-16s %s" % (f["label"], f["note"]))
        need = len(REQUIRED[r["type"]])
        print("     → 必填 %d/%d %s\n" % (need - r["bad"], need,
                                          "通过" if r["bad"] == 0 else "**未通过**"))
    print("-" * 50)
    if overall_ok:
        print("结论：全部核对通过，字段已按规范写入 ✅")
    else:
        print("结论：存在 %d 处缺失/不一致 ❌ —— 请用 update_story_or_task 修正后重新核对" % bad_total)
    return 0 if overall_ok else 1


if __name__ == "__main__":
    sys.exit(main())
