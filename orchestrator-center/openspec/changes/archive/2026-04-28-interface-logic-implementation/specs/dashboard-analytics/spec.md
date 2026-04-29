# Dashboard Analytics Specification

## Purpose
Provide a high-level overview of the orchestrator's health and activity.

## Requirements

### Requirement: Dynamic Stats Header
The system MUST display real counts of linked identities and active missions in the header.

#### Scenario: Header stats update
- GIVEN the user is on the Hub
- WHEN the accounts list is fetched
- THEN the header "Identities Linked" count MUST reflect the `accounts.length`.

### Requirement: Multi-view Navigation
The sidebar MUST allow switching between different specialized views without a full page reload.

#### Scenario: Switching to Missions view
- GIVEN the user is on the Dashboard
- WHEN the user clicks "Missions" in the sidebar
- THEN the main content area MUST update to show the Missions view
- AND the "Missions" sidebar item MUST show the active state.
