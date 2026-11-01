# 模板与 Schema

## §1 `opencode.json` 配置片段（全局或项目）

```json
{
  "$schema": "https://opencode.ai/config.json",
  "subagent_depth": 12,
  "agent": {
    "general": {
      "tools": { "task": true },
      "permission": { "task": "allow" }
    },
    "swarm-lead": {
      "description": "Swarm lead/manager: may spawn worker/sub-lead agents via the task tool. Read docs/swarm*/PROTOCOL first.",
      "mode": "subagent",
      "tools": { "task": true },
      "permission": { "task": "allow" }
    },
    "swarm-worker": {
      "description": "Swarm worker: executes one atomic experiment/analysis; must not spawn subagents.",
      "mode": "subagent",
      "tools": { "task": false }
    }
  }
}
```

要旨：
- `swarm-lead` 可派生（`task=true` + `permission.task=allow`）；`swarm-worker` 叶子（`task=false`）。
- 内置 `general` 默认没有 task 工具；想用必须显式打开。
- 建议同时给 `swarm-lead` 加 `permission.edit` 白名单等防误改（可选）。
- **改完必须重启 opencode**；重启后先跑 `references/prompts.md` §6 验证嵌套。

## §2 `CHARTER.md` 骨架（docs/swarm<N>/，入库）

```markdown
# Swarm<N> Charter — <使命一句话>（v1，所有代理必读）

- intensity: <low|medium|high|xhigh|max|infinite>（默认 medium）
- granularity: <question|variant|atomic-experiment|matrix-cell+replication|micro-hypothesis|continuous-microtask>
- intensity_rationale: <一句话：为什么这个等级>
- prompt_block: <none|never-stop-engine>（infinite 必须为 never-stop-engine；全文见 references/prompts.md §0.1）
- never_stop_scope: <root|all|depth:N>（infinite 默认 root：只有 depth-1 root 无限执行）
- cycle_mode: <none|unbounded>（xhigh/max/infinite 必须为 unbounded）

## 1. 使命
<研究问题、数据集、为什么做、成功定义（指标+CI+技能门+复现要求）>

## 2. 目标与技能门
- 主目标：<如：≥3 个任务达 skill-gated F1≥0.70 且双 split 复现>
- 技能门：<平凡基线清单；过门判据>
- 头room 判定：required-AUROC(目标) − 观测 AUROC；≤0.03 high / 0.03–0.08 reachable / >0.08 low

## 3. 候选任务卡（可扩展）
| ID | 任务 | 标签/单元 | 临床/业务意义 | 备注（生理/行为/对照） |
|---|---|---|---|---|
| ... | ... | ... | ... | ... |

## 4. 晋级与停止
- 强度档位与预算：见 `state.intensity_profile`；升降档规则见 `references/intensity.md` §6
- 每任务输出：prevalence、baseline、主指标+CI、required、headroom、判定
- 晋级：headroom 高/可及 → 深挖（特征/模型/锚点/严重度设定扫描）
- 停止：① 主目标达成 ② 穷举证伪/多代无新达标 ③ 预算触顶 ④ 用户 STOP
- xhigh/max/infinite 档例外：①②只转验证/反例/加固/换杠杆/下一 Cycle 继续，不写 STOP；仅外部 STOP、预算硬闸、安全红线可收口
- infinite 额外：执行体 prompt 必须原样携带 `references/prompts.md` §0.1 全文（缺块不得派出）
- 反作弊：不得用 test 调参；亚组预注册+FDR；新标签必须过泄漏审计

## 5. 唯一口径
<筛选协议版本、队列、split、特征、模型、阈值规则、bootstrap 设置>

## 6. 规划与 Cycle
- 先 PLAN 后派发：root/lead/manager 在派生任何子代理前写/评审/冻结 `PLAN.md`；未冻结不得派发。
- xhigh+：每个 Cycle 的 Directions 必须覆盖全部已想到方向；禁止“下一步/可选项/open/TBD/待定/后续/备选/TODO”。
- Cycle 无固定上限（xhigh/max/infinite）；infinite 下 Cycle 无限；被 `never_stop_scope` 覆盖的执行体
  （默认仅 depth-1 root）不得自停。
- 执行：单次 bash `<=60s`；长任务后台启动 + 轮询；独立 bash/SubAgent 必须并行，串行只用于显式依赖。
- 审计：与生产并行、抽样、只审绿色/晋级候选；审计并发 `<= 生产并发 20%`，审计墙钟 `<= Cycle 生产墙钟的 20%`。
```

