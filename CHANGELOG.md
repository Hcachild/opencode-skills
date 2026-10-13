# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.7.0] - 2026-10-13

### Added
- `doc-coauthoring` — 结构化文档共创工作流（Context Gathering → Refinement & Structure → Reader Testing），引导用户高效传递上下文、迭代内容并做读者验证
- `humanizer` — 去除 AI 写作痕迹的文本改写（not-X-but-Y 对仗、单句收尾、三段式排比、夸张措辞等 AI tells；基于 Wikipedia "Signs of AI writing"）
- `opencode-chat-viewer` — 查看/搜索/导出本机 OpenCode 历史对话（opencode.db 的 session/message/part 三表，只读；支持按日期列会话、按 ID/标题查看、关键词搜索、批量导出）
- `pretty-mermaid` — Mermaid 图渲染为带主题的 SVG/PNG 或 ASCII/Unicode 终端图（flowchart/sequence/state/class/ERD/XY chart，15 个内置主题；依赖 beautiful-mermaid + @resvg/resvg-js）
- `tapd-work-recording` — 把日报/纪要/对话记录转成 TAPD 任务卡并经 MCP 建卡、复核、补工时（容器落位、字段映射、HTML 描述格式、工时填报规范等实战要点）

### Changed
- Updated `microsoft-foundry` 1.2.26 → 1.2.28 — 部署文档补充私有 PyPI 索引导致 `azd deploy` 失败的排障指引（改用公共索引 re-lock 或导出 pinned requirements.txt）
- Updated `by56-wiki-faq-update` — 环境速查更新：by_production 为主用生产（by56_wiki 已部署运行）、by_code_base 仅保留旧代码目录；补充数据标注/审核表结构（qa_review_items / qa_review_batches）与导出方法
- Skill count from 148 to 153, regenerated README index
- `pretty-mermaid` 运行前需在其目录 `npm install`；不提交 `node_modules` / `package-lock.json`
- Kept credentials sanitized (placeholders only, never commit secrets)

## [1.6.1] - 2026-10-11

### Changed
- Updated `agent-swarm` — 中断恢复改为优先续跑原 Task Agent 会话：用原 `task_id` + 仅 "继续" 的极简 prompt，嵌套链逐级恢复；仅当会话不可恢复时才发重建 brief（SKILL.md / `references/protocol.md` / `references/prompts.md` §5 同步）
- Updated `agent-swarm` — 新增「与批量处理 skill 协同」：成千上万条同构数据直接套用 `parallel-data-processing` 的「切 N 片 → 每片一个 worker → 校验合并」模式（一个 manager 挂 N 个 worker），不必为每条单开子任务
- Skill count unchanged at 148

## [1.6.0] - 2026-10-11

### Added
- `agent-swarm` — 嵌套子代理长跑研究集群：sponsor → root curator → track-lead → manager → worker 树状结构，CHARTER/PROTOCOL/ROADMAP 治理、backlog/leaderboard/checkpoint 运行时、指纹与测试注册、预算门与 STOP 规则
- `codex-ppt` — 从文章/报告/论文/笔记/大纲生成视觉统一的图块式 PPT/PPTX（风格库、幻灯片子代理生成、质量门与组装流程）
- `deep-web-research` — 多轮深度联网搜索/找东西/查证（线索中断时向用户追问澄清；不适用于一次性简单查询）
- `fanqie-image-restore` — 番茄图片混淆/小番茄加密图还原（Gilbert 空间曲线、块混淆、逐像素/行像素混淆）
- `ppt-design-skill` — 基于 pptx-designer 库的可编辑 PPT 设计/生成/视觉审查/迭代（brief → PPTX → PDF → PNG 工作流）

### Changed
- Skill count from 143 to 148, regenerated README index
- `requirements.txt`: added `python-pptx` / `Pillow` / `filelock` (codex-ppt) and `pptx-designer` (ppt-design-skill)
- Kept credentials sanitized (placeholders only, never commit secrets); excluded `__pycache__`/`.pyc`; Claude Code `openai.yaml` kept in `misc/openai-yaml/`

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
