---
name: deep-web-research
description: Use when the user asks to 联网搜索/查找/找出 an unknown thing (game, app, product, video, song, article, person, event, dataset), 查证/求证 a claim, or 查资料/查数据 — triggers: 帮我搜一下、帮我找、找一下、这是什么、求游戏名、查证、求证、是真的吗、搜个资料、深度搜索、identify this、find this、fact-check、verify、TOMT. Multi-round deep web search that asks the user clarifying questions when the trail goes cold. Not for simple one-shot lookups that a single search answers.
license: MIT
---

# Deep Web Research（深度联网搜索 / 找东西 / 查证）

把"用户凭记忆描述一个东西 → 联网找出它并验证"做成一套可重复的流程。适用于游戏、APP、产品、视频、歌曲、文章、人物、事件、数据等任何需要"顺藤摸瓜"的检索。

## 核心原则

1. **关键词是命门**：优先用最独特、最罕见的**细节指纹**当搜索词（罕见机制、剧情反转、界面元素、道具用途），而不是泛泛的描述（"一个解谜游戏"）。
2. **多路并行**：一次消息里发多个搜索请求，覆盖不同措辞、中英双语、不同引擎；不要串行挤牙膏。
3. **不收敛就问**：同一角度搜 2~3 轮仍无果，就停下来用 `question` 工具向用户发**选择题**，而不是继续瞎猜。
4. **候选要逐条验证**：出现候选后，用一手来源（攻略/walkthrough、wiki、商店页、官方页）核对他记忆里的**每一个**细节；部分匹配不算找到。
5. **给出来源**：结论必须附可点击的来源链接，并标注哪些点吻合、哪些点与用户记忆有出入。

## 工作流程

### Phase 0 — 解析需求，提取特征

- 把用户的描述拆成特征清单，并分成两类：
  - **客观指纹**（必须吻合）：独特机制、剧情反转/结局、角色名、道具用途、平台、语言、关卡结构。
  - **主观印象**（可容错）：画风"写实/卡通"、颜色、年份、具体比例——用户经常记错。
- 找出其中**最罕见的一条**作为第一搜索词。例如："苍蝇收集换提示"、"结局有人假扮野兽"、"造船+金矿+雪球+迷雾关卡组合"。

### Phase 1 — 广撒网（并行搜索）

- 第一轮一次发 3~4 个并行搜索：
  - 中文一组 + 英文一组，同一指纹换 2~3 种说法。
  - 用引号做精确匹配，避免泛词。
- 工具选择：
  - `tavily_tavily_search`：`search_depth=advanced`，可用 `include_domains` 定向站点、`max_results` 调大。
  - `websearch`：补充另一路结果，中文查询效果好。
  - `tavily_tavily_research`：深度多源研究，但**容易超时**，只在其他方式都失败时用一次。
  - `tavily_tavily_extract` / `webfetch`：打开具体页面（攻略、wiki、商店页）读原文验证。
  - `tavily_tavily_crawl` / `tavily_tavily_map`：站点内爬取/摸清结构。
- 常用定向站点（按主题选）：
  - 游戏识别：`reddit.com`（r/tipofmyjoystick、r/FindAGame）、`zhihu.com`、`tieba.baidu.com`、`taptap.cn`、`douban.com`、`bilibili.com`、`store.steampowered.com`、`bigfishgames.com`、`hogs.fandom.com`、`mobygames.com`、`gamefaqs.gamespot.com`、`*fandom.com` 各作品 wiki。
  - 攻略/流程：`ali213.net`、`3dmgame.com`、`9game.cn`、`gamersky.com`、`casualgameguides.com`、`gamehouse.com/blog`、`appunwrapper.com`、`jayisgames.com`。

### Phase 2 — 换角度迭代

搜索失败≠没有，只是词不对。换这些角度：

- **同义词/译名变体**：追寻 vs 追踪、苍蝇 vs 飞虫/萤火虫、野兽 vs 怪物/野人、飞船 vs 小船。
- **搜"机制"而不是"整体"**：`"collect the flies" hints`、`"build a ship" level walkthrough`。
- **搜攻略/流程/结局文本**：`<关键词> 攻略 结局`、`<keywords> walkthrough ending`——攻略里常直接写结局细节。
- **搜社区问答**：`求游戏名`、`叫什么名字`、`tip of my joystick`、`what was that game`。
- **搜作品 wiki 的细节页**：wiki 常有"hints system / collectibles / level list"页面，直接印证机制。
- **换语言**：中文找不到就英文，英文找不到就日文/俄文（原版语言）。
- 某站 403 就换来源，或用搜索结果摘要里的原文片段。

### Phase 3 — 不收敛 → 问用户（question 工具）

