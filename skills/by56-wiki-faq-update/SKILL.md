---
name: by56-wiki-faq-update
description: >-
  更新 by56_wiki 知识库（BaiYun 运小星知识库）中的 FAQ/文档行级数据，如仓库地址、电话、收费标准等业务信息变更。通过 SSH 在 by_dev（测试）或 by_code_base（生产）上运行通用脚本 scripts/update_faq_rows.py，完成定位、DB 更新（faq_items/knowledge_chunks/documents.parsed_preview_json）、embedding 重新生成、FAQ BM25 + chunk BM25 索引重建、源 Excel 同步（自动备份）、检索与在线 MCP 验证，最后清理服务器 git 痕迹并将变更文档下载到本机。Use when: 用户说"更新知识库里的 XX 信息"、"地址/电话/收费变了需要改"、"by_dev/by_code_base 上 by56_wiki 数据要更新"，或提供业务原话要求同步到知识库。
---

# by56_wiki FAQ 数据更新

知识库检索链路（必须全部覆盖，否则部分入口仍返回旧数据）：
1. `knowledge_chunks` 的 `embedding`（pgvector 向量召回，MCP search->hit 的主要来源）
2. `faq_items` → FAQ BM25（`data/indices/faq_bm25.pkl`）
3. `knowledge_chunks` → chunk BM25（`data/indices/chunk_bm25.pkl`，覆盖 qa + wiki_section chunk）
4. `documents.parsed_preview_json`（后台预览，重发布时的一致性来源）
5. 源 Excel（`data/uploads/...` 与 `data/wecom/...`，git 处理见下）

## 工作流

1. **确认目标环境**：用户指定或默认询问 by_dev（测试）/ by_code_base（生产）。两环境 RDS 不同、代码版本略有差异，详见 references/environments.md。
2. **定位受影响数据**：先扫描 DB 找出所有命中旧内容的 current chunk（旧地址/旧电话等可能有十几条 FAQ + wiki 表格，不能只看用户贴的那一条）：
   ```bash
   ssh by_dev "cd /root/workspace/by56_wiki && .venv/bin/python - <<'PYEOF'
   ...查询 knowledge_chunks / faq_items / documents 按旧文本 like 匹配...
   PYEOF"
   ```
   或直接跑脚本 `--match` 看 dry-run 定位结果。
3. **准备新文本**：把业务原话整理成正式答案（模式 A 整段替换）或新旧子串对（模式 B 局部替换，如只改地址片段）。新答案文件写到服务器 /tmp。
4. **跑通用脚本**（默认 dry-run，确认定位无误后 `--apply`）：
   ```bash
   scp scripts/update_faq_rows.py by_dev:/tmp/
   ssh by_dev "cd /root/workspace/by56_wiki && .venv/bin/python /tmp/update_faq_rows.py \
     --match '182-190' \
     --new-answer-file /tmp/new_answer.txt \
     --excel 'data/uploads/20260622161319_c35136521ffb486b9635ca692f889afe.xlsx' \
     --excel 'data/wecom/单证知识库文档（已分类）-仓库.xlsx' \
     --verify-query '海雄仓收货信息' \
     --apply"
   ```
   - 组合模式：`--replace '旧=>新'`（可多次）可只做子串替换；与 `--new-answer-file` 可并用（整段换答案 + 局部换 wiki 表格）。
   - 维度自动取目标 chunk 现有 `embedding_dim`（测试 2048 / 生产 1536），无需手工指定。
   - 脚本会：更新 faq_items.answer、chunk answer/content/search_text、preview_json、重嵌入、重建两个 BM25、同步 Excel（自动 `.bak.YYYYMMDD`）、打印验证。
5. **在线 MCP 验证**（端到端，服务在 10096 端口）：
   - 测试环境参数 `user_question`；生产环境参数 `message`（旧版 contract）。返回结构也不同，见 references/environments.md。
   - 用 python urllib 写请求文件执行，不要在 PowerShell 里拼 curl 转义（引号会被吞）。
6. **git 清理 + 本地存档**（用户要求服务器不留 git 痕迹时）：
   - 还原被 git 跟踪的 Excel：`git checkout -- 'data/wecom/xxx.xlsx'`，删除 `*.bak.*`。
   - `data/uploads/` 在 `.gitignore` 中（`git check-ignore` 确认），无需还原、不产生痕迹。
   - 只还原本次改动的文件，不动服务器上 pre-existing 的 git 改动（如 app/main.py 等）。
   - 把更新后的 Excel scp 到本机 `D:\workspace\by56_wiki\data\wecom\` 和 `data\uploads\`。

## 常见坑

- **PowerShell 引号**：`ssh host "python -c '...'"` 引号被吞报语法错误 → 脚本先 scp 到 /tmp 再执行；heredoc 传复杂 JSON 同样不可靠，用 python 文件方式构造。
- **脚本 dry-run 零写入**：update_faq_rows.py 内置"计划-执行"模式，未加 `--apply` 不修改任何数据（DB/Excel 均不写）。验证 dry-run 可用：跑完查 `faq_items.answer='TEST'` 应为 0。**切勿用 TEST 等占位文本做非 dry-run 测试**，一旦写入需从生产库导出正确答案回滚（见下）。
- **preview JSON 写库**：`documents.parsed_preview_json` 是 JSON 列，in-place 修改 dict 不触发 SQLAlchemy dirty 跟踪 → 必须 `flag_modified(doc, "parsed_preview_json")` 强制写库，否则后台预览仍是旧数据，重发布时旧内容会回灌。
- **数据库在 RDS**：by_dev 连 `pgm-wz9j75t19vqr2108...`（测试），by_code_base 连 `pgm-wz91ayr9l1m1fld8...`（生产），是两个库，需分别更新。
- **不要硬编码 chunk/faq ID**：两环境 ID 相同但不可依赖，用内容模式匹配。
- **费条目不要误改**：含"海雄仓库"字样的收费条目（如"板数判定归海雄仓库最终解释"）没有地址，只改地址时不要碰。模式 A 已内置保护：仅替换 answer 命中 `--match` 文本的条目，但 `--match` 过宽（如"海雄"）仍会命中收费条目，dry-run 输出里务必核对 PLAN 列表。
- **嵌入失败会抛错不落库**：`embed_persistent_texts` 生产模式不允许本地 hash 回退，失败即中止，安全。
- **污染回滚**：若误写，从另一环境（权威库）导出正确 answer：`select id, answer from faq_items where id = any(...)` dump JSON，再按 faq_item_id 回写 faq_items.answer 与 chunks.answer（content/search_text 若未动则无需修），重建两个 BM25。

## 参考
- environments.md：主机/端口/DB/embedding/MCP 契约/git 规范速查。
