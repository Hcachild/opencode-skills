---
name: by56-wiki-embedding-reindex
description: >-
  更新 by56_wiki（BaiYun 运小星知识库）PostgreSQL/pgvector 向量库与检索索引。用于 Embedding 模型调整（换模型/换维度/服务端模型变更）后的全量向量重算、BM25 索引重建、HNSW 索引重建与验证。方法指导而非死板流程：跑向量重算时优先并发批量，动手前先探测目标 Embedding 模型是否支持批量接口（如需可联网查官方文档），若模型本身不支持批量必须向用户说明。Use when: 用户说"更新 by56_wiki 的向量库"、"Embedding Model 调整了需要重新跑索引"、"重算 embedding"、"重建向量索引"、"backfill 向量"、"换 embedding 模型"。
---

# by56_wiki Embedding 向量库更新

知识库 dense 检索链路（模型调整时全部要覆盖）：
1. PostgreSQL pgvector 向量列（RDS，5 张 chunk 表，当前 `vector(2048)`）
2. FAQ BM25（`data/indices/faq_bm25.pkl`）
3. chunk BM25（`data/indices/chunk_bm25.pkl`）
4. HNSW 向量索引（5 张表的 `ix_<table>_embedding_hnsw`）

## 环境速查

- 主机：`ssh by_dev`（root@120.79.167.211，测试环境）；生产为 by_code_base（路径同名 `/root/workspace/by56_wiki`，RDS 不同）
- 项目：`/root/workspace/by56_wiki`，服务 `pm2 by56-wiki-test`（port 10096，uvicorn），venv `.venv/bin/python`
- DB：阿里云 RDS（测试 `pgm-wz9j75t19vqr2108.pg.rds.aliyuncs.com/knowledge_base`），连接串在 `.env` 的 `KB_DATABASE_URL`（psycopg 格式，注意去掉 `+psycopg` 才能给 pg_dump/psql 用）
- 5 张向量表：`knowledge_chunks`、`hscode_chunks`、`trade_restriction_goods_chunks`、`transport_channel_product_chunks`、`product_certification_requirement_chunks`
- `document_parent_child_chunks` 已被用户判定为冗余并 DROP（2026-08-06），**不要重建、不要重算**

## 工作流

1. **预检（只读，先理解再动手）**：
   - `git status`、当前分支、`pm2 list` 服务状态
   - `.env` 向量段：`EMBEDDING_MODEL / KB_EMBEDDING_BACKEND / EMBEDDING_PROVIDER / EMBEDDING_API_KEY / EMBEDDING_API_BASE / EMBEDDING_DIM / EMBEDDING_MAX_CONCURRENCY`
   - DB 现状：`alembic_version`、各表 `embedding` 列类型（`vector(n)`）、`count(embedding)`、`embedding_model` 分布、HNSW 索引是否存在
   - 向量文本字段规则（入库侧一致）：knowledge_chunks 用 `question or title or search_text or content`；hscode/trade/cert 用 `product_name_simplified or product_name`；transport 用 `channel_name_simplified or channel_name or search_text or content`

2. **备份（必须，可回滚）**：目标 `/root/backups/by56_wiki/by56_wiki_pre_embedding_reindex_<日期>/`
   - `cp -a data/indices/*.pkl`（先停服务或接受极小窗口；pkl 是 tmp+rename 写入，cp 一般安全）
   - `pg_dump "$URL" -Fc -f <备份目录>/knowledge_base_pre_reindex.dump`（全库，含旧向量）
   - 改 `.env` 前先 `cp -a .env .env.bak.<标记>_<时间戳>`
   - 切分支前备份工作区痕迹（`git diff > app_main.py.diff`、untracked 脚本 cp 走），再 `git checkout --` 还原跟踪文件

3. **切代码/配置**（模型切换通常伴随开发组分支）：
   - 分支不在服务器时先 `git fetch origin`，再 `git checkout feature/xxx`
   - 迁移链不连续或 DB `alembic_version` 落后时，先核对迁移文件的 `down_revision` 链与幂等性（`IF NOT EXISTS`/`has_table`）
   - 更新 `.env` 向量段（新模型/新 base/新 key），保留旧 `.env` 备份

4. **探测模型能力（关键，动手前必做）**：
   - 先 curl 一次真实请求验证 key/端点/维度可用
   - **探测是否支持批量**：一次请求 `input` 放 N 条文本，看返回是 N 条向量还是 1 条；拿不准时联网查该 Embedding 模型官方 API 文档
   - 若模型不支持批量（如火山方舟 multimodal embedding：input 数组是"多模态组合"而非"批量列表"，一次请求只产出一条向量），**必须向用户说明**，用并发单条方式跑
   - 若支持批量（如阿里云 tongyi-embedding-vision 支持一次 20 条），优先批量 + 适当并发

