# Multiplayer verification — 6 September 2026

Implementation: `62de78f` on `codex/multiplayer`, incorporating the committed
Warband branch and main through `706a6c9`. The task's worktree is isolated;
main's checkout belongs to the other game work. See [the multiplayer guide](../../multiplayer.md).

## Automated checks

- `uv run python -m pytest tests -q`: **1,547 passed in 291.89 seconds** after
  merging main. One host-clock integration test was added afterward.
- `uv run python -m pytest tests/test_multiplayer_games.py -q`: **15 passed in
  1.11 seconds**, including that additional host-clock/disconnect test. The only
  subsequent production edit shortened a results button from “New solo game”
  to “Play solo”; the final native Tribes run verified its fit and behavior.
- `uv build`: framework source distribution and wheel built successfully.
- Bounded fuzzing before the main merge, at 25% of one CPU core:
  - Tribes: 3 AI games and 2 random-input scene runs, zero failures.
  - Warband: 1 AI game and 2 scene runs of 120 inputs, zero failures.
  - Shardbound: 2 model campaigns and 2 scene runs of 60 commands, zero failures.

Socket integration uses actual loopback TCP. Tests cover ownership, turn
permissions, atomic rejections, stale revisions, room/game mismatches,
reconnection, scene lifetime, all three guest input paths, Shardbound's next
shard and offline-save guards, and exclusion of multiplayer from solo rankings.

## Native evidence

```bash
SAGA2D_SILENT=1 uv run python tools/verify_multiplayer.py /tmp/saga2d-multiplayer
SAGA2D_SILENT=1 uv run python tools/verify_multiplayer.py /tmp/saga2d-multiplayer --game tribes
```

The second command refreshed Tribes after the button label adjustment. The
verifier runs a separate host process and a real pyglet guest, enters the room
through native keys, sends gameplay orders, compares accepted snapshots, and
captures title/join/gameplay screens. Tribes also reaches round-limit results;
Warband receives updates under its F10 menu; Shardbound explores, guards, and
advances a tactical round. Captured screens were opened and visually inspected.

`native.txt` and `tribes-final.txt` retain command output. `SHA256SUMS` covers
the retained files. Native frames are paced at 30 FPS and jobs run sequentially.
These checks ran on macOS using loopback; they do not establish cross-platform,
wide-area latency, NAT traversal, or modified-client anti-cheat support.
