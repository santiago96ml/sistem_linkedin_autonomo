# Tasks: voyager-api-capture

## Phase 1: Implementation
- [x] 1.1 Update `leadlinked_fusion/autonomous_voyager_commenter.py` to use GraphQL mutation format for comments. <!-- id: 0 -->
  - Inject `fetch` mutation with `queryId: voyagerSocialDashComments.afec6d88d7810d45548797a8dac4fb87`.
  - Include headers: `csrf-token`, `x-restli-protocol-version: 2.0.0`, and `x-li-track`.
- [x] 1.2 Update `leadlinked_fusion/voyager_injector.py` to align with the GraphQL injection strategy for cross-script consistency. <!-- id: 1 -->
- [x] 1.3 Implement reaction (like) functionality in `leadlinked_fusion/autonomous_voyager_commenter.py`. <!-- id: 2 -->
  - Inject `fetch` mutation with `queryId: voyagerSocialDashReactions.b731222600772fd42464c0fe19bd722b`.

## Phase 2: Verification
- [x] 2.1 Verify successful comment submission (Status 200/201) by checking the response of the injected `fetch` call in `leadlinked_fusion/autonomous_voyager_commenter.py`. <!-- id: 3 -->
- [x] 2.2 Verify successful reaction submission (Status 200/201) by checking the response of the injected `fetch` call. <!-- id: 4 -->
- [x] 2.3 Perform a realistic E2E test: Navigate to a LinkedIn post, execute a comment injection, and confirm visibility in the DOM. <!-- id: 5 -->
- [x] 2.4 Confirm dynamic extraction and usage of `csrf-token` and `JSESSIONID` from browser cookies. <!-- id: 6 -->

### Next Step
Ready for implementation (sdd-apply).
