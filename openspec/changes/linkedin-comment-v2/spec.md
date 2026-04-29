# Specification: linkedin-comment-v2

## Requirements
- **Cookie Loading**: Must load session cookies from `leadlinked_fusion/results/fresh_cookies.json` at startup.
- **Typing Strategy**: Use `page.keyboard.type` with a `50ms` delay between keystrokes to mimic human behavior.
- **"Triple Vía" Submission Sequence**:
  1. **Primary**: Send `Control+Enter` shortcut while focused on the editor.
  2. **Secondary**: Identify and click the submit button using selector `button.comments-comment-box__submit-button:not(:disabled)`.
  3. **Tertiary**: Perform a hardware-level mouse click at coordinates calculated relative to the bottom-right corner of the `.comments-comment-box` container.
- **Verification**: 
  - Confirm the editor becomes empty after submission.
  - Search the DOM for a new `.comments-comment-item` element containing the exact text of the comment.

## Scenarios
- **Success**: The comment is visible in the DOM and the editor is cleared.
- **Partial Success**: The `Control+Enter` shortcut fails to submit, but the secondary button click succeeds.
- **Fallback Success**: Both primary and secondary methods fail, but the tertiary coordinate-based click results in a successful post.
- **Failure**: The editor is not found, or none of the three submission paths result in a visible comment in the DOM.

## Acceptance Criteria
- The comment must be verified as visible on LinkedIn before reporting success.
- The system must report failure if the comment is not found in the DOM, even if the UI actions seemed to complete.
