# Skill Registry

## User Skills
| Name | Description | Trigger |
|------|-------------|---------|
| `branch-pr` | PR creation workflow following issue-first enforcement. | PR creation, opening PRs. |
| `issue-creation` | Standardized issue creation and approval workflow. | Creating GitHub issues, bug reports. |
| `go-testing` | Go testing patterns including Bubbletea TUI testing. | Writing Go tests, adding coverage. |
| `judgment-day` | Parallel adversarial review protocol with dual judges. | "judgment day", "review adversarial". |
| `skill-creator` | Creates new AI agent skills following the spec. | "create a new skill", add instructions. |

## Compact Rules

### `branch-pr`
- Link approved issue (`Closes #N`).
- Exactly one `type:*` label.
- Branch format: `type/description`.
- Conventional Commits: `type(scope): description`.

### `issue-creation`
- Use templates (Bug/Feature) only.
- Approval: Issues start as `status:needs-review`. MUST get `status:approved` before PR.
- Required fields: Reproduction steps (bugs), Proposed solution (features).

### `go-testing`
- Use table-driven tests for functions.
- TUI: Test `Model.Update()` directly or use `teatest`.

### `judgment-day`
- Parallel Review: TWO blind judge sub-agents in parallel.
- Classification: `WARNING (real)` (blocks) vs `WARNING (theoretical)` (INFO only).
- Iterative: Fix & re-judge cycle (max 2 rounds before escalation).

### `skill-creator`
- Structure: `SKILL.md` (required), `assets/`, `references/`.
- Content: Critical patterns first, minimal code examples, copy-paste commands.
