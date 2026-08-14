---
name: code-review-score
description: >-
  Two-axis code review (Standards + Spec) with numeric scoring and a merge
  recommendation. Use when the user asks to review a PR/branch, score code
  changes, decide whether to merge, or compare a diff against a tech proposal /
  PRD / issue. Triggers: code review, PR review, 打分, 审查, 能否合并, review score.
---

# Code Review Score

Review a PR or branch along **Standards** and **Spec**, then **score** and recommend merge. Do not rewrite the change unless the user asks.

## Inputs

Collect before reviewing (ask only what is missing):

| Input | Default |
|---|---|
| Fixed point / base | PR base branch, else `origin/dev` or `origin/main` |
| Head | PR head / current branch / `HEAD` |
| Spec | User path, PR body, `docs/`/`specs/`/`workstreams/`, or issue refs |
| Scope note | If PR is a slice of a larger PRD, judge only in-scope items |

## Process

### 1. Pin the diff

```bash
git rev-parse <fixed-point>
git log <fixed-point>..HEAD --oneline
git diff --stat <fixed-point>...HEAD
git diff <fixed-point>...HEAD
```

For GitHub PRs also fetch metadata:

```bash
gh pr view <n> --json title,body,baseRefName,headRefName,files,additions,deletions,mergeable,statusCheckRollup,commits,url
```

Fail early if the ref is bad or the three-dot diff is empty.

### 2. Find Spec and Standards

**Spec** (first hit wins):

1. Path the user gave (tech proposal / PRD / workstream)
2. Issue refs in commits (`#123`, `Closes #45`)
3. Matching docs under `docs/`, `specs/`, `.scratch/`, `docs/workstreams/`
4. If none: ask; if user says none, Spec axis reports `no spec available`

**Standards**:

- Repo docs: `CODING_STANDARDS.md`, `CONTRIBUTING.md`, `CONTEXT.md` style rules
- Always apply the smell baseline in [references/scoring-rubric.md](references/scoring-rubric.md)
- Repo-documented rules override the baseline; smells are judgement calls
- Skip anything tooling already enforces (formatter/linter/CI)

### 3. Parallel axes

Run Standards and Spec reviews in parallel (sub-agents when available). Keep axes separate — do not merge findings into one ranked list until the Score section.

**Standards brief** (under 400 words):  
(a) documented-standard violations with file + rule;  
(b) baseline smells with name + hunk quote;  
mark hard vs judgement.

**Spec brief** (under 400 words):  
(a) missing/partial requirements;  
(b) scope creep;  
(c) implemented-but-wrong;  
quote the spec line;  
label **out-of-scope** gaps when the PR is a slice of a larger PRD (not bugs).

### 4. Verify

Run the smallest relevant checks when practical:

- Targeted unit tests for touched modules
- `gh pr checks` / CI status if a PR exists
- Note skips (env/DB) separately from failures

### 5. Score and recommend

Use the rubric in [references/scoring-rubric.md](references/scoring-rubric.md).

Dimensions (0–100 each), then weighted overall:

| Dimension | Weight |
|---|---|
| Spec fit (in-scope) | 30% |
| Correctness | 25% |
| Code quality / Standards | 20% |
| Tests / verification | 15% |
| Docs / maintainability | 10% |

Merge call (pick one):

- **Approve** — ship
- **Approve with nits** — optional follow-ups
- **Request changes** — fix listed medium/high before merge
- **Merge now + follow-up** — only if user needs urgency and risk is display/docs-only, not core path

## Output format

```markdown
## 结论
**总分 XX/100。建议：<Approve | Approve with nits | Request changes | Merge now + follow-up>。**
一句话理由。

## Spec
- 做得好的：…
- 应对齐的问题（表：严重度 | 问题 | 对照规格）
- 范围外（不算本 PR 缺项）：…

## Standards
- 硬违规：…（或无）
- 判断性味道：…

## 分项打分
| 维度 | 分 | 说明 |
|---|---|---|
| 需求契合 | |
| 实现正确性 | |
| 代码质量 | |
| 测试 | |
| 文档/可维护 | |
| **综合** | **N** | |

## 能否合并
| 选项 | 建议 |
|---|---|
| 现在直接合 | … |
| 修完再合 | 必改清单 |
| 先合再 follow-up | 前提条件 |

## 验证
- 跑过的命令与结果
- CI 状态
```

Keep the response pointed: lead with score + merge call; details after. Prefer tables for findings.

## Rules

- Read real diffs/tests; do not review from PR description alone
- Separate **in-scope** vs **out-of-scope** against the larger PRD
- Do not treat diagnostics/UI-only PRs as missing whole runtime systems unless the PR claims them
- Do not auto-commit, push, or approve the GitHub PR unless the user asks
- Never paste secrets from configs into the review
