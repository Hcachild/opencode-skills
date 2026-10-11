---
name: agent-swarm
description: 'Run long-running iterative research/experiment campaigns as a nested-subagent swarm (Agent 集群/蜂群): sponsor → root curator → track-lead → manager → worker generations, with CHARTER/PROTOCOL/ROADMAP governance, backlog/leaderboard/checkpoint runtime, fingerprint & test registration, skill gate, budget gates and STOP rules. Use when the user asks to 启动swarm/开集群/长跑实验/持续迭代研究/派子代理并行做实验/恢复被中断的swarm, or mentions "Generation N", root curator, swarm-lead/swarm-worker, or a docs/swarm*/ + swarm*/ directory pair.'
---

# Agent Swarm —— 嵌套子代理长跑研究集群

把「长期迭代研究/实验」组织成一个可恢复、可审计、可收敛的树状子代理集群。
来自真实长跑实践（MOVER-SIS 研究：多波 swarm、数百子代理/实验，产出过达标任务，
也以"穷举证伪 + 上界报告"诚实收敛）。

## 何时使用

- 目标需要**大量并行实验/分析**，单代理在时间/上下文内完不成（用户说"开 N 个 Task Agent 持续迭代"）
- 需要**跨多轮（generation）持续探索**，每轮基于上轮结果调整方向
- 需要**可复现、可审计**的纪律：预注册、防重复、单次 test、预算硬闸、技能门
- 用户提到 "swarm/集群/长跑/大范围探索/发散探索"，或已有一对 `docs/swarmN/`（宪章）+ `swarmN/`（运行时）

不适合：单次线性任务；目标模糊、无法定义验收标准与平凡基线的任务。

## 架构与角色

```
Sponsor（主会话，你自己）        —— 建宪章、发 root brief、每代收口 commit、决定收敛
└── root curator (swarm-lead)   —— 代际调度：派 lead、合并 leaderboard、写 checkpoint、停止裁决
    ├── track-lead (swarm-lead) —— 一条赛道/任务：定变体网格、派 manager、汇总本赛道
    │   └── manager (swarm-lead)—— 拆 2–4 个原子实验，派 worker
    │       └── worker (swarm-worker) —— 只做一个原子实验；叶子，禁止派生
    └── ...（每层每节点可并行 ≤128 子代理；实际深度 ≤6，subagent_depth=12 支持接棒）
```

- **代理并发**：每层每个节点均可派生至上限（root/lead/manager 一视同仁，如 128）；首代可全量并行分派
- **重计算**另受物理槽限制（`locks/heavy_XX`，按机器核数定，如 ≤16），与代理并发无关
- root 上下文将满时派生**继任 root**接棒（写 checkpoint、深度+1）

**与批量处理 skill 协同**：若已安装批量处理 skill（如 `parallel-data-processing`），对**扁平的大批量同构工作**（逐条分类/提取/打标成千上万条数据）直接采用它的"切 N 片 → 每片一个 Task Agent 输出 JSON → 校验合并"模式（一个 manager 挂 N 个 worker 即可），不必为每个小项单开 track；层级 swarm 仍负责研究主线与治理。

## 一次性基建（每个研究目标一套）

1. **配置子代理**（全局/项目 `opencode.json`，片段见 `references/templates.md` §1）：
   `subagent_depth`、`swarm-lead`（`task=true`，可派生）、`swarm-worker`（`task=false`，叶子）。
   **必须重启 opencode 生效**；重启后先做嵌套验证（spawn swarm-lead → 它再 spawn swarm-worker 落盘验证）。
2. **定义验收标准与技能门**：什么算达标（指标+CI 要求）、必须打败哪些平凡基线（all-positive、简单规则、现状态）。目标值写进 CHARTER。
3. 建 `docs/swarm<N>/`：`CHARTER.md`（使命/任务卡/技能门/反作弊/停止条件）、`PROTOCOL.md`（角色/路径/领取/锁/预算/记录契约）、`ROADMAP.md`（阶段/里程碑/首代种子/剪枝）——骨架见 `references/templates.md` §2–4，**入库并 commit**。
4. 建 `swarm<N>/` 运行时（**gitignore**）：`state.json`、`agent_log.jsonl`、`backlog.jsonl`、`leaderboard.csv`、`checkpoints/`、`runs/`、`claims/`、`registry/`、`locks/`、`prereg/`、`test_uses.jsonl`、`tools/`（复制本技能 `scripts/append_jsonl.py`、`scripts/heavy_lock.py`）——schema 见 `references/templates.md` §5–9。
5. 运行时一律**绝对路径**；严禁在仓库根建 `runs/`、`track_notes/`（会污染 git 状态）。

## 代际循环（核心）

每代 =「Sponsor 发 brief → root 指挥一波 → 收口 → 决定下一代」。

1. **Sponsor 发 root**：`task` 工具 spawn `swarm-lead`（prompt 见 `references/prompts.md` §1），必含：
   必读文档与运行时文件、本代背景（上代 checkpoint 关键数字）、优先任务（排序）、队形与预算、收尾交付物、返回格式（≤40 行）。