## §3 `PROTOCOL.md` 骨架（docs/swarm<N>/，入库）

把 `references/protocol.md` 的最终版复制进来，替换：
- `<SWARM>`/`<DOCS>` 实际绝对路径
- 并发上限（每层 ≤N）、物理槽数、预算硬闸数字
- PLAN.md 规划门、Cycle 规则、禁词表、bash `<=60s`、并行波次、审计时间盒
- 数据/代码落位路径（数据侧脚本/模型侧脚本/产物目录）
- 工具箱（可复用的基线、评估、审计脚本清单）

## §4 `ROADMAP.md` 骨架

```markdown
# Swarm<N> 路线图 v1

## 1. 阶段
- P1 <阶段名，第 1–K 代>：<基建 + 首轮筛查/基线>
- P2 <阶段名>：<对高价值项深挖/预注册+复现，目标达标>
- P3 交付：<达标 ≥M 项 → 交付报告；未达标归档（回头路清单）>

## 2. 里程碑
- M0 基建；M1 <首个里程碑>；M2 <达标项>；M3 <STOP 条件>；M4 交付报告

## 3. 首代种子（<ID 列表>）
<逐条一句话：任务 → 验收>

## 4. 剪枝
- <指标差距 >阈值 → 冻结（除非换设定）>
- <行为类任务与规则差 <0.03 → 冻结>
- 子集→全量缩水 >0.05 → 复核

## 5. Cycle（仅 xhigh/max/infinite）
- 每 Cycle = 写/评审/冻结 PLAN → 全并行派发 → RESULTS → 更新下一 Cycle PLAN。
- Cycle 不设固定上限；infinite 下无限，外部 `STOP`/预算/安全信号才收口；只有 `never_stop_scope`
  覆盖的执行体（默认 root）不得自停。
- 每个 Cycle 的 Directions 必须覆盖全部已想到方向；不允许延期项。
```

## §5 运行时文件 Schema（swarm<N>/，gitignore）

**state.json**（root 独占）：

```json
{
  "phase": "swarm<N>",
  "generation": 0,
  "cycle": 0,
  "cycle_id": "C0000",
  "never_stop_scope": "root",
  "intensity": "medium",
  "intensity_profile": {
    "max_parallel_agents": 30,
    "max_heavy_slots": 32,
    "granularity": "variant",
    "plan_required": true,
    "cycle_mode": "generation",
    "bash_timeout_s": 60,
    "audit_wall_share": 0.2,
    "batch_policy": "optional",
    "batch_shard_size": 10,
    "batch_parallel": 10,
    "seeds": 3,
    "splits": 2,
    "audit": "one-audit-track",
    "human_gate_every": 3,
    "checkpoint_every": "generation",
    "backup_every": "generation",
    "budget_window": "campaign"
  },
  "agents_launched": 0,
  "experiments_done": 0,
  "heavy_hours_used": 0.0,
  "budget": { "max_agents": 80, "max_experiments": 500, "max_heavy_hours": 2000, "max_generations": 3 },
  "started": "YYYY-MM-DD",
  "status": "boot | running | innovation-phase | stopped | converged",
  "primary_goal": "<一句话>",
  "active_sessions": { "<agent_id>": "ses_..." }
}
```

> 上面的数字是 **medium** 默认档。其他档位见 `references/intensity.md`；`init_swarm.py --intensity` 会自动写入。
> 若 init 版本较旧、未写 `plan_required/cycle_mode/bash_timeout_s/audit_wall_share`，root 启动时补齐。
> `intensity=infinite` 时，CHARTER 的 `prompt_block` 必须为 `never-stop-engine`；被 `never_stop_scope`
> 覆盖的执行体 prompt（含 root/lead/manager/worker/续跑/重建）必须原样附上 `references/prompts.md`
> §0.1 全文；缺块不得派出。`never_stop_scope` 默认 `root`：只有 depth-1 root 无限执行；
> lead/manager/worker 有限返回。只有用户明确指定时才改为 `all`（所有 SubAgent 无限）或
> `depth:N`（深度 `<=N` 无限；`depth:1` 等价 root）。
> `xhigh/max/infinite`：`cycle_mode="unbounded"`（不设 Cycle 上限，`max_generations` 在 xhigh+ 只作外层
> checkpoint 计数，不限制 Cycle）；`infinite` 下 Cycle 无限，执行体不得自停。`bash_timeout_s=60`、`audit_wall_share=0.2` 为所有档位默认。

