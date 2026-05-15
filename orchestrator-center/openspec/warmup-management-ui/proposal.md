# Proposal: Account Warmup Management System (Warmup Lab)

## Goal
Implement a sophisticated multi-stage warmup system for LinkedIn accounts to maximize deliverability and prevent bans, based on a 120-day progressive trust-building protocol.

## Context & Research
Based on expert research, new LinkedIn accounts require a rigorous warmup phase to establish "human-like" biometrics. The protocol consists of:
- **Phase 1 (Day 1-14):** Manual-only behavior, low volume (5 invites/day, 15 likes).
- **Phase 2 (Day 15-30):** Light automation (10-15 invites, 20-30 profile visits).
- **Phase 3 (Day 60+):** Progressive scaling using the "10-day rule" (+5-10 actions every 10 days).
- **Phase 4 (Day 90-120):** Stable status (50 invites/day, 120/week).
- **Global Safety:** Max 150 total actions per 24h window.

## Proposed Features
1. **Warmup Lab Dashboard:** A dedicated UI view to monitor progress, trust scores, and health bars.
2. **AI Personality Engine:** Configure industry (rubro) and agent personality (tone, formal/informal) for coherent interaction.
3. **VIP Profile Monitoring:** High-priority notification tracking for specific influencers (e.g., Fabio Romero).
4. **Higiene Bot:** Automated withdrawal of pending invitations older than 3 weeks.
5. **Humanized Orchestration:** Random delays (15-45s) and realistic mouse/typing behavior.

## Technology Stack
- **Backend:** FastAPI, SQLAlchemy (SQLite), Playwright.
- **Frontend:** React (Next.js), Lucide Icons, TailwindCSS.
- **Persistence:** `WarmupConfig` and `DailyActionLog` tables.

## Success Criteria
- 0 shadowbans or restrictions during the 60-day window.
- Successful implementation of the 150-action "Circuit Breaker".
- Accurate "Health Bar" visualization in the UI.
