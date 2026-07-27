#!/usr/bin/env python3
"""Query decrypted WeCom databases for conversations, contacts, and messages.

Usage:
    python query_wecom.py [--profile <id>] [--action <action>] [options]

Actions:
    stats     - Summary statistics (default)
    sessions  - List all conversations
    contacts  - List/search contacts
    history   - Show message history for a conversation
    search    - Full-text search messages
    export    - Export conversation to Markdown or JSON
"""

import argparse
import io
import json
import os
import sqlite3
import sys
from pathlib import Path
from datetime import datetime

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

OUTPUT_DIR = Path(os.environ["TEMP"]) / "opencode" / "wecom_decrypted"
REPORT_DIR = Path(os.environ["TEMP"]) / "opencode" / "wecom_report"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

TYPE_NAMES = {
    0: "文本", 1: "文本", 2: "文本", 3: "文本",
    4: "图片", 5: "图片", 6: "语音", 7: "语音",
    8: "视频", 14: "截图", 15: "文件",
    38: "应用消息", 40: "通话", 503: "状态",
    516: "链接", 570: "文档",
    1002: "名片", 1011: "会议通知", 1052: "置顶", 1055: "取消置顶",
    123: "表情/引用",
}


def decode_content(content_bytes):
    """Decode message content from bytes (UTF-8 or protobuf extraction)."""
    if not content_bytes:
        return ""
    if isinstance(content_bytes, str):
        return content_bytes
    try:
        text = content_bytes.decode('utf-8')
        control = sum(1 for c in text if ord(c) < 32 and c not in '\n\r\t')
        if control < len(text) * 0.1:
            return text.strip()
    except Exception:
        pass
    # Protobuf text extraction
    try:
        data = content_bytes
        texts = []
        i = 0
        while i < len(data) - 1:
            tag = data[i]
            wire_type = tag & 0x07
            if wire_type == 2:
                i += 1
                length = 0
                shift = 0
                while i < len(data) and shift < 35:
                    b = data[i]
                    length |= (b & 0x7F) << shift
                    shift += 7
                    i += 1
                    if not (b & 0x80):
                        break
                if 0 < length <= len(data) - i:
                    chunk = data[i:i + length]
                    try:
                        t = chunk.decode('utf-8')
                        printable = sum(1 for c in t if ord(c) >= 32 or c in '\n\r\t')
                        if printable >= len(t) * 0.7 and len(t) > 1:
                            texts.append(t)
                    except Exception:
                        pass
                    i += length
                else:
                    i += 1
            elif wire_type == 0:
                i += 1
                while i < len(data) and data[i] & 0x80:
                    i += 1
                i += 1
            else:
                i += 1
        if texts:
            return " ".join(texts)
    except Exception:
        pass
    return f"[二进制{len(content_bytes)}B]"


def format_time(ts):
    if not ts:
        return ""
    if ts > 1e12:
        return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d %H:%M:%S")
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


def load_profile(profile_id):
    """Load decrypted databases for a profile."""
    db_dir = OUTPUT_DIR / profile_id
    if not db_dir.exists():
        print(f"Profile {profile_id} not found at {db_dir}")
        print("Run decrypt_wecom.py first.")
        return None

    conns = {}
    for db_name in ["message.db", "session.db", "user.db"]:
        db_path = db_dir / db_name
        if db_path.exists():
            conns[db_name] = sqlite3.connect(str(db_path))

    if "message.db" not in conns:
        print(f"No message.db found for profile {profile_id}")
        return None

    # Build user map
    user_map = {}
    if "user.db" in conns:
        cur = conns["user.db"].cursor()
        cur.execute("SELECT id, name, real_name FROM user_table")
        for row in cur.fetchall():
            user_map[str(row[0])] = row[1] or row[2] or str(row[0])

    # Build session map
    sess_map = {}
    if "session.db" in conns:
        cur = conns["session.db"].cursor()
        cur.execute("SELECT id, name FROM conversation_table")
        for row in cur.fetchall():
            sess_map[str(row[0])] = row[1] or ""

    conns["_user_map"] = user_map
    conns["_sess_map"] = sess_map
    return conns


