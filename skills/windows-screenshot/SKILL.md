---
name: windows-screenshot
description: >-
  Windows 本机截图统一入口：全屏 / 指定窗口（含被遮挡、最小化、UWP）/ 屏幕区域 / 浏览器页面（整页长图、元素级裁剪、移动端模拟、强制深色、2x 高清、页面内标注定位）/ 后处理（裁剪、放大内嵌图、红框标签、复制到剪贴板）。三脚本零第三方依赖：win-shot.ps1（系统级）、page-shot.mjs（Chrome/Edge CDP）、postprocess.ps1（标注合成）。Use when: 用户说"截个图/截屏/把那个窗口截下来/截这个网页/来张整页长图/截这个区域/标出来给我看/放大这块/复制图片到剪贴板"，或任务需要产出截图作为证据、文档配图、Bug 截图、UI 对比。触发词: 截图、截屏、screenshot、窗口截图、网页截图、整页长图、元素截图、标注截图、区域截图、复制到剪贴板。
---

# Windows 截图 Skill

三个脚本按职责分工，都无需第三方依赖（Node 18+、PowerShell 5.1/7、本机 Chrome 或 Edge）。

```powershell
$S = "C:\Users\Young\.config\opencode\skills\windows-screenshot\scripts"
```

| 要截什么 | 用什么 |
| --- | --- |
| 整个屏幕 / 多显示器 | `win-shot.ps1 -Mode screen` |
| 某个应用窗口（微信、编辑器、Excel…） | `win-shot.ps1 -Mode window -Title <正则>` |
| 屏幕上一块坐标区域 | `win-shot.ps1 -Mode region -Rect "x,y,w,h"` |
| 网页整页 / 单个元素 / 移动端 / 深色 | `page-shot.mjs` |
| 裁剪、放大内嵌、红框标签、贴剪贴板 | `postprocess.ps1` |

所有脚本输出一行 JSON：`path / width / height / method / bytes`（外加 `clipboard`）。

## 1. 系统与窗口截图 — win-shot.ps1

```powershell
pwsh -NoProfile -File $S\win-shot.ps1 -Mode list                      # 列出可见窗口：句柄/进程/标题/坐标/是否最小化
pwsh -NoProfile -File $S\win-shot.ps1 -Mode screen -Out D:\shots\all.png
pwsh -NoProfile -File $S\win-shot.ps1 -Mode window -Title "企业微信" -Out D:\shots\wecom.png
pwsh -NoProfile -File $S\win-shot.ps1 -Mode window -Process chrome -Title "飞书" -Out D:\shots\page.png
pwsh -NoProfile -File $S\win-shot.ps1 -Mode region -Rect "-100,200,800,600" -Out D:\shots\area.png -Clipboard
```

要点：
- `-Title` / `-Process` 是**正则**，多个候选时优先非最小化窗口；找不到先跑 `-Mode list`。
- 默认路径 = 提窗口到前台 + 裁剪 `DWMWA_EXTENDED_FRAME_BOUNDS` + `CopyFromScreen`（`method: screen-blt`），所以**截到的是当前屏幕上真实内容，会被上层窗口遮挡**。
- `-PrintWindow` 不抢焦点、可截被遮挡窗口（`method: printwindow`），但 UWP/部分 Chromium 窗口会全黑；脚本会采样检测黑图并**自动回退** screen-blt（`method` 字段会体现），无需手工判断。
- 最小化窗口自动 `ShowWindow(9)` 恢复，再等 350 ms；若截到残影，前置换窗后自行 `Start-Sleep` 再加时。
- `-Padding 10` 给窗口加白边；`-Clipboard` 成功后可直接粘贴到 IM/文档。
- 坐标支持多显示器负值（screen 用整个虚拟桌面）。

## 2. 网页 / 浏览器页面截图 — page-shot.mjs

基于 Chrome/Edge 无头实例 + DevTools 协议，独立 profile，不动用户正在用的浏览器。

