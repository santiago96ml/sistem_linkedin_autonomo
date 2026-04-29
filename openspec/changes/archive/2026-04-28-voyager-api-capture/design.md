# Design: Voyager API Capture Migration to GraphQL

## Technical Approach
Implement **GraphQL Mutation Injection** using Playwright's `page.evaluate`. This strategy leverages the browser's active session state (cookies, tracking tokens, and fingerprinting) to execute social actions via the current LinkedIn GraphQL API (`/voyager/api/graphql`).

## Architecture Decisions

### Decision: Browser-Based Fetch Injection
**Choice**: Use `page.evaluate` to execute `fetch` requests within the LinkedIn context.
**Alternatives considered**: Direct Python `requests` or `aiohttp`.
**Rationale**: Direct API calls from Python would require precise replication of complex tracking headers (`x-li-track`) and session synchronization. Browser injection automatically handles these, significantly reducing detection risk and implementation complexity.

### Decision: GraphQL Execution Pattern
**Choice**: Use the `action=execute` pattern with specific `queryId` hashes.
**Alternatives considered**: Traditional REST endpoints.
**Rationale**: LinkedIn has moved most interactive social features to GraphQL mutations. The `action=execute` endpoint is the current standard for comments and reactions.

## Data Flow
The system follows a three-tier execution flow:
1. **Python Orchestration**: `autonomous_voyager_commenter.py` manages the browser lifecycle.
2. **Browser Context**: Playwright navigates to the target post and extracts the `csrf-token` from cookies.
3. **GraphQL Execution**: A JavaScript `fetch` mutation is injected and executed, returning the status to Python.

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `leadlinked_fusion/autonomous_voyager_commenter.py` | Modify | Update `page.evaluate` script to use GraphQL mutation format, add `x-li-track` header, and use correct `queryId`. |
| `leadlinked_fusion/voyager_injector.py` | Modify | Update to match the new GraphQL injection strategy for cross-script consistency. |

## Interfaces / Contracts

### GraphQL Comment Payload
```json
{
  "queryId": "voyagerSocialDashComments.afec6d88d7810d45548797a8dac4fb87",
  "action": "execute",
  "variables": {
    "input": {
      "commentary": { "text": "COMMENT_TEXT" },
      "commentedOn": "URN",
      "socialAction": "URN"
    }
  }
}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Integration | GraphQL Injection | Verify 200/201 response from the injected `fetch` call. |
| E2E | Visibility | Navigate to the post after injection and verify the comment appears in the DOM. |

## Migration / Rollout
No data migration required. This is a behavioral update to existing automation scripts.
