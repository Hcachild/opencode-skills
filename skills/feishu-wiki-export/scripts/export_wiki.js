#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

const sleep = ms => new Promise(r => setTimeout(r, ms));

let BASE_URL = 'https://my.feishu.cn';
let authFetch = null;

const stats = { total: 0, ok: 0, failed: 0, warnings: 0 };
const failedList = [];

function usage() {
  console.log(`Feishu (Lark) wiki tree -> local Markdown exporter

Usage:
  node export_wiki.js --url <feishu-wiki-url> --out <dir>
  node export_wiki.js --token <node_token> --out <dir>
  node export_wiki.js --space <space_id> --out <dir>

Options:
  --url <url>      Feishu wiki URL, e.g. https://my.feishu.cn/wiki/XXXX
  --token <token>  Wiki node token (alternative to --url)
  --space <id>     Export every top-level node of a wiki space
  --out <dir>      Output directory (default: ./feishu-wiki-export)
  --help           Show this help

Credentials are resolved from:
  1. FEISHU_APP_ID / FEISHU_APP_SECRET environment variables
  2. config.json next to feishu-common (e.g. ~/.agents/skills/config.json)
  3. feishu-doc-*/config.json under ~/.agents/skills or ~/.config/opencode/skills
`);
}

function parseArgs(argv) {
  const args = { url: null, token: null, space: null, out: null, help: false };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--url') args.url = argv[++i];
    else if (a === '--token') args.token = argv[++i];
    else if (a === '--space') args.space = argv[++i];
    else if (a === '--out') args.out = argv[++i];
    else if (a === '--help' || a === '-h') args.help = true;
    else {
      console.error('Unknown argument: ' + a);
      process.exit(2);
    }
  }
  return args;
}

function extractToken(url) {
  const clean = String(url || '').split('?')[0];
  const m = clean.match(/\/(?:wiki|docx|docs|sheets|base)\/([A-Za-z0-9]+)/);
  return m ? m[1] : null;
}

function findFeishuCommon() {
  const candidates = [
    path.join(__dirname, '..', '..', 'feishu-common', 'index.js'),
    path.join(os.homedir(), '.agents', 'skills', 'feishu-common', 'index.js'),
    path.join(os.homedir(), '.config', 'opencode', 'skills', 'feishu-common', 'index.js'),
  ];
  for (const c of candidates) {
    if (fs.existsSync(c)) return c;
  }
  throw new Error('feishu-common not found. Install the feishu-common skill, or set FEISHU_APP_ID / FEISHU_APP_SECRET.');
}

function loadCredentials(commonPath) {
  if (process.env.FEISHU_APP_ID && process.env.FEISHU_APP_SECRET) return;
  const readDirSafe = d => { try { return fs.readdirSync(d); } catch (e) { return []; } };
  const skillRoots = [
    path.join(os.homedir(), '.agents', 'skills'),
    path.join(os.homedir(), '.config', 'opencode', 'skills'),
  ];
  const candidates = [
    path.join(path.dirname(commonPath), '..', 'config.json'),
    path.join(path.dirname(commonPath), 'config.json'),
  ];
  for (const root of skillRoots) {
    candidates.push(path.join(root, 'config.json'));
    for (const name of readDirSafe(root)) {
      if (name.startsWith('feishu-doc')) candidates.push(path.join(root, name, 'config.json'));
    }
  }
  for (const c of candidates) {
    try {
      const cfg = JSON.parse(fs.readFileSync(c, 'utf8'));
      if (cfg.app_id && cfg.app_secret) {
        process.env.FEISHU_APP_ID = cfg.app_id;
        process.env.FEISHU_APP_SECRET = cfg.app_secret;
        return;
      }
    } catch (e) {}
  }
  throw new Error('Feishu credentials not found. Set FEISHU_APP_ID / FEISHU_APP_SECRET or create config.json (e.g. ~/.agents/skills/config.json with app_id/app_secret).');
}

