# Exploration: Voyager API Capture

## Current State
LinkedIn has migrated its social actions (likes, comments, etc.) from the legacy `voyager/api/socialActions` endpoint to a **GraphQL-based** architecture using the `voyager/api/graphql` endpoint. The current `autonomous_voyager_commenter.py` fails because it looks for the old endpoint and is bypassed by LinkedIn's ServiceWorkers.

## Affected Areas
- `leadlinked_fusion/autonomous_voyager_commenter.py` — Needs to be updated to use GraphQL endpoints and new header requirements.
- `leadlinked_fusion/voyager_injector.py` — Likely needs similar updates for consistency.

## Approaches

1. **GraphQL Injection (Recommended)** — Update the system to use the new `voyager/api/graphql` endpoint with the correct `queryId` and `x-li-track` headers.
   - Pros: Highly reliable, matches current LinkedIn architecture, avoids ServiceWorker interception issues if implemented correctly via browser injection or direct API.
   - Cons: Requires identifying specific `queryId` hashes for different actions.
   - Effort: Medium

2. **DOM-Level Automation (Fallback)** — Rely solely on clicking and typing via Playwright without direct API injection.
   - Pros: Simplest to implement, very "human-like".
   - Cons: Slower, more fragile to UI changes (e.g. comment box not loading).
   - Effort: Low

## Technical Details Captured
- **Endpoint**: `https://www.linkedin.com/voyager/api/graphql`
- **Headers**:
    - `csrf-token`: Matches `JSESSIONID` cookie.
    - `x-restli-protocol-version`: `2.0.0`
    - `x-li-track`: Base64 metadata (e.g. `{"clientVersion":"...","osName":"..."}`)
- **QueryIDs**:
    - Reactions: `voyagerSocialDashReactions.b731222600772fd42464c0fe19bd722b`
    - Comments (Load): `voyagerSocialDashComments.afec6d88d7810d45548797a8dac4fb87`

## Recommendation
Implement **Approach 1 (GraphQL Injection)**. It provides the best balance of speed and reliability while allowing us to bypass some of the UI's flakiness.

## Risks
- **Hash Rotation**: LinkedIn may rotate `queryId` hashes, requiring a way to detect them dynamically or update them frequently.
- **Stealth**: Direct API calls must include valid `x-li-track` and other fingerprinting headers to avoid detection.

## Ready for Proposal
Yes. The capture was successful and we have the necessary data to design a robust injector.
