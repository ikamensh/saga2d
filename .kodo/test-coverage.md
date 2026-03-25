# Feature Coverage — Subsystem Test Map

## Verified baseline (non-visual delivery)

| Item | Value |
|------|--------|
| **Command** | `uv sync --extra dev` then `SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot` |
| **Result** | **2795 passed**, **3 skipped**, **0 failed** (verified 2026-03-25, ~40s) |
| **Skips** | `tests/core/test_game.py` — three `game.run()` tests (headless disables interactive loop) |
| **Not in baseline** | `tests/screenshot/` (golden PNGs), `tests/visual/` (manual/GUI-adjacent), `tests/visual_verify/` (AI + env) — run separately; failures there do not invalidate delivery baseline |

**Local variants:** `pytest` instead of `uv run python -m pytest` if project `.venv` is active. Full tree: drop `--ignore` flags (expect visual/AI/env variance).

---

## Stage 1 — Coverage anchor (PLAN core + target subsystem slice)

**PLAN.md Stage 1** (backend protocol, `Game` loop, `Scene` / `SceneStack`, push/pop/replace): covered under the **Verified baseline** command via `tests/core/test_game.py`, `tests/core/test_scene.py`, `tests/core/test_scene_timers.py`, `tests/core/test_scene_draw.py`, `tests/core/test_scene_sprites.py`, and related integration suites. With `SAGA2D_HEADLESS=1`, three `game.run()` tests in `test_game.py` are **skipped**. Standalone smoke (Game → Scene → Sprite → `MoveTo`, mock): `scripts/smoke_game_move_to.py`.

**Target subsystems** — files, classes, **initial baseline coverage** (pytest collected in listed modules; all pass under the delivery baseline; verified 2026-03-25). **Gap summary:** table *Initial feature coverage — untested / partial* below; detail: §1–§8.

| Subsystem | Source module | Primary types (approx. lines) | Integration | Primary pytest | Tests collected |
|-----------|---------------|------------------------------|-------------|----------------|-----------------|
| **Audio** | `saga2d/audio.py` | `AudioManager` (~L80), `_CrossfadeProxy` (~L30) | `Game.audio`; `saga2d/backends/base.py` audio protocol; `AssetManager.sound` / `.music` in `saga2d/assets.py` | `tests/systems/test_audio.py` | **83** |
| **Input** | `saga2d/input.py` | `InputEvent` (~L36), `_with_world_coords()` (~L87), `InputManager` (~L117) | `Game.tick` in `saga2d/game.py`; `mock_backend` injectors | `tests/systems/test_input.py`; world coords also `tests/kodo_test_systems.py` | **33** (+ kodo) |
| **Cursor** | `saga2d/cursor.py` | `CursorManager` | `Game.cursor`; backend cursor API; `scene.py` cleanup | `tests/systems/test_cursor.py` | **18** |
| **ColorSwap** | `saga2d/rendering/color_swap.py` | `ColorSwap` (~L50); `register_palette`, `get_palette`, `_clear_palettes` | `Sprite` / `AssetManager.image_swapped` (`sprite.py`, `assets.py`); `Game._teardown` clears palettes | `tests/rendering/test_color_swap.py` | **25** |
| **Layout** | `saga2d/ui/layout.py` | `Anchor`, `Layout`; `compute_anchor_position`, `compute_flow_layout`, `compute_content_size` | `component.py` / `components.py` (`Panel`); `widgets.py` (Grid, TabGroup, DataTable) | `tests/ui/test_ui.py` (`TestLayoutMath`, `TestLayoutErrorMessages`, sizing) | **23** with `-k Layout`; more tests hit Panel flow |
| **Theme** | `saga2d/ui/theme.py` | `Style`, `ResolvedStyle`, `_pick`, `Theme` + `resolve_*` | `Game.theme`; components/widgets | `tests/ui/test_theme.py`; `tests/ui/test_drag_drop.py::TestThemeDragProperties` | **13** (+ drag theme class) |
| **DragDrop** | `saga2d/ui/drag_drop.py` | `DragManager`, `_DragSession` | `Component` attrs; `_UIRoot.drag_manager` in `component.py`; theme drop/ghost colors | `tests/ui/test_drag_drop.py` (baseline); screenshot suite excluded | **49** |
| **Screens / dialogs / sequence / settings** | `saga2d/ui/screens.py` | `MessageScreen` (~L54), `ChoiceScreen` (~L116), `ConfirmDialog` (~L193), `SaveLoadScreen` (~L265), `_SequenceRunner` (~L399), `_SettingsScene` (~L461) | **`Game.show_sequence`** → `_SequenceRunner`; **`Game.push_settings`** → `_SettingsScene` (`saga2d/game.py`) | `tests/ui/test_screens.py`; `tests/core/test_settings.py` | **42** + **36** |

**Naming:** There is no public `SettingsScene` or `SequenceRunner` type — use **`_SettingsScene`** / **`_SequenceRunner`** in source, or **`Game.push_settings`** / **`Game.show_sequence`** from game code.

### Eight subsystems — file/class map (quick reference)

| Subsystem | Module | Primary types |
|-----------|--------|---------------|
| Audio | `saga2d/audio.py` | `AudioManager`, `_CrossfadeProxy` |
| Input | `saga2d/input.py` | `InputEvent`, `InputManager`, `_with_world_coords()` |
| Cursor | `saga2d/cursor.py` | `CursorManager` |
| ColorSwap | `saga2d/rendering/color_swap.py` | `ColorSwap`, `register_palette`, `get_palette`, `_clear_palettes` |
| Layout | `saga2d/ui/layout.py` | `Anchor`, `Layout`, `compute_anchor_position`, `compute_flow_layout`, `compute_content_size` |
| Theme | `saga2d/ui/theme.py` | `Style`, `ResolvedStyle`, `_pick`, `Theme` |
| DragDrop | `saga2d/ui/drag_drop.py` | `DragManager`, `_DragSession` |
| Screens / dialogs | `saga2d/ui/screens.py` (+ `saga2d/game.py`) | `MessageScreen`, `ChoiceScreen`, `ConfirmDialog`, `SaveLoadScreen`, `_SequenceRunner`, `_SettingsScene`; `Game.show_sequence`, `Game.push_settings` |

### Initial feature coverage — untested / partial (project context)

Condensed gap list from §1–§8, kodo findings (e.g. F14 channel docs), and AGENTS.md (mock vs real pyglet `dispatch_event`). **U** = no dedicated test; **P** = covered in part or only via related paths. Baseline still green; this tracks *depth*, not pass/fail.

