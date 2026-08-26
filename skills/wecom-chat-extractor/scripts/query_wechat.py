#!/usr/bin/env python3
"""Query decrypted WeChat 4.x databases (from wechat_key_tool_windows.py + wechat_merge_wal.py).

Actions:
    accounts            List WeChat account data dirs
    sessions            List chats with message counts (derived from Msg_ tables)
    contacts            Search contacts (--query <name>)
    history             Chat history (--chat <name|--id <md5|table>> --limit N)
    search              Keyword search across all chats (--keyword <text> [--chat X])
    github              Scan all messages for GitHub repo links (URL + owner/repo)

Requires: pycryptodome (decrypt step), zstandard (compressed message bodies).
"""

import argparse
import datetime
import hashlib
import re
import sqlite3
from pathlib import Path

try:
    import zstandard as zstd

    _dctx = zstd.ZstdDecompressor()
except ImportError:
    _dctx = None

ZSTD_MAGIC = b"\x28\xb5\x2f\xfd"
DEFAULT_ROOT = Path.home() / "Documents" / "xwechat_files"


def pick_account(root: Path, account: str | None) -> Path:
    accounts = [d for d in root.iterdir() if d.is_dir() and (d / "db_storage").exists()] if root.exists() else []
    if not accounts:
        raise SystemExit(f"No WeChat account dirs under {root}")
    if account:
        acct = root / account
        if not acct.exists():
            raise SystemExit(f"Account dir not found: {acct}")
        return acct
    return max(accounts, key=lambda d: (d / "db_storage").stat().st_mtime)


def db_path(merged: Path, rel: str):
    p = merged / rel
    return p if p.exists() else None


def open_db(merged: Path, rel_candidates):
    for rel in rel_candidates:
        p = db_path(merged, rel)
        if p:
            try:
                return sqlite3.connect(p), rel
            except sqlite3.DatabaseError:
                continue
    return None, None


def get_content(content) -> str:
    """Decode message_content; WCDB compresses blobs with zstd."""
    if content is None:
        return ""
    if isinstance(content, bytes):
        if content.startswith(ZSTD_MAGIC) and _dctx is not None:
            try:
                return _dctx.decompress(content).decode("utf-8", "replace")
            except Exception:
                try:
                    return _dctx.decompressobj(content, max_output_size=1 << 24).decode("utf-8", "replace")
                except Exception:
                    return "<zstd decompress failed>"
        return content.decode("utf-8", "replace")
    return str(content)


class ChatIndex:
    """Maps contact username <-> Msg table suffix (md5) and resolves senders."""

    def __init__(self, merged: Path):
        self.merged = merged
        self.h2chat = {}
        self.id2display = {}
        conn, _ = open_db(merged, ["contact/contact.db"])
        display_by_name = {}
        if conn:
            rows = conn.execute(
                "SELECT username, nick_name, remark FROM contact"
            ).fetchall()
            for uname, nick, remark in rows:
                display = remark or nick or uname
                display_by_name[uname] = display
                self.h2chat[hashlib.md5(uname.encode()).hexdigest()] = display
            conn.close()

        # real_sender_id -> Name2Id.rowid -> user_name -> display name
        mconn, _ = open_db(merged, ["message/message_0.db"])
        if not mconn:
            return
        for rid, uname in mconn.execute("SELECT rowid, user_name FROM Name2Id"):
            self.id2display[rid] = display_by_name.get(
                uname, display_by_name.get(uname.lower(), uname)
            )
        mconn.close()

    def msg_tables(self):
        conn, _ = open_db(self.merged, ["message/message_0.db"])
        if not conn:
            raise SystemExit(f"message_0.db not found under {self.merged} - run decrypt+merge first")
        tables = [
            r[0]
            for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'Msg_%'")
        ]
        conn.close()
        return tables

    def chat_name(self, table: str) -> str:
        return self.h2chat.get(table[4:], table)

    def sender(self, sid) -> str:
        return self.id2display.get(sid, f"uid{sid}")


