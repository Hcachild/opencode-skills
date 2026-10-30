# Prompt 模板

占位符用 `<...>`。所有模板都假设已读过本技能 `SKILL.md` 与 `references/protocol.md`。
原则：**下发的每个代理 prompt 都自带完整上下文与硬规则**，不依赖父代理的隐性记忆。

## §0 通用头（每个派生 prompt 必带，放在最前）

```
run_token=<SWARM>-g<G>-<agent_id>-<8hex>   # 全局唯一，父代理生成并记入 agent_log
开工第一步：python <SWARM>/tools/session_map.py self --token <run_token>
把输出 SESSION_ID=<ses_...> / PARENT_ID=<ses_...> 开工即写进 runs/<agent_id>/SESSION_ID 与 NOTES，
并在最终回报首行带上。
```

- 父代理注意：`task` 工具返回头 `<task id="ses_...">` 就是子代理 session id（= 续跑 `task_id`）。
  返回后立刻写 `runs/<agent_id>/SESSION_ID` 并追加 `agent_log.jsonl`
  （`{"event":"spawn","agent_id":...,"session_id":"ses_...","parent_session_id":"ses_..."}`）。
- **中断返回 `Task cancelled` 时没有 `<task id>`**（实测）：用子代理开工写的 `SESSION_ID`、`run_token` 反查，或 `children --parent`。
- 找不到子代理时：`session_map.py children --parent <自己的 session_id>`，或按 `agent_id` 反查。
  **不要**用 `opencode session list`（不列子代理），**不要**按 `time_updated` 猜。
- **会话备份**：checkpoint/收口时 `session_backup.py export-state --swarm <SWARM>`；
  删除会话前先 export。删除父会话会级联删除子会话（实测）。

## §1 Sponsor → root curator（每代 launch brief）

```
你是 <项目> swarm<N> 的 root curator（Generation <G>）。嵌套已验证可用（你可派生 swarm-lead 子代理）。
强度=<intensity>（默认 medium；读 state.intensity_profile 的槽位/代理并发/审计/备份节奏，不得擅自升档）。
run_token=<SWARM>-root-g<G>-<8hex>；开工先跑 `python <SWARM>/tools/session_map.py self --token <run_token>`，
记下 SESSION_ID（=你的 task_id）并在每代 checkpoint 的"在途代理"表记录所有子代理的 session id。

## 开工必读（按序）
1) <DOCS>/CHARTER.md（使命/任务卡/技能门/反作弊/停止条件）
2) <DOCS>/PROTOCOL.md（角色/领取/锁/预算/记录契约）
3) <DOCS>/ROADMAP.md（阶段与迭代循环）
4) <SWARM>/state.json、backlog.jsonl、leaderboard.csv、checkpoints/gen_<G-1>.md

## 本代背景（承前）
- <上代 checkpoint 关键数字：达标项、冻结项、已证伪路径、真实运营/交付线索>
- <协议版本与纪律变化（如技能门、操作点协议）>

## 本代目标（按优先序）
1. <任务 A：具体验收标准>
2. <任务 B>
3. <算力富余时的备选>

## 队形与预算（硬性）
- 任务粒度：按 intensity=<intensity> 拆到 <问题/变体/原子实验/矩阵单元/微假设>；high+ 一个 worker = 一个原子单元（数据切片×模型×seed×split），不得把多个单元塞给一个 worker。
- 批量同构任务：high+ 必须检查 `parallel-data-processing`（本地 skill；缺失则到用户 GitHub Hcachild 找），用其
  split→worker JSON→check-only→merge；分片 10–50 条/worker，每批 20–30 个；结果写 `<SWARM>/batches/<batch_id>/`。
- 队形：你(root,d1) → track-lead(swarm-lead,d2) → manager(d3) → worker(swarm-worker,d4)；每层每节点 ≤<128> 子。
- 物理重槽 <SWARM>/locks/heavy_01..NN，并发 ≤<state.intensity_profile.max_heavy_slots>（默认 medium 32；high 128）；轻任务不限；槽位不超卖。
- 预算硬闸：agent_log ≤<state.budget.max_agents>、runs ≤<state.budget.max_experiments>、heavy_hours ≤<state.budget.max_heavy_hours>、代数 ≤<state.budget.max_generations>、并行代理 ≤<state.intensity_profile.max_parallel_agents>；派生前后核对并追加 agent_log。
- 绝对路径；不改共享代码、不 git、不 test 调参、raw 只读。

## 收尾（必须）
1) leaderboard.csv 更新（每任务一行，含技能门与头room 列）；backlog 状态 + 新假设
2) checkpoints/gen_<G>.md
3) 两仓库 docs/experiments.md 追加记录（数据侧有产物则加）
4) state.json（generation=<G>、计数、heavy_hours、active_sessions）
   并运行 `python <SWARM>/tools/session_backup.py export-state --swarm <SWARM>`
   （或 `export-tree --root <你的 SESSION_ID>`）备份在途会话
5) 仅当 <STOP 条件> 满足 → 写 <SWARM>/STOP + 交付报告；否则给出下代建议
6) 上下文充足就自己继续下一代；否则写 checkpoint 并启动继任 root

## 返回给 sponsor（≤40 行）
并发执行情况（派生数/层数）、任务结果表（主指标+CI/基线/技能门/头room）、冻结与证伪清单、
预算、阻塞、Gen-<G+1> 建议。
```

