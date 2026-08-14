const fs = require('fs');
const path = require('path');

const TOKEN_CACHE_FILE = path.resolve(__dirname, '../memory/feishu_token.json');

let tokenCache = {
  token: null,
  expireTime: 0
};

function loadConfig() {
  const configPath = path.join(__dirname, '../config.json');
  let config = {};
  if (fs.existsSync(configPath)) {
    try {
      config = JSON.parse(fs.readFileSync(configPath, 'utf8'));
    } catch (e) {
      console.error("Failed to parse config.json");
    }
  }
  return {
    app_id: process.env.FEISHU_APP_ID || config.app_id,
    app_secret: process.env.FEISHU_APP_SECRET || config.app_secret
  };
}

async function getTenantAccessToken(forceRefresh = false) {
  const now = Math.floor(Date.now() / 1000);

  if (!forceRefresh && !tokenCache.token && fs.existsSync(TOKEN_CACHE_FILE)) {
    try {
      const saved = JSON.parse(fs.readFileSync(TOKEN_CACHE_FILE, 'utf8'));
      const expiry = saved.expire || saved.expireTime;
      if (saved.token && expiry > now) {
        tokenCache.token = saved.token;
        tokenCache.expireTime = expiry;
      }
    } catch (e) {}
  }

  if (forceRefresh) {
    tokenCache.token = null;
    tokenCache.expireTime = 0;
    try { if (fs.existsSync(TOKEN_CACHE_FILE)) fs.unlinkSync(TOKEN_CACHE_FILE); } catch(e) {}
  }

  if (tokenCache.token && tokenCache.expireTime > now) {
    return tokenCache.token;
  }

  const config = loadConfig();
  if (!config.app_id || !config.app_secret) {
    throw new Error("Missing app_id or app_secret. Set FEISHU_APP_ID and FEISHU_APP_SECRET env vars or config.json.");
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

      try {
        const cacheDir = path.dirname(TOKEN_CACHE_FILE);
        if (!fs.existsSync(cacheDir)) fs.mkdirSync(cacheDir, { recursive: true });
        fs.writeFileSync(TOKEN_CACHE_FILE, JSON.stringify({
          token: tokenCache.token,
          expire: tokenCache.expireTime
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
