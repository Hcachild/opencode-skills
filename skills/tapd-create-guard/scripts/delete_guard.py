#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TAPD 删除前「关联影响」评估器
配套技能：tapd-create-guard

作用：给定工作项全量落盘（或该工作项及其相关项的落盘），算出**删除某条工作项会牵连什么**：
      整棵子树、涉及的工作项类型分布、工时汇总、上游父级链、以及删除后父级汇总的变化。
      输出一段**醒目警告 + 影响清单**，用于让用户确认；**用户确认前不得执行删除**。

用法:
  # 基于全量落盘评估（可传多个分页文件，自动合并去重）
  python delete_guard.py --id 1132496738001001744 --items items_p1.json items_p2.json

  # 也可直接对单条工作项（无子树信息时只报自身）
  python delete_guard.py --id 1132496738001001744 --items item.json --format json

退出码: 0=影响清单已生成(仍必须用户确认后才可删)  2=输入错误
"""

import argparse
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

TYPE_LABELS = {
    "1132496738001000033": "Epic（史诗故事）",
    "1132496738001000032": "Feature（特性）",
    "1132496738001000031": "Story（需求）",
    "1132496738001000035": "Task（任务）",
}
TYPE_SHORT = {
    "1132496738001000033": "Epic",
    "1132496738001000032": "Feature",
    "1132496738001000031": "Story",
    "1132496738001000035": "Task",
}


def load_items(paths):
    """合并多个落盘文件；兼容 {data:[{Story:{...}}]} / {data:[{...}]} / 裸数组。"""
    items = {}
    for p in paths:
        raw = sys.stdin.read() if p == "-" else open(p, encoding="utf-8").read()
        obj = json.loads(raw)
        rows = obj.get("data") if isinstance(obj, dict) else obj
        if not isinstance(rows, list):
            raise SystemExit("无法识别 items 结构（期望 {'data':[...]} 或裸数组）：%s" % p)
        for row in rows:
            if not isinstance(row, dict):
                continue
            node = row
            for k in ("Story", "Bug", "Task"):
                if isinstance(row.get(k), dict):
                    node = row[k]
                    break
            nid = str(node.get("id") or "").strip()
            if nid:
                items[nid] = node
    return items


def num(v):
    try:
        return float(str(v).strip())
    except Exception:
        return 0.0


def children_map(items):
    kids = {}
    for nid, it in items.items():
        pid = str(it.get("parent_id") or "").strip()
        if pid and pid not in ("0", ""):
            kids.setdefault(pid, []).append(nid)
    return kids


def subtree(root, kids):
    """广度优先收集整棵子树（不含 root 自身）。"""
    out, queue = [], list(kids.get(root, []))
    seen = set()
    while queue:
        nid = queue.pop(0)
        if nid in seen:
            continue
        seen.add(nid)
        out.append(nid)
        queue.extend(kids.get(nid, []))
    return out


def ancestor_chain(nid, items):
    chain, cur = [], items.get(nid)
    guard = 0
    while cur and guard < 20:
        pid = str(cur.get("parent_id") or "").strip()
        if not pid or pid in ("0", ""):
            break
        parent = items.get(pid)
        if not parent:
            chain.append({"id": pid, "name": "（未在本次数据中，需另行确认）"})
            break
        chain.append({"id": pid, "name": parent.get("name") or "", "type": parent.get("workitem_type_id")})
        cur = parent
        guard += 1
    return chain


def main():
    ap = argparse.ArgumentParser(description="TAPD 删除前关联影响评估")
    ap.add_argument("--id", required=True, help="拟删除的工作项 id")
    ap.add_argument("--items", nargs="+", required=True, help="工作项落盘 JSON（可多个，支持 - 读 stdin）")
    ap.add_argument("--format", choices=["text", "json"], default="text")
    args = ap.parse_args()

    items = load_items(args.items)
    target = items.get(str(args.id).strip())
    if target is None:
        print("在给定数据中没找到 id=%s 的工作项；请确认 id 或补充落盘范围。" % args.id, file=sys.stderr)
        return 2

    tid = str(target.get("id"))
    kids = children_map(items)
    desc = subtree(tid, kids)

    by_type, eff, eff_done, done_cnt = {}, 0.0, 0.0, 0
    for nid in desc:
        it = items.get(nid, {})
        t = TYPE_SHORT.get(str(it.get("workitem_type_id") or ""), "其他")
        by_type[t] = by_type.get(t, 0) + 1
        eff += num(it.get("effort"))
        eff_done += num(it.get("effort_completed"))
        if str(it.get("status") or "") in ("done", "status_9", "status_10", "status_11", "status_12", "status_13", "status_14"):
            done_cnt += 1

    chain = ancestor_chain(tid, items)
    parent = items.get(str(target.get("parent_id") or ""))

    report = {
        "target": {
            "id": tid,
            "name": target.get("name") or "",
            "type": TYPE_LABELS.get(str(target.get("workitem_type_id") or ""), "未知类型"),
            "type_id": target.get("workitem_type_id"),
            "status": target.get("status"),
            "owner": target.get("owner"),
        },
        "subtree": {
            "total": len(desc),
            "by_type": by_type,
            "done": done_cnt,
            "effort_sum": eff,
            "effort_completed_sum": eff_done,
            "items": [{"id": n, "name": items.get(n, {}).get("name") or "",
                       "type": TYPE_SHORT.get(str(items.get(n, {}).get("workitem_type_id") or ""), "其他"),
                       "status": items.get(n, {}).get("status")}
                      for n in desc],
        },
        "parent_chain": chain,
        "parent": {"id": str(target.get("parent_id")), "name": (parent or {}).get("name") or ""},
        "impacts": [],
    }

    im = report["impacts"]
    if desc:
        im.append("**级联删除**：该工作项及其 **%d 个下级**（%s）将一并被删除"
                  % (len(desc), "、".join("%s×%d" % (k, v) for k, v in sorted(by_type.items()))))
        if done_cnt:
            im.append("其中 **%d 个下级已「完成」** —— 已发生的工作记录会被一并清掉" % done_cnt)
    if eff or eff_done:
        im.append("**工时清零**：下级累计预估 %g h、完成 %g h 将随删除消失，父级工时汇总会同步下降"
                  % (eff, eff_done))
    if parent:
        im.append("**父级汇总变化**：父级「%s」(%s) 的工时/进度汇总会减少" % (parent.get("name") or "", parent.get("id")))
    if chain:
        im.append("**上游链路**：%s — 删除后该层级出现缺口" %
                  " › ".join("%s(%s)" % (c["name"], c["id"]) for c in reversed(chain)))
    im.append("**不可逆风险**：删除属高风险操作；即便平台侧可恢复，关联关系、工时与评论也不保证完整还原")
    if not desc:
        im.append("本次数据中未见其下级 —— 若实际存在子项而未被拉取，影响会**被低估**，请先确认取数范围完整")

    if args.format == "json":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    W = "！"
    lines = []
    lines.append("=" * 60)
    lines.append("%s  警 告 ： 删 除 操 作 不 可 逆  %s" % (W, W))
    lines.append("=" * 60)
    lines.append("")
    lines.append("拟删除：%s「%s」" % (report["target"]["type"], report["target"]["name"]))
    lines.append("  ID：%s   状态：%s   处理人：%s"
                 % (tid, report["target"]["status"], report["target"]["owner"]))
    lines.append("")
    lines.append("---- 关联影响（必须逐项向用户确认）----")
    for i, s in enumerate(im, 1):
        lines.append("  %d. %s" % (i, s))
    lines.append("")
    if desc:
        lines.append("---- 将被一并删除的下级（共 %d 条）----" % len(desc))
        for n in report["subtree"]["items"][:50]:
            lines.append("  · [%s] %s  %s" % (n["type"], n["name"], n["id"]))
        if len(desc) > 50:
            lines.append("  · …（其余 %d 条略）" % (len(desc) - 50))
        lines.append("")
    lines.append("=" * 60)
    lines.append("请回复明确确认后才可执行删除；未确认前不得删除。")
    lines.append("=" * 60)
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    sys.exit(main())
