---
name: github-cn-access
description: Use when GitHub 推送/拉取/克隆在国内网络失败或反复超时（Could not connect、Recv failure、Connection reset、TLS 卡死、要重试很多遍才通），或需要配置/修复 GitHub 的 SSH over 443 稳定通道、刷新 ssh.github.com 的 IP、给 git 加自动重试与 fail-fast 防挂死。triggers（触发词）：github 推送失败、git push 超时、github 打不开、clone 失败、ssh.github.com、443 端口、重试才通、github 加速。
license: MIT
---

# GitHub CN Access（国内网络稳定推送 / 自动重试 / SSH-443 通道）

把「国内网络访问 GitHub 时断时续、push 要重试很多遍」处理成一套可靠、可自动化的流程。

## 根因认知（先理解再动手）

1. **阻断是"窗口式"的**：好窗口里一切正常（HTTPS 大推送也能过，只是慢）；坏窗口里 TCP 超时（~21s 挂死）、TLS 握手卡死、传输中途 reset。同一天内两种窗口会反复切换。
2. **DNS 污染是叠加变量**：本地/运营商 DNS 对 `github.com`、`ssh.github.com` 常返回混杂/虚假 A 记录，客户端挑到坏 IP 就挂死。**直连真实 IP 的成功率远高于走域名**。
3. **HTTPS+SNI 是最受伤的路径**（github.com:443 及 TLS 特征明显）；**SSH over 443（ssh.github.com）最稳**，且 SSH 协议几乎没有可拦截的明文特征。
4. **git 默认没有超时**：坏窗口时 push 会挂死 5 分钟以上才报错。**必须加 fail-fast 参数 + 自动重试**，否则 agent 会「看起来卡住」。

## Agent 快速协议（遇到 git 网络错误时）

按顺序执行，不要过早放弃、也不要死循环：

1. **识别**：`Could not connect` / `Recv failure: Connection was reset` / `timeout` / `TLS` / `Connection reset` 等 → 网络抽风，可自动重试。
2. **自动重试**：最多 **5 次**，间隔 **5~15 秒**（网络是窗口式的，换个时机往往就通）。推荐直接用本 skill 脚本：
   `pwsh -File scripts/git-push-retry.ps1 -Repo <仓库路径>`（支持 `-Operation fetch/pull`，只对瞬时错误重试，遇到认证/reject 类永久错误立即停止并原样报错）。
3. **加 fail-fast 防挂死**（HTTPS remote 时）：
   `git -c http.lowSpeedLimit=1000 -c http.lowSpeedTime=30 push`
4. **换传输阶梯**（重试 2~3 次仍失败时）：
   ① `git@github.com:`（SSH-443 固定 IP，最稳，见配置章节）
   ② 备用别名 `github-dns`（走 DNS 的 SSH 端点，`git remote set-url origin git@github-dns:OWNER/REPO.git` 临时用）
   ③ HTTPS + fail-fast（最后手段）
5. **报告阈值**：连续 **5 次或 5 分钟**仍失败才向用户报告，附完整错误文本；不要静默放弃。
6. **大改动（>10MB）**：耐心等待或分批推送；坏窗口下要预留几分钟。

## 一次性配置（若尚未配置）

完整步骤（含备份、known_hosts、逐一验证）见 `references/setup-ssh-443.md`。核心是 `~/.ssh/config`：

```
Host github.com
    HostName <ssh.github.com 的可用 IP>   # 直连 IP，绕开被污染的 DNS
    Port 443
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ConnectTimeout 15
    ServerAliveInterval 15
    ServerAliveCountMax 4
```

配套：known_hosts 需要 `[<IP>]:443` 的 GitHub host key 条目（GitHub 官方 ed25519 指纹 `SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU`）。

## IP 会变，一键刷新

`ssh.github.com` 的 IP 可能变化。失效时运行：

```powershell
pwsh -File scripts/refresh-github-ssh-ip.ps1            # 自动：DoH 解析 → 逐个测速 → 更新 config+known_hosts → 验证
pwsh -File scripts/refresh-github-ssh-ip.ps1 -DryRun    # 只预览不改动
```

手动兜底：`curl "http://223.5.5.5/resolve?name=ssh.github.com&type=A"` 拿新 IP，手改 `~/.ssh/config` 的 `HostName`，并补 `known_hosts` 的 `[IP]:443` 条目。

## 诊断（详见 references/diagnostics.md）

```powershell
# 1) 干净解析（AliDNS DoH，免污染）
curl "http://223.5.5.5/resolve?name=ssh.github.com&type=A"
# 2) 直连 IP 对比域名（判断是否 DNS 抽风）
#    直连 IP 连得上、域名不行 → DNS 污染；都连不上 → 坏窗口，等 1-5 分钟重试
# 3) 验证 SSH 全链路
ssh -o BatchMode=yes -T git@github.com    # 期望 "Hi <user>!"（或 Permission denied = 传输 OK 但 key 未注册）
# 4) 验证 git 传输
git ls-remote origin
```

## 安全红线

- **永远不要** `git config http.sslVerify false` / 关闭 SSH 主机校验来"绕过"问题。
- 不要把 token/密码写进 remote URL；凭据只走 credential helper / SSH key。
- 不明来源的公共加速镜像不要用于 `push` 或任何携带凭据的操作（只读 clone 才考虑镜像）。
- 修改 `~/.ssh/config`、`known_hosts`、git 全局配置前先备份（脚本会自动备份）。
