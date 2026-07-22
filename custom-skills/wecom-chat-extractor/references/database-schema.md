# WeCom Database Schema Reference

## Overview

WeCom 5.x on Windows stores three core encrypted SQLite databases per profile:

| Database | Purpose | Key Tables |
|----------|---------|------------|
| `message.db` | All chat messages | `message_table`, `message_small_table` |
| `session.db` | Conversations/sessions | `conversation_table`, `conversation_user_table` |
| `user.db` | Contacts/users | `user_table`, `department_tableV2` |

All databases use wxSQLite3 AES-128-CBC page encryption (4096-byte pages).

---

## message.db

### message_table

Primary message storage. Each row is one message.

| Column | Type | Description |
|--------|------|-------------|
| `message_id` | INTEGER PK | Local message ID (autoincrement) |
| `server_id` | VARCHAR | Server-assigned message ID |
| `sequence` | BIGINT | Monotonic sequence number |
| `sender_id` | VARCHAR | User ID of sender (matches `user_table.id`) |
| `conversation_id` | VARCHAR | Conversation ID (see prefix table below) |
| `content_type` | INTEGER | Message type (see type table below) |
| `send_time` | INTEGER | Timestamp (milliseconds since epoch) |
| `flag` | BIGINT | Bitfield flags |
| `content` | BLOB | Message content (text/protobuf binary) |
| `devinfo` | VARCHAR | Device info |
| `from_app_id` | INTEGER | Source app ID |
| `msg_from_devinfo` | VARCHAR | Extended device info |
| `extra_content` | BLOB | Extra content (links, previews, etc.) |
| `local_extra_content` | BLOB | Local extra content |
| `client_id` | VARCHAR | Client-generated message ID |

### message_small_table

Same schema as `message_table`. Stores older/smaller messages (likely a
compaction tier). Query both tables for full history.

### message_appinfo

| Column | Type | Description |
|--------|------|-------------|
| `msgid` | VARCHAR PK | Message ID |
| `send_time` | INTEGER | Send timestamp |
| `appinfo` | BLOB | Application-specific metadata |

### message_revoke_record_table_v2

| Column | Type | Description |
|--------|------|-------------|
| `con_nid` | INTEGER | Conversation numeric ID |
| `appinfo` | BLOB | Revoke info |
| `sendtime` | INTEGER | Original send time |
| `is_history` | INTEGER | Is this from history |
| `is_lookup` | INTEGER | Lookup flag |
| `msgdata_pb` | BLOB | Protobuf revoke data |

### msg_voice2text

| Column | Type | Description |
|--------|------|-------------|
| `message_id` | VARCHAR PK | Message ID |
| `voice_id` | VARCHAR | Voice clip ID |
| `text` | TEXT | Transcribed text |
| `collapse` | INTEGER | Collapse flag |
| `voice_silent_transfer` | INTEGER | Silent transfer flag |

---

## session.db

### conversation_table

| Column | Type | Description |
|--------|------|-------------|
| `con_numeric_id` | INTEGER PK | Numeric conversation ID |
| `id` | VARCHAR UNIQUE | Conversation ID (e.g. `R:39483580466778`) |
| `name` | VARCHAR | Display name (group name or empty for 1-on-1) |
| `create_time` | BIGINT | Creation timestamp |
| `modify_time` | BIGINT | Last modification timestamp |
| `create_user_id` | VARCHAR | Creator user ID |
| `is_sticked` | INTEGER | Pinned (置顶) flag |
| `is_marked` | INTEGER | Marked flag |
| `last_message_time` | BIGINT | Last message timestamp |
| `last_message_id` | VARCHAR | Last message ID |
| `is_blocked` | INTEGER | Muted/blocked flag |
| `is_collect` | INTEGER | Collected flag |
| `status` | INTEGER | Conversation status |
| `flag` | BIGINT | Bitfield flags |
| `session_id` | VARCHAR | Session ID |
| `roomname_remark` | VARCHAR | Custom remark for room name |
| `from_xid` | VARCHAR | From user ID (for 1-on-1) |
| `to_vid` | VARCHAR | To virtual ID (for 1-on-1) |

### conversation_user_table

Group member mapping.

| Column | Type | Description |
|--------|------|-------------|
| `conversation_id` | VARCHAR | Conversation ID |
| `user_id` | VARCHAR | User ID |
| `join_time` | BIGINT | Join timestamp |
| `gag_type` | INTEGER | Mute type |
| `invite_user_id` | VARCHAR | Who invited this user |
| `nick_name` | VARCHAR | Member nickname in group |
| `is_admin` | INTEGER | Admin flag |
| `join_scene` | INTEGER | How they joined |
| `is_classroom_nickname` | INTEGER | Classroom nickname flag |
| `special_uin_type` | INTEGER | Special user type |

### conversation_extra_table

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR PK | Conversation ID |
| `my_last_send_time` | INTEGER | Last time I sent a message |

### draft_table_1

| Column | Type | Description |
|--------|------|-------------|
| `conversation_id` | VARCHAR PK | Conversation ID |
| `content` | TEXT | Draft content |

### unread_conversation_table

| Column | Type | Description |
|--------|------|-------------|
| `conversation_id` | VARCHAR | Conversation ID |
| `begin_cursor` | VARCHAR | Unread start cursor |
| `current_cursor` | VARCHAR | Current read cursor |
| `unread_count` | INTEGER | Unread message count |

### top_message

| Column | Type | Description |
|--------|------|-------------|
| `key` | VARCHAR PK | Conversation ID |
| `value` | BLOB | Top message data |

---

## user.db

