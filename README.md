# opencode-skills

Personal collection of 138 opencode agent skills.

## Quick Start

```bash
# Clone
git clone https://github.com/Hcachild/opencode-skills.git
cd opencode-skills

# Install (symlink to ~/.config/opencode/skills/)
./install.sh

# Or on Windows
.\install.ps1
```

Restart OpenCode — skills load automatically.

## Installation

### macOS / Linux

```bash
./install.sh                # symlink all skills globally
./install.sh --copy          # copy all skills globally
./install.sh --project       # install to .opencode/skills/ (project-local)
./install.sh --list          # list available skills
./install.sh tdd             # install a single skill
```

### Windows (PowerShell)

```powershell
.\install.ps1                # symlink all skills globally
.\install.ps1 -Copy          # copy all skills globally
.\install.ps1 -Project       # install to .opencode\skills\ (project-local)
.\install.ps1 -List          # list available skills
.\install.ps1 -Skill tdd     # install a single skill
```

### Makefile

```bash
make install         # symlink skills to ~/.config/opencode/skills/
make install-copy    # copy skills
make install-project # install to .opencode/skills/
make uninstall       # remove installed skills
make list            # list available skills
make validate        # validate SKILL.md frontmatter
make status          # show installation status
make deps            # install Python dependencies
```

### Python Dependencies

Some skills require Python packages:

```bash
pip install -r requirements.txt
```

### Node.js Dependencies

The `feishu-doc` skill requires Node.js packages. The installer will attempt `npm install` automatically. If that fails:

```bash
cd skills/feishu-doc-1.2.7
npm install --production
```

## Skills Requiring Configuration

After installation, fill in credentials for these skills:

| Skill | File | What to fill |
|-------|------|-------------|
| `autoglm-*` (6 skills) | `*.py` | `APP_ID` + `APP_KEY` |
| `feishu-doc-1.2.7` | `config.json` | `app_id` + `app_secret` |
| `aminer-open-academic` | `scripts/aminer_client.py` | API key |

## Repository Structure

```
opencode-skills/
├── skills/              # 138 skill directories
├── install.sh           # macOS/Linux installer
├── install.ps1          # Windows installer
├── Makefile             # Build/install/validate commands
├── requirements.txt     # Python dependencies
├── opencode.json        # OpenCode project config
├── AGENTS.md            # Project rules
├── LICENSE              # MIT
├── CONTRIBUTING.md      # Contribution guide
├── CHANGELOG.md         # Version history
├── version.json         # Version metadata
└── README.md            # This file
```

## Skill Index (138 skills)

