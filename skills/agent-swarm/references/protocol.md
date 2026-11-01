# 运行时契约（Runtime Protocol）

所有 swarm 代理必读。以下 `<SWARM>` 指 `swarm<N>/` 运行时目录的绝对路径，
`<DOCS>` 指 `docs/swarm<N>/`。根目录与编号在建 swarm 时确定，之后不得漂移。

## 0. 角色、深度与分支

| 角色 | 类型 | 职责 | 派生 |
|---|---|---|---|
| Sponsor | 主会话（primary） | 建宪章、发 root brief、每代收口（commit/push docs）、与用户决定收敛 | 只派生 root |
| root curator | `swarm-lead` (d1) | 写主 PLAN→评审冻结→派 lead；Cycle 调度、合并 leaderboard、写 checkpoint、停止与接棒裁决 | ≤128 子 |
| lead-1 / track-lead | `swarm-lead` (d2) | 写子树 PLAN→评审→并行派 manager；一条赛道汇总结果 | ≤128 子 |
| manager | `swarm-lead` (d3) | 写/更新任务 PLAN，把任务拆为 PLAN 中全部原子单元，并行派 worker、收集与初验 | ≤128 子 |
| worker | `swarm-worker` (d4) | 只做一个原子实验/分析；**不得派生**（tools.task=false） | 0 |

- 实际谱系深度 ≤6；全局 `subagent_depth: 12`（约 11 级接棒链）。
- root 上下文将满：写 checkpoint（状态/榜单/待办/预算/建议），派生继任 root 交接，自增深度。
- 子代理类型一律 `swarm-lead`（可派生）/ `swarm-worker`（叶子），不用 `general`。
- 强度档位见 `references/intensity.md`（默认 medium）。high 起增加 **queue-master**（128 重槽排队/优先级/stale lock）；xhigh 起增加**独立审计 root**；max 起增加 **meta-curator + portfolio manager**。
- **root 第一波必须派 `lead-1`**（用户指定的主 lead）；其他 lead 按 PLAN 并列。lead/manager 按 PLAN
  并行派生下一层，禁止"派一个、等一个"。

## 1. 启动契约（每个代理 prompt 必含）

`agent_id`、`role`、`track`（任务 ID 或 meta）、`task_id`、`parent`/`root`、
`depth=<1..N>`、`run_token`（唯一串，如 `<swarm>-g<G>-<agent_id>-<8hex>`）、
`granularity`/`task_scope`（按强度档位拆到原子单元：变体/数据切片/模型/seed/split/复核）、
`PLAN` 路径（`cycles/<C>/.../PLAN.md`；本代理对应行/子树）、并行波次、bash 时间盒（`<=60s`）、
必读文件清单、输入路径、验收标准、预算（分钟 + 是否抢重槽）、停止规则；
并标明该代理是否被 `never_stop_scope` 覆盖（决定是否附 §0.1 永不终止块）。
每个 worker 只做一个原子单元；任务粒度见 `references/intensity.md` §2.1。

开工三步：
1. 读 `cycles/<C>/PLAN.md`（含本代理的完整任务与下一层规格）与相关运行时文件。
2. 读 `<DOCS>/{CHARTER,PROTOCOL,ROADMAP}.md`。
3. 自报 session id：`python <SWARM>/tools/session_map.py self --token <run_token>`，
   **开工即写** `runs/<agent_id>/SESSION_ID`（一行 `ses_...`），再写进 NOTES 与回报。

- **绝对禁止提问工具**：任何代理（含 sponsor 在 swarm 执行链中）不得调用 `question`/ask 工具，
  不得向用户或父代理提问；不确定项写入 `PLAN.md` 的 `Assumptions` 与 NOTES，按最小风险路径继续。

## 2. 运行时目录（`<SWARM>/`，gitignore）

