#!/usr/bin/env node
/**
 * Feishu wiki/doc toolbox for module docs.
 *
 * Usage:
 *   node feishu_doc_tools.cjs <command> [--key value]
 *
 * Commands:
 *   resolve --token <wiki_token>
 *   children --parent <wiki_node_token>
 *   create-child --parent <wiki_node_token> --title <title>
 *   raw --doc <doc_token>
 *   blocks --doc <doc_token>
 *   append --doc <doc_token> --file <blocks.json> [--index N]
 *   table --doc <doc_token> --file <table.json>
 *   mermaid --doc <doc_token> --file <diagram.mmd> [--index N]
 *   image --doc <doc_token> --file <image.png> [--index N]
 *   insert-table-row --doc <doc_token> --block <table_block_id> [--values <json>]
 *   delete-block --doc <doc_token> --block <block_id>
 *   bitable-info --doc <doc_token>
 *   bitable-records --doc <doc_token> [--view <view_id>]
 *   bitable-add --doc <doc_token> --file <record.json>
 *   bitable-sort --doc <doc_token> --view <view_id> --field <field_name> --desc true|false
 *
 * Env:
 *   FEISHU_APP=company   (required for the wiki/docx permissions)
 */

const fs = require('fs');
const path = require('path');
const { fetchWithAuth } = require(path.resolve(__dirname, '../../feishu-common/index.js'));

process.env.FEISHU_APP = process.env.FEISHU_APP || 'company';
const BASE = 'https://open.feishu.cn/open-apis';

function parseArgs(argv) {
  const opts = {};
  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (!arg.startsWith('--')) continue;
    const key = arg.slice(2);
    const next = argv[i + 1];
    if (next !== undefined && !next.startsWith('--')) {
      opts[key] = next;
      i++;
    } else {
      opts[key] = true;
    }
  }
  return opts;
}

async function api(pathname, init = {}) {
  const res = await fetchWithAuth(`${BASE}${pathname}`, init);
  const data = await res.json();
  if (data.code !== 0) throw new Error(`${pathname}: ${JSON.stringify(data)}`);
  return data.data;
}

async function getNode(token) {
  const data = await api(`/wiki/v2/spaces/get_node?token=${encodeURIComponent(token)}`);
  return data.node;
}

async function resolveDoc(token) {
  const clean = String(token).match(/\/(?:docx|wiki|doc)\/([a-zA-Z0-9]+)/)?.[1] || token;
  try {
    const node = await getNode(clean);
    if (node.obj_type === 'docx' || node.obj_type === 'doc') {
      return { doc: node.obj_token, node };
    }
  } catch {
    /* not a wiki token */
  }
  return { doc: clean, node: undefined };
}

async function listChildren(doc, parent = doc) {
  const out = [];
  let pageToken = '';
  do {
    const data = await api(
      `/docx/v1/documents/${doc}/blocks/${parent}/children?page_size=100${pageToken ? `&page_token=${encodeURIComponent(pageToken)}` : ''}`,
    );
    out.push(...(data.items || []));
    pageToken = data.has_more ? data.page_token : '';
  } while (pageToken);
  return out;
}

async function listBlocks(doc) {
  const out = [];
  let pageToken = '';
  do {
    const data = await api(
      `/docx/v1/documents/${doc}/blocks?page_size=500${pageToken ? `&page_token=${encodeURIComponent(pageToken)}` : ''}`,
    );
    out.push(...(data.items || []));
    pageToken = data.has_more ? data.page_token : '';
  } while (pageToken);
  return out;
}

function textRun(content, style = {}) {
  return { text_run: { content, text_element_style: { ...style } } };
}

/**
 * Parse simple inline markdown: **bold**, `code`, [text](url).
 * Bold containing code is split into bold text and bold+inline-code runs,
 * which avoids literal backticks in the final block.
 */
function rich(text) {
  const out = [];
  const re = /(\[[^\]]+\]\([^)]+\)|\*\*[\s\S]+?\*\*|`[^`]+`)/g;
  let last = 0;
  let match;
  while ((match = re.exec(String(text))) !== null) {
    if (match.index > last) out.push(textRun(String(text).slice(last, match.index)));
    const token = match[0];
    if (token.startsWith('**')) {
      const inner = token.slice(2, -2);
      const parts = inner.split(/(`[^`]+`)/g);
      for (const part of parts) {
        if (!part) continue;
        if (part.startsWith('`') && part.endsWith('`')) {
          out.push(textRun(part.slice(1, -1), { bold: true, inline_code: true }));
        } else {
          out.push(textRun(part, { bold: true }));
        }
      }
    } else if (token.startsWith('`')) {
      out.push(textRun(token.slice(1, -1), { inline_code: true }));
    } else {
      const link = token.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
      out.push(textRun(link[1], { link: { url: encodeURI(link[2]) } }));
    }
    last = match.index + token.length;
  }
  if (last < String(text).length) out.push(textRun(String(text).slice(last)));
  return out.length ? out : [textRun(String(text))];
}