| # | Skill | Description |
|---|-------|-------------|
| 1 | [1password](skills/1password-1.0.1) | Set up and use 1Password CLI (op). Use when installing the CLI, enabling desktop app integration, si... |
| 2 | [a-stock-analysis](skills/a-stock-analysis-1.0.0) | A股实时行情与分时量能分析。获取沪深股票实时价格、涨跌、成交量，分析分时量能分布（早盘/尾盘放量）、主力动向（抢筹/出货信号）、涨停封单。支持持仓管理和盈亏分析。Use when: (1) 查询A股实... |
| 3 | [self-reflection](skills/agent-self-reflection-1.0.0) | Periodic self-reflection on recent sessions. Analyzes what went well, what went wrong, and writes co... |
| 4 | [aigc-down-skill](skills/aigc-down-skill) | 降低中文学术写作（本/专科毕业论文）AIGC检测率的专项 skill。 基于真实论文改写实验（AIGC率从 >50% 降至 11%）归纳的规律，并参考 Wikipedia「Signs of AI wr... |
| 5 | [aigc-reduce-community](skills/aigc-reduce-community) | 基于网友/毕业季学生实战经验总结的中文论文降AIGC检测率补充 skill。 与 aigc-down-skill（AI写作模式分类驱动）互补，本 skill 侧重实战经验： 知网/维普/万方 AIGC... |
| 6 | [aminer-data-search](skills/aminer-open-academic-1.0.5) | 使用 AMiner 开放平台 API 进行学术数据查询与分析。当用户需要查询学者信息、论文详情、机构数据、期刊内容或专利信息时使用此 skill。 触发场景：提到 AMiner、学术数据查询、查论文/... |
| 7 | [architecture-designer](skills/architecture-designer-0.1.0) | Use when designing new system architecture, reviewing existing designs, or making architectural deci... |
| 8 | [ask-matt](skills/ask-matt) | Ask which skill or flow fits your situation. A router over the skills in this repo. |
| 9 | [audit-security](skills/audit-security) | Runs a deliberately small, hand-curated security sweep across a repo. Finds secrets committed to git... |
| 10 | [autoglm-browser-agent](skills/autoglm-browser-agent) | 智能浏览器自动化代理,可执行任何需要浏览器的任务。 包括但不限于:打开网页、搜索信息(百度/谷歌/必应)、浏览社交媒体(微博/小红书/知乎/抖音/B站)、 点赞/评论/转发/收藏、发帖/发消息、登录网... |
| 11 | [autoglm-deepresearch](skills/autoglm-deepresearch) | 对用户提出的课题进行深度研究和调研，输出结构化的深度报告。当用户需要深入了解某个话题、做行业调研、专题研究、竞品分析等场景时使用此 skill。 与普通搜索不同，deepresearch 会先做少量定... |
| 12 | [autoglm-generate-image](skills/autoglm-generate-image) | 使用 AutoGLM 文生图接口，根据用户输入的文字描述生成图片。当用户需要生成图片、文字转图片、AI绘图等场景时使用此 skill。 Token 通过本地服务 http://127.0.0.1:53... |
| 13 | [autoglm-open-link](skills/autoglm-open-link) | 使用 AutoGLM Open Link 接口打开指定网页并提取页面正文内容。当用户需要读取某个网页详情、提取文章全文、抓取页面正文做摘要或分析时使用此 skill。 Token 通过本地服务 htt... |
| 14 | [autoglm-search-image](skills/autoglm-search-image) | 使用 AutoGLM 搜图接口，根据用户输入的关键词搜索相关图片。当用户需要搜索图片、查找图片素材等场景时使用此 skill。 Token 通过本地服务 http://127.0.0.1:53699/... |
| 15 | [autoglm-websearch](skills/autoglm-websearch) | 使用 AutoGLM Web Search 接口进行网络信息搜索。当用户需要联网搜索、查询最新资讯、检索网页内容或获取实时信息时使用此 skill。 Token 通过本地服务 http://127.0... |
| 16 | [automation-workflows](skills/automation-workflows-0.1.0) | Design and implement automation workflows to save time and scale operations as a solopreneur. Use wh... |
| 17 | [backtest-expert](skills/backtest-expert-0.1.0) | Expert guidance for systematic backtesting of trading strategies. Use when developing, testing, stre... |
| 18 | [baiyun-context](skills/baiyun-context) | Use when 需要导出或排查运小星(BaiYun_Agent)用户的对话记录：找上下文、生成"找到上下文N_完整对话记录.xlsx"、按时间段全量导出对话（含模块/answer_state/联网搜... |
| 19 | [baiyun-release-workflow](skills/baiyun-release-workflow) | Execute and audit BaiYun_Agent release, remote commit, push, and PR workflows, including by_dev remo... |
| 20 | [batch-grill-me](skills/batch-grill-me) | A relentless interview that asks every frontier question at once, round by round. |
| 21 | [blog-writer](skills/blog-writer-0.1.0) | This skill should be used when writing blog posts, articles, or long-form content in the writer's di... |
| 22 | [brainstorming](skills/brainstorming-0.1.0) | You MUST use this before any creative work - creating features, building components, adding function... |
| 23 | [bugfix-workflow](skills/bugfix-workflow) | Bug修复通用工作流。当生产环境发现Bug需要紧急修复时使用，覆盖所有类型：功能异常、输出错误、性能问题、安全漏洞、用户体验问题等。触发关键词：Bug修复、hotfix、生产事故、fix、根因分析、影... |
| 24 | [by56-wiki-embedding-reindex](skills/by56-wiki-embedding-reindex) | 更新 by56_wiki（BaiYun 运小星知识库）PostgreSQL/pgvector 向量库与检索索引。用于 Embedding 模型调整（换模型/换维度/服务端模型变更）后的全量向量重算、B... |
| 25 | [by56-wiki-faq-update](skills/by56-wiki-faq-update) | 更新 by56_wiki 知识库（BaiYun 运小星知识库）中的 FAQ/文档行级数据，如仓库地址、电话、收费标准等业务信息变更。通过 SSH 在 by_dev（测试）或 by_code_base（... |
| 26 | [claude-handoff](skills/claude-handoff) | Hand the current conversation off to a fresh background agent that picks up the work immediately. |
| 27 | [clawdefender](skills/clawdefender-1) | Security scanner and input sanitizer for AI agents. Detects prompt injection, command injection, SSR... |
| 28 | [Code](skills/code-1.0.4) | Coding workflow with planning, implementation, verification, and testing for clean software developm... |
| 29 | [code-review](skills/code-review) | Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes — Standar... |
| 30 | [code-review-score](skills/code-review-score) | Two-axis code review (Standards + Spec) with numeric scoring and a merge recommendation. Use when th... |
| 31 | [codebase-conventions](skills/codebase-conventions) | Generally-applicable conventions for how code is written and arranged — tooling/package manager, imp... |
| 32 | [codebase-design](skills/codebase-design) | Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module'... |
| 33 | [codex-fix](skills/codex-fix) | Post-edit loop that invokes `/codex:rescue` for a second-model review of the current branch, collect... |
| 34 | [content-strategy](skills/content-strategy-0.1.0) | Build and execute a content marketing strategy for a solopreneur business. Use when planning what co... |
| 35 | [copywriting](skills/copywriting-0.1.0) | Write persuasive copy for landing pages, emails, ads, sales pages, and marketing materials. Use when... |
| 36 | [cursor-chat-viewer](skills/cursor-chat-viewer) | 查看本机 Cursor 的历史对话记录（Agent/Composer 会话）。从 Cursor 的本地 SQLite 数据库（state.vscdb）直接读取，支持按 Agent ID 查看完整对话、... |
| 37 | [debug-pro](skills/debug-pro-1.0.0) | Systematic debugging methodology and language-specific debugging commands. Use when debugging, diagn... |
| 38 | [design-an-interface](skills/design-an-interface) | Generate multiple radically different interface designs for a module using parallel sub-agents. Use ... |
| 39 | [diagnosing-bugs](skills/diagnosing-bugs) | Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"debug t... |
| 40 | [documentation-and-adrs](skills/documentation-and-adrs) | 记录技术决策及其背景、约束、备选方案和取舍，并维护架构决策记录、公共 API 文档、README、变更日志与面向开发代理的项目规则。适用于作出重要架构决策、比较竞争方案、新增或修改公共接口、发布影响用... |
| 41 | [domain-modeling](skills/domain-modeling) | Build and sharpen a project's domain model. Use when the user wants to pin down domain terminology o... |
| 42 | [edit-article](skills/edit-article) | Edit and improve articles by restructuring sections, improving clarity, and tightening prose. Use wh... |
| 43 | [executing-plans](skills/executing-plans-0.1.0) | Use when you have a written implementation plan to execute in a separate session with review checkpo... |
| 44 | [feishu-chat-history](skills/feishu-chat-history) | Fetch and summarize Feishu group chat history. Use when the user asks to read, review, or summarize ... |
| 45 | [feishu-common](skills/feishu-common) | Shared Feishu (Lark) auth library for feishu-* skills. Provides tenant_access_token caching and auth... |
| 46 | [feishu-cron-reminder](skills/feishu-cron-reminder) | Create cron jobs that reliably deliver reminders to Feishu (飞书) chats. Use when the user asks to set... |
| 47 | [feishu-doc](skills/feishu-doc-1.2.7) | Fetch content from Feishu (Lark) Wiki, Docs, Sheets, and Bitable. Automatically resolves Wiki URLs t... |
| 48 | [feishu-drive](skills/feishu-drive-1.0.0) | 飞书云空间文件管理 Skill。上传/下载/移动/搜索文件、创建文件夹、获取元数据等。当需要管理飞书云空间中的文件和文件夹时使用此 Skill。 |
| 49 | [feishu-perm](skills/feishu-perm) | Feishu permission management for documents and files. Activate when user mentions sharing, permissio... |
| 50 | [feishu-screenshot](skills/feishu-screenshot) | Capture macOS screenshots and send to Feishu. Use when the user asks to take a screenshot and share ... |
| 51 | [feishu-send-file](skills/feishu-send-file) | Send files to a Feishu group or user via REST API. Use when the user explicitly asks to send a file,... |
| 52 | [FFmpeg Video Editor](skills/ffmpeg-video-editor-1.0.0) | Generate FFmpeg commands from natural language video editing requests - cut, trim, convert, compress... |
| 53 | [fight-repo-rot](skills/fight-repo-rot) | Finds what's rotting in a repo and returns a prioritized diagnosis — dead code first, then god files... |
| 54 | [find-skills](skills/find-skills) | Helps users discover and install agent skills when they ask questions like "how do I do X", "find a ... |
| 55 | [foxcode-image-gen](skills/foxcode-image-gen) | Generate high-quality images via the FoxCode gpt-image-2 API. Use when the user asks to generate, cr... |
| 56 | [frontend-design](skills/frontend-design-3-0.1.0) | Create distinctive, production-grade frontend interfaces with high design quality. Use this skill wh... |
| 57 | [git-essentials](skills/git-essentials-1.0.0) | Essential Git commands and workflows for version control, branching, and collaboration. |
| 58 | [git-guardrails-claude-code](skills/git-guardrails-claude-code) | Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.... |
| 59 | [grill-me](skills/grill-me) | A relentless interview to sharpen a plan or design. |
| 60 | [grill-with-docs](skills/grill-with-docs) | A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as ... |
| 61 | [grilling](skills/grilling) | Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test ... |
| 62 | [handoff](skills/handoff) | Compact the current conversation into a handoff document for another agent to pick up. |
| 63 | [implement](skills/implement) | Implement a piece of work based on a spec or set of tickets. |
| 64 | [improve-codebase-architecture](skills/improve-codebase-architecture) | Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill throug... |
| 65 | [interview-designer](skills/interview-designer-1.0.0) | Analyze resumes and design interview strategies using evidence-based methodology. Transforms intervi... |
| 66 | [loop-me](skills/loop-me) | Grill me about specs for the workflows I want to build, within this workspace. |
| 67 | [manage-assets](skills/manage-assets) | Finds oversized files, binary bloat, and accidental artifact commits in a repo — large files current... |
| 68 | [manage-secrets-env](skills/manage-secrets-env) | Opinionated defaults and full lifecycle playbook for secrets and environment variables. Decides wher... |
| 69 | [Market Research](skills/market-research-1.0.0) | Size markets, analyze competitors, and validate opportunities with practical frameworks and free dat... |
| 70 | [Memory](skills/memory-1.0.2) | Infinite organized memory that complements your agent's built-in memory with unlimited categorized s... |
| 71 | [microsoft-foundry](skills/microsoft-foundry) | Build, deploy, evaluate, optimize, fine-tune, and manage Microsoft Foundry agents, models, and resou... |
| 72 | [migrate-to-shoehorn](skills/migrate-to-shoehorn) | Migrate test files from `as` type assertions to @total-typescript/shoehorn. Use when user mentions s... |
| 73 | [obsidian-ontology-sync](skills/obsidian-ontology-sync-1.0.1) | Bidirectional sync between Obsidian PKM (human-friendly notes) and structured ontology (machine-quer... |
| 74 | [obsidian-vault](skills/obsidian-vault) | Search, create, and manage notes in the Obsidian vault with wikilinks and index notes. Use when user... |
| 75 | [opencode-controller](skills/opencode-controller-1.0.0) | Control and operate Opencode via slash commands. Use this skill to manage sessions, select models, s... |
| 76 | [parallel-data-processing](skills/parallel-data-processing) | 精细化批量数据处理通用工作流。当需要对大量结构化数据逐条进行精细处理（分类、审核、翻译、改写、信息提取、打标、清洗、校验等）时使用，例如"把这些FAQ逐条分类"、"给这1万条记录逐条打标签"、"逐条翻... |
| 77 | [perf-goal-fill](skills/perf-goal-fill) | Fill ??????????/???and??????in a human, goal-not-result style. Use when filling ?????, ??/??, ????, ... |
| 78 | [ponytail](skills/ponytail) | Forces the laziest solution that actually works, simplest, shortest, most minimal. Channels a senior... |
| 79 | [ponytail-audit](skills/ponytail-audit) | Whole-repo audit for over-engineering. Like ponytail-review, but scans the entire codebase instead o... |
| 80 | [ponytail-debt](skills/ponytail-debt) | Harvest every `ponytail:` comment in the codebase into a debt ledger, so the deliberate shortcuts an... |
| 81 | [ponytail-gain](skills/ponytail-gain) | Show ponytail's measured impact as a compact scoreboard: less code, less cost, more speed, from the ... |
| 82 | [ponytail-help](skills/ponytail-help) | Quick-reference card for all ponytail modes, skills, and commands. One-shot display, not a persisten... |
| 83 | [ponytail-review](skills/ponytail-review) | Code review focused exclusively on over-engineering. Finds what to delete: reinvented standard libra... |
| 84 | [project-conventions](skills/project-conventions) | Opinionated defaults for the lower-stakes structural conventions every project has to pick — branch ... |
| 85 | [prototype](skills/prototype) | Build a throwaway prototype to answer a design question. Use when the user wants to sanity-check whe... |
| 86 | [qa](skills/qa) | Interactive QA session where user reports bugs or issues conversationally, and the agent files GitHu... |
| 87 | [refactor-verify](skills/refactor-verify) | Proves a behavior-preserving code change (refactor, rename, split, merge, extract, inline, or delete... |
| 88 | [request-refactor-plan](skills/request-refactor-plan) | Create a detailed refactor plan with tiny commits via user interview, then file it as a GitHub issue... |
| 89 | [research](skills/research) | Investigate a question against high-trust primary sources and capture the findings as a Markdown fil... |
| 90 | [research-paper-writer](skills/research-paper-writer-0.1.0) | Creates formal academic research papers following IEEE/ACM formatting standards with proper structur... |
| 91 | [resolving-merge-conflicts](skills/resolving-merge-conflicts) | Use when you need to resolve an in-progress git merge/rebase conflict. |
| 92 | [scaffold-exercises](skills/scaffold-exercises) | Create exercise directory structures with sections, problems, solutions, and explainers that pass li... |
| 93 | [security-auditor](skills/security-auditor-1.0.0) | Use when reviewing code for security vulnerabilities, implementing authentication flows, auditing OW... |
| 94 | [Self-Improving Agent (With Self-Reflection)](skills/self-improving-1.1.3) | Self-reflection + Self-criticism + learning from corrections. Agent evaluates its own work, catches ... |
| 95 | [sentry-create-alert](skills/sentry-create-alert) | Create Sentry alerts using the workflow engine API. Use when asked to create alerts, set up notifica... |
| 96 | [sentry-debug-issue](skills/sentry-debug-issue) | Debug and fix a Sentry issue — find it (by link, ID, or search), pull full context (stack trace, bre... |
| 97 | [sentry-fix-stack-traces](skills/sentry-fix-stack-traces) | Make Sentry stack traces readable — upload source maps for JavaScript/TypeScript, or debug files for... |
| 98 | [sentry-get-started](skills/sentry-get-started) | Guided entry point for using Sentry through your agent. Orients you to your current setup and, for a... |
| 99 | [sentry-instrument](skills/sentry-instrument) | Instrument an application with Sentry — detect the platform, install and initialize the SDK if neede... |
| 100 | [sentry-otel-exporter-setup](skills/sentry-otel-exporter-setup) | Configure the OpenTelemetry Collector with Sentry Exporter for multi-project routing and automatic p... |
| 101 | [sentry-setup-releases](skills/sentry-setup-releases) | Set up Sentry releases and deploy tracking — tag events with a version and environment, create the r... |
| 102 | [sentry-snapshots-cocoa](skills/sentry-snapshots-cocoa) | Full Sentry Snapshots setup for Apple/Cocoa projects. Use when asked to "setup SnapshotPreviews", "s... |
| 103 | [SEO (Site Audit + Content Writer + Competitor Analysis)](skills/seo-1.0.3) | SEO specialist agent with site audits, content writing, keyword research, technical fixes, link buil... |
| 104 | [seo-content-writer](skills/seo-content-writer-2.0.0) | Use when the user asks to "write SEO content", "create a blog post", "write an article", "content wr... |
| 105 | [session-logs](skills/session-logs-1.0.0) | Search and analyze your own session logs (older/parent conversations) using jq. |
| 106 | [setup-ci](skills/setup-ci) | Teaches CI/CD from first principles to a non-developer, then scaffolds a working test + deploy pipel... |
| 107 | [setup-matt-pocock-skills](skills/setup-matt-pocock-skills) | Configure this repo for the engineering skills — set up its issue tracker, triage label vocabulary, ... |
| 108 | [setup-pre-commit](skills/setup-pre-commit) | Set up Husky pre-commit hooks with lint-staged (Prettier), type checking, and tests in the current r... |
| 109 | [setup-ts-deep-modules](skills/setup-ts-deep-modules) | Wire dependency-cruiser into a TypeScript repo so each package is a deep module — implementation hid... |
| 110 | [ship-cycle](skills/ship-cycle) | Issue-driven development orchestrator. Turns improvement intent into a well-specified, bilingual iss... |
| 111 | [skill-creator](skills/skill-creator-0.1.0) | Guide for creating effective skills. This skill should be used when users want to create a new skill... |
| 112 | [skill-doctor](skills/skill-doctor) | 在用 skill 的复利迭代器——任务收尾时把本次真实使用经验复盘成补丁，安全落盘并记入账本，让同一个 skill 在新场景下越用越准（观察→提炼→判定→落盘→记账）。触发词：skill 复盘、迭代 ... |
| 113 | [skill-vetter](skills/skill-vetter-1.0.0) | Security-first skill vetting for AI agents. Use before installing any skill from ClawdHub, GitHub, o... |
| 114 | [social-content](skills/social-content-generator-0.1.0) | When the user wants help creating, scheduling, or optimizing social media content for LinkedIn, Twit... |
| 115 | [Social Media Scheduler](skills/social-media-scheduler-1.0.0) | Plan, draft, and organize social media content across platforms. Create content calendars, write pla... |
| 116 | [supabase-postgres-best-practices](skills/supabase-postgres-best-practices) | Postgres performance optimization and best practices from Supabase. Use this skill when writing, rev... |
| 117 | [tdd](skills/tdd) | Test-driven development. Use when the user wants to build features or fix bugs test-first, mentions ... |
| 118 | [teach](skills/teach) | Teach the user a new skill or concept, within this workspace. |
| 119 | [test-runner](skills/test-runner-1.0.0) | Write and run tests across languages and frameworks. Use when writing, running, or fixing tests. |
| 120 | [tmux](skills/tmux-1.0.0) | Remote-control tmux sessions for interactive CLIs by sending keystrokes and scraping pane output. |
| 121 | [to-questionnaire](skills/to-questionnaire) | Turn a decision you can't fully answer into a questionnaire for someone else to fill in. |
| 122 | [to-spec](skills/to-spec) | Turn the current conversation into a spec and publish it to the project issue tracker — no interview... |
| 123 | [to-tickets](skills/to-tickets) | Break a plan, spec, or the current conversation into a set of tracer-bullet tickets, each declaring ... |
| 124 | [triage](skills/triage) | Move issues and external PRs through a state machine of triage roles — categorise, verify, grill if ... |
| 125 | [ubiquitous-language](skills/ubiquitous-language) | Extract a DDD-style ubiquitous language glossary from the current conversation, flagging ambiguities... |
| 126 | [ui-ux-pro-max](skills/ui-ux-pro-max-0.1.0) | UI/UX design intelligence and implementation guidance for building polished interfaces. Use when the... |
| 127 | [unify-design](skills/unify-design) | Establishes a web project's design system as the single source of truth — colors, spacing, typograph... |
| 128 | [vibesubin](skills/vibesubin) | The vibesubin command and vibe. Runs every code-hygiene specialist in the plugin across a repository... |
| 129 | [video-frames](skills/video-frames-1.0.0) | Extract frames or short clips from videos using ffmpeg. |
| 130 | [wayfinder](skills/wayfinder) | Plan a huge chunk of work — more than one agent session can hold — as a shared map of decision ticke... |
| 131 | [wecom-chat-extractor](skills/wecom-chat-extractor) | Extract and query local chat data on Windows for BOTH WeCom (企业微信/WeChat Work) and personal WeChat 4... |
| 132 | [wizard](skills/wizard) | Generate an interactive bash wizard that walks a human through a manual procedure — third-party setu... |
| 133 | [write-for-ai](skills/write-for-ai) | Writes documentation, commit messages, and PR descriptions optimized for the NEXT AI session to unde... |
| 134 | [writing-beats](skills/writing-beats) | Writing, exploit — assemble raw material into a journey of beats, grounding each term before a beat ... |
| 135 | [writing-fragments](skills/writing-fragments) | Writing, explore — mine raw fragments, no structure yet. |
| 136 | [writing-great-skills](skills/writing-great-skills) | Reference for writing and editing skills well — the vocabulary and principles that make a skill pred... |
| 137 | [writing-plans](skills/writing-plans-0.1.0) | Use when you have a spec or requirements for a multi-step task, before touching code |
| 138 | [writing-shape](skills/writing-shape) | Writing, exploit — shape raw material into an article, paragraph by paragraph. |