```
state.json                 全局指针（root 独占写）
agent_log.jsonl            代理启动/结束日志（所有代理用 tools/append_jsonl.py 追加）
backlog.jsonl              任务/假设队列（lead+ 追加；owner 更新自己条目的 status）
leaderboard.csv            已验证榜单（root 独占写）
track_notes/<track>.md     赛道叙述（track-lead 写）
tracks/<track>/candidates.csv  赛道候选结果（track-lead 写）
runs/<agent_id>/           单任务产物（worker 写：NOTES.md, metrics.json, cmd.txt, SESSION_ID, artifacts/）
sessions/<agent_id>.json   会话导出备份（opencode export；删除会话前/每代 checkpoint 生成）
batches/<batch_id>/        批量处理（chunks/ + results/ + out/ + manifest.json；不写仓库根）
claims/<task_id>.claim     任务领取（独占创建）
registry/<fp12>.done       实验指纹注册（防重复）；复现用 .repro_<agent_id>
locks/heavy_01..NN.lock    重任务物理槽（独占创建；内容 agent|iso|eta_min）
checkpoints/gen_<n>.md     root 每代 checkpoint
cycles/<C>/                xhigh+ 每 Cycle：PLAN.md / PLAN_REVIEW.md / PLAN.amend.*.md / DISPATCH.jsonl / RESULTS.md
cycles/<C>/leads/<id>/PLAN.md       lead 子树计划（与主 PLAN 一致）
cycles/<C>/managers/<id>/PLAN.md    manager 任务计划（worker 派发表）
prereg/                    实验预注册（协议/任务卡模板；PLAN 见 cycles/）
test_uses.jsonl            test 使用登记（planned→used 两行）
tools/                     append_jsonl.py / heavy_lock.py
STOP                       出现即全体停止派生
```

**路径纪律**：全部使用绝对路径；严禁在仓库根创建 `runs/`、`track_notes/` 等目录。

## 3. 领取、防重、防冲突

- **领取**：`New-Item <SWARM>/claims/<task_id>.claim -ItemType File -ErrorAction Stop`；
  已存在且 <6h 则换任务；>6h 视为死代理，先改名 `.stale` 再建。
- **防重指纹**：`fp12 = sha1(task_card|features|model|params|index|seed|cohort)[:12]`；
  跑前查 `registry/<fp12>.done`（存在则跳过），完成后创建。high+ 的每个原子单元一个 fp12；
  同一 fp12 只允许一个 claim，细粒度任务没有指纹 = 必然重复。
- **唯一写权**：worker 只写自己 `runs/<id>/` 与 claims；track-lead 只写本 track 文件；
  root 独占 leaderboard/state/checkpoints/tracks 上层。禁止互写、禁止改共享代码。

## 3.1 批量处理契约（high+）

适用于"扁平、同构、数量大"的逐条处理（分类/提取/打标/翻译/清洗/校验）。优先用
`parallel-data-processing` skill 的 `split_data.py` + `merge_results.py`；缺失时按同一模式手写。

- **粒度**：`batch-shard`（10–50 条/worker），覆盖默认原子实验粒度；每批 20–30 个并行。
- **路径**：`<SWARM>/batches/<batch_id>/{chunks,results,out,manifest.json}`；不写仓库根。
- **领取/防重**：一个分片一个 claim；`fp12 = sha1(manifest|chunk_id|规则版本)[:12]`，已有结果且校验通过则跳过。
- **校验**：先 `merge_results.py --check-only`；每个分片有 JSON、可解析、ID 数量/顺序与 manifest 一致；
  **未通过不得合并**；失败只补跑对应分片。
- **审计**：high 抽样 3–5%；xhigh 随机 1–2% 分片双跑比对；max/infinite 自动审计 + 异常重跑。
- **保真**：原文/问题字段从 manifest 回填，不依赖 Agent 转写；Agent 只写新增结果字段。
- **记录**：每个分片 worker 除结果 JSON 外，还要写 `runs/<agent_id>/NOTES.md`（分片号/条数/结果路径/check 状态/session id）；manager 写批次汇总 NOTES。

## 3.2 PLAN.md 规划门与 Cycle 契约（所有强度；xhigh+ Cycle）

