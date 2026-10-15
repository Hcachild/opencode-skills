---
name: ucpan-download
description: 'Download files/folders from UC网盘 (ucpan, drive.uc.cn, fast.uc.cn) share links without the official client and mostly without login, using the bundled multi-threaded Python downloader. Use when the user posts a drive.uc.cn/s/... or fast.uc.cn/s/... share link, asks to 下载/拉取/搬运 UC网盘分享 or ucpan 资源, or complains the UC client is slow or annoying.'
---

# UC网盘分享链接下载 (ucpan-dl)

用自带脚本 `scripts/ucpan-dl.py` 匿名解析 UC 分享链接并多线程下载（无需客户端；大多数文件也无需登录）。

## 快速开始

```powershell
# 全量下载（目录结构原样保留到 --out）
python C:\Users\Hanpeng\.config\opencode\skills\ucpan-download\scripts\ucpan-dl.py "<分享链接>" --out "D:\ucpan"

# 只列清单（小、快，先给用户确认）
python ...\ucpan-dl.py "<分享链接>" --out "D:\ucpan" --list

# 只下载匹配正则的子集
python ...\ucpan-dl.py "<分享链接>" --out "D:\ucpan" --only "原神"

# 带提取码 / 需要登录的文件（如 .apk）
python ...\ucpan-dl.py "<分享链接>" --out "D:\ucpan" --pwd xxxx --cookie "__puus=...; __pus=..."
```

常用参数：`--out`（必填建议）、`--only 正则`、`--pwd`、`--cookie`、`--jobs`（并发文件数，默认3）、`--chunks`（单文件分块数，默认16）、`--list`。

## 关键行为

- **输出目录**：默认 `./ucpan-out`；会写入 `.ucpan_index.json` 缓存（复用后跳过重新扫描，可安全删除）。完成后在 `[完成] 成功 X/Y` 行汇报，失败文件单列。
- **断点续传且幂等**：直接重跑同一命令即可——已完成文件自动跳过、未完成从 `.part*` 分块续传、token 过期自动刷新换链。**重试失败文件优先用重跑，不要另存新目录**。
- **速度**：单连接被限速 ~100KB/s，靠并发堆速度。默认 3 文件 × 16 分块 ≈ 2~3MB/s（视网络）。若太慢可加大 `--jobs 4~5`；被风控/报错多则减。
- **需要登录的文件**：`.apk` 等类型会被 CDN 拒绝（`require login [auth not found]`）。解法：用户浏览器登录 drive.uc.cn → F12 控制台 `copy(document.cookie)` → 用 `--cookie "<粘贴>"` 重跑（只补缺失文件）。不要尝试免登录绕 APK。
- 分享标题、文件数会在开头打印；`--list` 输出每行 `大小 路径`，适合先展示给用户挑。

## 使用流程（给 Agent）

1. 从用户消息提取分享链接（`https://drive.uc.cn/s/<id>` 或 `fast.uc.cn` 均可，带 `?public=1#/list/share` 也没问题）。
2. 小分享直接问清保存目录后全量下载；大分享/未知内容先 `--list` 展示数量与总大小（脚本会打印 `[ok] 共 N 个文件, X`）再确认。
3. 下载完成后核对 `[完成] 成功 X/Y`；有失败项按上面的「关键行为」处理。
4. 若下载的是 `*_encrypted.png` 番茄混淆图，下载完成后引导用 `fanqie-image-restore` skill 处理。

## 故障排查

| 现象 | 处理 |
|------|------|
| `分享已失效/被封禁` | 让用户重新分享；无法绕过 |
| 个别文件 `未返回直链（可能需登录Cookie）` | 用 `--cookie` 重跑（见上） |
| `.apk` 下载 403 `require login` | 同上，必须带 cookie |
| 下载中断/报错退出 | 直接重跑原命令，自动续传 |
| 速度只有 ~100KB/s | 确认没用 `--chunks 1`；加大 `--jobs`/`--chunks` |
| `sqlite`/缺依赖 `requests` | `pip install requests` |

## 技术细节（维护用）

- API 走 `pc-api.uc.cn` 的 `/1/clouddrive/*`（token → transfer_share/detail → file/download），参数 `entry=ft&fr=pc&pr=UCBrowser`。分享页 `drive.uc.cn` 与 `fast.uc.cn` 同源。
- 换链接口需要 `share_fid_token`（有效期短，几分钟级），过期报 `code=41020`；脚本按「父目录 fid → 重新列目录 → 换新 token」自愈。
- **CDN 直链 GET 必须不带 `Content-Type` 头**：URL 签名把 Content-Type(空) 算进 StringToSign，带上 `application/json` 会 `SignatureDoesNotMatch`。脚本用裸 `requests.get(url, headers={"User-Agent": ...})` 下载。
- 直链带 `Expires=`（约 3 小时）与签名，勿跨 UA 复用。
- 参考实现：`hmjz100/LinkSwift`（油猴）、`foxxorcat/gopeed-extension`（gopeed 扩展）、`byLsPro/JxPan`（CF Workers）。
