# Feishu Docx / Wiki API Cookbook

All calls use `Authorization: Bearer <tenant_access_token>` via `fetchWithAuth` from `feishu-common`. Set `FEISHU_APP=company` for the app with wiki + docx permissions.

Base: `https://open.feishu.cn/open-apis`.

## 1. Wiki nodes

Resolve a wiki token (also returns `space_id`, `parent_node_token`, `obj_token`):

```http
GET /wiki/v2/spaces/get_node?token=<wiki_node_token>
```

Create a child doc under a parent:

```http
POST /wiki/v2/spaces/{space_id}/nodes
Content-Type: application/json

{
  "obj_type": "docx",
  "node_type": "origin",
  "parent_node_token": "<parent_node_token>",
  "title": "模块名（English）"
}
```

Response: `node.node_token`, `node.obj_token` (document_id), `node.url`.

List children:

```http
GET /wiki/v2/spaces/{space_id}/nodes?page_size=50&parent_node_token=<parent_node_token>
```

`page_size` max is 50. Listing the whole space without a parent filter may return `131006 permission denied`; per-node `get_node` and parent-filtered lists usually work.

## 2. Docx blocks

The root block id equals the document id (`obj_token`). Create children:

```http
POST /docx/v1/documents/{doc}/blocks/{parent}/children
Content-Type: application/json

{ "children": [ <block>, ... ], "index": 0 }
```

`index` is optional. Batch ≤20 blocks (10 is safest).

Block type map:

| type | block | payload key |
|---|---|---|
| 2 | text | `text` |
| 3/4/5 | heading1/2/3 | `heading1` / `heading2` / `heading3` |
| 12 | bullet | `bullet` |
| 13 | ordered | `ordered` |
| 14 | code | `code` |
| 15 | quote | `quote` |
| 22 | divider | `divider` |
| 27 | image | `image` |
| 31 | table | `table` |
| 32 | table cell | `table_cell` |
| 40 | add_ons ("文本绘图") | `add_ons` |

Text block:

```json
{
  "block_type": 2,
  "text": {
    "elements": [
      { "text_run": { "content": "普通文本", "text_element_style": {} } },
      { "text_run": { "content": "粗体", "text_element_style": { "bold": true } } },
      { "text_run": { "content": "inline code", "text_element_style": { "inline_code": true } } },
      { "text_run": { "content": "链接", "text_element_style": { "link": { "url": "https://example.com" } } } }
    ]
  }
}
```

Heading/bullet/ordered/quote use the same `{ elements }` shape under their own key.

Read blocks:

```http
GET /docx/v1/documents/{doc}/blocks?page_size=500
GET /docx/v1/documents/{doc}/blocks/{parent}/children?page_size=100
GET /docx/v1/documents/{doc}/raw_content
```

`raw_content` is for a quick text read; it may render bold as `**...**`. For leak checks, inspect the actual text elements via the blocks API.

## 3. Tables

Create a table (≤9 rows per call):

```json
{
  "block_type": 31,
  "table": {
    "property": {
      "row_size": 4,
      "column_size": 3,
      "column_width": [70, 620, 220],
      "header_row": true
    }
  }
}
```

Feishu auto-creates a cell block (type 32) per cell, and each cell gets an empty text block. Fill a cell by patching its child text block:

```http
PATCH /docx/v1/documents/{doc}/blocks/{text_block_id}
Content-Type: application/json

{
  "update_text_elements": {
    "elements": [ { "text_run": { "content": "值", "text_element_style": {} } } ]
  }
}
```

Add a row:

```http
PATCH /docx/v1/documents/{doc}/blocks/{table_block_id}
Content-Type: application/json

{ "insert_table_row": { "row_index": -1 } }
```

Then list the table children and fill the last N cell text blocks. `row_index: -1` appends.

**Limit:** 10+ rows at creation returns `1770001 invalid param`. Create 9 or fewer, then append rows.

## 4. Mermaid ("文本绘图")

Use an add-on block, not a code block:

```json
{
  "block_type": 40,
  "add_ons": {
    "component_id": "",
    "component_type_id": "blk_631fefbbae02400430b8f9f4",
    "record": "{\"data\":\"flowchart LR\\n  A[Start] --> B[End]\",\"theme\":\"default\",\"view\":\"chart\"}"
  }
}
```

- `record` is a JSON string with `data` (Mermaid source), `theme: "default"`, `view: "chart"`.
- Feishu renders this as a native text drawing.
- Quote labels that contain parentheses: `A["openStore(dataDir, URL)"]`.
- Validate with `scripts/check_mermaid.cjs` (Mermaid 11 `parse` + `render`).

## 5. Images

Three steps, order matters:

1. Create an empty image block:

```json
{ "block_type": 27, "image": {} }
```

Response gives `block_id`.

2. Upload the image (`multipart/form-data`):

```http
POST /drive/v1/medias/upload_all
```

Fields:

| field | value |
|---|---|
| `file_name` | `shot.png` |
| `parent_type` | `docx_image` |
| `parent_node` | **the image block_id**, not the doc |
| `size` | byte size |
| `extra` | `{"drive_route_token":"<doc_token>"}` |
| `file` | binary |

3. Patch the block:

```http
PATCH /docx/v1/documents/{doc}/blocks/{image_block_id}
Content-Type: application/json

{ "replace_image": { "token": "<file_token>" } }
```

Image `width`/`height` are not patchable; the natural size is used.

## 6. Delete a block

Root-level delete uses indexes:

```http
DELETE /docx/v1/documents/{doc}/blocks/{doc}/children/batch_delete
Content-Type: application/json

{ "start_index": 25, "end_index": 26 }
```

`end_index` is exclusive. Find the index immediately before deleting. If you insert a replacement first, re-list children and locate the old block again.

## 7. Rich-text leaks

If bold contains inline code, do not emit `**...`...`...**` as one run. Split into separate runs:

```js
[
  { text_run: { content: "see ", style: {} } },
  { text_run: { content: "dev", style: { bold: true, inline_code: true } } },
  { text_run: { content: " branch", style: { bold: true } } }
]
```

After writing, fetch text blocks and scan for literal `**` or backticks.

## 8. Bitable / Gantt

See `references/gantt-bitable.md`.

## 9. Mermaid validation and screenshots

Validate:

```bash
FEISHU_APP=company node scripts/check_mermaid.cjs --doc <doc_token_or_wiki_token>
```

The script loads `mermaid.min.js` (UMD) from jsdelivr, falls back to unpkg, then runs `mermaid.parse` and `mermaid.render` on every block_type 40.

Screenshot evidence with Playwright:

```js
const { chromium } = require('D:/workspace/aaas-fork/node_modules/.pnpm/playwright@1.62.1/node_modules/playwright');
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.5 });
await page.goto(url, { waitUntil: 'networkidle' });
await page.screenshot({ path: 'shot.png' });
```

Gitea PR/file pages used in this workspace are public.

## 10. Common errors

| Error | Cause | Fix |
|---|---|---|
| `1770032 forBidden` | wrong Feishu app | `FEISHU_APP=company` |
| `1770001 invalid param` | table >9 rows, bad block payload, image token at create | create ≤9 rows; create image empty then replace |
| `131006 permission denied` | listing whole wiki space | use `get_node` + `parent_node_token` |
| Mermaid parse error at `(` | parentheses in node label | quote the label: `A["...(...)..."]` |
| Literal `**` / backticks in doc | bold + inline code in one run | split runs |
| Bitable sort 404 | used v1 sort route | use Base v3 `PUT .../views/{view}/sort` |
| `batch_delete` deletes wrong block | index shifted after insert | re-list and find the old block id again |
