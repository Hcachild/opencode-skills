[CmdletBinding()]
param(
    [string]$Asar,
    [switch]$SkipAppCheck,
    [switch]$KeepFiles
)

$ErrorActionPreference = "Stop"
$script:Utf8 = New-Object System.Text.UTF8Encoding($false)
$script:Root = Join-Path $env:LOCALAPPDATA ("opencode-desktop-e2e-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
$script:Pass = 0
$script:Fail = 0
$script:Results = New-Object System.Collections.Generic.List[object]

function Write-Result {
    param([string]$Name, [bool]$Ok, [string]$Detail)
    if ($Ok) { $script:Pass++ } else { $script:Fail++ }
    $script:Results.Add([pscustomobject]@{ Test = $Name; Result = $(if ($Ok) { "PASS" } else { "FAIL" }); Detail = $Detail })
    $color = if ($Ok) { "Green" } else { "Red" }
    Write-Host ("[{0}] {1} - {2}" -f $(if ($Ok) { "PASS" } else { "FAIL" }), $Name, $Detail) -ForegroundColor $color
}

function Get-AsarPath {
    if ($Asar) { return $Asar }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\@opencode-aidesktop\resources\app.asar"),
        (Join-Path $env:LOCALAPPDATA "@opencode-aidesktop\resources\app.asar"),
        (Join-Path $env:LOCALAPPDATA "Programs\OpenCode\resources\app.asar"),
        (Join-Path $env:LOCALAPPDATA "OpenCode\resources\app.asar")
    )
    if ($env:ProgramFiles) { $candidates += (Join-Path $env:ProgramFiles "@opencode-aidesktop\resources\app.asar") }
    foreach ($c in $candidates) { if (Test-Path -LiteralPath $c -PathType Leaf) { return $c } }
    throw "OpenCode desktop app.asar not found"
}

function Get-AsarInfo {
    param([byte[]]$Bytes)
    $jsonLen = [System.BitConverter]::ToUInt32($Bytes, 12)
    $jsonText = $script:Utf8.GetString($Bytes, 16, $jsonLen)
    $header = $jsonText | ConvertFrom-Json -AsHashtable
    $dataStart = 16 + $jsonLen
    if (($dataStart % 4) -ne 0) { $dataStart += 4 - ($dataStart % 4) }
    return [pscustomobject]@{ Header = $header; DataStart = [int64]$dataStart }
}

function Find-AsarEntry {
    param($Node, [string]$Prefix, [int64]$Target, [int64]$DataStart)
    $files = $Node['files']
    if (-not $files) { return $null }
    foreach ($name in $files.Keys) {
        $entry = $files[$name]
        $full = if ($Prefix) { "$Prefix/$name" } else { $name }
        if ($entry -is [System.Collections.IDictionary] -and $entry.Contains("files")) {
            $found = Find-AsarEntry -Node $entry -Prefix $full -Target $Target -DataStart $DataStart
            if ($found) { return $found }
        } elseif ($entry -is [System.Collections.IDictionary] -and $entry.Contains("offset") -and $null -ne $entry["offset"]) {
            $abs = $DataStart + [int64]$entry["offset"]
            $size = [int64]$entry["size"]
            if ($Target -ge $abs -and $Target -lt ($abs + $size)) {
                return [pscustomobject]@{ Path = $full; Offset = $abs; Size = $size }
            }
        }
    }
    return $null
}

$nodeTest = @'
const fs = require("node:fs");
const vm = require("node:vm");
const path = process.argv[2];
const text = fs.readFileSync(path, "utf8");
const arrayStart = text.indexOf("RETRYABLE_MESSAGE_PATTERNS = [");
if (arrayStart < 0) throw new Error("patterns array not found");
const arrayEnd = text.indexOf("\n  ];", arrayStart);
if (arrayEnd < 0) throw new Error("patterns array end not found");
const patterns = text.slice(arrayStart, arrayEnd + 5);
const fnStart = text.indexOf("function cap(ms3)");
const fnEnd = text.indexOf("function str3", fnStart);
if (fnStart < 0 || fnEnd < 0) throw new Error("retry functions not found");
const fns = text.slice(fnStart, fnEnd);
const sandbox = {
  RETRY_INITIAL_DELAY: 2e3,
  RETRY_BACKOFF_FACTOR: 2,
  RETRY_JITTER_FACTOR: 0.25,
  RETRY_MAX_DELAY_NO_HEADERS: 3e5,
  RETRY_MAX_DELAY: 3e5,
  GO_UPSELL_MESSAGE: "Free usage exceeded, subscribe to Go",
  GO_UPSELL_URL: "https://opencode.ai/go",
  ContextOverflowError2: { isInstance: () => false },
  APIError2: { isInstance: (e) => Boolean(e && e.__api) },
  parseJSON13: (v) => { try { return JSON.parse(v); } catch { return undefined; } },
  str3: (v) => (v === undefined || v === null ? "" : String(v)),
  num: (v) => { const n = Number.parseFloat(v === undefined || v === null ? "" : String(v)); return Number.isNaN(n) ? undefined : n; },
  iife2: (fn) => fn(),
  isRecord2: (v) => Boolean(v) && typeof v === "object",
  console, Math, Number, Date, JSON
};
const code = `${patterns}\n${fns}\n({ delay8, retryable, matchesRetryableMessage })`;
const r = vm.runInNewContext(code, sandbox, { filename: "retry-extract.js" });
const assert = (cond, msg) => { if (!cond) throw new Error("FAIL: " + msg); console.log("PASS: " + msg); };
assert(r.matchesRetryableMessage("The response was blocked by the provider's content filter") === true, "content filter message matches");
assert(r.matchesRetryableMessage("network error") === true, "network error still matches");
assert(r.matchesRetryableMessage(undefined) === false, "undefined is not retryable");
assert(r.delay8(1, undefined, 0) === 2000, "first delay is 2000ms");
assert(r.delay8(20, undefined, 0) === 300000, "exponential delay capped at 300000ms");
assert(r.delay8(1, { data: { responseHeaders: { "retry-after": "600" } } }, 0) === 300000, "retry-after capped at 300000ms");
assert(Boolean(r.retryable({ __api: true, data: { message: "The response was blocked by the provider's content filter", statusCode: 400, isRetryable: false } }, "test")), "APIError content filter is retryable");
assert(Boolean(r.retryable({ data: { message: "The response was blocked by the provider's content filter" } }, "test")), "plain content filter error is retryable");
assert(r.retryable({ __api: true, data: { message: "invalid request", statusCode: 400, isRetryable: false } }, "test") === undefined, "invalid request is not retryable");
assert(Boolean(r.retryable({ __api: true, data: { message: "network error", statusCode: 500, isRetryable: false } }, "test")), "500 network error is retryable");
console.log("ALL DESKTOP RETRY TESTS PASSED");
'@

