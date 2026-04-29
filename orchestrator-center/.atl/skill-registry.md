# Skill Registry — orchestrator-center

This registry tracks available AI skills and project-specific conventions.

## Project Conventions

### Next.js Agent Rules
From: `frontend/AGENTS.md`
> This is NOT the Next.js you know. This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.

## User Skills

| Skill | Trigger |
|-------|---------|
| branch-pr | Creating a PR, opening a PR, preparing changes for review |
| go-testing | Writing Go tests, using teatest, adding test coverage |
| issue-creation | Creating a GitHub issue, reporting a bug, requesting a feature |
| judgment-day | "judgment day", "review adversarial", "dual review", "doble review", "juzgar", "que lo juzguen" |
| skill-creator | Creating a new skill, adding agent instructions, documenting patterns |

## Compact Rules

### Next.js 16 / React 19
- APIs and file structures may differ from training data.
- Read `node_modules/next/dist/docs/` for specific version guidance.
- Heed all deprecation notices.
