---
name: tapd-work-recording
description: >-
  把工作内容（日报/纪要/对话记录）转成 TAPD 任务卡，并通过 MCP 创建、复核与补工时；含任务 owner 批量改派（账号切换）。
  内置本项目 TAPD（百运与中技公共项目需求池等）的容器落位指南、字段映射（任务类型=custom_field_19）、
  新任务模式绕过、HTML 描述格式、更新清字段陷阱、账号切换/直连备用通道、工时填报规范等实战要点（均经实测验证）。
  Use when: (1) 用户说"把这个写成TAPD的格式 / 传输至TAPD / 帮我创建任务 / 建卡 / 补录 / 改派", (2) 需要补录或核对历史工时,
  (3) 需要查询/核对 TAPD 任务、工时、容器条目（只读场景同样适用）。
  触发词: TAPD、建卡、补录、任务卡、工时、传输至TAPD、写成TAPD的格式、TAPD记录、改派。
---

# TAPD Work Recording（工作内容 → 任务卡 → MCP 建卡 → 补工时/改派）

把工作内容（日报、纪要、对话记录）整理成 TAPD 任务卡，经 MCP 创建到对应项目/容器，并复核、补工时、按需改派。

## 环境

- MCP server：`tapd`（mcp-server-tapd），工具前缀 `tapd_*`
- Token 身份：**`杨汉鹏_`**（姓名：杨汉鹏；新账号；昵称 2026-10-15 由 `yanghanpeng` 改为 `杨汉鹏_`；旧账号 `杨汉鹏` 已停用 status=2）。
  **owner/creator 一律用运行时 `c.nick`，不要硬编码昵称**——昵称变更后字面量不会自动匹配（会挂成孤立字符串）；TAPD 对已正确挂接的成员会自动显示当前昵称。
- 项目：
  - `32496738` 百运与中技公共项目需求池（主战场）
  - `67680981` （老空间）AI项目组需求池（AaaS/运小星）——新账号暂不在该项目成员中
  - `36495762` 生产缺陷处理（缺陷空间，创建人：测试/技术支持）

## 容器（父需求）速查

| 工作类型 | 容器 | 完整 ID |
|---|---|---|
| 标注平台类（账号/性能/取证/修复/标注开展） | 数据标注与准备 | 1132496738001000997 |
| 探索/预研/PoC（JEV、JoySafety、入库预研） | 非项目类技术预研与POC | 1132496738001000996 |
| 9 月线上问题/配置/发布 | 百运科技-日常运维类-9月 | 1132496738001000768 |
| 10 月线上问题/配置/发布 | 百运科技-日常运维类-10月 | 1132496738001001406 |
| 行政/个人（绩效表、简历） | 其他临时任务 | 1132496738001000994 |
| 会议（备选） | 非项目类会议与沟通 | 1132496738001000992 |
| AaaS（P1A/E13/P1B） | P1A-E13 完整运小星 Plugin 迁移与 P1A Exit（67680981） | 1167680981001000497 |
| SN318 | SN318系统：产品管理及数据映射 | 1132496738001000865 |

固定字段 ID（32496738）：
- 任务类型 workitem_type_id：`1132496738001000035`（「任务」）
- 非项目类工作 category_id：`1132496738001000040`
- 任务默认模板 templated_id：`1132496738001000049`

**落位前先查状态**：已关闭（任务 done）、已上线/已关闭的 Story 不能挂（例：知识库 v1.3 的 B/C 系列、P1A 系列）。容器可选「数据标注与准备/预研/运维类月度/其他临时任务」等开放条目。

## 关键字段映射

| 字段 | 说明 |
|---|---|
| 任务类型 | `custom_field_19`：需求&调研 / UI设计 / 技术设计 / 开发 / 测试 / 验收 / 管理 / 其他 |
| 优先级 | `priority_label`：P0 / P1 / P2 / P3 |
| 预估工时 | `effort`（字符串，如 "3"） |
| 起止 | `begin` / `due`（YYYY-MM-DD，补录时填对应过去日期） |
| 命名惯例 | 前缀-标题：开发- / 调研- / 配置- / 技术设计- / 线上问题排查： / 会议- / 文档- |

## 建卡流程（用户习惯：先出卡，确认后再建）

