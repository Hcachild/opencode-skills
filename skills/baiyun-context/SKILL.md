---
name: baiyun-context
description: Use when 需要导出或排查运小星(BaiYun_Agent)用户的对话记录：找上下文、生成“找到上下文N_完整对话记录.xlsx”、查询用户某天的 audit log、定位对话里为什么走某工具（如 knowledge_chat 而非 product_compliance_check）、检查 MCP 合规工具是否启用、对比测试/正式环境的工具与提示词差异。触发词：运小星、BaiYun_Agent、by56_wiki、audit log、对话记录、导出Excel、合规工具、MCP、knowledge_chat。
---

# 运小星对话记录导出与排查（baiyun-context）

## Overview
运小星客服机器人（BaiYun_Agent 项目）把所有用户对话按天写入 audit log（JSONL）。本 skill 提供：
1. **导出对话记录为 Excel**——默认精简版（只留用户提问+AI最终回复），可选详细版（含每轮工具调用记录），图片自动提取并嵌入预览。
2. **问题定位**——查对话中实际调用了哪些工具、MCP 是否暴露合规工具、提示词/配置差异，解释"为什么走了 XX 工具"。

核心原则：**audit log 是唯一保留图片与工具调用的数据源**（`conversations.db` 的 `conversation_message` 表会丢图片信息，不要用它导出）。

## 环境与服务器速查

| 环境 | SSH 主机 | IP | 运小星 BaiYun_Agent | 知识库 by56_wiki |
|---|---|---|---|---|
| 正式（默认） | `by_production` | 8.135.23.169 | `/root/BaiYun_Agent` | 无（MCP 指向 by_code_base） |
| 正式·知识库 | `by_code_base` | 120.79.129.209 | 无 | `/root/workspace/by56_wiki`（MCP 端口 10096） |
| 测试 | `by_dev` | 120.79.167.211 | `/root/BaiYun_Agent`（MCP 指向本机 10096） | `/root/workspace/by56_wiki`（MCP 端口 10096） |

- 默认查**正式环境**（by_production）；用户明确说测试环境/本地环境时才用 `by_dev`。知识库 by56_wiki 的排查用 `by_code_base`（正式）。
- 正式 BaiYun_Agent 的 MCP 配置 `mcp_servers.json` 指向 `http://120.79.129.209:10096/mcp`（by_code_base）；测试指向 `http://127.0.0.1:10096/mcp`（本机）。

## 数据源

### audit log（权威）
```
/root/BaiYun_Agent/logs/conversations/audit/{user_id}/{YYYY-MM-DD}.jsonl
```
每行一条记录（一轮对话 round），关键字段：
- `round_index`、`datetime`、`user_name`、`user_department`
- `user_input.text`（用户消息）、`user_input.has_image`、`user_input.image_urls`（`data:image/...;base64,...`）
- `tool_calls[]`：`tool_name`（如 `mcp__by56_knowledge_base__knowledge_chat`、`tool_search`、`quote_tool`、`handoff_to_human`）、`success`、`kind`、`visible_text`（工具可见输出）
- `response`（AI 最终回复）、`metadata.llm_model`
- `rag_context`（如含 `conversation_id: N`，是 by56_wiki 侧的知识库会话）

### conversations.db（备选，丢图片）
`/root/BaiYun_Agent/logs/conversations/conversations.db`，表 `conversation_message`。图片信息不完整，**仅当 audit log 缺失时用**。服务器上可能没有 sqlite3 命令，用 `python3 -c` + sqlite3 模块。

### 找用户 ID
```
ssh by_production "grep -rl '用户名' /root/BaiYun_Agent/logs/conversations/audit/ | sort"
```
输出里取目录名即 user_id，然后 `ls` 该目录确认日期文件。

## 导出 Excel 工作流

流程：读入源 Excel（找到上下文N.xlsx，含 时间/query问题/用户名称）→ 按"用户名称+时间"在 audit log 定位该轮的完整对话（该用户当天 jsonl 的全部轮次，注意**同一用户一天的所有轮次都属于同一上下文**）→ 生成 `找到上下文N_完整对话记录.xlsx`。

1. **读源 Excel**：`python` + openpyxl 读 `时间/query问题/用户名称`。
2. **定位 audit 文件**：`grep -rl 用户名 audit/` → `cat {uid}/{日期}.jsonl`。
3. **导出**：用本 skill 的脚本 `scripts/export_excel.py`：
   - 默认（精简）：`python export_excel.py -i 2026-07-21.jsonl -u 邓番玉 -o 找到上下文4_完整对话记录.xlsx`
   - 详细（含工具调用）：加 `--detailed`
   - 图片：自动保存到 `--img-dir`，并嵌入 Excel"图片预览"列；`--desc "文件名:描述"` 可提供图片描述（可用该轮 AI 回复中识别出的内容，或 qwen3.5-plus VL 读图，见下）。
4. **校验**：重新 load_workbook 打印行列数、图片数，确认可打开。

列结构（精简版）：`用户名称 | 角色 | 时间戳 | 对话内容 | 备注 | 图片描述 | 图片文件 | 图片预览`
- 角色=用户 / AI回复；备注写 `含图片(N张)`；每轮 2 行（用户+AI）。
- 详细版在用户行后插入工具行：角色=工具调用，对话内容=该工具 `visible_text`（或 error），备注=工具名|success。

