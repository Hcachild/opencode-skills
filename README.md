# opencode-skills

Personal collection of 112 opencode agent skills.

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
├── skills/              # 112 skill directories
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

## Skill Index (112 skills)

| # | Skill | Description |
|---|-------|-------------|
| 1 | [1password](skills/1password-1.0.1) | Set up and use 1Password CLI (op). Use when installing the CLI, enabling desktop app integratio... |
| 2 | [a-stock-analysis](skills/a-stock-analysis-1.0.0) | A股实时行情与分时量能分析。获取沪深股票实时价格、涨跌、成交量，分析分时量能分布（早盘/尾盘放量）、主力动向（抢筹/出货信号）、涨停封单。支持持仓管理和盈亏分析。Use when: (1) ... |
| 3 | [self-reflection](skills/agent-self-reflection-1.0.0) | Periodic self-reflection on recent sessions. Analyzes what went well, what went wrong, and writ... |
| 4 | [aminer-data-search](skills/aminer-open-academic-1.0.5) | 使用 AMiner 开放平台 API 进行学术数据查询与分析。当用户需要查询学者信息、论文详情、机构数据、期刊内容或专利信息时使用此 skill。 触发场景：提到 AMiner、学术数据查询... |
| 5 | [architecture-designer](skills/architecture-designer-0.1.0) | Use when designing new system architecture, reviewing existing designs, or making architectural... |
| 6 | [ask-matt](skills/ask-matt) | Ask which skill or flow fits your situation. A router over the skills in this repo. |
| 7 | [autoglm-browser-agent](skills/autoglm-browser-agent) | 智能浏览器自动化代理,可执行任何需要浏览器的任务。 包括但不限于:打开网页、搜索信息(百度/谷歌/必应)、浏览社交媒体(微博/小红书/知乎/抖音/B站)、 点赞/评论/转发/收藏、发帖/发消... |
| 8 | [autoglm-deepresearch](skills/autoglm-deepresearch) | 对用户提出的课题进行深度研究和调研，输出结构化的深度报告。当用户需要深入了解某个话题、做行业调研、专题研究、竞品分析等场景时使用此 skill。 与普通搜索不同，deepresearch 会... |
| 9 | [autoglm-generate-image](skills/autoglm-generate-image) | 使用 AutoGLM 文生图接口，根据用户输入的文字描述生成图片。当用户需要生成图片、文字转图片、AI绘图等场景时使用此 skill。 Token 通过本地服务 http://127.0.0... |
| 10 | [autoglm-open-link](skills/autoglm-open-link) | 使用 AutoGLM Open Link 接口打开指定网页并提取页面正文内容。当用户需要读取某个网页详情、提取文章全文、抓取页面正文做摘要或分析时使用此 skill。 Token 通过本地服... |
| 11 | [autoglm-search-image](skills/autoglm-search-image) | 使用 AutoGLM 搜图接口，根据用户输入的关键词搜索相关图片。当用户需要搜索图片、查找图片素材等场景时使用此 skill。 Token 通过本地服务 http://127.0.0.1:5... |
| 12 | [autoglm-websearch](skills/autoglm-websearch) | 使用 AutoGLM Web Search 接口进行网络信息搜索。当用户需要联网搜索、查询最新资讯、检索网页内容或获取实时信息时使用此 skill。 Token 通过本地服务 http://... |
| 13 | [automation-workflows](skills/automation-workflows-0.1.0) | Design and implement automation workflows to save time and scale operations as a solopreneur. U... |
| 14 | [backtest-expert](skills/backtest-expert-0.1.0) | Expert guidance for systematic backtesting of trading strategies. Use when developing, testing,... |
| 15 | [baiyun-context](skills/baiyun-context) | Use when 需要导出或排查运小星(BaiYun_Agent)用户的对话记录：找上下文、生成“找到上下文N_完整对话记录.xlsx”、查询用户某天的 audit log、定位对话里为什么... |
| 16 | [baiyun-release-workflow](skills/baiyun-release-workflow) | Execute and audit BaiYun_Agent release, remote commit, push, and PR workflows, including by_dev... |
| 17 | [batch-grill-me](skills/batch-grill-me) | A relentless interview that asks every frontier question at once, round by round. |
| 18 | [blog-writer](skills/blog-writer-0.1.0) | This skill should be used when writing blog posts, articles, or long-form content in the writer... |
| 19 | [brainstorming](skills/brainstorming-0.1.0) | "You MUST use this before any creative work - creating features, building components, adding fu... |
| 20 | [bugfix-workflow](skills/bugfix-workflow) | Bug修复通用工作流。当生产环境发现Bug需要紧急修复时使用，覆盖所有类型：功能异常、输出错误、性能问题、安全漏洞、用户体验问题等。触发关键词：Bug修复、hotfix、生产事故、fix、根... |
| 21 | [claude-handoff](skills/claude-handoff) | Hand the current conversation off to a fresh background agent that picks up the work immediatel... |
| 22 | [clawdefender](skills/clawdefender-1) | Security scanner and input sanitizer for AI agents. Detects prompt injection, command injection... |
| 23 | [Code](skills/code-1.0.4) | Coding workflow with planning, implementation, verification, and testing for clean software dev... |
| 24 | [code-review](skills/code-review) | Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes — St... |
| 25 | [code-review-score](skills/code-review-score) | Two-axis code review (Standards + Spec) with numeric scoring and a merge recommendation. Use wh... |
| 26 | [codebase-design](skills/codebase-design) | Shared vocabulary for designing deep modules. Use when the user wants to design or improve a mo... |
| 27 | [content-strategy](skills/content-strategy-0.1.0) | Build and execute a content marketing strategy for a solopreneur business. Use when planning wh... |
| 28 | [copywriting](skills/copywriting-0.1.0) | Write persuasive copy for landing pages, emails, ads, sales pages, and marketing materials. Use... |
| 29 | [debug-pro](skills/debug-pro-1.0.0) | Use when encountering any bug, test failure, or unexpected behavior, before proposing fixes |
| 30 | [design-an-interface](skills/design-an-interface) | Generate multiple radically different interface designs for a module using parallel sub-agents.... |
| 31 | [diagnosing-bugs](skills/diagnosing-bugs) | Diagnosis loop for hard bugs and performance regressions. Use when the user says "diagnose"/"de... |
| 32 | [documentation-and-adrs](skills/documentation-and-adrs) | 记录技术决策及其背景、约束、备选方案和取舍，并维护架构决策记录、公共 API 文档、README、变更日志与面向开发代理的项目规则。适用于作出重要架构决策、比较竞争方案、新增或修改公共接口、... |
| 33 | [domain-modeling](skills/domain-modeling) | Build and sharpen a project's domain model. Use when the user wants to pin down domain terminol... |
| 34 | [edit-article](skills/edit-article) | Edit and improve articles by restructuring sections, improving clarity, and tightening prose. U... |
| 35 | [executing-plans](skills/executing-plans-0.1.0) | Use when you have a written implementation plan to execute in a separate session with review ch... |
| 36 | [feishu-chat-history](skills/feishu-chat-history) | Fetch and summarize Feishu group chat history. Use when the user asks to read, review, or summa... |
| 37 | [feishu-common](skills/feishu-common) | Shared Feishu (Lark) auth library for feishu-* skills. Provides tenant_access_token caching and... |
| 38 | [feishu-cron-reminder](skills/feishu-cron-reminder) | Create cron jobs that reliably deliver reminders to Feishu (飞书) chats. Use when the user asks t... |
| 39 | [feishu-doc](skills/feishu-doc-1.2.7) | Fetch content from Feishu (Lark) Wiki, Docs, Sheets, and Bitable. Automatically resolves Wiki U... |
| 40 | [feishu-drive](skills/feishu-drive-1.0.0) | 飞书云空间文件管理 Skill。上传/下载/移动/搜索文件、创建文件夹、获取元数据等。当需要管理飞书云空间中的文件和文件夹时使用此 Skill。 |
| 41 | [feishu-perm](skills/feishu-perm) | | |
| 42 | [feishu-screenshot](skills/feishu-screenshot) | Capture macOS screenshots and send to Feishu. Use when the user asks to take a screenshot and s... |
| 43 | [feishu-send-file](skills/feishu-send-file) | Send files to a Feishu group or user via REST API. Use when the user explicitly asks to send a ... |
| 44 | [FFmpeg](skills/ffmpeg-video-editor-1.0.0) | Generate FFmpeg commands from natural language video editing requests - cut, trim, convert, com... |
| 45 | [find-skills](skills/find-skills) | Helps users discover and install agent skills when they ask questions like "how do I do X", "fi... |
| 46 | [foxcode-image-gen](skills/foxcode-image-gen) | Generate high-quality images via the FoxCode gpt-image-2 API. Use when the user asks to generat... |
| 47 | [frontend-design](skills/frontend-design-3-0.1.0) | Create distinctive, production-grade frontend interfaces with high design quality. Use this ski... |
| 48 | [git-essentials](skills/git-essentials-1.0.0) | Essential Git commands and workflows for version control, branching, and collaboration. |
| 49 | [git-guardrails-claude-code](skills/git-guardrails-claude-code) | Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D,... |
| 50 | [grill-me](skills/grill-me) | A relentless interview to sharpen a plan or design. |
| 51 | [grill-with-docs](skills/grill-with-docs) | A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary... |
| 52 | [grilling](skills/grilling) | Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-... |
| 53 | [handoff](skills/handoff) | Compact the current conversation into a handoff document for another agent to pick up. |
| 54 | [implement](skills/implement) | "Implement a piece of work based on a spec or set of tickets." |
| 55 | [improve-codebase-architecture](skills/improve-codebase-architecture) | Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill t... |
| 56 | [interview-designer](skills/interview-designer-1.0.0) | Analyze resumes and design interview strategies using evidence-based methodology. Transforms in... |
| 57 | [loop-me](skills/loop-me) | Grill me about specs for the workflows I want to build, within this workspace. |
| 58 | [Market](skills/market-research-1.0.0) | "Size markets, analyze competitors, and validate opportunities with practical frameworks and fr... |
| 59 | [Memory](skills/memory-1.0.2) | Infinite organized memory that complements your agent's built-in memory with unlimited categori... |
| 60 | [microsoft-foundry](skills/microsoft-foundry) | "Deploy, evaluate, fine-tune, and manage Foundry agents end-to-end with azd: hosted agent scaff... |
| 61 | [migrate-to-shoehorn](skills/migrate-to-shoehorn) | Migrate test files from `as` type assertions to @total-typescript/shoehorn. Use when user menti... |
| 62 | [obsidian-ontology-sync](skills/obsidian-ontology-sync-1.0.1) | Bidirectional sync between Obsidian PKM (human-friendly notes) and structured ontology (machine... |
| 63 | [obsidian-vault](skills/obsidian-vault) | Search, create, and manage notes in the Obsidian vault with wikilinks and index notes. Use when... |
| 64 | [opencode-controller](skills/opencode-controller-1.0.0) | Control and operate Opencode via slash commands. Use this skill to manage sessions, select mode... |
| 65 | [parallel-data-processing](skills/parallel-data-processing) | 精细化批量数据处理通用工作流。当需要对大量结构化数据逐条进行精细处理（分类、审核、翻译、改写、信息提取、打标、清洗、校验等）时使用，例如"把这些FAQ逐条分类"、"给这1万条记录逐条打标签"... |
| 66 | [prototype](skills/prototype) | Build a throwaway prototype to answer a design question. Use when the user wants to sanity-chec... |
| 67 | [qa](skills/qa) | Interactive QA session where user reports bugs or issues conversationally, and the agent files ... |
| 68 | [request-refactor-plan](skills/request-refactor-plan) | Create a detailed refactor plan with tiny commits via user interview, then file it as a GitHub ... |
| 69 | [research](skills/research) | Investigate a question against high-trust primary sources and capture the findings as a Markdow... |
| 70 | [research-paper-writer](skills/research-paper-writer-0.1.0) | Creates formal academic research papers following IEEE/ACM formatting standards with proper str... |
| 71 | [resolving-merge-conflicts](skills/resolving-merge-conflicts) | "Use when you need to resolve an in-progress git merge/rebase conflict." |
| 72 | [scaffold-exercises](skills/scaffold-exercises) | Create exercise directory structures with sections, problems, solutions, and explainers that pa... |
| 73 | [security-auditor](skills/security-auditor-1.0.0) | Use when reviewing code for security vulnerabilities, implementing authentication flows, auditi... |
| 74 | [Self-Improving](skills/self-improving-1.1.3) | Self-reflection + Self-criticism + learning from corrections. Agent evaluates its own work, cat... |
| 75 | [sentry-create-alert](skills/sentry-create-alert) | Create Sentry alerts using the workflow engine API. Use when asked to create alerts, set up not... |
| 76 | [sentry-debug-issue](skills/sentry-debug-issue) | Debug and fix a Sentry issue — find it (by link, ID, or search), pull full context (stack trace... |
| 77 | [sentry-fix-stack-traces](skills/sentry-fix-stack-traces) | Make Sentry stack traces readable — upload source maps for JavaScript/TypeScript, or debug file... |
| 78 | [sentry-get-started](skills/sentry-get-started) | Guided entry point for using Sentry through your agent. Orients you to your current setup and, ... |
| 79 | [sentry-instrument](skills/sentry-instrument) | Instrument an application with Sentry — detect the platform, install and initialize the SDK if ... |
| 80 | [sentry-otel-exporter-setup](skills/sentry-otel-exporter-setup) | Configure the OpenTelemetry Collector with Sentry Exporter for multi-project routing and automa... |
| 81 | [sentry-setup-releases](skills/sentry-setup-releases) | Set up Sentry releases and deploy tracking — tag events with a version and environment, create ... |
| 82 | [sentry-snapshots-cocoa](skills/sentry-snapshots-cocoa) | Full Sentry Snapshots setup for Apple/Cocoa projects. Use when asked to "setup SnapshotPreviews... |
| 83 | [SEO](skills/seo-1.0.3) | SEO specialist agent with site audits, content writing, keyword research, technical fixes, link... |
| 84 | [seo-content-writer](skills/seo-content-writer-2.0.0) | 'Use when the user asks to "write SEO content", "create a blog post", "write an article", "cont... |
| 85 | [session-logs](skills/session-logs-1.0.0) | Search and analyze your own session logs (older/parent conversations) using jq. |
| 86 | [setup-matt-pocock-skills](skills/setup-matt-pocock-skills) | Configure this repo for the engineering skills — set up its issue tracker, triage label vocabul... |
| 87 | [setup-pre-commit](skills/setup-pre-commit) | Set up Husky pre-commit hooks with lint-staged (Prettier), type checking, and tests in the curr... |
| 88 | [setup-ts-deep-modules](skills/setup-ts-deep-modules) | Wire dependency-cruiser into a TypeScript repo so each package is a deep module — implementatio... |
| 89 | [skill-creator](skills/skill-creator-0.1.0) | Guide for creating effective skills. This skill should be used when users want to create a new ... |
| 90 | [skill-vetter](skills/skill-vetter-1.0.0) | Security-first skill vetting for AI agents. Use before installing any skill from ClawdHub, GitH... |
| 91 | [social-content](skills/social-content-generator-0.1.0) | "When the user wants help creating, scheduling, or optimizing social media content for LinkedIn... |
| 92 | [Social](skills/social-media-scheduler-1.0.0) | Plan, draft, and organize social media content across platforms. Create content calendars, writ... |
| 93 | [supabase-postgres-best-practices](skills/supabase-postgres-best-practices) | Postgres performance optimization and best practices from Supabase. Use this skill when writing... |
| 94 | [tdd](skills/tdd) | Test-driven development. Use when the user wants to build features or fix bugs test-first, ment... |
| 95 | [teach](skills/teach) | Teach the user a new skill or concept, within this workspace. |
| 96 | [test-runner](skills/test-runner-1.0.0) | Use when writing and running tests across languages and frameworks |
| 97 | [tmux](skills/tmux-1.0.0) | Remote-control tmux sessions for interactive CLIs by sending keystrokes and scraping pane outpu... |
| 98 | [to-questionnaire](skills/to-questionnaire) | Turn a decision you can't fully answer into a questionnaire for someone else to fill in. |
| 99 | [to-spec](skills/to-spec) | Turn the current conversation into a spec and publish it to the project issue tracker — no inte... |
| 100 | [to-tickets](skills/to-tickets) | Break a plan, spec, or the current conversation into a set of tracer-bullet tickets, each decla... |
| 101 | [triage](skills/triage) | Move issues and external PRs through a state machine of triage roles — categorise, verify, gril... |
| 102 | [ubiquitous-language](skills/ubiquitous-language) | Extract a DDD-style ubiquitous language glossary from the current conversation, flagging ambigu... |
| 103 | [ui-ux-pro-max](skills/ui-ux-pro-max-0.1.0) | UI/UX design intelligence and implementation guidance for building polished interfaces. Use whe... |
| 104 | [video-frames](skills/video-frames-1.0.0) | Extract frames or short clips from videos using ffmpeg. |
| 105 | [wayfinder](skills/wayfinder) | Plan a huge chunk of work — more than one agent session can hold — as a shared map of decision ... |
| 106 | [wecom-chat-extractor](skills/wecom-chat-extractor) | Extract and query WeCom (企业微信/WeChat Work) local chat data on Windows. Discovers encrypted SQLi... |
| 107 | [wizard](skills/wizard) | Generate an interactive bash wizard that walks a human through a manual procedure — third-party... |
| 108 | [writing-beats](skills/writing-beats) | Writing, exploit — assemble raw material into a journey of beats, grounding each term before a ... |
| 109 | [writing-fragments](skills/writing-fragments) | Writing, explore — mine raw fragments, no structure yet. |
| 110 | [writing-great-skills](skills/writing-great-skills) | Reference for writing and editing skills well — the vocabulary and principles that make a skill... |
| 111 | [writing-plans](skills/writing-plans-0.1.0) | Use when you have a spec or requirements for a multi-step task, before touching code |
| 112 | [writing-shape](skills/writing-shape) | Writing, exploit — shape raw material into an article, paragraph by paragraph. |

## License

MIT