1. **收集内容**：日报会话 `ses_0dd996e1effePzF8Km92TkxanG`（用 `opencode-chat-viewer` skill 查）或周文件 `C:\Users\Young\Downloads\2026年*.md`，或用户直接给的纪要。
2. **拆条**：一条工作 = 一张卡；同类小活合并，避免拆碎。
3. **选容器**：按上表；确认容器开放。
4. **写卡**：字段全填 + 任务说明（模板见下）。
5. **聊天框输出卡片让用户确认**（他会改预估工时/任务名/合并拆分）。
6. **MCP 创建**（模板见下）。
7. **复核**（fetch 检查 description / begin / due / effort / custom_field_19 / parent_id / **owner 是否为当前昵称**）。
8. **报链接**：`https://www.tapd.cn/{workspace_id}/prong/tasks/view/{id}`。
9. （按需）补工时、改派。

## MCP 调用模板

### 创建任务（★ 必须按此绕过，见"大坑"第 1 条）

```
tapd_create_story_or_task(
  workspace_id=32496738,
  name="开发-示例任务",
  options={
    "entity_type": "stories",                        # ★ 绕过（勿用 tasks）
    "workitem_type_id": "1132496738001000035",       # 任务类型
    "parent_id": "1132496738001000996",              # 容器（父需求）
    "owner": "杨汉鹏_",                               # ★ 用当前昵称（先确认，勿用过时昵称）
    "priority_label": "P2",
    "begin": "2026-10-13",
    "due": "2026-10-13",
    "effort": "3",
    "custom_field_19": "需求&调研",                   # 任务类型
    "category_id": "1132496738001000040",
    "templated_id": "1132496738001000049",
    "description": "<h2>…</h2>…"                     # ★ 必须 HTML（见"大坑"第 2 条）
  })
```

### 更新任务（★ 必须带 begin+due）

```
tapd_update_story_or_task(
  workspace_id=32496738,
  options={
    "entity_type": "stories",      # ★ 勿用 tasks（/tasks 403）
    "id": "1132496738001001708",
    "begin": "2026-09-28",         # ★ 不传会被清空
    "due": "2026-09-30",           # ★ 不传会被清空
    "description": "<h2>…</h2>…"
  })
```

### 查询（复核/落位核查用）

```
tapd_get_stories_or_tasks(workspace_id, {"entity_type": "tasks", "id": "<id>",
  "fields": "id,name,status,begin,due,effort,custom_field_19,priority_label,owner,parent_id,description"})
tapd_get_timesheets(workspace_id, {"owner": "杨汉鹏_", "limit": 200, "order": "created desc"})
# 注：2026-10-14 之前的历史工时挂在旧账号「杨汉鹏」名下（查历史用 owner="杨汉鹏"）
tapd_get_workitem_types(workspace_id, {})   # 找 name=任务 的类型 id
```

### 补工时（花费工时填在任务上）

```
tapd_add_timesheets(workspace_id=32496738,
  options={"entity_type": "story", "entity_id": "<任务ID>", "timespent": "3",
           "spentdate": "2026-10-13", "owner": "杨汉鹏_"})
```

- 历史记录 entity_type 为 `story`（同任务型条目）；**先试一条历史日期**确认可补填，再批量
- 单位 h；一般每天 8h；单条任务单日 ≤24h

### 备用通道：Python 直连（MCP 进程持旧 KEY / 账号切换 / MCP 故障时）

会话里的 MCP 进程在**启动时**读取 opencode.json 的环境变量——改了 KEY 需**重启 OpenCode** 才生效；未重启期间（或 MCP 出问题时）用直连通道（同一套 mcp-server-tapd 包，行为一致）：

```powershell
& "C:\Users\Young\AppData\Local\Programs\Python\Python312\Scripts\uvx.exe" --from mcp-server-tapd python <script.py>
```

```python
import os
os.environ["TAPD_ACCESS_TOKEN"] = "<YOUR_TAPD_ACCESS_TOKEN>"   # 当前昵称 杨汉鹏_
os.environ["TAPD_API_BASE_URL"] = "https://api.tapd.cn"
from mcp_server_tapd.tapd import TAPDClient
c = TAPDClient(); print(c.nick)                   # 先确认身份（当前应为 杨汉鹏_）
c.create_or_update_story({ ...与 MCP 相同的 payload；owner 用 c.nick ... })
```

直连时描述**无需** markdown 转换，直接传 HTML；创建后同样要复核。

### 账号改派：任务 owner 批量迁移（旧账号 → 新账号）

单条改派（2026-10-14 实测：owner/begin/due/description/effort/类型全部无损）：

```python
c.create_or_update_story({
  "workspace_id": 32496738, "id": "<任务ID>", "owner": c.nick,   # 当前昵称：杨汉鹏_
  "workitem_type_id": "1132496738001000035",
  "begin": "<原值>", "due": "<原值>",   # ★ 必须带上（否则会被清空）
})
```

