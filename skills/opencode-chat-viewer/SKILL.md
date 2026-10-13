---
name: opencode-chat-viewer
description: >-
  查看本机 OpenCode 自己的历史对话记录。数据源是 OpenCode 本地 SQLite 数据库（~/.local/share/opencode/opencode.db，session/message/part 三表），支持按日期列会话、按 ID/标题查看完整对话、关键词搜索、按日期批量导出（写日报/工作纪要等素材场景）。注意边界：不要用 session-logs（那是 clawdbot/openclaw 的 JSONL 日志，路径 ~/.clawdbot/agents/...，与本 skill 无关），也不要用 cursor-chat-viewer（那是 Cursor 的 state.vscdb）。Use when: (1) 查 OpenCode 对话/会话/聊天记录, (2) 找某一天有哪些 OpenCode 会话, (3) 按 session ID 或标题看对话内容, (4) 搜索 OpenCode 历史对话里的关键词, (5) 导出某天的全部 OpenCode 对话。触发词: OpenCode 对话、OpenCode 会话、opencode.db、OpenCode 聊天记录、查 OpenCode 记录、导出 OpenCode 对话。
---

# OpenCode Chat Viewer

读取本机 OpenCode 自己的对话记录（只读，安全）。数据源：`~/.local/share/opencode/opencode.db`（SQLite，实测约 6GB，`part` 表为大头）。

## 与其它"对话查看" skill 的边界（勿杂糅）

| 数据源 | 用什么 |
|---|---|
| OpenCode 本地库 `~/.local/share/opencode/opencode.db` | **本 skill** |
| Cursor 本地库 `%APPDATA%\Cursor\User\globalStorage\state.vscdb` | `cursor-chat-viewer` |
| clawdbot/openclaw 的 JSONL `~/.clawdbot/agents/<id>/sessions/*.jsonl` | `session-logs`（jq 工具链，位置完全不同） |
| 运小星/知识库线上对话（BaiYun_Agent/by56_wiki） | `baiyun-context` |
| 企业微信/个人微信本地库 | `wecom-chat-extractor` |

## 位置

- 默认：`~/.local/share/opencode/opencode.db`（Windows 为 `C:\Users\<user>\.local\share\opencode\opencode.db`），可用 `--db` 覆盖。
- 依赖 Python 3.10+（标准库 sqlite3，无需额外包）。以 `mode=ro` 只读打开，OpenCode 运行中可并发读。

## 使用

脚本：`scripts/opencode-chat.py`。

### 1. 列会话

```powershell
python "C:\Users\Young\.config\opencode\skills\opencode-chat-viewer\scripts\opencode-chat.py" list --date 2026-10-12
python "C:\Users\Young\.config\opencode\skills\opencode-chat-viewer\scripts\opencode-chat.py" list --limit 20
```

输出每行：`sessionId | 标题 | 时间区间 | 消息数 | 目录`。`--date` 列出当天有消息的会话（按时间升序），不加则列最近 `--limit` 个会话。子会话带 `↳` 前缀。

### 2. 按 ID / 标题看完整对话

```powershell
python "...\opencode-chat.py" view ses_0dd996e1effePzF8Km92TkxanG --date 2026-10-10
python "...\opencode-chat.py" view "TAPD查看" --include-reasoning --include-tools
```

`view` 支持完整 ID、ID 前缀、标题模糊匹配（多个命中会列出候选）。默认只输出正文（user/assistant 的 text 部分）；`--include-reasoning` 加思考过程，`--include-tools` 加工具调用（名称/状态/入参摘要）。`--date` / `--from` `--to` 只看窗口内的消息，`--max-chars`（默认 6000，0 不限）截断单条。

### 3. 关键词搜索

```powershell
python "...\opencode-chat.py" search "SN318" --days 14
python "...\opencode-chat.py" search "查询opencode的对话" --from 2026-10-01 --to 2026-10-12
```

搜会话标题 + 全部消息 part 文本，输出命中会话列表（含命中数与前几条片段）。全库 LIKE 扫描约 20 秒，带日期范围会快很多；强烈建议按需加 `--days`/`--from/--to`。

### 4. 按日期批量导出（日报/工作纪要素材）

```powershell
python "...\opencode-chat.py" export --date 2026-10-10 --out C:\...\Temp\opencode --prefix oc_1010 --include-reasoning
```

把当天所有会话逐会话导出为 `<prefix>_<序号>_<标题简化>.txt`（`[role HH:MM:SS]` 行格式），并写 `<prefix>_index.txt` 索引（会话、时间区间、消息数、文件名）。也可 `--session <id>` 只导一个，`--from/--to` 覆盖多天。

## 注意事项

- 三表结构：`session`（标题/目录/时间）→ `message`（data JSON 含 role/time）→ `part`（data JSON 含 type: text/reasoning/tool/step-*）。
- 所有查询只做 SELECT；时间显示为本地时区（库内为毫秒时间戳）。
- 已针对大库优化：按会话查 part 走 `message(session_id,time_created)` + `part(message_id)` 索引，秒级；全库 LIKE 搜索较慢（约 20 秒）。
- 对话正文若被压缩过（compaction part），历史消息可能只剩摘要，属正常现象。
- 若输出到控制台出现乱码，是终端编码问题，文件内容本身是 UTF-8。
