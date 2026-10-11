# Prompt 模板

占位符用 `<...>`。所有模板都假设已读过本技能 `SKILL.md` 与 `references/protocol.md`。
原则：**下发的每个代理 prompt 都自带完整上下文与硬规则**，不依赖父代理的隐性记忆。

## §1 Sponsor → root curator（每代 launch brief）

```
你是 <项目> swarm<N> 的 root curator（Generation <G>）。嵌套已验证可用（你可派生 swarm-lead 子代理）。

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
- 队形：你(root,d1) → track-lead(swarm-lead,d2) → manager(d3) → worker(swarm-worker,d4)；每层每节点 ≤<128> 子。
- 物理算力槽 <SWARM>/locks/heavy_01..NN（≤<16> 并发训练），轻任务不限。
- 预算硬闸：agent_log ≤<10000> 行；派生前后核对并追加 agent_log。
- 绝对路径；不改共享代码、不 git、不 test 调参、raw 只读。

## 收尾（必须）
1) leaderboard.csv 更新（每任务一行，含技能门与头room 列）；backlog 状态 + 新假设
2) checkpoints/gen_<G>.md
3) 两仓库 docs/experiments.md 追加记录（数据侧有产物则加）
4) state.json（generation=<G>、计数、heavy_hours）
5) 仅当 <STOP 条件> 满足 → 写 <SWARM>/STOP + 交付报告；否则给出下代建议
6) 上下文充足就自己继续下一代；否则写 checkpoint 并启动继任 root

## 返回给 sponsor（≤40 行）
并发执行情况（派生数/层数）、任务结果表（主指标+CI/基线/技能门/头room）、冻结与证伪清单、
预算、阻塞、Gen-<G+1> 建议。
```

## §2 root → track-lead（派发一条赛道）

```
你是 swarm<N> Gen-<G> track lead（agent_id=<gG-<task>-lead>，role=lead，track=<TASK>，task_id=<ID>）。root=<swarm-root-genG>。

必读（先读再动手；全部只读）：
1) <DOCS>/{CHARTER,PROTOCOL,ROADMAP}.md
2) <SWARM>/prereg/<相关协议>.md（不可变，唯一口径）
3) <SWARM>/backlog.jsonl 的 <ID> 行；checkpoints 上代
参考代码/结果（只读）：<路径清单>

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
你负责把本任务拆为 <2-4> 个互斥原子实验并派 <N> 个 worker（subagent_type=swarm-worker，不得再派生）。

预注册（binding，lead 冻结于 <lead NOTES 路径>，本层只记录不修改）：
- 变体网格：<逐组合列出>
- 选择规则：<只看 valid；tie-break；选中后才 test 单次>
- green 判定：<指标阈值 + CI + 技能门>
- 对照要求：<回归均值/平凡基线/泄漏敏感性>

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
只做这一件事，不得派生任何子代理。

输入：<绝对路径清单 + 字段/行数/校验>
任务：<可执行的明确步骤；预注册规则写死，不得按结果更改>
输出：<runs/<agent_id>/ 下 NOTES.md, metrics.json, cmd.txt, artifacts/> + <数据侧产物路径>
验收：<断言：复算一致/命中期望数字/sha1 校验/QC 条目>
预算：<轻/重 分钟数>；重任务先抢槽：python <SWARM>/tools/heavy_lock.py acquire --agent <agent_id> --locks-dir <SWARM>/locks --slots <NN>（完 release）
纪律：不改既有文件；不 git；raw 只读；test 只用一次（框架自动登记 planned→used）；事件用 append_jsonl.py 追加 agent_log。

NOTES.md 必含：目标 / 数据版本 / 命令 / 结果（主指标+CI+prevalence）/ 产物缩短 sha1 / 结论 / 新假设 / 遗留异常。
【回报 manager】≤40 行。
```

## §5 恢复 root（会话中断后）

```
你（swarm<N> root curator，Generation <G>）之前被意外中断。sponsor 已完成现场核查，情况如下：

## 关键事实（无需重跑）
- <已完成的实验及其最终数字/产物路径，逐条列出>
- <在途/未完成任务及其现场状态>
- 现场残留：<claims/locks/state 状态>

## 你的任务（恢复本代并收尾）
1. 恢复嵌套子代理：检查此前派生的子代理是否有未完成/中断的（尤其 <方向>）。
   能拿到原会话的直接续跑；否则按下列信息重建 prompt 重新派发（任务互斥、指纹防重）：
   一级：<session id / agent_id 列表>
2. 清理残留 claims/locks（`.stale` 后重建）；核对 registry/test_uses 无重复消耗。
3. 完成收尾：leaderboard/state/checkpoint/docs 记录；若达标 → STOP + REPRODUCE 清单。
4. 回报 sponsor ≤40 行。

纪律不变：预注册、test 单次、技能门、预算硬闸、绝对路径。
```

## §6 嵌套能力验证（配置后一次性）

```
这是嵌套能力验证，只做一件事（≤3 分钟），不要做任何其他事：
1) 用 task 工具派生一个 subagent_type=swarm-worker 的子代理，其 prompt 为：
   "请创建目录 <验证目录>（若不存在），把内容 nested-ok 写入 result.txt（无换行），然后只回复嵌套成功。"
2) 若 task 工具不可用/调用失败/类型不存在：返回一行 `TASK_TOOL=no reason=<简短原因>`。
3) 若成功：等待子代理返回，检查 result.txt 存在且内容为 nested-ok，回复一行：
   `TASK_TOOL=yes CHILD_REPLY=<子代理回复> FILE_OK=<true/false>`
```
