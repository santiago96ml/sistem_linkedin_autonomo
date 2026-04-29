# Proposal: Account Orchestrator Center

## Overview
A centralized command center to orchestrate multiple LinkedIn identities. Each account operates in its own isolated environment, receiving missions (sequences of actions) from the dashboard.

## Scope
- **Account Management**: Add/Edit/Delete accounts with specific proxy and authentication state.
- **Mission Engine**: Define sequences of tasks (e.g., Like -> Comment -> Follow).
- **Monitoring**: Real-time status of each account and mission.
- **Security**: Automated `csrf-token` and cookie management using the Voyager GraphQL pattern discovered.

## Success Criteria
- 10+ accounts running missions simultaneously without leakage.
- Dashboard showing real-time logs for each action.
- Automatic recovery from browser crashes or network errors.
