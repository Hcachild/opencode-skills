---
name: wecom-chat-extractor
description: >-
  Extract and query local chat data on Windows for BOTH WeCom (企业微信/WeChat Work)
  and personal WeChat 4.x (Weixin.exe). Discovers encrypted SQLite databases,
  extracts decryption keys from process memory (WeCom AES-128 wxSQLite3;
  WeChat SQLCipher 4 with 4.0.x memory-pattern or 4.1+ Config.Cipher runtime scan),
  decrypts databases, merges WAL, and queries conversations, contacts, message
  history, and shared GitHub repos.
  Use when: (1) 查询企业微信聊天记录, (2) 提取企业微信对话数据,
  (3) 搜索企业微信消息, (4) 查看群聊或单聊历史,
  (5) 分析企业微信联系人, (6) 导出企业微信对话,
  (7) 查询/导出个人微信聊天记录, (8) 微信群分享的GitHub项目提取.
  Triggers: 企业微信, WeCom, WXWork, 微信, WeChat, Weixin, 聊天记录, 对话数据,
  群聊消息, 单聊, 微信群GitHub项目.
---

# Chat Extractor: WeCom + Personal WeChat (Windows)

Two independent pipelines. Identify the target app first:

| | Part A: WeCom | Part B: Personal WeChat |
|---|---|---|
| Process | `WXWork.exe` | `Weixin.exe` |
| Data dir | `Documents\WXWork\<profile_id>\Data\` | `Documents\xwechat_files\<wxid_dir>\db_storage\` |
| Encryption | wxSQLite3 AES-128-CBC | SQLCipher 4 (AES-256-CBC + HMAC-SHA512), per-DB key+salt |

---

# Part A: WeCom (企业微信)

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

## Conversation ID Prefixes (WeCom only)

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

## Message Content Types (WeCom only)

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

## Key Tables (WeCom)

See `references/database-schema.md` for full table/column documentation.

## Notes

- Read-only: never modifies source databases
- File locks handled via `CreateFileW` with `FILE_SHARE_READ | FILE_SHARE_WRITE`
- Protobuf binary content is best-effort decoded (varint text extraction)
- Other profiles may use different keys — re-scan if decryption fails

---

# Part B: Personal WeChat 4.x (Weixin.exe / 微信)

Full schema/encryption details: `references/wechat4-schema.md`.

## Prerequisites

- **WeChat desktop 4.x running and logged in** (process `Weixin.exe`)
- **Python 3.10+**, `pip install pycryptodome zstandard`
- Recommended: **admin terminal** (reading Weixin.exe memory needs sufficient rights)
- Windows only for the key tool (macOS/Linux need other tooling)

## How it differs from WeCom

- ~18 separate SQLite DBs per account, each with its **own key + salt**
- SQLCipher 4: AES-256-CBC, page 4096, PBKDF2-HMAC-SHA512 x256000, HMAC-SHA512
- WeChat **4.0.x** caches derived keys in memory as `` x'<64hex key><32hex salt>' ``
- WeChat **4.1+** no longer caches raw keys — needs runtime `Config.Cipher`
  object scan + PBKDF2 derivation (handled by the vendored key tool)
- Message bodies may be **zstd-compressed** (magic `28 B5 2F FD`)

## Workflow (3 steps, run from one working directory)

### Step 1: Extract keys

```bash
python scripts/wechat_key_tool_windows.py extract \
    --db-dir "C:\Users\<you>\Documents\xwechat_files\<wxid_dir>\db_storage" \
    --output all_keys.json
```

Auto-detects account dirs; falls back to explicit `--db-dir`. Expect
`N/N salts 找到密钥`. If extraction fails on 4.0.x-style accounts, the same
tool's older memory-pattern path applies automatically.

### Step 2: Decrypt databases

```bash
python scripts/wechat_key_tool_windows.py decrypt \
    --db-dir "...db_storage" --keys all_keys.json --output decrypted
```

Decrypts every DB into `decrypted/` (HMAC-verified pages).

### Step 2b: Merge WAL (recent messages!)

The tool ignores WAL files. Recent messages often live ONLY in the WAL:

```bash
python scripts/wechat_merge_wal.py --keys all_keys.json \
    --decrypted decrypted --output merged
```

Validates frames by salt chain + cumulative checksum, then page-HMAC picks the
cipher layout. Auto-picks the most recently active account.

> **Stale snapshot gotcha**: WeChat checkpoints periodically and resets the WAL.
> If step 2b reports `0 valid committed frames`, the live main DB already
> contains everything — but your `decrypted/` copy may predate that. Re-run
> Step 2 (decrypt) and then Step 2b again.

### Step 3: Query

```bash
python scripts/query_wechat.py [--merged merged] <action> [options]
```

Actions:

| Action | Description | Options |
|--------|-------------|---------|
| `accounts` | List account data dirs | — |
| `sessions` | Chats with msg counts | `--top N` |
| `contacts` | Search contacts/groups | `--query <name>` |
| `history` | Chat history (zstd-decoded) | `--chat <name>` or `--id <md5>` `--limit N` |
| `search` | Keyword search across chats | `--keyword <text>` `--limit N` |
| `github` | Scan shared GitHub repos (URL + bare owner/repo, base64-noise filtered) | — |

Examples:

```bash
python scripts/query_wechat.py sessions --top 20
python scripts/query_wechat.py history --chat "by56" --limit 200 > by56_history.txt
python scripts/query_wechat.py github
```

Chat tables are named `Msg_<md5(username)>`; group usernames look like
`123456@chatroom`. Senders resolve via `real_sender_id -> Name2Id.rowid ->
user_name -> contact display name` (NOT contact.id).

## Notes (Part B)

- Read-only; source DBs are opened via shared-read snapshots
- WeChat being logged in is required at key-extraction time only
- Keys survive across restarts (key is stable per DB unless version changes);
  no need to re-extract for later re-decrypts
- The vendored key tool is MIT-licensed from
  [TANGandXUE/wcdb-key-tool](https://github.com/TANGandXUE/wcdb-key-tool)
