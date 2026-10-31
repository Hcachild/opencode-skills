[CmdletBinding()]
param(
    [string]$Path,
    [switch]$Restore,
    [switch]$NoBackup,
    [int]$MaxDelayMs = 300000,
    [switch]$WaitAndReplace,
    [string]$Target,
    [string]$Patched,
    [string]$ExpectedHash,
    [string]$ExpectedNewHash,
    [string]$LogFile,
    [string]$TaskName,
    [string]$WorkerConfig
)

$ErrorActionPreference = "Stop"
$script:Enc = [System.Text.Encoding]::GetEncoding(28591)
$script:LogDir = Join-Path $env:LOCALAPPDATA "opencode-retry-patch"
$script:Cleanup = @()
$script:Marker = "https://opencode.ai/go"
$script:Utf8 = New-Object System.Text.UTF8Encoding($false)

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    Write-Host $line
    if ($LogFile) {
        try {
            $dir = Split-Path -Parent $LogFile
            if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
            Add-Content -LiteralPath $LogFile -Value $line -Encoding UTF8
        } catch { }
    }
}

function Get-HashHex {
    param([byte[]]$Bytes)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        $hash = $sha.ComputeHash($Bytes)
        return ([System.BitConverter]::ToString($hash)).Replace("-", "")
    } finally {
        $sha.Dispose()
    }
}

function Get-FileHashHex {
    param([string]$File)
    return Get-HashHex ([System.IO.File]::ReadAllBytes($File))
}

function Test-Writable {
    param([string]$File)
    try {
        $fs = [System.IO.File]::Open($File, [System.IO.FileMode]::Open, [System.IO.FileAccess]::ReadWrite, [System.IO.FileShare]::None)
        $fs.Close()
        $fs.Dispose()
        return $true
    } catch {
        return $false
    }
}

function Convert-ToNumber {
    param([string]$Text)
    $t = $Text.Replace("_", "")
    if ($t -match "^0[xX]") {
        return [double][Convert]::ToInt64($t.Substring(2), 16)
    }
    return [double]::Parse($t, [System.Globalization.CultureInfo]::InvariantCulture)
}

function Format-MaxLiteral {
    param([string]$OldToken, [int]$Value)
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($Value -gt 0) {
        $exp = [int][Math]::Floor([Math]::Log10([double]$Value))
        $mant = [double]$Value / [Math]::Pow(10, $exp)
        $mantText = $mant.ToString("0.############", [System.Globalization.CultureInfo]::InvariantCulture)
        $candidates.Add($mantText + "e" + [string]$exp)
    }
    $candidates.Add([string]$Value)
    foreach ($c in $candidates) {
        if ($c.Length -le $OldToken.Length) {
            return $c + (" " * ($OldToken.Length - $c.Length))
        }
    }
    throw "Cannot express MaxDelayMs=$Value within the existing token '$OldToken'"
}

function Get-AnchorIndexes {
    param([string]$Text)
    $list = New-Object System.Collections.Generic.List[int]
    $i = 0
    while (($i = $Text.IndexOf($script:Marker, $i, [System.StringComparison]::Ordinal)) -ge 0) {
        $list.Add($i)
        $i += $script:Marker.Length
    }
    return $list
}

function New-PatchState {
    return [pscustomobject]@{
        Replacements = New-Object System.Collections.Generic.List[object]
        ByIndex = @{}
        FoundMax = $false
        FoundNoHeader = $false
        FoundRetryCap = $false
        FoundContentFilter = $false
        AlreadyContentFilter = $false
        AlreadyMax = $false
    }
}

function Add-Replacement {
    param($State, [string]$Text, [int]$Index, [int]$Length, [string]$NewText)
    if ($Length -le 0) { return }
    if ($NewText.Length -ne $Length) { throw "Replacement length mismatch at $Index" }
    if ($State.ByIndex.ContainsKey($Index)) {
        $existing = $State.ByIndex[$Index]
        if ($existing.New -ne $NewText) { throw "Conflicting replacement at $Index" }
        return
    }
    $old = $Text.Substring($Index, $Length)
    $item = [pscustomobject]@{ Index = $Index; Length = $Length; Old = $old; New = $NewText }
    $State.Replacements.Add($item)
    $State.ByIndex[$Index] = $item
}

