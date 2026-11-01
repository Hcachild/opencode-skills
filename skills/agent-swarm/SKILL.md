---
name: agent-swarm
description: 'Run long-running iterative research/experiment campaigns as a nested-subagent swarm (Agent 集群/蜂群): sponsor → root curator → track-lead → manager → worker generations, with a mandatory PLAN.md planning/review gate, xhigh+ Cycle iterations, CHARTER/PROTOCOL/ROADMAP governance, backlog/leaderboard/checkpoint runtime, fingerprint & test registration, skill gate, budget gates and STOP rules. Use when the user asks to 启动swarm/开集群/长跑实验/持续迭代研究/派子代理并行做实验/恢复被中断的swarm, or mentions "Generation N","Cycle","PLAN.md", root curator, swarm-lead/swarm-worker, or a docs/swarm*/ + swarm*/ directory pair.'
---

# Agent Swarm —— 嵌套子代理长跑研究集群

把「长期迭代研究/实验」组织成一个可恢复、可审计、可收敛的树状子代理集群。
来自真实长跑实践（MOVER-SIS 研究：多波 swarm、数百子代理/实验，产出过达标任务，
也以"穷举证伪 + 上界报告"诚实收敛）。

## 何时使用

- 目标需要**大量并行实验/分析**，单代理在时间/上下文内完不成（用户说"开 N 个 Task Agent 持续迭代"）
- 需要**跨多轮（generation / xhigh+ Cycle）持续探索**，每轮基于上轮结果调整方向
- 需要**可复现、可审计**的纪律：预注册、防重复、单次 test、预算硬闸、技能门
- 用户提到 "swarm/集群/长跑/大范围探索/发散探索/PLAN.md/Cycle/规划"，或已有一对 `docs/swarmN/`（宪章）+ `swarmN/`（运行时）

不适合：单次线性任务；目标模糊、无法定义验收标准与平凡基线的任务。

## 强度等级（默认 medium）

用 `intensity` 控制队形、并发、预算与审计强度；详见 `references/intensity.md`。
**等级越高越严格**，不能降低预注册/test 单次/技能门/会话备份等硬规则。

| 等级 | 重槽并发 | 累计代理 | 墙钟 | 重槽时 | 典型场景 |
|---|---:|---:|---|---:|---|
| low | 4 | 1–8 | 15m–4h | 8–64 | 单点核查 |
| **medium（默认）** | 16–32 | 30–80 | 1–3 天 | 500–2,000 | 小规模多假设筛选 |
| high | **128** | 200–600 | 1–2 周 | 10,000–30,000 | 标准长跑研究 |
| xhigh | 256–512 | 800–2,500 | 3–8 周 | 50,000–150,000 | 论文级/多中心攻坚 |
| max | 1,024+ | 3,000–10,000 | 2–6 个月 | 200,000–800,000 | 探索型大科学/穷举 |
| infinite | 弹性 1,024–4,096 | 20,000+ | 持续 | 滚动 10–50 万/月 | 常驻研究系统 |

- 默认 **medium**；`init_swarm.py` 不传 `--intensity` 时按 medium 生成预算。
- **任务粒度随强度上升**：low 问题/脚本级、medium 变体级、high 原子实验级（一个数据切片×模型×seed×split = 一个 worker）、xhigh 矩阵单元+独立复核、max 微假设、infinite 持续微任务。高等级用粗任务 = 代理空转；低等级切太细 = 协调爆炸。backlog 行数应≈任务数（medium 30–80、high 200–600、xhigh 800–2,500、max 3,000–10,000）。
- **high 起需要 queue-master** 专管 128 重槽排队；xhigh 起接中央队列/多机调度，`heavy_lock.py` 只做本地闸门。
- 强度是**上限**，不是必须用满；槽位不超卖，槽时到 80% 暂停派生、100% 硬停（infinite 下等待 sponsor 月度重置或显式 `STOP`，不得伪装成完成）。
- high+ 自检清单（批量 skill、嵌套链、session id、备份、NOTES）见 `references/intensity.md` §2.3。
- 强度可按 track 覆盖（如 max 里跑 low 筛查 + high 验证），但升级只能由 sponsor 决定。
- **infinite 无限执行范围可配（默认只给 depth-1 root）**：`never_stop_scope` 决定谁必须带
  `references/prompts.md` §0.1 的「永不终止执行引擎」全文：
  - `root`（默认）：只有 sponsor 直接派生的**第一个深度 SubAgent（depth=1，root curator）**无限执行；
    lead/manager/worker 是有限任务，正常返回结果，root 才能持续 Cycle。
  - `depth:N`：深度 `<=N` 的执行体无限（`depth:1` 等价 root）。
  - `all`：所有 SubAgent 无限执行（仅当用户明确指定）。
  被 scope 覆盖的执行体：每个派生/续跑/重建 prompt 必须原样包含 §0.1，缺块不得派出；未被覆盖的
  执行体不加块、按正常有限任务返回。该块只禁止执行体**自我终止**；用户/Sponsor 的 `STOP`、预算硬闸、
  安全红线属于外部信号，收到时按 PROTOCOL 收口。root 无限时可能长期不返回最终消息；sponsor 通过
  NOTES/`agent_log`/checkpoint 监控，必要时外部 `STOP`/abort。

