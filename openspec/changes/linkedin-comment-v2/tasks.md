# Tasks: linkedin-comment-v2

- [ ] **Setup**: Ensure the environment is ready and `fresh_cookies.json` is available. <!-- id: 0 -->
- [ ] **Refactor `like_post.py`**: <!-- id: 1 -->
    - [ ] Implement `submit_comment_triple_via` helper with the 3 tiers (Control+Enter, Submit Button Click, Dynamic Coordinate Click). <!-- id: 2 -->
    - [ ] Implement `verify_comment_presence` with DOM scanning to confirm the comment exists in the feed. <!-- id: 3 -->
    - [ ] Update `like_profile_post` to integrate the new robust logic and logging. <!-- id: 4 -->
- [ ] **Update `demo_fabio_comment.py`**: <!-- id: 5 -->
    - [ ] Standardize the cookie loading logic to use the relative path `results/fresh_cookies.json`. <!-- id: 6 -->
    - [ ] Update the test prompt for the agent to use the new robust flow. <!-- id: 7 -->
- [ ] **Testing & Verification**: <!-- id: 8 -->
    - [ ] Run a test to verify the comment is correctly posted and detected. <!-- id: 9 -->
    - [ ] Check logs for "Triple Vía" step execution to ensure fallback logic works if needed. <!-- id: 10 -->
