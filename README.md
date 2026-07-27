# opencode-skills

Personal collection of 110 opencode agent skills.

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
├── skills/              # 110 skill directories
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

## Skill Index (110 skills)

| # | Skill | Description |
|---|-------|-------------|
| 1 | [1password](skills/1password-1.0.1) | Set up and use 1Password CLI (op). |
| 2 | [a-stock-analysis](skills/a-stock-analysis-1.0.0) | A股实时行情与分时量能分析。 |
| 3 | [agent-self-reflection](skills/agent-self-reflection-1.0.0) | Periodic self-reflection on recent sessions. |
| 4 | [aminer-data-search](skills/aminer-open-academic-1.0.5) | Academic data search via AMiner API. |
| 5 | [architecture-designer](skills/architecture-designer-0.1.0) | System architecture design and review. |
| 6 | [ask-matt](skills/ask-matt) | Router over skills in the repo. |
| 7 | [autoglm-browser-agent](skills/autoglm-browser-agent) | Browser automation agent. |
| 8 | [autoglm-deepresearch](skills/autoglm-deepresearch) | Deep research and investigation. |
| 9 | [autoglm-generate-image](skills/autoglm-generate-image) | Text-to-image generation. |
| 10 | [autoglm-open-link](skills/autoglm-open-link) | Open and extract web page content. |
| 11 | [autoglm-search-image](skills/autoglm-search-image) | Image search. |
| 12 | [autoglm-websearch](skills/autoglm-websearch) | Web search. |
| 13 | [automation-workflows](skills/automation-workflows-0.1.0) | Design and implement automation workflows. |
| 14 | [backtest-expert](skills/backtest-expert-0.1.0) | Systematic backtesting of trading strategies. |
| 15 | [batch-grill-me](skills/batch-grill-me) | Relentless interview, all frontier questions at once. |
| 16 | [blog-writer](skills/blog-writer-0.1.0) | Blog posts and long-form content writing. |
| 17 | [brainstorming](skills/brainstorming) | Explore user intent before creative work. |
| 18 | [brainstorming](skills/brainstorming-0.1.0) | Explore user intent before creative work (v0.1.0). |
| 19 | [claude-handoff](skills/claude-handoff) | Hand off conversation to a fresh background agent. |
| 20 | [clawdefender](skills/clawdefender-1) | Security scanner and input sanitizer for AI agents. |
| 21 | [code](skills/code-1.0.4) | Coding workflow with planning, implementation, verification, and testing. |
| 22 | [code-review](skills/code-review) | Review changes along Standards and Spec axes. |
| 23 | [codebase-design](skills/codebase-design) | Vocabulary for designing deep modules. |
| 24 | [content-strategy](skills/content-strategy-0.1.0) | Content marketing strategy for solopreneurs. |
| 25 | [copywriting](skills/copywriting-0.1.0) | Persuasive copy for landing pages, emails, ads. |
| 26 | [debug-pro](skills/debug-pro-1.0.0) | Systematic debugging methodology. |
| 27 | [design-an-interface](skills/design-an-interface) | Generate multiple interface designs using parallel sub-agents. |
| 28 | [diagnosing-bugs](skills/diagnosing-bugs) | Diagnosis loop for hard bugs and performance regressions. |
| 29 | [dispatching-parallel-agents](skills/dispatching-parallel-agents) | 2+ independent tasks without shared state. |
| 30 | [domain-modeling](skills/domain-modeling) | Build and sharpen a project's domain model. |
| 31 | [edit-article](skills/edit-article) | Edit and improve articles. |
| 32 | [executing-plans](skills/executing-plans) | Execute written implementation plans with review checkpoints. |
| 33 | [executing-plans](skills/executing-plans-0.1.0) | Execute written implementation plans (v0.1.0). |
| 34 | [feishu-chat-history](skills/feishu-chat-history) | Fetch and summarize Feishu group chat history. |
| 35 | [feishu-cron-reminder](skills/feishu-cron-reminder) | Cron jobs delivering reminders to Feishu chats. |
| 36 | [feishu-doc](skills/feishu-doc-1.2.7) | Fetch content from Feishu Wiki, Docs, Sheets, and Bitable. |
| 37 | [feishu-drive](skills/feishu-drive-1.0.0) | 飞书云空间文件管理。 |
| 38 | [feishu-perm](skills/feishu-perm) | Feishu permission management. |
| 39 | [feishu-screenshot](skills/feishu-screenshot) | Capture screenshots and send to Feishu. |
| 40 | [feishu-send-file](skills/feishu-send-file) | Send files to Feishu group or user. |
| 41 | [ffmpeg-video-editor](skills/ffmpeg-video-editor-1.0.0) | Generate FFmpeg commands from natural language. |
| 42 | [find-skills](skills/find-skills) | Discover and install agent skills. |
| 43 | [finishing-a-development-branch](skills/finishing-a-development-branch) | Decide how to integrate completed work. |
| 44 | [frontend-design](skills/frontend-design-3-0.1.0) | Production-grade frontend interfaces with high design quality. |
| 45 | [git-essentials](skills/git-essentials-1.0.0) | Essential Git commands and workflows. |
| 46 | [git-guardrails-claude-code](skills/git-guardrails-claude-code) | Block dangerous git commands via hooks. |
| 47 | [grill-me](skills/grill-me) | Relentless interview to sharpen a plan or design. |
| 48 | [grill-with-docs](skills/grill-with-docs) | Relentless interview that also creates docs. |
| 49 | [grilling](skills/grilling) | Stress-test plans, decisions, or ideas. |
| 50 | [handoff](skills/handoff) | Compact conversation into a handoff document. |
| 51 | [implement](skills/implement) | Implement work based on a spec or set of tickets. |
| 52 | [improve-codebase-architecture](skills/improve-codebase-architecture) | Scan codebase for deepening opportunities. |
| 53 | [interview-designer](skills/interview-designer-1.0.0) | Analyze resumes and design interview strategies. |
| 54 | [loop-me](skills/loop-me) | Grill about specs for workflows. |
| 55 | [market-research](skills/market-research-1.0.0) | Size markets, analyze competitors, validate opportunities. |
| 56 | [memory](skills/memory-1.0.2) | Infinite organized memory storage. |
| 57 | [microsoft-foundry](skills/microsoft-foundry) | Deploy, evaluate, fine-tune, and manage Foundry agents. |
| 58 | [migrate-to-shoehorn](skills/migrate-to-shoehorn) | Migrate `as` type assertions to shoehorn. |
| 59 | [obsidian-ontology-sync](skills/obsidian-ontology-sync-1.0.1) | Bidirectional sync between Obsidian PKM and structured ontology. |
| 60 | [obsidian-vault](skills/obsidian-vault) | Search, create, and manage Obsidian notes. |
| 61 | [opencode-controller](skills/opencode-controller-1.0.0) | Control and operate Opencode via slash commands. |
| 62 | [prototype](skills/prototype) | Build a throwaway prototype to answer a design question. |
| 63 | [qa](skills/qa) | Interactive QA session, file GitHub issues conversationally. |
| 64 | [receiving-code-review](skills/receiving-code-review) | Receive code review feedback with technical rigor. |
| 65 | [request-refactor-plan](skills/request-refactor-plan) | Create a detailed refactor plan with tiny commits. |
| 66 | [requesting-code-review](skills/requesting-code-review) | Verify work meets requirements before merging. |
| 67 | [research](skills/research) | Investigate a question against high-trust primary sources. |
| 68 | [research-paper-writer](skills/research-paper-writer-0.1.0) | Formal academic research papers (IEEE/ACM). |
| 69 | [resolving-merge-conflicts](skills/resolving-merge-conflicts) | Resolve in-progress git merge/rebase conflicts. |
| 70 | [scaffold-exercises](skills/scaffold-exercises) | Create exercise directory structures. |
| 71 | [security-auditor](skills/security-auditor-1.0.0) | Review code for security vulnerabilities. |
| 72 | [self-improving](skills/self-improving-1.1.3) | Self-reflection + self-criticism + learning from corrections. |
| 73 | [seo](skills/seo-1.0.3) | SEO specialist: site audits, content, keyword research. |
| 74 | [seo-content-writer](skills/seo-content-writer-2.0.0) | SEO-optimized content that ranks in search engines. |
| 75 | [session-logs](skills/session-logs-1.0.0) | Search and analyze session logs using jq. |
| 76 | [setup-matt-pocock-skills](skills/setup-matt-pocock-skills) | Configure repo for engineering skills. |
| 77 | [setup-pre-commit](skills/setup-pre-commit) | Set up Husky pre-commit hooks with lint-staged. |
| 78 | [setup-ts-deep-modules](skills/setup-ts-deep-modules) | Wire dependency-cruiser into a TypeScript repo. |
| 79 | [skill-creator](skills/skill-creator-0.1.0) | Guide for creating effective skills. |
| 80 | [skill-vetter](skills/skill-vetter-1.0.0) | Security-first skill vetting for AI agents. |
| 81 | [social-content](skills/social-content-generator-0.1.0) | Social media content creation and optimization. |
| 82 | [social-media-scheduler](skills/social-media-scheduler-1.0.0) | Plan, draft, and organize social media content. |
| 83 | [subagent-driven-development](skills/subagent-driven-development) | Execute implementation plans with independent tasks. |
| 84 | [supabase-postgres-best-practices](skills/supabase-postgres-best-practices) | Postgres performance optimization and best practices. |
| 85 | [systematic-debugging](skills/systematic-debugging) | Debug bugs, test failures, unexpected behavior. |
| 86 | [tdd](skills/tdd) | Test-driven development. |
| 87 | [teach](skills/teach) | Teach the user a new skill or concept. |
| 88 | [test-driven-development](skills/test-driven-development) | Implement features/bugfixes test-first. |
| 89 | [test-runner](skills/test-runner-1.0.0) | Write and run tests across languages and frameworks. |
| 90 | [tmux](skills/tmux-1.0.0) | Remote-control tmux sessions. |
| 91 | [to-questionnaire](skills/to-questionnaire) | Turn a decision into a questionnaire. |
| 92 | [to-spec](skills/to-spec) | Turn conversation into a spec. |
| 93 | [to-tickets](skills/to-tickets) | Break a plan into tracer-bullet tickets. |
| 94 | [triage](skills/triage) | Move issues and PRs through triage state machine. |
| 95 | [ubiquitous-language](skills/ubiquitous-language) | Extract DDD-style ubiquitous language glossary. |
| 96 | [ui-ux-pro-max](skills/ui-ux-pro-max-0.1.0) | UI/UX design intelligence and implementation guidance. |
| 97 | [using-git-worktrees](skills/using-git-worktrees) | Set up isolated workspace for feature work. |
| 98 | [using-superpowers](skills/using-superpowers) | Establish how to find and use skills. |
| 99 | [verification-before-completion](skills/verification-before-completion) | Verify before claiming work is complete. |
| 100 | [video-frames](skills/video-frames-1.0.0) | Extract frames or clips from videos using ffmpeg. |
| 101 | [wayfinder](skills/wayfinder) | Plan huge work as shared map of decision tickets. |
| 102 | [wecom-chat-extractor](skills/wecom-chat-extractor) | Extract and query WeCom local chat data on Windows. |
| 103 | [wizard](skills/wizard) | Generate interactive bash wizard for manual procedures. |
| 104 | [writing-beats](skills/writing-beats) | Assemble raw material into a journey of beats. |
| 105 | [writing-fragments](skills/writing-fragments) | Mine raw fragments, no structure yet. |
| 106 | [writing-great-skills](skills/writing-great-skills) | Reference for writing and editing skills well. |
| 107 | [writing-plans](skills/writing-plans) | Write implementation plans from specs. |
| 108 | [writing-plans](skills/writing-plans-0.1.0) | Write implementation plans from specs (v0.1.0). |
| 109 | [writing-shape](skills/writing-shape) | Shape raw material into an article. |
| 110 | [writing-skills](skills/writing-skills) | Create, edit, or verify skills before deployment. |

## License

MIT