### user_table

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR PK | User ID (e.g. `1688854519855968`) |
| `name` | VARCHAR | Display name |
| `english_name` | VARCHAR | English name |
| `email` | VARCHAR | Email address |
| `mobile` | VARCHAR | Mobile number |
| `phone` | VARCHAR | Phone number |
| `number` | VARCHAR | Employee number |
| `level` | INTEGER | User level |
| `authority` | VARCHAR | Authority |
| `account` | VARCHAR | Account ID |
| `gender` | INTEGER | Gender (1=male, 2=female) |
| `avator_url` | VARCHAR | Avatar URL |
| `corp_id` | VARCHAR | Corporation ID |
| `real_name` | VARCHAR | Real name |
| `position` | VARCHAR | Job position |
| `address` | VARCHAR | Address |
| `external_corp_name` | VARCHAR | External corp name |
| `external_job` | VARCHAR | External job title |

### department_tableV2

| Column | Type | Description |
|--------|------|-------------|
| `id` | VARCHAR PK | Department ID |
| `name` | VARCHAR | Department name |
| `englishname` | VARCHAR | English name |
| `parent_id` | VARCHAR | Parent department ID |
| `pre_id` | VARCHAR | Previous sibling ID |
| `display_order` | INTEGER | Sort order |
| `sequence` | BIGINT | Sequence number |
| `user_count` | INTEGER | Number of users |
| `level` | INTEGER | Hierarchy level |

### user_dept_tableV2

Maps users to departments.

| Column | Type | Description |
|--------|------|-------------|
| `department_id` | VARCHAR | Department ID |
| `user_id` | VARCHAR | User ID |
| `job` | VARCHAR | Job title |
| `is_main_job` | INTEGER | Is main position |
| `sort` | INTEGER | Sort order |
| `staff_type` | INTEGER | Staff type |

### external_user_relation_v3

External (WeChat) contacts.

| Column | Type | Description |
|--------|------|-------------|
| `user_id` | VARCHAR PK | External user ID |
| `status` | INTEGER | Relationship status |
| `remarks` | VARCHAR | Remark name |
| `real_remarks` | VARCHAR | Real remark |
| `create_time` | BIGINT | Added time |
| `corp_remark` | VARCHAR | Corp-level remark |

### wechat_contactV1

WeChat contacts synced to WeCom.

| Column | Type | Description |
|--------|------|-------------|
| `wxid` | VARCHAR PK | WeChat ID |
| `name` | VARCHAR | Display name |
| `avator` | VARCHAR | Avatar URL |

---

## Conversation ID Prefixes

The first 1-2 characters of `conversation_table.id`:

| Prefix | Type | Description |
|--------|------|-------------|
| `R:` | Group | Group chat (群聊) |
| `S:` | Single | One-on-one chat (单聊). Format: `S:<self_id>_<other_id>` |
| `M:` | WeChat | External WeChat contact |
| `T:` | Thread | Topic/thread conversation |
| `O:` | App | Application/official account |
| `Y:` | System | System session |
| `FILEASSIST` | File | File transfer assistant |
| `ANNOUNCE` | System | Announcements |

For `S:` conversations, the ID format is `S:<my_user_id>_<other_user_id>`.
Extract `other_user_id` by splitting on `_` and taking the last part.

---

## Message Content Types

| content_type | Meaning | Content Format |
|--------------|---------|----------------|
| 0 | Text/Mixed | Protobuf or plain text |
| 1 | Text | Plain text |
| 2 | Text | Plain text |
| 3 | Text | Plain text |
| 4 | Image | Binary (protobuf metadata) |
| 5 | Image | Binary (protobuf metadata) |
| 6 | Voice | Binary (audio metadata) |
| 7 | Voice | Binary (audio metadata) |
| 8 | Video | Binary (video metadata) |
| 14 | Screenshot | Protobuf (file path, hash, name) |
| 15 | File | Protobuf (file metadata) |
| 38 | App message | Protobuf |
| 40 | Call | Call metadata |
| 123 | Emoji/Quote | Protobuf (reply reference + content) |
| 503 | Status | Status update |
| 516 | Link | Protobuf (title, URL, description) |
| 570 | Document | Protobuf (file reference) |
| 1002 | Contact card | User IDs (semicolon-separated) |
| 1011 | Meeting notice | Protobuf (meeting details) |
| 1052 | Pin | Pinned message reference |
| 1055 | Unpin | Unpinned message reference |

### Content Decoding

Text messages (type 0-3) may be:
1. Plain UTF-8 text (if control characters < 10%)
2. Protobuf-encoded with embedded text fields
3. Pure binary (unparseable)

The `decode_content()` function in `query_wecom.py` handles all three cases:
1. Try UTF-8 decode with control character check
2. Walk protobuf varint tags, extract length-delimited UTF-8 fields
3. Fallback: `[二进制 NB]` placeholder

---

## Querying Tips

### Find a user by name
```sql
SELECT id, name, real_name FROM user_table
WHERE name LIKE '%关键词%' OR real_name LIKE '%关键词%'
```

### List conversations with message counts
```sql
SELECT c.conversation_id, c.name, COUNT(m.message_id) as cnt,
       MAX(m.send_time) as last_time
FROM conversation_table c
LEFT JOIN message_table m ON c.id = m.conversation_id
GROUP BY c.conversation_id
ORDER BY last_time DESC
```

### Get messages for a conversation
```sql
SELECT sender_id, content_type, send_time, content
FROM message_table
WHERE conversation_id = 'R:39483580466778'
ORDER BY send_time DESC
LIMIT 50
```

### Search messages containing keyword
```sql
SELECT conversation_id, sender_id, send_time, content
FROM message_table
WHERE content_type IN (0,1,2,3)
  AND content LIKE '%关键词%'
ORDER BY send_time DESC
```

Note: `LIKE` on BLOB content is unreliable; use Python-side filtering after
fetching text-type messages.
