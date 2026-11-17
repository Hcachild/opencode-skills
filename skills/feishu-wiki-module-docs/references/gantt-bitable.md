# Bitable / Gantt Sync

The parent doc often embeds a bitable (block_type 18) as a Gantt. Use it for milestones and todos.

## 1. Find the bitable

`GET /docx/v1/documents/{doc}/blocks?page_size=500` → find `block_type: 18`.

```json
{
  "block_type": 18,
  "bitable": { "token": "<app_token>_<table_id>" }
}
```

Split at `_tbl`:

```js
const at = token.indexOf('_tbl');
const app = token.slice(0, at);
const table = token.slice(at + 1);
```

The CLI does this for you:

```bash
FEISHU_APP=company node scripts/feishu_doc_tools.cjs bitable-info --doc <parent_doc>
```

It prints `app`, `table`, `fields`, and `views`.

## 2. Fields and records

List fields:

```http
GET /bitable/v1/apps/{app}/tables/{table}/fields?page_size=100
```

List records (optionally a view):

```http
GET /bitable/v1/apps/{app}/tables/{table}/records?page_size=100&view_id={view}
```

Add a record:

```http
POST /bitable/v1/apps/{app}/tables/{table}/records
Content-Type: application/json

{
  "fields": {
    "任务名": "09-21 测试环境验收与交付",
    "任务状态": "已完成",
    "备注": "PR #14 ...",
    "开始日期": 1790092800000,
    "截止日期": 1790092800000
  }
}
```

Single-select accepts the option name (`未开始` / `进行中` / `已完成`).

## 3. Dates

DateTime fields take epoch milliseconds. The date formatter is typically `yyyy/MM/dd`, so timezone differences are hidden.

- `Date.UTC(2026, 8, 21)` → 2026-09-21 00:00 UTC.
- Existing rows may use Beijing midnight (`Date.UTC(...) - 8h`); either is fine for date-only display, but keep new rows consistent within a batch.
- `Date.UTC(2026, 7, 18)` → 2026-08-18.

## 4. Gantt view and sort

List views:

```http
GET /bitable/v1/apps/{app}/tables/{table}/views?page_size=20
```

Find the view named `甘特图` (type `gantt`). The timebar fields can be inspected with Base v3:

```http
GET /base/v3/bases/{app}/tables/{table}/views/{view}
```

Response includes `_meta.sort` and `_meta.timebar`.

Set sort (v3 only; v1 has no sort endpoint):

```http
PUT /base/v3/bases/{app}/tables/{table}/views/{view}/sort
Content-Type: application/json

{ "sort_config": [ { "field": "开始日期", "desc": false } ] }
```

- `desc: false` → ascending, oldest at top (past → current).
- `desc: true` → descending, newest at top.
- `PATCH`/`POST` on this route returns 404; use `PUT`.
- Verify:

```http
GET /base/v3/bases/{app}/tables/{table}/views/{view}/sort
GET /base/v3/bases/{app}/tables/{table}/views/{view}   # _meta.sort
```

The CLI:

```bash
FEISHU_APP=company node scripts/feishu_doc_tools.cjs bitable-sort \
  --doc <parent_doc> --view <view_id> --field 开始日期 --desc false
```

Record order follows the view sort when listing with `view_id`; the Gantt timeline uses the date fields, not the record order.

## 5. Parent sync checklist

For each new module doc, if the workflow expects parent sync:

1. Insert a short section before a stable anchor heading:
   - heading2 with module name and date range.
   - one-sentence conclusion.
   - a 3-column table: `PR | 内容 | 结果` (≤9 rows).
   - 3–4 bullets: key mechanism, test evidence, boundary.
   - link to the child doc.
2. Append a row to the parent's 修改记录 table:
   - date, “补充「<module>」模块摘要与子文档入口；同步甘特图里程碑与待办”, maintainer.
3. Add a completed Gantt record:
   - task name with date range and module.
   - status `已完成`.
   - note with PR numbers, key evidence, boundaries, child doc name.
   - start/end dates.
4. Add a pending record if production work remains:
   - task name `待办 <module>生产化（...）`.
   - status `未开始`.
   - note with concrete gaps.
   - start date = today.
5. Set the Gantt sort direction requested by the user and verify the top/bottom records.

## 6. Pitfalls

- **v1 sort 404:** use `/base/v3/bases/.../views/.../sort` with `PUT`.
- **`desc` direction:** `false` is ascending (oldest first), not “default but maybe descending”.
- **Record append order:** new records go to the end of the record array; without a view sort they will not be chronological.
- **Date timezone:** mixing UTC and Beijing midnight can make a same-day task appear on the previous day in ISO output; display usually still matches. Pick one convention.
- **Parent section placement:** insert before the intended heading; after insertion the anchor index shifts by the number of inserted blocks.
- **修改记录 table:** `insert_table_row` adds an empty row; fill the last 3 cell text blocks.
- **Do not add a Gantt row without a matching doc section** unless the user explicitly wants a tasks-only record.
