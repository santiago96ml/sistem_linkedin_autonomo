# Mission Control Specification

## Purpose
Allow users to create and monitor automated LinkedIn tasks.

## Requirements

### Requirement: Mission Creation
The system MUST allow users to select an active identity and specify a task to execute.

#### Scenario: Launching a comment mission
- GIVEN the user is in the Missions view
- WHEN the user selects an account and enters a Post URL and Comment text
- AND clicks "Execute Mission"
- THEN the system MUST send a POST request to `/missions/`
- AND show a success notification if the mission is queued.

### Requirement: Mission Status Tracking
The system SHOULD display the status of recent missions (Pending, Running, Completed, Failed).

#### Scenario: Monitoring mission progress
- GIVEN there is a running mission
- WHEN the system polls the backend
- THEN the mission status in the list MUST update automatically.