5. **迁移/改列**（换维度时）：参考迁移文件写法：
   ```sql
   DROP INDEX IF EXISTS ix_<table>_embedding_hnsw;
   UPDATE <table> SET embedding = NULL;
   ALTER TABLE <table> ALTER COLUMN embedding TYPE vector(2048) USING NULL;
   UPDATE <table> SET embedding_json = '[]'::json, embedding_dim = 2048, embedding_model = NULL;
   ```
   或直接 `alembic upgrade head`（若有现成迁移）。**改列前必须停服**（旧代码+旧维度查询会报错）。

6. **全量重算（并发批量，幂等）**：用模板脚本 `scripts/reembed_all_2048.py`（见本 skill 目录）：
   - 上传到服务器 `/root/scripts/by56_wiki/`（不入 git），`nohup` 后台跑，日志到 `/root/scripts/by56_wiki/logs/`
   - 幂等：只处理 `embedding IS NULL` 的行（迁移清空后全 NULL），中断/失败可随时重跑
   - 用法：`python reembed_all_2048.py <table> <concurrency>`，不传表名跑全部
   - 每个表一个独立进程 + 独立日志，互不阻塞
   - **并发经验（火山方舟 doubao-embedding-vision，实测 2026-08）**：429 限流是硬约束，8-16 并发最优（~5-6/s 零失败）；32 反而降速；256 会打满服务器 CPU 且 ~45% 失败（还要补跑，总时长更差）。每进程并发从 8-16 起步，观察日志失败率，429 用退避重试（3/6/9/12/15s × 6 次）
   - 跑完检查失败行（日志 `/root/scripts/by56_wiki/reembed_errors_<table>.log`），用低并发（8）补跑，目标 `count(embedding)=count(*)` 且 `vector_dims(embedding)=2048`

7. **重建 BM25 + HNSW**：
   ```bash
   .venv/bin/python scripts/rebuild_bm25_index.py reset-and-rebuild   # faq_bm25.pkl
   # chunk BM25（python）：chunking_service.rebuild_chunk_keyword_index(db)
   # HNSW：CREATE INDEX ... USING hnsw (embedding vector_cosine_ops) WHERE embedding IS NOT NULL AND is_current = true
   ```

8. **启动 + 验证（端到端）**：
   - `pm2 start by56-wiki-test --update-env`（--update-env 让新 .env 生效），healthz ok
   - 检索冒烟：`embed_query_text(query, target_dim=2048)` 后跑一条 `embedding <=> :vec::vector` 的 HNSW 查询，确认语义命中正常
   - 看 pm2 日志无 dimension/embedding 报错

## 常见坑

- **PowerShell 引号吞变量**：`ssh by_dev "cmd \$var"` 的 `\$` 会被本地 PowerShell 解析（`$(...)` 会本地执行、`\$!` 丢失）→ 复杂逻辑一律写成 `.sh`/`.py` 文件，`Get-Content -Raw | ssh by_dev "bash -s"` 执行；远程写文件用 `cat >` 管道。
- **pkill 自杀**：ssh 命令行里 `pkill -f 'reembed_all_2048.py hscode'` 会匹配并杀掉包含该字符串的 ssh 自身 bash → 用脚本文件方式（`bash -s`，命令行不含 pattern）。
- **方舟 endpoint**：Agent/Coding Plan 的 key 用 `https://ark.cn-beijing.volces.com/api/plan/v3`（`/api/v3` 实测 401）。`.env.example` 里写 `/api/v3` 是坑，以实测为准。
- **改维度后旧代码必挂**：列改 2048 后，旧代码/旧模型（1536）的 dense 查询维度不匹配直接报错；服务侧必须同步切换支持新模型的代码（provider），否则"白停"。
- **`.env` 里写中文注释有编码风险**：脚本写 .env 时用 utf-8 显式读写。
- **删除冗余表**：用户 2026-08-06 指示 `document_parent_child_chunks` 为冗余已 DROP；检索代码均有 try/except 容错，表不存在不影响服务启动。
- **备份永远先行**：改列/清空/重算是破坏性操作，无 dump 不动手。

## 参考
- `scripts/reembed_all_2048.py`：通用幂等并发重算模板（按表跑、并发可调、429 退避、失败日志）
- 本 skill 目录下可扩展 `references/`（环境/模型/端点速查）
