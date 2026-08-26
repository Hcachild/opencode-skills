---
name: baiyun-context
description: Use when 需要导出或排查运小星(BaiYun_Agent)用户的对话记录：找上下文、生成"找到上下文N_完整对话记录.xlsx"、按时间段全量导出对话（含模块/answer_state/联网搜索指标）、查询用户某天的 audit log、定位对话里为什么走某工具（如 knowledge_chat 而非 product_compliance_check）、排查联网搜索触发/模块为空/答案为空等问题、检查 MCP 合规工具是否启用、对比测试/正式环境的工具与提示词差异。触发词：运小星、BaiYun_Agent、by56_wiki、audit log、对话记录、导出Excel、合规工具、MCP、knowledge_chat、联网搜索、knowledge_events、mcp_tool_audits、模块、answer_state。
---

# 运小星对话记录导出与排查（baiyun-context）

> **更新：2026-08-25**（初始构建 2026-08-10）
> 8/23 09:47:54 运小星新版上线后有重大行为变化（图片不落盘、direct_output 工具回复、遥测默认值），本版已按现状重写；旧版中失效的内容移至文末「已废弃内容」。

## Overview
运小星客服机器人（BaiYun_Agent 项目）把所有用户对话按天写入 audit log（JSONL），知识库问答/联网行为遥测写入 knowledge_events.jsonl，KB 服务端 MCP 调用审计写入 RDS `mcp_tool_audits` 表。本 skill 提供：
1. **导出对话记录为 Excel**——单用户上下文版（找到上下文N_完整对话记录.xlsx），或按时间段全量版（含 模块/answer_state/上传文件/联网指标/request_id 等列）。
2. **问题定位**——查对话实际调用的工具、模块分类来源、联网搜索为何触发/未触发、MCP 配置与提示词差异。

核心原则（2026-08-23 新版后）：**audit log 是对话主数据源，但图片二进制已不落盘**；知识库分类（模块）/回答状态/联网指标以 `knowledge_events.jsonl` 为准；MCP 调用审计与 trace id 以 RDS `mcp_tool_audits` 为准。

## 环境与服务器速查

| 环境 | SSH 主机 | IP | 运小星 BaiYun_Agent | 知识库 by56_wiki |
|---|---|---|---|---|
| 正式（默认） | `by_production` | 8.135.23.169 | `/root/BaiYun_Agent` | 无（MCP 指向 by_code_base） |
| 正式·知识库 | `by_code_base` | 120.79.129.209 | 无 | `/root/workspace/by56_wiki`（MCP 端口 10096） |
| 测试 | `by_dev` | 120.79.167.211 | `/root/BaiYun_Agent`（MCP 指向本机 10096） | `/root/workspace/by56_wiki`（MCP 端口 10096） |

- 默认查**正式环境**（by_production）；用户明确说测试环境/本地环境时才用 `by_dev`。知识库 by56_wiki 的排查用 `by_code_base`（正式）。
- 正式 BaiYun_Agent 的 MCP 配置 `mcp_servers.json` 指向 `http://120.79.129.209:10096/mcp`（by_code_base）；测试指向 `http://127.0.0.1:10096/mcp`（本机）。
- **by_code_base 工作区代码可能落后于线上**：`git -C /root/workspace/by56_wiki log --oneline -1` 对比 `origin/main`。看线上真实逻辑用 `git -C /root/workspace/by56_wiki show origin/main:app/...`（2026-08-22 release a621cdc 起含联网策略/审计服务）。
- by_code_base 系统python3 缺包；DB/依赖操作用 `/root/workspace/by56_wiki/.venv/bin/python`（含 psycopg3）。

## 数据源（2026-08-25 现状）

### 1) audit log（对话主数据）
```
/root/BaiYun_Agent/logs/conversations/audit/{user_id}/{YYYY-MM-DD}.jsonl
```
每行一条记录（一轮对话 round），关键字段：
- `round_index`、`datetime`、`user_name`、`user_department`、`message_id`、`trace_id`（8位hex，关联键）
- `user_input.text`（用户消息；附件以 `[文件: xxx.png]` 或 `[附件1] xxx（类型：png；大小：25.5KB）` 文本内联）、`user_input.image_urls`（**8/23 新版后恒为空**）
- `tool_calls[]`：`tool_name`、`success`、`payload`（含 `formatted_text`/`message`/`direct_output`）
- `response`（AI 最终回复；**direct_output 业务工具回复时为空**，见「答案回退链」）

