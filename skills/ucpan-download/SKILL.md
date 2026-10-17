---
name: ucpan-download
description: 'Download files/folders from UC网盘 (ucpan, drive.uc.cn, fast.uc.cn) share links without the official client and mostly without login, using the bundled multi-threaded Python downloader. Includes a one-shot QR-login helper (ucpan-login.py) that saves a cookie to ~/.ucpan_cookie for downloading login-only types (apk/exe/zip/mp4/pdf). Use when the user posts a drive.uc.cn/s/... or fast.uc.cn/s/... share link, asks to 下载/拉取/搬运 UC网盘分享 or ucpan 资源, or complains the UC client is slow or annoying.'
---

# UC网盘分享链接下载 (ucpan-dl)

用自带脚本 `scripts/ucpan-dl.py` 解析 UC 分享链接并多线程下载（无需客户端；图片类无需登录，其他类型扫码登录一次即可）。

## 快速开始

```powershell
# 全量下载（目录结构原样保留到 --out）
python C:\Users\Hanpeng\.config\opencode\skills\ucpan-download\scripts\ucpan-dl.py "<分享链接>" --out "D:\ucpan"

# 只列清单（小、快，先给用户确认）
python ...\ucpan-dl.py "<分享链接>" --out "D:\ucpan" --list

# 只下载匹配正则的子集
python ...\ucpan-dl.py "<分享链接>" --out "D:\ucpan" --only "原神"

# 定向下载：在浏览器分享页里点进某个文件夹，把地址栏整条链接粘过来 → 只下该文件夹（含子目录）
python ...\ucpan-dl.py "https://drive.uc.cn/s/xxxx?public=1#/list/share/<fid>-名称/<fid>-名称/..." --out "D:\ucpan"

# 需要非图片文件（apk/exe/zip/mp4/pdf 等）时：先扫码登录一次（约 10 秒，存 ~/.ucpan_cookie）
python ...\ucpan-login.py
# 之后 ucpan-dl 自动读取凭证，无需任何参数；也可手动 --cookie/--cookie-file 传
```

常用参数：`--out`（必填建议）、`--only 正则`、`--pwd`、`--cookie`、`--cookie-file`、`--jobs`（并发文件数，默认3）、`--chunks`（单文件分块数，默认16）、`--list`、`--check`。

## 关键行为

- **输出目录**：默认 `./ucpan-out`；会写入 `.ucpan_index.json` 缓存（复用后跳过重新扫描，可安全删除）。完成后在 `[完成] 成功 X/Y` 行汇报，失败文件单列。
- **断点续传且幂等**：直接重跑同一命令即可——已完成文件自动跳过、未完成从 `.part*` 分块续传、token 过期自动刷新换链。**重试失败文件优先用重跑，不要另存新目录**。
- **速度**：单连接被限速 ~100KB/s，靠并发堆速度。默认 3 文件 × 16 分块 ≈ 2~3MB/s（视网络）。若太慢可加大 `--jobs 4~5`；被风控/报错多则减。
- **需要登录的文件**：非图片类型（`.apk/.exe/.zip/.7z/.mp4/.pdf` 等）会被 CDN 拒绝（`require login [auth not found]`），与大小无关（1.2MB 的 pdf 也拦）。解法：跑 `ucpan-login.py` 扫码一次（Cookie 存到 `~/.ucpan_cookie`，ucpan-dl 自动使用）；或用浏览器登录后 F12 `copy(document.cookie)`，`--cookie "<粘贴>"` 重跑（只补缺失文件）。不要尝试免登录绕。
- **深链接定向下载**：粘贴带 `#/list/share/<fid>-<名称>/...` 的地址（在分享页点进文件夹后的地址栏链接）→ 只扫描最深一级文件夹的子树（按 fid 解析，不依赖名称），文件落到 `<--out>/<文件夹真实名>/` 下；索引缓存按 (分享ID, 文件夹) 隔离。
- **先探测再下载**：拿不准可下载哪些文件时，先跑 `--check`（逐文件试取 1KB，按类型输出「可下载/需登录」统计），再决定是否需要 cookie。
- **凭证有效性**：ucpan-dl 启动时自动校验 `~/.ucpan_cookie`，无效会提示「登录凭证无效/已过期，本次按匿名模式运行」——重跑 `ucpan-login.py` 即可。
- 分享标题、文件数会在开头打印；`--list` 输出每行 `大小 路径`，适合先展示给用户挑。

## 使用流程（给 Agent）

1. 从用户消息提取分享链接（`https://drive.uc.cn/s/<id>` 或 `fast.uc.cn` 均可，带 `?public=1#/list/share` 也没问题）。
2. 小分享直接问清保存目录后全量下载；大分享/未知内容先 `--list` 展示数量与总大小（脚本会打印 `[ok] 共 N 个文件, X`）再确认。
3. 下载完成后核对 `[完成] 成功 X/Y`；有失败项按上面的「关键行为」处理。
4. 若下载的是 `*_encrypted.png` 番茄混淆图，下载完成后引导用 `fanqie-image-restore` skill 处理。

