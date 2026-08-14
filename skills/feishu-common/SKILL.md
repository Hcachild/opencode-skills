---
name: feishu-common
description: Shared Feishu (Lark) auth library for feishu-* skills. Provides tenant_access_token caching and authed fetch. Install before feishu-doc-1.2.7. Not a standalone skill — used via require('../feishu-common/index.js').
---

# feishu-common

Shared authentication library used by `feishu-doc-1.2.7` (and other feishu-* skills).

## Installation

```bash
cd skills/feishu-common
npm install
```

## Configuration

Credentials come from environment variables or `config.json`:

| Source | Keys |
|--------|------|
| Env vars | `FEISHU_APP_ID`, `FEISHU_APP_SECRET` |
| `config.json` (optional) | `app_id`, `app_secret` |

## API

- `getTenantAccessToken(forceRefresh?)` — cached tenant access token
- `fetchWithAuth(url, options?)` — fetch with Bearer auth and 401/403 retry

## Notes

- Token cache file: `../memory/feishu_token.json` (gitignored, never commit)
- Only install this skill if you use feishu-* skills