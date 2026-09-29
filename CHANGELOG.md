# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.0] - 2026-09-29

### Added
- `resume-tailor` — 按 JD 定制简历（严格防编造 + 去 AI 腔写作规范），支持 `.resume/` 数据目录、work-history profile 持久化与匹配度分析（改编自 Proficiently 开源技能，MIT）
- `resume-builder` — Harvard 标准 + ATS 友好的简历创建/改写/格式化/翻译，含 .docx + 文本型 PDF 交付流程（python-docx → docx2pdf → pypdf 校验）（改编自 dabydat/resume-builder-skill，MIT）
- `interview-prep-generator` — STAR 故事库、高频面试题预测、自我介绍脚本、反问清单与困难问题应对（源自 Paramchoudhary/ResumeSkills，MIT）
- `salary-negotiation-prep` — 市场薪资调研、总包计算、counter-offer 邮件/电话话术、竞争 offer 对比（源自 Paramchoudhary/ResumeSkills，MIT）

### Changed
- Skill count from 139 to 143, regenerated README index
- `requirements.txt`: added `python-docx` / `docx2pdf` / `pypdf` for resume-builder document generation
- Kept credentials sanitized (placeholders only, never commit secrets)

## [1.4.0] - 2026-09-29

### Added
- `feishu-wiki-export` — 递归导出飞书（Lark）知识库/Wiki 为本地 Markdown 完整备份（blocks→md、图片/附件、表格、Mermaid、旧版 doc / sheet 节点），将个人飞书知识库全量导出流程沉淀为技能

### Changed
- Updated `microsoft-foundry` to upstream v1.2.22 → v1.2.26: 本地运行适配 `pyproject.toml` / `uv.lock`（venv 就近服务目录解析、私有索引 re-lock 指引、运行进程退出即停止轮询）；preset 部署成本估算改用独立 `azure-cost` 插件；校验规则 1.2.0 → 1.3.0（新增 AUTH-001 / IMG-001 / NET-001 等）
- Skill count from 138 to 139, regenerated README index
- Kept credentials sanitized (placeholders only, never commit secrets); ignored feishu-common runtime token cache under `skills/memory/`

## [1.3.0] - 2026-09-21

### Added
- `audit-security`, `fight-repo-rot`, `manage-assets`, `manage-secrets-env`, `project-conventions`, `refactor-verify`, `setup-ci`, `ship-cycle`, `unify-design`, `vibesubin`, `write-for-ai` — code-hygiene / engineering specialist suite
- `codex-fix`, `codebase-conventions`, `skill-doctor`, `perf-goal-fill` — review-fix loop, code conventions, skill iteration ledger, performance goal writing

### Changed
- Updated 9 skills to match local OpenCode state: `a-stock-analysis-1.0.0`, `bugfix-workflow`, `by56-wiki-embedding-reindex`, `by56-wiki-faq-update`, `cursor-chat-viewer`, `debug-pro-1.0.0`, `feishu-drive-1.0.0`, `test-runner-1.0.0`, `microsoft-foundry` (2026-09 upstream refresh)
- Skill count from 123 to 138, regenerated README index
- Kept credentials sanitized (placeholders only): kept repo versions for `autoglm-*`, `foxcode-image-gen` and `feishu-doc-1.2.7/config.json`; excluded `autoglm-browser-agent/dist` binaries

## [1.2.0] - 2026-08-26

### Added
- `aigc-down-skill`, `aigc-reduce-community` — 中文论文降 AIGC 检测率（模式分类驱动 + 实战经验）
- `by56-wiki-embedding-reindex`, `by56-wiki-faq-update` — BaiYun 运小星知识库向量重建与 FAQ 更新
- `cursor-chat-viewer` — 查看/搜索/导出本机 Cursor 历史对话
- `ponytail`, `ponytail-audit`, `ponytail-debt`, `ponytail-gain`, `ponytail-help`, `ponytail-review` — minimal/lazy coding mode suite

### Changed
- Updated 50+ existing skills to match local OpenCode installations (`autoglm-*`, `feishu-*`, `wecom-chat-extractor` WeChat 4.x support, `baiyun-*`, sentry suite, matt-pocock engineering skills, etc.)
- Skill count from 112 to 123, regenerated README index
- Kept credentials sanitized (placeholders only, never commit secrets)

## [1.1.0] - 2026-08-14

### Added
- `baiyun-context`, `baiyun-release-workflow` — BaiYun_Agent context export and release workflows
- `bugfix-workflow` — production bug hotfix workflow
- `code-review-score` — two-axis code review with numeric scoring
- `documentation-and-adrs` — technical decision records and docs
- `feishu-common` — shared Feishu auth library (dependency of `feishu-doc`)
- `foxcode-image-gen` — gpt-image-2 image generation
- `parallel-data-processing` — split/merge parallel data processing
- `sentry-create-alert`, `sentry-debug-issue`, `sentry-fix-stack-traces`, `sentry-get-started`, `sentry-instrument`, `sentry-otel-exporter-setup`, `sentry-setup-releases`, `sentry-snapshots-cocoa` — Sentry skills

### Changed
- Updated `autoglm-*` skills (deepresearch/generate-image/open-link/search-image/websearch)
- Updated `feishu-doc-1.2.7` scripts (`inspect_meta.js`, `setup_iter11.js`, `package.json`)
- Updated skill count from 110 to 112, regenerated README index
- Kept credentials sanitized (placeholders only, never commit secrets)

### Removed
- Legacy superpowers skills no longer used locally: `brainstorming`, `dispatching-parallel-agents`, `executing-plans`, `finishing-a-development-branch`, `receiving-code-review`, `requesting-code-review`, `subagent-driven-development`, `systematic-debugging`, `test-driven-development`, `using-git-worktrees`, `using-superpowers`, `verification-before-completion`, `writing-plans`, `writing-skills`

## [1.0.0] - 2026-07-27

### Added
- Initial release with 110 skills
- `install.sh` for macOS/Linux installation
- `install.ps1` for Windows installation
- `Makefile` with install/uninstall/validate/list/status targets
- `requirements.txt` for Python dependencies
- `AGENTS.md` project configuration
- `opencode.json` OpenCode project config
- `.gitignore` for cache and build artifacts
- `LICENSE` (MIT)
- `CONTRIBUTING.md` contribution guide

### Changed
- Restructured from 3 separate directories to unified `skills/` directory
- Removed platform-specific binaries (`.exe` files)
- Removed Claude Code `openai.yaml` agent configs
- Cleaned sensitive data (API keys, tokens) from all files
- Fixed missing YAML frontmatter in `debug-pro` and `test-runner` skills

### Removed
- `custom-skills/`, `agents-skills/`, `superpowers/` directory structure
- `agents/openai.yaml` files (Claude Code format, not used by OpenCode)
- `autoglm-browser-agent/dist/*.exe` (platform-specific binaries)
- `feishu-doc-1.2.7/cache/` (cached API responses with tokens)
- `__pycache__/` and `.pyc` files
