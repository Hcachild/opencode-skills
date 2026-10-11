---
name: fanqie-image-restore
description: 'Restore 混淆图/加密图 from 番茄图片混淆/小番茄 (fanqie/tomato) apps, including 空间曲线混淆(Gilbert curve)、块混淆、逐像素/行像素混淆. Use when the user asks to 解混淆/还原/处理 a folder of scrambled images (e.g. D:\opencode-workspace\<date>\ folders, filenames like encrypted_*.png or UUID.jpg).'
---

# 小番茄/番茄图片混淆还原

处理被「番茄图片混淆」类 APP/网站打乱的图片，还原为可看原图。

## 算法知识

| 方法 | 别名 | 密钥 | 特征 |
|------|------|------|------|
| tomato | 小番茄/空间曲线混淆 | 浮点数(默认1.0) | 最常见；基于 Gilbert 空间填充曲线；无密钥默认 |
| block | 块混淆 | 字符串 | 32x32 块打乱；尺寸不是32倍数时会填充变大 |
| perpixel | 逐像素混淆 | 字符串 | 每个像素随机置换 |
| rowpixel | 行像素混淆 | 字符串 | 仅水平方向置换 |

要点：
- **混淆和解混淆互为逆操作**。图片可能被「解混淆」方向处理过（如 20260716 案例），此时需用「混淆」方向还原。
- 同一图片可能被**多次**混淆，需相同次数反向操作。
- 有些图片先压缩过则无法完全还原（正常现象）。
- 算法源码参考：`https://github.com/jiarandiana0307/PicEncrypt`。

## 工作流程

用户通常说「帮我处理 YYYYMMDD 文件夹」。按以下步骤：

### 1. 自动检测方法与方向

```powershell
python C:\Users\Hanpeng\.config\opencode\skills\fanqie-image-restore\scripts\detect_method.py "D:\opencode-workspace\20260718"
```

检测器用 local std（32x32 块局部标准差均值）启发式排序：**降幅越大越可能是正确还原**，通常正确项降幅 >= 2。输出会直接给出推荐命令。
检测只取文件夹第一张图（约 20~60 秒，numpy 向量化），同文件夹图片通常用相同参数。

### 2. 批量还原

```powershell
python C:\Users\Hanpeng\.config\opencode\skills\fanqie-image-restore\scripts\fanqie_decrypt.py "D:\opencode-workspace\20260718" -o "D:\opencode-workspace\20260718_restored"
```

常用参数：
- `-e` 用混淆(encrypt)方向处理（默认是解混淆 decrypt）
- `-n 3` 重复 3 次（多次混淆时）
- `-m block -k "密钥"` 指定方法/密钥（非 tomato 时）
- `-k 0.5` tomato 指定浮点密钥（默认 1.0）

输出默认保存为 `<输入文件夹>_restored\<原名>_restored.jpg`。

### 3. 验证

用 Read 工具查看还原后的图片（支持看图），确认内容正常、无噪声块。
也可对比 local std：还原正确的图片局部更平滑（std 更低）。

## 经验记录（工作区实际案例）

| 文件夹 | 方法 | 方向 | 结果 |
|--------|------|------|------|
| 20260701~03 | tomato key=1 | decrypt x1 | std 17.99→11.06 |
| 20260707/08 | tomato key=1 | decrypt x1 | 正常 |
| 20260716 | tomato key=1 | **encrypt x1** | 被反向处理过 |
| 20260717 | tomato key=1 | decrypt x1 | std 15.61→11.06 |
| 20260718 | tomato key=1 | decrypt x1 | std 20.02→12.04，15张 |

图片常见来源：手机截图 1440x2560 / 2128x1456，UUID 或中文文件名。

## 故障排查

- **检测无推荐**（降幅都 <= 1.5）：
  1. 用 `--keys "自定义密钥"` 补充常见密钥之外的密钥；
  2. 询问用户密钥或混淆次数；
  3. 试 `detect_method.py` 排名前 3 的候选，用 Read 看图人工判断。
- **`python` 报缺少依赖**：`pip install pillow numpy`。
- **还原后仍有噪点**：可能被多次混淆，用 `-n 2`、`-n 3` 递增尝试；
  或图片经过有损压缩，属正常损失。
- **块混淆输出尺寸变大**：宽高按 32 向上取整所致，属正常现象。