- **先 PLAN 后派发**：root 写 `cycles/<C>/PLAN.md`，lead/manager 写本子树 PLAN；
  必须 review（`PLAN_REVIEW.md` 或 PLAN 的 `## Review` 段），修订后冻结 `plan_hash`，才能 `task` 派生。
  **未冻结 = 不得派发**。每个 task 批次/波次前都要确认对应 PLAN 行存在且已冻结；任务变了先 `PLAN.amend`。
  `plan_hash = sha256(Directions|Dispatch|Waves|Bash/Jobs|Audit)[:16]`，冻结后写入 PLAN 与 checkpoint。
  非 xhigh+ 的 `<C>` 可用外层代/批次 id（如 `G0001`/`B001`），目录统一 `cycles/<C>/`。
- **PLAN 内容**：全部已想到方向；完整 Dispatch Tree（到 worker，写清每个 SubAgent 的下一层任务）；
  并行波次/DAG；bash/长任务；审计时间盒；每个 worker 任务的输入/输出/验收/预算/fp12/owner；
  不确定的输入/口径写入 `Assumptions`，不得调用提问工具等待确认。
- **xhigh+ 无延期**：Directions 覆盖全部已想到方向（不是 2–4 个）；正文禁止“下一步/可选项/open/TBD/
  待定/后续/备选/TODO”；不可行方向本 Cycle 派 `probe`，结论写 `RESULTS.md` 的 closed 列。
- **Cycle**：仅 xhigh+；每 Cycle 结束写 `RESULTS.md`，据结果更新下一 Cycle PLAN；xhigh/max 无固定
  Cycle 上限，infinite 无限；`max_generations` 在 xhigh+ 只作外层 checkpoint 计数，不限制 Cycle。Cycle 关闭 =
  所有 Directions 有结果（keep/kill/probe-more/closed）或外部 blocked；未完成方向同 Cycle 续派，
  不得滚到下一 Cycle。
- **计划变更**：`PLAN.amend.<n>.md`，重新 review + 冻结；可在 Cycle 内取消/改派在途 SubAgent，
  但必须记录原因、影响的 agent/session、新任务与验收；禁止静默改任务。
- **并行**：无依赖 SubAgent 同波；依赖 DAG 无环；禁止“派一个、等一个、再派下一个”。
- **派发记录**：每次 `task` 派生后追加 `cycles/<C>/DISPATCH.jsonl`
  （cycle/wave/parent/agent_id/subagent_type/task_id/session_id/status），用于核对 PLAN 是否真的全并行执行。
- **执行**：单次 bash `<=60s`；长任务后台 + 轮询；独立命令同一消息并行。
- **审计**：并行、抽样、只审 green/晋级；审计并发 `<= 生产并发 20%`，审计墙钟 `<=20%` Cycle 生产墙钟；未审 green 标 `unverified`。

## 4. 资源与算力

- 重型训练（全量/长序列/多 seed）必须持槽：`scripts/heavy_lock.py acquire --agent <id> --locks-dir <SWARM>/locks --slots NN`；
  无槽先做轻任务或等待；槽 start 超 `--stale-min`（默认 150min）自动失效可重抢；完事 `release`。
- 重任务并发 = min(物理配额, `intensity_profile.max_heavy_slots`)：low 4 / medium 16–32 / high 128 / xhigh 256–512 / max 1024+ / infinite 弹性。槽位不超卖；high 起由 queue-master 统一排队，xhigh 起接中央队列/多机调度，`heavy_lock.py` 只做本地闸门。
- 子集筛查（如 ≤2000–3000 人）先跑；只有效应 > 2× 划分噪声才晋级全量；子集→全量缩水 >0.05 要复核。
- 单 worker 预算：轻 ~15min；重任务 low/medium ~90–180min，high 可到 2–8h，xhigh+ 按队列分段并写 checkpoint；超预算先报告再继续。
- **bash 时间盒**：每次调用 `<=60s`（显式 `timeout<=60000`）；独立命令同一消息并行发，不用 `&&` 串独立命令。
- **长任务**：必须后台启动 + 轮询；PLAN 写明启动命令/日志/PID/预计时长/恢复方式；禁止一个 bash 调用阻塞等训练完成。
- **并行派发**：无依赖 SubAgent 同一波次并行；依赖写显式 DAG，依赖解除即并行；禁止串行排队。
- **审计并行**：审计与生产并行；只审 green/晋级；审计并发 `<= 生产并发 20%`，审计墙钟 `<= Cycle 生产墙钟 20%`。

