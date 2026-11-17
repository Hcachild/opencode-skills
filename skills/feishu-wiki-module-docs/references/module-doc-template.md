# Module Doc Template

Use this skeleton for one module per child doc. Replace `<...>` with facts; delete sections that do not apply. Keep the doc technical and evidence-based, not a sales summary.

## Structure

```markdown
## 修改记录
| 日期 | 内容 | 维护人 | 状态 |
| 2026-11-05 | 初版：按 PR #<n> / #<n> 归档 <module> | <name> | 当前稿 |

关联代码：PR #<n>（<commit>）... 关联文档：<plans/reviews/runbooks> ... 代码位置：<paths>。
状态说明：已合并=代码在 dev；测试环境=...；生产=未放行；已归档=旧探索。

## 当前状态
- 机制 1 ...
- 机制 2 ...
- 测试/验收 ...
- 生产门禁 ...
- 边界 ...

## 阅读提示
- 术语 A = ...
- 术语 B = ...
- “测试环境可用” ≠ “生产可用”。

## 一、总体架构 / 数据流
<一段话>
<Mermaid>

## 二、演进 / 决策
<一段话>
<Mermaid 或表格：PR / 范围 / 结果>

## 三、核心机制
### 3.1 ...
### 3.2 ...
### 3.3 ...
<表格 + bullets>

## 四、验证与证据
| 范围 | 证据 | 结果 |
...
<截图 1–4>

## 五、边界与后置项
- 已收口 ...
- 仍是测试环境 ...
- 未做 ...
- 结论 ...

## 结论
<把“代码/测试环境完成”与“生产未放行”分开>
```

## Style rules

- Start with the facts: PR numbers, commits, dates, digests, environment names.
- Use “已合并 / 已关闭 / 测试环境 / NO-GO / OPEN / CLOSED” precisely. A closed PR is not merged.
- Every mechanism section answers: what it does, where the code is, what fails, what is out of scope.
- Every test section states the evidence source (test file, E2E doc, runbook, execution id, digest).
- Prefer tables for matrices and boundaries; bullets for invariants and caveats.
- Use 3–5 Mermaid diagrams: architecture, lifecycle/flow, sequence, failure/decision. Do not use a code block for Mermaid.
- Use 3–6 screenshots: PR page, runbook/E2E page, console/UI page. Caption them with “图 N：...”.
- Keep raw test numbers scoped: “only that measurement, not a production SLO”.
- Never put secrets, tokens, DSNs, private keys, or PII in the doc.
- End with a boundary/conclusion that a reader can act on; no generic “future work”.

## Parent sync (optional, when asked)

1. Insert a short section before the anchor heading:
   - heading2: `<date range> <module>`
   - one-sentence conclusion
   - 3-column table `PR | 内容 | 结果`
   - 3–4 bullets
   - child doc link
2. Append a 修改记录 row.
3. Add Gantt completed + pending records.
4. Set the Gantt view sort and verify.

See `references/gantt-bitable.md`.

## Pre-publish checklist

- [ ] 修改记录 table has the new row.
- [ ] Mermaid validation: 0 failures.
- [ ] No literal `**` / backticks in text.
- [ ] Table rows/columns and cell text are correct.
- [ ] Every image block has a token.
- [ ] Parent summary / 修改记录 / Gantt statuses agree.
- [ ] Mermaid/截图 captions separate synthetic fixtures from product-path evidence.
