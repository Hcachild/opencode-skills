# 运行时契约（Runtime Protocol）

所有 swarm 代理必读。以下 `<SWARM>` 指 `swarm<N>/` 运行时目录的绝对路径，
`<DOCS>` 指 `docs/swarm<N>/`。根目录与编号在建 swarm 时确定，之后不得漂移。

## 0. 角色、深度与分支

| 角色 | 类型 | 职责 | 派生 |
|---|---|---|---|
| Sponsor | 主会话（primary） | 建宪章、发 root brief、每代收口（commit/push docs）、与用户决定收敛 | 只派生 root |
| root curator | `swarm-lead` (d1) | 代际调度、派 lead/manager、合并 leaderboard、写 checkpoint、停止与接棒裁决 | ≤128 子 |
| track-lead | `swarm-lead` (d2) | 一条赛道：读 backlog、定变体网格、派 manager、汇总赛道结果 | ≤128 子 |
| manager | `swarm-lead` (d3) | 把任务拆为 2–4 个互斥原子实验，派 worker、收集与初验 | ≤128 子 |
| worker | `swarm-worker` (d4) | 只做一个原子实验/分析；**不得派生**（tools.task=false） | 0 |

- 实际谱系深度 ≤6；全局 `subagent_depth: 12`（约 11 级接棒链）。
- root 上下文将满：写 checkpoint（状态/榜单/待办/预算/建议），派生继任 root 交接，自增深度。
- 子代理类型一律 `swarm-lead`（可派生）/ `swarm-worker`（叶子），不用 `general`。

## 1. 启动契约（每个代理 prompt 必含）

`agent_id`、`role`、`track`（任务 ID 或 meta）、`task_id`、`parent`/`root`、
必读文件清单、输入路径、验收标准、预算（分钟 + 是否抢重槽）、停止规则。
开工第一步：读 `<DOCS>/{CHARTER,PROTOCOL,ROADMAP}.md` 与相关运行时文件，再动手。

## 2. 运行时目录（`<SWARM>/`，gitignore）

```
state.json                 全局指针（root 独占写）
agent_log.jsonl            代理启动/结束日志（所有代理用 tools/append_jsonl.py 追加）
backlog.jsonl              任务/假设队列（lead+ 追加；owner 更新自己条目的 status）
leaderboard.csv            已验证榜单（root 独占写）
track_notes/<track>.md     赛道叙述（track-lead 写）
tracks/<track>/candidates.csv  赛道候选结果（track-lead 写）
runs/<agent_id>/           单任务产物（worker 写：NOTES.md, metrics.json, cmd.txt, artifacts/）
claims/<task_id>.claim     任务领取（独占创建）
registry/<fp12>.done       实验指纹注册（防重复）；复现用 .repro_<agent_id>
locks/heavy_01..NN.lock    重任务物理槽（独占创建；内容 agent|iso|eta_min）
checkpoints/gen_<n>.md     root 每代 checkpoint
prereg/                    预注册（协议、计划、任务卡模板）
test_uses.jsonl            test 使用登记（planned→used 两行）
tools/                     append_jsonl.py / heavy_lock.py
STOP                       出现即全体停止派生
```

**路径纪律**：全部使用绝对路径；严禁在仓库根创建 `runs/`、`track_notes/` 等目录。

## 3. 领取、防重、防冲突

- **领取**：`New-Item <SWARM>/claims/<task_id>.claim -ItemType File -ErrorAction Stop`；
  已存在且 <6h 则换任务；>6h 视为死代理，先改名 `.stale` 再建。
- **防重指纹**：`fp12 = sha1(task_card|features|model|params|index|seed|cohort)[:12]`；
  跑前查 `registry/<fp12>.done`（存在则跳过），完成后创建。
- **唯一写权**：worker 只写自己 `runs/<id>/` 与 claims；track-lead 只写本 track 文件；
  root 独占 leaderboard/state/checkpoints/tracks 上层。禁止互写、禁止改共享代码。

## 4. 资源与算力

- 重型训练（全量/长序列/多 seed）必须持槽：`scripts/heavy_lock.py acquire --agent <id> --locks-dir <SWARM>/locks --slots NN`；
  无槽先做轻任务或等待；槽 start 超 `--stale-min`（默认 150min）自动失效可重抢；完事 `release`。
