import { spawn } from 'node:child_process';
import { existsSync, mkdirSync, mkdtempSync, statSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import net from 'node:net';

const args = process.argv.slice(2);
const opt = (name, def = undefined) => {
  const i = args.indexOf('--' + name);
  if (i < 0) return def;
  const v = args[i + 1];
  return (v === undefined || v.startsWith('--')) ? true : v;
};
const flag = name => args.includes('--' + name);

const url = opt('url');
if (!url) {
  console.error('用法: node page-shot.mjs --url <URL> [--mode viewport|full|element|annotate] [--selector CSS] [--out file.png]');
  process.exit(2);
}

const mode = opt('mode', 'viewport');
const selector = opt('selector');
const width = Number(opt('width', 1440));
const height = Number(opt('height', 900));
const dpr = Number(opt('dpr', 2));
const mobile = flag('mobile');
const dark = flag('dark');
const hide = opt('hide');
const waitMs = Number(opt('wait', 1200));
const profile = opt('profile');
const headed = flag('headed');
const scrollThrough = flag('scroll-through');
const browserPref = opt('browser', 'auto');
let out = opt('out');

const CHROME_PATHS = [
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
  'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe'
];
if (browserPref === 'edge') CHROME_PATHS.reverse();
const exe = CHROME_PATHS.find(p => existsSync(p));
if (!exe) {
  console.error('找不到 Chrome/Edge，请安装或用 --browser 指定');
  process.exit(2);
}
if (!out) out = join(tmpdir(), `page-shot-${Date.now()}.png`);
mkdirSync(dirname(out), { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));

const freePort = () => new Promise(resolve => {
  const srv = net.createServer();
  srv.listen(0, '127.0.0.1', () => {
    const p = srv.address().port;
    srv.close(() => resolve(p));
  });
});

const port = await freePort();
const chromeArgs = [
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${profile || mkdtempSync(join(tmpdir(), 'page-shot-prof-'))}`,
  '--no-first-run', '--no-default-browser-check', '--hide-scrollbars',
  '--disable-extensions', '--force-color-profile=srgb'
];
if (!headed) chromeArgs.push('--headless=new', '--disable-gpu');
chromeArgs.push('about:blank');

const proc = spawn(exe, chromeArgs, { stdio: 'ignore', windowsHide: true });

let ver;
for (let i = 0; i < 100; i++) {
  try { ver = await (await fetch(`http://127.0.0.1:${port}/json/version`)).json(); break; }
  catch { await sleep(150); }
}
if (!ver) { proc.kill(); throw new Error('DevTools 未就绪'); }

const ws = new WebSocket(ver.webSocketDebuggerUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let seq = 0;
const pending = new Map();
ws.onmessage = ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) {
    const { res, rej } = pending.get(m.id);
    pending.delete(m.id);
    m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
  }
};
const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
  const id = ++seq;
  pending.set(id, { res, rej });
  ws.send(JSON.stringify({ id, method, params, sessionId }));
});

const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
const S = (m, p) => send(m, p, sessionId);

const shots = [];
const capture = async (file, params) => {
  const { data } = await S('Page.captureScreenshot', { format: 'png', ...params });
  writeFileSync(file, Buffer.from(data, 'base64'));
  shots.push(file);
  return file;
};
const evalJs = async (expression, awaitPromise = false) => {
  const r = await S('Runtime.evaluate', { expression, returnByValue: true, awaitPromise });
  if (r.exceptionDetails) throw new Error(r.exceptionDetails.text + ' ' + (r.exceptionDetails.exception?.description || ''));
  return r.result.value;
};
const waitReady = async (timeout = 30000) => {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    try { if (await evalJs('document.readyState') === 'complete') break; } catch { }
    await sleep(100);
  }
  await sleep(waitMs);
};

