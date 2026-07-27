# Makefile for opencode-skills
# Usage:
#   make install      # symlink skills to ~/.config/opencode/skills/
#   make install-copy # copy skills to ~/.config/opencode/skills/
#   make install-project  # install to .opencode/skills/ (project-local)
#   make uninstall    # remove symlinks
#   make list         # list available skills
#   make validate     # validate SKILL.md frontmatter
#   make status       # show installation status
#   make help         # show all targets

SKILLS_DIR := skills
GLOBAL_DEST := $(HOME)/.config/opencode/skills
PROJECT_DEST := .opencode/skills

.PHONY: help install install-copy install-project uninstall list validate status deps

help: ## Show all available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Symlink skills to ~/.config/opencode/skills/
	@./install.sh

install-copy: ## Copy skills to ~/.config/opencode/skills/
	@./install.sh --copy

install-project: ## Install skills to .opencode/skills/ (project-local)
	@./install.sh --project

uninstall: ## Remove installed skill symlinks
	@echo "Removing skills from $(GLOBAL_DEST)..."
	@for dir in $(SKILLS_DIR)/*/; do \
		name=$$(basename $$dir); \
		target="$(GLOBAL_DEST)/$$name"; \
		if [ -L "$$target" ] || [ -d "$$target" ]; then \
			rm -rf "$$target"; \
			echo "  Removed: $$name"; \
		fi; \
	done
	@echo "Done."

list: ## List available skills
	@./install.sh --list

validate: ## Validate SKILL.md frontmatter (requires Python 3 + PyYAML)
	@echo "Validating SKILL.md files..."
	@python3 -c "\
import os, sys, yaml; \
errors = []; \
skills_dir = '$(SKILLS_DIR)'; \
[errors.append(f'{d}: missing or invalid SKILL.md') for d in sorted(os.listdir(skills_dir)) \
	if os.path.isdir(os.path.join(skills_dir, d)) \
	and (not os.path.exists(os.path.join(skills_dir, d, 'SKILL.md')) \
	or not _check(os.path.join(skills_dir, d, 'SKILL.md'))) \
	if not (lambda f: (lambda c: c.startswith('---') and 'name:' in c and 'description:' in c)(open(f).read()))(os.path.join(skills_dir, d, 'SKILL.md')) \
	if True] if False else None; \
count = 0; \
ok = 0; \
for d in sorted(os.listdir(skills_dir)): \
	p = os.path.join(skills_dir, d, 'SKILL.md'); \
	if not os.path.isdir(os.path.join(skills_dir, d)): continue; \
	count += 1; \
	if not os.path.exists(p): \
		errors.append(f'{d}: missing SKILL.md'); continue; \
	content = open(p).read(); \
	if not content.startswith('---'): \
		errors.append(f'{d}: missing YAML frontmatter'); continue; \
	ok += 1; \
print(f'  {ok}/{count} skills valid'); \
[print(f'  ERROR: {e}') for e in errors]; \
sys.exit(1 if errors else 0)"

status: ## Show installation status
	@echo "Skills in repository: $$(ls -d $(SKILLS_DIR)/*/ | wc -l)"
	@echo "Installed globally:   $$(ls -d $(GLOBAL_DEST)/*/ 2>/dev/null | wc -l)"
	@echo "Installed in project: $$(ls -d $(PROJECT_DEST)/*/ 2>/dev/null | wc -l)"

deps: ## Install Python dependencies
	@echo "Installing Python dependencies..."
	@pip install -r requirements.txt
	@echo "Done."