### 并发/缩写提示
- 一天多条 query 的文件（找到上下文N.xlsx）里，若同一用户名同一天出现多次，导出该用户当天的完整 jsonl，一次导出即可覆盖。
- 工具名带前缀 `mcp__by56_knowledge_base__`，grep 时记住。

## 读图（VL）

场景：需要在 Excel 中补"图片描述"。
- 推荐模型：**qwen3.5-plus**（用户指定）。可用 endpoint：`https://dashscope.aliyuncs.com/compatible-mode/v1`（OpenAI 兼容），key 用 by56_wiki 的 `EMBEDDING_API_KEY`（见 by_code_base `/root/workspace/by56_wiki/.env`，也是 PADDLE_OCR_API_KEY）。
- `https://coding.dashscope.aliyuncs.com/v1` **不支持视觉模型**（会报 model not supported），不要用。
- 若 VL 不可用：图片描述取该轮 AI 回复中对图片内容的识别（如"冲水阀 flush valve"），或标注"见该轮 AI 回复"。

## 问题定位工作流（为什么走了 XX 工具）

例：用户问"MCP 服务器是不是已经有合规工具了，那为什么会走 knowledge_chat？"

1. **看实际调用**：audit log 该轮 `tool_calls` 的 `tool_name`。例：杨汉鹏 2026-08-07 "古董文物能不能发美国" → tools=`['mcp__by56_knowledge_base__knowledge_chat', 'tool_search']`，确认走了 knowledge_chat。
2. **查 MCP 配置**：`cat /root/BaiYun_Agent/mcp_servers.json`
   - **正式环境**：`disabledTools: ["product_compliance_check"]` → 合规工具被禁用，即使暴露也只能走 knowledge_chat。这是最常见原因。
   - **测试环境**：`disabledTools: []`（未禁用）。
3. **查提示词**：`cat /root/BaiYun_Agent/config/mcp_prompts/by56_wiki.md`
   - 测试版 prompt 已有 `product_compliance_check`/`product_hscode_search`/`transport_channel_check` 结构化门禁规范；正式版是旧规范（合规也统一走 `knowledge_chat`）。
   - 若工具存在且未禁用但模型仍走 knowledge_chat：是模型未按 prompt 分流（多意图/门禁识别失败），需看该轮 tool_calls 佐证。
4. **查 MCP 实际暴露的工具**（不依赖 mcp_servers.json，验证运行态）：
   ```python
   # 在 by_dev 或 by_code_base 上执行
   import json, urllib.request
   req = urllib.request.Request('http://127.0.0.1:10096/mcp',
       data=json.dumps({"jsonrpc":"2.0","id":1,"method":"tools/list"}).encode(),
       headers={'Content-Type':'application/json','Accept':'application/json, text/event-stream'})
   body = urllib.request.urlopen(req).read().decode()
   print(body)  # 注意可能是 SSE 格式，需解析 data: 行
   ```
   参考：by_dev 实际暴露 `kb_guide, knowledge_chat, product_compliance_check, product_hscode_search, transport_channel_check, exchange_rate`。
5. **查知识库侧代码/运行状态**：by56_wiki 服务 `ps aux | grep 10096`（uvicorn app.main:app --port 10096）；工具实现位于 `/root/workspace/by56_wiki/app/services/llm_wiki/`（`tools.py`、`compliance_tool.py`、`public_tools.py`）。
6. **对比测试/正式**：把 by_dev 与 by_production 的 mcp_servers.json + mcp_prompts 逐个字段 diff，差异即根因候选。

## 常见坑

| 坑 | 解法 |
|---|---|
| PowerShell 下 `ssh host "python3 -c '...'"` 引号被吞，报语法错误 | 把脚本写成本地文件，`scp` 到服务器 `/tmp` 再 `python3 /tmp/x.py`；或 heredoc `python3 << 'PYEOF'` |
| `ssh host "curl -d '{\"a\":1}'"` 转义混乱 | 用 `--data @/tmp/req.json`（文件方式传 body） |
| MCP tools/list 返回 Parse error | 检查 JSON body 是否被转义污染；用 python urllib 构造请求最稳 |
| 服务器无 sqlite3 命令 | 用 python3 + sqlite3 模块 |
| conversations.db 导出丢图片 | 改用 audit log |
| 图片是 base64 data URL | `header, b64 = url.split(',', 1)`；`ext = 'png' if 'png' in header else 'jpg'` |
| 详细版工具行太多 | 每工具一行，内容取 `visible_text`（截断到合理长度） |

## 关键事实备忘
- 学习模型：`metadata.llm_model`（如 kimi-k2.5 / ark-code-latest）。
- BaiYun_Agent `.env` 关键项：`LLM_API_KEY`、`OPENAI_API_BASE=https://ark.cn-beijing.volces.com/api/plan/v3`、`LLM_MODEL=ark-code-latest`。
- by56_wiki `.env` 关键项：`EMBEDDING_API_KEY`（dashscope，`EMBEDDING_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1`）、`LLM_WIKI_API_KEY`（deepseek）、`KB_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/knowledge_base`。
- knowledge_chat 返回首行 `conversation_id: N` 表示 by56_wiki 侧会话，追问需回传。