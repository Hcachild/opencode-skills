[CmdletBinding(DefaultParameterSetName = 'list')]
param(
    [Parameter(ParameterSetName = 'list')]
    [switch]$List,

    [Parameter(ParameterSetName = 'view', Mandatory = $true)]
    [Parameter(ParameterSetName = 'export', Mandatory = $true)]
    [string]$AgentId,

    [Parameter(ParameterSetName = 'search')]
    [string]$Search,

    [Parameter(ParameterSetName = 'export', Mandatory = $true)]
    [string]$Export,

    [int]$Limit = 20,
    [switch]$IncludeThinking
)

$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

function Get-CursorDb {
    $candidates = @()
    if ($env:APPDATA) { $candidates += (Join-Path $env:APPDATA 'Cursor\User\globalStorage\state.vscdb') }
    if ($env:HOME) {
        $candidates += (Join-Path $env:HOME 'Library/Application Support/Cursor/User/globalStorage/state.vscdb')
        $candidates += (Join-Path $env:HOME '.config/Cursor/User/globalStorage/state.vscdb')
    }
    foreach ($p in $candidates) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    throw "未找到 Cursor 数据库 (state.vscdb)"
}

function Get-Sqlite {
    $cmd = Get-Command sqlite3 -ErrorAction SilentlyContinue
    if (-not $cmd) { throw '未找到 sqlite3，请先安装（https://sqlite.org/download.html）' }
    return $cmd.Source
}

function Invoke-SqliteFile {
    param([string]$Db, [string]$SqlFile)
    $sqlite = Get-Sqlite
    $out = & $sqlite $Db ".read $SqlFile" 2>&1
    if ($LASTEXITCODE -ne 0) { throw "sqlite3 执行失败: $out" }
}

function New-TempSql {
    param([string]$Sql)
    $tmp = Join-Path ([System.IO.Path]::GetTempPath()) 'cursor-chat-skill'
    New-Item -ItemType Directory -Force -Path $tmp | Out-Null
    $file = Join-Path $tmp ("sql_" + [guid]::NewGuid().ToString('N') + ".sql")
    $enc = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($file, $Sql, $enc)
    return $file
}

function Read-TempFile {
    param([string]$File)
    if (-not (Test-Path -LiteralPath $File)) { return @() }
    Write-Output -NoEnumerate @(Get-Content -LiteralPath $File -Encoding UTF8)
}

function Get-EpochLocal {
    param([long]$Ms)
    if (-not $Ms) { return '' }
    return [DateTimeOffset]::FromUnixTimeMilliseconds($Ms).ToLocalTime().ToString('yyyy-MM-dd HH:mm:ss')
}

function Format-Time {
    param([string]$Iso)
    try {
        $dt = [DateTime]::Parse($Iso).ToLocalTime()
        return $dt.ToString('HH:mm:ss')
    } catch { return '' }
}

function Get-BubbleMeta {
    param([string]$Db, [string]$ComposerId)
    $sql = @"
.output '$env:TEMP\cursor-chat-skill\meta_out.txt'
SELECT json_extract(value, '$.name'),
       json_extract(value, '$.subtitle'),
       json_extract(value, '$.workspaceIdentifier.uri.fsPath'),
       json_extract(value, '$.modelConfig.modelName'),
       json_extract(value, '$.contextUsagePercent'),
       json_extract(value, '$.contextTokensUsed'),
       json_extract(value, '$.contextTokenLimit'),
       json_extract(value, '$.filesChangedCount'),
       json_extract(value, '$.createdAt'),
       json_extract(value, '$.lastUpdatedAt'),
       json_extract(value, '$.status')
FROM cursorDiskKV
WHERE key = 'composerData:$ComposerId';
.output stdout
"@
    $tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) 'cursor-chat-skill'
    New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
    $sf = New-TempSql $sql
    Invoke-SqliteFile -Db $Db -SqlFile $sf
    $row = Read-TempFile (Join-Path $tmpDir 'meta_out.txt')
    if (-not $row) { return $null }
    $f = $row[0] -split '\|'
    return [pscustomobject]@{
        Name            = $f[0].Trim()
        Subtitle        = $f[1].Trim()
        Workspace       = $f[2].Trim()
        Model           = $f[3].Trim()
        ContextPercent  = $f[4].Trim()
        ContextTokens   = $f[5].Trim()
        ContextLimit    = $f[6].Trim()
        FilesChanged    = $f[7].Trim()
        CreatedAt       = Get-EpochLocal ([long]$f[8])
        UpdatedAt       = Get-EpochLocal ([long]$f[9])
        Status          = $f[10].Trim()
    }
}

function Get-Bubbles {
    param([string]$Db, [string]$ComposerId)
    $tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) 'cursor-chat-skill'
    New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null
    $sql = @"
