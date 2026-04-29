# Proposal: Voyager API Capture Migration to GraphQL

## Intent
LinkedIn has migrated social actions (likes, comments) to a GraphQL-based architecture (`/voyager/api/graphql`). The current legacy endpoints (`/voyager/api/socialActions`) used in `autonomous_voyager_commenter.py` are intercepted by ServiceWorkers or deprecated, causing injection failures. This change migrates the system to the current GraphQL architecture to ensure reliability and bypass interception.

## Scope

### In Scope
- Migration of comment injection logic to GraphQL mutations.
- Implementation of `x-li-track` and `csrf-token` header handling.
- Support for reaction (like) actions via GraphQL.
- Updates to `leadlinked_fusion/autonomous_voyager_commenter.py`.

### Out of Scope
- Full refactor of the `leadlinked_fusion` project.
- Handling of multiple account logins (stays single account for now).

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- **voyager-commenting**: Transition from legacy REST to GraphQL mutations using `action=execute`.
- **voyager-reactions**: Transition from legacy REST to GraphQL mutations for post reactions.

## Approach
Implement **GraphQL Injection** by updating the Playwright injection script to use `fetch` targeting `https://www.linkedin.com/voyager/api/graphql`.
- **Token Extraction**: Dynamically extract `csrf-token` from the `JSESSIONID` cookie.
- **QueryID Usage**:
    - Comments: `voyagerSocialDashComments.afec6d88d7810d45548797a8dac4fb87`
    - Reactions: `voyagerSocialDashReactions.b731222600772fd42464c0fe19bd722b`
- **Headers**: Include `x-restli-protocol-version: 2.0.0` and a valid `x-li-track` base64 tracking header.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `leadlinked_fusion/autonomous_voyager_commenter.py` | Modified | Update `fetch` logic, headers, and payload structure. |
| `leadlinked_fusion/voyager_injector.py` | Modified | Ensure injection strategy matches GraphQL requirements. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| QueryID Rotation | Medium | Implement dynamic hash detection if possible or maintain an easily updatable config. |
| Stealth/Detection | Low | Use valid `x-li-track` headers and browser-consistent user agents. |

## Rollback Plan
Revert changes in `autonomous_voyager_commenter.py` to the previous version using Git.

## Success Criteria
- [ ] Comment successfully posted via GraphQL injection with status 201/200.
- [ ] Reaction (like) successfully applied via GraphQL injection.
- [ ] Correct CSRF and tracking headers verified in outgoing requests.
