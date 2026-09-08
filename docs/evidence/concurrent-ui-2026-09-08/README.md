# Concurrent campaign development checkpoint — 2026-09-08

Code: **1cce62a**, with server catalog **d3ebdc9**, Realm services **2915a91**
and framework scene return **44fbe78**. This is a development entry, not a
selectable or packaged PvP release. The existing menu still opens shared-realm co-op.

## What works in this checkpoint

Each authenticated seat sees its own Realm and the common map, with ownership
colors and capital/hero information presented relative to that seat. Purchases,
replacement, infusion, independent PvE and Ready use authoritative day/Realm
revision commands. Unrelated peer orders preserve local battle state and Help.
Both players finish ordinary campaign activity before one shared day settles.

A paid challenge waits through the incumbent's actual PvE and earned choice.
The UI shows the committed action and offers withdrawal without refund. Human
armies then use ordinary alternating tactical phases, their own unit IDs and
mana, with input disabled during the opposing phase. Existing BattleScene and
game rules are reused. Local orders animate only after their proposed trace
matches the accepted battle exactly.

The framework change is `Game.pop_to(scene)`: remove overlays above a retained
scene and reveal that scene once. No Realm, PvP or battle knowledge enters
Saga2D. Game-specific snapshot projection and screen reconciliation stay in `eador`.

## Critique and fixes

1. The first map pass crowded the opposing capital with a miniature and left
   troops without the clearer solo army cards. Both armies now use the same
   compact banner geometry; army cards group each miniature, level and health.
   Three inspected baseline frames are retained under `before/`.
2. The native seat-1 route exposed the inherited Westwatch stronghold caption.
   Shared readers now use the actual capital. Tower and recovery prose refers
   to the capital/campaign day. PvP help includes the tactical controls.
3. Socket/UI regressions cover invalid tactical preview refusals, live F6
   persistence information, nested paid replacement and an accepted PvE loss
   which immediately opens a waiting duel. The obsolete result dialog can no
   longer cover that new battle. Broader solo coverage exposed a zero-height
   empty ability paragraph in ordinary replacement reviews; it is now omitted.

## Integration evidence

- **34 passed in 48.11 s** in `final-tests.log`; `run_final_tests.py` records the
  exact selection. The process measured 48.234 s wall / 12.100 s CPU at the
  cooperative 25% allowance. The accepted receipt confirms unchanged source.
  This includes all 12 concurrent scene cases, five human tactical cases,
  solo map reading, paid replacement, save/load and manual tactical input.
- Earlier battle adapter/playback/solo audio selection: **55 passed in 28.43 s**.
- Realm service/network/solo selection: **42 passed in 2.67 s**.
- Dedicated-server selection: **20 passed in 2.54 s**, including complete
  private checkpoints across abrupt real server process restarts. The logged
  CPU measurement is parent-process CPU, not the sum of server children.
- The framework increment separately passed 38 focused scene/input/ownership
  checks. Its behavior and usage are recorded in
  [framework scene return](../../framework-scene-return.md).

These selections overlap. No complete repository-suite pass is claimed.
The earlier failing compatibility log is retained to show the empty-row
regression; the final selection and native review pass after its fix.

## Native evidence

All runs use the real pyglet backend, 30 FPS input pacing and a cooperative
25% CPU allowance. `run-summary.json` records timings, inputs and source hash
differences per receipt. `manifest.json` records each retained file's SHA-256.

| Folder | Directed route | Inspected PNGs |
| --- | --- | ---: |
| `seat-0/`, `seat-1/` | Real loopback peer; purchase, simultaneous private PvE, invalid click refusal, live F6, Help during peer orders, retreat, Ready barrier, map and Hero at 125% | 13 each |
| `conflict/` | Paid approaches and disclosed PvE autoplay; wait, peer choice, shared attacker Guard/End phase, peer Guard/retreat, earned skill and returned map | 7 |
| `human-defender/` | Fresh Wizard duel adapter; blocked opposing-phase inputs, local move/heal, paid Acolyte, shared mana and handoff | 4 |
| `replacement/` | Ordinary solo Swordsman quote at 100/125%, exact paid replacement and map return | 3 |

All **40 accepted PNGs** were inspected by the parent/review agents. Nine
unchanged seat-0 frames were checked by exact SHA-256 against the earlier
inspected pass; its four new/changed frames were opened directly. No blocking
clipping or overlap remained. Disabled waiting buttons still have low-contrast
text; the separate status/guidance remains readable and should be improved
before the mode becomes selectable.

The conflict receipt precedes the later empty-row change in
`eador/replacement_scene.py`, which its route does not display. Its other
recorded source files match this checkpoint. Seat routes and the final
replacement/defender captures have their own exact source hashes. Receipts
preserve these boundaries rather than claiming one identical global capture tree.

The conflict preparation records every paid order and outcome; it never
injects health, province ownership or rewards. Four later UI orders are checked
against exact authoritative checkpoints. It contains three PvE autoplay
preparation fights, not independent human play. Each run uses one native game
window at a time; the peer sends genuine socket commands.

Reproduce from the repository root with the virtualenv Python:

```sh
.venv/bin/python tools/verify_eador_concurrent_ui.py /tmp/new-seat-0 --seat 0
.venv/bin/python tools/verify_eador_concurrent_ui.py /tmp/new-seat-1 --seat 1
.venv/bin/python tools/verify_eador_concurrent_conflict_ui.py /tmp/new-conflict
.venv/bin/python tools/verify_eador_human_ui.py /tmp/new-defender
```

Run these sequentially and use new output directories. The retained
`verify_replacement_row.py` is the bounded final solo visual probe.

## Remaining work

Peer tactical commands currently update snapshots without playback. Full mode
selection, player setup, leaving and UI rejoin, two independent native game
processes, native capital victory/loss, complete human listening/playtests,
Windows and a refreshed multiplayer package remain open. Choice/save tooltip
copy inherited from solo still needs a full live-room wording pass. Server
process persistence tests do not prove the unfinished native rejoin flow.
The existing Mac development archive remains unchanged. **G01–G19 remain incomplete.**