**backlog.jsonl**（每行一个任务，owner 只改自己条目）：

```json
{"id": "V001", "track": "meta", "priority": 1, "status": "ready|claimed|done|frozen", "heavy": false,
 "granularity": "variant|atomic-experiment|audit|micro|batch-shard", "parent_task": "V000",
 "spec": "任务描述（可执行）", "inputs": ["路径/表"], "accept": "验收标准", "budget_min": 90,
 "result": "DONE: 关键数字; fp12 ...  或  KILL: 原因"}
```

> 粒度由 `state.intensity_profile.granularity` 决定；high+ 的每个原子单元必须独立一行、独立 fp12。

**batches/<batch_id>/manifest.json**（批量同构任务，high+；由 split 脚本生成）：

```json
{"batch_id": "B001", "source": "data.xlsx", "rule_version": "v1", "shard_size": 10,
 "shards": [{"chunk": "chunk_001.txt", "ids": ["sheet:R2", "sheet:R3"], "n": 2}]}
```

> 校验/回填只认 manifest；一个分片一个 claim，`fp12 = sha1(manifest|chunk|rule)[:12]`。
> 结果写 `results/chunk_XXX.json`，check-only 通过后才允许 merge 到 `out/`。

**leaderboard.csv** 建议列头：

```
task_card,track,stage,label,unit,model,cohort,anchor,threshold_rule,auroc,auprc,f1,f1_ci_low,f1_ci_high,
precision,recall,prevalence,skill_baseline_f1,skill_baseline_name,skill_gate_pass,required_auroc_070,
headroom,headroom_class,green,validated,split,source,notes
```

**agent_log.jsonl**（用 `tools/append_jsonl.py` 追加）：

```json
{"ts": "2026-10-06T14:49:46+08:00", "parent_id": "swarm-root-gen1", "task_id": "V001",
 "event": "spawn|done|decision|stop", "agent_id": "g1-v001-lead", "role": "lead",
 "run_token": "swarm1-g1-V001-lead-8hex", "session_id": "ses_...",
 "parent_session_id": "ses_...", "track": "meta", "depth": 2, "never_stop": false,
 "detail": "dispatched by root gen1 (wave1)"}
```

> `session_id` 取 `task` 工具返回头 `<task id="ses_...">`，它与续跑用的 `task_id` 是同一个值；
> 派生返回后立刻追加，并写 `runs/<agent_id>/SESSION_ID`。`event=done` 行也带同一个 `session_id`。
> `run_token` 是恢复兜底：`session_map.py self --token <run_token>` / `agent --agent-id <agent_id>` 可反查。
> `depth` / `never_stop` 由 `never_stop_scope` 计算（默认仅 depth=1 为 true），用于审计派发是否正确。

**test_uses.jsonl**（planned→used 两行，fp12 相同）：

```json
{"ts": "...", "task_id": "D1", "agent_id": "g1-v002-w1", "track": "D1", "model": "hgb3",
 "label_rule": "pressor_response_5min_10mmHg", "split": "split42",
 "canonical": "D1|pressor_response_5min_10mmHg|feat_B15|hgb3|split42", "fp12": "a367562f9cd1",
 "purpose": "test single evaluation", "status": "planned"}
{"...": "...", "status": "used", "metrics": {"f1": 0.51, "f1_ci_low": 0.47, "auroc": 0.76, "n_test": 1778}}
```

**STOP**：空文件即可；内容建议写 `reason=<...> date=<...>`。

## §5.1 `cycles/<C>/PLAN.md` 模板（xhigh+ 每个 Cycle 必写；high 及以下每个任务批次必写）

> root 写主 PLAN；lead/manager 在派生下一层前写本子树 PLAN（路径：
> `cycles/<C>/leads/<lead_id>/PLAN.md`、`cycles/<C>/managers/<mgr_id>/PLAN.md`）。
> 非 xhigh+ 的 `<C>` 可用外层代/批次 id（如 `G0001`/`B001`），目录统一 `cycles/<C>/`。
> 写完必须 review，修订后冻结 `plan_hash`；未冻结不得派发。xhigh+ 的 Directions 必须覆盖全部已想到方向。

