# Proposal: Interface Logic Implementation

## Intent

Implement the full internal logic for the Intelligence Hub dashboard. Currently, the UI is mostly static with mocked data and incomplete navigation. This change will connect the frontend to the FastAPI backend, enable real-time telemetry, and provide full control over accounts and missions.

## Scope

### In Scope
- **Component Refactoring**: Extracting views from `page.tsx` into dedicated components.
- **Dynamic Navigation**: Implementing the view switcher for Orchestrator, Accounts, Missions, and Security.
- **Real-time Telemetry**: Implementing polling for system logs and mission updates.
- **Mission Control**: UI for creating and monitoring LinkedIn missions (commenting, etc.).
- **Live Dashboard**: Connecting header stats (linked identities, active missions) to real backend data.

### Out of Scope
- **WebSockets**: We will use efficient polling for now to avoid backend infrastructure changes.
- **Advanced Analytics**: Detailed charts and historical data (will be part of future work).
- **Proxy Management**: Basic display only; full management is deferred.

## Capabilities

### New Capabilities
- `mission-control`: Interface to select an account and launch specific tasks (e.g., commenting).
- `live-telemetry`: Background polling and display of real-time system logs.

### Modified Capabilities
- `identity-linking`: Connecting the existing "Vincular Nueva Identidad" wizard to the real 2FA flow.
- `dashboard-analytics`: Replacing hardcoded stats with real data from `/accounts/` and `/missions/`.

## Approach

We will use a **Component-Based Refactoring** approach:
1.  **View Architecture**: `page.tsx` will act as a thin layout wrapper. Vistas like `DashboardView`, `AccountsView`, and `MissionsView` will be separated.
2.  **State Synchronization**: A central polling hook in the main layout will keep the accounts and logs in sync.
3.  **Action Flow**: Standardizing the `fetch` patterns for starting logins and missions.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/app/page.tsx` | Modified | Massive refactor to distribute logic. |
| `frontend/src/components/` | New | Creation of view-specific components. |
| `backend/main.py` | Modified | Minor additions for dashboard aggregate stats. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| API Latency | Low | Use optimistic UI updates and loading states. |
| Memory Leak in Polling | Low | Ensure `setInterval` is cleaned up on component unmount. |
| 2FA Timeout | Med | Provide clear feedback if the session expires during verification. |

## Rollback Plan

Revert `page.tsx` to the current static version. The backend changes are additive and won't break existing (simulated) flows.

## Success Criteria

- [ ] Navigation between tabs updates the main content area correctly.
- [ ] Logs in the terminal reflect real data from the database.
- [ ] New accounts added via the wizard appear immediately in the list.
- [ ] Users can trigger a "Comment" mission from the Missions view.
