# Fix Hydration Mismatch Error (Dark Reader)

## TL;DR

> **Quick Summary**: Fix hydration mismatch caused by Dark Reader browser extension injecting attributes into Lucide icons.
>
> **Deliverables**:
> - Create `Icon` wrapper component with `suppressHydrationWarning`
> - Replace all lucide-react icon usages across the frontend
>
> **Estimated Effort**: Short (~15 min)
> **Parallel Execution**: NO - sequential
> **Critical Path**: Create Icon.tsx → Update page.tsx → Update components

---

## Context

### Original Request
User reported hydration mismatch error in Next.js frontend caused by Dark Reader extension injecting `data-darkreader-inline-stroke` and `style={{--darkreader-inline-stroke:"currentColor"}}` attributes into SVG elements rendered by lucide-react icons.

### Error Analysis
- **Error**: `A tree hydrated but some attributes of the server rendered HTML didn't match the client properties`
- **Root Cause**: Browser extension (Dark Reader) modifies SVGs client-side after SSR
- **Affected Elements**: All Lucide icon components (Zap, Activity, Terminal, Users, etc.)
- **Solution**: Use `suppressHydrationWarning` on SVG elements

### Metis Review
- **Gap 1**: Need to handle both default and named lucide-react exports
- **Gap 2**: Some view components also use icons (will need updates)
- **Resolution**: Create centralized Icon wrapper + update all usages

---

## Work Objectives

### Core Objective
Eliminate hydration mismatches by adding `suppressHydrationWarning` to all SVG elements rendered by lucide-react icons.

### Concrete Deliverables
- File: `orchestrator-center/frontend/src/components/Icon.tsx` - wrapper component
- File: `orchestrator-center/frontend/src/app/page.tsx` - updated icon imports/usages
- Files: All view components using lucide icons

### Definition of Done
- [ ] No hydration mismatch console errors when Dark Reader is active
- [ ] All icons render correctly both SSR and client-side

### Must Have
- `Icon` wrapper component that passes props to lucide icons
- `suppressHydrationWarning` attribute on the underlying SVG element
- All page.tsx icon usages updated

### Must NOT Have
- No manual `suppressHydrationWarning` on individual icons (use wrapper)
- No removal of icon functionality

---

## Verification Strategy

### QA Policy
Every task includes agent-executed QA scenarios.

**Frontend/UI Verification:**
```
Scenario: Hydration test with Dark Reader
  Tool: playwright
  Preconditions: Dark Reader extension enabled in browser
  Steps:
    1. Navigate to http://localhost:3000
    2. Open browser console
    3. Check for hydration mismatch warnings
  Expected Result: No hydration mismatch errors in console
  Evidence: .sisyphus/evidence/hydration-fix-test.png
```

---

## Execution Strategy

### Sequential Execution (Wave 1)
```
1. Create Icon.tsx component
2. Update page.tsx to use Icon wrapper
3. Check view components for icon usage
4. Update any view components using icons
```

### Dependency Matrix
- Task 1 (Icon.tsx): Independent - can start immediately
- Task 2 (page.tsx): Depends on Task 1
- Task 3 (check components): Independent - can start in parallel with Task 1
- Task 4 (update components): Depends on Task 3

---

## TODOs

- [ ] 1. **Create Icon.tsx wrapper component**

  **What to do**:
  - Create `orchestrator-center/frontend/src/components/Icon.tsx`
  - Import lucide-react icons
  - Create `Icon` component that wraps lucide icons with `suppressHydrationWarning`
  - Re-export commonly used icons for convenience

  **Must NOT do**:
  - Don't modify lucide-react source

  **Recommended Agent Profile**:
  > - **Category**: `quick` - simple component creation
  > - **Skills**: []
  > - **Reason**: Straightforward component wrapper

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Blocks**: Tasks 2, 3, 4

  **References**:
  - `orchestrator-center/frontend/src/app/page.tsx:1-20` - Current icon imports pattern
  - React docs: `suppressHydrationWarning` attribute behavior

  **Acceptance Criteria**:
  - [ ] File created at correct path
  - [ ] Component accepts icon, size, color, className props
  - [ ] `suppressHydrationWarning` attribute passed to SVG

  **QA Scenarios**:
  ```
  Scenario: Icon component renders correctly
    Tool: Bash (node)
    Preconditions: Dev server running
    Steps:
      1. Import Icon component in a test file
      2. Render with a lucide icon
      3. Check that SVG has suppressHydrationWarning attribute
    Expected Result: SVG element contains suppressHydrationWarning
    Evidence: .sisyphus/evidence/icon-component-test.js
  ```

  **Commit**: YES
  - Message: `fix(frontend): add Icon wrapper with suppressHydrationWarning`
  - Files: `src/components/Icon.tsx`