```markdown
# <SWARM> Cycle <C> PLAN

- cycle: C0001
- intensity: <low|medium|high|xhigh|max|infinite>
- never_stop_scope: <root|all|depth:N>（仅 infinite 生效；默认 root）
- goal: <用户原始要求 + 本 Cycle 可验证子目标>
- parent_plan: <主 PLAN 路径 / none>
- plan_hash: <sha256(Directions|Dispatch|Waves|Bash/Jobs|Audit)[:16]；未填 = 未冻结>
- status: draft|reviewed|frozen|amended
- created: <YYYY-MM-DD HH:MM>
- reviewed: <YYYY-MM-DD HH:MM>

## 0. Assumptions（禁止调用提问工具；不确定项写这里并按最小风险路径执行）

| ID | 不确定点 | 采用假设 | 依据 | 影响/回退 |
|---|---|---|---|---|
| A1 | <口径/路径/资源未知> | <采用的假设> | <文档/数据/经验> | <对结果的影响与触发回退条件> |
| ... | ... | ... | ... | ... |

## 1. Directions（全部已想到方向；xhigh+ 不得裁剪为 2–4 个）

| ID | 方向/假设 | 来源 | 为什么值得做 | 本 Cycle 动作 | owner | 状态 | 验收 |
|---|---|---|---|---|---|---|---|
| D1 | <主假设> | <用户/上轮/失败模式> | <机制/证据> | <实验/分析/证伪> | <agent_id> | dispatch | <可验证断言> |
| D2 | <竞争假设> | ... | ... | ... | ... | dispatch | ... |
| D3 | <替代数据/标签/模型/锚点> | ... | ... | ... | ... | dispatch | ... |
| D4 | <反例/审计方向> | ... | ... | ... | ... | dispatch | ... |
| ... | ... | ... | ... | ... | ... | ... | ... |

> 规则：状态只能是 `dispatch`（本 Cycle 执行）、`probe`（本 Cycle 最小证伪）、`closed`（本 Cycle 内已证伪，
> 必须附本 Cycle 的 probe 证据）。不得预先把方向标 `closed` 来逃避派发；不允许任何延期到下一 Cycle 的方向；
> 新方向出现时在下一 Cycle 的 PLAN 增加，但本 Cycle 已知的必须全派。

## 2. Dispatch Tree（完整到 worker；写清每个 SubAgent 及其下一层要做什么）

| agent_id | role / subagent_type | parent | 任务 | 输入 | 输出 | 验收 | 预算 | fp12 | wave | 依赖 |
|---|---|---|---|---|---|---|---|---|---|---|
| lead-1 | swarm-lead | root | <主赛道汇总/拆分> | <路径> | <tracks/...> | <汇总断言> | <N 代理/分钟> | - | W1 | - |
| mgr-1 | swarm-lead | lead-1 | <拆本方向全部原子单元；xhigh+ 不设 2–4 上限> | ... | ... | ... | ... | - | W1 | - |
| w-1 | swarm-worker | mgr-1 | <原子实验 1> | ... | ... | ... | ... | <fp12> | W1 | - |
| w-2 | swarm-worker | mgr-1 | <原子实验 2> | ... | ... | ... | ... | <fp12> | W1 | - |
| ... | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

> 每个 lead/manager 的子 PLAN 必须与本表一致；worker 只做一行对应的原子单元，不得再派生。

## 3. Parallel Waves（无依赖必须同波；串行只用于显式依赖）

| wave | 并行 agents | 依赖 | 并发上限 | 启动条件 |
|---|---|---|---|---|
| W1 | <lead-1, mgr-1, mgr-2, w-1...> | - | <<= max_parallel_agents> | PLAN frozen |
| W2 | <...> | W1 done | <...> | W1 全部完成/部分完成阈值 |
| ... | ... | ... | ... | ... |

## 4. Bash / Long Jobs（全部命令 <=60s；长任务后台 + 轮询）

- 单次 bash：`timeout<=60000ms`；独立命令同一消息并行；不要用 `&&` 串独立命令。
- 长任务清单：

| job_id | 后台启动命令 | 预计时长 | 日志 | PID/锁 | 轮询间隔 | 恢复/续跑方式 |
|---|---|---|---|---:|---|---|
| J1 | <Start-Process/nohup ...> | <2h> | <run.log> | <pid/heavy_01> | <60s> | <checkpoint/续跑命令> |

## 5. Audit（并行、抽样、只审 green/晋级；<=20% 生产墙钟）

- 审计对象：<green/晋级候选 task_id 列表>
- 审计方法：<独立复现/脚本校验/抽样双跑>
- 审计 agent（并行）：<agent_id 列表>；审计并发 `<= 生产并发 20%`
- 时间盒：<= 本 Cycle 生产墙钟的 20%；超时记 `unverified` 并继续，不阻塞下一 Cycle
- 未审 green 标记：`unverified`（不得宣称达标）

## 6. Plan Review（冻结前逐项打勾；禁词表见 `references/prompts.md` §0.2）

- [ ] Directions 覆盖全部已想到方向（xhigh+ 不得少列；不是 2–4 个）
- [ ] 不确定项已写入 `Assumptions`；未调用 `question`/ask 提问工具
- [ ] 无任何延期项/保留项（禁词表见 §0.2）
- [ ] Dispatch Tree 完整到 worker，lead/manager 子 PLAN 与本表一致
- [ ] 每个 worker 任务有输入/输出/验收/预算/fp12/owner/依赖
- [ ] 无依赖任务同波并行；依赖 DAG 无环
- [ ] 每条 bash <=60s；长任务有后台/日志/PID/轮询/恢复
- [ ] 审计并行、抽样、只审 green/晋级，时间盒 <=20%
- [ ] Cycle 关闭条件 = 所有 Directions 有结果（keep/kill/probe-more/closed）或外部 blocked；无跨 Cycle 遗留
- [ ] plan_hash 已填，status=frozen

Review notes（写要更新的部分，改完再冻结；所有 review 发现必须在本 Cycle 内处理，不得延期）：
- <review 发现的问题 1 -> 已改：...>
- <review 发现的问题 2 -> 本轮内证伪/验证动作（必须在本 Cycle 执行）：...>

## 7. Amendments（计划变更必须显式）

| amend | 时间 | 改了什么 | 原因 | 重新 review 人/时间 | 新 plan_hash |
|---|---|---|---|---|---|
| A1 | ... | ... | ... | ... | ... |
```

