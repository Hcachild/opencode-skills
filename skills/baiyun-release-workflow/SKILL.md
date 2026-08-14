---
name: baiyun-release-workflow
description: Execute and audit BaiYun_Agent release, remote commit, push, and PR workflows, including by_dev remote repository work, dev/main branch checks, GitHub authentication preflight, cached-ref PR description fallback, and verification gates. Use when the user asks to commit, push, submit PR, merge dev to main, prepare PR text, work on by_dev, or handle auth-blocked GitHub operations for BaiYun repositories.
---

# BaiYun Release Workflow

Use this skill when the user expects real git or release-adjacent execution, not only a plan.

## Preflight

1. Identify the target location.
   - If the user names `by_dev`, `by_production`, or a server path, do not assume the local checkout is the target.
   - Confirm host, repository path, current branch, worktree status, and remote URL.
2. Inspect local state before changing anything:
   - `git status --short --branch`
   - `git branch --show-current`
   - `git remote -v`
   - relevant `git diff --stat` / `git diff --name-only`
3. Respect dirty worktrees. Do not revert unrelated changes.
4. If creating a PR, verify authentication early:
   - `gh auth status`
   - `git fetch origin main dev --prune` when network/auth should work
   - SSH probe only if remote or user flow expects SSH.

## Remote `by_dev` Commit And Push

1. Confirm SSH host config and remote repo path.
2. On the remote host, confirm branch and upstream before staging.
3. Run the relevant verification gate before commit.
   - Prefer focused tests for touched files.
   - Common BaiYun narrow gate: targeted `pytest`, `python -m py_compile`, `ruff --select F821,F822,F823` for touched modules, and `git diff --check`.
4. Stage only intended files.
5. Commit with a specific message.
6. Push to the intended branch.
7. Re-check status and local/remote SHA alignment.

## PR Workflow

1. If the user asks for `dev -> main` PR, the default target is to create a PR and wait for user review, not merge.
2. If auth works, create the PR with the requested title/body and report the URL.
3. If auth fails, do not pretend it succeeded.
4. If cached refs exist, produce a ready-to-paste PR title/body from:
   - `git log --oneline --decorate origin/main..origin/dev`
   - `git diff --stat origin/main..origin/dev`
   - `git diff --name-only origin/main..origin/dev`
5. Explicitly mark cached-ref output as based on local refs, not freshly fetched remote truth.

## Output

Return:

- Target repo, branch, and remote verified.
- Verification commands and pass/fail status.
- Files staged/committed/pushed or why no write was done.
- Commit SHA, push result, or PR URL when created.
- Auth blocker details and fallback artifact when blocked.

When using app-supported git actions, emit the required Codex git directives only after the action succeeds.
