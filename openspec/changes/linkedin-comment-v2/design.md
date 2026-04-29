# Technical Design: LinkedIn Comment V2 - Triple Via Submission

## 1. Architecture
- **Target Files**: `leadlinked_fusion/actions/like_post.py` and `leadlinked_fusion/demo_fabio_comment.py`.
- **Core Strategy**: Implementation of a redundant submission loop (Triple Vía) with decoupled verification.
- **Workflow Enhancement**:
    1. **Initialization**: Ensure `fresh_cookies.json` is loaded to maintain session context.
    2. **Interaction**: Mimic human typing followed by a three-tiered submission attempt.
    3. **Confirmation**: Shift from state-checking (editor empty) to result-checking (DOM presence).

## 2. Component Design
### `submit_comment_triple_via(page: Page, editor: Locator, text: str) -> bool`
- **Tier 1 (Native)**: Focus the editor and trigger `page.keyboard.press("ControlOrMeta+Enter")`.
- **Tier 2 (Direct DOM)**: Locate the submit button using `.comments-comment-box__submit-button:not(:disabled)` and perform a hardware-level `click()`.
- **Tier 3 (Coordinate Fallback)**: Calculate the bounding box of the `.comments-comment-box` container and click 20px from the bottom-right corner.

### `verify_comment_presence(page: Page, text: str, timeout: int = 5000) -> bool`
- **Method**: Use a locator-based search for `.comments-comment-item` that contains the specific `text`.
- **Latency Handling**: Implement a `wait_for_selector` or a polling loop with the specified timeout to allow for network/server delay.

## 3. Implementation Details (Open Code)
- The logic will be implemented as a new helper function within `like_post.py` to keep the main `like_profile_post` function clean.
- We will add logging for each tier of the "Triple Vía" to facilitate debugging and "reverse engineering" transparency.

## 4. Integration & Testing
- **Script**: `demo_fabio_comment.py` will serve as the primary test bench.
- **Data**: Cookies will be injected into the Playwright context via `storage_state`.
