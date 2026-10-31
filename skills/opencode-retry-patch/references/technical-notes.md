# Technical notes

## Upstream source

OpenCode 1.x retry policy lives in `packages/opencode/src/session/retry.ts`:

- `RETRY_INITIAL_DELAY = 2000`
- `RETRY_BACKOFF_FACTOR = 2`
- `RETRY_MAX_DELAY_NO_HEADERS = 30_000`
- `RETRY_MAX_DELAY = 2_147_483_647`
- `RETRY_MAX_RETRIES = 5`
- `policy()` returns `Cause.done(...)` when `meta.attempt > RETRY_MAX_RETRIES`
- `matchesRetryableMessage()` checks `RETRYABLE_MESSAGE_PATTERNS` against the message/response body

PR `#41939` introduced the 5-attempt cap. The patch removes that branch, raises both delay caps to `300000`, and extends the retryable-message helper with a content-filter match.

## CLI binary (Bun standalone)

The npm package `opencode-ai` ships a Bun standalone executable. It contains:

- a Bun runtime (PE/ELF/Mach-O)
- an embedded module graph with plain-text JS chunks
- a trailer `\n---- Bun! ----\n` followed by an offsets record

The retry code is inside one bundled chunk (for example `chunk-*.js`). Because the file is a compiled executable, any patch that changes the JS length breaks internal offsets. The scripts therefore only perform **same-length** replacements:

- `3e4` → `3e5` (30s → 5min)
- `2147483647` → `3e5` + padding (2^31-1 → 5min)
- `if (<id>.attempt > <id>)` → `if (0)` + padding
- `return typeof <v> === "string" && ARR.some(...)` → `ARR.some(...) || /content.?f/i.test(<v>)` + padding

The scripts locate the retry block by the stable `https://opencode.ai/go` marker, not by line numbers, so they survive most 1.x minifier changes. On 1.18.16 the retry cap does not exist; the scripts patch only the delay constants.

## Desktop (`app.asar`)

The desktop app is Electron. `resources/app.asar` has a Pickle-based header:

- offset 0/4/8: Pickle sizes
- offset 12: JSON header length
- offset 16: JSON header
- data start: aligned `16 + jsonLength`

The sidecar server is `out/main/sidecar.js`, which imports `./chunks/node-*.js` and calls `Server.listen`. The retry code is in that main chunk. The app's Electron fuse `EnableEmbeddedAsarIntegrityValidation` is **Disabled**, so `app.asar` can be modified in place. The script still keeps the file size and all asar offsets unchanged.

The desktop patch makes the same four changes; it also runs `node --check` on the patched chunk and restarts the app.

## Deferred apply

The CLI binary is locked while opencode runs. The patch script:

1. Writes the patched bytes to `opencode.exe.retry-new`.
2. Writes a small ASCII `apply-worker.ps1` shadow and a JSON config under `%LOCALAPPDATA%\opencode-retry-patch`.
3. Creates a one-time scheduled task that runs the shadow with the JSON config.
4. The worker waits for the binary to unlock, verifies the old and new hashes, creates `*.retrybak`, replaces the binary, then deletes the scheduled task.

The shadow + JSON approach avoids command-line encoding problems when the skill lives under a non-ASCII path (for example `D:\tool\opencode重试解除`). Do not put the original script path directly into the scheduled task action.

## E2E semantics

CLI E2E starts a local Python mock provider and runs a copy of the tested binary with a temporary OpenCode config:

- HTTP 500 + `Retry-After: 0.2` → must keep making requests and stay alive (unpatched stops after 5 retries)
- HTTP 400 + content-filter message + `Retry-After: 0.2` → must keep retrying (unpatched exits after 1 build request)
- HTTP 500 without timing headers on a short-cap copy → measures the exponential gap cap (`MaxDelayMs`)

Desktop E2E extracts the patched chunk from `app.asar` and evaluates the retry functions in Node with the real `RETRYABLE_MESSAGE_PATTERNS`, then checks the app process and latest `server.log` for `server ready`.

## Tested versions

| Version | Surface | Result |
|---|---|---|
| 1.19.4 | CLI | 4/4 E2E PASS |
| 1.18.17 | CLI | patch applied, binary starts |
| 1.18.16 | CLI | patch applied (no retry cap), binary starts |
| 1.19.5 | Desktop | 3/3 E2E PASS |