2. **root 执行**：按波次派 lead（每 track 一条 lead→manager→worker 链）；维护 leaderboard/state/checkpoint；裁决冲突；达标或越限时写 `STOP`。
3. **Sponsor 收口**：核对产物 → commit + push 仅 `docs/` 侧（experiments.md、charter 修订、交付报告；运行时永不入库，push 失败用重试循环）→ 向用户汇总 → 按停止条件决定：继续下一代 / 换任务卡 / 开新波次（新编号 swarm）/ 收敛交付。
4. **每代先读上代 checkpoint** 再开局；不重复已证伪路径（维护"已关闭清单"）。

### 停止条件（写进 CHARTER）

- **主目标达成**（且过技能门 + 多 split/多种子复现 + 审计）→ 写 `swarm<N>/STOP`、复现清单、交付报告
- **穷举证伪**（连续多代无新达标、只剩重复路径）→ 上界报告，诚实收敛（"不是预算耗尽，是价值耗尽"）
- 预算硬闸触顶；用户随时可写 `STOP` 或口头停止

## 铁律（违反 = 结果不可信）

1. **技能门**：任何指标宣称必须打败同队列平凡基线（all-positive、年龄/术式等简单规则）；否则只是描述性数字，不得计为达标。
2. **预注册**：变体网格、选择规则、停止判据先写入 NOTES 再执行；选择只看 valid，test 单次。
3. **test 单次 + 登记**：`test_uses.jsonl` planned→used；每个 fp12 只评一次；禁止 test 调参、禁止在 test 上选择。
4. **防重复指纹**：`fp12=sha1(task|data|features|model|params|seed)[:12]`；跑前查 `registry/`，跑后写 `.done`。
5. **领取独占**：`claims/<task_id>.claim` 原子创建；>6h 视为死领取，改名 `.stale` 后重抢。
6. **重计算抢槽**：`scripts/heavy_lock.py` 物理槽；无槽先做轻任务或等待，禁止裸跑重训练。
7. **写权分离**：worker 只写自己 `runs/<agent_id>/`；lead 只写本 track；root 独占 `state/leaderboard/checkpoints`；代理均不改共享代码、不 git——只有 sponsor 收口时 commit。
8. **预算硬闸**：每次派生前后核对 `agent_log` 行数、runs 数、重任务小时、STOP 是否存在；任一越限 → 停派生、写 checkpoint、退出。
9. **诚实报告**：流行度/检测混入等伪影必须披露并冻结；证伪路径入"已关闭清单"防止回头；假 STOP 要撤销。
10. **记录契约**：worker 落 `NOTES.md`（目标/数据版本/命令/结果+CI/产物/结论/新假设）；返回父代理最终消息 ≤40 行。

（完整运行时契约与评估协议见 `references/protocol.md`。）

## 恢复被中断的 swarm

1. **盘点现场**（只读）：`state.json`、`agent_log.jsonl` 尾部、`runs/` 新增目录、`claims/*.claim`、`locks/*.lock`、`STOP`。
2. **恢复 Task Agent 对话（首选、极简）**：
   - 用原 `task_id` 恢复同一子代理会话，prompt 就一句 **"继续"**——它的上下文还在，自己知道做到哪、下一步是什么；**非必要不要回复一大堆话**（重发背景/规格浪费 token，还可能打乱它）。
   - 只在需要纠偏/补充约束时加最少一句（如 `继续；先收尾再回报`）。
   - **嵌套链逐级恢复**：root 恢复后，让 root 用同样方式（"继续"）恢复它派生的 lead/manager/worker；sponsor 不要替 root 重写整套 brief。
   - 兜底：仅当原会话/task_id 不可恢复时，才发重建 brief（`references/prompts.md` §5 兜底模板，只附最少必要事实、声明"已完成项无需重跑"）。
3. **清理与收尾**：清残留 claims/locks（`.stale` 后重抢），补齐 checkpoint/leaderboard/state，完成在途任务卡，再继续下一代。

## 常见坑

- 配置未重启 → 嵌套不生效；内置 `general` 默认无 task 工具（务必用自定义 `swarm-lead/swarm-worker`）。
- docs/ 与 runtime 混在一起 → git 污染；runtime 必须 gitignore。
- 子集→全量缩水（>0.05 结论翻转）：子集只筛查，晋级必须全量复核。
- 假 STOP：高流行度队列的 F1 是伪影——技能门 + 同队列平凡基线可拦截。
- 不抢槽直接上重训练 → 机器过载、任务互相拖死。
- 每代只汇报数字不落盘 → 无法恢复/复现；NOTES + checkpoint 是硬契约。
- 恢复时重发大段 brief → 浪费 token 还可能打乱子代理；优先对原会话说"继续"。
- 一开始就拉满预算 → 先跑 1–2 代观测真实成本与产出价值，再决定加码（**价值耗尽可能早于预算耗尽**）。

## 配套文件

- `references/protocol.md` —— 运行时契约完整版（角色/目录/领取/锁/预算/记录/评估/停止/接棒）
- `references/prompts.md` —— 各角色 prompt 模板（root/lead/manager/worker/恢复/嵌套验证）
- `references/templates.md` —— 宪章骨架 + state/backlog/leaderboard/checkpoint/NOTES/预注册卡模板 + config 片段
- `scripts/append_jsonl.py`、`scripts/heavy_lock.py` —— 并发安全 JSONL 追加与物理重任务槽
