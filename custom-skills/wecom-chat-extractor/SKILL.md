---
name: wecom-chat-extractor
description: >-
  Extract and query WeCom (企业微信/WeChat Work) local chat data on Windows.
  Discovers encrypted SQLite databases, scans WXWork.exe process memory for the
  AES-128 decryption key, decrypts message.db/session.db/user.db (including WAL),
  and queries conversations, contacts, and message history.
  Use when: (1) 查询企业微信聊天记录, (2) 提取企业微信对话数据,
  (3) 搜索企业微信消息, (4) 查看群聊或单聊历史,
  (5) 分析企业微信联系人, (6) 导出企业微信对话.
  Triggers: 企业微信, WeCom, WXWork, 聊天记录, 对话数据, 群聊消息, 单聊.
---

# WeCom Chat Extractor (Windows)

Extract WeCom (企业微信) local chat data from encrypted SQLite databases on Windows.

## Prerequisites

- **WeCom desktop** installed and running (process `WXWork.exe`)
- **Python 3.10+** with `pycryptodome` (`pip install pycryptodome`)
- No admin rights needed (uses `PROCESS_VM_READ` only)

## Database Locations

WeCom 5.x on Windows stores data under:

```
%USERPROFILE%\Documents\WXWork\<profile_id>\Data\
  message.db        # Messages (encrypted, AES-128-CBC, 4096-byte pages)
  session.db        # Conversations/sessions
  user.db           # Contacts/users
  message_lookup.db # Message search index
  *.db-wal          # Write-Ahead Log (committed frames merged during decrypt)
```

Multiple `<profile_id>` directories exist (one per logged-in account). Each profile
uses a **different** 16-byte AES key.

## Encryption

WeCom uses wxSQLite3-style AES-128-CBC page encryption:

- **Page size**: 4096 bytes
- **Raw key**: 16 bytes, found in WXWork.exe process memory
- **Per-page key**: `MD5(raw_key + LE(page_number) + b"sAlT")`
- **Per-page IV**: LCG-seeded MD5 based on page number
- **Page 1 special**: SQLite header bytes 0-16 stripped; bytes 16-24 kept as
  plaintext recognition marker; ciphertext = bytes[8:16] + bytes[24:]
- **WAL**: 32-byte header + 24-byte frame headers; committed frames decrypted
  and merged into plaintext snapshot

## Workflow

### Step 1: Scan for the decryption key

```bash
python scripts/scan_key_win.py
```

- Finds `WXWork.exe` PID via `tasklist`
- Opens process with `PROCESS_VM_READ` (no admin needed)
- Enumerates RW memory regions via `VirtualQueryEx`
- Reads each region with `ReadProcessMemory`
- Validates 16-byte candidates against page 1 of the largest encrypted DB
- Saves key to `%TEMP%\opencode\wecom_key.txt`

Output: `KEY FOUND: <hex_string>`

### Step 2: Decrypt databases

```bash
python scripts/decrypt_wecom.py [--key <hex>] [--profile <id>]
```

- Reads encrypted DB + WAL files (handles file locks via `CreateFileW` shared mode)
- Decrypts all pages, merges WAL committed frames
- Writes plaintext snapshots to `%TEMP%\opencode\wecom_decrypted\<profile>\`

Options:
- `--key`: Override key (default: read from `wecom_key.txt`)
- `--profile`: Decrypt only one profile (default: all)

### Step 3: Query conversations

```bash
python scripts/query_wecom.py [--profile <id>] [--action <action>] [options]
```

Actions:

| Action | Description | Options |
|--------|-------------|---------|
| `sessions` | List all conversations | `--query <keyword>` |
| `contacts` | List/search contacts | `--query <name>` |
| `history` | Show message history | `--chat <name>` `--limit <N>` |
| `search` | Full-text search messages | `--keyword <text>` `--limit <N>` |
| `export` | Export to Markdown/JSON | `--chat <name>` `--format <md\|json>` |
| `stats` | Summary statistics | — |

Default action: `stats`.

### Quick one-liner (scan + decrypt + query)

```bash
python scripts/scan_key_win.py && python scripts/decrypt_wecom.py && python scripts/query_wecom.py
```

## Conversation ID Prefixes

| Prefix | Type |
|--------|------|
| `R:` | Group chat (群聊) |
| `S:` | One-on-one chat (单聊) |
| `M:` | WeChat external contact (微信联系人) |
| `T:` | Thread/topic |
| `O:` | Application/official account |
| `Y:` | System session |
| `FILEASSIST` | File transfer assistant |
| `ANNOUNCE` | Announcements |

## Message Content Types

| content_type | Meaning |
|--------------|---------|
| 0,1,2,3 | Text (文本) |
| 4,5 | Image (图片) |
| 6,7 | Voice (语音) |
| 8 | Video |
| 14 | Screenshot |
| 15 | File |
| 38 | App message |
| 40 | Call/audio-video |
| 123 | Emoji/quote reply |
| 503 | Status |
| 516 | Link |
| 570 | Document |
| 1002 | Contact card |
| 1011 | Meeting notice |

## Key Tables

See `references/database-schema.md` for full table/column documentation.

## Notes

- Read-only: never modifies source databases
- File locks handled via `CreateFileW` with `FILE_SHARE_READ | FILE_SHARE_WRITE`
- Protobuf binary content is best-effort decoded (varint text extraction)
- Other profiles may use different keys — re-scan if decryption fails
