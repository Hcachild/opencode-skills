# SSH over 443 稳定通道 —— 完整配置指南

> 适用：国内网络下 `git push/pull/clone` 对 GitHub 时断时续、要重试很多遍的情况。
> 原理：把 git 传输从 HTTPS 换成 SSH，并固定连到 `ssh.github.com` 的真实 IP（443 端口），
> 绕开两件事：① DNS 污染（不再走域名解析）② GitHub 主站 IP/TLS 特征的间歇性阻断。

## 0. 前置检查

- 本机已有 SSH 密钥：`ls ~/.ssh/id_ed25519.pub`（没有就 `ssh-keygen -t ed25519`）
- 账户尚未注册该公钥时，先在 GitHub 网页添加：
  `https://github.com/settings/ssh/new` → Title 随意 → Key type 选 **Authentication Key** → 粘贴 `.pub` 全文 → Add
- 验证公钥是否已注册：`ssh -T git@github.com` 出现 `Hi <用户名>!` 即成功
  （出现 `Permission denied (publickey)` 说明通道通了但公钥还没注册）

## 1. 获取 ssh.github.com 的可用 IP

用阿里 DoH 的 JSON 接口拿干净解析（明文 HTTP，不受 SNI 阻断影响）：

```bash
curl "http://223.5.5.5/resolve?name=ssh.github.com&type=A"
```

返回的 `Answer[].data` 即候选 IP（若首个候选不可达，手动逐个 TCP 测试选通的）。

## 2. 写入 ~/.ssh/config（先备份！）

```bash
cp ~/.ssh/config ~/.ssh/config.bak-$(date +%Y%m%d)
```

在 config 中替换/新增（`HostName` 换成第 1 步拿到的 IP）：

```
# GitHub SSH over 443 - IP pinned to bypass poisoned DNS
Host github.com
    HostName <IP>
    Port 443
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ConnectTimeout 15
    ServerAliveInterval 15
    ServerAliveCountMax 4

# Fallback: DNS-resolved endpoint（IP 失效但 DNS 正常时临时用）
Host github-dns
    HostName ssh.github.com
    Port 443
    User git
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
    ConnectTimeout 15
```

Windows 路径：`C:\Users\<用户名>\.ssh\config`。

## 3. 补 known_hosts 条目

直连 IP 时主机校验名是 `[IP]:443`，需要对应条目。GitHub 全集群共用同一套官方 host key，
ed25519 公钥为（指纹 `SHA256:+DiY3wvvV6TuJJhbpZisF/zLDA0zPMSvHdkr4UvCOqU`）：

```
[<IP>]:443 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOMqqnkVzrm0SdG6UOoqKLsabgH5C9okWi0dh2l9GKJl
```

（若已有 `[ssh.github.com]:443 ssh-ed25519 ...` 条目，直接复制其 key 字符串换成新 IP 前缀即可，
等价且已经过历史验证。可用 `ssh-keygen -F "[ssh.github.com]:443" -f ~/.ssh/known_hosts` 查看。）

## 4. 验证

```bash
ssh -o BatchMode=yes -T git@github.com          # 期望: Hi <用户名>! ...
git ls-remote git@github.com:<owner>/<repo>.git # 期望: 正常列出 refs
git -C <本地仓库> push git@github.com:<owner>/<repo>.git main   # 真实推送验证
```

## 5. 可选增强

### 5.1 全局把 HTTPS 地址自动改走 SSH

```bash
git config --global url."git@github.com:".insteadOf "https://github.com/"
# 撤销：
git config --global --unset url."git@github.com:".insteadOf
```

效果：所有 `https://github.com/...` 的仓库（含旧 clone、新 clone）自动走 SSH-443 通道。
注意：这会对全部 GitHub HTTPS 操作生效（包括公开仓库的匿名 clone，届时也要求本机 key，通常无害）。

### 5.2 HTTPS 兜底时防挂死（全局 fail-fast）

```bash
git config --global http.lowSpeedLimit 1000
git config --global http.lowSpeedTime 30
```

低于 1KB/s 持续 30 秒即中止（一般是坏窗口），配合重试脚本即可。

### 5.3 合并到日常流程

把 push 换成重试包装（本 skill 的 `scripts/git-push-retry.ps1`），或在 AGENTS.md / CI 中写明
「GitHub 网络失败自动重试最多 5 次、间隔 5~15 秒」。

## 6. 故障排查

| 症状 | 判断 | 处理 |
|---|---|---|
| 域名连不上、直连 IP 可以 | DNS 污染 | 保持 IP 固定；或给系统配 DoH |
| 直连 IP 也超时（同网段其它服务正常） | 该 IP 被针对性阻断 / 坏窗口 | 换 IP（第 1 步）或等几分钟重试 |
| `Connection reset` 反复出现 | SNI/TLS 层干扰（HTTPS 特征） | 换 SSH 传输（本指南路线） |
| `Permission denied (publickey)` | 通道通、公钥未注册 | 第 0 步注册公钥 |
| `Host key verification failed` | known_hosts 缺 `[IP]:443` 条目 | 第 3 步补条目（勿关闭校验） |
| 一段时间后又全挂了 | IP 变更 / 阻断策略变化 | 跑 `scripts/refresh-github-ssh-ip.ps1` |

## 7. 回滚

```bash
cp ~/.ssh/config.bak-<日期> ~/.ssh/config
# 如有：git config --global --unset url."git@github.com:".insteadOf
# 如有：git config --global --unset http.lowSpeedLimit / http.lowSpeedTime
```
