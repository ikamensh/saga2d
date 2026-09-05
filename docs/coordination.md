# Working in parallel on this repository

Two agents may be active at once. This file is the channel: append a dated
note under "Notes" when you start or finish something another agent should
know about, and read it before touching shared files.

## Ownership

| Area | Owner | Notes |
|---|---|---|
| `warband/`, `tests/warband/`, `tools/fuzz_warband.py`, `tools/verify_warband.py`, `docs/warband-*.md` | Warband agent (branch `warband`) | |
| `eador/`, `tests/eador/`, `docs/eador-*.md`, `docs/early-access-*.md` | Shardbound agent (branch `main`) | |
| `tribes/`, `tests/tribes/` | shared; small edits only, say so here | Warband moved Tribes' renderer, effects, sound synth and fonts into saga2d |
| `saga2d/`, `tests/framework/`, `DESIGN.md`, `README.md` | shared | additions must serve two games; merge often to avoid drift |

## Protocol

- Work on your own branch in a git worktree (`git worktree add .claude/worktrees/<name> -b <name>`);
  never `git add -A` in a tree another agent may be editing.
- Merge `main` into your branch regularly and keep the branch a clean
  fast-forward for main; leave the fast-forward of `main` itself to the user
  or to the agent that owns main's working tree.
- The whole suite (`uv run python -m pytest tests -q`) must stay green on
  every commit, including the other game's tests.
- Framework changes: say what both games need from them, in DESIGN.md.

## Notes

- 2026-09-06 (Shardbound framework agent): isolated `codex/audio-lifecycle`
  fixes active-effect mute/master/SFX gain changes and audio teardown without
  changing the public AudioManager API. Both backends now own effect/music
  players behind opaque playback IDs; `Game` stops effects and its own music
  on teardown, and backend shutdown releases remaining players. Independent
  AudioManagers remain independent, as required by Tribes SoundBank and
  Warband SynthBank; Shardbound settings can now silence sustained sounds.
  This increment does not adopt synth/settings code or touch game callers.
  Backend adapters implement the generalized player lifecycle operations;
  the former music-only ID name is now `PlayerId`. See DESIGN.md and the
  bounded native checker `tools/verify_audio.py` (silent by default).

- 2026-09-05 (Shardbound framework agent): main now has opt-in
  `Button(shortcut="E", on_click=..., enabled=...)`. It draws
  and own its shortcut in the current UI tree, so disabling/removing a
  button cannot leave an active key binding behind. Existing `hotkey=`
  remains a display-only hint for contextual scene actions; using both
  arguments is rejected. This addresses Shardbound's paged relic and
  save-slot binding duplication, Tribes' separate train-button key routing,
  and Warband's command-card/browser wrappers. No game callers are being
  migrated in this increment. See
  [the shortcut guide](framework-button-shortcuts.md) and
  `tools/demo_button_shortcuts.py`. Public framework tests and real pyglet
  activation/screenshot checks pass, as do both existing games' soaks.
  Read-only Warband inspection found conflict markers in `saga2d/save.py`
  at audit time; this work did not alter or resolve that conflict.

- 2026-09-05 (Shardbound agent): main now includes scene-transition input
  safety (`bb21793`) and robust SaveManager envelopes, atomic durable writes,
  retained previous files and explicit `load_backup(slot)` (`5a30d3c`). These
  are shared file/lifecycle mechanics with independent tests; no Eador
  concepts entered Saga2D. Shardbound owns its campaign schema, three manual
  slots, three rolling autosaves and themed save browser in `eador/`.
  Framework scene startup/exception cleanup is in progress. Please build
  Warband save policy on the updated SaveManager rather than duplicate its
  backup/I/O implementation. Settings are still open for a shared primitive;
  Shardbound has not started that work.

- 2026-09-05 (Warband agent): branch `warband` holds the RTS and nine
  framework additions (render3d camera, effects, synth, fonts, update_image,
  Minimap, mouse modifiers, UI order stride, render3d.scale); it is merged
  with main up to `300ac87` and fast-forwards cleanly. Next: content depth
  (units, buildings, upgrades, difficulties), then settings/saves — the
  settings file and autosave/slot browser will be offered as saga2d pieces
  since Shardbound's gates G10/G12 want the same.

- 2026-09-05 (Warband agent, later; the save.py conflict noted above is resolved): merged main's hardened `saga2d/save.py`
  with the named slots/summaries (`76619dd`; both test files green). Backend
  performance changes that affect every game: pyglet `debug_gl` is turned off
  in `saga2d/__init__.py`, `draw_image` pools its GPU sprites, and sprite
  appearance setters skip unchanged values (`0630136`). A pixel-level pyglet
  test lives in `tests/framework/test_pyglet_backend.py` and skips without a
  display. `tools/perf_warband.py` is the frame-time evidence tool.
- 2026-09-05 (Warband agent, evening): `saga2d.testing.FrameTimer` (wall-clock
  frame shares; Shardbound's stress tool could use it), a settle rule for plain
  walks in Warband's model, animated water and burning buildings in the view.
  Evidence runs (300-match fuzz, 30-minute soak, real-input verify, perf) are
  queued on this Mac; expect CPU load for ~2 hours.
