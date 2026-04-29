# Proposal: linkedin-comment-v2

## Intent
Implement a robust LinkedIn comment submission system using the "Triple Vía" strategy to ensure comments are successfully posted and persisted on LinkedIn's servers.

## Scope
- **`leadlinked_fusion/actions/like_post.py`**: Update `like_profile_post` to implement the new submission and verification logic.
- **`leadlinked_fusion/demo_fabio_comment.py`**: Ensure correct loading of `fresh_cookies.json` and update the test prompt to reflect the new capabilities.

## Approach
1. **Primary Submission (Vía 1)**: Use `Control + Enter` keyboard shortcut within the comment editor. This is the native LinkedIn command for submitting comments and is generally more reliable than manual navigation.
2. **Hardware Click Backup (Vía 2)**: If the shortcut fails to clear the editor, use a precise DOM selector (`.comments-comment-box__submit-button`) to locate and perform a real hardware click on the "Post" button.
3. **Dynamic Coordinate Fallback (Vía 3)**: As a final resort, calculate the button's position dynamically based on the editor's bounding box to perform a click in the expected area.
4. **Robust Verification**: Replace the "DNA scan" with a more specific verification step that scans the `.comments-comment-item` elements for the exact text posted, ensuring it is present in the DOM after the submission attempt.

## Session Setup
- All sessions must be initialized using `leadlinked_fusion/results/fresh_cookies.json` to maintain authentication state.
- Ensure the browser is launched with the correct `storage_state` derived from these cookies.
