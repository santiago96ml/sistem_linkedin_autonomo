# Identity Linking Specification

## Purpose
Securely link LinkedIn accounts to the orchestrator using a guided wizard.

## Requirements

### Requirement: 2FA Guided Flow
The system MUST handle the transition from login credentials to 2FA challenge.

#### Scenario: 2FA verification success
- GIVEN the user has entered valid credentials
- WHEN the backend returns `2fa_required`
- THEN the wizard MUST show the 2FA input screen
- AND upon submitting a valid code, it MUST show the "Success" screen.

### Requirement: Account persistence
Newly linked accounts MUST be persisted and displayed in the Accounts view immediately after success.

#### Scenario: Automatic refresh
- GIVEN a user successfully links an account
- WHEN the wizard closes
- THEN the system MUST refresh the accounts list from `/accounts/`.