## 架构与角色

```
Sponsor（主会话，你自己）        —— 建宪章、发 root brief、每代收口 commit、决定收敛
└── root curator (swarm-lead)   —— 写主 PLAN→评审冻结→派 lead；Cycle 调度/合并/checkpoint/停止裁决
    ├── lead-1 / track-lead (swarm-lead) —— 写子树 PLAN→评审→并行派 manager；汇总本赛道
    │   └── manager (swarm-lead)—— 写/更新任务 PLAN→并行派 worker
    │       └── worker (swarm-worker) —— 只做一个原子实验；bash≤60s；叶子，禁止派生
    └── ...（每层每节点可并行 ≤128 子代理；实际深度 ≤6，subagent_depth=12 支持接棒）
```

- **代理并发**：每层每个节点均可派生至上限（root/lead/manager 一视同仁，如 128）；首代可全量并行分派
- **并行优先**：无依赖的子代理必须同一波次并行派生；串行只允许用于 PLAN 中显式声明的依赖链
- **infinite 默认只 root 无限**：depth-1 root 带 §0.1 永不终止；lead/manager/worker 正常有限返回，
  否则 root 收不到结果、无法推进 Cycle。只有用户明确 `all` 才让所有 SubAgent 无限。
- **重计算**另受物理槽限制（`locks/heavy_XX`，按机器核数定，如 ≤16），与代理并发无关
- **bash 执行纪律**：单次 bash 调用 `<=60s`（显式传 `timeout<=60000`）；独立命令同一消息并行发；
  长任务须后台启动 + 轮询，PLAN 写明启动命令/日志/PID/预计时长/恢复方式
- root 上下文将满时派生**继任 root**接棒（写 checkpoint、深度+1）

**与批量处理 skill 协同（high+ 强制检查）**：

- 对**扁平的大批量同构工作**（成千上万条逐条分类/提取/打标/翻译/清洗/校验），使用 `parallel-data-processing` 的
  "切分片 → 每片一个 Task Agent 输出 JSON → check-only 校验 → 合并"模式；一个 manager 挂 N 个 worker，
  **不要为每条数据单开 track 或 worker**。
- 档位要求：low 不适用；medium 可用；**high 起必须检查并按需使用**；xhigh 起随机 1–2% 分片双跑比对；
  max/infinite 自动审计与去重。
- 获取顺序：本地 `~/.config/opencode/skills/parallel-data-processing/` → 用户 GitHub（Hcachild）中的批量处理
  skill/repo → 都没有则按同一模式手写分片/合并脚本（split → worker JSON → check → merge）。
- 分片 10–50 条/worker，每批 20–30 个并行；结果写 `<SWARM>/batches/<batch_id>/{chunks,results,out}`，
  不写仓库根；`manifest.json` 是回填与校验的唯一依据。

## 一次性基建（每个研究目标一套）

1. **配置子代理**（全局/项目 `opencode.json`，片段见 `references/templates.md` §1）：
   `subagent_depth`、`swarm-lead`（`task=true`，可派生）、`swarm-worker`（`task=false`，叶子）。
   **必须重启 opencode 生效**；重启后先做嵌套验证（spawn swarm-lead → 它再 spawn swarm-worker 落盘验证）。
