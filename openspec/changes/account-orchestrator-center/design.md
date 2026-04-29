# Design: Account Orchestrator Center

## Architecture
```
[ Next.js Dashboard ] <-> [ FastAPI Backend ] <-> [ SQLite/PostgreSQL ]
                                  |
                        [ Playwright Worker Pool ]
                                  |
                        [ LinkedIn Voyager API ]
```

## Database Schema
- **Accounts**: `id`, `name`, `proxy_url`, `storage_state` (JSONB), `status`.
- **Missions**: `id`, `account_id`, `status` (queued, active, success, failed), `tasks` (JSON).
- **Logs**: `id`, `mission_id`, `message`, `timestamp`.

## UI/UX
- **Dashboard**: "Command Center" feel. Dark mode, terminal-style logs.
- **Account Cards**: Show status (Online/Offline/Restricted).
- **Mission Builder**: Drag-and-drop or simple form to sequence actions.