流程：① 只读盘点（`owner=旧账号` 全量列表）；② **试改 1 条并复查**；③ 批量逐条改（间隔 0.3s）；④ 复查（旧账号剩余=0、新账号数=预期）。

注意：
- 新账号不在某项目成员里时，该项目任务无法改派（例：67680981 老空间，先让管理员把账号加进项目）
- 昵称变更后：已正确挂接的成员自动显示新昵称；**错误字面量不会匹配**（曾踩坑：昵称改为 杨汉鹏_ 后用旧昵称 yanghanpeng 建卡，owner 挂成孤立字符串，已修正）

### 工时增添：把旧账号的工时补到新账号（花费人补录，2026-10-15 实测全链路）

不改/不删旧记录，仅"增添花费人"（用户口径：不叫迁移）：
1. **前置**：任务需非终态——done 先流转 progressing（`/stories` update `{"status":"progressing", begin, due, workitem_type_id}`；实测 done→progressing 可直接流转）；**补录完成后按需改回 done**（`status:"done"`，同样带 begin+due）
2. **增添**：逐条 `update_timesheets({entity_type:"story", entity_id, timespent, spentdate, memo})`——owner 自动=当前昵称（c.nick）
3. **幂等**：按 `(entity_id, spentdate, timespent)` 去重后再加（避免重复增添）
4. **验证**：old 与 new 按 key 双向对账（missing 应为 0）
5. **效果与清理**：旧记录保留 → 任务工时合计显示两份；如需清理旧记录，`timesheets/delete_timesheets`（entity_type/entity_id/workspace_id/cost_ids[]，≤100 条/次，**不可逆**，动手前必须确认）
6. **查询坑**：按 `entity_id` 单独过滤工时查询会 422——用 `owner` 拉全量后本地筛选

## 任务说明模板（description 必须用 HTML）

```html
<h2>一、任务说明</h2><ul><li>做什么：…</li><li>怎么做（技术要点）：…</li></ul><h2>二、完成定义（DoD）</h2><ul><li>…</li></ul><h2>三、依赖</h2><ul><li>依赖任务/接口：…</li><li>阻塞：…</li></ul>
```

要点：一节一个小标题（h2）；条目用 ul/li；技术细节（提交号、指标、路径）写进"怎么做"；不确定的写"待确认"。

## 大坑与规避（全部实测）

1. **新任务模式探测 bug → 403**：`tapd_create_story_or_task(entity_type="tasks")` 内部探测 `check_new_task_mode` 用 `creator="TAPD_SYSTEM"` 查询，而项目实际值是 `"TAPD system"`（大小写不符）→ 探测失败 → 回退已禁用的旧 `/tasks` 接口 → `403 Forbidden`。**绕过**：`entity_type="stories"` + `workitem_type_id="1132496738001000035"`（等价新任务模式的创建方式，直接走 /stories）。更新同理用 `stories`。
2. **描述"挤成一坨"**：纯文本（含 `- 列表`）经服务端 python-markdown 转换时因缺空行被包成**单个 `<p>`**，HTML 里换行=空格 → 显示一坨。**做法**：直接传 HTML（`<h2>` + `<ul><li>`），服务端转换对现成 HTML 原样保留。
3. **更新误清 `due`**：`tapd_update_story_or_task` 更新时若不传 `due` 会被清空（实测踩坑）。**做法**：更新时同时带 `begin` + `due`。
4. **创建/更新后必须复核**：拉取该 id 检查 description 为 HTML 分节、begin/due/effort/custom_field_19/parent_id/owner 正确，再向用户报链接。
5. **账号/昵称切换**：新账号昵称 2026-10-14 为 `yanghanpeng`、2026-10-15 改为 `杨汉鹏_`（旧账号 `杨汉鹏` 停用）。**owner 必须用运行时昵称（c.nick），勿硬编码**。KEY 轮换后 MCP 需重启才生效，过渡期用"备用通道"。32496738 的 35 条历史任务已于 10-14 改派。

## 规范边界（《TAPD操作指导和规范要求》）

- Story 由产品经理创建（**不自建 Story**）；**任务（Task）各角色可自建** —— 所有建卡都是"任务"
- 工时如实填报、持续记录；漏记应尽快补录
- 用户说"只读"时，只做查询，**绝不写操作**

## 参考

- 实战沉淀：2026-10-12~15 的补录与改派（17 条任务创建 + 35 条 owner 改派 + 40 条工时增添 + 2 次修复 + 容器/字段/账号切换/工时补录全部实测）
- 相关 skill：`opencode-chat-viewer`（查工作记录来源）、`parallel-data-processing`（批量处理时）