2. **定义验收标准与技能门**：什么算达标（指标+CI 要求）、必须打败哪些平凡基线（all-positive、简单规则、现状态）。目标值写进 CHARTER。
3. 建 `docs/swarm<N>/`：`CHARTER.md`（使命/强度等级/任务卡/技能门/反作弊/停止条件/规划与 Cycle）、`PROTOCOL.md`（角色/路径/PLAN 门/Cycle/领取/锁/预算/并行/审计时间盒/记录契约）、`ROADMAP.md`（阶段/里程碑/首代种子/剪枝）——骨架见 `references/templates.md` §2–4，**入库并 commit**。
4. 建 `swarm<N>/` 运行时（**gitignore**）：`state.json`（含 `intensity`/`never_stop_scope` 与派生预算）、`agent_log.jsonl`、`backlog.jsonl`、`leaderboard.csv`、`checkpoints/`、`cycles/`（xhigh+ 的 `PLAN.md`/`PLAN_REVIEW.md`/`RESULTS.md`）、`runs/`、`claims/`、`registry/`、`locks/`、`prereg/`、`test_uses.jsonl`、`tools/`（复制本技能 `scripts/append_jsonl.py`、`scripts/heavy_lock.py`、`scripts/session_map.py`、`scripts/session_backup.py`）、`sessions/`（会话 JSON 备份）——schema 见 `references/templates.md` §5–9。推荐用 `init_swarm.py --intensity medium` 一键生成；若 init 未生成 `cycles/`，root 首启先建 `cycles/C0000/`。
5. 运行时一律**绝对路径**；严禁在仓库根建 `runs/`、`track_notes/`（会污染 git 状态）。

## 代际循环（核心）

每代 =「Sponsor 发 brief → root 指挥一波 → 收口 → 决定下一代」。

1. **Sponsor 发 root**：`task` 工具 spawn `swarm-lead`（prompt 见 `references/prompts.md` §1），必含：
   必读文档与运行时文件、上一 Cycle 背景（checkpoint/RESULTS 关键数字）、**全部方向（xhigh+ 不裁剪、不排序取舍）**、队形与预算、落盘交付物、返回格式（≤40 行；被 infinite scope 覆盖时为进度快照，不等待最终返回）。
   必须要求 root **先写/评审/冻结 `cycles/<C>/PLAN.md`**，再派发 lead；xhigh+ 按 Cycle 滚动。
   `intensity=infinite` 时按 `never_stop_scope` 决定：默认只给 depth-1 root 附上 `references/prompts.md` §0.1 全文；`all`/`depth:N` 时按 scope 附块，未覆盖的子代理不加块、按有限任务返回。
2. **root 执行**：先写 `cycles/<C>/PLAN.md` → 评审/冻结 → 再按 PLAN 的并行波次派 `lead-1`/lead(s)（每 track 一条 lead→manager→worker 链）；维护 leaderboard/state/checkpoint；裁决冲突；达标或越限时写 `STOP`（被 infinite scope 覆盖的执行体例外：达标转验证/反例/加固继续，只有外部信号可写 `STOP`）。
3. **Sponsor 收口**：核对产物 → commit + push 仅 `docs/` 侧（experiments.md、charter 修订、交付报告、xhigh+ 的 PLAN/RESULTS 快照；运行时永不入库，push 失败用重试循环）→ 向用户汇总 → 按停止条件决定：继续下一代 / 换任务卡 / 开新波次（新编号 swarm）/ 收敛交付。
4. **每代先读上代 checkpoint** 再开局；不重复已证伪路径（维护"已关闭清单"）。
5. **xhigh+ 在外层代内按 Cycle 滚动**：每 Cycle 写 `PLAN.md`→review 冻结→全并行派发→`RESULTS.md`→
   更新下一 Cycle PLAN；Cycle 不设固定上限（infinite 无限），只有外部 `STOP`/预算/安全信号收口。

## 规划门（所有强度）与 Cycle（xhigh+）

### 1) 先计划、评审、冻结，再派发（所有强度；xhigh+ 强制）

