# Contributing to opencode-skills

## Adding a New Skill

1. Create a directory under `skills/<skill-name>/`
2. Add a `SKILL.md` file with required YAML frontmatter:

```markdown
---
name: skill-name
description: Use when [specific triggering conditions and symptoms]
---

# Skill Name

## Overview
...
```

3. `name` must use lowercase letters, numbers, and hyphens only
4. `description` must start with "Use when..." and describe triggering conditions
5. Add supporting files (scripts, references) as needed
6. Run `make validate` to check frontmatter compliance
7. Update `README.md` skill index
8. Commit and push

## Skill Naming Conventions

- Use lowercase with hyphens: `my-skill-name`
- Version suffixes are allowed: `my-skill-1.0.0`
- Keep names descriptive and concise

## File Structure

```
skills/<skill-name>/
  SKILL.md          # Required: main skill definition
  scripts/          # Optional: executable scripts
  references/       # Optional: deep-dive documentation
  assets/           # Optional: data files, templates
```

## Security

- **Never** commit API keys, tokens, or passwords
- Use placeholder values like `YOUR_API_KEY` with TODO comments
- Run a secret scan before committing: check for patterns like `sk-`, `ghp_`, `token=`, `secret=`

## Validation

```bash
make validate    # Check SKILL.md frontmatter
make list        # List all skills
```
