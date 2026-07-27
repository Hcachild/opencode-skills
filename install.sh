#!/usr/bin/env bash
# install.sh — Install opencode-skills to ~/.config/opencode/skills/
# Usage:
#   ./install.sh              # install all skills (symlink)
#   ./install.sh --copy        # install all skills (copy)
#   ./install.sh --project     # install to .opencode/skills/ (project-local)
#   ./install.sh --list        # list available skills
#   ./install.sh <skill-name>  # install a single skill

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="$SCRIPT_DIR/skills"
MODE="symlink"
SCOPE="global"
TARGET_SKILL=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --copy)    MODE="copy"; shift ;;
        --project) SCOPE="project"; shift ;;
        --list)    
            echo "Available skills:"
            find "$SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; | sort
            exit 0
            ;;
        --help|-h)
            echo "Usage: ./install.sh [OPTIONS] [SKILL_NAME]"
            echo ""
            echo "Options:"
            echo "  --copy       Copy files instead of symlinking"
            echo "  --project    Install to .opencode/skills/ (project-local)"
            echo "  --list       List available skills"
            echo "  --help       Show this help message"
            echo ""
            echo "Examples:"
            echo "  ./install.sh                    # Install all skills globally (symlink)"
            echo "  ./install.sh --copy             # Install all skills globally (copy)"
            echo "  ./install.sh --project          # Install to current project"
            echo "  ./install.sh tdd                # Install only the 'tdd' skill"
            exit 0
            ;;
        *)         TARGET_SKILL="$1"; shift ;;
    esac
done

# Determine destination
if [[ "$SCOPE" == "project" ]]; then
    DEST=".opencode/skills"
else
    DEST="$HOME/.config/opencode/skills"
fi

mkdir -p "$DEST"

# Gather skills to install
if [[ -n "$TARGET_SKILL" ]]; then
    if [[ ! -d "$SKILLS_DIR/$TARGET_SKILL" ]]; then
        echo "Error: Skill '$TARGET_SKILL' not found in $SKILLS_DIR"
        echo "Run './install.sh --list' to see available skills."
        exit 1
    fi
    SKILLS=("$TARGET_SKILL")
else
    mapfile -t SKILLS < <(find "$SKILLS_DIR" -maxdepth 1 -mindepth 1 -type d -exec basename {} \; | sort)
fi

echo "Installing ${#SKILLS[@]} skill(s) to $DEST (mode: $MODE)"
echo ""

installed=0
skipped=0
for skill in "${SKILLS[@]}"; do
    src="$SKILLS_DIR/$skill"
    dst="$DEST/$skill"

    if [[ -e "$dst" || -L "$dst" ]]; then
        if [[ "$MODE" == "copy" ]]; then
            rm -rf "$dst"
        else
            echo "  SKIP  $skill (already exists at $dst)"
            ((skipped++))
            continue
        fi
    fi

    if [[ "$MODE" == "symlink" ]]; then
        ln -s "$src" "$dst"
        echo "  LINK  $skill -> $dst"
    else
        cp -r "$src" "$dst"
        echo "  COPY  $skill -> $dst"
    fi
    ((installed++))
done

echo ""
echo "Done: $installed installed, $skipped skipped."

# Install Node.js dependencies for feishu-doc
FEISHU_DOC="$DEST/feishu-doc-1.2.7"
if [[ -d "$FEISHU_DOC" && -f "$FEISHU_DOC/package.json" ]]; then
    echo ""
    echo "Installing Node.js dependencies for feishu-doc-1.2.7..."
    if command -v npm &>/dev/null; then
        (cd "$FEISHU_DOC" && npm install --production) || echo "  Warning: npm install failed for feishu-doc"
    elif command -v bun &>/dev/null; then
        (cd "$FEISHU_DOC" && bun install) || echo "  Warning: bun install failed for feishu-doc"
    else
        echo "  Warning: Neither npm nor bun found. Run 'npm install' in $FEISHU_DOC manually."
    fi
fi

# Remind about Python dependencies
echo ""
echo "NOTE: Some skills require Python dependencies."
echo "  pip install -r requirements.txt"
echo ""
echo "Restart OpenCode for skills to take effect."
