# Design: Interface Logic Implementation

## Technical Approach

We will refactor the current monolithic `page.tsx` into a modular, view-based architecture. A central orchestrator state will be managed at the top level and synchronized with the backend via polling. This ensures the premium UI remains responsive while reflecting real-time data.

## Architecture Decisions

### Decision: View Modularization
**Choice**: Separate `Dashboard`, `Accounts`, `Missions`, and `Security` into standalone components.
**Alternatives considered**: Keeping everything in `page.tsx` with conditional rendering.
**Rationale**: `page.tsx` is already 500+ lines. Further adding mission logic will make it unmaintainable. Modularization improves clarity and testability.

### Decision: Real-time Data Sync
**Choice**: HTTP Polling every 5 seconds for logs and account status.
**Alternatives considered**: WebSockets or SSE.
**Rationale**: The current backend is purely REST-based. Adding WebSockets requires modifying the infrastructure. Polling is sufficient for monitoring LinkedIn missions and logs.

### Decision: State Management
**Choice**: Centralized state in `page.tsx` passed via props to views.
**Alternatives considered**: React Context or Zustand.
**Rationale**: The app state is relatively small (accounts, logs, status). Prop drilling is minimal (1 level), keeping the implementation simple and lightweight.

## Data Flow

```
[page.tsx (State + Polling)]
      │
      ├─→ [DashboardView] (Stats + Recent Activity)
      ├─→ [AccountsView] (Account Grid + Wizard)
      ├─→ [MissionsView] (Mission History + Task Creation)
      └─→ [SecurityView] (Security Logs + Proxy Status)

[API Polling Hook] ──GET /logs, /accounts─→ [FastAPI Backend]
[Action Handlers] ──POST /missions ───────→ [FastAPI Backend]
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/components/views/DashboardView.tsx` | Create | Overview stats and recent mission cards. |
| `frontend/src/components/views/AccountsView.tsx` | Create | Account grid and integration with the Wizard. |
| `frontend/src/components/views/MissionsView.tsx` | Create | Mission history table and "Launch Mission" form. |
| `frontend/src/components/views/SecurityView.tsx` | Create | Security-specific logs and system health. |
| `frontend/src/app/page.tsx` | Modify | Refactor to act as the view switcher and state manager. |
| `backend/main.py` | Modify | Add `/stats` endpoint for aggregate dashboard data. |

## Interfaces / Contracts

### New Backend Endpoint: `GET /stats`
```json
{
  "total_identities": 5,
  "active_missions": 12,
  "success_rate": 94,
  "system_status": "nominal"
}
```

### Frontend State Shape
```typescript
interface OrchestratorState {
  accounts: Account[];
  missions: Mission[];
  logs: LogEntry[];
  stats: {
    totalIdentities: number;
    activeMissions: number;
    successRate: number;
  };
  systemStatus: 'nominal' | 'offline';
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | State update logic | Test polling helper functions. |
| Integration | Tab switching | Verify correct view component renders on state change. |
| Manual | Mission launch | E2E test of creating a mission and seeing it in the list. |

## Migration / Rollout

No data migration required. Phased refactor:
1. Extract `AccountsView` (matches current UI).
2. Implement View Switcher.
3. Connect real backend stats.
4. Implement `MissionsView`.
