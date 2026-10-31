[CmdletBinding()]
param(
    [string]$Binary = "$env:APPDATA\npm\node_modules\opencode-ai\bin\opencode.exe",
    [int]$ExpectedMaxDelayMs = 300000,
    [int]$Seconds = 12,
    [int]$TimingSeconds = 15,
    [switch]$SkipRuntime,
    [switch]$KeepFiles
)

$ErrorActionPreference = "Stop"
$script:Enc = [System.Text.Encoding]::GetEncoding(28591)
$script:Root = Join-Path $env:LOCALAPPDATA ("opencode-retry-e2e-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
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

function Get-Python {
    foreach ($name in @("python", "python3", "py")) {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd) { return $cmd.Source }
    }
    throw "Python is required for the E2E mock provider"
}

function Write-MockServer {
    $mock = @'
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

port = int(sys.argv[1])
mode = sys.argv[2]
retry_after = sys.argv[3] if len(sys.argv) > 3 else None
count = 0
start = time.time()


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        global count
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        count += 1
        print(json.dumps({"t": round(time.time() - start, 3), "n": count, "path": self.path}), flush=True)
        if mode == "filter":
            status = 400
            body = {
                "error": {
                    "message": "The response was blocked by the provider's content filter",
                    "type": "invalid_request_error",
                    "code": "content_filter",
                }
            }
        else:
            status = 500
            body = {"error": {"message": "mock upstream failure", "type": "server_error"}}
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        if retry_after is not None:
            self.send_header("Retry-After", retry_after)
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
print(f"PORT {server.server_address[1]}", flush=True)
server.serve_forever()
'@
    $path = Join-Path $script:Root "mock-server.py"
    [System.IO.File]::WriteAllText($path, $mock, (New-Object System.Text.UTF8Encoding($false)))
    return $path
}

function Start-Mock {
    param([string]$MockPath, [string]$Mode, [string]$RetryAfter)
    $safe = ($Mode + "-" + [guid]::NewGuid().ToString("N").Substring(0, 12))
    $dir = Join-Path $script:Root $safe
    New-Item -ItemType Directory -Path $dir -Force | Out-Null
    $log = Join-Path $dir "server.log"
    $err = Join-Path $dir "server.err.log"
    $args = @("-u", $MockPath, "0", $Mode)
    if ($RetryAfter) { $args += $RetryAfter }
    $proc = Start-Process -FilePath (Get-Python) -ArgumentList $args -RedirectStandardOutput $log -RedirectStandardError $err -PassThru -WindowStyle Hidden
    $port = $null
    for ($i = 0; $i -lt 100; $i++) {
        Start-Sleep -Milliseconds 100
        if (Test-Path -LiteralPath $log) {
            $line = Get-Content -LiteralPath $log -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($line -match "^PORT (\d+)$") { $port = [int]$Matches[1]; break }
        }
        if ($proc.HasExited) { break }
    }
    if (-not $port) {
        if (-not $proc.HasExited) { Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue }
        throw "Mock server failed to start: $(Get-Content -LiteralPath $err -ErrorAction SilentlyContinue | Out-String)"
    }
    return [pscustomobject]@{ Process = $proc; Port = $port; Log = $log; Dir = $dir }
}

function Stop-Mock {
    param($Mock)
    if ($Mock -and $Mock.Process -and -not $Mock.Process.HasExited) {
        Stop-Process -Id $Mock.Process.Id -Force -ErrorAction SilentlyContinue
    }
}

function Write-TestConfig {
    param([int]$Port, [string]$Path)
    $config = [ordered]@{
        '$schema' = "https://opencode.ai/config.json"
        provider = [ordered]@{
            deepseek = [ordered]@{
                options = [ordered]@{
                    baseURL = "http://127.0.0.1:$Port/v1"
                    apiKey = "test"
                }
            }
        }
    }
    $json = $config | ConvertTo-Json -Depth 8
    [System.IO.File]::WriteAllText($Path, $json, (New-Object System.Text.UTF8Encoding($false)))
}

