# AGENTS.md — Project rules for opencode-skills

## Project Overview

This repository contains a collection of 123 opencode agent skills. Each skill lives in `skills/<name>/SKILL.md`.

## Conventions

- All skills are in the `skills/` directory (flat structure)
- Every skill must have a `SKILL.md` with YAML frontmatter (`name` + `description`)
- Never commit secrets, API keys, or tokens — use placeholders with TODO comments
- Platform-specific binaries (`.exe`) should not be committed
- Shell scripts (`.sh`) require `#!/usr/bin/env bash` shebang and `set -euo pipefail`

## Key Files

- `install.sh` / `install.ps1` — Installation scripts
- `Makefile` — Build/install/validate commands
- `requirements.txt` — Python dependencies
- `skills/` — All skill directories

## Skills Requiring External Configuration

| Skill | Configuration Needed |
|-------|---------------------|
| `autoglm-*` | `APP_ID` and `APP_KEY` in each `.py` file |
| `feishu-common` | `FEISHU_APP_ID` / `FEISHU_APP_SECRET` env vars or `config.json` |
| `feishu-doc-1.2.7` | `app_id` and `app_secret` in `config.json` |
| `feishu-chat-history` | Feishu API credentials in `references/api.md` |
| `aminer-open-academic-1.0.5` | API key in `scripts/aminer_client.py` |
| `foxcode-image-gen` | `YOUR_FOXCODE_API_KEY` in `scripts/generate_image.py` |

## Do Not

- Do not commit `node_modules/`, `__pycache__/`, or `cache/` directories
- Do not commit `.pyc` files
- Do not commit `openai.yaml` files (Claude Code format)
- Do not commit binary executables
