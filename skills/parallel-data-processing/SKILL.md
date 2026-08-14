---
name: parallel-data-processing
description: 精细化批量数据处理通用工作流。当需要对大量结构化数据逐条进行精细处理（分类、审核、翻译、改写、信息提取、打标、清洗、校验等）时使用，例如"把这些FAQ逐条分类"、"给这1万条记录逐条打标签"、"逐条翻译这个文件"。核心机制：用脚本把数据切成N个分片，并行开启N个Task Agent（默认每个Agent处理10条，数量可由用户提示词控制，支持上百个Agent分批并行），每个Agent独立处理自己的分片并输出JSON结果，最后脚本统一校验并合并结果。触发关键词：批量处理、逐条、逐行、N个Agent、并行处理、数据分类、打标、审核、分片处理。
---

# 精细化批量数据处理（并行 Agent 工作流）

> 对大量数据逐条进行精细处理时使用。不是让一个 Agent 一次性读完所有数据，而是**切成小片，每片一个 Agent**，并行处理后再合并。默认每 Agent 10 条，可配置；支持大规模并行（每批 20~30 个，多批推进，总计可达上百个 Agent）。

## 工作流总览

```
1. 确认任务与参数（处理内容、每Agent条数、输出要求）
2. 提取数据（脚本通用提取 xlsx/csv/txt/jsonl）
3. 分片（split_data.py，默认每片10条，可配置）
4. 并行启动 Agent（Task工具，每批20~30个，循环到全部完成）
5. 校验（merge_results.py --check-only，ID数量与顺序必须一致）
6. 合并输出（按结果字段拆分或合并为一个文件）
7. 与用户核对抽样结果
```

---

## 第一步：确认任务与参数

开工前与用户确认（一句话即可，缺省用默认值）：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 每 Agent 条数 | **10** | 用户提示词可指定，如"每个Agent处理5条"、"每片20条" |
| 每批并行 Agent 数 | **20~30** | 单次消息最多并行这么多 Task 调用；"上百个Agent"= 每批20~30连续推批 |
| 输出格式 | xlsx（与源文件同目录同名） | 可指定 csv/jsonl |
| 结果字段 | 用户定义 | 分类/打标/翻译等任务的输出字段 |

关键约定：
- **数量必须逐条处理，不得合并、不得跳过、不得缩写**，每个 Agent 处理自己分片内的每一条。
- **内容保真**：问题/原文等内容字段一律从源文件复制，不依赖 Agent 转写，避免省略（参照 merge 脚本回填源数据字段）。
- 分片 ID 格式 `<前缀>:R<行号>`（如 `仓库:R103`），用于最终回填与溯源。

## 第二步：提取 + 分片（脚本，用户工作目录）

```powershell
# xlsx（最常见）：跳过表头，Excel行号即ID，每片10条
python <skill>/scripts/split_data.py --input 数据.xlsx --chunk-size 10 --out-dir chunks

# 自定义：每片5条、只取第1和第2列
python <skill>/scripts/split_data.py --input 数据.xlsx --chunk-size 5 --columns 1,2 --out-dir chunks

# 其他格式
python <skill>/scripts/split_data.py --input 数据.csv  --chunk-size 10 --out-dir chunks
python <skill>/scripts/split_data.py --input 数据.txt  --chunk-size 10 --out-dir chunks --format txt
python <skill>/scripts/split_data.py --input 数据.jsonl --chunk-size 10 --out-dir chunks --format jsonl
```

产物：`chunks/chunk_001.txt ~ chunk_NNN.txt`（每片若干条，格式 `ID:`/`TEXT:`/`---`）+ `chunks/manifest.json`（条目清单，供合并回填）。

分片数 = ceil(总条数 / 每Agent条数)。例：2034 条 / 每片10 = 204 片；每片 20 = 102 片。

## 第三步：并行启动 Agent（Task 工具）

每批 20~30 个 Task 并行，循环推进直到全部分片完成。

**Agent Prompt 模板**（对每个分片生成一份，按需替换占位符）：

```
你是<任务角色>。读取 <chunks目录>\chunk_XXX.txt（UTF-8，<每片条数>条数据，
格式 ID:/TEXT:/---，TEXT 中" / "是原文换行符）。逐条<处理动作>，不得遗漏、不得合并。

<处理标准与规则，如分类标准、翻译要求、打分规则...>
拿不准最多1-2次网络搜索验证。

输出：用write工具写到 <results目录>\chunk_XXX.json，UTF-8 JSON数组按分片顺序：
[{"id":"仓库:R2","<结果字段1>":"...","<结果字段2>":"..."}, ...]
最终回复报告：共X条，<各类结果统计>，存疑条目（如有）。
```

要点：
- 每个 Task 用 `general` 子代理，prompt 中必须写明**输入分片路径**与**输出 JSON 路径**（各自独立，互不冲突）。
- 必须要求"按分片顺序输出 JSON 数组"、"逐条判定不得遗漏"，这是校验通过的前提。
- 每批完成后检查返回，若有失败/存疑，单独补跑该分片。
- 大批量时逐批推进，例如 204 片 → 每批 26 个 → 约 8 批，全部完成后进入校验。

## 第四步：校验（脚本）

```powershell
python <skill>/scripts/merge_results.py --chunks-dir chunks --results-dir results --check-only
```

必须全部通过：每个分片都有对应 JSON、可解析、ID 顺序与数量完全一致。
失败项（如缺结果、尾逗号导致的 JSON 解析错误、ID 缺漏）逐项修复后重跑，**未通过校验不得进入合并**。

## 第五步：合并输出

```powershell
# 按结果字段拆分到不同文件夹（如分类任务 public/internal）
python <skill>/scripts/merge_results.py --chunks-dir chunks --results-dir results `
  --split-key verdict --split-map "public=公开信息,internal=企业内部信息" `
  --output-dir out --out-fields row,text,verdict,reason

# 合并为单个文件（含源数据+结果字段）
python <skill>/scripts/merge_results.py --chunks-dir chunks --results-dir results `
  --mode single --out-fields row,text,verdict,reason --output-dir out
```

- 源数据字段（row/text）从 manifest 回填，**不依赖 Agent 转写**，确保内容完整无省略。
- 输出 xlsx 时行号列用源文件的原始行号列（注意：若源数据行号列本身不连续，不要用物理行号匹配，按顺序对应）。

## 第六步：交付核对

- 向用户报告统计（总量、各分类/结果数量、每个文件条数）。
- 抽样 3~5 条展示结果字段，确认符合预期。
- 提醒数据源本身的异常（如原始数据中就有未写完的占位内容），这不是处理流程引入的。

---

## 常见问题

- **JSON 解析失败**：多为尾逗号或 BOM，用 `utf-8-sig` 读取并剔除 `,\s*]` 后重跑校验。
- **行号错位**：源文件行号列若缺号（如 37 直接跳 39），绝不能用行号匹配回填，按**顺序对应**。
- **内容疑似被省略**：先查源文件；输出字段应直接来自源数据（manifest 回填），Agent 只产出新增结果字段。
- **Agent 中途失败**：只补跑对应分片，不需要重跑全部。
- **上百个 Agent**：分批并行即可，如 26 个/批 × 8 批 = 208 个 Agent；不要试图单条消息塞上百个 Task 调用。

## 相关文件

- `scripts/split_data.py`：提取+分片
- `scripts/merge_results.py`：校验+合并输出
