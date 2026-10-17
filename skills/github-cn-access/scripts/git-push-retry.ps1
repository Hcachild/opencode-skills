<#
git-push-retry.ps1 — 国内网络下 git 操作的自动重试包装

用法:
  pwsh -File git-push-retry.ps1 -Repo D:\path\to\repo
  pwsh -File git-push-retry.ps1 -Repo D:\path\to\repo -Operation fetch
  pwsh -File git-push-retry.ps1 -Repo D:\path\to\repo -Remote upstream -Branch main -MaxAttempts 8

行为:
  - 仅对"瞬时网络错误"重试（超时/连接重置/TLS/EOF 等），最多 MaxAttempts 次，间隔 5~15 秒
  - 遇到永久错误（认证失败、reject、仓库不存在等）立即停止并原样输出报错
  - HTTPS remote 自动追加 fail-fast 参数（<1KB/s 持续 30s 即中止），防止坏窗口无限挂死
  - 全程禁用交互提示（GIT_TERMINAL_PROMPT=0 / GCM_INTERACTIVE=never），适合 agent 调用
#>
param(
    [Parameter(Mandatory = $true)][string]$Repo,
    [ValidateSet('push', 'fetch', 'pull')][string]$Operation = 'push',
    [string]$Remote = 'origin',
    [string]$Branch = '',
    [int]$MaxAttempts = 5
)

$ErrorActionPreference = 'Continue'
$env:GIT_TERMINAL_PROMPT = '0'
$env:GCM_INTERACTIVE = 'never'

$transientPatterns = 'Could not connect|Recv failure|Connection was reset|Connection reset|timed out|timeout|unable to access|Connection refused|remote end hung up|Broken pipe|early EOF|unexpected disconnect|index-pack failed|TLS|schannel|EOF'
$permanentPatterns = 'rejected|non-fast-forward|fetch first|Permission denied|Authentication failed|could not read Username|Repository not found|does not exist|protected branch|pre-receive hook declined|cannot lock ref'

if (-not (Test-Path -LiteralPath (Join-Path $Repo '.git'))) {
    "[github-retry] 错误: $Repo 不是 git 仓库"
    exit 2
}

$remoteUrl = (git -C $Repo remote get-url $Remote 2>$null)
if (-not $remoteUrl) {
    "[github-retry] 错误: 仓库没有名为 $Remote 的 remote"
    exit 2
}
"[github-retry] repo=$Repo op=$Operation remote=$Remote ($remoteUrl) max=$MaxAttempts"

for ($i = 1; $i -le $MaxAttempts; $i++) {
    $gitArgs = @('-C', $Repo)
    if ($remoteUrl -match '^https://') {
        $gitArgs += @('-c', 'http.lowSpeedLimit=1000', '-c', 'http.lowSpeedTime=30')
    }
    $gitArgs += $Operation
    $gitArgs += $Remote
    if ($Branch) { $gitArgs += $Branch }

    $out = & git @gitArgs 2>&1
    $code = $LASTEXITCODE
    $joined = ($out | Out-String)

    if ($code -eq 0) {
        "[github-retry] attempt ${i}/${MaxAttempts}: OK"
        $out | ForEach-Object { "    $_" }
        exit 0
    }

    if ($joined -match $permanentPatterns) {
        "[github-retry] 永久错误（不重试），原始输出:"
        $out | ForEach-Object { "    $_" }
        exit 1
    }

    $kind = if ($joined -match $transientPatterns) { 'transient' } else { 'unknown' }
    "[github-retry] attempt ${i}/${MaxAttempts} failed [$kind]:"
    $out | Select-Object -First 3 | ForEach-Object { "    $_" }

    if ($i -lt $MaxAttempts) {
        $wait = 5 + (Get-Random -Maximum 11)
        "[github-retry] waiting ${wait}s (网络为窗口式阻断，换个时机重试)..."
        Start-Sleep -Seconds $wait
    }
}

"[github-retry] $MaxAttempts 次均失败；如持续失败请检查 SSH-443 通道（ssh -T git@github.com）或刷新 IP（refresh-github-ssh-ip.ps1）"
exit 1
