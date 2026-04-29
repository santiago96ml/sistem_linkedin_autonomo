# Live Telemetry Specification

## Purpose
Provide real-time feedback of backend activity and agent status.

## Requirements

### Requirement: Log Polling
The system MUST poll the `/logs/` endpoint every 5 seconds to retrieve the latest system messages.

#### Scenario: Real-time log stream
- GIVEN the Hub is open
- WHEN the poll interval is reached
- THEN the terminal view MUST append new logs from the backend
- AND auto-scroll to the latest entry.

### Requirement: System Status Indicator
The system MUST display an active "Nominal" status only if the last poll to `/` or `/accounts/` was successful.

#### Scenario: Connection loss detection
- GIVEN the backend goes offline
- WHEN a poll fails
- THEN the "SYSTEM STATUS" indicator MUST change to "Offline" (Red).
