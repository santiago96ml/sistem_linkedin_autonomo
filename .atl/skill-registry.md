# Skill Registry

## User Skills
| Name | Description | Trigger |
|------|-------------|---------|
| `branch-pr` | PR creation workflow following issue-first enforcement. | PR creation, opening PRs. |
| `issue-creation` | Standardized issue creation and approval workflow. | Creating GitHub issues, bug reports. |
| `fastapi-standard` | FastAPI backend patterns for this project. | Python files, FastAPI routes. |
| `nextjs-react` | Frontend patterns for the Next.js dashboard. | Next.js components, React hooks. |
| `pytest-tdd` | Strict TDD patterns using pytest. | Writing tests, Python bugfixes. |
| `judgment-day` | Parallel adversarial review protocol with dual judges. | "judgment day", "review adversarial". |

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

### `fastapi-standard`
- Use Pydantic models for request/response validation.
- Dependency injection for database sessions.
- Async endpoints for all I/O bound operations.

### `nextjs-react`
- Use App Router (if applicable) or standardized View architecture.
- Controlled components for all inputs.
- Tailwind CSS for styling (Vanilla CSS for core system).

### `pytest-tdd`
- **STRICT TDD MODE**: Write failing test first.
- Use `pytest-asyncio` for async routes.
- Mock external APIs (Muapi.ai, etc.).

### `judgment-day`
- Parallel Review: TWO blind judge sub-agents in parallel.
- Classification: `WARNING (real)` (blocks) vs `WARNING (theoretical)` (INFO only).
- Iterative: Fix & re-judge cycle (max 2 rounds before escalation).
