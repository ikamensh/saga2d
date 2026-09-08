# Accepted shared-combat playback — 2026-09-08

Code: **6d6ac934245668807c1b2cea56f28a8b68a43be4**. This completes the
development PvP playback increment. The mode is still not selectable or packaged.

Both seats receive a bounded history of accepted shared tactical orders.
Help and other readers can remain open while orders arrive. Returning plays
the accumulated actions from the correct local perspective, then reconciles
the latest campaign state. Orders arriving during playback queue behind the
frozen animation. A retreat remains watchable after the authority has already
settled the battle; viewing cannot apply casualties, ownership or rewards again.

The journal, detached replay and viewer inbox belong to Shardbound. Existing
Battle rules, traces, sprites, movement, contact audio and playback are reused.
Solo/private battle completion keeps its own result path. No framework API is
added. Private PvE and trusted campaign checkpoints exclude the shared journal.
Each journal/inbox retains at most 24 orders / 192 KiB, and each playback batch
lasts at most eight seconds. Missing history, a full queue or a restored
authority produces an explicit catch-up notice. Replay verifies the recorded
result digest before displaying any historical action.

## Verification

- **116 tests passed in 32.97 s**: shared journal, concurrent model/socket/UI,
  hosted restart, existing playback and manual battle audio coverage.
  `integration.log` and `summary.json` retain the result and exact selection.
  Measured wall time was 33.349 s; parent CPU was 7.938 s. Hosted child CPU is
  not included in that parent measurement.
- After the final notice wording changed from “current battle” to “current
  state,” all **five concurrent playback regressions passed in 1.69 s**.
  `final-notice-tests.log` records this overlapping selection.
- Native pyglet verification passed at a **1280×720 window / 125% text**,
  with 2560×1440 HiDPI framebuffers. The accepted run used **29 inputs**,
  **24 accepted public commands**, and **four exact UI-to-authority comparisons**.
  Every inspection preserved the authoritative checkpoint.
- Native wall/CPU time was **17.117 / 4.431 s** with a cooperative **25% CPU
  allowance** and **30 FPS cap**. The game and both sockets closed cleanly.

The initial armies are bought through public orders and conquer three real
PvE encounters. Six disclosed autoplay commands prepare those encounters;
health, ownership and rewards are never injected. Later native inputs pay for
the challenge, guard, end the tactical phase and accept the earned skill.
The socket peer moves, guards and retreats while Help remains open. Native
input then opens historical playback, its log and live-room save information,
finishes playback, accepts the reward and returns to the map. Finally the
exact earned checkpoint is restored and published through the retained host,
proving the restart notice appears without another realm order. This final
native step is an authority restore, not a native process restart.

All **12 accepted captures** were inspected. The first native pass exposed
“Waiting for opponent” during playback; the final HUD explains that resolved
actions are being watched and identifies the skip/log controls. The restart
notice uses “current state” because its battle may already be over. No new
clipping, overlap or inaccessible controls were observed. Eleven final PNGs
match the directly inspected preceding pass byte-for-byte; the changed final
notice was opened again. `summary.json` records these comparisons.

`native/verification.json.gz` contains the complete public command/checkpoint
and input receipt. Its **93 source hashes all match the named code commit**.
The receipt preserves the earlier HEAD and dirty-path metadata from capture;
the subsequent exact-commit comparison in `summary.json` identifies the
accepted code. `manifest.json` authenticates retained evidence files.

## Reproduce

From the repository root, run the retained paced test driver with the exact
selection listed in `summary.json`, or only the five playback regressions:

```sh
.venv/bin/python docs/evidence/concurrent-playback-2026-09-08/run_tests.py -q tests/eador/test_concurrent_playback.py
.venv/bin/python tools/verify_eador_concurrent_conflict_ui.py /tmp/new-peer-playback
```

Run expensive jobs sequentially; choose a new native output directory.

This is directed input against one real socket peer, not independent human
play or two native clients. Native capture is muted; audio dispatch is covered
by the included playback/manual-audio tests, without a new human listening
claim. Full mode setup/leave/rejoin, native capital victory/loss, cross-platform
packaging and the wider Early Access gates remain open. No deployment or
package refresh is part of this checkpoint.