| Subsystem | Untested (U) | Partial (P) |
|-----------|--------------|-------------|
| **Audio** | `play_sound` with unknown channel; `crossfade_music(..., duration=0)`; `_teardown` / idempotent teardown; `set_volume` with NaN/Inf (no `isfinite` guard in code) | Effective volume / crossfade interruption well covered |
| **Input** | `bind` with empty string or `None` key/action; `translate` given unknown raw event types | Defaults, rebind, mouse path, game integration covered; **real pyglet** `dispatch_event` path not in mock baseline |
| **Cursor** | `register` with missing image asset; `set_visible` with non-bool; multi-cursor switching; cursor vs scene push/pop | Single custom cursor, backend args, `Game.cursor` lazy init |
| **ColorSwap** | `_clear_palettes` in isolation; duplicate source colors in mapping (last-wins undocumented); non-RGBA / odd formats; `Sprite.image` reassigned after construction with swap | `apply`, registry, `image_swapped`, sprite at construct time |
| **Layout** | `compute_flow_layout` **padding**; anchor with **zero-size** parent; child **larger** than parent; **negative** spacing/padding | Spacing, anchors (9), flow VERTICAL/HORIZONTAL, error messages |
| **Theme** | `resolve_list_style`, `resolve_grid_style`, `resolve_tooltip_style`, `resolve_tabgroup_style`, `resolve_datatable_style`; many property accessors (tab/datatable/progressbar/list/grid shadows, button outline, …) | `resolve_label` / `resolve_button` / `resolve_panel`; `button_min_width`; drag colors via `TestThemeDragProperties` |
| **DragDrop** | `DragManager.cancel_active()`; ghost using `_image_handle` (sprite path); `drop_accept` / `on_drop` raising; drag while **scene pops** | Rect ghost, targets, escape cancel, nested targets, `Game.tick` hook |
| **Screens / dialogs** | `ChoiceScreen` **empty** `choices`; number key **`"0"`**; `ConfirmDialog` **double** Enter; `MessageScreen` dismiss on release/scroll/drag; `SaveLoadScreen` implicit `game.save_manager`, **overwrite** occupied slot; `_SettingsScene` **rebind steals** another action’s key | Core flows for each screen, sequence runner, settings volume/rebind happy path |

Full method-level tables: §1–§8 below.

**Headless multi-subsystem demo** (cursor, audio, List, drag, Message/Choice/Confirm, settings/rebind): `scripts/multi_subsystem_headless_demo.py` — see section *Headless multi-subsystem demo* below.

---

## Repo-wide subsystem map

High-level mapping from `saga2d/` sources to primary pytest areas. Status = coverage *under the baseline command above* (mock + headless).

| Subsystem | Source (main) | Primary tests | Baseline notes |
|-----------|---------------|-----------------|----------------|
| **Game / loop** | `saga2d/game.py` | `tests/core/test_game.py` | 3 skips when `SAGA2D_HEADLESS=1` |
| **Scene / stack / timers** | `saga2d/scene.py` | `tests/core/test_scene.py`, `test_scene_timers.py`, `test_scene_draw.py`, `test_scene_sprites.py`, `tests/kodo_test_scene_lifecycle.py`, `tests/test_kodo_stage4_*.py` | Lifecycle + flush/deferred ops heavily covered |
| **Actions / sequences** | `saga2d/actions.py` | `tests/actions/test_actions.py`, `tests/kodo_test_sprite_actions.py`, `tests/test_kodo_stage2_*.py` | F42/F43 regressions |
| **Animation** | `saga2d/animation.py` | `tests/rendering/test_animation.py`, `tests/kodo_test_rendering.py` | |
| **Sprite** | `saga2d/rendering/sprite.py` | `tests/rendering/test_sprite.py`, kodo suites | |
| **Camera** | `saga2d/rendering/camera.py` | `tests/rendering/test_camera.py`, `tests/test_kodo_camera_*_edge.py` | Shake / `screen_to_world` regressions |
| **Particles** | `saga2d/rendering/particles.py` | `tests/rendering/test_particles.py`, `tests/test_kodo_systems_edge.py` | F26 lifetime validation |
| **Color swap** | `saga2d/rendering/color_swap.py` — `ColorSwap`, palette API | `tests/rendering/test_color_swap.py` | See §4; Stage 1 table |
| **Layers / tint** | `saga2d/rendering/layers.py` | `tests/rendering/test_tint.py` | |
| **UI tree / events** | `saga2d/ui/component.py` | `tests/ui/test_ui.py`, `tests/ui/test_widgets.py` | F30 mutation-during-traversal |
| **Components** | `saga2d/ui/components.py` | `tests/ui/test_ui.py`, `tests/test_kodo_stage3_*.py` | |
| **Widgets** | `saga2d/ui/widgets.py` | `tests/ui/test_widgets.py`, kodo UI suites | |
| **Layout math** | `saga2d/ui/layout.py` — `Anchor`, `Layout`, `compute_*` | `tests/ui/test_ui.py` (`TestLayoutMath`, …) | See §5; Stage 1 table |
| **Theme / style** | `saga2d/ui/theme.py` — `Style`, `ResolvedStyle`, `Theme` | `tests/ui/test_theme.py`, `tests/ui/test_drag_drop.py` | See §6 — resolver gaps; Stage 1 table |
| **Screens / dialogs** | `saga2d/ui/screens.py` — `MessageScreen`, `ChoiceScreen`, `ConfirmDialog`, `SaveLoadScreen`, `_SequenceRunner`, `_SettingsScene` | `tests/ui/test_screens.py`, `tests/core/test_settings.py` | See §8; `game.py` `show_sequence` / `push_settings` |
| **HUD** | `saga2d/ui/hud.py` | `tests/ui/test_hud.py` | |
| **Drag & drop** | `saga2d/ui/drag_drop.py` — `DragManager`, `_DragSession` | `tests/ui/test_drag_drop.py` | See §7; Stage 1 table |
| **Assets** | `saga2d/assets.py` | `tests/systems/test_assets.py` | |
| **Save / load** | `saga2d/save.py` | `tests/systems/test_save.py`, `tests/kodo_test_persistence_resources*.py` | Corrupt / envelope edges |
| **Audio** | `saga2d/audio.py` — `AudioManager`, `_CrossfadeProxy` | `tests/systems/test_audio.py` | See §1; Stage 1 table |
| **Input** | `saga2d/input.py` — `InputEvent`, `InputManager` | `tests/systems/test_input.py`, `tests/kodo_test_systems.py` | See §2; Stage 1 table |
| **Cursor** | `saga2d/cursor.py` — `CursorManager` | `tests/systems/test_cursor.py` | See §3; Stage 1 table |
| **FSM** | `saga2d/util/fsm.py` | `tests/systems/test_fsm.py` | |
| **Timer / tween** | `saga2d/util/timer.py`, `tween.py` | `tests/actions/test_timer.py`, `tests/actions/test_tween.py` | |
| **Settings UI** | `saga2d/ui/screens.py::_SettingsScene` + `saga2d/game.py::push_settings` | `tests/core/test_settings.py` | Stage 1 table + §8f |
| **Backends** | `saga2d/backends/{base,mock,pyglet}.py` | Mock: all baseline; pyglet: screenshot | Real `dispatch_event` rarely exercised |
| **Cross-cutting E2E** | — | `tests/kodo_test_stage7_e2e.py`, `tests/integration/*.py`, `tests/examples/test_*.py` | |