- **root 第一件事不是派 lead，而是写 PLAN**：在派发 `lead-1` 之前，必须先在
  `<SWARM>/cycles/<C>/PLAN.md` 写完整计划。计划必须包含：
  - **全部已想到的方向**（exhaustive directions）：主假设、竞争假设、失败模式、替代数据/标签/模型/锚点、
    反例/审计方向；xhigh+ 不得只列 2–4 个"先试试"的方向。
  - **完整派发树**：`root → lead-1 → manager(s) → worker(s)`；每个 SubAgent 的
    `agent_id / subagent_type / 任务 / 输入 / 输出 / 验收 / 预算 / fp12 / 依赖`；
    还要写清"这个 SubAgent 要派发的下一层 SubAgent 各自完成什么"。
  - **并行波次**：无依赖任务必须同波并行；有依赖必须写成显式 DAG，依赖解除后立即并行。
  - **bash 计划**：每条命令必须能在 `<=60s` 返回；长任务必须写后台启动/轮询/日志/PID/预计时长。
  - **审计计划**：并行、抽样、时间盒；只审晋级/绿色候选，不串行全量复核。
- **写完必须 review**：逐项对照 `references/prompts.md` §0.2 的 PLAN 评审清单，把要改的部分改回 PLAN，
  然后冻结 `plan_hash`，写 `PLAN_REVIEW.md`（或 PLAN.md 的 `## Review` 段）。
  **未冻结的 PLAN 不得派发任何子代理**；每个 task 批次/波次前确认对应 PLAN 行已冻结，任务变了先 AMEND。
- **每层都要计划**：root 写主 PLAN；`lead-1` 派生 manager/worker 前，必须写本子树
  `cycles/<C>/leads/<lead_id>/PLAN.md`（与主 PLAN 一致）；manager 派生 worker 前同样写/更新
  `.../managers/<mgr_id>/PLAN.md`。子计划不得漏掉主 PLAN 里的任何方向。
- **xhigh+ 禁止延期项**：PLAN 里不得出现"下一步 / 可选项 / 可选 / open / TBD / 待定 / 后续 / 备选 /
  TODO / 视情况 / 有时间再做"。所有已想到方向必须在本 Cycle 派发；认为不可行的方向，也必须在本 Cycle
  派一个**最小证伪任务**，把结论写进 `RESULTS.md` 的 closed 列，**不能留到下一轮**。
- **计划变更必须显式**：写 `PLAN.amend.<n>.md`，重新 review + 冻结；可在 Cycle 内取消/改派在途
  SubAgent，但必须记录原因、影响的 agent/session、新任务与验收；禁止口头改计划或静默改任务。
- **禁止提问**：任何代理不得调用 `question`/ask 工具；不确定的输入/口径写入 PLAN 的 `Assumptions`，
  按最小风险路径继续，并在 RESULTS 中标注该假设的影响。

### 2) Cycle：一轮完整的「计划→并行执行→收集→再计划」

- **适用**：仅 `xhigh / max / infinite`。high 及以下仍按 generation 运行，不启用 Cycle 语义。
- 一个 **Cycle** = 读上轮结果 → 写/更新 `PLAN.md` → review 冻结 → **全并行**派发 → 收集
  `RESULTS.md` → 更新状态。产物统一放 `<SWARM>/cycles/<C>/`（`PLAN.md`、`PLAN_REVIEW.md`、
  `DISPATCH.jsonl`、`RESULTS.md`、`AMEND_*.md`）。
- **Cycle 数量**：xhigh+ 在一次 swarm 内可容纳无限多 Cycle；`max_generations` 在 xhigh+ 只作外层 checkpoint 计数，
  **不限制 Cycle**。预算/外部 `STOP` 是唯一外部边界；`infinite` 下 Cycle 必须无限，执行体不得自停。
- **每轮必须更新计划**：根据 `RESULTS.md` 的失败/阻塞/新信息更新下一轮 PLAN；该换方向就换方向、
  该拆细就拆细、该换工具就换工具。要有人的"耐心感"：有信号就继续深挖，方向死了就换杠杆，
  **但不允许以"没进展/资源不足/完成"为由停下**。
- **xhigh+ 的广度是"全部"**：每个 Cycle 的 Directions 表必须覆盖当前所有已想到方向（不是 2–4 个）；
  发现新方向立即写入下一 Cycle 的 PLAN 并在该 Cycle 派发，不许留作"以后"。