async function api(url, opts = {}, retries = 5) {
  let lastErr;
  for (let i = 0; i < retries; i++) {
    try {
      const res = await authFetch(url, { headers: { 'Content-Type': 'application/json' }, ...opts });
      const data = await res.json();
      if (data.code !== 0) throw new Error('code=' + data.code + ' msg=' + data.msg);
      return data.data;
    } catch (e) {
      lastErr = e;
      if (/code=(131006|131005|131002)/.test(e.message)) throw e;
      await sleep(1000 * Math.pow(2, i));
    }
  }
  throw lastErr;
}

async function getNode(nodeToken) {
  const d = await api('https://open.feishu.cn/open-apis/wiki/v2/spaces/get_node?token=' + nodeToken);
  return d.node;
}

async function listChildren(spaceId, parentNodeToken) {
  const items = [];
  let pageToken = '';
  do {
    let url = 'https://open.feishu.cn/open-apis/wiki/v2/spaces/' + spaceId + '/nodes?page_size=50';
    if (parentNodeToken) url += '&parent_node_token=' + parentNodeToken;
    if (pageToken) url += '&page_token=' + pageToken;
    const d = await api(url);
    items.push(...(d.items || []));
    pageToken = d.has_more ? d.page_token : '';
  } while (pageToken);
  return items;
}

async function fetchBlocks(objToken) {
  const all = [];
  let pageToken = '';
  do {
    let url = 'https://open.feishu.cn/open-apis/docx/v1/documents/' + objToken + '/blocks?page_size=500';
    if (pageToken) url += '&page_token=' + pageToken;
    const d = await api(url);
    all.push(...(d.items || []));
    pageToken = d.has_more ? d.page_token : '';
  } while (pageToken);
  return all;
}

async function downloadMedia(token) {
  const res = await authFetch('https://open.feishu.cn/open-apis/drive/v1/medias/' + token + '/download');
  if (res.status !== 200) throw new Error('media download http ' + res.status);
  const ct = res.headers.get('content-type') || '';
  const buf = Buffer.from(await res.arrayBuffer());
  return { ct, buf };
}