### 2) knowledge_events.jsonl（知识库遥测：模块/answer_state/联网指标）
```
/root/BaiYun_Agent/logs/knowledge_events.jsonl
```
- 事件类型：`evt_ai_qa_question_submit`（提交）、`evt_qa_exact_match_reply`（回复）、`ai_qa_answer_show_wai`（最终展示，含 kb_* 指标）、`evt_yxx_fuzzy_*`（模糊引导）等
- **`message_id` 与 audit log 100% 关联；`trace_id` == audit `trace_id`**（2026-08-25 已验证）
- 关键字段：`knowledge_category_name`（模块：合规（拒收基础+资质）/QA常规问答/HSCode/渠道产品信息；**空=答案非知识库产出**）、`answer_state`（完全命中回答来源/追问/引导/其他；**非知识库轮次是默认值，勿当真实命中**）、`answer_content`、`kb_selected_source`（public_web/enterprise_knowledge）、`kb_confidence_score`（=top1_score）、`kb_latency_ms`（企业检索耗时）、`kb_network_latency_ms`（联网耗时）、`kb_network_answer_content`
- 按行 grep 日期字符串过滤；同 message_id 多条事件，聚合取第一个非空值

### 3) mcp_tool_audits（KB 服务端 MCP 审计，RDS）
- 库：by_code_base `.env` 的 `KB_DATABASE_URL`（阿里云 RDS PostgreSQL knowledge_base）
- 连接：`/root/workspace/by56_wiki/.venv/bin/python` + `psycopg`（系统 python3 缺包，psql 不可用）
- 列：`tool`、`user_question`、`request_id`、`outer_trace_id`、`langfuse_trace_id`、`elapsed_ms`、`result_status`、`extras_json`、`created_at`
- **`outer_trace_id` == audit `trace_id`**（关联键）
- `extras_json` 按工具白名单存储（前端标签见 `frontend/src/features/knowledge-admin/McpAuditDetailDrawer.tsx`）：
  - knowledge_chat：`top1_score`、`similarity_level`、`online_mode`、`kb_elapsed_ms`(企业检索耗时ms)、`web_elapsed_ms`(联网耗时ms)、`online_summary_status`(联网总结: skipped/ok/failed)、`online_summary_content`(Fast Model 文本摘要)、`online_search_content`(联网搜索文本摘要)、`conversation_id`
  - product_compliance_check：`decision`、`gate.action`、`decision_id`、`evidence_summary.final_basis`(public_web/enterprise_knowledge)、`evidence_summary.knowledge_base.status`、`evidence_summary.public_web.status`、`kb_evidence`、`extracted_facts`、`cross_check`、`web_attempts`、`web_search_content`、`fast_model_output`、`qualification_requirements`、`missing_fields`。**无 top1_score**（检索相似度 similarity_score 只存在于内存 metadata，未落库）

## 关联键（三方对齐）
```
audit.trace_id == knowledge_events.trace_id == mcp_tool_audits.outer_trace_id
audit.message_id == knowledge_events.message_id（100% 命中）
```

## 8/23 09:47:54 新版行为变化（重要）
1. **图片二进制不落盘**：`user_input.image_urls` 恒为空，附件只剩文本引用；原始文件在网关内存缓存 TTL 600s（10分钟），过期/重启即失，**事后无法找回**。VLM 视觉描述（`vision_summary`）只注入当轮 prompt，不落盘（audit/metadata/agent.log 均无正文）。
2. **direct_output 业务工具回复**（报价卡/面单卡等）：`response` 为空，实际回复在 `tool_calls[].payload.formatted_text` 或 `payload.message`。
3. **遥测默认值陷阱**：非知识库轮次（询价/面单/转人工）也会上报 evt_ai_qa_question_submit，其 `knowledge_category_name` 为空、`answer_state` 是默认"完全命中回答来源"——不是真实命中。
4. 模块分类规则（KB 侧 `_select_knowledge_category`）：按该轮实际调用的知识库工具定类——compliance→合规（拒收基础+资质）、hscode→HSCode、transport_channel→渠道产品信息、search→QA常规问答；都没调用→空。