- **Cycle 关闭条件**：不是"时间到"，而是 Directions 每一行都有结果（keep/kill/probe-more/closed）或
  外部 blocked；未完成方向必须在**同一 Cycle 内**续派/拆细/换工具，不能滚到下一 Cycle。
- **Cycle 内禁止串行**：无依赖的 SubAgent 必须同一波次并行派生；有依赖的写成 DAG，依赖完成即并行。
  不允许"派一个、等一个、再派下一个"的省事写法。
- **审计不拖慢 Cycle**：审计任务与生产任务并行派生，并发 ≤ 生产并发的 20%，时间盒 ≤ 本 Cycle 生产墙钟的 20%；
  只对晋级/绿色候选做独立复现，抽样优先；审计超时记录未决并继续下一 Cycle，未审的 green 不得宣称达标。

## Task Agent 的 session id 与恢复保证（派生后立刻落盘）

- `task` 工具返回的 `<task id="ses_...">` **就是子代理会话 id，也是续跑用的 `task_id`**（2026-10-22 在 opencode 1.19.x 实测：同一 id 续跑，上下文保留）。
- **双保险落盘**：子代理开工用 `run_token` 自报后立即写自己的 `runs/<agent_id>/SESSION_ID`（一行 `ses_...`，不等结束）；父代理在 `task` 返回后把 `agent_id → session_id` 追加进 `agent_log.jsonl`（`event=spawn`）。
- 子代理需要知道自己的 id：prompt 里带唯一 `run_token=<swarm>-g<G>-<agent_id>-<8hex>`，开工先运行
  `python <SWARM>/tools/session_map.py self --token <run_token>`，把输出的 `SESSION_ID`/`PARENT_ID` 写进 NOTES 与回报。
- 父代理/接棒者丢了链路时按会话树恢复（只读 DB，opencode 运行中也可用）：
  `python <SWARM>/tools/session_map.py children --parent <session_id>`
  或 `opencode db "select id,parent_id,agent,title from session where parent_id='<sid>' order by time_created" --format json`。
- **找不到就用 token 反查**：`session_map.py self --token <run_token>` 或 `session_map.py agent --agent-id <agent_id>`。
- **不要用 `opencode session list` 找子代理**（实测只列主会话）；**不要按 `time_updated` 猜**（并发会话会串到别人）。
- 恢复一律用 `task` 工具 `task_id=<ses_...>`（不是自造的 agent_id）；每代 checkpoint 的"在途代理"表要记录 session id。

### 恢复保证与边界（2026-10-22 实测，opencode 1.19.x）

| 场景 | 实测结果 |
|---|---|
| 子代理当前轮被 abort/cancel | 同 session id + "继续" 可恢复，口令/上下文保留 |
| `task` 被外部打断 | 返回 `Task cancelled`，**不带 `<task id>`**；必须靠子代理开工写的 `SESSION_ID` / token 反查 |
| 新客户端进程接续（`opencode run --attach -s <ses_...>`） | 同一会话可继续（历史从 DB 读取） |
| 删除父会话 | **级联删除全部子会话**；token/children 均查不到 |
| 用已删除的 `task_id` 续跑 | `task` **静默新建**一个 session（返回头 id ≠ 请求 id），看似成功但上下文为空 |
| 会话被删/DB 损坏且无备份 | 不能恢复同一会话，只能按 NOTES/checkpoint 重建 |
| 有 `opencode export` 备份 | `opencode import` 实测恢复**同一 session id** 与完整历史（父会话已删的孤儿子会话也可单独恢复） |

- **续跑后必须核对返回头 id**：`task` 返回 `<task id="A">`，若 A ≠ 请求的 `task_id` → 原会话已不在，你拿到的是全新空会话；立即停手，改走备份 import 或重建 brief，别在空会话里继续干活。

**结论：不是 100%。** 正常中断（abort/取消/进程重启）可稳定恢复同一会话；删除会话/DB 损坏属于不可恢复，除非有导出备份。因此：

- **会话备份**：每代 checkpoint 或收口时执行
  `python <SWARM>/tools/session_backup.py export-state --swarm <SWARM>`
  （写 `<SWARM>/sessions/<agent_id>.json`）；也可 `export-tree --root <root_session>` 备份整棵会话树。删除任何会话前先
  `session_backup.py export --session <ses_...> --agent-id <id> --out-dir <SWARM>/sessions`。
  恢复：`python <SWARM>/tools/session_backup.py import --file <...>.json`。
  备份是**导出时的快照**（运行中会话可能缺最后一轮），关键结论仍必须落 NOTES。