- 同一角度 2~3 轮无果立即提问，别硬搜。
- 一次问 3~5 题，每题给**具体选项**（允许自定义答案），选项要能真正区分候选。
- 高价值问题模板：
  - 平台/来源（手机 / PC / 网页 / Steam / 小程序 / 记不清）
  - 年代（与大作同期的锚点更好："和 X 同期"）
  - 语言（中文 / 英文 / 汉化）
  - 最独特机制的细节（怎么出现、怎么用、换到什么奖励）
  - 场景/主题、视角、是否有关卡/地图
- 用户回答后**立刻带新信息重搜**；可能需要连续 2~3 轮问答（本次实战就用了 3 轮）。
- 提问前先自己搜过几轮，问题才有针对性；问题里不要夹带未验证的猜测当结论。

### Phase 4 — 候选验证（最关键）

- 用 `webfetch` / `tavily_tavily_extract` 打开**一手来源**逐条核对：
  - 结局/反转是否与用户记忆一致（攻略原文最可靠）。
  - 独特机制是否真实存在（如"蓝苍蝇换提示"、"船小游戏"）。
  - 平台、年份、开发商、中英文名。
- **系列作品要区分是哪一部**：列出系列每部的特色关卡/机制，确认"同时具备用户所有特征"的那一部（例：Royal Envoy 1 vs 2 的差异）。
- 主观描述（画风/颜色）可容错；客观特征（机制/剧情）必须吻合才可下结论。
- 多来源交叉验证；单一来源存疑时再找一个独立来源。

### Phase 5 — 输出结论

按以下顺序，用用户的语言回答：

1. **结论先行**：名称（中文名 + 原名）、平台、年份、开发商。
2. **逐条对照**：把用户记得的每个细节和确认的证据对应起来（可列表）。
3. **来源链接**：每个关键结论附链接。
4. **出入说明**：记忆与事实不符处明确写出（"你说的 X 实际是 Y"）。

### Phase 6 — 衍生需求（找视频/找资源）

- 如"B站有没有相关视频"：先 `webfetch` 站点搜索页，或直接调站点 API：
  ```powershell
  # B站搜索 API 示例（bash 工具内）
  $ua="Mozilla/5.0 ..."
  curl.exe -s -H "User-Agent: $ua" -H "Referer: https://www.bilibili.com/" -b "buvid3=..." `
    "https://api.bilibili.com/x/web-interface/search/type?search_type=video&keyword=<urlencoded>" `
    -o "$env:TEMP\bili.json"
  $j = Get-Content -Raw "$env:TEMP\bili.json" | ConvertFrom-Json
  $j.data.result | Select-Object bvid, title, author, duration
  ```
  取 UP 主全部视频可用 `x/space/arc/search?mid=<mid>&keyword=<kw>`。
- 超大页面/超长输出交给 `task` 的 `explore` 子代理去 grep/分段读，避免自己吃掉上下文。

## 提问模板（直接套用）

```
question(questions: [
  { header: "平台", question: "你是在哪玩的/看到的？",
    options: ["手机", "PC单机", "网页小游戏", "记不清"] },
  { header: "年代", question: "大概什么时候？",
    options: ["2010-2013（和X同期）", "2014-2016", "2017以后", "记不清"] },
  { header: "关键机制", question: "那个XX是怎么出现/使用的？",
    options: ["…", "…", "…", "记不清"] },
])
```
选项要写用户能一眼认出的具体现象，而不是抽象分类。

## 实战案例（本次对话提炼）

| 需求 | 卡点 | 破局方式 | 结果 |
|------|------|----------|------|
| 找"寻找野兽的2D解谜游戏" | 泛词全无果 | 问选择题（平台/视角/画风/年代/野兽类型）→ 用"大脚怪"重搜 → 游侠攻略验证结局"真正的大脚怪站在阴影里" | 《大脚怪：追寻阴影》 |
| 找"收集苍蝇换提示的游戏" | "苍蝇"词不对 | 换"flies/fireflies hints walkthrough" → 攻略原文"two blue flies… red fly gives hint" + 小船小游戏 | The Tiny Bang Story |
| 找"能造房+造船/金矿/雪球/迷雾关卡" | 特征太杂 | 拆成独特关卡组合搜攻略 → 逐条命中（Build a Ship / Snowball Tournament / Obelisk 驱雾） | Royal Envoy 2 |

## 注意事项

- 别过早下结论，也别把"相似作品"当答案；至少验证 2 个以上独有特征。
- 用户的记忆会错（画风、颜色、年份、名字），**以独特客观特征为准**。
- 善用"和已知作品同期/同类"作为锚点（如"和大脚怪同期"）。
- 每个结论都留来源；来源不可靠时直说不确定。
- 不搜索或帮助定位他人隐私信息；涉及盗版/破解资源只说明存在性，不给下载引导。
