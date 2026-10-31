---
name: opencode-retry-patch
description: 'Patch OpenCode CLI (Bun standalone binary) and OpenCode Desktop (Electron app.asar) so transient network/5xx/429 errors and provider content-filter blocks retry indefinitely instead of stopping after 5 attempts, with a 5-minute exponential-backoff cap. Use when opencode stops after 5 retries, users ask for 无限重试/重试不设上限/退避5分钟, or a content filter error terminates the session (客户端/CLI 都适用).'
---

# OpenCode 重试限制解除

把 OpenCode 1.x 的 session retry 从「5 次后终止」改成「一直重试」，单次指数退避上限改为 5 分钟，并让 provider 的 `content filter` 响应也进入重试。

## 改动

| 项目 | 原值 | 补丁后 |
|---|---|---|
| 重试次数 | 5 次后终止 | 无上限 |
| 指数退避上限 | 无 header 30s / 有 header `2^31-1` ms | `300000` ms（5 分钟） |
| content filter | 非重试，直接报错终止 | 按可重试处理 |
| `retry-after` | 最长 `2^31-1` ms | 最长 5 分钟 |

适用于 OpenCode 1.x（已验证 1.18.16 / 1.18.17 / 1.19.4 CLI，桌面端 1.19.5）。OpenCode 2.x 的 retry 策略不同，不要直接套用。

## 快速使用

Windows + PowerShell 7+。脚本会自动定位 npm/standalone CLI 和 `@opencode-aidesktop`。

### CLI

```powershell
# 打补丁。二进制被占用时自动排队；退出 opencode 后由计划任务替换
.\scripts\opencode-retry-patch.cmd

# E2E：mock provider 验证 500 / content filter 不会在 5 次后停止
.\scripts\opencode-retry-e2e.cmd

# 恢复
.\scripts\opencode-retry-patch.cmd -Restore
```

### Desktop

```powershell
# 关闭桌面端 -> 备份 app.asar -> 打补丁 -> 重新启动
.\scripts\opencode-desktop-retry-patch.cmd -CloseApp

# E2E：静态 + retry 行为单测 + app/server ready
.\scripts\opencode-desktop-retry-e2e.cmd

# 恢复
.\scripts\opencode-desktop-retry-patch.cmd -Restore
```

脚本不依赖当前目录；从 skill 目录或任意位置运行均可。

## 工作流程

1. 确认版本：`opencode --version`；桌面端看 `resources/app.asar` 内 `package.json`。1.x 适用。
2. CLI：定位 Bun standalone 二进制，解析嵌入 JS，做**等长**替换：
   - `RETRY_MAX_DELAY_NO_HEADERS` `30000` → `300000`
   - `RETRY_MAX_DELAY` `2147483647` → `300000`
   - 删除 `if (meta.attempt > RETRY_MAX_RETRIES)` 终止分支
   - `matchesRetryableMessage` 增加 `/content.?f/i`
3. Desktop：关闭 `OpenCode.exe`，解析 `resources/app.asar`，定位 sidecar 引入的 `out/main/chunks/node-*.js`，做同样的等长替换；不改变 asar 文件大小/偏移。
4. 先备份 `*.retrybak`，E2E 通过后生效。
5. OpenCode / 桌面端升级会覆盖补丁；升级后重跑。

## 文件

- `scripts/opencode-retry-patch.ps1` / `.cmd` — CLI 补丁
- `scripts/opencode-retry-e2e.ps1` / `.cmd` — CLI E2E
- `scripts/opencode-desktop-retry-patch.ps1` / `.cmd` — 桌面端补丁
- `scripts/opencode-desktop-retry-e2e.ps1` / `.cmd` — 桌面端 E2E
- `references/technical-notes.md` — 二进制/asar 结构、补丁点、版本适配
- `references/troubleshooting.md` — 锁定、计划任务、恢复、升级、常见错误

## 已验证

- CLI 1.19.4：E2E 4/4 PASS（500 持续重试、content filter 持续重试、300000ms cap、静态检查）
- CLI 1.18.17 / 1.18.16：补丁可应用、可启动
- Desktop 1.19.5：E2E 3/3 PASS（静态、行为单测、app running + server ready）
- 反例：未打补丁的 500 在 5 次后退出；content filter 只请求 1 次就退出

## 注意

- 桌面端补丁会关闭并重启应用（`-CloseApp`）；只在用户明确同意时这样做。
- 修改后 Windows 代码签名失效，属正常现象。
- content filter 也会按指数退避重试；provider 给出的 `retry-after` 超过 5 分钟时会被截到 5 分钟。
- 只处理 OpenCode 1.x 的 Bun/Electron 构建；源码安装请改 `packages/opencode/src/session/retry.ts` 后重建。