- **禁删会话**：swarm 运行/收尾期间不要删除任何父/子会话。
- **同一会话 ≠ 记得所有细节**：长会话会 compact/截断，恢复后可能丢中间细节；关键状态必须落 NOTES/checkpoint，恢复时以文件为准。
- 兜底永远是 **NOTES + checkpoint + agent_log**：会话没了也能重建任务，只是不是同一对话。

## 停止条件（写进 CHARTER）

- **主目标达成**（且过技能门 + 多 split/多种子复现 + 审计；**非 xhigh/max/infinite**）→ 写 `swarm<N>/STOP`、复现清单、交付报告
- **穷举证伪**（连续多代无新达标、只剩重复路径；**非 xhigh/max/infinite**）→ 上界报告，诚实收敛（"不是预算耗尽，是价值耗尽"）
- 预算硬闸触顶；用户随时可写 `STOP` 或口头停止
- **infinite 档特例**：被 `never_stop_scope` 覆盖的执行体（默认仅 depth-1 root）不得自我判定停止。
  主目标达成只触发"验证 + 反例搜索 + 边界/回归测试 + 加固 + 扩展验收标准"，然后继续；不写 `STOP`、
  不输出最终消息。未覆盖的 lead/manager/worker 是有限任务，正常返回结果。只有外部信号（用户/Sponsor
  `STOP`、预算硬闸、安全红线）才能收口；root 在 checkpoint 记录 `external_stop=<原因>`。
- **xhigh/max Cycle 特例**：不设固定 Cycle 上限；主目标达成不自动停，转入下一 Cycle 的验证、反例、
  边界与扩展验收。只有预算硬闸、用户/Sponsor `STOP` 或安全红线可以收口。

## 铁律（违反 = 结果不可信）

1. **技能门**：任何指标宣称必须打败同队列平凡基线（all-positive、年龄/术式等简单规则）；否则只是描述性数字，不得计为达标。
2. **预注册**：变体网格、选择规则、停止判据先写入 NOTES 再执行；选择只看 valid，test 单次。
3. **test 单次 + 登记**：`test_uses.jsonl` planned→used；每个 fp12 只评一次；禁止 test 调参、禁止在 test 上选择。
4. **防重复指纹**：`fp12=sha1(task|data|features|model|params|seed)[:12]`；跑前查 `registry/`，跑后写 `.done`。
5. **领取独占**：`claims/<task_id>.claim` 原子创建；>6h 视为死领取，改名 `.stale` 后重抢。
6. **重计算抢槽**：`scripts/heavy_lock.py` 物理槽；无槽先做轻任务或等待，禁止裸跑重训练。
7. **写权分离**：worker 只写自己 `runs/<agent_id>/`；lead 只写本 track；root 独占 `state/leaderboard/checkpoints`；代理均不改共享代码、不 git——只有 sponsor 收口时 commit。
8. **预算硬闸**：每次派生前后核对 `agent_log` 行数、runs 数、重槽占用/槽时、并发代理数、`intensity_profile` 上限、STOP 是否存在；任一越限 → 停派生、写 checkpoint、退出（infinite 下视为外部信号：停派生/等 sponsor 重置，不自我收口）。
9. **诚实报告**：流行度/检测混入等伪影必须披露并冻结；证伪路径入"已关闭清单"防止回头；假 STOP 要撤销。
10. **记录契约**：worker 落 `NOTES.md`（目标/数据版本/命令/结果+CI/产物/结论/新假设/`SESSION_ID`）；返回父代理最终消息 ≤40 行（被 infinite scope 覆盖的执行体为进度快照，非最终消息，回报后继续）；父代理记录子代理 `<task id="ses_...">`。
11. **infinite 永不终止块（按 scope）**：`never_stop_scope` 覆盖的执行体（默认仅 depth-1 root）的
    每个派生/续跑/重建 prompt 必须原样携带 `references/prompts.md` §0.1 全文；未覆盖的 lead/manager/worker
    不加块、按有限任务返回。只有用户/Sponsor `STOP`、预算硬闸、安全红线可以终止被覆盖执行体；
    执行体自身不得以"完成/失败/阻塞/无进展/资源不足"收口。
