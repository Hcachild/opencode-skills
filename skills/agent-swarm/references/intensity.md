# 强度等级（Intensity）

默认 **medium**。强度不是"多派几个 agent"，而是同时放大探索宽度、验证深度、恢复能力和治理成本。
**等级越高，越严格**：高等级不能降低预注册、test 单次、技能门、raw 只读、会话备份等硬规则。

## 1. 两个预算口径

| 口径 | 含义 | 谁控制 |
|---|---|---|
| **重槽并发 `max_heavy_slots`** | 同时允许跑多少个重型任务；按 CPU/GPU/内存配额标定 | 机器/集群容量 |
| **重槽时 `max_heavy_hours`** | 所有重任务时长之和；128 槽满负荷 7 天 ≈ 21,504 槽时 | sponsor 预算 |
| **代理并发 `max_parallel_agents`** | 同时在跑的代理数；受 API 速率/协调开销限制 | 强度等级 |
| **累计代理 `max_agents`** | 整个 campaign 的派生总数 | 强度等级 |

> 槽位是吞吐上限，槽时是总预算；两者都不能超卖。到 80% 槽时暂停派生写 checkpoint，100% 硬停。

## 2. 等级表（建议默认值，可按硬件/经费乘系数）

| 等级 | 重槽并发 | 代理并发 | 累计代理 | 墙钟 | 重槽时 | 验证/审计（并行，并发/墙钟<=20%） |
|---|---:|---:|---:|---|---:|---|
| **low** | 4 | 1–4 | 1–8 | 15m–4h | 8–64 | 1 split / 1 seed / 抽检 |
| **medium（默认）** | 16–32 | 10–30 | 30–80 | 1–3 天 | 500–2,000 | 2 splits / 3 seeds / 1 条审计线 |
| **high** | 128 | 64–192 | 200–600 | 1–2 周 | 10,000–30,000 | 3 splits / 5 seeds / 红队 + 抽样双审计（并行、时间盒） |
| **xhigh** | 256–512 | 200–600 | 800–2,500 | 3–8 周 | 50,000–150,000 | 5+ splits/中心 / 10 seeds / 独立复现 / 外部验证 |
| **max** | 1,024+ | 1,000–3,000 | 3,000–10,000 | 2–6 个月 | 200,000–800,000 | 自动审计 swarm / 多模型族 / 留出封存（并行、时间盒） |
| **infinite** | 弹性 1,024–4,096 | 2,000–8,000 | 20,000+ 累计 | 持续 | 滚动 100,000–500,000/月 | 持续审计 / 漂移监测 / 定期再验证（并行、时间盒） |

## 2.1 任务细分程度（强度决定粒度）

强度越高，单个任务必须越**原子**：更多代理需要互不重叠的工作单元，验证也需要独立单元。

| 等级 | 任务粒度 | 主要拆分维度 | 单任务预算 | 典型任务数 | 验收单元 |
|---|---|---|---:|---:|---|
| low | 问题/脚本级 | 按问题或步骤粗拆 | 15min–2h | 1–8 | 人工抽检 |
| medium | 假设/变体级 | 标签 × 特征集 × 模型 × split | 1–4h | 30–80 | 单指标 + 平凡基线 |
| high | 原子实验级 | 数据切片 × 模型 × seed × split | 2–8h | 200–600 | 预注册 + CI + 审计 |
| xhigh | 矩阵单元 + 独立复核 | 中心 × split × seed × 模型族 × 复核维度 | 4–12h | 800–2,500 | 独立复现 + 外部验证 |
| max | 微假设/单元级 | 自动生成假设 × 数据切片 × 模型族 | 1–8h | 3,000–10,000 | 自动审计 + 证据图 |
| infinite | 持续微任务队列 | 机会/漂移/新数据/旧结论再验证 | 1–8h | 持续 | 版本化知识库 + 定期再验证 |

**拆分规则**：

- 一个 worker 只做一个原子单元；单任务必须有 `scope / inputs / outputs / acceptance / budget / fp12`，且不与其他任务共享写目标。
- 任务**一个预算内做不完** → 按数据切片、时间窗、seed、split 或审计维度继续拆；**两个 worker 可能写同一产物** → 合并或加锁。
- 粒度太粗（high 还用 medium 的变体级任务）→ 代理空转、重复劳动；粒度太细（low 拆到单文件单行）→ 协调成本 > 执行。
- **细粒度必须配防重**：high+ 每个原子任务写 `fp12` 并查 `registry/`；max/infinite 需要自动去重 + closed list，否则几千个代理会重复爆炸。
- **验证单元独立**：xhigh+ 的复核/审计任务不能由产出该结果的同一个 worker 承担。
- **backlog 规模 ≈ 任务数**：medium 30–80 行、high 200–600、xhigh 800–2,500、max 3,000–10,000、infinite 持续队列；先按粒度把 backlog 拆出来，再派 worker，不要边派边想。