.output '$tmpDir\bubbles_out.txt'
SELECT value FROM cursorDiskKV
WHERE key LIKE 'bubbleId:${ComposerId}:%'
ORDER BY json_extract(value, '$.createdAt');
.output stdout
"@
    $sf = New-TempSql $sql
    Invoke-SqliteFile -Db $Db -SqlFile $sf
    $lines = Read-TempFile (Join-Path $tmpDir 'bubbles_out.txt')
    $result = @()
    foreach ($line in $lines) {
        if (-not $line) { continue }
        try {
            $b = $line | ConvertFrom-Json
            $result += $b
        } catch { }
    }
    return $result
}

function Format-Bubble {
    param($B, [bool]$ShowThinking)
    $time = Format-Time $B.createdAt
    if ($B.type -eq 1) {
        if (-not $B.text) { return $null }
        $lines = @("[User $time]")
        $lines += ($B.text -split "`n" | ForEach-Object { "  $_" })
        return ($lines -join "`n")
    }
    if ($B.type -eq 2) {
        $out = @()
        if ($B.capabilityType -eq 15 -and $B.toolFormerData) {
            $t = $B.toolFormerData
            $args = ''
            if ($t.params) {
                try { $p = $t.params | ConvertFrom-Json; $args = ($p.PSObject.Properties | ForEach-Object { "$($_.Name)=$($_.Value)" }) -join ', ' } catch { }
            }
            $status = if ($t.status) { $t.status } else { 'unknown' }
            $out += "[Tool $time] $($t.name)($args) -> $status"
        }
        elseif ($B.capabilityType -eq 30 -and $B.thinking -and $ShowThinking) {
            $out += "[Thinking $time]"
            $out += (($B.thinking.text -split "`n") | ForEach-Object { "  $_" })
        }
        elseif ($B.text) {
            $out += "[Agent $time]"
            $out += ($B.text -split "`n" | ForEach-Object { "  $_" })
        }
        if ($out.Count -eq 0) { return $null }
        return ($out -join "`n")
    }
    return $null
}

# ---------- 入口 ----------
$db = Get-CursorDb
$tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) 'cursor-chat-skill'
New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