def fmt_ts(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")


STRIP_SENDER_PREFIX = re.compile(r"^[\w\-]+:\r?\n")


def clean_text(text: str) -> str:
    return STRIP_SENDER_PREFIX.sub("", text)


def iter_messages(merged: Path, idx: ChatIndex, only_table: str | None = None):
    conn, _ = open_db(merged, ["message/message_0.db"])
    tables = [only_table] if only_table else idx.msg_tables()
    for t in tables:
        try:
            rows = conn.execute(
                f"SELECT create_time, real_sender_id, local_type, message_content FROM [{t}] ORDER BY sort_seq"
            ).fetchall()
        except sqlite3.DatabaseError:
            continue
        for ts, sid, typ, content in rows:
            yield t, ts, idx.sender(sid), typ, get_content(content)
    conn.close()


def action_accounts(args):
    root = Path(args.root)
    if not root.exists():
        raise SystemExit(f"{root} not found")
    for d in sorted(root.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
        if d.is_dir():
            print(f"{d.name:35s} last activity: {fmt_ts(d.stat().st_mtime)}")


def action_sessions(args):
    merged = Path(args.merged)
    idx = ChatIndex(merged)
    conn, _ = open_db(merged, ["message/message_0.db"])
    stats = []
    for t in idx.msg_tables():
        n, lo, hi = conn.execute(
            f"SELECT COUNT(*), MIN(create_time), MAX(create_time) FROM [{t}]"
        ).fetchone()
        stats.append((hi or 0, idx.chat_name(t), n))
    stats.sort(reverse=True)
    print(f"{'last message':<18} {'msgs':>6}  chat")
    for hi, name, n in stats[: args.top]:
        print(f"{fmt_ts(hi):<18} {n:>6}  {name}")


def action_contacts(args):
    merged = Path(args.merged)
    conn, _ = open_db(merged, ["contact/contact.db"])
    if not conn:
        raise SystemExit("contact.db not found")
    q = f"%{args.query}%"
    for uname, nick, remark, typ in conn.execute(
        "SELECT username, nick_name, remark, local_type FROM contact "
        "WHERE nick_name LIKE ? OR remark LIKE ? OR username LIKE ?",
        (q, q, q),
    ):
        tag = "[群]" if uname.endswith("@chatroom") else ""
        print(f"{tag}{uname:35s} nick={nick!s:<20} remark={remark}")


def resolve_chat_table(idx: ChatIndex, args) -> str | None:
    if getattr(args, "id", None):
        return args.id if args.id.startswith("Msg_") else f"Msg_{args.id}"
    if getattr(args, "chat", None):
        target = args.chat.lower()
        conn, _ = open_db(idx.merged, ["message/message_0.db"])
        for h, name in idx.h2chat.items():
            if target in name.lower() or target == h.lower():
                cand = f"Msg_{h}"
                if conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (cand,)
                ).fetchone():
                    return cand
        raise SystemExit(
            f"Chat '{args.chat}' has no message table (no indexed messages?). "
            "Run the sessions action to list known chats."
        )
    return None


def action_history(args):
    merged = Path(args.merged)
    idx = ChatIndex(merged)
    table = resolve_chat_table(idx, args)
    msgs = list(iter_messages(merged, idx, table))
    limit = args.limit or len(msgs)
    print(f"== {idx.chat_name(table)} ({len(msgs)} msgs, showing last {limit}) ==")
    for t, ts, sender, typ, text in msgs[-limit:]:
        body = clean_text(text)[:500].replace("\n", "\n    ")
        print(f"[{fmt_ts(ts)}] {sender}: {body}")


def action_search(args):
    merged = Path(args.merged)
    idx = ChatIndex(merged)
    table = resolve_chat_table(idx, args) if getattr(args, "chat", None) or getattr(args, "id", None) else None
    kw = args.keyword.lower()
    hits = 0
    for t, ts, sender, typ, text in iter_messages(merged, idx, table):
        if kw in text.lower():
            where = idx.chat_name(t)
            print(f"[{fmt_ts(ts)}] ({where}) {sender}: {clean_text(text)[:300]}")
            hits += 1
            if args.limit and hits >= args.limit:
                break
    print(f"-- {hits} hit(s)")


GH_URL = re.compile(r"https?://(?:www\.)?(?:github\.com)/([\w.\-]+)/([\w.\-]+)")
ANY_URL = re.compile(r"https?://\S+")
GH_BARE = re.compile(r"(?<![\w./@+\-])([a-zA-Z][\w\-]{1,30})/([a-zA-Z][\w.\-]{2,40})(?![\w./@+=])")
BARE_STOP = {"v1", "v2", "api", "http", "https", "page", "t", "cgi-bin"}


def looks_like_base64(s: str) -> bool:
    return len(s) > 20 or (any(c.isupper() for c in s) and any(c.isdigit() for c in s))


def action_github(args):
    merged = Path(args.merged)
    idx = ChatIndex(merged)
    seen = {}
    for t, ts, sender, typ, text in iter_messages(merged, idx):
        if "/" not in text:
            continue
        found = []
        for m in GH_URL.finditer(text):
            found.append(f"https://github.com/{m.group(1)}/{m.group(2)}")
        stripped = ANY_URL.sub(" ", text)  # strip all URLs before bare matching
        for m in GH_BARE.finditer(stripped):
            owner, repo = m.group(1), m.group(2)
            if owner.lower() in BARE_STOP or repo.lower() in BARE_STOP:
                continue
            if "." in owner or "_" in owner or looks_like_base64(owner):
                continue  # GitHub usernames never contain . or _; base64 tokens
            found.append(f"{owner}/{repo} (bare - verify owner)")
        for repo in found:
            key = repo.lower()
            if key not in seen:
                seen[key] = (ts, idx.chat_name(t), sender, repo, clean_text(text))
    print(f"unique repos: {len(seen)}\n")
    for key, (ts, chat, sndr, repo, text) in sorted(seen.items(), key=lambda kv: kv[1][0]):
        print("=" * 88)
        print(f"{fmt_ts(ts)} | {chat} | {sndr} | {repo}")
        snippet = text[:260].replace("\n", " | ")
        print(f"   {snippet}")


def main():
    ap = argparse.ArgumentParser(description="Query decrypted WeChat 4.x databases")
    ap.add_argument("--root", default=str(DEFAULT_ROOT))
    ap.add_argument("--account", help="wxid dir (default: most recent)")
    ap.add_argument("--merged", default="merged", help="dir containing decrypted+WAL-merged DBs")
    sub = ap.add_subparsers(dest="action", required=True)

    sub.add_parser("accounts", help="list account dirs")

    p = sub.add_parser("sessions", help="chats with counts")
    p.add_argument("--top", type=int, default=50)

    p = sub.add_parser("contacts", help="search contacts")
    p.add_argument("--query", default="")

    p = sub.add_parser("history", help="chat history")
    p.add_argument("--chat", help="chat name (fuzzy)")
    p.add_argument("--id", help="Msg table suffix (md5 hex) or full table name")
    p.add_argument("--limit", type=int, default=100)

    p = sub.add_parser("search", help="keyword search")
    p.add_argument("--keyword", required=True)
    p.add_argument("--chat")
    p.add_argument("--id")
    p.add_argument("--limit", type=int, default=30)

    sub.add_parser("github", help="scan for shared GitHub repos")

    args = ap.parse_args()
    if args.action == "accounts":
        action_accounts(args)
        return
    acct = pick_account(Path(args.root), args.account)
    merged_root = Path(args.merged)
    # default working convention: run decrypt/merge/query from one workdir
    if not merged_root.exists() and (Path("decrypted") / "message" / "message_0.db").exists():
        pass  # fall through; error surfaces later with a clear message

    if args.action == "sessions":
        action_sessions(args)
    elif args.action == "contacts":
        action_contacts(args)
    elif args.action == "history":
        action_history(args)
    elif args.action == "search":
        action_search(args)
    elif args.action == "github":
        action_github(args)


if __name__ == "__main__":
    main()