## 2.2 high+ 与批量处理 skill 协同

对**扁平、同构、数量大**的工作（成千上万条逐条分类/提取/打标/翻译/清洗/校验），不要用"每条一个 worker"，
改用批量分片模式；它和层级 swarm 是互补关系：层级 swarm 管研究主线，批量 skill 管大批量同构执行。

| 等级 | 批量处理策略 |
|---|---|
| low | 不适用 |
| medium | 可选（数据量 > 几百条时建议用） |
| high | **必须检查并按需使用**；抽样 3–5% 分片人工复核 |
| xhigh | 必须使用；随机 1–2% 分片双跑比对 |
| max | 必须使用；自动审计 + 去重 + 异常分片重跑 |
| infinite | 持续批量队列；版本化 manifest + 结果归档 |

**执行契约**：

- 推荐 skill：`parallel-data-processing`（本地 `~/.config/opencode/skills/parallel-data-processing/`）。
  找不到时到用户 GitHub（Hcachild）找批量处理 skill/repo；再没有就按同一模式手写 split/merge 脚本。
- 分片 10–50 条/worker；每批 20–30 个并行；分片 ID / manifest 是回填与校验的唯一依据。
- 任务粒度在 backlog 里标 `batch-shard`（覆盖默认的原子实验粒度）。
- 结果路径：`<SWARM>/batches/<batch_id>/{chunks,results,out}`，不写仓库根。
- 防重：`sha1(manifest|chunk_id|规则版本)[:12]`，一个分片一个 claim；已存在结果且校验通过则跳过。
- 校验：先 `check-only`（每个分片有 JSON、可解析、ID 数量/顺序与 manifest 完全一致），**未通过不得合并**；
  失败只补跑对应分片。
- 审计：high 抽样 3–5%；xhigh 随机 1–2% 双跑比对；max/infinite 自动审计与异常重跑。
- 内容保真：原文/问题字段从 manifest 回填，不依赖 Agent 转写；Agent 只产出新增结果字段。
- 记录：每个分片 worker 除结果 JSON 外，还要写 `runs/<agent_id>/NOTES.md`（分片号/条数/结果路径/check/session id）。

## 2.3 high+ 自检清单

- [ ] `state.intensity_profile`：`max_heavy_slots=128`、`batch_policy=required`（high）。
- [ ] `<SWARM>/tools/batch/` 存在 `split_data.py`、`merge_results.py`；`batches/` 已建。
- [ ] 实际链是 root→lead→manager→worker，未跳级；worker 是叶子。
- [ ] root 加载/使用 `agent-swarm`；lead/manager 加载/使用 `parallel-data-processing`；worker 至少能加载该 skill。
- [ ] 批量任务有 `manifest.json`；`check-only` 通过后才 merge；失败分片单独补跑。
- [ ] 每个代理有 `SESSION_ID`；`agent_log.jsonl` 有 `session_id`；`state.active_sessions` 完整。
- [ ] 当前 Cycle 的 `PLAN.md` 已写、已 review、已冻结（`plan_hash` 有值）；lead/manager 子 PLAN 与主 PLAN 一致。
- [ ] Directions 覆盖全部已想到方向（xhigh+ 不是 2–4 个）；每行状态为 dispatch/probe/closed，**无延期项**。
- [ ] Dispatch Tree 完整到 worker；无依赖任务同波并行；依赖 DAG 无环；无"派一个等一个"。
- [ ] 每条 bash `<=60s`；长任务有后台启动/日志/PID/轮询/恢复方案；独立 bash 同消息并行。
- [ ] 审计并行、抽样、只审 green/晋级；审计并发 `<= 生产并发 20%`，审计墙钟 `<= Cycle 生产墙钟 20%`；未审 green 标 `unverified`。
- [ ] `session_backup.py export-state` 成功，`sessions/` 文件数与代理数一致。
- [ ] 每个 worker 有 `runs/<agent_id>/NOTES.md`（含分片/条数/结果路径/check/session id）。
- [ ] `intensity=infinite` 时：`never_stop_scope` 覆盖的执行体（默认仅 depth-1 root）prompt 均原样包含
      `references/prompts.md` §0.1 全文；未覆盖的 lead/manager/worker 不加块、有限返回；抽查会话首条 prompt。
