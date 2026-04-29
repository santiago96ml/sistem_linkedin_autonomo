# Exploration: Account Orchestrator Center

## Goal
Develop a central dashboard to manage multiple LinkedIn accounts, assign tasks (missions), and track execution using isolated browser contexts.

## Multi-Account Management
- **Playwright Context Isolation**: Use `BrowserContext` for each account to ensure zero cookie/cache leakage.
- **Session Persistence**: Store `storageState` (JSON) for each account in a local database (SQLite/PostgreSQL).
- **Proxy Support**: Each context will be configured with a specific proxy (HTTP/SOCKS5) to avoid IP-based account flagging.

## Architecture Proposal
- **Frontend**: Next.js 14 (App Router) + Tailwind CSS + shadcn/ui + Lucide Icons.
- **Backend**: FastAPI (Python). High performance, async support for Playwright.
- **Task Worker**: Celery or simple `asyncio` background tasks to manage concurrent Playwright instances.

## Risks
- LinkedIn detection: Patterns of activity.
- Resource usage: High CPU/RAM for headless browsers.
- Token/Cookie expiry.