## 下载边界（2026-10 实测）

| 类型 | 匿名（无 cookie） | 登录后（免费账号） |
|------|------------------|------------------|
| 图片 .png/.jpg/.jpeg | ✅ 可下载 | ✅ |
| .apk / .exe / .dmg | ❌ 需登录 | ✅ |
| .zip / .7z / .001x 分卷包 | ❌ 需登录 | ✅ |
| .mp4 视频 | ❌ 需登录 | ✅（见下） |
| .pdf 文档 | ❌ 需登录 | ✅ |

匿名边界细节：
- 与**大小无关**（1.2MB pdf 也拦）；与 **UA/Referer 无关**；`risk_type/ban` 元数据均为 0。服务端按类型的白名单：**只有图片类对匿名开放**。

登录后复核（2026-10-17，凭 ~/.ucpan_cookie）：
- 之前被拦的 7 个分享 `--check` 全部「可下载」；实下 apk×2 / exe / 7z 46MB / dmg 370MB / pdf×2 全部成功且大小与元数据**精确一致**。
- 大视频抽查（713MB / 917MB，含版权敏感资源）：HTTP 206、**服务器端文件大小与元数据一致、ftyp 头正常** → 未被替换成「请使用UC浏览器播放」提示视频（社区黑号案例未出现于本账号，但账号级风控存在，遇替换只能换号）。
- 速度：登录**不解除单连接 ~100KB/s 限速**（非会员无加速），仍靠 16 分块并发约 1.2~1.7MB/s/文件；连续下载累计 >2GB 无配额拦截。
- 未验证：单文件 >10GB（官方口径上限 10GB）；带提取码分享；长期/大流量配额。

## 凭证获取（ucpan-login.py）

一次性扫码登录工具：出二维码 → 手机 **UC浏览器/UC网盘 App** 扫码确认 → Cookie 自动存到 `~/.ucpan_cookie` → 进程退出（无常驻）。有效期通常数周，失效重跑即可。

```powershell
python C:\Users\Hanpeng\.config\opencode\skills\ucpan-download\scripts\ucpan-login.py
```

- `--timeout 300` 延长等待；`--no-open` 不自动打开二维码图片（终端有字符版二维码）
- 走官方 CAS 扫码接口（`api.open.uc.cn/cas/ajax/*`），不需要 UC 客户端、不需要密码
- 同类官方登录的其它路径均不可纯命令行化：短信登录发送前有强制阿里云滑块（`20180001`）；账密登录需过 NoCaptcha；第三方扫码（淘宝/支付宝/微博）由各自官方页面渲染，纯协议复刻代价高——所以扫码是本工具唯一全自动的凭证获取方式

## 故障排查

| 现象 | 处理 |
|------|------|
| `分享已失效/被封禁` | 让用户重新分享；无法绕过 |
| 个别文件 `未返回直链（可能需登录Cookie）` | 跑 `ucpan-login.py` 或用 `--cookie`（见上） |
| 非图片文件 403 `require login` | 同上，必须带 cookie（这是服务端类型白名单，不是 bug） |
| `登录凭证无效/已过期` | 重跑 `ucpan-login.py` 扫码刷新 |
| 下载中断/报错退出 | 直接重跑原命令，自动续传 |
| 速度只有 ~100KB/s | 确认没用 `--chunks 1`；加大 `--jobs`/`--chunks` |
| `sqlite`/缺依赖 `requests` | `pip install requests` |
| `ucpan-login` 报缺 `qrcode` | `pip install qrcode`（pillow 可选，用于保存二维码图片） |

## 技术细节（维护用）

- API 走 `pc-api.uc.cn` 的 `/1/clouddrive/*`（token → transfer_share/detail → file/download），参数 `entry=ft&fr=pc&pr=UCBrowser`。分享页 `drive.uc.cn` 与 `fast.uc.cn` 同源。
- 换链接口需要 `share_fid_token`（有效期短，几分钟级），过期报 `code=41020`；脚本按「父目录 fid → 重新列目录 → 换新 token」自愈。
- **CDN 直链 GET 必须不带 `Content-Type` 头**：URL 签名把 Content-Type(空) 算进 StringToSign，带上 `application/json` 会 `SignatureDoesNotMatch`。脚本用裸 `requests.get(url, headers={"User-Agent": ...})` 下载。
- 直链带 `Expires=`（约 3 小时）与签名，勿跨 UA 复用。
- 参考实现：`hmjz100/LinkSwift`（油猴）、`foxxorcat/gopeed-extension`（gopeed 扩展）、`byLsPro/JxPan`（CF Workers）。