- [ ] root 更新 `leaderboard.csv`、`backlog.jsonl`、`checkpoints/gen_<n>.md`、`cycles/<C>/RESULTS.md`。

## 2.4 规划、Cycle 与执行时间盒（所有等级）

| 等级 | PLAN.md | Cycle | 方向广度 | Cycle 上限 | 审计时间盒 |
|---|---|---|---|---|---|
| low | 每个任务/脚本前 | 无 | 任务范围 | - | 抽检，`<=20%` |
| medium | 每代/每批前 | 无 | 计划变体全列 | - | `<=20%` |
| high | 每代/每波前 | 无 | 计划 track 全列 | - | `<=20%` |
| xhigh | 每 Cycle + 子树 | 有 | **全部已想到方向** | 无固定上限 | `<=20%` |
| max | 每 Cycle + 子树 | 有 | **全部已想到方向** | 无固定上限 | `<=20%` |
| infinite | 每 Cycle + 子树 | 有 | **全部已想到方向** | **无限** | `<=20%` |

**硬规则**：

1. **先 PLAN 后派发**：root 写主 `cycles/<C>/PLAN.md`，lead/manager 写本子树 PLAN；
   必须 review、冻结 `plan_hash` 后才能派生任何 SubAgent。未冻结 = 不得派发。
2. **xhigh+ 方向全量**：每个 Cycle 的 Directions 必须覆盖当前**全部**已想到方向（主/竞争假设、
   失败模式、替代数据/标签/模型/锚点、反例/审计）；不是 2–4 个"先试试"，不设人为上限。
3. **xhigh+ 无延期项**：PLAN 正文禁止“下一步 / 可选项 / 可选 / open / TBD / 待定 / 后续 / 备选 /
   TODO / 视情况 / 有时间再做”。不可行方向也要在本 Cycle 派一个 `probe`（最小证伪），结论写
   `RESULTS.md` 的 closed 列，不能留到下一轮。
4. **Cycle 仅 xhigh+**：xhigh/max 不设固定 Cycle 上限，infinite 的 Cycle 无限；`max_generations`
   xhigh+ 只作外层 checkpoint 计数，不限制 Cycle。每轮按 `RESULTS.md` 更新下一轮 PLAN，允许换方向/换杠杆/重分解，
   但不得以"完成/失败/阻塞/无进展/资源不足"自停。
5. **并行优先**：无依赖的 bash 命令同一消息并行；无依赖的 SubAgent 同一波次并行派生；
   有依赖必须写显式 DAG，依赖解除后立即并行。禁止"派一个、等一个、再派下一个"。
6. **bash 时间盒**：每条命令 `<=60s`（显式 `timeout<=60000`）；长任务必须后台启动 + 轮询，
   PLAN 写明启动命令/日志/PID/预计时长/恢复方式；禁止一个调用阻塞等待训练完成。
7. **审计时间盒**：审计与生产并行、抽样、只审 green/晋级候选；审计并发 ≤ 生产并发的 20%，
   审计墙钟 `<= Cycle 生产墙钟的 20%`；超时记 `unverified` 并继续；未审 green 不得宣称达标；
   禁止串行全量复核。
8. **Cycle 关闭条件**：所有 Directions 都有结果（keep/kill/probe-more/closed）或外部 blocked；
   未完成方向必须在同一 Cycle 内续派/拆解/换工具，不能滚到下一 Cycle。

## 3. 逐级说明

### low — 单点核查
- 任务粒度：问题/脚本级；1 个 lead 带 2–4 个 worker，1 代结束；不设 manager。
- 只回答一个窄问题；结果用于决策，不用于对外宣称。
- 示例：核对几个脚本有没有未来信息、几张表 join 键是否一致、扫 5 个阈值看方向。

### medium — 小规模多假设（默认）
- 任务粒度：假设/变体级；root → 2–3 条 track → manager → worker；2–3 代。
- 预注册选择规则；决赛变体 2 splits / 2–3 seeds；必须过平凡基线。
- 适合：特征/标签/模型的小网格筛选，选 1–2 个方向晋级。
- 示例：3 种标签 × 4 种特征 × 2 个模型，选 1–2 个进 high。