- 整机重任务并发 = 槽数（按 CPU 核数/内存定，如 20 逻辑核/32GB → 16 槽）。
- 子集筛查（如 ≤2000–3000 人）先跑；只有效应 > 2× 划分噪声才晋级全量；子集→全量缩水 >0.05 要复核。
- 单 worker 预算：轻 ~15min、重 ~90–180min；超预算先报告再继续。

## 5. 预算与派生纪律（硬闸）

派生任何子代理前检查（任一越限 → 停派生、写 checkpoint、退出）：

```
agent_log.jsonl 行数 < state.budget.max_agents        （如 10000）
runs/ 数量          < state.budget.max_experiments    （如 5000）
heavy_hours_used    < state.budget.max_heavy_hours    （如 600）
generation          < state.budget.max_generations    （如 300）
<SWARM>/STOP 不存在
```

同 manager 的 worker 必须任务互斥（不同 task_id / 指纹）。

## 6. 记录契约

- worker 结束必须落盘 `runs/<agent_id>/NOTES.md`（≤40 行摘要即可，含：
  目标 / 数据版本 / 命令 / 结果（主指标 + CI + prevalence + 辅助口径）/ 产物路径与 sha1 / 结论 / 新假设 / 遗留异常）。
- 返回父代理的**最终消息 ≤40 行**：状态、关键数字、文件路径、新假设、下一建议。
- 每个 lead 在 NOTES.md 顶部记录自己的 task_id（可恢复）；root 每代写
  `checkpoints/gen_<n>.md`（执行与预算、榜单增量、审计裁决、阻塞、下代建议）。
- Sponsors 每代把 `docs/experiments.md` 记录 + 交付物 commit/push（数据、权重、运行时永不入库）。

## 7. 评估口径（唯一合法口径）

- **预注册**：变体网格与选择规则先写入 NOTES 再执行；选择只用 valid。
- **test 单次**：valid best-F1（或预注册的等价规则）选定后，test 评估一次；
  比较必须登记 `test_uses.jsonl`（planned → used，含 canonical 与 fp12）。
- **技能门（skill gate）**：F1 > max(all-positive, 简单规则基线)，AUROC > 最佳规则基线；
  未过门 → 只作描述性数字，不计达标。
- **头room 分析**：按 prevalence 计算"达目标 F1 所需 AUROC"（required-AUROC），
  与观测 AUROC 比较：gap ≤0.03 高头room / 0.03–0.08 可及 / >0.08 低（冻结或换设定）。
- **晋级门槛**：全量 + 预注册 + ≥3 seeds + 患者/事件簇 bootstrap CI（1000）+ 亚组 FDR + 泄漏审计。
- **双重 split**：达标任务必须在 ≥2 个独立 split 复现才可宣称/写 STOP。
- **反作弊**：不得用 test 调参；亚组预注册 + FDR；新标签必须过泄漏审计（时间锚、回归均值、事件对齐）；
  高 prevalence 队列须同队列平凡基线对照，防流行度伪影。

## 8. 停止与接棒

- 主目标达成（达标 + 技能门 + 双 split 复现 + 审计通过）→ 立即写 `<SWARM>/STOP`、
  生成复现任务清单（REPRODUCE_gen<n>.md）、报告 root/sponsor，停止扩大探索。
- 穷举收敛：连续多代无新达标且无未测杠杆 → 上界报告（每任务诚实上限 + 证据链 + 已证伪清单），
  状态置 `converged`，停止。
- root 上下文将满：写 checkpoint → 派生继任 root（深度+1）→ 交接包 = checkpoint + state + 待办。
- 用户可随时创建 `STOP` 或口头停止；假 STOP（不过技能门）按完整性宪章撤销并记录。

## 9. 恢复检查清单

1. `state.json`（generation/status/计数）与 `agent_log.jsonl` 尾部对齐；
2. `runs/` 中无 NOTES 的目录 = 在途任务；`claims/*` 与之一一对应；
3. 残留 `locks/*`：内容 agent 已消亡 → `.stale` 清理；
4. **恢复 Task Agent 对话优先、消息极简**：用原 `task_id` 续跑同一子代理会话，
   prompt 只需 "继续"（非必要不发大段背景/规格）；嵌套链由各级自己逐级恢复；
   仅当会话不可恢复时，才发重建 brief（最少事实 + 声明已完成项无需重跑）；
5. 完成后补 leaderboard/state/checkpoint，再启动下一代。