### 找用户 ID
```
ssh by_production "grep -rl '用户名' /root/BaiYun_Agent/logs/conversations/audit/ | sort"
```
输出里取目录名即 user_id，然后 `ls` 该目录确认日期文件。

## 导出 Excel 工作流

### A) 单用户上下文版（找到上下文N_完整对话记录.xlsx）
流程：读入源 Excel（找到上下文N.xlsx，含 时间/query问题/用户名称）→ 按"用户名称+时间"在 audit log 定位该轮的完整对话（该用户当天 jsonl 的全部轮次，注意**同一用户一天的所有轮次都属于同一上下文**）→ 生成 `找到上下文N_完整对话记录.xlsx`。

1. **读源 Excel**：`python` + openpyxl 读 `时间/query问题/用户名称`。
2. **定位 audit 文件**：`grep -rl 用户名 audit/` → `cat {uid}/{日期}.jsonl`。
3. **导出**：用本 skill 的脚本 `scripts/export_excel.py`：
   - 默认（精简）：`python export_excel.py -i 2026-07-21.jsonl -u 邓番玉 -o 找到上下文4_完整对话记录.xlsx`
   - 详细（含工具调用）：加 `--detailed`
   - 图片：**仅适用旧版数据（8/23 前）**，自动保存到 `--img-dir` 并嵌入"图片预览"列；8/23 后无 base64 可提取。
4. **校验**：重新 load_workbook 打印行列数，确认可打开。

列结构（精简版）：`用户名称 | 角色 | 时间戳 | 对话内容 | 备注 | 图片描述 | 图片文件 | 图片预览`

### B) 时间段全量版（2026-08-25 新增，推荐）
按时间段导出所有人的知识库相关对话，列结构（17 列）：
`时间 | query问题 | 运小星答案 | 模块 | 用户名称 | answer_state | 上传文件 | 是否触发联网搜索 | top1_score | 企业检索耗时(ms) | 联网耗时(ms) | 联网用途 | Fast Model 文本摘要 | 联网搜索文本摘要 | request_id | langfuse_trace_id | outer_trace_id`

流程（三方合并）：
1. by_production：audit log + knowledge_events.jsonl 按 message_id 聚合（参考会话中已验证的提取脚本模式：过滤日期→聚合 events 首个非空值→answer 回退链）。
2. by_code_base：`mcp_tool_audits` 按时间段导出 JSON（psycopg）。
3. 本地按 `trace_id == outer_trace_id` 关联合并生成 xlsx。

**答案回退链**（关键）：`response` → events `answer_content` → `tool_calls[].payload.formatted_text / payload.message`（跳过 tool_search/exec）。direct_output 工具（quote/waybill/invoice 等）的回复只能从第三级拿到。

**模块空时标注业务类型**：按 tool_calls 推断——quote_tool/express_quote_tool→非知识库·询价报价、waybill_tool→面单查询、handoff_to_human→转人工、invoice_convert_tool→发票转换、无工具→指令/引导。

**联网用途生成规则**（与代码阈值一致）：knowledge_chat 行按 top1_score 三档（见下节）；合规行按 `evidence_summary.*` 生成"企业知识+联网并行核验（企业:X / 联网:Y），最终依据:Z"。

**Excel 写入坑**：
- 单元格文本上限 **32767 字符**，超限 Excel 报"内容有问题"并要求修复——所有字段写入前截断到 32000。
- 清洗 XML 非法字符：`[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f\ud800-\udfff...]`。
- 时间格式化 `YYYY-MM-DD HH:MM:SS`（去掉 T 和微秒，用户要求）。
- dict/list 值先 `json.dumps` 再写入。

**开发/测试人员过滤**（内部人员对话不纳入统计，2026-08-25 名单）：
钟嘉祥、郭立城、黄嘉洋、Jerry、Larry、李亮、林业丰、李清云、麦浩龙、唐健新、Tron、王帅、许培泉、杨汉鹏、张伟