### high — 标准长跑研究
- 任务粒度：原子实验级（一个数据切片 × 模型 × seed × split = 一个 worker）。
- 完整四层；3–8 条 track；3–6 代；root 接棒。
- **每波先 PLAN + review/冻结**；无依赖任务同波并行；bash `<=60s`，长任务后台；审计并行、抽样、`<=20%` 墙钟。
- **128 重槽**；需要 queue-master 专管排队、优先级、stale lock。
- 双 split + 3–5 seeds + 簇 bootstrap + 泄漏审计；绿标必须过红队。
- 示例：MOVER-SIS 这类多任务研究、论文主线。

### xhigh — 项目级/论文级攻坚
- 任务粒度：矩阵单元 + **独立复核单元**；产出与复核必须不同 worker。
- **Cycle 模式**：每 Cycle = 写/评审/冻结 PLAN → 全并行派发 → RESULTS → 更新下一 Cycle PLAN；
  不设固定 Cycle 上限（`max_generations` 只作外层 checkpoint 计数）。每个 Cycle 的 Directions 必须覆盖全部已想到方向，
  禁止 2–4 个"先试试"和任何延期项。
- 按方向需要开子 swarm + 独立审计/红队 + meta 汇总，不人为限定 2–4 个；外层代 6–12。
- 256–512 槽；建议接中央队列/多机调度，`heavy_lock.py` 只做本地闸门。
- ≥5 splits/中心、10 seeds、外部验证、独立重实现绿标、claim provenance；
  这些只对 green/晋级候选执行，与生产并行、抽样、时间盒（不要求全部任务都做）。
- 并行/时间盒：无依赖 SubAgent 同波；单次 bash `<=60s`；审计与生产并行且 `<=20%` Cycle 墙钟。
- 示例：多中心临床验证、专利/毕业论文关键 claim。

### max — 探索型大科学/穷举
- 任务粒度：微假设/单元级；假设由系统自动生成，每个假设拆成可独立验证的最小单元。
- **Cycle 模式**：不设固定 Cycle 上限；每轮 Directions 覆盖全部已生成/已想到方向，禁止延期项；
  不可行方向派 `probe` 证伪并写入 closed。
- 多个子程序并行；meta-curator + 假设生成/执行/审计/综合四条线；外层代 10–30，Cycle 不设上限。
- 1,024+ 槽；Slurm/K8s + 配额；自动审计 swarm + 多模型族 + 留出封存。
- 收口：只有预算/外部 STOP/安全红线可停；"目标达成"只转下一 Cycle 的验证/扩展，不自我停止；
  "边际信息增益 < 成本"只转换杠杆/换方向，不结束执行体。
- 并行/时间盒：无依赖同波；bash `<=60s`；长任务后台；审计并行且 `<=20%` Cycle 墙钟。
- 示例：全库表型发现、超大标签/特征/超参空间搜索。

### infinite — 常驻研究系统（理论无限）
- 任务粒度：持续微任务队列（新数据/漂移/旧结论再验证）；任务有 provenance、过期时间和优先级。
- **无限执行 scope**：`never_stop_scope` 决定谁带 §0.1 永不终止块。默认 `root`：只有 depth-1 root
  无限执行；lead/manager/worker 有限返回，保证 root 收结果。用户可显式设 `all`（所有 SubAgent 无限）
  或 `depth:N`（深度 `<=N` 无限）。被覆盖的 prompt 必须原样包含全文；未覆盖的不加块。
  完成/失败/阻塞/无进展只触发状态转换并继续，不触发停止；只有用户/Sponsor `STOP`、预算硬闸、安全红线可外部收口。
- **Cycle 无限**：每 Cycle = 写/评审/冻结 PLAN → 全并行派发 → RESULTS → 更新下一 Cycle PLAN；
  Cycle 数量无限，执行体不得自停。每轮 Directions 覆盖全部已想到方向，禁止 2–4 个裁剪与任何延期项。
- 常设 meta-curator + 轮换 root + 按机会开子 swarm；人类 sponsor 作为 board。
- 不设固定代数上限，但设**滚动月度预算**（槽时/代理数/token）；持续审计与漂移监测。
- 月度滚动：每月 checkpoint 时 sponsor 重置 `heavy_hours_used`/窗口计数（或归档 `state.month_YYYYMM.json` 后归零）；`max_agents`/`max_experiments` 只是软上限，实际以月度槽时/token 为准。
- "无限"不是永动机：受算力、数据、经费、人类注意力与边际价值限制；某条线价值耗尽就冻结/降级/换杠杆，
  但执行体继续跑其他线或对该线做再验证，不得因此自我停止。
