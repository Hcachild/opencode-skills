[CmdletBinding()]
param(
    [string]$Path,
    [switch]$Restore,
    [switch]$CloseApp,
    [switch]$NoRelaunch,
    [switch]$NoBackup
)

$ErrorActionPreference = "Stop"
$script:Utf8 = New-Object System.Text.UTF8Encoding($false)
$script:DesktopExeName = "OpenCode.exe"

function Write-Status {
    param([string]$Message, [string]$Level = "INFO")
    $line = "{0} [{1}] {2}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Level, $Message
    $color = if ($Level -eq "ERROR") { "Red" } elseif ($Level -eq "WARN") { "Yellow" } else { "Gray" }
    Write-Host $line -ForegroundColor $color
}

function Get-FileHashHex {
    param([byte[]]$Bytes)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return ([System.BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace("-", "")
    } finally {
        $sha.Dispose()
    }
}

function Get-DesktopApp {
    if ($Path) {
        $p = $Path
        if (Test-Path -LiteralPath $p -PathType Leaf) { return $p }
        if (Test-Path -LiteralPath (Join-Path $p "resources\app.asar") -PathType Leaf) { return (Join-Path $p "resources\app.asar") }
        throw "app.asar not found: $Path"
    }
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA "Programs\@opencode-aidesktop\resources\app.asar"),
        (Join-Path $env:LOCALAPPDATA "@opencode-aidesktop\resources\app.asar"),
        (Join-Path $env:LOCALAPPDATA "Programs\OpenCode\resources\app.asar"),
        (Join-Path $env:LOCALAPPDATA "OpenCode\resources\app.asar")
    )
    if ($env:ProgramFiles) { $candidates += (Join-Path $env:ProgramFiles "@opencode-aidesktop\resources\app.asar") }
    if (${env:ProgramFiles(x86)}) { $candidates += (Join-Path ${env:ProgramFiles(x86)} "@opencode-aidesktop\resources\app.asar") }
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c -PathType Leaf) { return $c }
    }
    throw "OpenCode desktop app.asar not found"
}

function Get-DesktopExe {
    param([string]$AsarPath)
    $resources = Split-Path -Parent $AsarPath
    $root = Split-Path -Parent $resources
    $exe = Join-Path $root "OpenCode.exe"
    if (Test-Path -LiteralPath $exe -PathType Leaf) { return $exe }
    return $null
}

function Stop-DesktopApp {
    param([string]$Exe)
    $procs = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $Exe })
    if ($procs.Count -eq 0) { return $false }
    Write-Status "Closing $($procs.Count) desktop process(es)..." "WARN"
    foreach ($p in $procs) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    for ($i = 0; $i -lt 50; $i++) {
        Start-Sleep -Milliseconds 200
        if (@(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $Exe }).Count -eq 0) { break }
    }
    $remaining = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $Exe }).Count
    if ($remaining -gt 0) { throw "Desktop app is still running ($remaining process(es))" }
    return $true
}

function Start-DesktopApp {
    param([string]$Exe)
    if (-not $Exe) { return }
    Write-Status "Starting desktop app..."
    Start-Process -FilePath $Exe | Out-Null
    Start-Sleep -Seconds 8
    $count = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $Exe }).Count
    if ($count -gt 0) {
        Write-Status "Desktop app is running ($count processes)."
    } else {
        Write-Status "Desktop app did not stay running." "ERROR"
    }
}