function Get-BinaryPatchState {
    param([string]$Text, [int]$MaxDelayMs)
    $state = New-PatchState
    $anchors = Get-AnchorIndexes $Text
    if ($anchors.Count -eq 0) { return $state }

    $numPattern = "(?:[0-9][0-9_]*(?:\.[0-9_]*)?(?:[eE][+-]?[0-9]+)?|0x[0-9a-fA-F]+)"
    $runRegex = [regex]("^\s*""\s*,\s*(?<body>(?:[A-Za-z_$][\w$]*\s*=\s*" + $numPattern + "\s*,\s*)+)")
    $assignRegex = [regex]("(?<id>[A-Za-z_$][\w$]*)\s*=\s*(?<num>" + $numPattern + ")\s*,")
    $fallbackNoHeader = [regex]("=\s*(?<num>30_000|30000|3e4)\s*,")
    $fallbackMax = [regex]("=\s*(?<num>2_147_483_647|2147483647)\s*,")
    $capRegex = [regex]'if\s*\(\s*(?<v>[A-Za-z_$][\w$]*)\.attempt\s*>\s*(?<c>[A-Za-z_$][\w$]*)\s*\)\s*return\s+(?<f>[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)\(\s*\k<v>\.attempt\s*\)'
    $contentRegex = [regex]'function\s+(?<fn>[A-Za-z_$][\w$]*)\((?<p>[A-Za-z_$][\w$]*)\)\{return (?<body>typeof \k<p>\s*===?\s*"string"\s*&&\s*(?<arr>[A-Za-z_$][\w$]*)\.some\(\((?<it>[A-Za-z_$][\w$]*)\)=>\k<it>\.test\(\k<p>\)\))'

    foreach ($anchor in $anchors) {
        $after = $anchor + $script:Marker.Length
        $windowLen = [Math]::Min(100000, $Text.Length - $after)
        if ($windowLen -le 0) { continue }
        $window = $Text.Substring($after, $windowLen)
        if ($window.IndexOf("/content.?f/i", [System.StringComparison]::Ordinal) -ge 0) { $state.AlreadyContentFilter = $true }

        $run = $runRegex.Match($window)
        if ($run.Success) {
            $body = $run.Groups["body"].Value
            $bodyStart = $after + $run.Groups["body"].Index
            foreach ($m in $assignRegex.Matches($body)) {
                $raw = $m.Groups["num"].Value
                $val = Convert-ToNumber $raw
                $abs = $bodyStart + $m.Groups["num"].Index
                if ([Math]::Abs($val - 30000) -lt 0.5) {
                    $state.FoundNoHeader = $true
                    Add-Replacement $state $Text $abs $raw.Length (Format-MaxLiteral $raw $MaxDelayMs)
                } elseif ([Math]::Abs($val - 2147483647) -lt 0.5) {
                    $state.FoundMax = $true
                    Add-Replacement $state $Text $abs $raw.Length (Format-MaxLiteral $raw $MaxDelayMs)
                } elseif ([Math]::Abs($val - $MaxDelayMs) -lt 0.5) {
                    $state.AlreadyMax = $true
                }
            }
        } else {
            $probe = $window.Substring(0, [Math]::Min(6000, $window.Length))
            if ($probe.IndexOf("retry-after-ms", [System.StringComparison]::Ordinal) -ge 0) {
                $m = $fallbackNoHeader.Match($probe)
                if ($m.Success) {
                    $raw = $m.Groups["num"].Value
                    $state.FoundNoHeader = $true
                    Add-Replacement $state $Text ($after + $m.Groups["num"].Index) $raw.Length (Format-MaxLiteral $raw $MaxDelayMs)
                }
                $m = $fallbackMax.Match($probe)
                if ($m.Success) {
                    $raw = $m.Groups["num"].Value
                    $state.FoundMax = $true
                    Add-Replacement $state $Text ($after + $m.Groups["num"].Index) $raw.Length (Format-MaxLiteral $raw $MaxDelayMs)
                }
            }
        }

        $capProbe = $window.Substring(0, [Math]::Min(50000, $window.Length))
        foreach ($m in $capRegex.Matches($capProbe)) {
            $headLen = $m.Value.IndexOf("return", [System.StringComparison]::Ordinal)
            if ($headLen -gt 0) {
                $newHead = "if(0)" + (" " * ($headLen - 5))
                Add-Replacement $state $Text ($after + $m.Index) $headLen $newHead
                $state.FoundRetryCap = $true
            }
        }

        foreach ($m in $contentRegex.Matches($capProbe)) {
            $fn = $m.Groups["fn"].Value
            $p = $m.Groups["p"].Value
            $arr = $m.Groups["arr"].Value
            $it = $m.Groups["it"].Value
            $body = $m.Groups["body"].Value
            $checks = @(
                "/content.?f/i.test($p)",
                "/content.f/i.test($p)",
                "/content f/i.test($p)",
                "/content/i.test($p)"
            )
            $replacement = $null
            foreach ($check in $checks) {
                $candidate = "$arr.some($it=>$it.test($p))||$check"
                if ($candidate.Length -le $body.Length) {
                    $replacement = $candidate + (" " * ($body.Length - $candidate.Length))
                    break
                }
            }
            if ($replacement) {
                Add-Replacement $state $Text ($after + $m.Groups["body"].Index) $body.Length $replacement
                $state.FoundContentFilter = $true
            } else {
                $full = $m.Value
                $candidate = "var $fn=$p=>$arr.some($it=>$it.test($p))||/content.?f/i.test($p);"
                if ($candidate.Length -le $full.Length) {
                    Add-Replacement $state $Text ($after + $m.Index) $full.Length ($candidate + (" " * ($full.Length - $candidate.Length)))
                    $state.FoundContentFilter = $true
                }
            }
        }
    }

    return $state
}