try {
    New-Item -ItemType Directory -Path $script:Root -Force | Out-Null
    $asarPath = Get-AsarPath
    $bytes = [System.IO.File]::ReadAllBytes($asarPath)
    $info = Get-AsarInfo $bytes
    $latin = [System.Text.Encoding]::GetEncoding(28591).GetString($bytes)
    $target = $latin.IndexOf("RETRY_MAX_RETRIES", [System.StringComparison]::Ordinal)
    $entry = if ($target -ge 0) { Find-AsarEntry -Node $info.Header -Prefix "" -Target $target -DataStart $info.DataStart } else { $null }
    if (-not $entry) { throw "Retry chunk not found in app.asar" }
    $chunk = $script:Utf8.GetString($bytes, [int]$entry.Offset, [int]$entry.Size)

    $okNoHeader = $chunk -match 'RETRY_MAX_DELAY_NO_HEADERS\s*=\s*3e5'
    $okMax = $chunk -match 'RETRY_MAX_DELAY\s*=\s*3e5'
    $okCap = $chunk -notmatch 'if\s*\(\s*[A-Za-z_$][\w$]*\.attempt\s*>\s*RETRY_MAX_RETRIES\s*\)'
    $okContent = $chunk.Contains('/content.?f/i')
    Write-Result "Static desktop patch check" ($okNoHeader -and $okMax -and $okCap -and $okContent) "noHeader=$okNoHeader max=$okMax capRemoved=$okCap content=$okContent"

    $chunkPath = Join-Path $script:Root "chunk.mjs"
    $testPath = Join-Path $script:Root "test.cjs"
    [System.IO.File]::WriteAllText($chunkPath, $chunk, $script:Utf8)
    [System.IO.File]::WriteAllText($testPath, $nodeTest, $script:Utf8)
    if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw "Node.js is required for the desktop retry test" }
    & node $testPath $chunkPath 2>&1 | ForEach-Object { Write-Host $_ }
    $nodeOk = $LASTEXITCODE -eq 0
    Write-Result "Desktop retry behavior" $nodeOk "node exit=$LASTEXITCODE"

    if (-not $SkipAppCheck) {
        $desktopExe = Join-Path (Split-Path -Parent (Split-Path -Parent $asarPath)) "OpenCode.exe"
        $running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $desktopExe }).Count
        if ($running -eq 0) {
            Write-Result "Desktop app running" $false "OpenCode.exe is not running"
        } else {
            $logRoot = Join-Path $env:APPDATA "ai.opencode.desktop\logs"
            $mainLog = $null
            if (Test-Path $logRoot) {
                $latestDir = Get-ChildItem $logRoot -Directory | Sort-Object LastWriteTime -Descending | Select-Object -First 1
                if ($latestDir) { $mainLog = Join-Path $latestDir.FullName "main.log" }
            }
            $ready = $false
            if ($mainLog -and (Test-Path $mainLog)) {
                $ready = (Get-Content $mainLog -Tail 200 | Select-String -Pattern "server ready").Count -gt 0
            }
            Write-Result "Desktop app running" ($running -gt 0 -and $ready) ("processes=$running serverReady=$ready")
        }
    }
} catch {
    Write-Result "Desktop E2E execution" $false $_.Exception.Message
} finally {
    $script:Results | Format-Table -AutoSize | Out-String | Write-Host
    Write-Host ("RESULT: {0} passed, {1} failed" -f $script:Pass, $script:Fail)
    if (-not $KeepFiles) { Remove-Item -LiteralPath $script:Root -Recurse -Force -ErrorAction SilentlyContinue }
    else { Write-Host "Artifacts: $script:Root" }
    if ($script:Fail -gt 0) { exit 1 } else { exit 0 }
}