- 示例：课题组数据科学平台、部署模型持续再验证。

## 4. 同一问题的六种打法

以"ICU 低血压预测"为例：

- **low**：4 槽，1 个 baseline、1 个 split，半天回答"有没有信号"。
- **medium**：16–32 槽，3 种标签 × 3 种特征 × 2 个模型，3 天选 1 个晋级。
- **high**：128 槽，10 个任务卡、3–5 代、3 splits + 5 seeds + 红队，1–2 周。
- **xhigh**：256–512 槽，多中心外部验证、10 seeds、独立复现、临床效用，1–2 个月。
- **max**：1,000+ 槽，自动搜索标签/特征/模型空间，50–100 个候选表型 + 上界报告，3–6 个月。
- **infinite**：弹性 1,000–4,000 槽，常驻平台持续吸收新数据、监控漂移、定期再验证，按月滚动预算。

## 5. 组织与基础设施随等级升级

| 能力 | low | medium | high | xhigh | max | infinite |
|---|---|---|---|---|---|---|
| 规划 | 任务前 PLAN | 每代 PLAN | 每波 PLAN | 每 Cycle PLAN + 子树 | 每 Cycle + 自动方向生成 | 每 Cycle + 持续方向生成 |
| Cycle | 无 | 无 | 无 | 无固定上限 | 无固定上限 | **无限** |
| 调度 | 手工 | 文件锁 | 文件锁 128 槽 + queue-master | 中央队列 + 多机 | Slurm/K8s + 配额 | 弹性调度 + 自动扩缩 |
| 组织 | 1 lead | root + 2–3 track | + queue-master + audit lead | + 子 swarm + 独立审计 root | + meta-curator + portfolio manager | + 人类 board + 运营/安全 |
| 恢复 | 结束备份 | 每代 `export-state` | 每代备份 + 禁删会话 | 每波 `export-tree` | 持续备份 + 事故演练 | 长期归档 + 版本化知识库 |
| 审计 | 人工抽检 | 1 条审计线 | 红队 + 抽样双审计（并行、时间盒） | 独立重实现 + 外部验证（抽样、并行、时间盒） | 自动审计 swarm + 模型多样性 | 持续审计 + 旧结论再验证 |
| 执行 | bash `<=60s` | 并行 bash | 并行派发 | 全并行 + DAG | 全并行 + 自动扩缩 | 全并行 + 持续队列 |
| 人类 gate | 结束看一次 | 每代 | 每 2–3 代 | 每 1–2 代 | 每周 steering | 每季度 board |

## 6. 控制规则

1. **sponsor 设定等级**：写入 `CHARTER.md` 与 `state.intensity`；root 不能私自升档，只能申请。
2. **可按 track 覆盖**：max 里可以跑 low 的廉价筛查 + high 的最终验证，不必全线拉满。
3. **自动降档**：连续 2–3 代无新绿标且 closed list 不再增长 → 降档或收敛（xhigh+ 下只冻结/降级该线并换杠杆，
   不结束执行体；收口只能由外部 `STOP`/预算/安全信号触发）。
4. **预算硬闸**：槽时/代理数/代数/实验数到 80% 暂停派生；100% 停（xhigh+ 视为外部信号：
   停派生/写 checkpoint 等 sponsor，不得写成 Cycle 完成）。
5. **人类 gate**：xhigh 每 1–2 代、max 每周、infinite 每季度。
6. **验证随强度上升**：low 可以只跑一次但不得宣称；high+ 必须预注册 + 多 seed + 审计；xhigh+ 必须独立复现。
7. **恢复随强度上升**：low 结束时备份；high 每代 `export-state`；max/infinite 每波 `export-tree`，禁止删会话。
8. **模型策略**：低档用便宜模型跑工人；高档 lead 用强模型、审计用不同模型族，避免"自己产、自己审"。
9. **槽位不超卖**：`slots_requested > slots_available` 时排队，不并发裸跑。
10. **high+ 必须有 queue-master**：管重槽排队、优先级、死锁和 stale lock。
11. **任务粒度随强度**：low 问题级、medium 变体级、high 原子实验级、xhigh 矩阵单元+复核、max 微假设、infinite 微任务队列；粗任务会浪费高等级并发，细任务会压垮低等级协调。
12. **infinite 无限执行 scope**：`never_stop_scope=root`（默认）时只有 depth-1 root 带 §0.1 无限执行，
    lead/manager/worker 有限返回；用户可设 `all` 或 `depth:N`。被覆盖的 prompt 必须原样包含全文；
    未覆盖的不加块。该块只约束自我终止，外部 `STOP`/预算/安全信号仍优先。
