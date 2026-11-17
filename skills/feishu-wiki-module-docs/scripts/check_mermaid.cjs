#!/usr/bin/env node
/**
 * Validate all Mermaid (Feishu "文本绘图", block_type 40) diagrams in a doc.
 *
 * Usage:
 *   node check_mermaid.cjs --doc <doc_or_wiki_token>
 *
 * Requires Playwright + Chromium. Set PLAYWRIGHT_MODULE if the default path is wrong.
 * Uses Mermaid 11 from a CDN; retries jsdelivr then unpkg.
 * Exits 1 if any diagram fails parse or render.
 */

const path = require('path');
const { fetchWithAuth } = require(path.resolve(__dirname, '../../feishu-common/index.js'));

process.env.FEISHU_APP = process.env.FEISHU_APP || 'company';
const BASE = 'https://open.feishu.cn/open-apis';
const PLAYWRIGHT = process.env.PLAYWRIGHT_MODULE || 'D:/workspace/aaas-fork/node_modules/.pnpm/playwright@1.62.1/node_modules/playwright';
const { chromium } = require(PLAYWRIGHT);

function parseArgs(argv) {
  const opts = {};
  for (let i = 0; i < argv.length; i++) {
    if (!argv[i].startsWith('--')) continue;
    const key = argv[i].slice(2);
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

async function api(pathname) {
  const res = await fetchWithAuth(`${BASE}${pathname}`);
  const data = await res.json();
  if (data.code !== 0) throw new Error(`${pathname}: ${JSON.stringify(data)}`);
  return data.data;
}

async function resolveDoc(token) {
  const clean = String(token).match(/\/(?:docx|wiki|doc)\/([a-zA-Z0-9]+)/)?.[1] || token;
  try {
    const data = await api(`/wiki/v2/spaces/get_node?token=${encodeURIComponent(clean)}`);
    if (data.node.obj_type === 'docx' || data.node.obj_type === 'doc') return data.node.obj_token;
  } catch {
    /* not a wiki token */
  }
  return clean;
}

async function readDiagrams(doc) {
  const diagrams = [];
  let pageToken = '';
  do {
    const data = await api(`/docx/v1/documents/${doc}/blocks?page_size=500${pageToken ? `&page_token=${encodeURIComponent(pageToken)}` : ''}`);
    for (const block of data.items || []) {
      if (block.block_type !== 40) continue;
      let record;
      try {
        record = JSON.parse(block.add_ons.record);
      } catch (error) {
        diagrams.push({ blockId: block.block_id, code: '', error: `bad add_ons.record: ${error.message}` });
        continue;
      }
      diagrams.push({ blockId: block.block_id, code: String(record.data || ''), error: undefined });
      diagrams[diagrams.length - 1].index = diagrams.length;
    }
    pageToken = data.has_more ? data.page_token : '';
  } while (pageToken);
  return diagrams;
}

(async () => {
  const opts = parseArgs(process.argv.slice(2));
  if (!opts.doc) throw new Error('missing --doc');
  const doc = await resolveDoc(opts.doc);
  const diagrams = await readDiagrams(doc);
  if (diagrams.length === 0) {
    console.log('No Mermaid blocks found.');
    return;
  }

  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('about:blank');
  const urls = [
    'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js',
    'https://unpkg.com/mermaid@11/dist/mermaid.min.js',
  ];
  const scriptErrors = [];
  let loaded = false;
  for (const url of urls) {
    try {
      await page.addScriptTag({ url, timeout: 30000 });
      loaded = await page.evaluate(() => Boolean(window.mermaid));
      if (loaded) break;
    } catch (error) {
      scriptErrors.push(`${url}: ${String(error && error.message || error)}`);
    }
  }
  if (!loaded) {
    console.error(JSON.stringify({ ok: false, error: 'mermaid CDN load failed: ' + scriptErrors.join(' | ') }));
    await browser.close();
    process.exit(1);
  }
  const results = await page.evaluate(async (items) => {
    const mermaid = window.mermaid;
    mermaid.initialize({ startOnLoad: false });
    const out = [];
    for (let i = 0; i < items.length; i++) {
      const item = items[i];
      if (item.error) {
        out.push({ ...item, ok: false, error: item.error });
        continue;
      }
      try {
        await mermaid.parse(item.code);
        const rendered = await mermaid.render('mmd_validate_' + i, item.code);
        out.push({ ...item, ok: true, svgLen: rendered.svg.length });
      } catch (error) {
        out.push({ ...item, ok: false, error: String((error && (error.message || error.str)) || error) });
      }
    }
    return out;
  }, diagrams.map(({ blockId, code, error, index }) => ({ blockId, code, error, index })));

  const failures = results.filter((item) => !item.ok);
  for (const item of results) {
    console.log(`${item.ok ? 'PASS' : 'FAIL'} | #${item.index} ${item.blockId}${item.ok ? '' : ' | ' + item.error}`);
  }
  console.log(`PASS ${results.length - failures.length}  FAIL ${failures.length}`);
  if (failures.length) {
    for (const failure of failures) {
      console.log(`\n### ${failure.blockId}\n${failure.error}\n--- code ---\n${failure.code}`);
    }
    process.exitCode = 1;
  }
  await browser.close();
})().catch((error) => {
  console.error(JSON.stringify({ ok: false, error: String(error?.message || error) }));
  process.exit(1);
});