---

## Highest-priority gaps (repo context + scan)

Ordered for future cycles — combines documented engine blind spots, baseline-excluded suites, and §1–§8 gap lists.

1. **GPU / pyglet path vs mock** — Z-order, blending, real font metrics: mock tests do not see draw order.
2. **Pyglet input dispatch** — `inject_key()` bypasses `dispatch_event`. Need tests calling `window.dispatch_event(...)`.
3. **Theme** — 5 untested `resolve_*` methods + 10+ accessor properties (§6). Largest single API gap.
4. **Layout** — `compute_flow_layout` padding, zero-size parent, child > parent, negative spacing (§5).
5. **Audio** — `set_volume` has no `isfinite` guard; `crossfade(duration=0)`, `_teardown` untested (§1).
6. **Drag/drop** — `cancel_active()`, sprite ghost, exception safety, drag across scene transition (§7).
7. **Screens** — Empty `ChoiceScreen`, key `"0"`, double-confirm, save overwrite (§8).
8. **Cursor / ColorSwap / Input** — Missing asset, `_clear_palettes`, bind validation, unknown event types (§2–§4).
9. **Extended suites** — `visual_verify` depends on API keys; treat as optional CI lane.

---

## Headless multi-subsystem demo

| Item | Detail |
|------|--------|
| **Path** | `scripts/multi_subsystem_headless_demo.py` |
| **Run** | `uv run python scripts/multi_subsystem_headless_demo.py` (`backend="mock"` — no GUI) |
| **Outcome** | Prints `PASS`/`FAIL`; exit 0/1 |

**Workflow:** temp assets → Theme override → HubScene with cursor, audio, List → drag-drop → MessageScreen → ChoiceScreen → ConfirmDialog → push_settings → rebind confirm → Escape pop → assert rebind.

**Finding (2026-03-25, PASS):** `List.on_event` consumes confirm action before Scene.handle_input sees it — expected dispatch order. No defect.

---

**§1–§8 deep-dive:** Audio, Input, Cursor, ColorSwap, Layout, Theme, DragDrop, Screens/Dialogs.

---

## 1. Audio System

**Source:** `saga2d/audio.py` (375 LOC) — `AudioManager`, `_CrossfadeProxy`
**Backend:** `backends/base.py` (protocol: `load_sound`, `play_sound`, `load_music`, `play_music`, `set_player_volume`, `stop_player`); `backends/mock_backend.py` (recording impl); `backends/pyglet_backend.py` (real playback via pyglet.media)
**Asset loading:** `saga2d/assets.py` — `AssetManager.sound()` (`.wav`→`.ogg`→`.mp3`), `AssetManager.music()` (`.ogg`→`.wav`→`.mp3`)
**Tests:** `tests/systems/test_audio.py` (**83 passed**; 8 classes: TestChannelVolume, TestPlaySound, TestPlayMusic, TestStopMusic, TestCrossfadeMusic, TestSoundPools, TestAssetManagerAudio, TestGameIntegration)

### Key classes/functions

| Class/Function | Location | Public API |
|---|---|---|
| `AudioManager` | `audio.py` | `set_volume(ch, level)`, `get_volume(ch)`, `play_sound(name, channel, optional)`, `play_music(name, loop, optional)`, `stop_music()`, `crossfade_music(name, duration, loop)`, `register_pool(name, sounds)`, `play_pool(name)`, `_teardown()` |
| `_CrossfadeProxy` | `audio.py:30` | Internal tween target — `old_volume`/`new_volume` property setters apply master×music×value |
| Volume channels | `AudioManager.__init__` | `master`, `music`, `sfx`, `ui` (all default 1.0) |

### Feature coverage table

| Feature | Source method | Test class | Status | Notes |
|---|---|---|---|---|
| Channel defaults (master/music/sfx/ui=1.0) | `__init__` | TestChannelVolume | ✅ tested | |
| set_volume / get_volume | `set_volume`, `get_volume` | TestChannelVolume | ✅ tested | |
| Volume clamp (0.0–1.0) | `set_volume` | TestChannelVolume | ✅ tested | |
| Unknown channel → KeyError | `set_volume`, `get_volume` | TestChannelVolume | ✅ tested | |
| Effective volume: master × channel | `play_sound` | TestChannelVolume | ✅ tested | sfx, ui, music |
| Volume change re-applies to active music | `set_volume` | TestChannelVolume | ✅ tested | |
| play_sound (sfx/ui channels) | `play_sound` | TestPlaySound | ✅ tested | |
| play_sound — missing asset (optional flag) | `play_sound` | TestPlaySound | ✅ tested | |
| play_sound — unknown channel | `play_sound` | – | ❌ **untested** | channel="bogus" → KeyError expected |
| play_music (loop, volume, stops old) | `play_music` | TestPlayMusic | ✅ tested | |
| play_music — missing asset | `play_music` | TestPlayMusic | ✅ tested | |
| stop_music (stops player, no-op) | `stop_music` | TestStopMusic | ✅ tested | |
| crossfade (two players, midpoint, completion) | `crossfade_music` | TestCrossfadeMusic | ✅ tested | |
| crossfade — same track = no-op | `crossfade_music` | TestCrossfadeMusic | ✅ tested | |
| crossfade — no music → fallthrough to play | `crossfade_music` | TestCrossfadeMusic | ✅ tested | |
| crossfade — interruption (second crossfade) | `crossfade_music` | TestCrossfadeMusic | ✅ tested | |
| crossfade — respects channel volume | `crossfade_music` | TestCrossfadeMusic | ✅ tested | |
| crossfade — NaN/Inf/negative duration | `crossfade_music` | test_kodo_new_edge_cases | ✅ tested | |
| crossfade — duration=0 | `crossfade_music` | – | ❌ **untested** | Edge: instant crossfade |
| stop_music cancels crossfade | `stop_music` | TestCrossfadeMusic | ✅ tested | |
| Sound pools (register, play, no-repeat) | `register_pool`, `play_pool` | TestSoundPools | ✅ tested | |
| Pool — empty/single/two-sound | `play_pool` | TestSoundPools | ✅ tested | |
| Pool — unregistered → KeyError | `play_pool` | TestSoundPools | ✅ tested | |
| Pool — re-register replaces | `register_pool` | TestSoundPools | ✅ tested | |
| Asset extensions (wav/ogg/mp3, caching) | `AssetManager.sound/music` | TestAssetManagerAudio | ✅ tested | |
| Game.audio integration | `Game.audio` | TestGameIntegration | ✅ tested | |
| _teardown | `_teardown` | – | ❌ **untested** | Called by Game._teardown, not isolated |
| set_volume with NaN/Inf | `set_volume` | – | ❌ **untested** | **No isfinite guard** — potential bug |