## 5. 预算与派生纪律（硬闸）

派生任何子代理前检查（任一越限 → 停派生、写 checkpoint、退出）：

```
cycles/<C>/PLAN.md 存在 且 status=frozen 且 plan_hash 有值   （PLAN 门）
agent_log.jsonl 行数 < state.budget.max_agents                 （按强度档位）
runs/ 数量          < state.budget.max_experiments             （按强度档位）
heavy_hours_used    < state.budget.max_heavy_hours             （按强度档位）
generation          < state.budget.max_generations             （high 及以下；xhigh+ 仅作外层 checkpoint 计数）
并行代理数          < state.intensity_profile.max_parallel_agents
重槽占用            < state.intensity_profile.max_heavy_slots
<SWARM>/STOP 不存在
```

> 默认 **medium**：`max_agents=80, max_experiments=500, max_heavy_hours=2000, max_generations=3, max_parallel_agents=30, max_heavy_slots=32`。其他档位见 `references/intensity.md` 或 `state.intensity_profile`。
> 任务数 ≈ 累计代理数：high+ 一个 worker 只做一个原子单元；把多个单元塞给一个 worker 会让粒度和预算失真。
> **PLAN 门**：未 review、未冻结 `plan_hash` 不得派生；xhigh+ 的 Directions 必须覆盖全部已想到方向，
> 且正文无延期项（禁词表见 `references/prompts.md` §0.2）。计划变更走 `PLAN.amend.<n>.md`。
> **infinite 无限执行 scope**：只有被 `never_stop_scope` 覆盖的代理（默认仅 depth-1 root）的 prompt
> 必须原样包含 `references/prompts.md` §0.1 全文；未覆盖的 lead/manager/worker 不加块、正常有限返回。
> 用户可明确设 `all`（所有 SubAgent 无限）或 `depth:N`（深度 `<=N` 无限）。
> **infinite 预算越限**：属外部信号——停派生/降并发/写 checkpoint，等 sponsor 月度重置或显式 `STOP`；
> 不得写成"任务完成"，也不得静默结束执行体。
> **xhigh/max 预算越限**：同样属外部信号——停派生/写 checkpoint 等 sponsor 决策；不得把预算边界写成 Cycle 完成。

同 manager 的 worker 必须任务互斥（不同 task_id / 指纹）。

## 6. 记录契约

- worker 结束必须落盘 `runs/<agent_id>/NOTES.md`（≤40 行摘要即可，含：
  目标 / 数据版本 / 命令 / bash 调用次数+最长耗时（`<=60s`）/ 长任务 PID+日志 / 结果（主指标 + CI +
  prevalence + 辅助口径）/ 产物路径与 sha1 / 结论 / 新假设 / 遗留异常 / `SESSION_ID`）。
- **PLAN/Cycle 记录**：root 每 Cycle 写 `cycles/<C>/PLAN.md`、`PLAN_REVIEW.md`、`RESULTS.md`；
  lead/manager 写本子树 `PLAN.md`。worker 的 NOTES 必须写明对应的 PLAN 行号或子树 PLAN 路径。
- **session id 落盘**：`task` 工具结果头 `<task id="ses_...">` 即子代理会话 id（= 续跑 `task_id`）；
  父代理收到后立刻追加 `agent_log.jsonl`（`event=spawn, agent_id, session_id, parent_session_id,
  depth, never_stop`）并写 `runs/<agent_id>/SESSION_ID`。子代理用 `run_token` 自行反查，写进 NOTES。