## §2 root → track-lead（派发一条赛道）

```
你是 swarm<N> Gen-<G> track lead（agent_id=<gG-<task>-lead>，role=lead，track=<TASK>，task_id=<ID>）。root=<swarm-root-genG>。
run_token=<SWARM>-g<G>-<task>-lead-<8hex>；开工先跑 session_map.py self --token <run_token>，
把 SESSION_ID 写进 NOTES；每次派生 manager/worker 后，把返回头 `<task id="ses_...">` 记进本 track 的 session 清单。

必读（先读再动手；全部只读）：
1) <DOCS>/{CHARTER,PROTOCOL,ROADMAP}.md
2) <SWARM>/prereg/<相关协议>.md（不可变，唯一口径）
3) <SWARM>/backlog.jsonl 的 <ID> 行；checkpoints 上代
参考代码/结果（只读）：<路径清单>

任务粒度：按 intensity=<intensity> 拆到 <问题/变体/原子实验/矩阵单元/微假设>；每个 worker 一个原子单元，
互斥且不共享写目标；high+ 每个单元一个 fp12。粗任务会浪费并发，细任务会压垮协调。
批量同构任务：high+ 必须用 `parallel-data-processing`（本地 skill；缺失到用户 GitHub Hcachild 找）的
split→worker JSON→check-only→merge；分片 10–50 条/worker、每批 20–30 个，结果写 `<SWARM>/batches/<batch_id>/`。
角色：派生 1 个 manager（task 工具，subagent_type=swarm-lead，agent_id=<gG-<task>-mgr>；prompt 必含完整
worker 规格/硬规则/验收/预算/回报格式），manager 派生 <N> 个 worker（subagent_type=swarm-worker，不得再派生）。
你只做规格传达、落盘校验、产物审查、track 汇总、回报 root；不重复 worker 的活。

硬规则（违反=任务失败）：
- 不改/不删任何既有代码与文件；新脚本只允许新增：<数据侧/模型侧路径>；产物写 <data work / runs 路径>。
- 不 git、raw 只读、不在 test 上调参；test 只一次且 test_uses.jsonl planned→used 登记（fp12 canonical=<...>）。
- 筛查/训练前抢 heavy 槽（python <SWARM>/tools/heavy_lock.py acquire --agent <worker_id> --locks-dir <SWARM>/locks --slots <NN>；完 release；无槽等待）。
- 事件记录：派生/结束/关键节点用 `python <SWARM>/tools/append_jsonl.py <SWARM>/agent_log.jsonl '<json>'` 追加以防并发写坏。
- 预算：本 track ≤<M> 代理；worker ≤<分钟>；不写 leaderboard.csv/state.json（root 独占）。

【本任务规格】N=<N> workers：
w1（<gG-<task>-w1>）<输入路径/字段/预注册规则/输出产物/验收断言>
w2（<gG-<task>-w2>）<独立验收/复算要求/差异阈值与查因要求>
lead 汇总：<tracks/<TASK>/candidates.csv + NOTES.md；变体选择规则（预注册）；失败原因分析>。

【回报 root】最终消息 ≤40 行：状态；产物绝对路径；核心数字表（prev/主指标+CI/基线/required/头room/green）；
用时与 worker 数；阻塞；新假设。
```