def action_stats(conns):
    """Print summary statistics."""
    msg_cur = conns["message.db"].cursor()
    user_map = conns["_user_map"]

    msg_cur.execute("SELECT COUNT(*) FROM message_table")
    total = msg_cur.fetchone()[0]
    print(f"总消息数: {total}")

    msg_cur.execute("SELECT COUNT(DISTINCT conversation_id) FROM message_table")
    conv_count = msg_cur.fetchone()[0]
    print(f"有消息的会话数: {conv_count}")

    # Top senders
    msg_cur.execute("""
        SELECT sender_id, COUNT(*) as cnt
        FROM message_table
        GROUP BY sender_id
        ORDER BY cnt DESC
        LIMIT 20
    """)
    print("\n发送消息最多的用户:")
    for s in msg_cur.fetchall():
        name = user_map.get(str(s[0]), str(s[0]))
        print(f"  {name}: {s[1]}条")

    # Group vs single chat
    msg_cur.execute("""
        SELECT
            CASE WHEN conversation_id LIKE 'R:%' THEN '群聊'
                 WHEN conversation_id LIKE 'S:%' THEN '单聊'
                 ELSE '其他' END as type,
            COUNT(*)
        FROM message_table
        GROUP BY type
        ORDER BY COUNT(*) DESC
    """)
    print("\n消息类型分布:")
    for row in msg_cur.fetchall():
        print(f"  {row[0]}: {row[1]}条")

    # Messages per day (last 30 days)
    msg_cur.execute("""
        SELECT date(send_time/1000, 'unixepoch', 'localtime') as day, COUNT(*)
        FROM message_table
        WHERE send_time > 1719792000000
        GROUP BY day
        ORDER BY day DESC
        LIMIT 30
    """)
    print("\n每日消息数 (最近30天):")
    for row in msg_cur.fetchall():
        print(f"  {row[0]}: {row[1]}条")


def action_sessions(conns, query=None):
    """List all conversations."""
    sess_map = conns["_sess_map"]
    msg_cur = conns["message.db"].cursor()

    msg_cur.execute("""
        SELECT conversation_id, COUNT(*) as cnt, MAX(send_time) as last_time
        FROM message_table
        GROUP BY conversation_id
        ORDER BY last_time DESC
    """)

    results = msg_cur.fetchall()
    if query:
        results = [r for r in results if query.lower() in (sess_map.get(str(r[0]), "") or "").lower()]

    print(f"\n会话列表 ({len(results)}个):\n")
    for cid, cnt, lt in results:
        cid_str = str(cid)
        name = sess_map.get(cid_str, "")
        prefix = cid_str[:2]
        type_str = {"R:": "群", "S:": "单", "M:": "微", "T:": "题", "O:": "应"}.get(prefix, "?")
        print(f"  [{type_str}] {name or '(未命名)':40s} | {cnt:5d}条 | {format_time(lt)}")


def action_contacts(conns, query=None):
    """List/search contacts."""
    user_map = conns["_user_map"]

    if query:
        filtered = {k: v for k, v in user_map.items() if query.lower() in (v or "").lower()}
        print(f"\n联系人搜索 '{query}' ({len(filtered)}个):\n")
    else:
        filtered = user_map
        print(f"\n联系人列表 ({len(filtered)}个):\n")

    for uid, name in sorted(filtered.items(), key=lambda x: x[1] or ""):
        print(f"  {name:30s} ({uid})")


def action_history(conns, chat=None, limit=50):
    """Show message history for a conversation."""
    sess_map = conns["_sess_map"]
    user_map = conns["_user_map"]
    msg_cur = conns["message.db"].cursor()

    # Find conversation by name or ID
    conv_id = None
    if chat:
        for cid, name in sess_map.items():
            if chat.lower() in (name or "").lower() or chat == cid:
                conv_id = cid
                break

    if not conv_id and chat:
        # Try partial ID match
        for cid in sess_map:
            if chat in cid:
                conv_id = cid
                break

    if not conv_id:
        print(f"未找到包含 '{chat}' 的会话")
        return

    conv_name = sess_map.get(conv_id, "(未命名)")
    print(f"\n{'='*60}")
    print(f"  会话: {conv_name}")
    print(f"  ID: {conv_id}")
    print(f"{'='*60}\n")

    msg_cur.execute("""
        SELECT sender_id, content_type, send_time, content
        FROM message_table
        WHERE conversation_id = ?
        ORDER BY send_time DESC
        LIMIT ?
    """, (conv_id, limit))

    rows = list(reversed(msg_cur.fetchall()))
    for r in rows:
        sender = user_map.get(str(r[0]), str(r[0]))
        ctype = TYPE_NAMES.get(r[1], f"type{r[1]}")
        time_str = format_time(r[2])
        content = decode_content(r[3])
        print(f"[{time_str}] {sender} ({ctype})")
        if content:
            print(f"  {content[:500]}")
        print()