function sanitize(name) {
  return String(name || '').replace(/[\\/:*?"<>|\r\n\t]/g, '_').replace(/[. ]+$/g, '').trim() || 'untitled';
}

function escapeInline(s) {
  return s.replace(/([\\`*_\[\]~])/g, '\\$1');
}

function extFromCt(ct) {
  if (ct.includes('png')) return 'png';
  if (ct.includes('jpeg') || ct.includes('jpg')) return 'jpg';
  if (ct.includes('gif')) return 'gif';
  if (ct.includes('webp')) return 'webp';
  if (ct.includes('svg')) return 'svg';
  return 'bin';
}

async function renderInline(elements) {
  let out = '';
  for (const el of elements || []) {
    if (el.text_run) {
      let t = el.text_run.content || '';
      const st = el.text_run.text_element_style || {};
      if (st.link && st.link.url) {
        let url = st.link.url;
        try { url = decodeURIComponent(url); } catch (e) {}
        out += '[' + escapeInline(t) + '](' + url + ')';
        continue;
      }
      if (st.inline_code) t = '`' + t.replace(/`/g, '\\`') + '`';
      if (st.bold) t = '**' + t + '**';
      if (st.italic) t = '*' + t + '*';
      if (st.strikethrough) t = '~~' + t + '~~';
      out += escapeInline(t);
    } else if (el.mention_doc) {
      const m = el.mention_doc;
      out += '[' + escapeInline(m.title || '文档') + '](' + (m.url || BASE_URL + '/docx/' + m.token) + ')';
    } else if (el.mention_user) {
      const m = el.mention_user;
      out += '@' + escapeInline(m.name || m.user_id || '用户');
    } else if (el.mention_chat) {
      const m = el.mention_chat;
      out += '[' + escapeInline(m.title || m.chat_id || '群聊') + '](https://my.feishu.cn/chat/' + (m.chat_id || '') + ')';
    } else if (el.equation) {
      out += ' $' + (el.equation.content || '') + '$ ';
    } else if (el.file) {
      out += ' [文件](' + (el.file.name || 'file') + ') ';
    } else if (el.image) {
      out += ' ![inline](https://open.feishu.cn/open-apis/drive/v1/medias/' + el.image.token + '/download) ';
    } else if (el.text_mention) {
      out += '@' + (el.text_mention.text || '');
    } else if (el.mention_docx) {
      out += '[' + escapeInline(el.mention_docx.title || '文档') + '](' + (el.mention_docx.url || '') + ')';
    } else {
      out += ' ';
    }
  }
  return out;
}

class DocRenderer {
  constructor(blocks, assetDir) {
    this.map = new Map(blocks.map(b => [b.block_id, b]));
    this.assetDir = assetDir;
    this.lines = [];
    this.ext = {};
  }

  async render() {
    const page = [...this.map.values()].find(b => b.block_type === 1);
    if (page) {
      const title = await renderInline(page.page && page.page.elements);
      if (title) this.lines.push('# ' + title, '');
      await this.renderChildren(page, 0);
    }
    return this.lines.join('\n');
  }

  async renderChildren(block, indent) {
    for (const cid of block.children || []) {
      const child = this.map.get(cid);
      if (child) await this.renderBlock(child, indent);
    }
  }

  async renderBlock(b, indent) {
    switch (b.block_type) {
      case 1: await this.renderChildren(b, indent); break;
      case 2: {
        const t = await renderInline(b.text && b.text.elements);
        if (t) this.lines.push(' '.repeat(indent) + t, '');
        break;
      }
      case 3: case 4: case 5: case 6: case 7: {
        const key = ['heading1','heading2','heading3','heading4','heading5'][b.block_type - 3];
        const t = await renderInline(b[key] && b[key].elements);
        if (t) this.lines.push('#'.repeat(b.block_type - 2) + ' ' + t, '');
        await this.renderChildren(b, indent);
        break;
      }
      case 12: {
        const t = await renderInline(b.bullet && b.bullet.elements);
        if (t) this.lines.push(' '.repeat(indent) + '- ' + t);
        await this.renderChildren(b, indent + 2);
        break;
      }
      case 13: {
        const t = await renderInline(b.ordered && b.ordered.elements);
        const seq = (b.ordered && b.ordered.style && b.ordered.style.sequence) || '1';
        if (t) this.lines.push(' '.repeat(indent) + seq + '. ' + t);
        await this.renderChildren(b, indent + 2);
        break;
      }
      case 17: {
        const t = await renderInline(b.todo && b.todo.elements);
        const done = b.todo && b.todo.style && b.todo.style.done;
        if (t) this.lines.push(' '.repeat(indent) + '- [' + (done ? 'x' : ' ') + '] ' + t);
        await this.renderChildren(b, indent + 2);
        break;
      }
      case 14: {
        const text = ((b.code && b.code.elements) || []).map(e => e.text_run ? e.text_run.content : '').join('').replace(/\n+$/, '');
        if (text) this.lines.push('```', text, '```', '');
        break;
      }
      case 22: this.lines.push('---', ''); break;
      case 27: {
        const token = b.image && b.image.token;
        if (token) {
          try {
            const fn = await this.saveMedia(token, 'images');
            this.lines.push('![](images/' + fn + ')', '');
          } catch (e) {
            this.lines.push('> [图片下载失败] token=' + token, '');
          }
        }
        break;
      }
      case 23: {
        const name = b.file && b.file.name;
        const token = b.file && b.file.token;
        if (token) {
          try {
            const fn = await this.saveMedia(token, 'files', name);
            this.lines.push('[' + escapeInline(name || fn) + '](files/' + encodeURI(fn) + ')', '');
          } catch (e) {
            this.lines.push('> [文件下载失败] ' + (name || token), '');
          }
        }
        break;
      }
      case 31: {
        await this.renderTable(b);
        this.lines.push('');
        break;
      }
      case 34: {
        const start = this.lines.length;
        await this.renderChildren(b, indent);
        const quoted = this.lines.splice(start);
        for (const ln of quoted) this.lines.push('> ' + ln);
        this.lines.push('');
        break;
      }
      case 33: await this.renderChildren(b, indent); break;
      case 30: {
        await this.renderSheet(b);
        break;
      }
      case 40: {
        try {
          const rec = JSON.parse(b.add_ons && b.add_ons.record);
          const data = (rec && rec.data) || '';
          const lines = data.replace(/\\n/g, '\n').split('\n');
          const hasMermaid = lines.some(l => /^(flowchart|graph|sequenceDiagram|classDiagram|stateDiagram|erDiagram|gantt|pie|journey|mindmap|timeline)/.test(l.trim()));
          if (hasMermaid) this.lines.push('```mermaid', lines.join('\n'), '```', '');
          else this.lines.push('```', lines.join('\n'), '```', '');
        } catch (e) {
          this.lines.push('> [图表无法解析]', '');
        }
        break;
      }
      default:
        this.lines.push('<!-- 未支持的块类型: ' + b.block_type + ' -->', '');
        await this.renderChildren(b, indent);
    }
  }

  async renderTable(b) {
    const prop = b.table && b.table.property;
    const colSize = (prop && prop.column_size) || 1;
    const rowSize = (prop && prop.row_size) || 0;
    const mergeInfo = (prop && prop.merge_info) || [];
    const cellIds = (b.table && b.table.cells) || [];
    const cellTexts = [];
    for (const cid of cellIds) {
      const cell = this.map.get(cid);
      const parts = [];
      if (cell) {
        for (const cc of cell.children || []) {
          const inner = this.map.get(cc);
          if (!inner) continue;
          if (inner.block_type === 2) {
            const t = await renderInline(inner.text && inner.text.elements);
            if (t) parts.push(t);
          } else if (inner.block_type === 1 || inner.block_type === 32 || inner.block_type === 34) {
            for (const ccc of inner.children || []) {
              const inn = this.map.get(ccc);
              if (inn && inn.block_type === 2) {
                const t = await renderInline(inn.text && inn.text.elements);
                if (t) parts.push(t);
              }
            }
          }
        }
      }
      cellTexts.push(parts.join('<br>'));
    }
    const grid = [];
    for (let r = 0; r < rowSize; r++) grid.push(new Array(colSize).fill(''));
    let idx = 0;
    for (let r = 0; r < rowSize && idx < cellTexts.length; r++) {
      for (let c = 0; c < colSize && idx < cellTexts.length; c++) {
        if (grid[r][c] !== '') continue;
        const text = cellTexts[idx];
        const mi = mergeInfo[idx] || {};
        const cs = Math.max(1, mi.col_span || 1);
        const rs = Math.max(1, mi.row_span || 1);
        grid[r][c] = text;
        for (let rr = r; rr < Math.min(rowSize, r + rs); rr++)
          for (let cc2 = c; cc2 < Math.min(colSize, c + cs); cc2++)
            if (rr !== r || cc2 !== c) grid[rr][cc2] = '';
        c += cs - 1;
        idx++;
      }
    }
    for (let r = 0; r < rowSize; r++) {
      const cells = grid[r].map(t => t.replace(/\|/g, '\\|').replace(/\n/g, '<br>'));
      this.lines.push('| ' + cells.join(' | ') + ' |');
      if (r === 0) this.lines.push('| ' + grid[r].map(() => '---').join(' | ') + ' |');
    }
  }

  async renderSheet(b) {
    const fullToken = b.sheet && b.sheet.token;
    if (!fullToken) return;
    const sp = fullToken.split('_')[0];
    try {
      const sheets = await listWorksheets(sp);
      for (const sh of sheets) {
        await dumpWorksheet(this.lines, sp, sh);
      }
    } catch (e) {
      this.lines.push('> [电子表格读取失败] token=' + fullToken + ' (' + e.message + ')', '');
    }
  }

  async saveMedia(token, subdir, preferredName) {
    const dir = path.join(this.assetDir, subdir);
    fs.mkdirSync(dir, { recursive: true });
    const cacheKey = subdir + '/' + token;
    if (this.ext[cacheKey]) return this.ext[cacheKey];
    const { ct, buf } = await downloadMedia(token);
    let fn;
    if (preferredName) {
      fn = sanitize(preferredName);
      if (!/\.\w+$/.test(fn)) fn += '.' + extFromCt(ct);
      if (fs.existsSync(path.join(dir, fn))) fn = token + '_' + fn;
    } else {
      fn = 'img_' + token + '.' + extFromCt(ct);
    }
    fs.writeFileSync(path.join(dir, fn), buf);
    this.ext[cacheKey] = fn;
    return fn;
  }
}

async function listWorksheets(spToken) {
  const meta = await api('https://open.feishu.cn/open-apis/sheets/v3/spreadsheets/' + spToken + '/sheets/query');
  return (meta.sheets || []).filter(s => !s.hidden);
}

async function dumpWorksheet(lines, sp, sh) {
  const gp = sh.grid_properties || {};
  const maxRows = Math.min(gp.row_count || 100, 500);
  const maxCols = Math.min(gp.column_count || 20, 26);
  if (maxRows === 0 || maxCols === 0) { lines.push('## ' + sh.title, '', '(空表格)', ''); return; }
  const lastCol = String.fromCharCode(64 + maxCols);
  const vd = await api('https://open.feishu.cn/open-apis/sheets/v2/spreadsheets/' + sp + '/values/' + sh.sheet_id + '!A1:' + lastCol + maxRows);
  const rows = vd.valueRange ? vd.valueRange.values : [];
  if (rows.length === 0) { lines.push('## ' + sh.title, '', '(空表格)', ''); return; }
  const norm = rows.map(r => {
    const len = Math.max(r ? r.length : 0, 1);
    return Array.from({ length: len }, (_, i) => {
      let v = r && r[i];
      if (v === null || v === undefined) return '';
      if (typeof v === 'object') v = JSON.stringify(v);
      return String(v).replace(/\|/g, '\\|').replace(/\n/g, '<br>');
    });
  });
  const nonEmpty = norm.filter(r => r.some(c => c !== ''));
  let maxLen = 0;
  for (const r of nonEmpty) maxLen = Math.max(maxLen, r.length);
  const CROP = 300;
  const shown = nonEmpty.slice(0, CROP).map(r => Array.from({ length: maxLen }, (_, i) => r[i] || ''));
  if (shown.length === 0) { lines.push('## ' + sh.title, '', '(空表格)', ''); return; }
  lines.push('## ' + sh.title, '');
  lines.push('| ' + shown[0].join(' | ') + ' |');
  lines.push('| ' + shown[0].map(() => '---').join(' | ') + ' |');
  for (const row of shown.slice(1)) lines.push('| ' + row.join(' | ') + ' |');
  lines.push('');
  if (nonEmpty.length > CROP) lines.push('> *(表格仅导出前 ' + CROP + ' 行，共 ' + nonEmpty.length + ' 行非空数据)*', '');
}

async function renderSpreadsheet(spToken) {
  const lines = [];
  const sheets = await listWorksheets(spToken);
  for (const sh of sheets) {
    await dumpWorksheet(lines, spToken, sh);
  }
  return lines.join('\n');
}

async function fetchRawDoc(objToken) {
  const d = await api('https://open.feishu.cn/open-apis/doc/v1/documents/' + objToken + '/raw_content');
  return d.content || '';
}

async function exportNode(node, dirPath) {
  stats.total++;
  const safeName = sanitize(node.title);
  const nodeDir = path.join(dirPath, safeName);
  fs.mkdirSync(nodeDir, { recursive: true });
  const mdFile = path.join(nodeDir, safeName + '.md');
  const url = BASE_URL + '/wiki/' + node.node_token;

  try {
    if (node.obj_type === 'docx') {
      const blocks = await fetchBlocks(node.obj_token);
      const renderer = new DocRenderer(blocks, nodeDir);
      const md = await renderer.render();
      fs.writeFileSync(mdFile, '<!-- 来源: ' + url + ' -->\n' + md + '\n', 'utf8');
      stats.ok++;
    } else if (node.obj_type === 'doc') {
      const raw = await fetchRawDoc(node.obj_token);
      fs.writeFileSync(mdFile, '<!-- 来源: ' + url + ' -->\n# ' + node.title + '\n\n' + raw + '\n', 'utf8');
      stats.ok++;
    } else if (node.obj_type === 'sheet') {
      const md = await renderSpreadsheet(node.obj_token);
      fs.writeFileSync(mdFile, '<!-- 来源: ' + url + ' -->\n# ' + node.title + '\n\n' + md + '\n', 'utf8');
      stats.ok++;
    } else {
      fs.writeFileSync(mdFile, '<!-- 来源: ' + url + ' -->\n# ' + node.title + '\n\n> [暂不支持导出该类型: ' + node.obj_type + ']\n', 'utf8');
      stats.warnings++;
    }
  } catch (e) {
    stats.failed++;
    failedList.push({ title: node.title, error: e.message });
    fs.writeFileSync(mdFile, '<!-- 来源: ' + url + ' -->\n# ' + node.title + '\n\n> [导出失败] ' + e.message + '\n', 'utf8');
  }
  console.log('[' + stats.total + '] ' + node.title + ' (' + node.obj_type + ') -> ' + nodeDir);
}

async function walk(node, dirPath) {
  await exportNode(node, dirPath);
  if (node.has_child) {
    const children = await listChildren(node.space_id, node.node_token);
    const childDir = path.join(dirPath, sanitize(node.title));
    for (const c of children) await walk(c, childDir);
  }
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.help) { usage(); return; }
  if (args.url) {
    try { BASE_URL = new URL(args.url).origin; } catch (e) {}
  }

  const commonPath = findFeishuCommon();
  loadCredentials(commonPath);
  authFetch = require(commonPath).fetchWithAuth;

  const outDir = path.resolve(args.out || 'feishu-wiki-export');
  fs.mkdirSync(outDir, { recursive: true });

  let roots;
  if (args.space) {
    try {
      roots = await listChildren(args.space, null);
    } catch (e) {
      if (/131006/.test(e.message)) {
        throw new Error('space-level listing denied (131006): the app has no wiki space read permission. Export branch by branch with --url/--token instead (each branch root token can be taken from an exported md header: <!-- 来源: https://<host>/wiki/<token> -->).');
      }
      throw e;
    }
    if (!roots.length) throw new Error('space ' + args.space + ': no top-level nodes found');
  } else {
    const token = args.token || extractToken(args.url || '');
    if (!token) { usage(); process.exit(2); }
    roots = [await getNode(token)];
  }

  for (const node of roots) {
    console.log('Root:', node.title, 'space:', node.space_id);
    await walk(node, outDir);
  }

  console.log('\n===== SUMMARY =====');
  console.log('total:', stats.total, 'ok:', stats.ok, 'failed:', stats.failed, 'warnings:', stats.warnings);
  console.log('out:', outDir);
  if (failedList.length) {
    console.log('\n===== FAILED =====');
    for (const f of failedList) console.log(JSON.stringify(f));
    process.exitCode = 1;
  }
}

main().catch(e => { console.error('FATAL', e.message || e); process.exitCode = 1; });
