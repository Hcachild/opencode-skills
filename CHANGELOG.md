# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
