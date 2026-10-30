#!/usr/bin/env python3
"""Backup / restore opencode agent sessions as JSON (same session id on import).

Session deletion cascades to all child sessions, and a lost session cannot be
resumed.  Export before deleting, and export active sessions at every
checkpoint, so a deleted/corrupted session can be restored.

Usage:
  python session_backup.py export --session ses_... --agent-id g1-w1 --out-dir <SWARM>/sessions
  python session_backup.py export-state --swarm <SWARM> --out-dir <SWARM>/sessions
  python session_backup.py export-tree --root ses_... --out-dir <SWARM>/sessions
  python session_backup.py import --file <SWARM>/sessions/g1-w1.json

Notes:
  * `opencode export` reads the local DB; safe while opencode is running.
  * Import restores the **same** session id (verified 2026-10-22, 1.19.x).
  * Import only when the session is missing; importing over a live session may
    duplicate or conflict.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


def opencode_exe() -> str:
    for name in ("opencode", "opencode.cmd", "opencode.exe"):
        p = shutil.which(name)
        if p:
            return p
    sys.exit("opencode CLI not found in PATH")


def run_export(session: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        p = subprocess.run(
            [opencode_exe(), "export", session],
            stdout=f,
            stderr=subprocess.PIPE,
            text=True,
        )
    if p.returncode != 0 or not tmp.exists() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        sys.exit(f"export failed for {session}: {p.stderr.strip()[-500:]}")
    tmp.replace(out)
    print(f"EXPORTED session={session} file={out} bytes={out.stat().st_size}")


def run_import(file: Path) -> None:
    if not file.exists():
        sys.exit(f"file not found: {file}")
    p = subprocess.run(
        [opencode_exe(), "import", str(file)],
        capture_output=True,
        text=True,
    )
    if p.returncode != 0:
        sys.exit(f"import failed: {p.stderr.strip()[-500:]}")
    print(p.stdout.strip() or f"IMPORTED file={file}")


def db_path() -> Path:
    env = os.environ.get("OPENCODE_DB")
    if env:
        return Path(env)
    home = Path(os.environ.get("USERPROFILE") or Path.home())
    return home / ".local" / "share" / "opencode" / "opencode.db"


def descendants(root: str) -> list[tuple[str, str | None, str | None]]:
    import sqlite3

    path = db_path()
    if not path.exists():
        sys.exit(f"DB not found: {path}")
    con = sqlite3.connect(str(path), timeout=10)
    con.execute("PRAGMA query_only=ON")
    out: list[tuple[str, str | None, str | None]] = []
    frontier = [root]
    seen = set()
    while frontier:
        sid = frontier.pop()
        if sid in seen:
            continue
        seen.add(sid)
        row = con.execute("select id, agent, title from session where id=?", (sid,)).fetchone()
        if row:
            out.append((row[0], row[1], row[2]))
        frontier.extend(r[0] for r in con.execute("select id from session where parent_id=?", (sid,)))
    con.close()
    return out


def export_tree(root: str, out_dir: Path) -> None:
    rows = descendants(root)
    if not rows:
        sys.exit(f"session tree not found for {root}")
    for sid, agent, title in rows:
        name = f"{agent or 'session'}_{sid}"
        try:
            run_export(sid, out_dir / f"{name}.json")
        except SystemExit as e:
            print(f"SKIP {sid}: {e}")


def export_state(swarm: Path, out_dir: Path) -> None:
    state = swarm / "state.json"
    if not state.exists():
        sys.exit(f"state.json not found: {state}")
    data = json.loads(state.read_text(encoding="utf-8"))
    active = data.get("active_sessions") or {}
    if not active:
        print("no active_sessions in state.json")
        return
    for agent_id, session in active.items():
        out = out_dir / f"{agent_id}.json"
        try:
            run_export(session, out)
        except SystemExit as e:
            print(f"SKIP {agent_id}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Backup/restore opencode sessions")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_exp = sub.add_parser("export", help="export one session")
    p_exp.add_argument("--session", required=True)
    p_exp.add_argument("--agent-id", default=None)
    p_exp.add_argument("--out-dir", type=Path, required=True)

    p_state = sub.add_parser("export-state", help="export all state.active_sessions")
    p_state.add_argument("--swarm", type=Path, required=True)
    p_state.add_argument("--out-dir", type=Path, default=None)

    p_tree = sub.add_parser("export-tree", help="export a parent session and all descendants")
    p_tree.add_argument("--root", required=True)
    p_tree.add_argument("--out-dir", type=Path, required=True)

    p_imp = sub.add_parser("import", help="import a session JSON (restores same id)")
    p_imp.add_argument("--file", type=Path, required=True)

    args = ap.parse_args()
    if args.cmd == "export":
        name = args.agent_id or args.session
        run_export(args.session, args.out_dir / f"{name}.json")
    elif args.cmd == "export-state":
        out_dir = args.out_dir or (args.swarm / "sessions")
        export_state(args.swarm, out_dir)
    elif args.cmd == "export-tree":
        export_tree(args.root, args.out_dir)
    elif args.cmd == "import":
        run_import(args.file)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
