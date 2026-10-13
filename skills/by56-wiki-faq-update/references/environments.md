# by56_wiki 环境速查

> 2026-10-13 核验：`by_production` 上已部署并运行 by56_wiki（原「无 by56_wiki」的说法已过时）；`by_code_base` 的服务未运行、仅保留代码目录。

## 服务器

| 环境 | SSH 主机 | 用途 | by56_wiki 服务 | MCP 端口 |
|---|---|---|---|---|
| 测试 | `by_dev` | 测试知识库 | 运行中（`.venv/bin/uvicorn ... --port 10096`） | 10096 |
| 生产（主用） | `by_production` | 正式知识库（含数据标注/审核平台） | 运行中（同上） | 10096 |
| 旧生产实例 | `by_code_base` | 代码目录保留（HEAD 较旧），服务未运行、10096 未监听 | — | — |

- 三台机器均有一份 `/root/workspace/by56_wiki`；`by_production` 检出较新（#253 已合入，HEAD c380e5d），`by_code_base` 停留旧提交（HEAD 0603a7c），改动前先 `git log` 对照。
- `by_production` 与 `by_code_base` 的 `.env` 均指向生产 RDS `pgm-wz91ayr9l1m1fld8...`（同库）；`by_dev` 指向测试 RDS `pgm-wz9j75t19vqr2108...`。
- `by_production` 上同时运行其他项目（SmartInquiry 9527、cs-invoice-parse 8080 等），勿误停。
- venv：`.venv/bin/python`（项目根目录下运行，`app.core.config` 自动加载 `.env`，勿手动重复加载）。
- 服务进程：`ps aux | grep uvicorn.*10096`。

## 数据标注 / 审核数据（生产库，只读）

- 审核记录在**生产库**的 `qa_review_items` / `qa_review_batches`：状态机 `pending → review → approved / modified（均展示「已通过」）/ rejected`；标注平台的「待审核 50 / 已通过 50」即这张表。
- 常用字段：`tool`（业务场景：product_compliance_check / knowledge_chat / product_hscode_search / transport_channel_check）、`change_type`（add/modify/disable）、`question / answer / original_answer`、`original_input_json / corrected_input_json`、`issue_type`（correct/incorrect/missing）、`resolution_action`、`comment`、`annotator / reviewer`。
- 只读导出：脚本 scp 到服务器 `/tmp` 后执行 `ssh by_production "cd /root/workspace/by56_wiki && .venv/bin/python /tmp/xxx.py"`。
- 坑：`original_input_json` 等为 `json` 类型，比较/去重要 `::text` 转型（`json` 不支持 `=` / `IS DISTINCT FROM`）。

## 数据库（RDS）

| 环境 | RDS 主机（脱敏） |
|---|---|
| by_dev（测试） | `pgm-wz9j75t19vqr2108.pg.rds.aliyuncs.com` |
| by_production / by_code_base（生产，同库） | `pgm-wz91ayr9l1m1fld8.pg.rds.aliyuncs.com` |

- URL 在 `.env` 的 `KB_DATABASE_URL`（`postgresql+psycopg://`），psycopg v3。
- 连库脚本模板（scp 到 /tmp 执行，避免 PowerShell 引号问题）：

```python
from app.core.database import get_engine
from sqlalchemy import text
eng = get_engine()
with eng.connect() as c:
    for r in c.execute(text("SELECT id, title, stored_path FROM documents WHERE title LIKE '%仓库%'")).fetchall():
        print(r)
```

## Embedding 差异（脚本自动按目标 chunk 维度适配）

| 环境 | 维度 | 模型 |
|---|---|---|
| by_dev（测试） | 2048 | doubao-embedding-vision-251215（multimodal 接口） |
| by_code_base（生产） | 1536 | text-embedding-v2 |

- 生产旧代码无 `app.core.embedding_dims` 模块；检索硬编码 `target_dim=1536`。
- 查询/存储同一空间：重嵌入必须用与现有 chunk 相同的 `embedding_dim`。

## MCP 在线验证

测试环境（新 contract）：

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"knowledge_chat","arguments":{"user_question":"海雄仓收货信息"}}}
```
返回 `answer.summary`（结构化 contract）。

生产环境（旧 contract）：

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"knowledge_chat","arguments":{"message":"海雄仓收货信息"}}}
```
返回 `content`（文本）+ `knowledge_event`（含 `source_answer_id` 即 chunk id、`score`、`coverage_reason`）。

执行方式（PowerShell 下勿直接 curl 拼转义）：

```python
# mcp_chat_test.py，scp 到服务器 /tmp 后运行
import json, urllib.request
payload = {"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"knowledge_chat","arguments":{"user_question":"海雄仓收货信息"}}}  # 生产用 message
req = urllib.request.Request("http://127.0.0.1:10096/mcp", data=json.dumps(payload).encode(),
    headers={"Content-Type":"application/json","Accept":"application/json, text/event-stream"})
print(urllib.request.urlopen(req, timeout=120).read().decode())
```

## 数据表关键列

- `knowledge_chunks`：`id / document_id / faq_item_id / chunk_type (qa|wiki_section|...) / question / answer / content / search_text / embedding (vector) / embedding_json / embedding_dim / embedding_model / metadata_json / is_current`
- `faq_items`：`id / document_id / row_no / question / answer / category / source_filename`
- `documents`：`id / title / source_filename / stored_path / parsed_preview_json / version / status`

chunk 生成规则（更新时要保持一致）：
- QA chunk：`content = "Question: {q}\nAnswer: {a}"`；嵌入文本 = `question`；`search_text = build_search_text(metadata, q, a, category, doc_title, source_filename)`（`app.services.retrieval.chunk_metadata`）。
- wiki chunk（chunk_type=wiki_section）：嵌入文本 = `search_text or content or title`；更新用子串替换 content + search_text。

## Git 规范（服务器）

- `data/uploads/` 被 `.gitignore` 忽略（`git check-ignore` 确认），改它不产生 git 痕迹。
- `data/wecom/*.xlsx` 被 git 跟踪：更新后需 `git checkout -- <file>` 还原 + 删除 `.bak.*`。
- 服务器常有 pre-existing 改动（如 `app/main.py`、`backups/`、`tmp_*.json`），**只还原本次改动的文件**，其余不动。
- 更新后的文档下载到本机：`scp by_dev:/root/workspace/by56_wiki/data/wecom/xxx.xlsx D:\workspace\by56_wiki\data\wecom\`。

## 验证残留

- 更新后扫描 `is_current AND content LIKE '%旧文本%'`，应为 0。
- 检索验证：`retrieve_qa_chunks_by_vector`、`bm25_store.search`、`chunk_bm25_store.search` 都应返回新文本。
- BM25 为 pickle 文件（`data/indices/faq_bm25.pkl`、`chunk_bm25.pkl`），按文件 mtime 缓存，重建后运行中服务自动读取新索引。
