# Independent battle playback review

Accepted within the requested modal lifetime, input, save/result safety, and architectural scope. No additional actionable finding. Reviewed committed bd05c08dcca32e8399c05230fd927e1643709405 and the complete delta to final frozen a27c4739c413b4c0b48c3a928ac739aea7b3f2b6.

## Verified

- At bd05c08, 17 existing trace/playback tests passed, plus seven independent public-input lifecycle checks.
- At final a27c473, all 25 tests (18 existing trace/playback tests plus seven independent lifecycle checks) passed in 11.32 seconds in an isolated worktree.
- Both E and A produce the same complete authoritative State as the public model command. During the modal, all ordinary tactical keys and every board-cell click leave that resolved State exact. Finish followed by queued A/E/T/Enter inputs does not leak another order into the revealed scene.
- Loading an older pre-win manual save during terminal playback destroys the entire previous scene stack. Advancing the game by 30 seconds cannot later publish a stale result or reward. Winning again and batching Finish/Continue keys settles once.
- Guide → Save & title during playback saves the resolved but unaccepted result. The playback stays paused beneath the guide/save browser, disappears on Title, and F9 restores exactly the pending result; accepting it settles once.
- Three genuine historical battle fixtures (v4 Brace, v10 pinned extraction, v12 pre-Relief Grove) were driven through A and natural playback ticks to completion. Every tick retained the exact expected complete State, and each playback completed within its bound.
- Final F5 acknowledgment regression passes: after a real autosave failure and successful manual save, Finish carries the current message to the parent battle, and the manual file contains the authoritative resolved state.
- Read the final moving-actor layer delta. It uses the existing screen_layer context and preserves the ordinary battle's layer 0/1 behavior; animated actors use layer 2/3. Native appearance is owned by root/production agent and was not visually verified in this review.

## Architecture

The BattleScene subclass reuses the board, objective and reading UI while replacing the command area and phase button. Its closed controls, disabled tactical buttons and top-only input dispatch keep presentation read-only. The existing scene stack supplies pause, queued-input isolation, replacement, and lifetime cleanup; the visual clock has no detached timer or persistent queue. The authoritative Battle remains in root.state, while the modal owns a separate visual Battle copy reconstructed from immutable trace frames. Save/load consistently targets root.state. No framework primitive, combat rule, AI or schema addition is justified or introduced for this playback.

## Limits and artifacts

This is code/public-command review of the exact revisions above. It is not full-suite, fuzz, packaged-build, native rendering, frame-time, human comprehension, or human playtest approval. Those checks remain with the owner/root. Known full-suite driver adjustments were read; their drivers use the real visible Finish command and preserve original assertions.

Independent checks: /tmp/review_playback_lifecycle.py
Isolated checkout (clean, final a27c473): /tmp/saga2d-playback-review-bd05c08
No edits were made to production source or the owner's worktree.