---

- [ ] 2. **Update page.tsx to use Icon wrapper**

  **What to do**:
  - Import `Icon` from `@/components/Icon`
  - Replace direct icon usages with `<Icon icon={IconName} ...>` pattern
  - Maintain all existing props (size, className, etc.)

  **Must NOT do**:
  - Don't change any visual styling or behavior

  **Recommended Agent Profile**:
  > - **Category**: `quick` - find and replace pattern
  > - **Skills**: []
  > - **Reason**: Simple prop transformation

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Depends on**: Task 1 (Icon.tsx)
  - **Blocks**: None

  **References**:
  - `orchestrator-center/frontend/src/app/page.tsx:131-143` - SidebarItem component
  - `orchestrator-center/frontend/src/app/page.tsx:160, 169-176` - Icon usages in sidebar
  - `orchestrator-center/frontend/src/app/page.tsx:209-214` - Header icons
  - `orchestrator-center/frontend/src/app/page.tsx:225-226` - Plus button icon

  **Acceptance Criteria**:
  - [ ] All `<Zap ... />` → `<Icon icon={Zap} ... />`
  - [ ] All `<Activity ... />` → `<Icon icon={Activity} ... />`
  - [ ] All `<Users ... />` → `<Icon icon={Users} ... />`
  - [ ] All icons maintain their original props and styling

  **QA Scenarios**:
  ```
  Scenario: Page renders with Icon wrapper
    Tool: playwright
    Preconditions: App running at localhost:3000
    Steps:
      1. Navigate to http://localhost:3000
      2. Check sidebar renders with all navigation icons
      3. Check header shows Users and Activity icons
    Expected Result: All icons visible and styled correctly
    Evidence: .sisyphus/evidence/page-icons-test.png
  ```

  **Commit**: YES
  - Message: `fix(frontend): use Icon wrapper for lucide icons in page.tsx`
  - Files: `src/app/page.tsx`

---

- [ ] 3. **Check and update view components for icon usage**

  **What to do**:
  - Search for lucide-react icon usage in all view components
  - Update each component to use Icon wrapper where applicable
  - Check: DashboardView, AccountsView, MissionsView, CommandCenterView, etc.

  **Must NOT do**:
  - Don't change functionality of the views

  **Recommended Agent Profile**:
  > - **Category**: `quick` - find/replace across files
  > - **Skills**: []
  > - **Reason**: Pattern-based updates

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Tasks 1, 2)
  - **Blocks**: None (informational for awareness)

  **References**:
  - `orchestrator-center/frontend/src/components/views/*.tsx` - All view components
  - `orchestrator-center/frontend/src/components/*.tsx` - Other components

  **Acceptance Criteria**:
  - [ ] All lucide icons in view components use Icon wrapper (if they exist)
  - [ ] No hydration warnings from view components

  **QA Scenarios**:
  ```
  Scenario: View components render without hydration errors
    Tool: playwright
    Preconditions: Navigate through all views
    Steps:
      1. Navigate to each view tab in the sidebar
      2. Check console for hydration errors after each navigation
    Expected Result: No hydration errors on any view
    Evidence: .sisyphus/evidence/all-views-test.png
  ```

  **Commit**: YES (if changes needed)
  - Message: `fix(frontend): use Icon wrapper in view components`
  - Files: Updated view components

---

## Final Verification Wave (MANDATORY)

- [ ] F1. **Hydration Test** — Verify no console errors
- [ ] F2. **Visual Test** — All icons visible and styled correctly

---

## Commit Strategy
- Message: `fix(frontend): resolve hydration mismatch from Dark Reader extension`
- Files: `src/components/Icon.tsx`, `src/app/page.tsx`, view components

---

## Success Criteria

### Verification Commands
```bash
# Start dev server
cd orchestrator-center/frontend && npm run dev

# Check console for hydration errors (should be empty)
# Browser console should show no hydration warnings
```

### Final Checklist
- [ ] `Icon.tsx` created with `suppressHydrationWarning` propagation
- [ ] All icons in `page.tsx` use `Icon` wrapper
- [ ] No hydration mismatch console errors