### 并发/缩写提示
- 一天多条 query 的文件（找到上下文N.xlsx）里，若同一用户名同一天出现多次，导出该用户当天的完整 jsonl，一次导出即可覆盖。
- 工具名带前缀 `mcp__by56_knowledge_base__`，grep 时记住。

## 联网搜索策略速查（2026-08-25，源自 by56_wiki origin/main 代码）

### QA（knowledge_chat）：按 top1_score 三档
阈值：`qa_kb_reliable_threshold=0.9`、`qa_kb_partial_threshold=0.5`（app/core/config.py）。

| top1_score | 行为 | 用户看到的答案来自 |
|---|---|---|
| ≥ 0.9 | 完全不联网 | 企业知识库 |
| 0.5 ~ 0.9 | 联网仅审计（audit_in_finalize），结果不给用户 | 企业知识库 |
| ≤ 0.5 | 立即联网（sync_immediately），Fast Model 总结网页原文（≤600字，即 online_summary_content；失败回退原文） | 联网（kb_selected_source=public_web） |

例外：时效类问题（政策/新规/认证/费率/关税/海关等关键词）强制联网；企业内部事实（账户/制度/地址/联系人）不联网、以知识库为准。

### 合规（product_compliance_check）：不看分数，策略开关 + 并行核验
- 开关：`compliance_online_policies` 表（空则回退 env `COMPLIANCE_ONLINE_MODE`，**默认 disabled**）；`ComplianceOnlinePolicyService` 每请求加载，TTL 10s 缓存。
- 开启后：企业知识检索（主线程）与联网搜索（子线程，豆包搜索 API，最多 2 查询，24s 超时）**并行**执行，与知识库是否命中无关。
- 联网结论由模型直接给 allow/reject/no_conclusion 候选 + 资质要求；`merge_compliance_decisions` 合并后 `final_basis` 决定最终依据（public_web=用户看到联网结论 / enterprise_knowledge=看到知识库规则）；联网失败 fail-closed 回退。
- 高危品自动加法规增强词（鳄鱼皮→CITES/FWS、无人机→EAR/FCC、玩具→CPSC/CPC）。

## 读图（VL）

场景：需要在 Excel 中补"图片描述"。**仅适用 8/23 前的旧数据**（新版图片二进制不落盘，无图可读；描述只能取该轮 AI 回复中对图片内容的引用）。
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
5. **查知识库侧代码/运行状态**：by56_wiki 服务工具实现位于 `/root/workspace/by56_wiki/app/services/llm_wiki/`（`tools.py`、`compliance_tool.py`、`telemetry.py`）；联网策略 `qa_online_policy.py`、`compliance/policy.py`。**工作区代码可能旧于线上**，用 `git show origin/main:<path>` 看真实逻辑。
6. **对比测试/正式**：把 by_dev 与 by_production 的 mcp_servers.json + mcp_prompts 逐个字段 diff，差异即根因候选。
7. **排查"模块为空/答案为空"**（2026-08-25 新增）：
   - 模块为空 → 该轮答案非知识库产出（询价/面单/转人工等业务流程），看 audit `tool_calls` 即知；知识库真实回答的行必有 knowledge_category_name。
   - 答案为空 → 按「答案回退链」去 tool payload 找 direct_output 输出。
   - answer_state 可疑（如转人工却显示"完全命中回答来源"）→ 遥测默认值，不可信。
8. **排查联网问题**：knowledge_chat 看 extras 的 `online_summary_status`（skipped=未触发/ok/failed）+ `top1_score` 分档；合规看 `evidence_summary.public_web.status`、`cross_check`、`web_attempts`；agent 侧事件看 `kb_selected_source`、`kb_network_latency_ms`。

## 常见坑

