const fs = require('fs');
const path = require('path');
const os = require('os');

const TOKEN_CACHE_FILE = path.resolve(__dirname, '../memory/feishu_token.json');

let tokenCache = {
  token: null,
  expireTime: 0,
  appId: null
};

// FEISHU_APP=<name> selects config.<name>.json (default: config.json).
function profileName() {
  const raw = (process.env.FEISHU_APP || '').trim();
  if (!raw) return '';
  if (!/^[A-Za-z0-9_-]+$/.test(raw)) {
    throw new Error('Invalid FEISHU_APP name (letters/digits/-/_ allowed): ' + raw);
  }
  return raw;
}

function configFileNames() {
  const p = profileName();
  return p ? ['config.' + p + '.json'] : ['config.json'];
}

function configCandidates() {
  const names = configFileNames();
  const roots = [
    path.resolve(__dirname, '..'),
    path.join(os.homedir(), '.agents', 'skills'),
    path.join(os.homedir(), '.config', 'opencode', 'skills')
  ];
  const seen = new Set();
  const out = [];
  const push = p => { if (!seen.has(p)) { seen.add(p); out.push(p); } };
  for (const name of names) {
    push(path.join(__dirname, '..', name));
    for (const root of roots) {
      push(path.join(root, name));
      let entries = [];
      try { entries = fs.readdirSync(root, { withFileTypes: true }); } catch (e) {}
      for (const ent of entries) {
        if (ent.isDirectory() && ent.name.startsWith('feishu-')) {
          push(path.join(root, ent.name, name));
        }
      }
    }
  }
  return out;
}

function loadConfig() {
  if (process.env.FEISHU_APP_ID && process.env.FEISHU_APP_SECRET) {
    return { app_id: process.env.FEISHU_APP_ID, app_secret: process.env.FEISHU_APP_SECRET };
  }
  for (const c of configCandidates()) {
    let cfg;
    try { cfg = JSON.parse(fs.readFileSync(c, 'utf8')); } catch (e) { continue; }
    if (cfg && cfg.app_id && cfg.app_secret) {
      return { app_id: cfg.app_id, app_secret: cfg.app_secret };
    }
  }
  return {
    app_id: process.env.FEISHU_APP_ID,
    app_secret: process.env.FEISHU_APP_SECRET
  };
}

function readDiskToken(appId) {
  try {
    if (!fs.existsSync(TOKEN_CACHE_FILE)) return null;
    const saved = JSON.parse(fs.readFileSync(TOKEN_CACHE_FILE, 'utf8'));
    const expiry = saved.expire || saved.expireTime;
    const now = Math.floor(Date.now() / 1000);
    // Cache is bound to an app; never reuse another app's token.
    if (saved.token && expiry > now && saved.app_id === appId) {
      return { token: saved.token, expireTime: expiry };
    }
  } catch (e) {}
  return null;
}

async function getTenantAccessToken(forceRefresh = false) {
  const now = Math.floor(Date.now() / 1000);
  const config = loadConfig();

  if (forceRefresh) {
    tokenCache.token = null;
    tokenCache.expireTime = 0;
    tokenCache.appId = null;
    try { if (fs.existsSync(TOKEN_CACHE_FILE)) fs.unlinkSync(TOKEN_CACHE_FILE); } catch (e) {}
  } else {
    if (tokenCache.token && tokenCache.expireTime > now && tokenCache.appId === config.app_id) {
      return tokenCache.token;
    }
    const cached = readDiskToken(config.app_id);
    if (cached) {
      tokenCache.token = cached.token;
      tokenCache.expireTime = cached.expireTime;
      tokenCache.appId = config.app_id;
      return tokenCache.token;
    }
    tokenCache.token = null;
    tokenCache.expireTime = 0;
    tokenCache.appId = null;
  }

  if (!config.app_id || !config.app_secret) {
    throw new Error("Missing app_id or app_secret. Set FEISHU_APP_ID and FEISHU_APP_SECRET env vars or create config[.<FEISHU_APP>].json (e.g. ~/.agents/skills/config.json).");
  }

  let lastError;
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const response = await fetch('https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          app_id: config.app_id,
          app_secret: config.app_secret
        })
      });

      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const data = await response.json();
      if (data.code !== 0) throw new Error(`Failed to get tenant_access_token: ${data.msg}`);

      tokenCache.token = data.tenant_access_token;
      tokenCache.expireTime = now + data.expire - 60;
      tokenCache.appId = config.app_id;

      try {
        const cacheDir = path.dirname(TOKEN_CACHE_FILE);
        if (!fs.existsSync(cacheDir)) fs.mkdirSync(cacheDir, { recursive: true });
        fs.writeFileSync(TOKEN_CACHE_FILE, JSON.stringify({
          token: tokenCache.token,
          expire: tokenCache.expireTime,
          app_id: config.app_id
        }, null, 2));
      } catch (e) {
        console.error("Failed to save token cache:", e.message);
      }

      return tokenCache.token;
    } catch (error) {
      lastError = error;
      if (attempt < 3) await new Promise(r => setTimeout(r, 1000 * Math.pow(2, attempt - 1)));
    }
  }

  throw lastError || new Error("Failed to retrieve access token after retries");
}

async function fetchWithAuth(url, options = {}) {
  const token = await getTenantAccessToken();
  const headers = {
    ...options.headers,
    'Authorization': `Bearer ${token}`
  };

  let response = await fetch(url, { ...options, headers });

  if (response.status === 401 || response.status === 403) {
    const retryToken = await getTenantAccessToken(true);
    headers.Authorization = `Bearer ${retryToken}`;
    response = await fetch(url, { ...options, headers });
  }

  return response;
}

module.exports = { getTenantAccessToken, getToken: getTenantAccessToken, fetchWithAuth };