## §3 lead → manager（拆分原子实验）

```
你是 <agent_id>（role=manager，parent=<lead_id>，task_id=<ID>，track=<TASK>）。
run_token=<SWARM>-g<G>-<task>-mgr-<8hex>；开工先跑 session_map.py self --token <run_token>，
SESSION_ID 写进 NOTES；派 worker 时给每个 worker 唯一 run_token，并在返回后记录 `<task id="ses_...">`。
你负责把本任务拆为 <2-4> 个互斥原子实验并派 <N> 个 worker（subagent_type=swarm-worker，不得再派生）。
拆分粒度按 intensity=<intensity>：<问题/变体/原子实验/矩阵单元/微假设>；一个 worker 只做一个原子单元；
xhigh+ 的复核/审计单元必须由不同 worker 承担（不能自己产、自己审）。

预注册（binding，lead 冻结于 <lead NOTES 路径>，本层只记录不修改）：
- 变体网格：<逐组合列出>
- 选择规则：<只看 valid；tie-break；选中后才 test 单次>
- green 判定：<指标阈值 + CI + 技能门>
- 对照要求：<回归均值/平凡基线/泄漏敏感性>

批量同构工作：若本任务是"逐条处理大量同构数据"（成千上万条 classify/extract/打标/翻译/清洗），
high+ **必须**加载 `parallel-data-processing`（本地 skill；缺失到用户 GitHub Hcachild 找；再没有就手写 split/merge），
按其"切 10–50 条/片→每片一个 worker 输出 JSON→check-only→合并"模式执行；结果写 `<SWARM>/batches/<batch_id>/`；
一个 manager 挂 20–30 个 worker 分批推进，不必为每条单开子任务；high 抽 3–5% 分片复核，xhigh+ 随机 1–2% 双跑比对。
每个 batch worker 除结果 JSON 外，还要写 `runs/<agent_id>/NOTES.md`（分片号/条数/结果路径/check/session id）；manager 写批次汇总 NOTES。

硬规则：<同上：不改既有文件/新增脚本路径/产物落位/不 git/raw 只读/test 单次登记/抢槽/append_jsonl/预算>。

【worker 规格】
w1：<精确输入、命令、输出、验收断言>
w2：<独立复算/交叉核对，差异容差与查因>

汇总：<valid_summary.csv、选中设定与理由、test 单次结果、独立复算、失败原因分析>。
【回报 lead】≤40 行：状态；各 worker 结论；核心数字；产物路径；阻塞；新假设。
```

## §4 manager → worker（原子实验，叶子）

```
你是 <agent_id>（role=worker，parent=<mgr_id>，task_id=<ID>，track=<TASK>）。
run_token=<SWARM>-g<G>-<task>-<worker>-<8hex>；开工第一步：
python <SWARM>/tools/session_map.py self --token <run_token>
把 SESSION_ID / PARENT_ID 写进 NOTES 与最终回报首行（缺 session id 视为记录不完整）。
只做这一件事，不得派生任何子代理。

任务粒度：<原子单元：数据切片/模型/seed/split/复核>；只做这一个单元，不合并其他单元。
输入：<绝对路径清单 + 字段/行数/校验>
任务：<可执行的明确步骤；预注册规则写死，不得按结果更改>
输出：<runs/<agent_id>/ 下 NOTES.md, metrics.json, cmd.txt, artifacts/> + <数据侧产物路径>
验收：<断言：复算一致/命中期望数字/sha1 校验/QC 条目>
预算：<轻/重 分钟数>；重任务先抢槽：python <SWARM>/tools/heavy_lock.py acquire --agent <agent_id> --locks-dir <SWARM>/locks --slots <NN>（完 release）
纪律：不改既有文件；不 git；raw 只读；test 只用一次（框架自动登记 planned→used）；事件用 append_jsonl.py 追加 agent_log。

NOTES.md 必含：目标 / 任务粒度（原子单元）/ fp12 / 数据版本 / 命令 / 结果（主指标+CI+prevalence）/ 产物缩短 sha1 / 结论 / 新假设 / 遗留异常。
批量任务：除 `batches/<batch_id>/results/chunk_XXX.json` 外，NOTES 还要写分片号/条数/结果路径/check 状态/session id。
【回报 manager】≤40 行。
```