function Get-AsarInfo {
    param([byte[]]$Bytes)
    if ($Bytes.Length -lt 32) { throw "app.asar is too small" }
    $jsonLen = [System.BitConverter]::ToUInt32($Bytes, 12)
    if ($jsonLen -le 0 -or (16 + $jsonLen) -gt $Bytes.Length) { throw "Invalid asar header" }
    $jsonText = $script:Utf8.GetString($Bytes, 16, $jsonLen)
    if (-not $jsonText.StartsWith('{"files"')) { throw "Unrecognized asar header" }
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

function Get-ChunkText {
    param([byte[]]$Bytes, $Entry)
    return $script:Utf8.GetString($Bytes, [int]$Entry.Offset, [int]$Entry.Size)
}

function Add-SameLengthReplacement {
    param([string]$Text, [string]$Old, [string]$New, [string]$Label)
    if ($Old.Length -ne $New.Length) {
        throw "$Label replacement length mismatch: $($Old.Length) != $($New.Length)"
    }
    $count = ([regex]::Matches($Text, [regex]::Escape($Old))).Count
    if ($count -eq 0) { return [pscustomobject]@{ Text = $Text; Count = 0 } }
    $updated = $Text.Replace($Old, $New)
    if ($updated.Length -ne $Text.Length) { throw "$Label changed chunk length" }
    return [pscustomobject]@{ Text = $updated; Count = $count }
}

function Patch-DesktopChunk {
    param([string]$Text)
    $original = $Text
    $details = New-Object System.Collections.Generic.List[string]

    $pattern = 'RETRY_MAX_DELAY_NO_HEADERS(\s*=\s*)3e4'
    $m = [regex]::Match($Text, $pattern)
    if ($m.Success) {
        $new = "RETRY_MAX_DELAY_NO_HEADERS" + $m.Groups[1].Value + "3e5"
        $Text = $Text.Substring(0, $m.Index) + $new + $Text.Substring($m.Index + $m.Length)
        $details.Add("RETRY_MAX_DELAY_NO_HEADERS=3e5")
    }

    $pattern = 'RETRY_MAX_DELAY(\s*=\s*)2147483647'
    $m = [regex]::Match($Text, $pattern)
    if ($m.Success) {
        $new = "RETRY_MAX_DELAY" + $m.Groups[1].Value + "3e5       "
        if ($new.Length -ne $m.Length) { throw "RETRY_MAX_DELAY replacement length mismatch" }
        $Text = $Text.Substring(0, $m.Index) + $new + $Text.Substring($m.Index + $m.Length)
        $details.Add("RETRY_MAX_DELAY=300000")
    }

    $pattern = 'if\s*\(\s*[A-Za-z_$][\w$]*\.attempt\s*>\s*RETRY_MAX_RETRIES\s*\)'
    $m = [regex]::Match($Text, $pattern)
    if ($m.Success) {
        $new = "if (0)" + (" " * ($m.Length - 6))
        $Text = $Text.Substring(0, $m.Index) + $new + $Text.Substring($m.Index + $m.Length)
        $details.Add("retry limit removed")
    }

    $pattern = 'return typeof (?<p>[A-Za-z_$][\w$]*) === "string" && RETRYABLE_MESSAGE_PATTERNS\.some\(\((?<pat>[A-Za-z_$][\w$]*)\) => \k<pat>\.test\(\k<p>\)\);'
    $m = [regex]::Match($Text, $pattern)
    if ($m.Success) {
        $p = $m.Groups["p"].Value
        $pat = $m.Groups["pat"].Value
        $base = "return RETRYABLE_MESSAGE_PATTERNS.some($pat => $pat.test($p)) || "
        $checks = @(
            "/content.?f/i.test($p)",
            "/content.f/i.test($p)",
            "/content f/i.test($p)",
            "/content/i.test($p)"
        )
        $new = $null
        foreach ($check in $checks) {
            $candidate = $base + $check + ";"
            if ($candidate.Length -le $m.Length) {
                $new = $candidate.Substring(0, $candidate.Length - 1) + (" " * ($m.Length - $candidate.Length)) + ";"
                break
            }
        }
        if (-not $new) { throw "Cannot fit content filter check into retryable helper" }
        $Text = $Text.Substring(0, $m.Index) + $new + $Text.Substring($m.Index + $m.Length)
        $details.Add("content filter retry enabled")
    }

    if ($Text.Length -ne $original.Length) { throw "Patched chunk length changed" }
    return [pscustomobject]@{ Text = $Text; Details = $details; Changed = ($Text -ne $original) }
}

function Test-PatchedChunk {
    param([string]$Text)
    $okNoHeader = $Text -match 'RETRY_MAX_DELAY_NO_HEADERS\s*=\s*3e5'
    $okMax = $Text -match 'RETRY_MAX_DELAY\s*=\s*3e5'
    $okCap = $Text -notmatch 'if\s*\(\s*[A-Za-z_$][\w$]*\.attempt\s*>\s*RETRY_MAX_RETRIES\s*\)'
    $okContent = $Text.Contains('/content.?f/i')
    return [pscustomobject]@{
        Ok = ($okNoHeader -and $okMax -and $okCap -and $okContent)
        Detail = "noHeader=$okNoHeader max=$okMax capRemoved=$okCap content=$okContent"
    }
}

$asar = Get-DesktopApp
$desktopExe = Get-DesktopExe $asar
Write-Status "app.asar: $asar"
if ($desktopExe) { Write-Status "desktop:  $desktopExe" }

if ($Restore) {
    $backups = @(Get-ChildItem -LiteralPath (Split-Path -Parent $asar) -Filter ((Split-Path -Leaf $asar) + ".*.retrybak") -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending)
    if ($backups.Count -eq 0) { throw "No app.asar backup found" }
    if ($desktopExe) { [void](Stop-DesktopApp $desktopExe) }
    Copy-Item -LiteralPath $backups[0].FullName -Destination $asar -Force
    Write-Status "Restored app.asar from $($backups[0].FullName)"
    if ($desktopExe -and -not $NoRelaunch) { Start-DesktopApp $desktopExe }
    exit 0
}

$bytes = [System.IO.File]::ReadAllBytes($asar)
$oldHash = Get-FileHashHex $bytes
$info = Get-AsarInfo $bytes
$textLatin = [System.Text.Encoding]::GetEncoding(28591).GetString($bytes)
$target = $textLatin.IndexOf("RETRY_MAX_RETRIES", [System.StringComparison]::Ordinal)
if ($target -lt 0) { throw "Retry code not found in app.asar" }
$entry = Find-AsarEntry -Node $info.Header -Prefix "" -Target $target -DataStart $info.DataStart
if (-not $entry) { throw "Could not locate the JS chunk containing retry code" }
Write-Status "retry chunk: $($entry.Path) (size $($entry.Size))"

$chunkText = Get-ChunkText $bytes $entry
$patchResult = Patch-DesktopChunk $chunkText
$check = Test-PatchedChunk $patchResult.Text
if (-not $check.Ok) { throw "Patch verification failed: $($check.Detail)" }

if (-not $patchResult.Changed) {
    Write-Status "Already patched: $asar"
    if ($desktopExe -and -not $NoRelaunch) {
        $running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $desktopExe }).Count
        if ($running -eq 0) { Start-DesktopApp $desktopExe }
    }
    exit 0
}

