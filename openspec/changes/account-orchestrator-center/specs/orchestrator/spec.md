# Spec: Account Orchestrator

## Requirements
- **Account Storage**: Must persist `JSESSIONID` and `li_at` cookies in `storageState` format.
- **StorageState Rotation**: Automatically refresh state when a 401/403 is detected.
- **Mission Queue**: FIFO queue for missions per account.
- **Failure Handling**: Exponential backoff for network errors; skip mission if account is restricted.

## Scenarios
### Scenario 1: Adding a new account
1. User provides login credentials or `storageState` JSON.
2. System validates connection to LinkedIn.
3. System saves account to DB with unique proxy.

### Scenario 2: Running a Commenting Mission
1. System selects account.
2. System launches Playwright with specific `storageState` and `proxy`.
3. System navigates to target post.
4. System executes `autonomous_voyager_commenter.py` logic (Like then GraphQL Comment).
5. System logs result and closes context.