- 返回父代理的**最终消息 ≤40 行**（被 `never_stop_scope` 覆盖的执行体改为**进度快照**，不是最终消息：
  写当前状态+下一动作，关键进度先落 NOTES/`agent_log.jsonl`，然后继续执行）：
  状态、关键数字、文件路径、新假设、下一建议、`SESSION_ID`。
- 每个 lead 在 NOTES.md 顶部记录自己的 `task_id`/`SESSION_ID`（可恢复）；root 每代写
  `checkpoints/gen_<n>.md`（执行与预算、榜单增量、在途代理的 agent_id→session_id、审计裁决、阻塞、下一 Cycle 输入）。
- **会话备份契约**：root 每代 checkpoint 时运行
  `python <SWARM>/tools/session_backup.py export-state --swarm <SWARM>`
  备份 `state.active_sessions`；sponsor 收口时用
  `export-tree --root <root_session>` 备份整棵会话树。删除任何会话前必须先
  `session_backup.py export --session <ses_...> --agent-id <id> --out-dir <SWARM>/sessions`。
  恢复：`session_backup.py import --file <...>.json`（实测恢复同一 session id，含父会话已删的孤儿）。
  备份是导出时快照，运行中会话可能缺最后一轮；关键结论仍以 NOTES/checkpoint 为准。
- Sponsors 每代把 `docs/experiments.md` 记录 + 交付物 commit/push（数据、权重、运行时永不入库）。

## 7. 评估口径（唯一合法口径）

- **预注册**：变体网格与选择规则先写入 NOTES 再执行；选择只用 valid。
- **test 单次**：valid best-F1（或预注册的等价规则）选定后，test 评估一次；
  比较必须登记 `test_uses.jsonl`（planned → used，含 canonical 与 fp12）。
- **技能门（skill gate）**：F1 > max(all-positive, 简单规则基线)，AUROC > 最佳规则基线；
  未过门 → 只作描述性数字，不计达标。
- **头room 分析**：按 prevalence 计算"达目标 F1 所需 AUROC"（required-AUROC），
  与观测 AUROC 比较：gap ≤0.03 高头room / 0.03–0.08 可及 / >0.08 低（冻结或换设定）。
- **晋级门槛（只对 green/晋级候选）**：全量 + 预注册 + ≥3 seeds + 患者/事件簇 bootstrap CI（1000）+ 亚组 FDR + 泄漏审计。
- **双重 split**：达标任务必须在 ≥2 个独立 split 复现才可宣称/写 STOP。
- **反作弊**：不得用 test 调参；亚组预注册 + FDR；新标签必须过泄漏审计（时间锚、回归均值、事件对齐）；
  高 prevalence 队列须同队列平凡基线对照，防流行度伪影。
- **审计效率**：审计与生产并行；只审 green/晋级候选；抽样优先；只验证关键断言
  （指标/泄漏/基线/复现），不做全量代码 walkthrough；审计并发 `<= 生产并发 20%`；
  审计墙钟 `<= Cycle 生产墙钟 20%`；超时记 `unverified` 并继续；禁止串行全量复核。未审 green 不得宣称达标。

## 8. 停止与接棒

- 主目标达成（达标 + 技能门 + 双 split 复现 + 审计通过；**非 xhigh/max/infinite**）→ 立即写 `<SWARM>/STOP`、
  生成复现任务清单（REPRODUCE_gen<n>.md）、报告 root/sponsor，停止扩大探索。
- 穷举收敛（**非 xhigh/max/infinite**）：连续多代无新达标且无未测杠杆 → 上界报告（每任务诚实上限 + 证据链 + 已证伪清单），
  状态置 `converged`，停止。
- root 上下文将满：写 checkpoint → 派生继任 root（深度+1）→ 交接包 = checkpoint + state +
  `cycles/<C>/PLAN.md` + `RESULTS.md` + 待办。