function Apply-Replacements {
    param([string]$Text, $State)
    if ($State.Replacements.Count -eq 0) { return $Text }
    $items = @($State.Replacements | Sort-Object -Property Index -Descending)
    $sb = [System.Text.StringBuilder]::new($Text)
    foreach ($item in $items) {
        if ($sb.Length -lt ($item.Index + $item.Length)) { throw "Replacement out of range" }
        $current = $sb.ToString($item.Index, $item.Length)
        if ($current -ne $item.Old) { throw "Unexpected text at offset $($item.Index)" }
        [void]$sb.Remove($item.Index, $item.Length)
        [void]$sb.Insert($item.Index, $item.New)
    }
    $out = $sb.ToString()
    if ($out.Length -ne $Text.Length) { throw "Patch changed file length" }
    return $out
}

function Get-SourcePatchText {
    param([string]$Text, [int]$MaxDelayMs)
    $new = $Text
    $new = [regex]::Replace($new, "(RETRY_MAX_DELAY_NO_HEADERS\s*=\s*)(?:30_000|30000|3e4)", ('${1}' + [string]$MaxDelayMs))
    $new = [regex]::Replace($new, "(RETRY_MAX_DELAY\s*=\s*)(?:2_147_483_647|2147483647)", ('${1}' + [string]$MaxDelayMs))
    $new = [regex]::Replace($new, "if\s*\(\s*meta\.attempt\s*>\s*RETRY_MAX_RETRIES\s*\)", "if (false)")
    if ($new.IndexOf("/content.?f/i", [System.StringComparison]::Ordinal) -lt 0) {
        $new = [regex]::Replace($new, '(RETRYABLE_MESSAGE_PATTERNS\.some\(\((?<p>[A-Za-z_$][\w$]*)\) => \k<p>\.test\((?<v>[A-Za-z_$][\w$]*)\)\))', '$1 || /content.?f/i.test(${v})')
    }
    return $new
}