### Likely workflows & edge cases to test next
- **NaN/Inf volume** → `set_volume("sfx", float('nan'))` — may corrupt effective volume math (master×NaN=NaN). Other setters hardened; this is the last holdout.
- **Instant crossfade** → `crossfade_music("track", duration=0)` — tween completes immediately; verify old player stops cleanly.
- **Unknown channel on play_sound** → `play_sound("hit", channel="bogus")` — should raise KeyError, but may compute NaN volume silently.
- **_teardown idempotency** → call `_teardown()` twice, or during active crossfade — verify cleanup is clean.
- **Pool with 0 sounds after register** → currently registers, but `play_pool` with empty list is no-op. Verify no crash.

---

## 2. Input System

**Source:** `saga2d/input.py` (228 LOC) — `InputEvent` (frozen dataclass), `InputManager`, `_with_world_coords`
**Backend events:** `backends/base.py` — `KeyEvent`, `MouseEvent`, `WindowEvent`, `Event` union
**Mock injection:** `backends/mock_backend.py` — `inject_key()`, `inject_click()`, `inject_mouse_move()`, `inject_scroll()`, `inject_drag()`, `inject_window_event()`, `inject_event()`
**Game dispatch pipeline:** `game.py:tick()` — poll → window filter → mouse tracking → translate → dispatch (HUD → UI → Camera → Scene bindings → Scene.handle_input)
**Tests:** `tests/systems/test_input.py` (**33 passed**; 5 classes), plus `tests/kodo_test_systems.py`, `tests/rendering/test_camera.py`

### Key classes/functions

| Class/Function | Location | Public API |
|---|---|---|
| `InputEvent` | `input.py:35` | Frozen dataclass: `type`, `key`, `action`, `x`, `y`, `button`, `dx`, `dy`, `world_x`, `world_y` |
| `InputManager` | `input.py:117` | `bind(action, key)`, `unbind(action)`, `get_bindings()`, `translate(raw_events)` |
| `_with_world_coords` | `input.py:87` | Populates `world_x/y` from camera; `_MOUSE_EVENT_TYPES` frozenset |
| Default bindings | `_setup_defaults` | confirm→return, cancel→escape, up/down/left/right→arrows |

### Feature coverage table

| Feature | Source method | Test class | Status | Notes |
|---|---|---|---|---|
| InputEvent frozen dataclass, defaults | `InputEvent` | TestInputEvent | ✅ tested | |
| InputEvent world_x/world_y | `InputEvent` | test_camera.py | ✅ tested | |
| Default bindings (6 actions) | `_setup_defaults` | TestInputManagerDefaults | ✅ tested | |
| translate — key_press/release with action | `translate` | TestInputManagerTranslate | ✅ tested | |
| translate — unmapped key → action=None | `translate` | TestInputManagerTranslate | ✅ tested | |
| translate — mouse events | `translate` | TestInputManagerTranslate | ✅ tested | click/move/scroll/drag |
| translate — empty list / None | `translate` | TestInputManagerTranslate | ✅ tested | |
| bind — custom action | `bind` | TestInputManagerBindings | ✅ tested | |
| bind — replaces old key for same action | `bind` | TestInputManagerBindings | ✅ tested | |
| bind — key stealing | `bind` | TestInputManagerEdgeCases | ✅ tested | |
| unbind — removes / no-op on unknown | `unbind` | TestInputManagerBindings | ✅ tested | |
| get_bindings — returns copy | `get_bindings` | TestInputManagerBindings | ✅ tested | |
| _with_world_coords — mouse with/without camera | `_with_world_coords` | kodo_test_systems | ✅ tested | |
| _with_world_coords — non-mouse unchanged | `_with_world_coords` | kodo_test_systems | ✅ tested | |
| Game integration — scenes receive InputEvent | `Game.tick` | TestGameInputIntegration | ✅ tested | |
| Game integration — WindowEvent close | `Game.tick` | TestGameInputIntegration | ✅ tested | |
| bind — empty string action/key | `bind` | – | ❌ **untested** | No validation on empty strings |
| bind — None action/key | `bind` | – | ❌ **untested** | No type check |
| translate — unknown event type | `translate` | – | ❌ **untested** | Silently skipped |

### Likely workflows & edge cases to test next
- **bind("", "")** → empty-string bindings may corrupt the key→action map or produce ghost bindings.
- **bind(None, None)** → may crash on dict operations or silently store None keys.
- **translate([object()])** → unknown event type in input list — currently silently skipped, but should be validated or documented.
- **Rapid rebind during gameplay** → bind("confirm", "a") then immediately bind("confirm", "b") — verify old key fully removed.
- **Event dispatch order** → HUD → UI → Camera → Bindings → handle_input. Test that consumed events stop propagating at each layer.

---

## 3. Cursor System

**Source:** `saga2d/cursor.py` (66 LOC) — `CursorManager`
**Backend:** `base.py` — `set_cursor(handle|None, hotspot_x, hotspot_y)`, `set_cursor_visible(bool)`; mock records state; pyglet converts hotspot y-coordinate for y-up
**Scene integration:** `scene.py:_cleanup_paused_scene()` — resets cursor to "default" on scene pop
**Tests:** `tests/systems/test_cursor.py` (**18 passed**; 5 classes: TestCursorRegister, TestCursorSet, TestCursorCurrent, TestCursorVisible, TestCursorBackendCalls + TestCursorGameIntegration)

### Key classes/functions

| Class/Function | Location | Public API |
|---|---|---|
| `CursorManager` | `cursor.py` | `register(name, image_name, hotspot=(0,0))`, `set(name)`, `set_visible(visible)`, `current` (property) |
| Game integration | `game.py` | `game.cursor` (lazy property → CursorManager) |

### Feature coverage table

| Feature | Source method | Test class | Status | Notes |
|---|---|---|---|---|
| register — load image + store handle | `register` | TestCursorRegister | ✅ tested | |
| register — custom hotspot | `register` | TestCursorRegister | ✅ tested | |
| register — overwrite existing | `register` | TestCursorRegister | ✅ tested | |
| set("default") — restores system cursor | `set` | TestCursorSet | ✅ tested | |
| set(custom) — activates registered cursor | `set` | TestCursorSet | ✅ tested | |
| set(unregistered) → KeyError | `set` | TestCursorSet | ✅ tested | |
| current property (initial="default") | `current` | TestCursorCurrent | ✅ tested | |
| set_visible(True/False) | `set_visible` | TestCursorVisible | ✅ tested | |
| Backend receives correct handle/hotspot/None | – | TestCursorBackendCalls | ✅ tested | |
| Game.cursor lazy property | `Game.cursor` | TestCursorGameIntegration | ✅ tested | |
| register — missing asset | `register` | – | ❌ **untested** | Should raise AssetNotFoundError |
| register — set after re-register | `register` | – | ⚠️ partial | Overwrite tested, not switch-after-reregister |
| set_visible(non-bool) | `set_visible` | – | ❌ **untested** | No type validation |
| Multiple cursors — switch between several | – | – | ❌ **untested** | Only single custom cursor tested |