12. **PLAN-first 门**：任何强度下，派发任何子代理前必须有**已冻结**的 `PLAN.md`；root 写主计划，
    lead/manager 写本子树计划。计划必须含全部方向、完整派发树、并行波次、bash/长任务方案、审计方案；
    未评审/未冻结 == 不得派发。
13. **xhigh+ 无延期项**：PLAN 正文禁止"下一步 / 可选项 / 可选 / open / TBD / 待定 / 后续 / 备选 /
    TODO / 视情况 / 有时间再做"；所有已想到方向必须在本 Cycle 全部派发；不可行也要派最小证伪任务，
    结论写 `RESULTS.md` 的 closed 列，不能留到下一轮。
14. **执行时间盒**：每次 bash 调用必须 `<=60s`（显式传 `timeout<=60000`）；长任务必须后台启动 +
    轮询（日志/PID/预计时长写入 PLAN），禁止一个调用阻塞等待。独立 bash 必须同一消息并行发，
    串行只用于真实依赖。
15. **全并行派发**：无依赖的 SubAgent 必须同一波次并行派生；有依赖写显式 DAG，依赖解除后立即并行。
    禁止"派一个、等一个、再派下一个"；xhigh+ 的 PLAN 必须给出波次与并发上限。
16. **审计时间盒**：审计与生产并行、抽样、只审绿色/晋级候选，只验证关键断言（指标/泄漏/基线/复现）；
    审计并发 `<= 生产并发 20%`，审计墙钟 `<= Cycle 生产墙钟的 20%`，超时记未决并继续。未审计的 green 不得计为达标；
    禁止串行全量复核拖垮 Cycle。
17. **绝对禁止提问工具**：所有 swarm 代理（root/lead/manager/worker，以及 sponsor 在 swarm 执行链中）
    **不得调用 `question`/ask 提问工具**，不得向用户或父代理提问。不确定时把假设写入 PLAN 的
    `Assumptions` 与 NOTES，按最小风险路径继续；需要人类决策只能由用户在外部主动介入。

（完整运行时契约与评估协议见 `references/protocol.md`。）

## 恢复被中断的 swarm

1. **盘点现场**（只读）：`state.json`、`agent_log.jsonl` 尾部、`runs/` 新增目录、`claims/*.claim`、`locks/*.lock`、`STOP`。
2. **恢复 Task Agent 对话（首选、极简）**：
   - 用原 `task_id=<ses_...>`（= 子代理 session id）恢复同一会话，prompt 就一句 **"继续"**——它的上下文还在，自己知道做到哪、下一个可验证动作是什么；**非必要不要回复一大堆话**（重发背景/规格浪费 token，还可能打乱它）。
   - session id 来源优先级：`runs/<agent_id>/SESSION_ID` / `agent_log.jsonl` 的 `session_id` 字段 → `session_map.py children --parent <sid>`（沿 `parent_id` 树）→ `session_map.py self --token <run_token>`（token 在 prompt 里）。
   - 若 `task` 返回的是 `Task cancelled`（**没有 id**，实测外部中断即如此）：立刻用上面三条反查，别把它当成"会话丢了"。
   - **续跑后核对返回头 `<task id="...">` 是否等于请求的 `task_id`**；不等 = 原会话已丢失，工具静默新建了空会话。
   - 只在需要纠偏/补充约束时加最少一句（如 `继续；先收尾再回报`）。
   - **嵌套链逐级恢复**：root 恢复后，让 root 用同样方式（"继续"）恢复它派生的 lead/manager/worker；sponsor 不要替 root 重写整套 brief。
   - **会话已被删除/查不到**：先看 `<SWARM>/sessions/<agent_id>.json`，有备份就
     `session_backup.py import --file <...>`（实测恢复同一 session id），再按原 id "继续"；
     没有备份才发重建 brief（`references/prompts.md` §5 兜底模板，只附最少必要事实、声明"已完成项无需重跑"）。
   - **主会话（sponsor/root）恢复**：TUI 用 `opencode -s <ses_...>`；命令行用
     `opencode run --attach <server> -s <ses_...> "继续"`（实测新进程可从 DB 接续同一会话）。
