#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAPD 人员匹配提醒器（2026-10-13 新增，用户要求）
规则：当授权账号要「修改 / 流转 / 删除」某 Epic / Feature / Story / Task / 需求池缺陷 / 生产缺陷时，
先回读该对象并跑本脚本：若其人员字段（处理人 / 产品经理 / 测试人员 / 开发人员 / 需求提出方 等）
**均与当前授权账号不匹配** → 醒目提醒「该 XX 的人员跟你不匹配，确定要操作么？」并列出逐字段明细；
用户明确强制要改 → 放行（提醒不阻断，但必须在确认页醒目展示）。

用法:
  python owner_match_guard.py --user "<当前授权账号昵称>" --type story  --data "对象回读.json"
  python owner_match_guard.py --user "<当前授权账号昵称>" --type epic   --data "对象回读.json"
  python owner_match_guard.py --user "<当前授权账号昵称>" --type feature --data "对象回读.json"
  python owner_match_guard.py --user "<当前授权账号昵称>" --type task   --data "对象回读.json"
  python owner_match_guard.py --user "<当前授权账号昵称>" --type bug --workspace 32496738 --data "对象回读.json"
  python owner_match_guard.py --user "<当前授权账号昵称>" --type bug --workspace 36495762 --data "对象回读.json"

data 兼容三种格式: 裸字段字典 / {"Story":{...}}、{"Bug":{...}} 等包装 / 包装数组（取第一条）。
退出码: 0=有人员字段匹配当前账号（或对象无人员值，仅提示）——可继续按流程操作
        1=人员字段均有值且全部不匹配 → 醒目提醒，用户强制确认后才可操作
        2=输入格式错误
"""
import argparse
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 各对象类型的「人员字段 → 界面名」映射（字段缺失自动跳过）
FIELD_SETS = {
    "story": [
        ("owner", "处理人"),
        ("developer", "开发人员"),
        ("custom_field_four", "产品经理"),
        ("custom_field_three", "测试人员"),
        ("custom_field_two", "需求提出方"),
    ],
    "task": [
        ("owner", "处理人"),
        ("developer", "开发人员"),
    ],
    "bug_pool": [  # 需求池 32496738 缺陷
        ("current_owner", "处理人"),
        ("de", "开发人员"),
        ("te", "测试人员"),
    ],
    "bug_prod": [  # 生产缺陷 36495762 缺陷
        ("current_owner", "处理人"),
        ("de", "开发人员"),
        ("te", "测试人员"),
        ("custom_field_two", "缺陷提出方"),
    ],
}


def unwrap(raw):
    """裸字典 / {"Story":{...}} / {"Bug":{...}} / 包装数组 → 字段字典。"""
    if isinstance(raw, list):
        if not raw:
            raise ValueError("data 为空数组")
        raw = raw[0]
    if isinstance(raw, dict):
        for key in ("Story", "Task", "Bug"):
            if key in raw and isinstance(raw[key], dict):
                return raw[key]
        return raw
    raise ValueError("data 格式无法识别（需要对象字段字典或包装结构）")


def split_names(value):
    """人员字段值规范化：去分号空格，按 ; ; ，, 拆多人，返回非空名单。"""
    s = str(value or "").strip().strip(";").strip()
    if not s:
        return []
    for sep in (";", "；", "，", ","):
        s = s.replace(sep, ";")
    return [p.strip() for p in s.split(";") if p.strip()]


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--user", required=True, help="当前授权账号昵称（get_current_user 实时获取）")
    ap.add_argument("--type", required=True, choices=["story", "epic", "feature", "task", "bug"],
                    help="对象类型")
    ap.add_argument("--workspace", help="bug 必传：32496738=需求池 / 36495762=生产缺陷处理")
    ap.add_argument("--data", required=True, help="对象回读数据 JSON 文件；传 - 从 stdin 读")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    t = args.type
    if t == "bug":
        ws = str(args.workspace or "").strip()
        if "32496738" in ws:
            field_set = FIELD_SETS["bug_pool"]
            type_label = "需求池缺陷"
        elif "36495762" in ws:
            field_set = FIELD_SETS["bug_prod"]
            type_label = "生产缺陷"
        else:
            print("bug 必须用 --workspace 指定空间（32496738 / 36495762）", file=sys.stderr)
            return 2
    else:
        field_set = FIELD_SETS[t]
        type_label = {"story": "Story", "epic": "Epic", "feature": "Feature", "task": "Task"}[t]

    try:
        obj = unwrap(load_json(args.data))
    except (json.JSONDecodeError, ValueError, OSError) as e:
        print("输入文件解析失败：%s" % e, file=sys.stderr)
        return 2

    title = str(obj.get("name") or obj.get("title") or "(未取到标题)")

    rows = []
    matched_any = False
    has_any_value = False
    for fid, label in field_set:
        if fid not in obj:  # 该对象没有此字段 → 跳过
            continue
        names = split_names(obj.get(fid))
        if not names:
            rows.append((label, fid, "（空）", False))
            continue
        has_any_value = True
        hit = any((args.user in n) or (n == args.user) for n in names)
        if hit:
            matched_any = True
        rows.append((label, fid, "; ".join(names), hit))

    need_alert = has_any_value and not matched_any

    if args.format == "json":
        print(json.dumps({
            "user": args.user, "type_label": type_label, "title": title,
            "need_alert": need_alert, "matched_any": matched_any,
            "has_any_value": has_any_value,
            "rows": [{"label": l, "field": f, "value": v, "match": m} for l, f, v, m in rows],
        }, ensure_ascii=False, indent=2))
        return 1 if need_alert else 0

    lines = []
    lines.append("TAPD 人员匹配检查（%s）" % type_label)
    lines.append("=" * 52)
    lines.append("对象：%s「%s」" % (type_label, title))
    lines.append("当前账号：%s" % args.user)
    lines.append("-" * 52)
    for label, fid, value, hit in rows:
        mark = "✅ 匹配" if hit else ("— 空" if value == "（空）" else "❌ 不匹配")
        lines.append("  %-8s %-16s 值：%s" % (mark, label + "(" + fid + ")", value))
    lines.append("-" * 52)

    if need_alert:
        lines.append("⚠️ 醒目提醒：%s「%s」的人员（处理人 / 产品经理 / 测试人员 / 开发人员 /"
                     " 需求提出方等）均与当前账号「%s」不匹配 —— 确定要操作么？" % (type_label, title, args.user))
        lines.append("     请向用户醒目展示上表明细；**用户明确强制要改 → 放行**（操作照常，但须记录该确认）。")
        lines.append("结论：人员均不匹配 —— 提醒后需用户强制确认才可执行修改 / 流转 / 删除。")
    elif not has_any_value:
        lines.append("结论：对象上无人员字段值 —— 无匹配提醒，可继续按流程操作（建议补齐人员字段）。")
    else:
        lines.append("结论：存在与当前账号匹配的人员字段 —— 无需人员匹配提醒，可继续按流程操作。")
    print("\n".join(lines))
    return 1 if need_alert else 0


def load_json(path):
    raw = sys.stdin.read() if path == "-" else open(path, encoding="utf-8").read()
    return json.loads(raw)


if __name__ == "__main__":
    sys.exit(main())