def action_search(conns, keyword=None, limit=100):
    """Full-text search messages."""
    user_map = conns["_user_map"]
    sess_map = conns["_sess_map"]
    msg_cur = conns["message.db"].cursor()

    if not keyword:
        print("请提供搜索关键词: --keyword <text>")
        return

    msg_cur.execute("""
        SELECT conversation_id, sender_id, content_type, send_time, content
        FROM message_table
        WHERE content_type IN (0,1,2,3)
        ORDER BY send_time DESC
        LIMIT ?
    """, (limit * 50,))

    matches = []
    for row in msg_cur.fetchall():
        content = decode_content(row[4])
        if keyword.lower() in (content or "").lower():
            matches.append({
                "conversation": sess_map.get(str(row[0]), ""),
                "sender": user_map.get(str(row[1]), str(row[1])),
                "type": TYPE_NAMES.get(row[2], ""),
                "time": format_time(row[3]),
                "content": content[:200],
            })
            if len(matches) >= limit:
                break

    print(f"\n搜索 '{keyword}' 找到 {len(matches)} 条消息:\n")
    for m in matches:
        print(f"[{m['time']}] {m['sender']} @ {m['conversation']}")
        print(f"  {m['content']}")
        print()


def action_export(conns, chat=None, fmt="md", limit=500):
    """Export conversation to Markdown or JSON."""
    sess_map = conns["_sess_map"]
    user_map = conns["_user_map"]
    msg_cur = conns["message.db"].cursor()

    conv_id = None
    if chat:
        for cid, name in sess_map.items():
            if chat.lower() in (name or "").lower() or chat == cid:
                conv_id = cid
                break

    if not conv_id:
        print(f"未找到会话 '{chat}'")
        return

    conv_name = sess_map.get(conv_id, "(未命名)")
    msg_cur.execute("""
        SELECT sender_id, content_type, send_time, content
        FROM message_table
        WHERE conversation_id = ?
        ORDER BY send_time DESC
        LIMIT ?
    """, (conv_id, limit))

    rows = list(reversed(msg_cur.fetchall()))
    messages = []
    for r in rows:
        sender = user_map.get(str(r[0]), str(r[0]))
        ctype = TYPE_NAMES.get(r[1], f"type{r[1]}")
        time_str = format_time(r[2])
        content = decode_content(r[3])
        messages.append({"sender": sender, "type": ctype, "time": time_str, "content": content})

    safe_name = conv_name.replace(":", "_").replace("/", "_")[:50]
    if fmt == "json":
        out_file = REPORT_DIR / f"{safe_name}.json"
        data = {"conversation": conv_name, "id": conv_id, "messages": messages}
        out_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        out_file = REPORT_DIR / f"{safe_name}.md"
        lines = [f"# {conv_name}\n\n"]
        for m in messages:
            lines.append(f"**[{m['time']}] {m['sender']}** ({m['type']})\n{m['content'][:300]}\n\n")
        out_file.write_text("".join(lines), encoding='utf-8')

    print(f"导出 {len(messages)} 条消息到: {out_file}")


def main():
    parser = argparse.ArgumentParser(description="Query WeCom chat data")
    parser.add_argument("--profile", help="Profile ID (default: first available)")
    parser.add_argument("--action", default="stats",
                        choices=["stats", "sessions", "contacts", "history", "search", "export"])
    parser.add_argument("--query", help="Search keyword (for sessions/contacts)")
    parser.add_argument("--chat", help="Conversation name or ID (for history/export)")
    parser.add_argument("--keyword", help="Search keyword (for search)")
    parser.add_argument("--limit", type=int, default=50, help="Max results")
    parser.add_argument("--format", default="md", choices=["md", "json"], help="Export format")
    args = parser.parse_args()

    # Find profile
    profile_id = args.profile
    if not profile_id:
        if OUTPUT_DIR.exists():
            for d in OUTPUT_DIR.iterdir():
                if d.is_dir() and (d / "message.db").exists():
                    profile_id = d.name
                    break
    if not profile_id:
        print("No decrypted profile found. Run decrypt_wecom.py first.")
        return 1

    print(f"Profile: {profile_id}")
    conns = load_profile(profile_id)
    if not conns:
        return 1

    if args.action == "stats":
        action_stats(conns)
    elif args.action == "sessions":
        action_sessions(conns, args.query)
    elif args.action == "contacts":
        action_contacts(conns, args.query)
    elif args.action == "history":
        action_history(conns, args.chat, args.limit)
    elif args.action == "search":
        action_search(conns, args.keyword, args.limit)
    elif args.action == "export":
        action_export(conns, args.chat, args.format, args.limit)

    for k, v in conns.items():
        if isinstance(v, sqlite3.Connection):
            v.close()


if __name__ == "__main__":
    raise SystemExit(main())
