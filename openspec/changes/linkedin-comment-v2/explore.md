# Exploration Report: LinkedIn Comment Failure & "Triple Vía" Design

**Change**: `linkedin-comment-v2`
**Status**: Completed
**Date**: 2026-04-27

## 1. Root Cause Analysis
The current implementation in `leadlinked_fusion/actions/like_post.py` fails due to:
- **Focus Instability**: The `Tab + Space` sequence is easily interrupted by dynamic LinkedIn UI elements (e.g., "Post with AI" tooltips).
- **Static Offsets**: Clicking with fixed offsets (e.g., `+30, +10`) fails when the comment box expands vertically, shifting the "Post" button out of reach.
- **False Positives**: The "ADN Scan" for the name "Santiago" in the full HTML is too broad and doesn't guarantee the comment was *persisted* for others to see.

## 2. Proposed Design: "Triple Vía de Envío"
To ensure 100% submission success, we will implement three redundant layers:

### Vía 1: Native Keyboard Shortcut (`Control+Enter`)
- **Action**: `page.keyboard.press("ControlOrMeta+Enter")`
- **Why**: Bypasses the need for focus navigation and triggers LinkedIn's internal React event directly.

### Vía 3: Precise DOM Interaction (Hardware Click)
- **Action**: Direct click on `button.comments-comment-box__submit-button:not(:disabled)`.
- **Why**: Simulates a physical mouse event on the specific button, ensuring state synchronization.

### Vía 3: Dynamic Coordinate Fallback
- **Action**: Calculate coordinates relative to the *bottom-right* of the parent container `.comments-comment-box`, not just the editor.
- **Why**: Handles cases where the button might be hidden behind a layer but still clickable via coordinates.

## 3. Verification Strategy (The "Open Code" Proof)
Instead of just checking if the box is empty, we will implement:
1. **Empty Editor Check**: Ensure the textbox is cleared.
2. **Comment List Scan**: Wait for a new element with class `.comments-comment-item` that contains the specific text sent.
3. **Session Persistence**: Re-check after a brief refresh or URN navigation to ensure the server-side save was successful.

## 4. Risks & Mitigations
- **Risk**: Bot detection on rapid `Control+Enter`. 
- **Mitigation**: Add a random "human pause" (1.5s - 3s) between typing and sending.