function Get-RequestTimes {
    param([string]$LogPath)
    $times = New-Object System.Collections.Generic.List[double]
    if (-not (Test-Path -LiteralPath $LogPath)) { return $times }
    foreach ($line in Get-Content -LiteralPath $LogPath -ErrorAction SilentlyContinue) {
        if ($line -match '^\{"t":\s*([0-9.]+)') { $times.Add([double]$Matches[1]) }
    }
    return $times
}

function Invoke-Run {
    param([string]$Exe, [string]$Mode, [string]$RetryAfter, [int]$RunSeconds, [string]$Tag)
    $mock = Start-Mock -MockPath $script:MockPath -Mode $Mode -RetryAfter $RetryAfter
    try {
        $cfg = Join-Path $mock.Dir "config.json"
        Write-TestConfig -Port $mock.Port -Path $cfg
        $out = Join-Path $mock.Dir "out.log"
        $err = Join-Path $mock.Dir "err.log"
        $env:OPENCODE_CONFIG = $cfg
        $env:DEEPSEEK_API_KEY = "test"
        $env:XDG_CONFIG_HOME = (Join-Path $script:Root "xdg-config")
        $env:XDG_DATA_HOME = (Join-Path $script:Root "xdg-data")
        $env:XDG_CACHE_HOME = (Join-Path $script:Root "xdg-cache")
        $p = Start-Process -FilePath $Exe -ArgumentList @("run", "hi", "-m", "deepseek/deepseek-flash", "--pure", "--dir", $script:Root) -WorkingDirectory $script:Root -RedirectStandardOutput $out -RedirectStandardError $err -PassThru -WindowStyle Hidden
        Start-Sleep -Seconds $RunSeconds
        $alive = $false
        if (-not $p.HasExited) { $alive = $true }
        $name = [System.IO.Path]::GetFileNameWithoutExtension($Exe)
        foreach ($proc in @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $Exe })) {
            if (-not $proc.HasExited) { $alive = $true }
        }
        $times = Get-RequestTimes $mock.Log
        $count = $times.Count
        if ($alive) {
            Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
        }
        foreach ($proc in @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $Exe })) {
            Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        }
        Start-Sleep -Milliseconds 500
        return [pscustomobject]@{ Alive = $alive; Count = $count; Times = $times; Out = $out; Err = $err; Dir = $mock.Dir }
    } finally {
        Stop-Mock $mock
    }
}

