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
- 每任务输出：prevalence、baseline、主指标+CI、required、headroom、判定
- 晋级：headroom 高/可及 → 深挖（特征/模型/锚点/严重度设定扫描）
- 停止：① 主目标达成 ② 穷举证伪/多代无新达标 ③ 预算触顶 ④ 用户 STOP
- 反作弊：不得用 test 调参；亚组预注册+FDR；新标签必须过泄漏审计

## 5. 唯一口径
<筛选协议版本、队列、split、特征、模型、阈值规则、bootstrap 设置>
```

## §3 `PROTOCOL.md` 骨架（docs/swarm<N>/，入库）

把 `references/protocol.md` 的最终版复制进来，替换：
- `<SWARM>`/`<DOCS>` 实际绝对路径
- 并发上限（每层 ≤N）、物理槽数、预算硬闸数字
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
```

## §5 运行时文件 Schema（swarm<N>/，gitignore）

**state.json**（root 独占）：

```json
{
  "phase": "swarm<N>",
  "generation": 0,
  "agents_launched": 0,
  "experiments_done": 0,
  "heavy_hours_used": 0.0,
  "budget": { "max_agents": 10000, "max_experiments": 5000, "max_heavy_hours": 600, "max_generations": 300 },
  "started": "YYYY-MM-DD",
  "status": "boot | running | innovation-phase | stopped | converged",
  "primary_goal": "<一句话>"
}
```

**backlog.jsonl**（每行一个任务，owner 只改自己条目）：

```json
{"id": "V001", "track": "meta", "priority": 1, "status": "ready|claimed|done|frozen", "heavy": false,
 "spec": "任务描述（可执行）", "inputs": ["路径/表"], "accept": "验收标准", "budget_min": 90,
 "result": "DONE: 关键数字; fp12 ...  或  KILL: 原因"}
```

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
 "track": "meta", "detail": "dispatched by root gen1 (wave1)"}
```

**test_uses.jsonl**（planned→used 两行，fp12 相同）：

```json
{"ts": "...", "task_id": "D1", "agent_id": "g1-v002-w1", "track": "D1", "model": "hgb3",
 "label_rule": "pressor_response_5min_10mmHg", "split": "split42",
 "canonical": "D1|pressor_response_5min_10mmHg|feat_B15|hgb3|split42", "fp12": "a367562f9cd1",
 "purpose": "test single evaluation", "status": "planned"}
{"...": "...", "status": "used", "metrics": {"f1": 0.51, "f1_ci_low": 0.47, "auroc": 0.76, "n_test": 1778}}
```

**STOP**：空文件即可；内容建议写 `reason=<...> date=<...>`。

## §6 `checkpoints/gen_<n>.md` 模板（root 写）

```markdown
# Generation <n> — swarm<N> checkpoint

- 日期/root/状态（达标数、STOP 是否触发、预算使用）
- 使命与协议版本回顾（一行）

## 1. 执行与预算
<波次/链数/代理数/实验数/heavy 小时/test_uses 与 registry 对账>

## 2. 本代结果（每任务一行：prev / 指标+CI / 基线 / required / headroom / 判定）

## 3. 审计与 root 裁决（关键裁决编号 R-...）

## 4. 冻结/证伪清单（防回头）

## 5. 待办与 Gen-<n+1> 建议（按优先级）
```

## §7 `runs/<agent_id>/NOTES.md` 模板（worker 写）

```markdown
# <agent_id> — <任务一句话>

- agent_id/role/parent/root/task_id/track；日期；纪律声明（未触 test/未 git/raw 只读）
- 耗时；heavy 槽 acquire/release 时间；产物路径

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
├── docs/swarm<N>/            # 入库：CHARTER / PROTOCOL / ROADMAP / 交付报告 / REPRODUCE_*
├── swarm<N>/                 # gitignore 运行时
│   ├── state.json  agent_log.jsonl  backlog.jsonl  leaderboard.csv  test_uses.jsonl  STOP
│   ├── checkpoints/gen_*.md
│   ├── claims/  registry/  locks/  prereg/  tracks/  track_notes/
│   ├── runs/<agent_id>/{NOTES.md, metrics.json, cmd.txt, artifacts/}
│   └── tools/{append_jsonl.py, heavy_lock.py}
└── .gitignore                # 确保 swarm<N>/ 整体忽略
```