function Get-Candidates {
    $list = New-Object System.Collections.Generic.List[string]
    $seen = @{}
    function Add-Candidate([string]$Candidate) {
        if (-not $Candidate) { return }
        $Candidate = $Candidate.Trim().Trim('"')
        if ($Candidate.IndexOf("%dp0%", [System.StringComparison]::OrdinalIgnoreCase) -ge 0) { return }
        if ($Candidate.IndexOf('$basedir', [System.StringComparison]::OrdinalIgnoreCase) -ge 0) { return }
        try {
            $full = [System.IO.Path]::GetFullPath($Candidate)
        } catch {
            return
        }
        if (-not (Test-Path -LiteralPath $full -PathType Leaf)) { return }
        $key = $full.ToLowerInvariant()
        if ($seen.ContainsKey($key)) { return }
        $seen[$key] = $true
        $list.Add($full)
    }

    if ($Path) {
        Add-Candidate $Path
        return $list
    }

    foreach ($cmd in @(Get-Command opencode -All -ErrorAction SilentlyContinue)) {
        if (-not $cmd.Source) { continue }
        if ($cmd.Source -match "\.exe$") {
            Add-Candidate $cmd.Source
            continue
        }
        try {
            $content = Get-Content -LiteralPath $cmd.Source -Raw -ErrorAction Stop
        } catch {
            continue
        }
        foreach ($m in [regex]::Matches($content, '(?i)([A-Z]:\\[^"\r\n]*?opencode\.exe)')) {
            Add-Candidate $m.Groups[1].Value
        }
        foreach ($m in [regex]::Matches($content, '(?i)(?:%dp0%|\$basedir)[\\/]([^"\r\n]*?opencode\.exe)')) {
            Add-Candidate (Join-Path (Split-Path -Parent $cmd.Source) $m.Groups[1].Value)
        }
    }

    $common = @(
        (Join-Path $env:APPDATA "npm\node_modules\opencode-ai\bin\opencode.exe"),
        (Join-Path $env:APPDATA "npm\node_modules\opencode-ai\node_modules\opencode-windows-x64\bin\opencode.exe"),
        (Join-Path $env:APPDATA "npm\node_modules\opencode-windows-x64\bin\opencode.exe"),
        (Join-Path $env:USERPROFILE ".bun\bin\opencode.exe"),
        (Join-Path $env:USERPROFILE ".local\bin\opencode.exe"),
        (Join-Path $env:USERPROFILE ".opencode\bin\opencode.exe"),
        (Join-Path $env:LOCALAPPDATA "opencode\bin\opencode.exe"),
        (Join-Path $env:LOCALAPPDATA "opencode\opencode.exe"),
        (Join-Path $env:LOCALAPPDATA "Programs\opencode\opencode.exe"),
        (Join-Path $env:ProgramData "opencode\opencode.exe")
    )
    if ($env:ProgramFiles) { $common += (Join-Path $env:ProgramFiles "opencode\opencode.exe") }
    if (${env:ProgramFiles(x86)}) { $common += (Join-Path ${env:ProgramFiles(x86)} "opencode\opencode.exe") }
    foreach ($c in $common) { Add-Candidate $c }

    return $list
}

function Get-HardlinkKey {
    param([string]$File)
    try {
        $lines = @(fsutil hardlink list $File 2>$null)
        if ($lines.Count -gt 0) {
            $normalized = @()
            foreach ($line in $lines) {
                $p = $line.Trim()
                if ($p -match "^\\") { $p = $env:SystemDrive + $p }
                $normalized += $p.ToLowerInvariant()
            }
            $normalized = @($normalized | Sort-Object)
            return $normalized[0]
        }
    } catch { }
    return $File.ToLowerInvariant()
}

function Remove-ApplyTask {
    param([string]$Name)
    if (-not $Name) { return }
    try { & schtasks.exe /Delete /TN $Name /F *> $null } catch { }
}