function heading(level, value) {
  const prop = { 1: 'heading1', 2: 'heading2', 3: 'heading3', 4: 'heading4' }[level];
  return { block_type: level + 2, [prop]: { elements: rich(value) } };
}
const text = (value) => ({ block_type: 2, text: { elements: rich(value) } });
const bullet = (value) => ({ block_type: 12, bullet: { elements: rich(value) } });
const ordered = (value) => ({ block_type: 13, ordered: { elements: rich(value) } });
const quote = (value) => ({ block_type: 15, quote: { elements: rich(value) } });
const divider = () => ({ block_type: 22, divider: {} });
const code = (value, language = 1) => ({ block_type: 14, code: { elements: [textRun(value)], language } });

function mermaidBlock(source) {
  return {
    block_type: 40,
    add_ons: {
      component_id: '',
      component_type_id: 'blk_631fefbbae02400430b8f9f4',
      record: JSON.stringify({ data: source, theme: 'default', view: 'chart' }),
    },
  };
}

async function insertBlocks(doc, blocks, index) {
  const created = [];
  const batchSize = 10;
  for (let i = 0; i < blocks.length; i += batchSize) {
    const chunk = blocks.slice(i, i + batchSize);
    const body = { children: chunk };
    if (index !== undefined) body.index = Number(index) + i;
    const data = await api(`/docx/v1/documents/${doc}/blocks/${doc}/children`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    created.push(...(data.children || []));
  }
  return created;
}

async function patchBlock(doc, blockId, payload) {
  return api(`/docx/v1/documents/${doc}/blocks/${blockId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

async function createTable(doc, rows, widths, index) {
  if (!Array.isArray(rows) || rows.length === 0) throw new Error('rows must be a non-empty array');
  if (rows.some((r) => !Array.isArray(r) || r.length !== rows[0].length)) {
    throw new Error('all rows must have the same number of columns');
  }
  if (rows.length > 9) throw new Error('Feishu table creation supports at most 9 rows; split or use insert-table-row');
  const created = await insertBlocks(doc, [{
    block_type: 31,
    table: { property: { row_size: rows.length, column_size: rows[0].length, column_width: widths, header_row: true } },
  }], index);
  const tableId = created[0].block_id;
  const cells = await listChildren(doc, tableId);
  const cols = rows[0].length;
  for (let i = 0; i < cells.length; i++) {
    const inner = await listChildren(doc, cells[i].block_id);
    const tb = inner.find((b) => b.block_type === 2);
    const value = rows[Math.floor(i / cols)]?.[i % cols];
    if (!tb || value === undefined || value === null || value === '') continue;
    await patchBlock(doc, tb.block_id, { update_text_elements: { elements: rich(String(value)) } });
  }
  return tableId;
}

async function createImage(doc, filePath, index) {
  const created = await insertBlocks(doc, [{ block_type: 27, image: {} }], index);
  const imageBlockId = created[0].block_id;
  const buf = fs.readFileSync(filePath);
  const form = new FormData();
  form.append('file_name', path.basename(filePath));
  form.append('parent_type', 'docx_image');
  form.append('parent_node', imageBlockId);
  form.append('size', String(buf.length));
  form.append('extra', JSON.stringify({ drive_route_token: doc }));
  form.append('file', new Blob([buf], { type: 'image/png' }), path.basename(filePath));
  const res = await fetchWithAuth(`${BASE}/drive/v1/medias/upload_all`, { method: 'POST', body: form });
  const upload = await res.json();
  if (upload.code !== 0) throw new Error(`upload: ${JSON.stringify(upload)}`);
  await patchBlock(doc, imageBlockId, { replace_image: { token: upload.data.file_token } });
  return imageBlockId;
}

async function insertTableRow(doc, blockId, values) {
  await patchBlock(doc, blockId, { insert_table_row: { row_index: -1 } });
  if (!Array.isArray(values)) return;
  const cells = await listChildren(doc, blockId);
  const last = cells.slice(-values.length);
  for (let i = 0; i < last.length; i++) {
    const inner = await listChildren(doc, last[i].block_id);
    const tb = inner.find((b) => b.block_type === 2);
    if (tb && values[i] !== undefined) {
      await patchBlock(doc, tb.block_id, { update_text_elements: { elements: rich(String(values[i])) } });
    }
  }
}

async function deleteRootBlock(doc, blockId) {
  const children = await listChildren(doc, doc);
  const index = children.findIndex((b) => b.block_id === blockId);
  if (index < 0) throw new Error('block is not a root child');
  await api(`/docx/v1/documents/${doc}/blocks/${doc}/children/batch_delete`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start_index: index, end_index: index + 1 }),
  });
}

async function bitableInfo(doc) {
  const blocks = await listBlocks(doc);
  const block = blocks.find((b) => b.block_type === 18);
  if (!block) throw new Error('bitable block not found');
  const token = block.bitable.token;
  const at = token.indexOf('_tbl');
  if (at < 0) throw new Error(`unexpected bitable token: ${token}`);
  const app = token.slice(0, at);
  const table = token.slice(at + 1);
  const fields = await api(`/bitable/v1/apps/${app}/tables/${table}/fields?page_size=100`);
  const views = await api(`/bitable/v1/apps/${app}/tables/${table}/views?page_size=20`);
  return { app, table, fields: fields.items || [], views: views.items || [] };
}

async function main() {
  const command = process.argv[2];
  const opts = parseArgs(process.argv.slice(3));
  if (!command) throw new Error('missing command');

  if (command === 'resolve') {
    const node = await getNode(opts.token);
    console.log(JSON.stringify(node, null, 2));
    return;
  }

  if (command === 'children') {
    const node = await getNode(opts.parent);
    const data = await api(`/wiki/v2/spaces/${node.space_id}/nodes?page_size=50&parent_node_token=${encodeURIComponent(opts.parent)}`);
    console.log(JSON.stringify(data.items || [], null, 2));
    return;
  }

  if (command === 'create-child') {
    const node = await getNode(opts.parent);
    const data = await api(`/wiki/v2/spaces/${node.space_id}/nodes`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ obj_type: 'docx', node_type: 'origin', parent_node_token: opts.parent, title: opts.title }),
    });
    console.log(JSON.stringify(data.node, null, 2));
    return;
  }

  if (command === 'raw') {
    const { doc } = await resolveDoc(opts.doc);
    const data = await api(`/docx/v1/documents/${doc}/raw_content`);
    console.log(data.content);
    return;
  }

  if (command === 'blocks') {
    const { doc } = await resolveDoc(opts.doc);
    console.log(JSON.stringify(await listBlocks(doc), null, 2));
    return;
  }

  if (command === 'append') {
    const { doc } = await resolveDoc(opts.doc);
    const blocks = JSON.parse(fs.readFileSync(opts.file, 'utf8'));
    const created = await insertBlocks(doc, blocks, opts.index);
    console.log(JSON.stringify(created, null, 2));
    return;
  }

  if (command === 'table') {
    const { doc } = await resolveDoc(opts.doc);
    const input = JSON.parse(fs.readFileSync(opts.file, 'utf8'));
    const id = await createTable(doc, input.rows, input.widths, input.index ?? opts.index);
    console.log(JSON.stringify({ table_block_id: id }));
    return;
  }

  if (command === 'mermaid') {
    const { doc } = await resolveDoc(opts.doc);
    const source = fs.readFileSync(opts.file, 'utf8');
    const created = await insertBlocks(doc, [mermaidBlock(source)], opts.index);
    console.log(JSON.stringify(created, null, 2));
    return;
  }

  if (command === 'image') {
    const { doc } = await resolveDoc(opts.doc);
    const id = await createImage(doc, opts.file, opts.index);
    console.log(JSON.stringify({ image_block_id: id }));
    return;
  }

  if (command === 'insert-table-row') {
    const { doc } = await resolveDoc(opts.doc);
    const values = opts.values ? JSON.parse(opts.values) : undefined;
    await insertTableRow(doc, opts.block, values);
    console.log(JSON.stringify({ ok: true }));
    return;
  }

  if (command === 'delete-block') {
    const { doc } = await resolveDoc(opts.doc);
    await deleteRootBlock(doc, opts.block);
    console.log(JSON.stringify({ ok: true }));
    return;
  }

  if (command === 'bitable-info') {
    const { doc } = await resolveDoc(opts.doc);
    console.log(JSON.stringify(await bitableInfo(doc), null, 2));
    return;
  }

  if (command === 'bitable-records') {
    const { doc } = await resolveDoc(opts.doc);
    const info = await bitableInfo(doc);
    const view = opts.view ? `&view_id=${encodeURIComponent(opts.view)}` : '';
    const data = await api(`/bitable/v1/apps/${info.app}/tables/${info.table}/records?page_size=100${view}`);
    console.log(JSON.stringify(data, null, 2));
    return;
  }

  if (command === 'bitable-add') {
    const { doc } = await resolveDoc(opts.doc);
    const info = await bitableInfo(doc);
    const record = JSON.parse(fs.readFileSync(opts.file, 'utf8'));
    const data = await api(`/bitable/v1/apps/${info.app}/tables/${info.table}/records`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(record),
    });
    console.log(JSON.stringify(data, null, 2));
    return;
  }

  if (command === 'bitable-sort') {
    const { doc } = await resolveDoc(opts.doc);
    const info = await bitableInfo(doc);
    const body = { sort_config: [{ field: opts.field, desc: String(opts.desc) === 'true' }] };
    const data = await api(`/base/v3/bases/${info.app}/tables/${info.table}/views/${opts.view}/sort`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    console.log(JSON.stringify(data, null, 2));
    return;
  }

  throw new Error(`unknown command: ${command}`);
}

main().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: String(error?.message || error) }));
  process.exit(1);
});