13. **先 PLAN 后派发**：root/lead/manager 在派生任何子代理前写 PLAN、评审、冻结 `plan_hash`；
    未冻结不得派发。计划变更走 `PLAN.amend.<n>.md` 并重新评审。
14. **xhigh+ Cycle 无延期**：每个 Cycle 的 Directions 必须覆盖全部已想到方向（不是 2–4 个）；
    禁止"下一步/可选项/open/TBD/待定/后续/备选/TODO"；不可行方向本 Cycle 派 `probe` 并写 closed。
15. **时间盒与并行**：单次 bash `<=60s`；长任务后台 + 轮询；独立 bash/SubAgent 必须并行；
    有依赖写显式 DAG，依赖解除即并行。禁止"派一个等一个"。
16. **审计时间盒**：审计与生产并行、抽样、只审 green/晋级；审计并发 `<= 生产并发 20%`，
    审计墙钟 `<= Cycle 生产墙钟 20%`；超时记 `unverified` 并继续；未审 green 不得宣称达标。
17. **绝对禁止提问工具**：所有代理（含 sponsor 在 swarm 执行链中；root/lead/manager/worker）不得调用
    `question`/ask 工具，不得向用户或父代理提问；不确定项写入 PLAN 的 `Assumptions` 与 NOTES，
    按最小风险路径继续。

## 7. 落地字段

`CHARTER.md` 顶部：

```yaml
intensity: medium          # low|medium|high|xhigh|max|infinite
granularity: variant       # question|variant|atomic-experiment|matrix-cell+replication|micro-hypothesis|continuous-microtask
intensity_rationale: "小规模多假设筛选，选 1–2 个方向晋级"
cycle_mode: none            # xhigh/max/infinite 必须为 unbounded
```

`state.json`：

```json
{
  "intensity": "medium",
  "cycle": 0,
  "cycle_id": "C0000",
  "never_stop_scope": "root",
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
  "budget": {
    "max_agents": 80,
    "max_experiments": 500,
    "max_heavy_hours": 2000,
    "max_generations": 3
  }
}
```

> `xhigh/max/infinite` 设 `cycle_mode="unbounded"`；`infinite` 的 Cycle 无上限。`max_generations` 在 xhigh+ 只作外层 checkpoint 计数，不限制 Cycle。
> `infinite` 的 `never_stop_scope` 默认 `root`（只有 depth-1 root 无限）；用户可显式改 `all` 或 `depth:N`。

初始化：

```powershell
python tools/swarm/init_swarm.py --repo <repo> --name swarm<N> --goal "<目标>" --intensity medium
```

## 8. 反模式

- 用 low 跑论文 claim → 欠统计、不可复现。
- 用 infinite 跑目标模糊的问题 → 资源空转、目标漂移。
- infinite 不附「永不终止执行引擎」块 → 完成一轮就收尾，常驻系统退化成一次性任务。
- 把 infinite 块当免死金牌无视外部 `STOP`/预算/安全红线 → 越权运行，必须按外部信号收口。
- 用 max 跑小数据 → 过拟合与重复劳动。
- 高等级但审计不升级 → 更快产出更多错误结论。
- 只加代理不加减槽 → 机器过载，任务互相拖死。
- high 还用 medium 的粗任务 → 代理空转、重复劳动。
- low 把任务拆太细 → 协调成本 > 执行。
- 细粒度不做 `fp12`/claim → 重复爆炸。
- 高等级不拆独立复核单元 → 自己产、自己审。
- 任务粒度与单任务预算不匹配 → 超时、半成品、假完成。
- 不写 PLAN 就派 SubAgent → 方向遗漏/重复劳动；xhigh+ 必须先评审冻结 PLAN。
- PLAN 里留"下一步/可选项/open/以后再做" → 广度被砍；xhigh+ 必须本 Cycle 全派发，不可行也派证伪任务。
- 把无依赖任务串行派发/串行 bash → 墙钟爆炸；必须同波/同消息并行。
- 一个 bash 调用等 2 小时训练 → 超时不可恢复；长任务必须后台 + 轮询，单次 `<=60s`。
- 审计串行全量复核 → Cycle 被拖死；只审 green/晋级、抽样、并行、`<=20%` 墙钟。