> `PLAN_REVIEW.md` 可直接复制 PLAN 的 `## 6. Plan Review` + Review notes，并记录 `plan_hash`；
> 或保留在 PLAN.md 的 `## Review` 段。两者必须有其一，否则视为未评审。

**DISPATCH.jsonl**（每次 `task` 派生追加一行；用于核对 PLAN 是否真的全并行执行）：

```json
{"ts": "YYYY-MM-DDTHH:MM:SS+08:00", "cycle": "C0001", "wave": "W1", "parent": "lead-1",
 "agent_id": "mgr-1", "subagent_type": "swarm-lead", "task_id": "D1",
 "session_id": "ses_...", "status": "spawned|done|lost"}
```

## §5.2 `cycles/<C>/RESULTS.md` 模板（每 Cycle 收口写）

```markdown
# <SWARM> Cycle <C> RESULTS

- plan_hash: <对应 PLAN>
- started/finished: <...>
- status: running|collected|closed

## 1. Directions 结果（逐方向，不得漏）
| ID | 方向 | 结果 | 关键数字/证据 | 判定 | 产物 |
|---|---|---|---|---|---|
| D1 | ... | ... | ... | keep/kill/probe-more | <路径> |

## 2. Agent 结果（并行执行情况）
| agent_id | session_id | 状态 | 结论 | 产物 | 用时 |
|---|---|---|---|---|---|
| ... | ses_... | done/lost | ... | ... | ... |

## 3. Audit（并行/时间盒执行情况）
- 审计对象/抽样率/用时/占生产墙钟比例：<...>；审计并发占生产并发：<...>%
- 结论：pass/fail/unverified（未审 green 不得宣称达标）

## 4. 本 Cycle 新发现的方向（写入下一 Cycle PLAN）
- <新方向 + 证据 + 建议 owner>

## 5. Closed（本 Cycle 内证伪，禁止回头）
- <方向/路径 + 证据 + 关闭原因>

## 6. 下一 Cycle 计划输入（不是延期清单）
- <必须进入下一 Cycle Directions 的全部方向；不得留待以后>

## 7. 未完成/blocked（必须在同一 Cycle 内续派/拆解）
- <方向 + 原因 + 同 Cycle 续派记录（agent_id/session_id/新任务）；不得滚到下一 Cycle>
```

## §6 `checkpoints/gen_<n>.md` 模板（root 写）

