# Design: Warmup Management System

## 1. Database Schema (SQLite)

```sql
CREATE TABLE warmup_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    niche TEXT,
    personality TEXT,
    vip_profiles TEXT, -- JSON array
    start_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    current_trust_level INTEGER DEFAULT 1,
    last_higiene_run DATETIME,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);

CREATE TABLE daily_action_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_id INTEGER NOT NULL,
    action_type TEXT NOT NULL, -- 'LIKE', 'COMMENT', 'CONNECTION', 'VISIT', 'DM'
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(id)
);
```

## 2. API Endpoints (FastAPI)

- `GET /warmup/stats`: Aggregated health data for all accounts in warmup.
- `GET /warmup/config/{account_id}`: Retrieve configuration.
- `POST /warmup/config`: Create or update configuration.
- `GET /warmup/health/{account_id}`: Current 24h action count and progress.

## 3. UI Components

### WarmupView.tsx
- **Header:** Title "Warmup Lab" and global health status.
- **AccountGrid:** List of accounts currently in warmup.
- **WarmupCard:**
  - Circular Progress (Day X/120).
  - Health Bar (Action count / 150).
  - Trust Level badge.
  - "Quick Actions" (Edit personality, run hygiene).

### PersonalityEditor.tsx
- Modal to edit `niche` and `personality`.
- Prompt preview (how the LLM will see the instructions).

## 4. Orchestrator Integration

- `orchestrator.py` will include a `WarmupManager` class.
- `MissionRunner` will call `WarmupManager.record_action(account_id, type)` on every successful task.
- `MissionRunner` will check `WarmupManager.can_perform_action(account_id)` before starting.
