# Troubleshooting

## `Target is in use` / `Patch scheduled as task ...`

Expected when the CLI is running. The scheduled task waits for the binary to unlock, then replaces it. Check:

```powershell
schtasks /Query /FO LIST | Select-String "OpenCodeRetryPatch"
Get-ChildItem "$env:LOCALAPPDATA\opencode-retry-patch"
Get-Content "$env:LOCALAPPDATA\opencode-retry-patch\apply-*.log" -Tail 50
```

Exit all opencode processes. The task applies, deletes itself, and removes its JSON/shadow/CMD files; only `apply-*.log` remains. If it does not:

```powershell
schtasks /Query /TN "OpenCodeRetryPatch-<hash>-<path>" /FO LIST /V
```

Last Result `64` usually means `pwsh -File` received a bad script path. The current scripts avoid this with the ASCII shadow + JSON config; if an old task exists, delete it and re-run the patch script.

## `No patch points matched` / `Not a supported opencode build`

The bundled JS minifier/version changed. The scripts search by the `https://opencode.ai/go` marker and structural patterns. Inspect the installed binary/chunk and update the regexes in:

- `scripts/opencode-retry-patch.ps1` (`Get-BinaryPatchState`)
- `scripts/opencode-desktop-retry-patch.ps1` (`Patch-DesktopChunk`)

Do not change the file length; use equal-length replacements.

## Desktop app is running

Re-run with `-CloseApp`:

```powershell
.\scripts\opencode-desktop-retry-patch.cmd -CloseApp
```

The script backs up `app.asar` before replacing it, then relaunches the app. `EnableEmbeddedAsarIntegrityValidation` is Disabled on the tested build, so the modified asar loads.

## Desktop app fails to start after patching

Restore the backup:

```powershell
.\scripts\opencode-desktop-retry-patch.cmd -Restore
```

Or copy `resources\app.asar.<hash>.retrybak` back to `app.asar`. Then report the version and the failed `node --check` output.

## Patch disappears after an update

OpenCode / desktop auto-update replaces the binary or `app.asar`. Re-run the patch script. Backups are named `*.retrybak`; remove old backups if disk usage matters.

## E2E dependency errors

- CLI E2E needs Python 3 (`python`/`python3`/`py`) for the mock provider.
- Desktop E2E needs Node.js.
- Both E2E scripts create temporary configurations and sessions; they do not modify the installed binary (they test a copy).

## Scope

Only OpenCode 1.x Bun/Electron builds are handled. For OpenCode 2.x, use its documented `session.retry` plugin hook or update the 2.x source instead of applying these byte patches.