function Start-ApplyWorker {
    param([string]$TargetFile, [string]$TempFile, [string]$OldHash, [string]$NewHash)
    $dir = $script:LogDir
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    $workerLog = Join-Path $dir ("apply-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".log")
    $shell = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
    if (-not $shell) { $shell = (Get-Command powershell -ErrorAction SilentlyContinue).Source }
    if (-not $shell) { throw "PowerShell executable not found" }
    $targetKey = (Get-HashHex ([System.Text.Encoding]::UTF8.GetBytes($TargetFile.ToLowerInvariant()))).Substring(0,8)
    $taskName = "OpenCodeRetryPatch-" + $OldHash.Substring(0,8) + "-" + $targetKey
    $shadow = Join-Path $dir ("apply-worker-" + $OldHash.Substring(0,8) + "-" + $targetKey + ".ps1")
    if ($PSCommandPath -ne $shadow) { Copy-Item -LiteralPath $PSCommandPath -Destination $shadow -Force }
    $workerConfig = Join-Path $dir ("apply-" + $OldHash.Substring(0,8) + "-" + $targetKey + ".json")
    $cmdPath = Join-Path $dir ("apply-" + $OldHash.Substring(0,8) + "-" + $targetKey + ".cmd")
    $configData = [ordered]@{
        Target = $TargetFile
        Patched = $TempFile
        ExpectedHash = $OldHash
        ExpectedNewHash = $NewHash
        LogFile = $workerLog
        TaskName = $taskName
        Cleanup = @($workerConfig, $shadow, $cmdPath)
    }
    $configJson = $configData | ConvertTo-Json -Depth 4
    [System.IO.File]::WriteAllText($workerConfig, $configJson, (New-Object System.Text.UTF8Encoding($false)))
    $argLine = "`"$shell`" -NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$shadow`" -WaitAndReplace -WorkerConfig `"$workerConfig`""
    $cmdContent = "@echo off`r`n$argLine`r`n"
    [System.IO.File]::WriteAllText($cmdPath, $cmdContent, [System.Text.Encoding]::Default)
    $startTime = (Get-Date).AddMinutes(1).ToString("HH:mm")
    $create = & schtasks.exe /Create /TN $taskName /SC ONCE /ST $startTime /TR "`"$cmdPath`"" /F /RL LIMITED 2>&1
    if ($LASTEXITCODE -eq 0) {
        $run = & schtasks.exe /Run /TN $taskName 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Target is in use. Patch scheduled as task '$taskName'; it will apply after opencode exits." "WARN"
            Write-Log "Worker log: $workerLog" "WARN"
            return
        }
        Remove-ApplyTask $taskName
    }
    $fallbackArgs = "-NoProfile -NonInteractive -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$shadow`" -WaitAndReplace -WorkerConfig `"$workerConfig`""
    $proc = Start-Process -FilePath $shell -ArgumentList $fallbackArgs -WindowStyle Hidden -PassThru
    Write-Log "Target is in use. Patch queued as PID $($proc.Id); it will apply after opencode exits." "WARN"
    Write-Log "Worker log: $workerLog" "WARN"
}

function Install-PatchedFile {
    param([string]$TargetFile, [string]$TempFile, [string]$OldHash, [string]$NewHash)
    if (-not (Test-Writable $TargetFile)) { return "locked" }
    $backup = $null
    if (-not $NoBackup) {
        $backup = "$TargetFile.$($OldHash.Substring(0,12)).retrybak"
        if (-not (Test-Path -LiteralPath $backup)) {
            Copy-Item -LiteralPath $TargetFile -Destination $backup -Force
            Write-Log "Backup: $backup"
        }
    }
    $newBytes = [System.IO.File]::ReadAllBytes($TempFile)
    $fs = [System.IO.File]::Open($TargetFile, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Write, [System.IO.FileShare]::Read)
    try {
        $fs.Position = 0
        $fs.Write($newBytes, 0, $newBytes.Length)
        $fs.SetLength($newBytes.Length)
        $fs.Flush($true)
    } finally {
        $fs.Dispose()
    }
    $actual = Get-FileHashHex $TargetFile
    if ($actual -ne $NewHash) { throw "Installed file hash mismatch" }
    Remove-Item -LiteralPath $TempFile -Force -ErrorAction SilentlyContinue
    Write-Log "Patched: $TargetFile"
    return "applied"
}

