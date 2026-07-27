# Miscellaneous

Non-essential files kept for reference. Not required for OpenCode skill discovery or usage.

## openai-yaml/

Claude Code agent interface configs (`openai.yaml`). Each file defines a skill's display name and short description for Claude Code's UI.

**Not used by OpenCode** — OpenCode only reads `SKILL.md` YAML frontmatter (`name` + `description`).

Kept here for:
- Reference if migrating back to Claude Code
- Display name mapping if needed

## autoglm-browser-agent-dist/

Windows binaries for the `autoglm-browser-agent` skill:
- `mcp_server.exe` — MCP server, called by `mcporter` to drive browser automation
- `relay.exe` — WebSocket relay daemon, keeps Chrome extension connection alive

**Windows only.** macOS/Linux users need the platform-native binaries from the original source.

If you need this skill on a new machine, copy these to `skills/autoglm-browser-agent/dist/`.
