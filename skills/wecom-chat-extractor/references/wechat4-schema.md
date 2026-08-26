# WeChat 4.x (Weixin.exe) Database Schema Notes

Verified on WeChat Windows 4.1.8 (2026-08). Personal WeChat only - WeCom uses a
completely different format (see database-schema.md).

## Locations

```
%USERPROFILE%\Documents\xwechat_files\<wxid_dir>\
  db_storage\
    message\message_0.db      # all chat messages (one Msg_ table per chat)
    message\biz_message_0.db  # official-account (公众号) messages, 100+ tables
    message\message_fts.db    # full-text search index
    message\media_0.db        # voice/media index
    contact\contact.db        # contacts + chatroom list (nick_name/remark)
    session\session.db        # SessionTable (chat list, unread, drafts)
    general\general.db        # revokemessage etc.
    head_image\head_image.db  # avatars
    favorite|emoticon|sns\... # collections, stickers, moments
  msg\, resource\             # media files (.dat image encryption separate)
```

`<wxid_dir>` = `<wxid>_xxx` suffix varies per account; multiple dirs = multiple
logged-in accounts over time. Pick the one with recent db mtime.

## Encryption (SQLCipher 4 via WCDB)

- AES-256-CBC + HMAC-SHA512, page 4096, reserve = IV(16) + HMAC(64) = 80
- **Each DB has its own key AND salt** (18+ DBs per account)
- WeChat 4.0.x caches derived raw keys in process memory as
  `` x'<64-hex enc_key><32-hex salt>' ``
- **WeChat 4.1+ no longer caches the raw key** - only a Config.Cipher object;
  requires runtime scan of that object then PBKDF2-HMAC-SHA512 (256000 iters)
  derivation. Use the vendored `wechat_key_tool_windows.py` which handles both.
- Page layout (main DB): page1 = salt(16) + ct(4000) + iv(16) + hmac(64);
  other pages = ct(4016) + iv(16) + hmac(64)
- HMAC: mac_key = PBKDF2-SHA512(enc_key, salt ^ 0x3a per-byte, **2 iters**, 32B);
  hmac over (ciphertext + iv + LE32(pgno))

## WAL

- Standard SQLite WAL header is plaintext (magic 0x377F0682/83, salts at
  offset 16..23); frame payloads encrypted like normal pages
- WAL files are reused without truncation -> contain stale frames from older
  generations; MUST validate frames via header-salt match + cumulative
  checksum chain before applying (wechat_merge_wal.py does this)
- In-frame pgno=1 pages use the salt-prefix layout (restore "SQLite format 3"
  header when writing out)
- WeChat checkpoints periodically and resets the WAL generation - if you get
  0 valid frames, the live main DB file already contains everything:
  **re-decrypt the main DB** instead (stale decrypted snapshot is the usual
  cause of missing recent messages)

## message_0.db tables

- `Msg_<md5(username)>` - one table per chat; username like
  `54261230522@chatroom` (group) or `wxid_xxx` (direct). Tables appear lazily;
  a brand-new group's table may exist only in WAL.
- Columns: local_id, server_id, local_type, sort_seq, real_sender_id,
  create_time (unix), source (xml), message_content, packed_info_data,
  WCDB_CT_message_content ...
- **message_content compression**: blobs starting with zstd magic
  `28 B5 2F FD` are WCDB-compressed; decompress with zstandard. Plain text
  messages (local_type=1) are usually uncompressed and prefixed with
  `<sender_wxid>:\n`
- `Name2Id(rowid, user_name, is_session)` - **real_sender_id joins
  Name2Id.rowid** (NOT contact.id!) -> user_name -> contact display name.
  Note: Name2Id rowids are per-message-DB; biz_message_0.db has its own space
- `contact.id` is a separate namespace (do not use for sender resolution)

### local_type values seen

1 text, 3 image, 47 sticker, 49/5x link-card XML, 34 voice, 43 video,
10000 system, large values = type with flags in high bits.

## contact.db

- `contact(id, username, nick_name, remark, local_type, ...)`
  - id joins message.real_sender_id
  - groups have username ending `@chatroom`; nick_name = group name
- `chat_room(room_id, owner_id, members_blob)` - protobuf member list

## session.db

- `SessionTable(username, summary, last_timestamp, sort_timestamp, ...)` -
  chat list with last-message preview

## Gotchas checklist

1. Empty result after decrypt -> stale main-DB snapshot; re-run decrypt while
   WeChat is running, or merge a fresher WAL
2. "database disk image is malformed" after merge -> stale frames applied
   (missing checksum-chain validation) or pgno=1 salt-prefix mishandled
3. GitHub links shared WITHOUT the https://github.com prefix (bare
   `owner/repo`) - scan both patterns; filter base64 noise from
   fileuploadtoken fragments (mixed case + digits + len > 20)