function Exit-Worker {
    param([int]$Code)
    Remove-ApplyTask $TaskName
    foreach ($path in @($script:Cleanup)) {
        if (-not $path) { continue }
        try {
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force -ErrorAction Stop }
        } catch { }
    }
    exit $Code
}

function Invoke-WaitAndReplace {
    if ($WorkerConfig) {
        $cfg = [System.IO.File]::ReadAllText($WorkerConfig, [System.Text.Encoding]::UTF8) | ConvertFrom-Json
        $Target = $cfg.Target
        $Patched = $cfg.Patched
        $ExpectedHash = $cfg.ExpectedHash
        $ExpectedNewHash = $cfg.ExpectedNewHash
        $LogFile = $cfg.LogFile
        $TaskName = $cfg.TaskName
        $script:Cleanup = @($cfg.Cleanup | Where-Object { $_ })
    }
    $deadline = (Get-Date).AddHours(24)
    while ((Get-Date) -lt $deadline) {
        if (-not (Test-Path -LiteralPath $Target -PathType Leaf)) {
            Write-Log "Target disappeared: $Target" "ERROR"
            Exit-Worker 1
        }
        if (Test-Path -LiteralPath $Patched -PathType Leaf) {
            if (Test-Writable $Target) {
                try {
                    $current = Get-FileHashHex $Target
                    if ($current -eq $ExpectedNewHash) {
                        Write-Log "Already patched: $Target"
                        Remove-Item -LiteralPath $Patched -Force
                        Exit-Worker 0
                    }
                    if ($current -ne $ExpectedHash) {
                        Write-Log "Target changed since patch was prepared; refusing to overwrite: $Target" "ERROR"
                        Remove-Item -LiteralPath $Patched -Force
                        Exit-Worker 1
                    }
                    $result = Install-PatchedFile -TargetFile $Target -TempFile $Patched -OldHash $ExpectedHash -NewHash $ExpectedNewHash
                    if ($result -eq "applied") { Exit-Worker 0 }
                } catch {
                    Write-Log "Apply failed, will retry: $($_.Exception.Message)" "WARN"
                }
            }
        } else {
            Write-Log "Patched temp file missing: $Patched" "ERROR"
            Exit-Worker 1
        }
        Start-Sleep -Seconds 2
    }
    Write-Log "Timed out waiting for target to unlock: $Target" "ERROR"
    Exit-Worker 1
}