```markdown
# Generation <n> — swarm<N> checkpoint

- 日期/root/状态（达标数、STOP 是否触发、预算使用）
- cycle_id / plan_hash / PLAN 状态（reviewed/frozen）
- 使命与协议版本回顾（一行）

## 1. 执行与预算
<波次/链数/代理数/实验数/heavy 小时/test_uses 与 registry 对账>

### Cycle / PLAN 对账
- cycle_id / plan_hash / status / Directions 数 / Dispatch 行数 / 并行波次数
- 延期项/保留项：无（xhigh+ 必须为 0）
- bash 超 60s 次数：0；长任务后台数/轮询：<...>
- 审计墙钟占生产墙钟：<n>%（必须 <=20%）；审计并发占生产并发：<n>%（必须 <=20%）

### 在途/本代代理（恢复用）
| agent_id | role | session_id (ses_...) | 状态 | 产物 |
|---|---|---|---|---|
| ... | ... | ... | running/done/lost | ... |

### 会话备份
- `session_backup.py export-state` 执行时间/结果：<...>
- `<SWARM>/sessions/` 文件数/总大小：<...>

## 2. 本代结果（每任务一行：prev / 指标+CI / 基线 / required / headroom / 判定）

## 3. 审计与 root 裁决（关键裁决编号 R-...）

## 4. 冻结/证伪清单（防回头）

## 5. 下一 Cycle 输入与待办（xhigh+ 待办必须进入下一 Cycle Directions，不得延期）
```

## §7 `runs/<agent_id>/NOTES.md` 模板（worker 写）

```markdown
# <agent_id> — <任务一句话>

- agent_id/role/parent/root/task_id/track/run_token/SESSION_ID；granularity（原子单元）/fp12；
  PLAN 行号或子树 PLAN 路径；日期；纪律声明（未触 test/未 git/raw 只读）
- 耗时；heavy 槽 acquire/release 时间；产物路径
- bash 调用次数/最长耗时（必须 <=60s）；长任务后台 PID/日志/轮询间隔

## 脚本与命令（新增，未改既有）
<命令 + run.log 路径>

## 校验（脚本内置断言，全部 PASS/FAIL）
<逐条：与既有产物 sha1 对比、复算一致性、QC 条目>

## 结果（主指标 + CI + prevalence + 辅助口径）
<数字表；若涉及 test：登记行号与 fp12>

## 对照（平凡基线/回归均值/泄漏敏感性）

## 结论 / 新假设 / 遗留异常
```

## §8 预注册卡模板（prereg/）

```markdown
# 预注册卡 <task_id>（<版本>，冻结时间）

1) 任务/标签规则（可执行：数据源/字段/阈值/持续时长/时间锚）
2) 队列与 split（版本、哈希、样本数、prevalence）
3) 特征时间锚（防泄漏：特征窗与标签窗严格关系）
4) 模型与阈值口径（valid best-F1 / 分位匹配；选择规则；tie-break）
5) test 单次登记（canonical + fp12，planned→used）
6) 技能门基线（冻结 sha1；一旦用于门禁不得再改）
7) 复现要求（≥2 split / ≥3 seeds / 簇 bootstrap / 亚组 FDR）
8) 停止与晋级判定
9) 预期产物清单
```

## §9 目录布局总览

```
repo/
├── docs/swarm<N>/            # 入库：CHARTER / PROTOCOL / ROADMAP / 交付报告 / REPRODUCE_* / cycles/（PLAN/RESULTS 快照）
├── swarm<N>/                 # gitignore 运行时
│   ├── state.json  agent_log.jsonl  backlog.jsonl  leaderboard.csv  test_uses.jsonl  STOP
│   ├── checkpoints/gen_*.md
│   ├── cycles/<C>/{PLAN.md,PLAN_REVIEW.md,PLAN.amend.*.md,DISPATCH.jsonl,RESULTS.md}
│   │   ├── leads/<lead_id>/PLAN.md
│   │   └── managers/<mgr_id>/PLAN.md
│   ├── claims/  registry/  locks/  prereg/  tracks/  track_notes/
│   ├── runs/<agent_id>/{NOTES.md, metrics.json, cmd.txt, SESSION_ID, artifacts/}
│   ├── sessions/<agent_id>.json      # opencode export 备份（同 id 可 import 恢复）
│   ├── batches/<batch_id>/{chunks,results,out,manifest.json}   # 批量同构任务（high+）
│   └── tools/{append_jsonl.py, heavy_lock.py, session_map.py, session_backup.py}
└── .gitignore                # 确保 swarm<N>/ 整体忽略
```
