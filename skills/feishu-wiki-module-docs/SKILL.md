---
name: feishu-wiki-module-docs
description: Build and maintain Feishu (Lark) wiki module documents. Use when the user asks to create a module doc or sub-document under a Feishu wiki parent, write headings/tables/Mermaid diagrams/images, update a parent summary or 修改记录, sync Gantt/bitable milestones and todos, or validate Mermaid syntax in Feishu docs. Covers wiki node creation, docx block APIs, "文本绘图" Mermaid blocks, table limits, image upload, bitable records and view sorting.
---

# Feishu Wiki Module Docs

Build one module per child doc under a Feishu wiki parent, then optionally sync a short summary, the 修改记录 row, and Gantt/bitable milestones into the parent.

## Prerequisites

- `FEISHU_APP=company` for the app that has wiki + docx permissions. The default app often returns `1770032 forBidden`.
- Auth helper: `C:/Users/Young/.agents/skills/feishu-common/index.js` (`fetchWithAuth`, `getToken`).
- Playwright + Chromium for screenshots and Mermaid validation. Default path used by the scripts: `D:/workspace/aaas-fork/node_modules/.pnpm/playwright@1.62.1/node_modules/playwright`.
- Read the parent doc and the reference style doc before writing.

## Workflow

1. **Gather facts.** Read the relevant PRs, plans, runbooks, E2E docs, and code. Distinguish merged / closed / test-env / production-NO-GO. Never treat a closed PR as merged.
2. **Create the child doc** under the parent wiki node:
   ```bash
   FEISHU_APP=company node scripts/feishu_doc_tools.cjs create-child \
     --parent <parent_wiki_node_token> --title "模块名（English）"
   ```
   Record `node_token`, `obj_token` (the docx document id), and `url`.
3. **Write content** with `scripts/feishu_doc_tools.cjs` and the recipes in `references/api-cookbook.md`.
   - Standard shape: 修改记录 table → 关联代码/文档 → 状态说明 → 当前状态 → 阅读提示 → numbered sections → 验证与证据 → 边界与后置项 → 结论.
   - Mix Mermaid, tables, bullets, and screenshots. Keep every table ≤9 rows at creation.
4. **Validate Mermaid**:
   ```bash
   FEISHU_APP=company node scripts/check_mermaid.cjs --doc <doc_token>
   ```
   Fix any failures; quote node labels containing parentheses.
5. **Verify the doc**: `raw`, `blocks`, table cell text, image tokens, Mermaid count, and no leaked `**` / backticks.
6. **Sync the parent** only when asked (or when the established workflow expects it):
   - Insert a summary section before an anchor heading.
   - Append a row to 修改记录 and fill it.
   - Add a completed Gantt record and, if needed, a pending production record; keep the view sorted.
   See `references/gantt-bitable.md`.

## Hard rules and pitfalls

- **Tables:** Feishu table creation fails above **9 rows** (`1770001`). Create ≤9 rows, then use `insert-table-row` and fill the last cells. Cells are auto-created; fill them by patching each cell's child text block.
- **Mermaid:** use block_type `40` add-on, not a code block:
  `component_type_id: "blk_631fefbbae02400430b8f9f4"`, record `{"data":"<mermaid>","theme":"default","view":"chart"}`.
  Parentheses inside labels break the parser: `A["openStore(dataDir, URL)"]`, not `A[openStore(dataDir, URL)]`.
- **Images:** 3 steps: create empty image block → upload media with `parent_node=<image_block_id>` + `extra.drive_route_token` → patch `replace_image`. Width/height cannot be patched; use natural size.
- **Rich text:** `**bold**`, `` `code` ``, `[text](url)` are fine. Bold containing code must be split into separate runs or the backticks leak. After writing, scan text blocks for literal `**` or backticks.
- **Wiki API:** `GET /wiki/v2/spaces/get_node?token=` works per node; listing all space nodes may fail with `131006`. List children with `parent_node_token` and `page_size≤50`.
- **Bitable/Gantt sort:** v1 has no sort endpoint. Use Base v3: `PUT /base/v3/bases/{app}/tables/{table}/views/{view}/sort` with `{sort_config:[{field:"开始日期",desc:false}]}`. `desc:false` = oldest first; `desc:true` = newest first.
- **Dates:** Bitable DateTime fields take epoch ms. Use `Date.UTC(y,m,d)` or Beijing-midnight consistently; the formatter hides the time.
- **Batch limits:** create blocks in batches ≤20 (10 is safest); block list `page_size=500`; wiki nodes `page_size≤50`.
- **Deletion:** `batch_delete` uses root-child indexes, not block ids. Find the index immediately before deleting; insert-then-delete shifts it.
- **No secrets:** redact keys/tokens/DSNs; use `secret:...` references in examples.

## Standard module doc shape

Copy `references/module-doc-template.md`. The pattern that worked:

- 修改记录 table (date / content / maintainer / status).
- 关联代码/文档 + 状态说明 (merged vs closed vs test-env vs production).
- 当前状态 (6–8 bullets) and 阅读提示 (4 bullets).
- Numbered sections: architecture / evolution / mechanisms / verification / boundaries.
- 3–5 Mermaid diagrams, 5–10 tables, 3–6 screenshots.
- 结论 that separates “code/test-env done” from “production not released”.

## Scripts

- `scripts/feishu_doc_tools.cjs` — wiki/docx/bitable CLI.
  - `resolve`, `children`, `create-child`, `raw`, `blocks`, `append`, `table`, `mermaid`, `image`, `insert-table-row`, `delete-block`, `bitable-info`, `bitable-records`, `bitable-add`, `bitable-sort`.
  - `append` accepts a JSON array of raw Feishu block objects.
  - `table` accepts `{ "rows": [[...]], "widths": [...], "index": 0 }`.
- `scripts/check_mermaid.cjs` — reads all block_type 40 diagrams and runs Mermaid 11 `parse` + `render`; exits 1 on failures.

## References

- `references/api-cookbook.md` — exact API payloads, block structures, image/table/Mermaid recipes, verification queries.
- `references/gantt-bitable.md` — bitable block discovery, fields, records, Gantt sort, parent-sync checklist.
- `references/module-doc-template.md` — reusable document skeleton and style checklist.

## Verification checklist

- [ ] Child doc is under the intended parent node.
- [ ] `修改记录` has the new row; maintainer/date correct.
- [ ] Mermaid check reports 0 failures.
- [ ] No literal `**` or backticks in text blocks.
- [ ] Table row/column counts and cell contents match.
- [ ] All image blocks have non-empty tokens.
- [ ] Parent summary, 修改记录, and Gantt records agree on status/date.
- [ ] Gantt view sort matches the requested direction (newest-first or oldest-first).
