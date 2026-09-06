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

- 2026-09-06 (Shardbound framework agent): independent Tribes regression
  found during the screen-layer checks also reproduces on pre-layer
  `a401607`. Save map seed 3, start seed 2, hover its fish at (10, 13), then
  quick-load: the Harvest button evaluated a stale hover before the loaded
  HUD was built. `codex/tribes-load-hover` clears those transient targets
  first; public save/input regressions cover an absent resource and a smaller
  loaded map. The development fuzzer now seeds title/world randomness as
  well as inputs, and retains full failure tracebacks. Normal game launch
  randomness is unchanged. This is a separate game fix, not a screen-layer
  or framework persistence change; no Warband files were edited.

- 2026-09-06 (Shardbound framework agent): isolated `codex/screen-layers`
  adds `with scene.screen_layer(1):` for immediate screen drawing. The scope
  works through existing game helpers, leaves world RenderLayer unchanged,
  and cannot escape the owning scene. UI controls draw above these local
  layers; children/later siblings now cover earlier text as well as shapes,
  matching input order. This serves Shardbound's stationary feedback pills
  and Tribes' floating text/toast composition. It extends the private stride
  from Warband `0f089fa`: four suborders remain available per UI component,
  so Minimap's `order + 1` frame stays above its image and below later UI.
  No Warband source or worktree was edited. The changed scene stride should
  be retained when merging its older stride-only implementation. Public
  integration tests and `tools/demo_screen_layers.py --verify` cover local
  composition, native pixels/input, UI overlap and modal isolation.

- 2026-09-06 (Shardbound framework agent): isolated `codex/window-display`
  adopts committed Warband `Game.set_fullscreen(bool)` and adds read-only
  `Game.fullscreen` / `window_size` plus `set_window_size((w, h))`. Choosing a
  size leaves fullscreen; toggling back restores the last actual OS windowed
  size. The native window is resizable, while the game's logical canvas stays
  fixed. Backend-only fixes normalize Cocoa Retina content units, refresh the
  projection after fullscreen recreation and clip drawing to the letterbox.
  Shardbound display settings and Warband's existing fullscreen preference
  use the same mechanism; Tribes can use it without model/UI reflow changes.
  Presets, saved settings and shortcuts remain game-owned. No Warband
  worktree or game callers were edited. See `docs/framework-display.md` and
  the independent native/pixel/input check `tools/demo_display.py --verify`.
  The methods occupy Warband's existing lifecycle locations so merging its
  earlier delegates requires an explicit choice instead of retaining two
  definitions and silently overriding size restoration or headless checks.

- 2026-09-06 (Shardbound root): adopting the pure `saga2d.synth` sample
  functions from committed Warband `f478e89`, with a public compose → WAV →
  playback test. Tribes will import these shared functions instead of keeping
  duplicate synthesis code; its compositions and SoundBank remain game-owned.
  Shardbound will compose original assets at build time and use `game.audio`.
  This increment does not adopt the cache/SynthBank wrapper or edit Warband.

- 2026-09-06 (Shardbound framework agent): `codex/settings-store` adopts the
  committed Warband `Settings(path, defaults)` mapping and `Game.settings` /
  `data_dir` interface. Optional `validator=` keeps ranges/enums in game code;
  explicit kind/finite/depth checks reject unsafe loaded values. `.error`
  still allows games to show a recovery screen with defaults in memory, but
  ordinary saves now refuse invalid current files. `reset()` stays in memory;
  its next successful `save()` retains displaced bytes under a unique recovery
  name. Existing recovery files survive further resets. The private durable
  writer extracted from SaveManager is shared; slot behavior remains unchanged.
  See `docs/framework-settings.md` and `tools/demo_settings.py`. No Warband
  worktree, game callers, settings UI, fullscreen or synthesis code changed.

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

- 2026-09-06 (Shardbound framework agent): display previews need a public snapshot
  even when opened fullscreen. `Game.windowed_size` now reports actual native
  windowed size or remembered restoration size while fullscreen; no game cache
  guesses that state. This serves Shardbound and Warband settings cancellation
  on top of the same reviewed display methods. The Shardbound Sound/Display UI
  and startup/recovery policy remain in `eador/`, using the existing Settings
  store. No Warband worktree or game source was changed. See
  `docs/eador-display-settings.md` for launch overrides and verification.

- 2026-09-06 (Shardbound research agent): isolated `codex/wrapped-label`
  adds opt-in `Label(text, width=300, wrap=True)` for retained UI flow.
  Shardbound reward descriptions and Warband's width-390 tutorial objective
  need measured multiline height without manual placement of the next control.
  The existing Scene paragraph algorithm moves to a private shared helper;
  no new backend protocol or game rule is introduced. A private preparation
  hook refreshes wrapped measurements before the existing input/draw layout
  boundaries. No Warband worktree or game callers were edited. Checkpoint
  `25cda6a` passes 888 full tests, both games' bounded fuzz runs and the native
  font/reactive/paused/resize input example. Existing paragraph pixels match
  actual prior `3923255` exactly. See `docs/framework-wrapped-label.md`.

- 2026-09-06 (Shardbound framework agent): native resize/reading-size verification
  exposed a Pyglet text-measurement cache collision: the key identified physical
  glyph size but stored logical dimensions divided by an earlier viewport scale.
  The cache now retains physical metrics and converts at the current scale. This
  fixes over/under-measurement for all games without a new API or game-specific
  policy. `tools/verify_text_measurement.py` compares warm/fresh measurements,
  wrapped flow, exact pixels and native clicks in both resize directions. No
  Warband worktree changed; Shardbound's scoped reading setting is separate.

- 2026-09-06 (Shardbound framework agent): the game-owned Codex reading-size
  increment uses existing wrapped Label/Column layout and Settings persistence.
  It adds no framework API or global theme changes. Whole-entry pagination is
  measured after UI attachment, and the scoped 100/125 preference explicitly
  leaves other game screens unchanged. No Warband worktree was touched. See
  `docs/eador-reading-size.md` for the vertical slice and remaining G10 scope.
