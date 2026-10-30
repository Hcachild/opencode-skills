#!/usr/bin/env python3
"""Locate opencode (sub)agent sessions in the local opencode SQLite DB.

Why: the `task` tool returns `<task id="ses_...">` — that id is the child
session id (same value accepted by `task_id`).  Once a parent's context is
lost, or when a child needs to know its own id, query the DB.

Usage:
  python session_map.py self     --token <run_token> [--json] [--all]
  python session_map.py children --parent <session_id> [--json] [--limit N]
  python session_map.py agent    --agent-id <agent_id> [--parent <sid>] [--json]
  python session_map.py path

Notes:
  * `--token` must be a unique string embedded in the child prompt
    (recommended: `<swarm>-g<G>-<agent_id>-<8hex>`).
  * `opencode session list` does NOT list subagent sessions (verified
    2026-10-22, opencode 1.19.x), so do not use it to find children.
  * Read-only, safe to run while opencode is running.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROLES_SUBAGENT = ("swarm-lead", "swarm-worker", "general")


def default_db() -> Path:
    env = os.environ.get("OPENCODE_DB")
    if env:
        return Path(env)
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    return home / ".local" / "share" / "opencode" / "opencode.db"


def connect(db: Path) -> sqlite3.Connection:
    if not db.exists():
        sys.exit(f"DB not found: {db}\nSet OPENCODE_DB or pass --db.")
    con = sqlite3.connect(str(db), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA query_only=ON")
    return con


def like_escape(token: str) -> str:
    token = token.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{token}%"


def find_by_token(con: sqlite3.Connection, token: str, limit: int, all_rows: bool):
    """Sessions whose *user* message contains token (subagent first prompt)."""
    sql = """
        select s.id, s.parent_id, s.agent, s.title, s.time_created,
               m.id as message_id
        from session s
        join part p on p.session_id = s.id
        join message m on p.message_id = m.id
        where p.data like ? escape '\\'
          and json_extract(m.data, '$.role') = 'user'
        order by s.time_created desc
    """
    rows = [dict(r) for r in con.execute(sql, (like_escape(token),))]
    if not all_rows:
        seen, uniq = set(), []
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                uniq.append(r)
        rows = uniq
    return rows[:limit]


def find_children(con: sqlite3.Connection, parent: str, limit: int):
    sql = """
        select id, parent_id, agent, title, time_created, time_updated
        from session where parent_id = ?
        order by time_created desc limit ?
    """
    return [dict(r) for r in con.execute(sql, (parent, limit))]


def find_by_agent(con: sqlite3.Connection, agent_id: str, parent: str | None, limit: int):
    """Find the session whose prompt mentions `agent_id=<...>` (optional parent)."""
    sql = """
        select s.id, s.parent_id, s.agent, s.title, s.time_created
        from session s
        join part p on p.session_id = s.id
        join message m on p.message_id = m.id
        where p.data like ? escape '\\'
          and json_extract(m.data, '$.role') = 'user'
    """
    args = [like_escape(f"agent_id={agent_id}")]
    if parent:
        sql += " and s.parent_id = ?"
        args.append(parent)
    sql += " order by s.time_created desc limit ?"
    args.append(limit)
    return [dict(r) for r in con.execute(sql, args)]


def minimal(r: dict) -> dict:
    return {
        "session_id": r["id"],
        "parent_id": r["parent_id"],
        "agent": r["agent"],
        "title": r["title"],
    }


def emit(rows, as_json: bool, empty_hint: str):
    if as_json:
        print(json.dumps([minimal(r) for r in rows], ensure_ascii=False, indent=2))
    elif rows:
        for i, r in enumerate(rows, 1):
            if len(rows) > 1:
                print(f"[{i}]")
            print(f"SESSION_ID={r['id']}")
            print(f"PARENT_ID={r['parent_id']}")
            print(f"AGENT={r['agent']}")
            print(f"TITLE={r['title']}")
    else:
        print(empty_hint, file=sys.stderr)
        return 1
    return 0


def main() -> int:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", type=Path, default=argparse.SUPPRESS)
    common.add_argument("--json", action="store_true", default=argparse.SUPPRESS)

    ap = argparse.ArgumentParser(
        description="Find opencode agent session ids", parents=[common]
    )
    ap.set_defaults(db=default_db(), json=False)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_self = sub.add_parser(
        "self", parents=[common], help="find my session id via a unique prompt token"
    )
    p_self.add_argument("--token", required=True)
    p_self.add_argument("--all", action="store_true")
    p_self.add_argument("--limit", type=int, default=5)

    p_children = sub.add_parser(
        "children", parents=[common], help="list child sessions of a parent"
    )
    p_children.add_argument("--parent", required=True)
    p_children.add_argument("--limit", type=int, default=100)

    p_agent = sub.add_parser(
        "agent", parents=[common], help="find sessions by agent_id= in prompt"
    )
    p_agent.add_argument("--agent-id", required=True)
    p_agent.add_argument("--parent", default=None)
    p_agent.add_argument("--limit", type=int, default=10)

    sub.add_parser("path", parents=[common], help="print the DB path")

    args = ap.parse_args()
    if args.cmd == "path":
        print(args.db)
        return 0

    con = connect(args.db)
    try:
        if args.cmd == "self":
            rows = find_by_token(con, args.token, args.limit, args.all)
            return emit(
                rows,
                args.json,
                f"no session found for token {args.token!r}; "
                "ensure the exact token is in the child's first prompt",
            )
        if args.cmd == "children":
            rows = find_children(con, args.parent, args.limit)
            return emit(rows, args.json, f"no child sessions under {args.parent}")
        if args.cmd == "agent":
            rows = find_by_agent(con, args.agent_id, args.parent, args.limit)
            return emit(
                rows,
                args.json,
                f"no session found for agent_id={args.agent_id!r}",
            )
    finally:
        con.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