### Likely workflows & edge cases to test next
- **Missing asset on register** → `cursor.register("aim", "nonexistent_cursor")` — should raise AssetNotFoundError.
- **Multi-cursor switching** → register 3 cursors, cycle through them, verify backend receives correct handle each time.
- **Cursor persistence across scene push/pop** → push scene (cursor reset to default), pop (verify scene's cursor choice restored or not).
- **set_visible(42)** → non-bool truthy value — backend may misinterpret.
- **Re-register then set** → register("aim", "old.png"), register("aim", "new.png"), set("aim") — verify new handle used.

---

## 4. ColorSwap System

**Source:** `saga2d/rendering/color_swap.py` (112 LOC) — `ColorSwap`, `register_palette()`, `get_palette()`, `_clear_palettes()`
**Sprite integration:** `rendering/sprite.py` — `Sprite(color_swap=..., team_palette=...)` (color_swap > team_palette > plain)
**Asset caching:** `assets.py` — `AssetManager.image_swapped(name, swap)` — key is `(name, swap.cache_key())`
**Backend:** `base.py:load_image_from_pil(pil_image)` — converts PIL Image to backend handle
**Teardown:** `game.py:_teardown()` calls `_clear_palettes()`
**Tests:** `tests/rendering/test_color_swap.py` (**25 passed**; 6 classes: TestColorSwap, TestPaletteRegistry, TestColorSwapAssetManager, TestLoadImageFromPil, TestColorSwapSprite, TestColorSwapIntegration)

### Key classes/functions

| Class/Function | Location | Public API |
|---|---|---|
| `ColorSwap` | `color_swap.py` | `__init__(source_colors, target_colors)`, `apply(image_path)` → PIL Image, `cache_key()` → hashable tuple |
| `register_palette` | `color_swap.py` | `register_palette(name, swap)` — global registry |
| `get_palette` | `color_swap.py` | `get_palette(name)` → ColorSwap (raises KeyError) |
| `_clear_palettes` | `color_swap.py` | Internal — clears registry (called by Game._teardown) |

### Feature coverage table

| Feature | Source method | Test class | Status | Notes |
|---|---|---|---|---|
| apply — color replacement | `apply` | TestColorSwap | ✅ tested | |
| apply — preserves alpha | `apply` | TestColorSwap | ✅ tested | |
| apply — unmatched pixels unchanged | `apply` | TestColorSwap | ✅ tested | |
| Empty mapping | `apply` | TestColorSwap | ✅ tested | |
| Mismatched lengths → ValueError | `__init__` | TestColorSwap | ✅ tested | |
| Nonexistent file → FileNotFoundError | `apply` | TestColorSwap | ✅ tested | |
| cache_key — unique, equal, hashable | `cache_key` | TestColorSwap | ✅ tested | |
| Palette registry — register/get | `register_palette` | TestPaletteRegistry | ✅ tested | |
| Palette registry — unregistered → KeyError | `get_palette` | TestPaletteRegistry | ✅ tested | |
| Palette registry — overwrite | `register_palette` | TestPaletteRegistry | ✅ tested | |
| image_swapped — handle + caching | `image_swapped` | TestColorSwapAssetManager | ✅ tested | |
| Sprite with color_swap / team_palette | `Sprite()` | TestColorSwapSprite | ✅ tested | |
| color_swap > team_palette precedence | – | TestColorSwapSprite | ✅ tested | |
| Two sprites same swap → same handle | – | TestColorSwapIntegration | ✅ tested | |
| _clear_palettes | `_clear_palettes` | – | ❌ **untested** | Called by Game._teardown, not isolated |
| Duplicate source colors | `apply` | – | ❌ **untested** | Last-wins behavior undocumented |
| Non-RGBA image format | `apply` | – | ❌ **untested** | .convert("RGBA") edge path |
| Sprite.image setter with color_swap post-construction | `Sprite.image` | – | ❌ **untested** | Only construction tested |

### Likely workflows & edge cases to test next
- **_clear_palettes isolation** → register palette, clear, verify get_palette raises KeyError.
- **Duplicate source colors** → `ColorSwap([(255,0,0),(255,0,0)], [(0,255,0),(0,0,255)])` — which target wins?
- **Non-PNG image** → apply() uses `formats=["PNG"]` — test with a JPEG or BMP to verify error path.
- **Sprite.image reassignment with swap** → change image on existing sprite that has color_swap — verify swap re-applied.
- **Concurrent sprites with different palettes on same base image** → verify cache distinguishes them correctly.

---

## 5. Layout System

**Source:** `saga2d/ui/layout.py` (141 LOC) — `Anchor` (9 enum values), `Layout` (3 enum values), `compute_anchor_position()`, `compute_flow_layout()`, `compute_content_size()`
**Component integration:** `component.py:Component.compute_layout()` → `_layout_children()`; `components.py:Panel._layout_children()` calls `compute_flow_layout`; `Panel.get_preferred_size()` calls `compute_content_size`
**Widget layout:** `widgets.py:Grid` — cell-based layout with `cell_size`, `spacing`; `TabGroup` — tab bar + content; `DataTable` — column-width distribution
**Tests:** `tests/ui/test_ui.py` (**24 layout-specific tests**; TestLayoutMath, TestLayoutErrorMessages + Panel/Button/Label sizing tests)

### Key classes/functions

| Class/Function | Location | Public API |
|---|---|---|
| `Anchor` | `layout.py:6` | CENTER, TOP, BOTTOM, LEFT, RIGHT, TOP_LEFT, TOP_RIGHT, BOTTOM_LEFT, BOTTOM_RIGHT |
| `Layout` | `layout.py:20` | NONE, VERTICAL, HORIZONTAL |
| `compute_anchor_position` | `layout.py:28` | `(anchor, parent_x, parent_y, parent_w, parent_h, child_w, child_h, margin=0)` → `(x, y)` |
| `compute_flow_layout` | `layout.py:72` | `(layout, parent_x/y/w/h, children_sizes, spacing=0, padding=0)` → `[(x, y), ...]` |
| `compute_content_size` | `layout.py:112` | `(layout, children_sizes, spacing=0, padding=0)` → `(w, h)` |

### Feature coverage table

| Feature | Source method | Test class | Status | Notes |
|---|---|---|---|---|
| Anchor — all 9 positions | `compute_anchor_position` | TestLayoutMath | ✅ tested | |
| Anchor — with margin | `compute_anchor_position` | TestLayoutMath | ✅ tested | |
| flow_layout — VERTICAL | `compute_flow_layout` | TestLayoutMath | ✅ tested | |
| flow_layout — HORIZONTAL | `compute_flow_layout` | TestLayoutMath | ✅ tested | |
| content_size — VERTICAL | `compute_content_size` | TestLayoutMath | ✅ tested | |
| content_size — HORIZONTAL | `compute_content_size` | TestLayoutMath | ✅ tested | |
| content_size — NONE/empty | `compute_content_size` | TestLayoutMath | ✅ tested | returns (2×padding, 2×padding) |
| flow_layout — NONE → [] | `compute_flow_layout` | TestLayoutMath | ✅ tested | |
| Error messages (bogus anchor/layout) | – | TestLayoutErrorMessages | ✅ tested | |
| flow_layout — padding parameter | `compute_flow_layout` | – | ❌ **untested** | padding arg exists, only spacing tested |
| anchor — zero-size parent | `compute_anchor_position` | – | ❌ **untested** | 0×0 parent rect |
| anchor — child larger than parent | `compute_anchor_position` | – | ❌ **untested** | Negative offsets |
| flow_layout — single child | `compute_flow_layout` | – | ❌ **untested** | Only 2+ children tested |
| content_size — padding + spacing combined | `compute_content_size` | – | ❌ **untested** | Both non-zero at once |
| Layout.NONE with children → empty positions | `compute_flow_layout` | – | ⚠️ partial | Tested empty list, not NONE with sizes |
| Negative spacing/padding | – | – | ❌ **untested** | No validation exists |

### Likely workflows & edge cases to test next
- **Padding in flow layout** → `compute_flow_layout(VERTICAL, ..., padding=10)` — children should be inset from edges.
- **Zero-size parent** → anchor calculations with 0×0 parent — verify no division errors, reasonable (0,0) output.
- **Child > parent** → anchor CENTER with child bigger than parent — should compute negative offsets (valid math, unusual UX).
- **Single child flow** → verify single child centers on cross-axis correctly.
- **Negative spacing** → `compute_flow_layout(VERTICAL, ..., spacing=-5)` — overlapping children. No crash expected but behavior undefined.
- **Panel with padding + spacing + children** → end-to-end Panel layout with both values set — verify content_size and child positions agree.

---

## 6. Theme System

**Source:** `saga2d/ui/theme.py` (413 LOC) — `Style` (optional overrides), `ResolvedStyle` (concrete values), `Theme` (40+ constructor params), `_pick()` helper
**Resolve methods:** `resolve_label_style`, `resolve_button_style` (state-aware: normal/hovered/pressed/disabled), `resolve_panel_style`, `resolve_list_style`, `resolve_grid_style`, `resolve_tooltip_style`, `resolve_tabgroup_style`, `resolve_datatable_style`
**Properties:** `button_min_width`, `button_hover_outline_color/width`, `progressbar_color/bg_color`, `selected_color`, `list_alt_row_bg_color`, `grid_cell_bg_color`, `tab_active/inactive_color`, `datatable_header_bg/text_color`, `datatable_row/alt_row_bg_color`, `drop_accept/reject_color`, `ghost_opacity`, `panel_shadow_offset/color`
**Integration:** `game.py:game.theme` (lazy); components call `resolve_*` in their draw/layout; widgets access properties directly
**Tests:** `tests/ui/test_theme.py` (**13 passed**; TestStyle, TestTheme) + `tests/ui/test_drag_drop.py:TestThemeDragProperties`

### Key classes/functions

| Class/Function | Location | Public API |
|---|---|---|
| `Style` | `theme.py:17` | Dataclass: `font`, `font_size`, `text_color`, `background_color`, `padding`, `border_color`, `border_width`, `hover_color`, `press_color` (all optional/None) |
| `ResolvedStyle` | `theme.py:35` | Dataclass: same fields but all concrete (non-None) |
| `Theme` | `theme.py:55` | 40+ kwargs; 8 `resolve_*` methods; 19 property accessors |
| `_pick(explicit, default)` | `theme.py:50` | Returns explicit if not None, else default |

### Feature coverage table

| Feature | Source method | Test class | Status | Notes |
|---|---|---|---|---|
| Style — all fields optional | `Style` | TestStyle | ✅ tested | |
| Style — partial override | `Style` | TestStyle | ✅ tested | |
| resolve_label_style — defaults + overrides | `resolve_label_style` | TestTheme | ✅ tested | |
| resolve_button_style — 4 states | `resolve_button_style` | TestTheme | ✅ tested | normal/hovered/pressed/disabled |
| resolve_button_style — explicit hover override | `resolve_button_style` | TestTheme | ✅ tested | |
| resolve_panel_style — defaults + override | `resolve_panel_style` | TestTheme | ✅ tested | |
| None means inherit from theme | `_pick` | TestTheme | ✅ tested | |
| button_min_width property | `button_min_width` | TestTheme | ✅ tested | |
| Drag-drop theme properties | `drop_accept_color` etc. | TestThemeDragProperties | ✅ tested | |
| Custom theme colors (DnD) | – | TestThemeDragProperties | ✅ tested | |
| **resolve_list_style** | `resolve_list_style` | – | ❌ **untested** | Used by List widget |
| **resolve_grid_style** | `resolve_grid_style` | – | ❌ **untested** | Used by Grid widget |
| **resolve_tooltip_style** | `resolve_tooltip_style` | – | ❌ **untested** | Used by Tooltip widget |
| **resolve_tabgroup_style** | `resolve_tabgroup_style` | – | ❌ **untested** | Used by TabGroup widget |
| **resolve_datatable_style** | `resolve_datatable_style` | – | ❌ **untested** | Used by DataTable widget |
| DataTable theme properties (4 accessors) | properties | – | ❌ **untested** | header/row/alt colors |
| Tab theme properties (2 accessors) | properties | – | ❌ **untested** | active/inactive color |
| panel_shadow_offset / shadow_color | properties | – | ❌ **untested** | 2 accessors |
| Theme custom constructor args | `Theme.__init__` | – | ⚠️ partial | Only DnD colors tested |
| list_alt_row/grid_cell/progressbar colors | properties | – | ❌ **untested** | 3+ accessors |
| button_hover_outline color/width | properties | – | ❌ **untested** | 2 accessors |

### Likely workflows & edge cases to test next
- **5 untested resolvers** → call each (`resolve_list_style`, `resolve_grid_style`, `resolve_tooltip_style`, `resolve_tabgroup_style`, `resolve_datatable_style`) with None and with explicit Style — verify returned ResolvedStyle matches theme defaults / overrides.
- **All 19 property accessors** → instantiate Theme with custom args, assert each property returns the custom value.
- **Full theme propagation** → set `game.theme = Theme(...)` with all-custom colors, render each widget type, verify resolved styles used correct values.
- **Style conflict resolution** → Style(padding=20) on a component in a Theme(panel_padding=8) — explicit wins.
- **Default Theme comparison** → `Theme()` with no args — verify all defaults match documented Slate color palette values.

---

## 7. Drag-and-Drop System

**Source:** `saga2d/ui/drag_drop.py` (295 LOC) — `DragManager`, `_DragSession`
**Component attributes:** `component.py` — `draggable`, `drag_data`, `drop_accept`, `on_drop` on `Component`
**UI root:** `component.py:_UIRoot.drag_manager` (lazy property)
**Theme:** `theme.py` — `drop_accept_color`, `drop_reject_color`, `ghost_opacity`
**Tests:** `tests/ui/test_drag_drop.py` (**49 passed**; 11+ classes), `tests/test_kodo_camera_drag_edge.py`, `tests/screenshot/test_drag_drop_screenshots.py`

### Key classes/functions

| Class/Function | Location | Public API |
|---|---|---|
| `DragManager` | `drag_drop.py` | `handle_event(event)` → bool, `cancel_active()`, `is_dragging` (property), `drag_data` (property) |
| `_DragSession` | `drag_drop.py:45` | Internal dataclass: source, data, start_x/y, ghost_x/y, ghost_offset_x/y, current_target, target_accepts |
| Component attrs | `component.py` | `draggable: bool`, `drag_data: Any`, `drop_accept: Callable`, `on_drop: Callable` |

**Event flow:** left-click on draggable → `_start_drag()` → move/drag updates ghost → release → `_end_drag()` evaluates target → calls `on_drop` if accepted. Escape → `_cancel_drag()`. All events consumed during drag.

### Feature coverage table

| Feature | Source method | Test class | Status | Notes |
|---|---|---|---|---|
| DragManager — initial state, lazy creation | `__init__` | TestDragManagerConstruction | ✅ tested | |
| Component drag attributes | `Component` | TestComponentDragAttributes | ✅ tested | |
| Start drag — click on draggable | `_start_drag` | TestDragStart | ✅ tested | |
| No drag — non-draggable/right-click/disabled/invisible | – | TestDragStart | ✅ tested | |
| Ghost tracking — follows move/drag | `handle_event` | TestGhostTracking | ✅ tested | |
| Drop on valid target — fires on_drop | `_end_drag` | TestDropOnValidTarget | ✅ tested | |
| Drop on rejecting target — no on_drop | `_end_drag` | TestDropOnValidTarget | ✅ tested | |
| Drop on non-target / empty space | `_end_drag` | TestDropOnValidTarget | ✅ tested | |
| Cancel drag — Escape key | `_cancel_drag` | TestCancelDrag | ✅ tested | |
| All events consumed during drag | `handle_event` | TestEdgeCases | ✅ tested | |
| Drop target feedback — accept/reject/change | `_find_drop_target` | TestDropTargetFeedback | ✅ tested | |
| Source excluded from drop targets | `_walk_for_target` | TestDropTargetFeedback | ✅ tested | |
| Ghost rendering (rect fallback, overlays) | `_draw_ghost` | TestGhostRendering | ✅ tested | |
| Game.tick integration | – | TestGameTickIntegration | ✅ tested | |
| Nested components — deepest target wins | `_walk_for_target` | TestNestedComponents | ✅ tested | |
| Various drag_data types | – | TestDragDataTypes | ✅ tested | |
| Multiple drags in sequence | – | TestEdgeCases | ✅ tested | |
| Cancel then new drag | – | TestEdgeCases | ✅ tested | |
| cancel_active() — external cancel | `cancel_active` | – | ❌ **untested** | Public API |
| Ghost with _image_handle (sprite-based) | `_draw_ghost` | – | ❌ **untested** | Only rect fallback tested |
| drop_accept raising exception | `_find_drop_target` | – | ❌ **untested** | Callback exception safety |
| on_drop raising exception | `_end_drag` | – | ❌ **untested** | Propagation behavior |
| Drag during scene transition | – | – | ❌ **untested** | Active drag when scene pops |

### Likely workflows & edge cases to test next
- **cancel_active()** → start drag, call `drag_manager.cancel_active()` programmatically — verify session ends, ghost cleared.
- **Exception in drop_accept** → `drop_accept=lambda d: 1/0` — does DragManager catch it or crash? Ghost stuck?
- **Exception in on_drop** → valid drop target, on_drop raises — verify drag session still cleaned up.
- **Sprite-based ghost** → component with `_image_handle` set — verify image-based ghost rendering path.
- **Drag across scene pop** → start drag, then `game.pop()` — does DragManager reference stale component? Is drag cancelled?
- **Double release** → inject two mouse releases rapidly — verify no crash from ending already-ended drag.

---

## 8. Screens & Dialog Workflows

**Source:** `saga2d/ui/screens.py` (654 LOC) — `MessageScreen`, `ChoiceScreen`, `ConfirmDialog`, `SaveLoadScreen`, `_SequenceRunner`, `_SettingsScene`
**Game convenience:** `game.py` — `game.show_sequence(screens, on_complete)`, `game.push_settings()`
**Scene base:** `scene.py` — `transparent`, `show_hud`, `pop_on_cancel` properties
**Tests:** `tests/ui/test_screens.py` (**42 passed**; TestMessageScreen, TestChoiceScreen, TestConfirmDialog, TestSaveLoadScreen, TestShowSequence), `tests/core/test_settings.py` (**36 passed**)

### Key classes/functions

| Class | Location | Constructor params | Key methods |
|---|---|---|---|
| `MessageScreen` | `screens.py:54` | `text, on_dismiss` | `on_enter()`, `handle_input()`, `_dismiss()` |
| `ChoiceScreen` | `screens.py:116` | `prompt, choices, on_choice` | `on_enter()`, `handle_input()`, `_select(index)` |
| `ConfirmDialog` | `screens.py:193` | `question, on_confirm, on_cancel` | `on_enter()`, `handle_input()`, `_confirm()`, `_cancel()` |
| `SaveLoadScreen` | `screens.py:265` | `mode, save_manager, on_save, on_load, slot_count` | `on_enter()`, `handle_input()`, `_on_slot_click()` |
| `_SequenceRunner` | `screens.py:399` | `screens, on_complete` | `on_enter()`, `on_reveal()`, `_finish()` |
| `_SettingsScene` | `screens.py:461` | (none) | `on_enter()`, `handle_input()`, `_adjust_volume()`, `_start_listening()` |

All screens: `transparent=True`, `show_hud=False`, modal (consume all events).

### Feature coverage table

#### 8a. MessageScreen

| Feature | Status | Notes |
|---|---|---|
| transparent + show_hud attrs | ✅ tested | |
| Dismiss on key_press / click | ✅ tested | |
| on_dismiss callback fires | ✅ tested | |
| Consumes all events (modal) | ✅ tested | |
| UI build + render | ✅ tested | |
| Dismiss on release/scroll/drag | ❌ **untested** | Only key_press/click tested |

#### 8b. ChoiceScreen

| Feature | Status | Notes |
|---|---|---|
| Escape cancels (no callback) | ✅ tested | |
| Button click → on_choice(index) | ✅ tested | |
| Number key shortcuts (1–9) | ✅ tested | |
| Invalid number ignored | ✅ tested | |
| Modal | ✅ tested | |
| on_choice=None works | ✅ tested | |
| Empty choices list | ❌ **untested** | 0 buttons + prompt only |
| Number key "0" | ❌ **untested** | "0" is digit, maps to index –1 |

#### 8c. ConfirmDialog

| Feature | Status | Notes |
|---|---|---|
| Yes/No buttons | ✅ tested | |
| on_confirm / on_cancel callbacks | ✅ tested | |
| Enter → confirm, Escape → cancel | ✅ tested | |
| Modal | ✅ tested | |
| No callbacks works | ✅ tested | |
| Double-confirm (Enter twice) | ❌ **untested** | Second pop on empty stack? |

#### 8d. SaveLoadScreen

| Feature | Status | Notes |
|---|---|---|
| Invalid mode → ValueError | ✅ tested | |
| slot_count ≤ 0 → ValueError (F56) | ✅ tested | |
| Load mode — filled/empty slots | ✅ tested | |
| Save mode — saves state | ✅ tested | |
| Back / Escape pops | ✅ tested | |
| on_save / on_load callbacks | ✅ tested | |
| save_manager=None → game's manager | ❌ **untested** | Only explicit override tested |
| Overwrite existing save slot | ❌ **untested** | Save to occupied slot |

#### 8e. _SequenceRunner / show_sequence

| Feature | Status | Notes |
|---|---|---|
| Chains message screens | ✅ tested | |
| on_complete fires after last | ✅ tested | |
| Empty sequence → immediate complete | ✅ tested | |
| transparent=True | ✅ tested | |

#### 8f. _SettingsScene / push_settings

| Feature | Status | Notes |
|---|---|---|
| UI structure (volume + keybindings) | ✅ tested | |
| Volume +/- buttons | ✅ tested | |
| Volume clamped 0.0–1.0 | ✅ tested | |
| Key rebinding — listen + bind | ✅ tested | |
| Escape cancels listening | ✅ tested | |
| Back / Escape pops | ✅ tested | |
| game.push_settings() convenience | ✅ tested | |
| Rebind stealing another action's key | ❌ **untested** | Bind confirm to escape |

### Likely workflows & edge cases to test next
- **ChoiceScreen(choices=[])** → 0 buttons, prompt only. Number keys should all be ignored. Escape still pops.
- **Number key "0"** → `int("0") - 1 = -1` → may index last choice or be out of range.
- **Double-confirm** → press Enter twice on ConfirmDialog — first pop removes it, second pop hits scene below.
- **Save overwrite** → save to slot 1 (already occupied), verify data replaced and on_save fired with correct slot.
- **Rebind key stealing in settings** → rebind "confirm" to "escape" key — verify "cancel" action loses its key, settings still navigable.
- **MessageScreen dismiss on drag** → inject drag event — does handle_input consume it? Is _dismiss called?
- **SaveLoadScreen with game.save_manager** → construct without explicit save_manager, verify it falls through to game's.

---

## Coverage Summary (§1–§8 subsystems)

Feature-level audit from the tables above — verified against actual pytest runs (2026-03-25).

| Subsystem | Source LOC | Primary Tests | Tested | Untested | Coverage |
|---|---|---|---|---|---|
| **Audio** | 375 | 83 | 24 | 4 | 🟢 86% |
| **Input** | 228 | 33 | 18 | 3 | 🟢 86% |
| **Cursor** | 66 | 18 | 10 | 4 | 🟡 71% |
| **ColorSwap** | 112 | 25 | 14 | 4 | 🟡 78% |
| **Layout** | 141 | 24 | 9 | 6 | 🟡 60% |
| **Theme** | 413 | 13 | 10 | 12 | 🔴 45% |
| **DragDrop** | 295 | 49 | 18 | 5 | 🟢 78% |
| **Screens** | 654 | 78 | 40 | 10 | 🟢 80% |
| **TOTAL** | **2,284** | **323** | **143** | **48** | **75%** |

### Legend
- 🟢 ≥ 78% features tested
- 🟡 60–77% features tested
- 🔴 < 60% features tested

### Priority gaps for next test pass

1. **Theme resolve methods** — 5 untested resolvers + 12 untested property accessors. Largest single API gap. Pure Python → easy to test.
2. **Layout edge cases** — padding, zero-size, child > parent, negative spacing, single-child. Pure math → easy to test.
3. **Audio validation** — `set_volume` NaN/Inf guard, `crossfade(duration=0)`, `_teardown` isolation, unknown channel.
4. **DragDrop exception safety** — `cancel_active()`, exception in `drop_accept`/`on_drop`, sprite ghost, drag during scene pop.
5. **Screens edge cases** — empty ChoiceScreen, key "0", double-confirm, save overwrite, rebind stealing in settings.
6. **Cursor gaps** — missing asset, multi-cursor switching, non-bool set_visible.
7. **ColorSwap internals** — `_clear_palettes`, duplicate source colors, non-RGBA, post-construction swap.
8. **Input validation** — empty/None bind args, unknown event type in translate.

---

## Appendix — environment blockers

Workflows that do not run under default headless mock CI (carried forward from prior coverage notes).

| Workflow | Reason |
|----------|--------|
| Pyglet backend rendering | Requires display server (X11/Wayland) |
| Screenshot golden-image comparison | Requires pyglet + display |
| AI visual verification | Requires `ANTHROPIC_API_KEY` |
| Interactive game examples | Requires windowed display |
| Audio hardware playback | Requires audio hardware |
| `game.run()` loop | Blocked by `SAGA2D_HEADLESS=1` |

## Appendix — archived kodo stage narratives

Long-form Stage 1–5 tester logs (runtime outcome tables for F42–F58, Stage 4 gameplay workflow, Stage 5 asset probes, pytest command snippets) lived in `.kodo/test-coverage.md` **before** the subsystem-map rewrite. Retrieve an older revision with:

`git log --oneline -- .kodo/test-coverage.md` → pick the commit *before* the rewrite → `git show <hash>:.kodo/test-coverage.md`