## §5 恢复 Task Agent 对话（中断后）

**首选：极简续跑。** 用原 `task_id=<ses_...>`（就是子代理 session id）恢复同一会话，prompt 只写：

```
继续
```

- 它保留完整上下文（目标/规格/纪律/已做工作），自己知道做到哪、下一步是什么。
- **非必要不要回复一大堆话**：不要重发背景、规格、纪律或已完成事实——浪费 token，还可能打乱它的判断。
- 只在需要纠偏/补充关键约束时加最少一句，例如：
  - `继续；先完成收尾（NOTES/登记），再回报。`
  - `继续；不要重跑已完成的 <X>，直接从 <Y> 接着做。`

**session id 丢了怎么办**（按优先级，只读）：
1. `runs/<agent_id>/SESSION_ID` 或 `agent_log.jsonl` 的 `session_id`；
2. `python <SWARM>/tools/session_map.py children --parent <你的 session_id>`；
3. `python <SWARM>/tools/session_map.py self --token <run_token>`（token 在 prompt 里）；
4. `python <SWARM>/tools/session_map.py agent --agent-id <agent_id>`。
5. 禁：`opencode session list`（不列子代理）、按 `time_updated` 猜（并发会串）。

**如果会话真的被删了**（父会话删除会级联删子会话，实测）：
- 有备份：`python <SWARM>/tools/session_backup.py import --file <SWARM>/sessions/<agent_id>.json`
  → 实测恢复同一 session id，再按原 id 发"继续"；
- 无备份：只能按 `NOTES.md` + checkpoint + 产物重建 brief（不要假装是同一会话）。
- **警告**：对已删除的 id 调 `task` 不会报错，而是**静默新建**一个空会话并返回新 id。
  恢复后必须核对 `<task id="...">` 是否等于请求的 `task_id`；不等就是没恢复。

**嵌套链**：root 恢复后，让 root 用同样方式（对它的子代理说"继续"）逐级恢复；
sponsor 不要越过 root 逐条重建所有子代理。上下文彻底丢失时，才用下面的兜底重建 brief。

**兜底（仅当原会话/task_id 不可恢复时）**：发重建 brief，只附最少必要事实，并声明"已完成项无需重跑"：

```
你是 <项目> swarm<N> root curator（Generation <G>），之前被意外中断，继续收尾。
- 已完成（无需重跑）：<逐条：实验/数字/产物路径>
- 在途/未完成：<现场状态>
- 收尾要求：<leaderboard/state/checkpoint/登记/STOP 判定>
纪律不变：预注册、test 单次、技能门、预算硬闸、绝对路径。
回报 ≤40 行。
```

## §6 嵌套能力验证（配置后一次性）

```
这是嵌套能力验证 + session id 验证，只做一件事（≤3 分钟），不要做任何其他事：
1) 用 task 工具派生一个 subagent_type=swarm-worker 的子代理，其 prompt 为：
   "run_token=NESTED_TEST_<8hex>。请创建目录 <验证目录>（若不存在），把内容 nested-ok 写入 result.txt（无换行）；
    再运行 python <SWARM>/tools/session_map.py self --token <该 run_token>；
    只回复两行：SESSION_ID=<命令输出的 SESSION_ID>、nested-ok。"
2) 若 task 工具不可用/调用失败/类型不存在：返回一行 `TASK_TOOL=no reason=<简短原因>`。
3) 若成功：记下 task 返回头 `<task id="ses_...">`，检查：
   - result.txt 存在且内容为 nested-ok；
   - 子代理回复的 SESSION_ID 与返回头 id 一致。
   回复一行：
   `TASK_TOOL=yes CHILD_SESSION=<ses_...> SESSIONS_MATCH=<true/false> FILE_OK=<true/false>`
```