```powershell
# 视口截图：2x 高清
node $S\page-shot.mjs --url https://opencode.ai/docs/ --mode viewport --dpr 2 --out D:\shots\v.png

# 整页长图（自动按 contentSize 拉高，1x 输出，避免超大图）
node $S\page-shot.mjs --url https://opencode.ai/docs/ --mode full --out D:\shots\full.png

# 元素级裁剪：只要 #content 这块
node $S\page-shot.mjs --url https://opencode.ai/docs/ --mode element --selector "#content" --dpr 2 --out D:\shots\el.png

# 页面内标注：暗色遮罩聚焦某个元素并打标签
node $S\page-shot.mjs --url https://opencode.ai/docs/ --mode annotate --selector "#content pre" --out D:\shots\mark.png

# 手机 + 深色 + 隐藏浮层
node $S\page-shot.mjs --url https://x.com --mobile --dark --hide "#cookie-banner, .ads" --dpr 3 --out D:\shots\m.png

# 需要登录态：先手动登录一次，profile 留在本机反复复用
node $S\page-shot.mjs --url https://intranet/ --headed --profile D:\shots\prof --out D:\shots\i.png
```

参数：`--url` 必填；`--mode viewport|full|element|annotate`；`--selector` CSS 选择器；`--width/--height`（默认 1440×900）；`--dpr`（默认 2）；`--mobile`；`--dark/light`；`--hide "sel1,sel2"`；`--wait 1200`（DOM 完成后额外等待，SPA 可加大）；`--scroll-through`（逐屏滚动触发懒加载，再做长图）；`--profile`；`--headed`；`--browser chrome|edge|auto`。

需要登录的站点：先 `--headed --profile <目录>` 打开，手工登录后关闭（脚本结束会关浏览器，cookie 已落盘），后续同一 `--profile` 即带登录态；不要直接指向正在运行的 Chrome 配置目录（实例锁冲突）。

限制：只能截自己启动的实例，**无法直接截用户已打开的后台标签页**——要么拿到 URL 重新渲染，要么用 `win-shot -Mode window` 截当前最前面的那个窗口。

## 3. 后处理 — postprocess.ps1

坐标为输入图像素坐标；一旦用了 `-Crop`，`-Box` / `-Zoom` 按**裁剪后**坐标。

```powershell
# 裁剪 + 红框标签 + 2x 放大内嵌插图 + 贴剪贴板
pwsh -NoProfile -File $S\postprocess.ps1 `
  -In  D:\shots\full.png -Out D:\shots\full-marked.png `
  -Crop "280,0,1160,1200" `
  -Box  "24,40,760,120:代码块" `
  -Zoom "24,40,760,120:2" `
  -Clipboard

# 多框：分号分隔；只缩放
pwsh -NoProfile -File $S\postprocess.ps1 -In a.png -Out b.png -Box "10,10,200,40:标题;300,80,400,200:表格"
pwsh -NoProfile -File $S\postprocess.ps1 -In a.png -Out b.png -Scale 0.5
```

规则：`-Zoom` 超出画布宽度会自动降倍并在底部居中排布（深色面板 + `放大 Nx` 说明 + 箭头）；标签用微软雅黑，含中文无需额外字体配置。

## 交付前验证（必须）

1. 用 Read 工具打开生成的 PNG，确认：内容正确、不是黑屏/灰屏、目标被遮挡或裁掉、文字可读。
2. 核对尺寸是否符合预期（整页长图宽度≈content 宽、dpr 2 时像素翻倍）。
3. 回复用户时给**绝对路径**；需要对方直接粘贴时加 `-Clipboard` 并确认返回 `clipboard-ok`。

## 常见坑

- **UWP 黑图**：计算器/设置/照片等 `PrintWindow` 全黑，脚本已自动回退；自写代码务必做黑图检测。
- **窗口被遮挡**：screen-blt 是屏幕像素，不是窗口内容；要真正的窗口内容用 `-PrintWindow`（能截则截）。
- **DPI 缩放**：脚本已 `SetProcessDpiAwarenessContext(-4)`；自写 .NET 抓屏若尺寸偏小/模糊，先做同样声明。
- **Chrome 残留**：`--profile` 复用前确认没有同目录实例在跑，否则 DevTools 端口连不上。
- **长图上限**：页面高 > 16384 px 可能被纹理上限截断（脚本会 `warning`），改 `--mode viewport` 分段截或降 `--dpr`。
- **隐私**：截图常含聊天记录/客户数据，默认放 `%TEMP%` 或用户指定目录，**不要**放进 git 仓库。
