---
name: cursor-chat-viewer
description: 查看本机 Cursor 的历史对话记录（Agent/Composer 会话）。从 Cursor 的本地 SQLite 数据库（state.vscdb）直接读取，支持按 Agent ID 查看完整对话、按关键词搜索、导出为文件。Use when: (1) 用户给了一个 Cursor Agent ID 想知道里面聊了什么, (2) 想查 Cursor 里的历史对话/聊天记录, (3) 想搜索 Cursor 会话里的某个关键词, (4) 想导出某个 Cursor 对话为文本/JSON。触发词: Cursor 对话、Cursor 聊天记录、Agent ID、cursor chat、查对话、导出对话。
---

# Cursor Chat Viewer

读取本机 Cursor 的对话记录（写入端是 Cursor，只读，安全）。数据源：`%APPDATA%\Cursor\User\globalStorage\state.vscdb`（SQLite）。

## 位置

- Windows: `$env:APPDATA\Cursor\User\globalStorage\state.vscdb`
- macOS: `~/Library/Application Support/Cursor/User/globalStorage/state.vscdb`
- Linux: `~/.config/Cursor/User/globalStorage/state.vscdb`

脚本会自动检测。依赖 `sqlite3` 命令行（已在 PATH 中，若无则提示安装）。

## 使用

脚本：`scripts/cursor-chat.ps1`，用 `&` 调用并传参。

### 1. 列出最近会话

```powershell
& "C:\Users\Young\.config\opencode\skills\cursor-chat-viewer\scripts\cursor-chat.ps1" -List -Limit 20
```

输出每行：`AgentId | 标题 | 工作区 | 更新时间`。用户给了 Agent ID 时直接跳转到第 2 步。

### 2. 按 Agent ID 查看完整对话

```powershell
& "...\cursor-chat.ps1" -AgentId <id>
```

输出会话元数据（标题/模型/工作区/上下文用量）+ 按时间排序的对话：
- `[User]` 用户消息（含附件路径）
- `[Agent]` AI 回复
- `[Tool]` 工具调用（名称/参数/状态，如 `read_file`、`get_mcp_tools`）
- 思考过程默认省略；需要时加 `-IncludeThinking`

### 3. 按关键词搜索

```powershell
& "...\cursor-chat.ps1" -Search "关键词" -Limit 20
```

同时匹配会话标题和消息正文，输出命中会话列表（含命中理由）。

### 4. 导出会话

```powershell
& "...\cursor-chat.ps1" -AgentId <id> -Export <输出目录>
```

导出到目录：`对话.txt`（可读文本）+ `composerData.json` + `bubbles/`（原始 JSON），并打印导出路径。

## 注意事项

- Cursor 正在运行时也可读（SQLite WAL 并发读），只做 SELECT，不写库。
- 所有查询走临时 SQL 文件 + `sqlite3 .read`，避免 PowerShell 中文编码问题；脚本内部已统一 UTF-8。
- 时间显示为本地时区。
- 对话正文若已压缩/汇总，历史消息可能只有摘要，属正常现象。