- 用户可随时创建 `STOP` 或口头停止；假 STOP（不过技能门）按完整性宪章撤销并记录。
- **infinite 档**：被 `never_stop_scope` 覆盖的执行体不得自我终止；主目标达成只转验证/反例搜索/
  边界回归/加固/扩展验收标准，穷举收敛只转"换杠杆/降级方案/重新分解"，均不写 `STOP`、不输出最终消息。
  默认 `never_stop_scope=root`：只有 depth-1 root 无限；lead/manager/worker 有限返回，保证 root 收结果。
  用户可设 `all` 或 `depth:N`。只有用户/Sponsor `STOP`、预算硬闸、安全红线可以收口，root 在 checkpoint
  记录 `external_stop=<原因>`。被覆盖的派生/续跑/重建 prompt 必须原样携带 `references/prompts.md` §0.1 全文。
- **xhigh/max Cycle 档**：Cycle 不设固定上限；主目标达成不自动停，转下一 Cycle 的验证、反例、边界与
  扩展验收；只有预算硬闸、用户/Sponsor `STOP`、安全红线可以收口。每个 Cycle 结束必须写 `RESULTS.md`
  并更新下一 Cycle `PLAN.md`。

## 9. 恢复检查清单

1. `state.json`（generation/status/计数）与 `agent_log.jsonl` 尾部对齐；
2. `runs/` 中无 NOTES 的目录 = 在途任务；`claims/*` 与之一一对应；
3. 残留 `locks/*`：内容 agent 已消亡 → `.stale` 清理；
3.1 **PLAN/Cycle 恢复**：先读 `cycles/<C>/PLAN.md`、`PLAN_REVIEW.md`、`RESULTS.md`；
   PLAN 缺失或未冻结 → 先补 PLAN + review + 冻结再派发；xhigh+ 必须全量方向、无延期项。
4. **恢复 Task Agent 对话优先、消息极简**：用原 `task_id=<ses_...>`（= 子代理 session id）
   续跑同一会话，prompt 只需 "继续"（非必要不发大段背景/规格）；嵌套链由各级自己逐级恢复；
   `intensity=infinite` 且该代理被 `never_stop_scope` 覆盖时，"继续"之后必须原样附上 §0.1 全文；
   未覆盖的代理按普通有限任务继续；
   仅当会话不可恢复时，才发重建 brief（最少事实 + 声明已完成项无需重跑）；
   `task` 被外部打断时返回 `Task cancelled` 且**不带 id**，按第 5 步反查后再续跑。
5. **session id 解析**（只读，opencode 运行中可用）：
   - `runs/<agent_id>/SESSION_ID`、`agent_log.jsonl` 的 `session_id`；
   - `python <SWARM>/tools/session_map.py children --parent <session_id>`；
   - `python <SWARM>/tools/session_map.py self --token <run_token>`（token 在 prompt 里）。
   - 禁：`opencode session list`（不列子代理）、按 `time_updated` 猜（并发会串）。
6. **恢复边界（实测 2026-10-22，opencode 1.19.x）**：
   - abort/取消当前轮、客户端重启 → 同 session id 可续（"继续"保留上下文）；
   - 删除父会话 → **级联删除全部子会话**（token/children 查不到）；
   - 用已删除的 task_id 续跑 → `task` **静默新建** session（返回头 id ≠ 请求 id），上下文为空；
   - 有 `sessions/<agent_id>.json` 备份 → `session_backup.py import` 恢复**同一 session id**；
   - 无备份且会话已删/DB 损坏 → 只能按 NOTES/checkpoint 重建，不是同一对话。
   - **恢复后第一步**：核对 `task` 返回头 id == 请求的 `task_id`；不等则视为未恢复。
   - 同一会话也可能 compact/截断而丢中间细节；恢复以 NOTES/checkpoint 为事实源，不依赖对话记忆。
   - 备份节奏按强度：low 结束时；medium/high 每代 `export-state`；xhigh/max/infinite 每波 `export-tree` 或持续备份。
7. 完成后补 leaderboard/state/checkpoint，再启动下一代。
