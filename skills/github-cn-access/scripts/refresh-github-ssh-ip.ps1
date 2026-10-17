<#
refresh-github-ssh-ip.ps1 — 刷新 GitHub SSH-443 通道的固定 IP

用法:
  pwsh -File refresh-github-ssh-ip.ps1            # 自动检测并更新（含备份）
  pwsh -File refresh-github-ssh-ip.ps1 -DryRun    # 只预览，不改动

流程:
  1) 通过 AliDNS 明文 DoH 接口解析 ssh.github.com 的 A 记录（不受 DNS 污染/SNI 阻断影响）
  2) 对每个候选 IP 做 TCP 443 连通性测速，选最快可用的
  3) 更新 ~/.ssh/config 中 Host github.com 块的 HostName（自动备份 config）
  4) 确保 known_hosts 有 [IP]:443 条目（复用 GitHub 官方 ed25519 host key，指纹
     SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU）
  5) 用 ssh -o BatchMode=yes -T git@github.com 验证
#>
param(
    [switch]$DryRun
)

$ErrorActionPreference = 'Continue'
$sshDir = Join-Path $env:USERPROFILE '.ssh'
$configPath = Join-Path $sshDir 'config'
$knownHostsPath = Join-Path $sshDir 'known_hosts'
$githubHostKey = 'ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl'

# --- 1) DoH 解析 ---
"[1/5] 通过 AliDNS 解析 ssh.github.com ..."
$resp = $null
foreach ($attempt in 1..3) {
    try {
        $resp = Invoke-RestMethod -Uri 'http://223.5.5.5/resolve?name=ssh.github.com&type=A' -TimeoutSec 10
        if ($resp.Answer) { break }
    } catch { Start-Sleep -Seconds 2 }
}
$candidates = @($resp.Answer | Where-Object { $_.type -eq 1 } | ForEach-Object { $_.data } | Select-Object -Unique)
if (-not $candidates) { "[github-refresh] 解析失败：拿不到任何 IP，稍后再试"; exit 1 }
"[github-refresh] 候选 IP: $($candidates -join ', ')"

# --- 2) 测速 ---
"[2/5] TCP 443 连通性测速 ..."
function Test-Tcp([string]$ip, [int]$timeoutMs = 4000) {
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $task = $client.ConnectAsync($ip, 443)
        if ($task.Wait($timeoutMs)) {
            $sw.Stop(); $client.Close()
            return [pscustomobject]@{ Ip = $ip; Ok = $true; Ms = [math]::Round($sw.Elapsed.TotalMilliseconds) }
        }
        $sw.Stop(); $client.Close()
    } catch { }
    return [pscustomobject]@{ Ip = $ip; Ok = $false; Ms = 999999 }
}
$probed = foreach ($ip in $candidates) {
    $r1 = Test-Tcp $ip; $r2 = Test-Tcp $ip; $r3 = Test-Tcp $ip
    $best = $r1, $r2, $r3 | Where-Object Ok | Sort-Object Ms | Select-Object -First 1
    if ($best) { $best } else { [pscustomobject]@{ Ip = $ip; Ok = $false; Ms = 999999 } }
}
$probed | ForEach-Object { "[github-refresh]   $($_.Ip) : $(if($_.Ok){"OK $($_.Ms)ms"}else{'TIMEOUT'})" }
$bestIp = ($probed | Where-Object Ok | Sort-Object Ms | Select-Object -First 1).Ip
if (-not $bestIp) { "[github-refresh] 所有候选 IP 均不可达（可能处于坏窗口），1~5 分钟后重试；不作为即保持原配置"; exit 1 }
"[github-refresh] 选定: $bestIp"

# --- 3) 更新 ssh config ---
"[3/5] 更新 ~/.ssh/config ..."
if (-not (Test-Path -LiteralPath $configPath)) { "[github-refresh] 找不到 $configPath，请先按 references/setup-ssh-443.md 配置"; exit 1 }
$config = Get-Content -LiteralPath $configPath -Raw
if ($config -notmatch 'Host\s+github\.com') { "[github-refresh] config 中无 'Host github.com' 块，请先按 setup 指南添加"; exit 1 }
$pattern = '(Host\s+github\.com\b[\s\S]*?HostName\s+)([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)'
$currentIp = ([regex]::Match($config, $pattern)).Groups[2].Value
if ($currentIp -eq $bestIp) {
    "[github-refresh] 当前已是 $bestIp，无需更新"
} elseif ($DryRun) {
    "[github-refresh] (DryRun) 将把 HostName $currentIp -> $bestIp"
} else {
    $backup = "$configPath.bak-$(Get-Date -Format yyyyMMdd-HHmmss)"
    Copy-Item -LiteralPath $configPath -Destination $backup -Force
    $newConfig = [regex]::Replace($config, $pattern, "`${1}$bestIp", 1)
    [System.IO.File]::WriteAllText($configPath, $newConfig, [System.Text.UTF8Encoding]::new($false))
    "[github-refresh] 已更新: $currentIp -> $bestIp (备份: $backup)"
}

# --- 4) known_hosts ---
"[4/5] 校验 known_hosts ..."
$entryName = "[$bestIp]:443"
$kh = if (Test-Path -LiteralPath $knownHostsPath) { Get-Content -LiteralPath $knownHostsPath -Raw } else { '' }
if ($kh -match [regex]::Escape($entryName)) {
    "[github-refresh] $entryName 已存在"
} elseif ($DryRun) {
    "[github-refresh] (DryRun) 将追加 $entryName 条目"
} else {
    [System.IO.File]::AppendAllText($knownHostsPath, "`n$entryName $githubHostKey`n", [System.Text.UTF8Encoding]::new($false))
    "[github-refresh] 已追加 $entryName (GitHub 官方 ed25519 host key)"
}

# --- 5) 验证 ---
"[5/5] 验证 ..."
if ($DryRun) { "[github-refresh] (DryRun) 跳过验证"; exit 0 }
$sw = [System.Diagnostics.Stopwatch]::StartNew()
$result = ssh -o BatchMode=yes -o ConnectTimeout=15 -T git@github.com 2>&1
$sw.Stop()
"[github-refresh] ssh -T -> $([math]::Round($sw.Elapsed.TotalSeconds,1))s : $($result | Select-Object -First 1)"