if ($desktopExe) {
    $running = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq $desktopExe }).Count
    if ($running -gt 0 -and -not $CloseApp) {
        throw "Desktop app is running. Re-run with -CloseApp (or close it manually)."
    }
    if ($running -gt 0) { [void](Stop-DesktopApp $desktopExe) }
}

$newChunkBytes = $script:Utf8.GetBytes($patchResult.Text)
if ($newChunkBytes.Length -ne $entry.Size) { throw "Patched chunk size changed" }
$newBytes = [byte[]]$bytes.Clone()
[Array]::Copy($newChunkBytes, 0, $newBytes, [int]$entry.Offset, $newChunkBytes.Length)
$newHash = Get-FileHashHex $newBytes

$replaceBackup = $null
if (-not $NoBackup) {
    $backup = "$asar.$($oldHash.Substring(0,12)).retrybak"
    if (-not (Test-Path -LiteralPath $backup)) {
        Copy-Item -LiteralPath $asar -Destination $backup -Force
        Write-Status "Backup: $backup"
    }
    $replaceBackup = $backup
} else {
    $replaceBackup = "$asar.replace-backup"
}

$temp = "$asar.retry-new"
[System.IO.File]::WriteAllBytes($temp, $newBytes)
try {
    [System.IO.File]::Replace($temp, $asar, $replaceBackup)
} finally {
    if ($NoBackup -and $replaceBackup -and (Test-Path -LiteralPath $replaceBackup)) {
        Remove-Item -LiteralPath $replaceBackup -Force -ErrorAction SilentlyContinue
    }
}
$installedHash = Get-FileHashHex ([System.IO.File]::ReadAllBytes($asar))
if ($installedHash -ne $newHash) { throw "Installed app.asar hash mismatch" }
Write-Status ("Patched: " + ($patchResult.Details -join ", "))

$verifyBytes = [System.IO.File]::ReadAllBytes($asar)
$verifyInfo = Get-AsarInfo $verifyBytes
$verifyEntry = Find-AsarEntry -Node $verifyInfo.Header -Prefix "" -Target ($target) -DataStart $verifyInfo.DataStart
if (-not $verifyEntry) { throw "Patched chunk not found" }
$verifyText = Get-ChunkText $verifyBytes $verifyEntry
$verifyCheck = Test-PatchedChunk $verifyText
if (-not $verifyCheck.Ok) { throw "Post-patch verification failed: $($verifyCheck.Detail)" }

if (Get-Command node -ErrorAction SilentlyContinue) {
    $verifyFile = "$asar.verify.mjs"
    [System.IO.File]::WriteAllText($verifyFile, $verifyText, $script:Utf8)
    try {
        & node --check $verifyFile 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "node --check failed for patched chunk" }
        Write-Status "Syntax check: OK"
    } finally {
        Remove-Item -LiteralPath $verifyFile -Force -ErrorAction SilentlyContinue
    }
}

if ($desktopExe -and -not $NoRelaunch) { Start-DesktopApp $desktopExe }
Write-Status "Done."