await S('Page.enable');
await S('Runtime.enable');
await S('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: dpr, mobile });
if (mobile) await S('Emulation.setTouchEmulationEnabled', { enabled: true, maxTouchPoints: 5 });
await S('Emulation.setEmulatedMedia', { features: [{ name: 'prefers-color-scheme', value: dark ? 'dark' : 'light' }] });

await S('Page.navigate', { url });
await waitReady();

if (hide) {
  const list = hide.split(',').map(s => s.trim()).filter(Boolean);
  await evalJs(`(() => {
    const sels = ${JSON.stringify(list)};
    const st = document.createElement('style');
    st.textContent = sels.map(s => s + '{display:none !important}').join('\\n');
    document.head.appendChild(st);
    return sels.length;
  })()`);
  await sleep(200);
}

if (scrollThrough) {
  await evalJs(`(async () => {
    const step = innerHeight * 0.8;
    for (let y = 0; y < document.body.scrollHeight; y += step) {
      scrollTo(0, y);
      await new Promise(r => setTimeout(r, 120));
    }
    scrollTo(0, 0);
    await new Promise(r => setTimeout(r, 300));
    return document.body.scrollHeight;
  })()`, true);
}

const result = { url, mode, browser: exe, viewport: [width, height], dpr, mobile, dark, shots };

if (mode === 'viewport') {
  result.file = await capture(out, { fromSurface: true });
} else if (mode === 'annotate') {
  if (!selector) throw new Error('annotate 模式需要 --selector');
  const box = await evalJs(`(() => {
    document.querySelectorAll('.__shot_mark').forEach(n => n.remove());
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) return null;
    el.scrollIntoView({ block: 'center' });
    const r = el.getBoundingClientRect();
    const mk = document.createElement('div');
    mk.className = '__shot_mark';
    Object.assign(mk.style, {
      position: 'fixed', left: (r.left - 6) + 'px', top: (r.top - 6) + 'px',
      width: (r.width + 12) + 'px', height: (r.height + 12) + 'px',
      border: '3px solid #ff2d55', borderRadius: '6px',
      boxShadow: '0 0 0 9999px rgba(0,0,0,.38)', zIndex: 999999, pointerEvents: 'none'
    });
    const tag = document.createElement('div');
    tag.className = '__shot_mark';
    Object.assign(tag.style, {
      position: 'fixed', left: (r.left - 6) + 'px', top: Math.max(4, r.top - 38) + 'px',
      background: '#ff2d55', color: '#fff', font: '600 14px/1.7 system-ui, sans-serif',
      padding: '1px 8px', borderRadius: '4px', zIndex: 1000000, pointerEvents: 'none'
    });
    tag.textContent = ${JSON.stringify(selector)};
    document.body.append(mk, tag);
    return { width: r.width, height: r.height };
  })()`);
  if (!box) throw new Error('selector 没有匹配元素: ' + selector);
  await sleep(350);
  result.marked = [Math.round(box.width), Math.round(box.height)];
  result.file = await capture(out, { fromSurface: true });
} else if (mode === 'element') {
  if (!selector) throw new Error('element 模式需要 --selector');
  const rect = await evalJs(`(() => {
    const el = document.querySelector(${JSON.stringify(selector)});
    if (!el) return null;
    el.scrollIntoView({ block: 'start' });
    const r = el.getBoundingClientRect();
    return { x: r.x + scrollX, y: r.y + scrollY, w: r.width, h: r.height };
  })()`);
  if (!rect) throw new Error('selector 没有匹配元素: ' + selector);
  result.element = [Math.round(rect.w), Math.round(rect.h)];
  result.file = await capture(out, {
    clip: { x: rect.x, y: rect.y, width: rect.w, height: rect.h, scale: 1 },
    captureBeyondViewport: true
  });
} else if (mode === 'full') {
  const m1 = await S('Page.getLayoutMetrics');
  const w = Math.ceil(Math.max(m1.cssContentSize.width, width));
  await S('Emulation.setDeviceMetricsOverride', { width: w, height, deviceScaleFactor: 1, mobile });
  await sleep(250);
  const m2 = await S('Page.getLayoutMetrics');
  const cs = m2.cssContentSize;
  result.pageSize = [Math.round(cs.width), Math.round(cs.height)];
  if (cs.height > 16384) result.warning = '页面高度 > 16384px，可能被纹理上限截断，可分段截图';
  result.file = await capture(out, {
    clip: { x: 0, y: 0, width: cs.width, height: cs.height, scale: 1 },
    captureBeyondViewport: true
  });
} else {
  throw new Error('未知 mode: ' + mode);
}

result.bytes = existsSync(out) ? statSync(out).size : 0;
console.log(JSON.stringify(result, null, 2));

await send('Browser.close').catch(() => { });
ws.close();
setTimeout(() => { try { proc.kill(); } catch { } process.exit(0); }, 400);