try {
    New-Item -ItemType Directory -Path $script:Root -Force | Out-Null
    if (-not (Test-Path -LiteralPath $Binary -PathType Leaf)) { throw "Binary not found: $Binary" }

    $bytes = [System.IO.File]::ReadAllBytes($Binary)
    $text = $script:Enc.GetString($bytes)
    $marker = "https://opencode.ai/go"
    $anchor = $text.IndexOf($marker, [System.StringComparison]::Ordinal)
    $patched = $false
    $detail = ""
    if ($anchor -lt 0) {
        $detail = "retry code not found"
    } else {
        $after = $anchor + $marker.Length
        $window = $text.Substring($after, [Math]::Min(50000, $text.Length - $after))
        $contentOk = $window.IndexOf("/content.?f/i", [System.StringComparison]::Ordinal) -ge 0
        $capRegex = [regex]'if\s*\(\s*([A-Za-z_$][\w$]*)\.attempt\s*>\s*([A-Za-z_$][\w$]*)\s*\)\s*return\s+([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\(\s*\1\.attempt\s*\)'
        $capOk = -not $capRegex.IsMatch($window)
        $delayOk = $false
        $runRegex = [regex]'^\s*"\s*,\s*(?<body>(?:[A-Za-z_$][\w$]*\s*=\s*(?<num>(?:[0-9][0-9_]*(?:\.[0-9_]*)?(?:[eE][+-]?[0-9]+)?|0x[0-9a-fA-F]+))\s*,\s*)+)'
        $run = $runRegex.Match($window)
        if ($run.Success) {
            $vals = @()
            foreach ($m in [regex]::Matches($run.Groups["body"].Value, '(?<num>(?:[0-9][0-9_]*(?:\.[0-9_]*)?(?:[eE][+-]?[0-9]+)?|0x[0-9a-fA-F]+))')) {
                $raw = $m.Groups["num"].Value.Replace("_", "")
                $num = if ($raw -match "^0x") { [double][Convert]::ToInt64($raw.Substring(2), 16) } else { [double]::Parse($raw, [Globalization.CultureInfo]::InvariantCulture) }
                $vals += $num
            }
            $matchesMax = @($vals | Where-Object { [Math]::Abs($_ - $ExpectedMaxDelayMs) -lt 0.5 }).Count
            $delayOk = $matchesMax -ge 2
        }
        $patched = $contentOk -and $capOk -and $delayOk
        $detail = "content=$contentOk capRemoved=$capOk maxDelay=$delayOk"
    }
    Write-Result "Static patch check" $patched $detail

    $script:MockPath = Write-MockServer
    if (-not $SkipRuntime) {
        $testExe = Join-Path $script:Root "e2e-target.exe"
        Copy-Item -LiteralPath $Binary -Destination $testExe -Force
        $r500 = Invoke-Run -Exe $testExe -Mode "500" -RetryAfter "0.2" -RunSeconds $Seconds -Tag "500"
        $ok500 = $r500.Alive -and $r500.Count -ge 15
        Write-Result "HTTP 500 keeps retrying (no 5-attempt stop)" $ok500 ("alive={0} requests={1}" -f $r500.Alive, $r500.Count)

        $rf = Invoke-Run -Exe $testExe -Mode "filter" -RetryAfter "0.2" -RunSeconds $Seconds -Tag "filter"
        $okf = $rf.Alive -and $rf.Count -ge 15
        Write-Result "Content filter keeps retrying" $okf ("alive={0} requests={1}" -f $rf.Alive, $rf.Count)

        if ($ExpectedMaxDelayMs -le 2000) {
            $rt = Invoke-Run -Exe $testExe -Mode "500" -RetryAfter $null -RunSeconds $TimingSeconds -Tag "timing"
            $gaps = New-Object System.Collections.Generic.List[double]
            for ($i = 1; $i -lt $rt.Times.Count; $i++) { $gaps.Add($rt.Times[$i] - $rt.Times[$i - 1]) }
            $tail = @($gaps | Select-Object -Last 8)
            $maxGap = if ($tail.Count -gt 0) { ($tail | Measure-Object -Maximum).Maximum } else { 0 }
            $minGap = if ($tail.Count -gt 0) { ($tail | Measure-Object -Minimum).Minimum } else { 0 }
            $capSeconds = $ExpectedMaxDelayMs / 1000.0
            $okTiming = $rt.Alive -and $rt.Count -ge 6 -and $maxGap -ge ($capSeconds * 0.7) -and $maxGap -le ($capSeconds * 1.6)
            Write-Result "Exponential backoff cap" $okTiming ("alive={0} requests={1} maxGap={2:N3}s minGap={3:N3}s cap={4:N3}s" -f $rt.Alive, $rt.Count, $maxGap, $minGap, $capSeconds)
        } else {
            $capDetail = if ($patched) { "max delay = {0} ms; runtime cap timing is covered by the short-cap test" -f $ExpectedMaxDelayMs } else { "static patch verification failed" }
            Write-Result "Exponential backoff cap (static)" $patched $capDetail
        }
    }
} catch {
    Write-Result "E2E execution" $false $_.Exception.Message
} finally {
    Remove-Item Env:OPENCODE_CONFIG -ErrorAction SilentlyContinue
    Remove-Item Env:DEEPSEEK_API_KEY -ErrorAction SilentlyContinue
    Remove-Item Env:XDG_CONFIG_HOME -ErrorAction SilentlyContinue
    Remove-Item Env:XDG_DATA_HOME -ErrorAction SilentlyContinue
    Remove-Item Env:XDG_CACHE_HOME -ErrorAction SilentlyContinue
    $script:Results | Format-Table -AutoSize | Out-String | Write-Host
    Write-Host ("RESULT: {0} passed, {1} failed" -f $script:Pass, $script:Fail)
    if (-not $KeepFiles) {
        Start-Sleep -Milliseconds 500
        Remove-Item -LiteralPath $script:Root -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        Write-Host "Artifacts: $script:Root"
    }
    if ($script:Fail -gt 0) { exit 1 } else { exit 0 }
}
