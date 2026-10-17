# 诊断手册 —— 判断"抽风"发生在哪一层

## 分层判据（从下往上）

| 层 | 测试 | 症状 → 结论 |
|---|---|---|
| DNS | `curl "http://223.5.5.5/resolve?name=<域名>&type=A"`（AliDNS，明文 HTTP 免污染） vs 本地 `Resolve-DnsName <域名>` | 两者结果不一致 → 本地 DNS 被污染，客户端会挑到坏 IP |
| TCP | 直连 IP 测 443：`Test-NetConnection` 或 TcpClient（6s 超时），连测 8~10 次 | 直连 IP 通过率高、域名通过率低 → 纯 DNS 问题；直连也不稳 → 该 IP 被针对性阻断或处于坏窗口 |
| TLS | `curl -sv --resolve <域名>:443:<IP> https://<域名>/` | 连上后 TLS 握手卡死 / `Recv failure: Connection was reset` → SNI 特征被干扰（HTTPS 无解，换 SSH） |
| SSH | `ssh -o BatchMode=yes -o ConnectTimeout=10 -T git@github.com` | 出现 `Hi <用户名>!` = 全链路 OK；`Permission denied (publickey)` = 传输 OK 公钥没注册；超时 = 查 IP/窗口 |
| 应用 | 小请求 `git ls-remote`、小推送 vs 大推送（>10MB） | 小操作通、大传输中途 reset → 窗口式限速，重试+分批+fail-fast |

## 快速矩阵模板（PowerShell）

```powershell
function TcpTest([string]$h,[int]$p=443,[int]$timeoutMs=5000){
  $sw=[System.Diagnostics.Stopwatch]::StartNew()
  try{
    $c=[System.Net.Sockets.TcpClient]::new(); $t=$c.ConnectAsync($h,$p)
    if($t.Wait($timeoutMs)){ $sw.Stop(); $c.Close(); "OK $([math]::Round($sw.Elapsed.TotalMilliseconds))ms" }
    else { $sw.Stop(); "TIMEOUT" }
  } catch { $sw.Stop(); "ERR" }
}
# 域名 vs 直连 IP 各测 8 次，对比通过率
1..8 | ForEach-Object { TcpTest "ssh.github.com" }
1..8 | ForEach-Object { TcpTest "<ssh.github.com 解析出的IP>" }
```

> 注意：`ConnectAsync(域名)` 会尝试解析出的多个地址；热点/运营商 DNS 返回混杂记录时，
> 单次超时≠地址全坏。**逐 IP 直连测试才有结论**。

## 已观测到的真实行为（2026-10 案例，供对照）

- 同一网络下，`ssh.github.com` **域名解析**访问：8/10 超时；**直连其 IP**：9/10 成功（~100ms）。→ DNS 污染是主要杀手。
- `github.com` 主站 IP 会**整段窗口不可达**（15/15 超时），几十秒后又恢复（HTTP 200 / 快速返回）。
- `api.github.com`、`raw.githubusercontent.com`、`codeload.github.com` 大多数时间可达，但也会偶发超时。
- HTTPS 到 github.com 的大传输（10~20MB push）在坏窗口会挂死 5 分钟以上；好窗口 ~260KB/s 能过。
- **SSH over 443 在坏窗口期间依然能完成握手与推送**（认证 3/3、小推送 8s、5MB 推送 ~45s）。
- 从国内数据中心（如深圳)测试 HTTPS 到 github.com：TCP 89ms 很快，但 3 次里 2 次 TLS 阶段挂死 →
  TLS/SNI 干扰普遍存在；**能换 SSH 就换 SSH**。

## 常见误判

1. 「浏览器能打开 GitHub，所以网络没问题」——浏览器会自动重试、缓存 DNS/页面，CLI 不会。
2. 「ping 不通就是封了」——GitHub 禁 ICMP，ping 本来就不通；用 TCP 443 测。
3. 「等一会就好」×「一直死等」——正确做法是**定量重试**（最多 5 次 / 5 分钟）再报告。
4. 「把 sslVerify 关掉试试」——`fatal: SSL certificate problem` 大多是坏窗口的产物，关闭校验只会掩盖问题并降低安全性。