function Restore-Backup {
    param([string]$TargetFile)
    $backups = @(Get-ChildItem -LiteralPath (Split-Path -Parent $TargetFile) -Filter ((Split-Path -Leaf $TargetFile) + ".*.retrybak") -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    if ($backups.Count -eq 0) {
        Write-Log "No backup found for $TargetFile" "WARN"
        return
    }
    $backup = $backups[0]
    if (-not (Test-Writable $TargetFile)) {
        Write-Log "Cannot restore while target is in use: $TargetFile" "ERROR"
        return
    }
    Copy-Item -LiteralPath $backup.FullName -Destination $TargetFile -Force
    Write-Log "Restored $TargetFile from $($backup.FullName)"
}

if ($WaitAndReplace) {
    Invoke-WaitAndReplace
    exit 0
}

if ($MaxDelayMs -lt 1000) {
    Write-Log "MaxDelayMs must be at least 1000" "ERROR"
    exit 1
}

$candidates = Get-Candidates
if ($candidates.Count -eq 0) {
    Write-Log "opencode executable not found. Use -Path to specify it." "ERROR"
    exit 1
}

$groups = @{}
$unique = New-Object System.Collections.Generic.List[string]
foreach ($candidate in $candidates) {
    $key = Get-HardlinkKey $candidate
    if ($groups.ContainsKey($key)) { continue }
    $groups[$key] = $candidate
    $unique.Add($candidate)
}

$processed = 0
$deferred = 0
$skipped = 0

foreach ($file in $unique) {
    Write-Log "Checking: $file"
    if ($Restore) {
        Restore-Backup -TargetFile $file
        $processed++
        continue
    }

    try {
        $bytes = [System.IO.File]::ReadAllBytes($file)
    } catch {
        Write-Log "Cannot read (file is locked): $file" "WARN"
        $skipped++
        continue
    }
    $oldHash = Get-HashHex $bytes
    $text = $script:Enc.GetString($bytes)

    $isBunBinary = $text.IndexOf("---- Bun! ----", [System.StringComparison]::Ordinal) -ge 0
    if (-not $isBunBinary -and $text.IndexOf("RETRY_MAX_DELAY_NO_HEADERS", [System.StringComparison]::Ordinal) -ge 0) {
        $sourceText = [System.IO.File]::ReadAllText($file, [System.Text.Encoding]::UTF8)
        $newText = Get-SourcePatchText -Text $sourceText -MaxDelayMs $MaxDelayMs
        if ($newText -eq $sourceText) {
            Write-Log "No source changes needed: $file" "WARN"
            $skipped++
            continue
        }
        $newBytes = $script:Utf8.GetBytes($newText)
        $temp = "$file.retry-new"
        [System.IO.File]::WriteAllBytes($temp, $newBytes)
        $newHash = Get-HashHex $newBytes
        try {
            $result = Install-PatchedFile -TargetFile $file -TempFile $temp -OldHash $oldHash -NewHash $newHash
        } catch {
            Write-Log "Patch failed: $($_.Exception.Message)" "ERROR"
            $skipped++
            continue
        }
        if ($result -eq "applied") {
            Write-Log "Source patched; rebuild or restart opencode to apply: $file"
            $processed++
        } else {
            Start-ApplyWorker -TargetFile $file -TempFile $temp -OldHash $oldHash -NewHash $newHash
            $deferred++
        }
        continue
    }

    if ($text.IndexOf($script:Marker, [System.StringComparison]::Ordinal) -lt 0) {
        Write-Log "Not a supported opencode build (retry code not found): $file" "WARN"
        $skipped++
        continue
    }

    $state = Get-BinaryPatchState -Text $text -MaxDelayMs $MaxDelayMs
    $hasWork = $state.Replacements.Count -gt 0
    if (-not $hasWork) {
        if ($state.AlreadyMax -and $state.AlreadyContentFilter -and -not $state.FoundRetryCap) {
            Write-Log "Already patched: $file"
            $skipped++
        } else {
            Write-Log "Supported retry code found, but no patch points matched: $file" "WARN"
            $skipped++
        }
        continue
    }

    $newText = Apply-Replacements -Text $text -State $state
    $newBytes = $script:Enc.GetBytes($newText)
    if ($newBytes.Length -ne $bytes.Length) { throw "Patched file length changed for $file" }
    $newHash = Get-HashHex $newBytes
    $temp = "$file.retry-new"
    [System.IO.File]::WriteAllBytes($temp, $newBytes)

    $parts = New-Object System.Collections.Generic.List[string]
    if ($state.FoundNoHeader -or $state.FoundMax) { $parts.Add("max delay -> $MaxDelayMs ms") }
    if ($state.FoundRetryCap) { $parts.Add("retry limit removed") }
    if ($state.FoundContentFilter) { $parts.Add("content filter retry enabled") }
    Write-Log ("Changes: " + ($parts -join ", "))

    try {
        $result = Install-PatchedFile -TargetFile $file -TempFile $temp -OldHash $oldHash -NewHash $newHash
    } catch {
        Write-Log "Patch failed: $($_.Exception.Message)" "ERROR"
        $skipped++
        continue
    }
    if ($result -eq "applied") {
        $processed++
    } else {
        if (Test-Path -LiteralPath $temp -PathType Leaf) {
            Start-ApplyWorker -TargetFile $file -TempFile $temp -OldHash $oldHash -NewHash $newHash
            $deferred++
        } else {
            Write-Log "Could not prepare patch: $file" "ERROR"
        }
    }
}

Write-Log "Done. applied=$processed deferred=$deferred skipped=$skipped"
if ($deferred -gt 0) {
    Write-Log "Restart opencode after the running instance exits; the queued patch is applied automatically." "WARN"
}