| 坑 | 解法 |
|---|---|
| PowerShell 下 `ssh host "python3 -c '...'"` 引号被吞，报语法错误 | 把脚本写成本地 .py 文件，`scp` 到服务器 `/tmp` 再 `python3 /tmp/x.py`（**最稳，一律用此法**） |
| PowerShell 本地 `python -c "多行代码"` 含中文/引号也易炸 | 同上，写临时 .py 文件执行 |
| `ssh host "curl -d '{\"a\":1}'"` 转义混乱 | 用 `--data @/tmp/req.json`（文件方式传 body） |
| MCP tools/list 返回 Parse error | 检查 JSON body 是否被转义污染；用 python urllib 构造请求最稳 |
| Excel 打开报"部分内容有问题，是否恢复" | 单元格文本超 32767 字符（如 web_search_content 原始内容 7 万+字）；写入前截断 32000 + 清洗 XML 非法字符 |
| response 为空的行 | direct_output 业务工具回复，去 `tool_calls[].payload.formatted_text/message` 找 |
| answer_state"完全命中回答来源"但模块为空 | 遥测默认值，该轮非知识库回答，不可信 |
| 图片二进制找不回（8/23 后） | 网关内存缓存 600s + VLM 描述不落盘；只能拿到 `[文件: xxx]` 文本引用；旧数据（7月）才有 base64 |
| by_code_base 系统 python3 缺 psycopg/sqlalchemy | 用 `/root/workspace/by56_wiki/.venv/bin/python`（含 psycopg3） |
| by_code_base 工作区代码与线上不一致 | `git -C /root/workspace/by56_wiki show origin/main:<path>` 看线上真实逻辑 |
| 详细版工具行太多 | 每工具一行，内容取 payload `formatted_text`（截断到合理长度） |

## 关键事实备忘
- 学习模型：`metadata.llm_model`（如 kimi-k2.5 / ark-code-latest）。
- BaiYun_Agent `.env` 关键项：`LLM_API_KEY`、`OPENAI_API_BASE=https://ark.cn-beijing.volces.com/api/plan/v3`、`LLM_MODEL=ark-code-latest`；VLM `doubao-seed-2-0-lite`（vision_summary）。
- by56_wiki `.env` 关键项：`EMBEDDING_API_KEY`（dashscope，`EMBEDDING_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1`）、`LLM_WIKI_API_KEY`（deepseek）、`KB_DATABASE_URL`（阿里云 RDS PostgreSQL knowledge_base，非 localhost）。
- knowledge_chat 返回首行 `conversation_id: N` 表示 by56_wiki 侧会话，追问需回传。
- 联网组件：QA/合规 Fast Model 总结 `doubao-seed-2-0-mini`（llm_wiki_fast_model）；合规联网搜索 endpoint `https://open.feedcoopapi.com/search_api/web_search`（豆包）；合规结论模型走 OpenRouter `deepseek/deepseek-v4-flash-0731`。
- 8/23 09:47:54 = 2026 新版上线时间点（图片存储行为分界线）。

---

## 已废弃内容（历史时期：2026-08-10 构建 ~ 2026-08-23 新版前，仅适用于旧数据）

以下结论在 2026-08-23 09:47:54 新版上线后**失效或仅限旧数据**，保留备查：

1. **"audit log 是唯一保留图片与工具调用的数据源"** —— 仅对 8/23 前的旧数据成立。旧数据 `user_input.image_urls` 含 `data:image/...;base64,...` 可提取嵌入 Excel；新版后恒为空，只剩 `[文件: xxx]` 文本引用。
2. **conversations.db 作为备选数据源** —— `conversation_message` 表 2026-07-28 后停更，无新数据；`wecom_medias` 表也只有 2026-06 的 16 条旧记录。两者均不可用于新数据排查。
3. **旧版图片导出流程**（extract_images 从 image_urls 提 base64 → 图片预览列、`--desc` 图片描述、qwen3.5-plus VL 读图）—— 仅适用 8/23 前数据。新版图片描述（VLM vision_summary）不落盘，无法事后获取；`scripts/export_excel.py` 的图片功能仅对旧 jsonl 有效。
4. **"图片是 base64 data URL" 坑位**（`header, b64 = url.split(',', 1)`）—— 仅旧数据。
5. **`rag_context` 含 conversation_id 判断知识库会话** —— 新版以 knowledge_events.jsonl 的 message_id/trace_id 关联为准，更可靠。
6. **by56_wiki `.env` 的 `KB_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/knowledge_base`** —— 已迁移阿里云 RDS（见 .env 实际值）。