3. **清理与收尾**：清残留 claims/locks（`.stale` 后重抢），补齐 checkpoint/leaderboard/state，完成在途任务卡，再继续下一代。删除任何会话前必须先 export。

## 常见坑

- 配置未重启 → 嵌套不生效；内置 `general` 默认无 task 工具（务必用自定义 `swarm-lead/swarm-worker`）。
- docs/ 与 runtime 混在一起 → git 污染；runtime 必须 gitignore。
- 子集→全量缩水（>0.05 结论翻转）：子集只筛查，晋级必须全量复核。
- 假 STOP：高流行度队列的 F1 是伪影——技能门 + 同队列平凡基线可拦截。
- 不抢槽直接上重训练 → 机器过载、任务互相拖死。
- 每代只汇报数字不落盘 → 无法恢复/复现；NOTES + checkpoint 是硬契约。
- 恢复时重发大段 brief → 浪费 token 还可能打乱子代理；优先对原会话说"继续"。
- 不知道子代理 session id → `task` 返回头 `<task id="ses_...">` 就是；派生后立刻落盘，丢了用 `session_map.py` 反查（别用 `opencode session list`，它不列子代理）。
- 以为"有 task_id 就 100% 能恢复" → 删除父会话会**级联删除子会话**，DB 损坏/裸删也救不回；必须 checkpoint 导出 `sessions/*.json`，并以 NOTES 为最终兜底。
- 强度虚标：用 high 的代理数却不给 128 槽/审计/恢复节奏 → 只会更快产出不可信结果；按 `references/intensity.md` 配齐再升档。
- 一开始就拉满预算 → 先跑 1–2 代观测真实成本与产出价值，再决定加码（**价值耗尽可能早于预算耗尽**）。
- infinite 档无限执行范围搞错 → 默认只给 depth-1 root 带 §0.1；把块发给所有 worker 会导致 worker
  不返回、root 收不到结果。只有用户明确 `all`/`depth:N` 才扩大范围。
- 不写 PLAN 就派 SubAgent → 任务漂移、重复劳动、方向遗漏；xhigh+ 必须先冻结 PLAN 再派。
- PLAN 里留"下一步/可选项/open/以后再做" → 等于把广度砍掉；xhigh+ 必须本 Cycle 全派发，不可行也派证伪任务。
- 把独立任务串行派发/串行 bash → 墙钟爆炸；无依赖必须同一消息/同一波次并行。
- 用一个 bash 调用等 2 小时训练 → 调用超时且无法恢复；长任务必须后台 + 轮询，单次 bash ≤60s。
- 审计串行全量复核 → Cycle 被审计拖死；只审 green/晋级、抽样、并行、时间盒 ≤20%。
- 调用 `question`/ask 提问工具 → 直接违规并阻塞执行；把假设写进 PLAN `Assumptions`，按最小风险路径继续。

## 配套文件

- `references/intensity.md` —— 强度等级 low/medium/high/xhigh/max/infinite（默认 medium）：槽位/槽时/代理量/审计/恢复/治理
- `references/protocol.md` —— 运行时契约完整版（角色/目录/PLAN 门/Cycle/领取/锁/预算/并行/审计时间盒/记录/评估/停止/接棒）
- `references/prompts.md` —— 各角色 prompt 模板（root/lead/manager/worker/恢复/嵌套验证）+ §0.1 infinite 强制「永不终止执行引擎」块 + §0.2 PLAN 评审清单
- `references/templates.md` —— 宪章骨架 + state/backlog/leaderboard/checkpoint/NOTES/预注册卡 + PLAN.md/Cycle 模板 + config 片段
- `scripts/append_jsonl.py`、`scripts/heavy_lock.py` —— 并发安全 JSONL 追加与物理重任务槽
- `scripts/session_map.py` —— 用 run_token / 父会话 id / agent_id 反查 Task Agent 的 session id（读 opencode SQLite，只读安全）
- `scripts/session_backup.py` —— `opencode export/import` 封装：按 state.active_sessions 批量备份、恢复同一 session id
- **依赖（high+ 必须检查）**：`parallel-data-processing` skill（本地 `~/.config/opencode/skills/parallel-data-processing/`；
  缺失时到用户 GitHub Hcachild 找，或按同模式手写 split/merge）
