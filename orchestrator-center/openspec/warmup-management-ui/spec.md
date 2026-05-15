# Specification: Warmup Management System

## 1. Trust Levels & Rules

| Phase | Days | Daily Invites | Profile Visits | Comments/Likes | Max Total Actions |
|-------|------|---------------|----------------|----------------|-------------------|
| 1     | 1-14 | 0 (Manual)    | 0              | 15 Likes       | 20                |
| 2     | 15-30| 10-15         | 20-30          | 5 Comments     | 50                |
| 3     | 31-60| 20-25         | 40-50          | 10 Comments    | 100               |
| 4     | 61-90| 30-35         | 60-80          | 15 Comments    | 130               |
| 5     | 91+  | 50 (Max)      | 100            | 25 Comments    | 150               |

## 2. Core Logic

### 2.1 The "10-Day Rule"
- Activity is monitored in 10-day windows.
- If a window has 10 days of continuous activity without flags, the account moves to the next Trust Level.
- If a flag (restriction/error) occurs, the count resets.

### 2.2 Global Circuit Breaker
- Every action (Visit, Like, Comment, DM, Connection) is logged in `DailyActionLog`.
- Before executing any task, the orchestrator checks `SUM(actions) WHERE date = TODAY`.
- If `SUM >= 150`, the task is rejected with `SAFETY_LIMIT_REACHED`.

### 2.3 Higiene Bot
- Runs every Monday at 02:00.
- Navigates to `https://www.linkedin.com/mynetwork/invitation-manager/sent/`.
- Scans for invitations sent > 21 days ago.
- Withdraws them until `pending_count < 500`.

### 2.4 VIP Sentry
- Polling interval: Every 15 minutes.
- Accounts check notifications for specific `vip_profile_ids`.
- Priority: 1. Like, 2. AI-generated Comment based on Personality.

## 3. Data Schema

### Table: WarmupConfig
- `account_id` (FK)
- `niche` (string): Industry focus.
- `personality` (text): Tone/Style instructions for LLM.
- `vip_profiles` (text): JSON list of LinkedIn IDs to monitor.
- `start_date` (datetime): When warmup began.
- `current_trust_level` (int): 1-5.
- `last_higiene_run` (datetime).

### Table: DailyActionLog
- `account_id` (FK)
- `action_type` (string): 'VISIT', 'LIKE', 'COMMENT', 'DM', 'CONNECTION'.
- `timestamp` (datetime).
