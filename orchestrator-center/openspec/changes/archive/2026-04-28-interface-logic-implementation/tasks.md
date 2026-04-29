# Tasks: Interface Logic Implementation

## Phase 1: Foundation & State

- [x] 1.1 Create `frontend/src/hooks/useOrchestrator.ts` to manage accounts, missions, logs, and polling logic.
- [x] 1.2 Add `GET /stats` endpoint in `backend/main.py` for aggregate dashboard metrics.

## Phase 2: View Modularization

- [x] 2.1 Extract and create `frontend/src/components/views/DashboardView.tsx` from existing UI code.
- [x] 2.2 Extract and create `frontend/src/components/views/AccountsView.tsx` from existing UI code.
- [x] 2.3 Create `frontend/src/components/views/MissionsView.tsx` with mission history list.
- [x] 2.4 Create `frontend/src/components/views/SecurityView.tsx` with dedicated security logs.

## Phase 3: UI Integration & Wiring

- [x] 3.1 Refactor `frontend/src/app/page.tsx` to use the view switcher and centralized state.
- [x] 3.2 Connect the Onboarding Wizard success event to trigger an accounts list refresh.
- [x] 3.3 Implement 5-second polling interval for logs and account statuses.

## Phase 4: Mission Logic Implementation

- [x] 4.1 Add "Launch Mission" modal/form in `MissionsView` to trigger `/missions/` POST.
- [x] 4.2 Add mission status badges (Running, Completed, Failed) to the mission list.

## Phase 5: Verification

- [ ] 5.1 Verify that logs append in real-time in the terminal component.
- [ ] 5.2 Verify that clicking sidebar tabs updates the main content without page reload.
- [ ] 5.3 Test full 2FA linking flow with backend feedback.