switch ($PSCmdlet.ParameterSetName) {
    'list' {
        $sql = @"
.output '$tmpDir\list_out.txt'
SELECT composerId,
       coalesce(json_extract(value, '$.name'), ''),
       coalesce(json_extract(value, '$.workspaceIdentifier.uri.fsPath'), ''),
       datetime(json_extract(value, '$.lastUpdatedAt') / 1000, 'unixepoch', 'localtime')
FROM composerHeaders
ORDER BY json_extract(value, '$.lastUpdatedAt') DESC
LIMIT $Limit;
.output stdout
"@
        $sf = New-TempSql $sql
        Invoke-SqliteFile -Db $Db -SqlFile $sf
        $rows = Read-TempFile (Join-Path $tmpDir 'list_out.txt')
        if (-not $rows) { Write-Output '没有找到任何 Cursor 会话。'; return }
        Write-Output ("{0,-38} | {1,-40} | {2,-24} | {3}" -f 'AgentId', '标题', '工作区', '更新时间')
        Write-Output ('-' * 130)
        foreach ($r in $rows) {
            $c = $r -split '\|', 4
            Write-Output ("{0,-38} | {1,-40} | {2,-24} | {3}" -f $c[0].Trim(), $c[1].Trim(), $c[2].Trim(), $c[3].Trim())
        }
        Write-Output ''
        Write-Output "共 $($rows.Count) 条。查看详情: -AgentId <id>; 搜索: -Search <关键词>"
    }

    'view' {
        $meta = Get-BubbleMeta -Db $db -ComposerId $AgentId
        if (-not $meta) {
            $sql = @"
.output '$tmpDir\exists_out.txt'
SELECT COUNT(*) FROM composerHeaders WHERE composerId = '$AgentId';
.output stdout
"@
            $sf = New-TempSql $sql
            Invoke-SqliteFile -Db $Db -SqlFile $sf
            $n = (Read-TempFile (Join-Path $tmpDir 'exists_out.txt'))[0]
            if ($n -and [int]$n -gt 0) { Write-Output "会话 $AgentId 存在但缺少 composerData(可能未完成或已清理)。"; return }
            Write-Output "未找到 AgentId: $AgentId。先用 -List 查看可用的会话。"
            return
        }
        Write-Output ('===== ' + $meta.Name + " ($AgentId) =====")
        Write-Output ("工作区: {0} | 模型: {1} | 状态: {2}" -f $meta.Workspace, $meta.Model, $meta.Status)
        if ($meta.Subtitle) { Write-Output ("副标题: {0}" -f $meta.Subtitle) }
        if ($meta.ContextPercent -ne $null -and $meta.ContextPercent -ne '') {
            Write-Output ("上下文: {0}% ({1}/{2} tokens) | 文件变更: {3}" -f $meta.ContextPercent, $meta.ContextTokens, $meta.ContextLimit, $meta.FilesChanged)
        }
        Write-Output ("创建: {0} | 更新: {1}" -f $meta.CreatedAt, $meta.UpdatedAt)
        Write-Output ('-' * 70)

        $bubbles = Get-Bubbles -Db $db -ComposerId $AgentId
        if (-not $bubbles) { Write-Output '该会话没有消息内容。'; return }
        foreach ($b in $bubbles) {
            $text = Format-Bubble -B $b -ShowThinking $IncludeThinking
            if ($text) { Write-Output $text; Write-Output '' }
        }
    }

    'search' {
        $escaped = $Search.Replace("'", "''")
        $sql = @"
.output '$tmpDir\search_out.txt'
SELECT composerId, coalesce(json_extract(value, '$.name'), '') AS n
FROM composerHeaders
WHERE lower(value) LIKE lower('%$escaped%')
ORDER BY json_extract(value, '$.lastUpdatedAt') DESC;
.output stdout
"@
        $sf = New-TempSql $sql
        Invoke-SqliteFile -Db $Db -SqlFile $sf
        $hits = @{}
        foreach ($r in (Read-TempFile (Join-Path $tmpDir 'search_out.txt'))) {
            $c = $r -split '\|', 2
            $hits[$c[0].Trim()] = "标题: $($c[1].Trim())"
        }
        $sql2 = @"
.output '$tmpDir\search_bubble_out.txt'
SELECT substr(key, 10, 36) AS cid, substr(value, 1, 400)
FROM cursorDiskKV
WHERE key LIKE 'bubbleId:%' AND value LIKE '%$escaped%';
.output stdout
"@
        $sf2 = New-TempSql $sql2
        Invoke-SqliteFile -Db $Db -SqlFile $sf2
        foreach ($r in (Read-TempFile (Join-Path $tmpDir 'search_bubble_out.txt'))) {
            $c = $r -split '\|', 2
            $cid = $c[0].Trim()
            if (-not $hits.ContainsKey($cid)) { $hits[$cid] = '' }
        }
        if ($hits.Count -eq 0) { Write-Output "没有找到包含 ""$Search"" 的会话。"; return }
        Write-Output "搜索 ""$Search"" 命中 $($hits.Count) 个会话:"
        Write-Output ''
        foreach ($k in ($hits.Keys | Sort-Object)) {
            Write-Output "$k"
            if ($hits[$k]) { Write-Output "  $($hits[$k])" }
            Write-Output "  查看: -AgentId $k"
            Write-Output ''
        }
    }

    'export' {
        if (-not $AgentId) { Write-Output '请指定 AgentId: -AgentId <id> -Export <目录>'; return }
        if (-not $Export) { Write-Output '请指定导出目录: -Export <目录>'; return }
        $outDir = $Export
        New-Item -ItemType Directory -Force -Path $outDir | Out-Null
        $bubbles = Get-Bubbles -Db $db -ComposerId $AgentId
        $sb = New-Object System.Text.StringBuilder
        foreach ($b in $bubbles) {
            $text = Format-Bubble -B $b -ShowThinking $true
            if ($text) { [void]$sb.AppendLine($text); [void]$sb.AppendLine('') }
        }
        $txtPath = Join-Path $outDir '对话.txt'
        $enc = New-Object System.Text.UTF8Encoding($false)
        [System.IO.File]::WriteAllText($txtPath, $sb.ToString(), $enc)

        $sql = @"
.output '$tmpDir\export_data.json'
SELECT value FROM cursorDiskKV WHERE key = 'composerData:$AgentId';
.output '$tmpDir\export_bubbles.txt'
SELECT key, value FROM cursorDiskKV WHERE key LIKE 'bubbleId:${AgentId}:%';
.output stdout
"@
        $sf = New-TempSql $sql
        Invoke-SqliteFile -Db $Db -SqlFile $sf
        $dataJson = (Read-TempFile (Join-Path $tmpDir 'export_data.json')) -join "`n"
        [System.IO.File]::WriteAllText((Join-Path $outDir 'composerData.json'), $dataJson, $enc)
        $bubbleDir = Join-Path $outDir 'bubbles'
        New-Item -ItemType Directory -Force -Path $bubbleDir | Out-Null
        foreach ($line in (Read-TempFile (Join-Path $tmpDir 'export_bubbles.txt'))) {
            if (-not $line) { continue }
            $idx = $line.IndexOf('|')
            if ($idx -le 0) { continue }
            $key = $line.Substring(0, $idx)
            $val = $line.Substring($idx + 1)
            $name = ($key -replace ':', '_') + '.json'
            [System.IO.File]::WriteAllText((Join-Path $bubbleDir $name), $val, $enc)
        }
        Write-Output "已导出会话 $AgentId 到:"
        Write-Output "  $txtPath"
        Write-Output "  $(Join-Path $outDir 'composerData.json')"
        Write-Output "  $bubbleDir"
    }
}