# Feature Coverage

Tracked across `kodo test` runs. Baseline: commit 477220f, 2026-03-21. Stage 4 fixes: 2026-03-22. Fresh re-test: 2026-03-23. **Stage 1 re-verify:** commit `4227501`, 2026-03-23.

## Stage 1 — Baseline install & full automated suite (verified 2026-03-23)

End-to-end check: install like a new user, import smoke, run the full pytest tree that does not require a display or API keys.

### Install

| Path | Command | Result |
|------|---------|--------|
| uv (typical for this repo) | `uv sync --extra dev` | **pass** — editable `saga2d` + pytest in env |
| pip (README) | `python3 -m venv /tmp/… && pip install -e "/path/to/saga2d[dev]"` | **pass** — `from saga2d import Game, Scene` (verified Python 3.13 venv; project requires **≥3.12**) |
| Import smoke | `uv run python -c "from saga2d import Game, Scene; g=Game('t',backend='mock'); g.push(Scene()); g.tick(0.016); g._teardown()"` | **pass** |

### Full pytest (CI-style)

**Scope:** all of `tests/` except `tests/visual_verify`, `tests/visual`, `tests/screenshot` (golden GPU capture and AI-verify need extra setup).

```bash
cd /path/to/saga2d
SAGA2D_HEADLESS=1 uv run python -m pytest tests/ \
  --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q
```

| Metric | Value |
|--------|-------|
| Collected | **2200** |
| Passed | **2197** |
| Skipped | **3** (`tests/core/test_game.py` — `game.run()` when `SAGA2D_HEADLESS` is set) |
| Failed | **0** |
| Duration | ~34 s (representative local run) |

**Stage 1 verdict:** baseline automated tests **pass**; set **`SAGA2D_HEADLESS=1`** in CI so `TestHeadlessMode` in `tests/test_kodo_core_fresh.py` and the `game.run()` guard stay consistent.

### Optional visual suites (this environment)

| Command | Outcome |
|---------|---------|
| `uv run python -m pytest tests/screenshot tests/visual tests/visual_verify -q` | **92 skipped** (markers / no live pyglet screenshot path) |

### Test artifacts

- **`.pytest_cache/`** — created at repo root when pytest runs (gitignored).
- No JUnit/HTML report is configured in `pyproject.toml` by default.

### Stage 1 coverage scope (what “baseline” means)

- **In suite:** core `Game`/`Scene`/stack, rendering (mock-recorded), UI, audio (mock), save/load, actions/tweens/timers, integration and kodo regression files under `tests/`.
- **Out of default run:** live GPU screenshot comparison, `tests/visual` pixel checks, Anthropic-based `tests/visual_verify` (optional extra `ai-verify`).

## Stage 6A — Clean-Room Install & Smoke Tests (2026-03-22)

### Install Tests

| Check | Command | Result |
|-------|---------|--------|
| Wheel install (fresh venv) | `pip install /path/to/saga2d` | **pass** — installs saga2d 0.1.0 + numpy + Pillow + pyglet |
| Editable install + dev deps | `pip install -e ".[dev]"` | **pass** — pytest 9.0.2 included |
| Test suite from editable install | `python -m pytest tests/ --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q` | **pass** — 1401/1404 (3 SAGA2D_HEADLESS expected) |

### Smoke Tests (14 tests, all pass)

All run from fresh venv with `backend='mock'`, no SAGA2D_HEADLESS, in `/tmp/saga2d-cleanroom/`.
Required creating `assets/images/sprites/test.png` (16x16 red RGBA) for Sprite tests.

| # | What | Imports / API exercised | Result |
|---|------|------------------------|--------|
| 1 | Top-level imports | `from saga2d import Game, Scene, Sprite, Panel, Label, Button, ...` (30+ symbols) | pass |
| 2 | Game(mock) creation | `Game('Test', resolution=(320,240), backend='mock')` | pass |
| 3 | Scene push + on_enter | `g.push(TestScene())`, assert `entered` flag | pass |
| 4 | Sprite creation | `Sprite('sprites/test', position=(100,100))`, `scene.add_sprite(sp)` | pass |
| 5 | Action: Sequence/Delay/Do | `sp.do(Sequence(Delay(0.1), Do(cb)))`, tick twice | pass |
| 6 | Timer | `scene.after(0.1, cb)`, tick twice | pass |
| 7 | UI Panel+Label+Button | `Panel(layout=VERTICAL, children=[Label, Button])`, `scene.ui.add()` | pass |
| 8 | Save/Load roundtrip | `SaveManager(Path(td)).save(1, {...}, 'TestScene')` → `.load(1)` | pass |
| 9 | Scene pop | `g.pop()`, assert stack empty | pass |
| 10 | StateMachine | `StateMachine(['idle','walk'], 'idle', transitions={...})` | pass |
| 11 | README quick-start | Panel+Layout+Anchor+Label+Button in on_enter | pass |
| 12 | Tween | `tween(obj, 'x', 0, 100, 1.0, ease=LINEAR)` | pass |
| 13 | MoveTo action | `MoveTo((100,100), speed=200)` | pass |
| 14 | Scene stack depth | push 3 scenes, pop 3, verify top at each step | pass |

### Findings

| ID | Severity | Description | Repro |
|----|----------|-------------|-------|
| **F10** | Low | `Game.__del__` crashes with `AttributeError: '_timer_manager'` when `__init__` failed partway | `Game('x', width=320)` → catches TypeError, `__del__` prints traceback to stderr |
| **F11** | Low | `Game.__del__` prints `ImportError: sys.meta_path is None` on normal script exit with scene on stack | Push scene, don't call `_teardown()`, let script exit → stderr noise during Python shutdown |

### Usability Issues (not bugs, but friction for new users)

| Issue | Detail |
|-------|--------|
| Sprite requires real asset file | `Sprite('foo')` immediately hits `AssetNotFoundError` — no "placeholder" mode for mock backend. New users must create `assets/images/` structure first. |
| No public `game.top()` | Must use `game._scene_stack.top()` (private API) to inspect current scene |
| Game is a strict singleton | Second `Game()` without `_teardown()` raises RuntimeError — unfriendly for REPL/notebook exploration |
| `SaveManager` requires `Path` not `str` | `SaveManager('/tmp/saves')` → `AttributeError: 'str' object has no attribute 'mkdir'` |
| API discoverability | `Scene.add_sprite()` not `Scene.add()`, `scene.ui.add()` not `scene.add_ui()`, `MoveTo((x,y), speed)` not `MoveTo(x, y, speed=)` — requires reading source or docs |

## Stage 6 part B — Input, camera picking, physics (2026-03-22)

| Check | Command / location | Result |
|-------|-------------------|--------|
| Input manager + Game dispatch | `pytest tests/systems/test_input.py -v` (33 tests) | pass |
| Camera + mouse world coords + shake + follow + bounds | `pytest tests/rendering/test_camera.py -v` (134 tests) | pass |
| Kodo camera regression | `pytest tests/kodo_test_rendering.py -k "Camera or screen_to_world or world" -v` | pass (17) |
| World coords helpers | `pytest tests/kodo_test_systems.py -k "world_coords or _with_world" -v` | pass (2) |
| Drag-drop (mouse paths) | `pytest tests/ui/test_drag_drop.py -q` | pass (49) |
| Integration A/B/C (incl. camera scroll + UI fixed in screen space) | `python -m tests.harness.integration_harness all -v` | pass |
| Systems scenario O (inject key + click → scene) | `python -m tests.harness.systems_util_harness O -v` | pass |
| UI harness I (camera bounds + `world_to_screen` / `screen_to_world`) | `python -m tests.harness.ui_rendering_harness I -v` | pass |

**Out of engine scope:** `Camera` has **no zoom or rotation**; there is **no** built-in physics/collision API (tunneling, filter groups, collision callbacks).

## Stage 6 part C — Shake vs picking fix + F10 cleanup (2026-03-22)

### F12: Camera shake vs mouse picking (confirmed bug, fixed)

**Bug:** During active camera shake, `screen_to_world()` and `InputEvent.world_x/y` used only `camera._x/_y`, while rendering used `camera._x + shake_offset_x`. Clicking on a visually rendered sprite during shake would give incorrect world coordinates — the click would "miss" by the shake offset.

**Fix:** `Camera.screen_to_world()` and `Camera.world_to_screen()` now include `_shake_offset_x/_y` in their calculations, matching what `_sync_sprites_to_camera()` uses for rendering.

**Files changed:** `saga2d/rendering/camera.py` (screen_to_world, world_to_screen)

**Regression tests (7):** `tests/rendering/test_camera.py::TestShakePickingRegression`

| Test | What it proves |
|------|---------------|
| `test_screen_to_world_includes_shake_offset` | screen→world adds shake offset |
| `test_world_to_screen_includes_shake_offset` | world→screen subtracts shake offset |
| `test_screen_world_roundtrip_during_shake` | roundtrip is exact during shake |
| `test_no_shake_unchanged` | no regression when shake inactive |
| `test_shake_expired_offset_zero` | offsets zero after shake expires |
| `test_click_world_coords_match_rendered_sprite_during_shake` | E2E: click at rendered position → correct world coords |
| `test_with_world_coords_includes_shake` | _with_world_coords helper propagates shake |

### F10: Game.__del__ crash on partial init (fixed)

**Bug:** If `Game.__init__` failed partway (e.g. invalid args), `__del__` → `_teardown()` would crash with `AttributeError: '_timer_manager'` because `_teardown()` accessed attributes unconditionally.

**Fix:** `Game._teardown()` now guards `_timer_manager`, `_tween_manager`, and `_scene_stack` with `hasattr()` checks, returning early if init was incomplete.

**Files changed:** `saga2d/game.py` (_teardown)

**Regression tests (2):** `tests/kodo_test_persistence_resources.py::TestTeardownCompleteness`

| Test | What it proves |
|------|---------------|
| `test_teardown_safe_after_partial_init_f10` | `_teardown()` on half-built Game doesn't raise |
| `test_del_safe_after_partial_init_f10` | `__del__()` on half-built Game doesn't raise |

### F11: Game.__del__ stderr on normal exit (not fixed — low value)

**Assessment:** F11 only fires when a user forgets `_teardown()` and lets the script exit with scenes on the stack. The existing `try/except` in `__del__` catches the error. The `sys.meta_path is None` guard in `_teardown()` already handles the module import path. The stderr noise is only visible in development. Not worth adding complexity for this edge case — `game.run()` calls `_teardown()` in its `finally` block, so production code is unaffected.

### Test counts

| Suite | Command | Count | Result |
|-------|---------|-------|--------|
| Full suite | `pytest --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q` | **1411** | pass |
| Camera (all) | `pytest tests/rendering/test_camera.py -v` | **134** (was 123+4=127, now +7) | pass |
| Persistence | `pytest tests/kodo_test_persistence_resources.py -v` | **50** (was 48, now +2) | pass |
| Kodo camera | `pytest tests/kodo_test_rendering.py -k "Camera or screen_to_world or world" -v` | **17** | pass |
| UI harness I | `python -m tests.harness.ui_rendering_harness I -v` | 1 | pass |

### Tester re-verification (2026-03-22)

End-to-end check (mock backend only): **1411** passed with `env -u SAGA2D_HEADLESS`. Focused bundle in one command:

`pytest tests/rendering/test_camera.py::TestShakePickingRegression tests/systems/test_input.py tests/rendering/test_camera.py tests/kodo_test_persistence_resources.py::TestTeardownCompleteness -v` → **173** passed.

**Shake + picking:** Confirmed in code (`camera.py` `screen_to_world` / `world_to_screen`; `game.py` sprite sync uses same offsets) and by `TestShakePickingRegression` (unit + `test_click_world_coords_match_rendered_sprite_during_shake`). **No remaining mismatch** between rendered sprite position and mouse world coords during shake.

Also re-ran: kodo camera filter (17), kodo `world_coords` (2), `tests/ui/test_drag_drop.py` (49), `integration_harness all`, `systems_util_harness O`, `ui_rendering_harness I` — all pass.

## Stage 7 — Remaining Feature Areas E2E (2026-03-22)

### Test file: `tests/kodo_test_stage7_e2e.py` — 70 tests (62 base E2E + 8 adversarial), all pass

| # | Area | Tests | What's exercised |
|---|------|-------|-----------------|
| 1 | Audio crossfade E2E | 4 | Tween-driven volume ramp, same-track noop, no-music fallback, stop cancels crossfade |
| 2 | Audio sound pools | 4 | Single-element pool, empty pool, unregistered raises, no-immediate-repeat |
| 3 | Audio volume edge cases | 5 | Clamp >1, clamp <0, invalid channel KeyError, ui channel |
| 4 | Audio optional assets | 4 | play_sound/play_music optional=True for missing, required raises |
| 5 | Audio _teardown | 2 | Stops music, idempotent double-call |
| 6 | Backend draw_text + load_font | 4 | Text recording, anchors, font handles, font with path |
| 7 | TextBox typewriter E2E | 6 | Gradual reveal, skip, reset, instant mode, text setter resets, draw emits text |
| 8 | Word wrap edge cases | 5 | Explicit newlines, empty string, single long word, zero max_width, multiple newlines |
| 9 | Backend draw_circle | 3 | Recording, segments param, opacity param |
| 10 | Backend draw_image | 2 | Recording, opacity param |
| 11 | Backend capture_frame | 1 | Returns PIL Image with correct size/mode |
| 12 | Label draw E2E | 2 | Emits draw_text calls, empty string no crash |
| 13 | Tween cancel + on_complete | 3 | on_complete fires, cancel stops, all 4 easing modes |
| 14 | Timer chaining | 2 | .then() chain fires in order, cancel via manager |
| 15 | FSM edge cases | 6 | Transition callbacks, unknown event returns False, valid_events property, self-transition, duplicate states, invalid initial raises |
| 16 | ProgressBar draw | 1 | Emits rect draw calls |
| 17 | SettingsScreen E2E | 1 | push_settings() + escape pops back |
| 18 | Tilemap scope | 2 | No tilemap module, no tilemap exports |
| 19 | Assets edge cases | 3 | frames() discovery, missing prefix raises, image caching |
| 20 | Scene draw helpers | 2 | draw_rect emits, draw_world_rect uses camera |

### Corrected test counts (previously under-counted in feature map)

| Area | Old count | Actual count | Source |
|------|-----------|-------------|--------|
| Audio | 8 | 83 | `tests/systems/test_audio.py` (83 tests, not 8) |
| Settings | 7 | 36 | `tests/core/test_settings.py` (36 tests) |
| Assets | 17 | 17 | `tests/systems/test_assets.py` (correct) |
| Cursor | 6 | 18 | `tests/systems/test_cursor.py` (18 tests) |
| Input | 33 | 33 | `tests/systems/test_input.py` |
| kodo_test_systems | — | 180 | Broad coverage: UI widgets, audio, save, input, FSM, cursor, drag-drop |

### Confirmed absent features (not bugs)

- **Tilemaps**: No `saga2d.tilemap` module, no tile-related exports. Saga2D is a sprite-based engine.
- **Physics/collision**: No built-in collision detection, tunneling, or physics simulation.
- **Pathfinding**: No A*, nav mesh, or grid pathfinding utilities.
- **Dialog/narrative**: Only modal screens (MessageScreen, ChoiceScreen); no dialog tree or scripting system.
- **Math/geometry**: No vector/matrix math utilities beyond coordinate conversion.

### Findings (Stage 7 base)

No new bugs found from base E2E pass. All 62 base tests pass.

### Stage 7 Adversarial Pass — 8 additional tests (2026-03-22)

| Area | Tests | Finding |
|------|-------|---------|
| NaN dt in Delay | 2 | **F13**: `Delay.update(NaN)` → stuck; negative dt delays completion |
| NaN dt in FadeOut/FadeIn | 2 | **F13**: `FadeOut/FadeIn.update(NaN)` → ValueError |
| Inf dt in Delay | 1 | +inf completes immediately (expected) |
| play_sound channel gap | 3 | **F14**: `channel='music'/'master'` accepted despite docstring |

F13/F14 documented with regression tests but not fixed (low risk).

### Totals after Stage 7 + Adversarial

| Suite | Count | Result |
|-------|-------|--------|
| Full main suite | **1411** | pass |
| All kodo tests (8 files) | **664** | pass |
| Example tests | **78** | pass |
| Integration harness | 3/3 | pass |

## Feature Map (50 areas)

| # | Feature / Workflow | Test File(s) | Test Count | Last Tested | Status | Findings |
|---|-------------------|-------------|-----------|-------------|--------|----------|
| 1 | Install & import | conftest.py (implicit) | — | 2026-03-21 | pass | uv pip install OK |
| 2 | Game lifecycle (create/tick/teardown) | core/test_game.py | 7 | 2026-03-21 | pass (4/7) | 3 game.run() tests fail under SAGA2D_HEADLESS=1 |
| 3 | Game.run() main loop | core/test_game.py | 3 | 2026-03-21 | env-fail | RuntimeError when SAGA2D_HEADLESS=1; passes when unset |
| 4 | Scene stack (push/pop/replace/clear_and_push) | core/test_scene.py, kodo_test_scene_lifecycle.py | 36+73 | 2026-03-21 | pass | F1 cursor crash fixed; hook ordering, mutations during hooks, empty-stack ops all verified |
| 5 | Scene lifecycle hooks (on_enter/on_exit/on_reveal) | core/test_scene.py, kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | Exact hook ordering verified for all operations; game property lifetime tested |
| 6 | Scene drawing (draw_rect/draw_world_rect/bg color) | core/test_scene_draw.py | 12 | 2026-03-21 | pass | |
| 7 | Scene-owned sprites | core/test_scene_sprites.py | 19 | 2026-03-21 | pass | add/remove/cleanup verified |
| 8 | Scene-owned timers | core/test_scene_timers.py | 19 | 2026-03-21 | pass | timer cleanup on scene exit |
| 9 | Settings / configuration | core/test_settings.py | 36 | 2026-03-22 | pass | Volume sliders, key rebinding, escape-to-pop, push_settings() |
| 10 | Sprites (create/position/remove/anchor/y-sort) | rendering/test_sprite.py, kodo_test_sprite_actions.py | 64+16 | 2026-03-21 | pass | F3 speed validation fixed; z-order, layer separation, removal lifecycle tested |
| 11 | Sprite tinting | rendering/test_tint.py | 11 | 2026-03-21 | pass | |
| 12 | Actions (Sequence/Parallel/Delay/Do/MoveTo/Fade/Remove/Repeat) | actions/test_actions.py, kodo_test_sprite_actions.py | 50+40 | 2026-03-21 | pass | F2 Repeat design-intent; F6 action replacement bug found |
| 13 | Camera (center_on/follow/pan_to/shake/bounds; screen/world + input) | rendering/test_camera.py, kodo_test_rendering.py | 134+17 | 2026-03-22 | pass | Translation only (no zoom/rotation). **F12 fixed**: shake vs picking mismatch (screen_to_world now includes shake offset) |
| 14 | Animation (play/queue/stop/loop/frames) | rendering/test_animation.py | 27 | 2026-03-21 | pass | |
| 15 | Particles (burst/continuous/stop/remove) | rendering/test_particles.py | 15 | 2026-03-21 | pass | |
| 16 | Color Swap (palette registration/apply) | rendering/test_color_swap.py | 6 | 2026-03-21 | pass | |
| 17 | UI Panel/Label/Button | ui/test_ui.py | 92 | 2026-03-22 | pass | F4 right-click fixed; layout math, anchoring, scene integration |
| 18 | UI Widgets (ProgressBar/List/Grid/DataTable/TextBox/TabGroup/Tooltip) | ui/test_widgets.py | 149 | 2026-03-22 | pass | DataTable 44 tests; PanelSpacing 14 |
| 19 | UI Layout (anchoring/flow) | ui/test_ui.py | (in #17) | 2026-03-22 | pass | All 9 anchors + flow |
| 20 | Theme & Style | ui/test_theme.py | 13 | 2026-03-22 | pass | Defaults, resolution, button states, overrides |
| 21 | HUD | ui/test_hud.py | 38 | 2026-03-22 | pass | Creation, visibility, input/update dispatch, scene transitions |
| 22 | Modal Screens (Message/Choice/Confirm/SaveLoad) | ui/test_screens.py | 42 | 2026-03-22 | pass | SequenceRunner, status/help modals |
| 23 | Drag & Drop | ui/test_drag_drop.py | 49 | 2026-03-22 | pass | DragManager, ghost tracking, drop targets, visual feedback |
| 24 | Audio (channels/music/sfx/crossfade/pools) | systems/test_audio.py, kodo_test_stage7_e2e.py | 83+19 | 2026-03-22 | pass | Crossfade E2E, sound pools, volume clamping, optional assets, _teardown |
| 25 | Input (action mapping/key stealing/mouse events, world_x/y dispatch) | systems/test_input.py, test_camera.py (§21) | 33+ | 2026-03-22 | pass | E2E world coords on click/move/drag; multi-event tick |
| 26 | Save/Load (save/load/delete/list/corrupt) | systems/test_save.py, kodo_test_persistence_resources.py | 51+25 | 2026-03-22 | pass | SE1: list_slots aborts on first corrupt slot (design-intent); SE2: saves top scene only; SE7: atomic write protects against partial save; F9: non-object JSON now raises SaveError |
| 27 | Tweening (tween/ease/cancel) | actions/test_tween.py | 22 | 2026-03-21 | pass | |
| 28 | Timers (after/every/cancel/chaining) | actions/test_timer.py | 24 | 2026-03-21 | pass | |
| 29 | FSM (transitions/callbacks/validation) | systems/test_fsm.py | 13 | 2026-03-21 | pass | |
| 30 | Cursor (register/set/visibility) | systems/test_cursor.py | 18 | 2026-03-21 | pass | |
| 31 | Assets (image/sound/music/frames/@2x) | systems/test_assets.py | 17 | 2026-03-21 | pass | |
| 32 | Mock Backend (event injection/tracking) | conftest.py + all | — | 2026-03-21 | pass | |
| 33 | Integration: adversarial reentrancy | integration/test_adversarial.py, kodo_test_scene_lifecycle.py | 18+73 | 2026-03-21 | pass | 7 FakeGame tests pass (F1 fixed); mutations in on_enter/on_exit/on_reveal/update tested |
| 34 | Integration: resource leaks | integration/test_resource_leaks.py, kodo_test_persistence_resources.py | 9+23 | 2026-03-22 | pass | SE4: save after teardown is silent noop; SE5: push() strips old top's resources; WeakSet GC verified; action/anim cleanup on remove |
| 35 | Transparent/pause_below semantics | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | 8 tests: opaque hides below, transparent shows both, chain blocking, independence |
| 36 | Scene.game property lifetime | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | 6 tests: set before on_enter, cleared after pop/replace/clear_and_push, kept when pushed over |
| 37 | on_enter exception rollback | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | push/replace/clear_and_push all roll back on on_enter crash |
| 38 | Cleanup ordering (sprites/timers/UI) | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-22 | pass | SE5/SE6: push() calls on_exit+cleanup on old top; sprites removed, timers cancelled; UI kept on push, cleared on pop |
| 39 | on_exit exception handling | kodo_test_scene_lifecycle.py | 3 | 2026-03-22 | **fixed** | F5: on_exit exception now pops scene (pop/replace/clear_and_push paths) |
| 40 | Active-action removal | kodo_test_sprite_actions.py | 7 | 2026-03-21 | pass | Remove mid-MoveTo/Sequence/Parallel, self-remove in Do, action tracking cleanup |
| 41 | Orphaned sprites | kodo_test_sprite_actions.py | 3 | 2026-03-21 | pass | No scene owner, survives scene pop, teardown with active actions |
| 42 | Deep action nesting | kodo_test_sprite_actions.py | 18 | 2026-03-21 | pass | 5-deep Seq, 10-wide Par, Repeat(Seq), Seq(Par(Seq)), battle sequence |
| 43 | Action replacement mid-callback | kodo_test_sprite_actions.py | 1 | 2026-03-22 | **fixed** | F6: update_action() now preserves action set by callback |
| 44 | Animation queue/state transitions | kodo_test_sprite_actions.py | 12 | 2026-03-22 | pass | Play, queue, interrupt, stop, PlayAnim action |
| 45 | Animation queue chain 3+ | kodo_test_sprite_actions.py | 1 | 2026-03-22 | **fixed** | F7: play() no longer clears queue when called from _drain_queue |
| 46 | Save input validation (slot types/bounds) | kodo_test_persistence_resources.py | 8 | 2026-03-22 | pass | slot=0, negative, float, string for save/load/delete |
| 47 | Non-serializable state handling | kodo_test_persistence_resources.py | 4 | 2026-03-22 | pass | lambda, set, bytes, custom object → SaveError |
| 48 | Game._teardown completeness | kodo_test_persistence_resources.py | 4 | 2026-03-22 | pass | SE4: post-teardown save is noop; sprite sets cleared, subsystems nulled, stack drained, on_exit called |
| 49 | Sprite/timer/anim cleanup on transitions | kodo_test_persistence_resources.py | 7 | 2026-03-22 | pass | SE5: push strips old top resources; owned sprites removed on pop, timers cancelled, push/pop ×5 no leak |
| 50 | Save class name & version migration | kodo_test_persistence_resources.py | 4 | 2026-03-22 | pass | SE3: load with empty stack returns data, skips restore; V1→V2 migration with dict.get defaults |

## Example / Tutorial Tests

| Example | Test File | Test Count | Status |
|---------|-----------|-----------|--------|
| Battle Vignette | examples/test_battle_vignette.py | 14 | pass |
| Menu Tutorial | examples/test_menu_tutorial.py | 46 | pass |
| Tower Defense (example) | examples/test_tower_defense_example.py | 4 | pass |
| Tower Defense (tutorial) | examples/test_tower_defense_tutorial.py | 21 | pass |

## Sharp Edges (confirmed design-intent, not bugs)

Discovered via Stage 5 exploratory testing. All verified by execution.

| ID | Behavior | Why not a bug | Test |
|----|----------|---------------|------|
| SE1 | `list_slots()` aborts on first corrupt slot — remaining slots unread | `list_slots` delegates to `load()` which raises `SaveError` by design on corrupt JSON | `test_list_slots_corrupted_mid_list` |
| SE2 | `game.save()` captures only the top scene's state | Documented API; games needing multi-scene state must aggregate in `get_save_state()` | `test_save_saves_top_scene_not_bottom` |
| SE3 | `game.load()` with empty stack returns data but skips `load_save_state()` | Returns data so caller can reconstruct scenes manually; documented in docstring | `test_load_empty_stack_no_crash` |
| SE4 | `game.save()` after `_teardown()` is a silent no-op | `top()` returns `None` → early return; post-teardown use is unsupported | `test_save_after_teardown_raises` |
| SE5 | `push()` calls `_cleanup_exiting_scene` on old top — owned sprites removed, timers cancelled | Intentional resource hygiene; pushed-over scenes recreate resources in `on_reveal()` | `test_owned_sprites_removed_on_pop` + script verification |
| SE6 | `push()` fires `on_exit()` on the old top scene (not just pop/replace) | Consistent with SE5 cleanup; `on_reveal()` re-enters when pushed scene is popped | `test_teardown_calls_scene_on_exit` |
| SE7 | Failed save (non-serializable state) leaves original file untouched | Atomic write: serialize to `.tmp` then `replace()` — failure before replace preserves original | `test_save_after_failed_save_succeeds` |

## Blocked / Not Tested

| Feature | Directory | Reason |
|---------|-----------|--------|
| Engine physics (continuous collision, tunneling, layers, callbacks) | — | Not part of Saga2D; no `pymunk`/Box2D-style API in framework |
| Visual rendering verification | tests/visual/ | Requires display + pyglet |
| Screenshot golden-image comparison | tests/screenshot/ | Requires display + pyglet |
| AI-powered visual verification | tests/visual_verify/ | Requires Anthropic API key |
| Audio playback (actual output) | — | Mock-only; no audio hardware tests |
| Performance / stress at scale | — | No load tests exist |

## Totals (through Stage 14)

- **55+ feature areas** identified and tested
- **All fully passing** (including 24 fixed bugs)
- **1 environment-dependent** (Game.run() with SAGA2D_HEADLESS — 3 tests skipped)
- **0 known-issues** remaining
- **1 area (visual) blocked** by display requirement
- **2304 unit tests** collected, all pass, 3 skipped
- **Findings**: 24 bugs fixed (F1, F3–F10, F12, F15–F16, F18–F19, F21–F27), 5 documented behaviors (F11, F13, F14, F17, F20), 11 sharp edges (SE1–SE11)

## Fresh Re-test — Comprehensive Edge Cases & Adversarial (2026-03-23)

### New test files (345 new tests)

| File | Tests | Areas Covered |
|------|-------|---------------|
| `tests/test_kodo_core_fresh.py` | 47 | Game headless mode, deferred ops, action composition, scene stack depth 100, quit idempotent, timer/tween edge cases |
| `tests/test_kodo_systems_fresh.py` | 99 | Save edge cases (unicode, deep nesting, corruption, slot validation), audio (volume clamp, crossfade, pools), input (key stealing, immutability), assets (caching, missing files), FSM (atomicity, rollback) |
| `tests/test_kodo_rendering_ui_fresh.py` | 131 | Sprite (opacity clamping, large coords, removal idempotent), camera (NaN/Inf, follow removed, pan cancel, shake reset, bounds), particles (burst 0, zero lifetime), UI widgets (empty data, bounds, negative spacing), theme resolve |
| `tests/test_kodo_adversarial_fresh.py` | 68 | Re-entrant scene ops, lifecycle abuse, 500+ sprites stress, 100 tweens, audio stress, multiple Game instances, save 100 slots, camera state transitions, button self-removal, 1000 sprite cleanup, animation queue 100, iteration-during-modification |

### Fixes Applied

| Fix | Description |
|-----|-------------|
| `tests/core/test_game.py` | Added `@pytest.mark.skipif(SAGA2D_HEADLESS)` to 3 game.run() tests so they skip gracefully instead of failing |

### Findings

**F21: game.run() tests fail under SAGA2D_HEADLESS=1 (low severity, usability)**
- 3 tests in `tests/core/test_game.py` call `game.run()` which raises RuntimeError when SAGA2D_HEADLESS is set
- Root cause: Tests don't account for the env var guard added for CI/headless safety
- Fix: Added `@pytest.mark.skipif` decorator
- These tests pass when SAGA2D_HEADLESS is unset

**No new bugs found.** All 345 adversarial and edge case tests pass. The framework handles:
- Re-entrant scene operations (push during on_enter, pop during update, etc.)
- Exception rollback in scene lifecycle hooks
- 500+ sprites in single scene without crash
- 100 simultaneous tweens
- 100 save slots written rapidly
- Sprite removal during action callbacks
- Camera state transitions (follow -> center_on -> pan_to)
- Button self-removal on click
- 1000 sprite create/remove with proper cleanup
- Deep scene stack (100 levels)
- Empty and boundary inputs for all UI widgets

### Test counts after fresh re-test

| Suite | Count | Result |
|-------|-------|--------|
| Full suite (excluding visual_verify) | **2031** | pass |
| Skipped (SAGA2D_HEADLESS) | **3** | skip |
| New edge case tests | **345** | pass |

### Updated Totals

- **2031 tests passing**, 3 skipped, 0 failures
- **50+ feature areas** covered by 345 fresh tests
- **0 new bugs found** — framework is remarkably robust
- **1 test infrastructure fix** (headless skip markers)

## Stage 8 — Edge Cases & Adversarial Testing (2026-03-23)

### New test files
- `tests/test_kodo_edge_cases.py` — 129 edge case tests
- `tests/test_kodo_regression.py` — 14 regression tests for F15–F19

### Findings (5 bugs fixed, 1 documented)

| ID | Severity | Description | Fixed? |
|----|----------|-------------|--------|
| **F15** | Medium | `Delay(NaN)` accepted — creates unstoppable action that never completes | Yes — added `math.isfinite()` check |
| **F16** | Medium | `MoveTo(speed=NaN)` accepted — crashes with ValueError during update | Yes — added `math.isfinite()` check |
| **F17** | Low | `ParticleEmitter(images=[])` crashes on `burst()` with IndexError | Documented (clear error message) |
| **F18** | Medium | `FSM.trigger()` not atomic — on_enter failure leaves state changed | Yes — added rollback in try/except |
| **F19** | Low | `SaveManager(str)` crashes — AttributeError: 'str' has no 'mkdir' | Yes — auto-converts str to Path |
| **F20** | Low | `replace()` during `on_enter()` causes recursion limit (pathological case) | Documented |

### Test counts after Stage 8

| Suite | Count | Result |
|-------|-------|--------|
| Full suite (excluding visual_verify) | **1554** | pass |
| Edge cases (test_kodo_edge_cases.py) | **129** | pass |
| Regression (test_kodo_regression.py) | **14** | pass |

## Stage 9 — Deep Edge Cases & New Bug Fixes (2026-03-23, Run 2)

### New test files (136 new tests)

| File | Tests | Areas Covered |
|------|-------|---------------|
| `tests/test_kodo_animation_tween_edge.py` | 40 | AnimationPlayer frame_duration validation (0, negative, NaN, Inf), AnimationDef validation, normal behavior, single frame, large dt, TweenManager duration edge cases (0, negative, NaN, Inf), tween conflicts, easing curves |
| `tests/test_kodo_widget_edge.py` | 51 | List(item_height=0) click/scroll/motion, empty List, Grid(0x0), Grid cell_at(0,0), TabGroup empty/invalid/add-remove, ProgressBar(max=0, NaN, negative), Tooltip(delay=0, negative, large dt), TextBox typewriter with text mutation, DataTable empty rows/columns |
| `tests/test_kodo_systems_edge.py` | 41 | ParticleEmitter inverted ranges/zero rate/burst-after-remove/NaN position/large dt, Camera shake(intensity=0, duration=0, decay=0)/follow removed/follow(None)/pan during shake/inverted bounds/edge scroll margin=0/center_on NaN, Audio crossfade-during-crossfade/wrong-case channel/empty asset/volume boundaries, CursorManager set/default/visible |

### Findings (4 bugs found and fixed)

| ID | Severity | Description | Fixed? |
|----|----------|-------------|--------|
| **F21** | Critical | `AnimationPlayer(frame_duration=0, loop=True)` causes infinite loop — game hangs permanently | Yes — added `frame_duration > 0 and isfinite()` validation |
| **F22** | Critical | `AnimationPlayer(frame_duration<0, loop=True)` causes infinite loop — game hangs permanently | Yes — same validation fix as F21 |
| **F23** | Medium | `AnimationDef/AnimationPlayer` accept NaN/Inf frame_duration — animation stuck forever or never advances | Yes — same validation fix |
| **F24** | Medium | `List(item_height=0)` crashes with ZeroDivisionError on click/motion events | Yes — added `item_height <= 0` guard |

### Fixes applied

| File | Change |
|------|--------|
| `saga2d/animation.py` | Added `import math` and `if not math.isfinite(frame_duration) or frame_duration <= 0: raise ValueError(...)` to both `AnimationDef.__init__` and `AnimationPlayer.__init__` |
| `saga2d/ui/widgets.py` | Added `if self._item_height <= 0: return True` guard before division in `List.on_event()` for both click and motion event paths |

### Test counts after Stage 9

| Suite | Count | Result |
|-------|-------|--------|
| Full suite (excluding visual/screenshot) | **2197** | pass |
| New edge case tests (3 files) | **136** | pass |
| Skipped (SAGA2D_HEADLESS) | **3** | skip |

### Additional observations (not bugs)

| Observation | Detail |
|-------------|--------|
| ParticleEmitter accepts NaN position | Setter silently accepts NaN, but `burst()` then crashes in `Sprite.__init__` with clear ValueError. Error surfaces at the right place. |
| Camera inverted world_bounds | Clamps to single fixed position — not wrong but likely not intended. No error raised. |
| ProgressBar fraction with NaN value | Python's min/max NaN quirk makes fraction=1.0, showing full bar. CPython behavior, not framework bug. |
| Grid.set_cell allows out-of-bounds | No bounds validation — component stored but never drawn/hit-tested. Harmless. |
| TabGroup has no remove_tab() API | Removing a child component doesn't clean up internal tab tracking. Design gap, not bug. |

## Stage 10 — NaN/Inf Validation Gaps in Tween/Timer/Actions/Widgets (2026-03-23, Run 3)

### Systematic NaN/Inf validation audit

This run systematically audited all numeric parameters across the framework for NaN/Inf handling.
The IEEE 754 standard makes NaN comparison tricky: `NaN < 0` is False, `NaN <= 0` is False,
`NaN >= 0` is False, `NaN > 0` is False. This means guards like `if x < 0: raise` silently
pass NaN through.

### Regression tests added (F21R-F25R in test_kodo_regression.py)

| Finding | Tests | Before Fix | After Fix |
|---------|-------|-----------|-----------|
| F21R: TweenManager.create() NaN/Inf/neg duration | 6 tests | 4 fail (NaN, Inf, -Inf, negative all accepted) | 6 pass |
| F22R: TimerManager.after() NaN/Inf delay | 5 tests | 2 fail (NaN, Inf accepted) | 5 pass |
| F23R: TimerManager.every() NaN/Inf interval | 3 tests | 2 fail (NaN, Inf accepted) | 3 pass |
| F24R: FadeOut/FadeIn NaN/Inf/neg duration | 10 tests | 6 fail (all invalid durations accepted) | 10 pass |
| F25R: TextBox NaN/Inf typewriter_speed | 6 tests | 3 fail (NaN, Inf, -Inf accepted) | 6 pass |
| **Total** | **30** | **17 fail** | **30 pass** |

### Source files changed

| File | Change |
|------|--------|
| `saga2d/util/tween.py` | Added `if not math.isfinite(duration) or duration < 0: raise ValueError(...)` in `create()` after from/to validation |
| `saga2d/util/timer.py` | Changed `after()`: `if delay < 0` → `if not math.isfinite(delay) or delay < 0`; Changed `every()`: `if interval <= 0` → `if not math.isfinite(interval) or interval <= 0` |
| `saga2d/actions.py` | Added `if not math.isfinite(duration) or duration < 0: raise ValueError(...)` to `FadeOut.__init__` and `FadeIn.__init__` |
| `saga2d/ui/widgets.py` | Added `import math`; Added `if not math.isfinite(typewriter_speed): raise ValueError(...)` to `TextBox.__init__` |

### Edge-case test files updated

| File | Tests | Notes |
|------|-------|-------|
| `tests/test_kodo_actions_edge.py` | 32 | Updated tests that documented pre-fix NaN/Inf acceptance to expect ValueError |
| `tests/test_kodo_timer_widget_edge.py` | 72 | Updated timer NaN/Inf tests and TextBox NaN/Inf tests to expect ValueError |
| `tests/test_kodo_camera_drag_edge.py` | 31 | Unchanged — no NaN validation bugs in camera/drag/save |

### Test counts after Stage 10

| Suite | Count | Result |
|-------|-------|--------|
| Full suite (excluding visual_verify) | **2197** | pass |
| Skipped (SAGA2D_HEADLESS) | **3** | skip |
| Stage 10 regression tests (F21-F25) | **30** | pass |
| Total kodo edge-case tests | **179** | pass |

### Updated cumulative totals

- **2197 tests passing**, 3 skipped, 0 failures
- **51 feature areas** tested
- **22 bugs found and fixed** across all runs (F1, F3-F10, F12, F15-F16, F18-F19, F21-F25)
- **5 documented behaviors** (F11, F13, F14, F17, F20)
- **10 sharp edges** (SE1-SE10)
- **0 known defects remaining** in source code

## Stage 11 — Discovery: New Gap Areas (2026-03-23)

### Environment

| Field | Value |
|-------|-------|
| Commit | `4227501` |
| Python | `.venv/bin/python` (3.13.2) |
| Install | `uv pip install -e ".[dev]"` |
| Test cmd | `.venv/bin/python -m pytest --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q` |
| Baseline | **2197 passed**, 3 skipped, 0 failures |

### Target Gap Areas (from run-status)

Seven areas identified for deeper testing:

1. **AnimationPlayer infinite loop with frame_duration=0** (critical) — already fixed in Stage 9
2. **List ZeroDivisionError with item_height=0** — already fixed in Stage 9
3. **Particle lifetime=(0,0) division by zero**
4. **Untested widget edge cases** (Grid 0×0, TabGroup empty, DataTable empty)
5. **Tween duration edge cases**
6. **Camera advanced scenarios**
7. **Audio crossfade state corruption**

### Gap 1: AnimationPlayer frame_duration=0 — ALREADY FIXED (Stage 9)

**Source:** `saga2d/animation.py`
- `AnimationDef.__init__`: validates `if not math.isfinite(frame_duration) or frame_duration <= 0: raise ValueError`
- `AnimationPlayer.__init__`: same validation
- **Tests:** `tests/test_kodo_animation_tween_edge.py` — 40 tests covering 0, negative, NaN, Inf frame_duration

**Status:** ✅ No further work needed.

### Gap 2: List item_height=0 ZeroDivisionError — ALREADY FIXED (Stage 9)

**Source:** `saga2d/ui/widgets.py`, `List` class
- Line 715–716: `if self._item_height <= 0: return True` guard in click handler
- Line 737–738: same guard in motion handler
- Line 838–840: `_visible_count()` returns 0 when item_height ≤ 0

**Tests:** `tests/test_kodo_widget_edge.py` — Tests 1–8 cover item_height=0 click, scroll, motion, empty items

**Status:** ✅ No further work needed.

### Gap 3: Particle lifetime=(0,0) Division by Zero

**Source:** `saga2d/rendering/particles.py`

| Method | Line | Behavior |
|--------|------|----------|
| `__init__` | 97, 116 | `lifetime` param: `tuple[float,float]`, default `(0.3, 0.8)`, **NO validation** for (0,0)/negative/NaN/Inf |
| `_spawn_particle` | 261 | `total_lifetime = random.uniform(*self._lifetime)` → 0 when (0,0) |
| `update` | 210–212 | **GUARDED**: `if p.fade_out and p.total_lifetime > 0: ratio = p.remaining / p.total_lifetime` |
| `update` | 201 | Particles with lifetime=0 die immediately (`remaining=0`, `0 <= 0` is True) |
| `burst` | 159–160 | Guards `n <= 0` (safe) |

**Division risk:** SAFE — the `p.total_lifetime > 0` guard on line 210 prevents ZeroDivisionError.

**Existing tests:**
- `tests/test_kodo_edge_cases.py::test_emitter_lifetime_zero_zero` — confirms particles die immediately
- `tests/test_kodo_systems_edge.py::TestParticleEmitterInvertedRanges` — inverted lifetime (0.8, 0.3)

**Remaining test gaps for particles:**

| Gap | File/Line | Fixture idea |
|-----|-----------|-------------|
| **lifetime=(0,0) + fade_out=True** — fade code path skipped but should confirm opacity stays 255 | particles.py:210 | Create emitter with `lifetime=(0,0), fade_out=True`, burst, tick tiny dt, verify sprite opacity unchanged before death |
| **Negative lifetime e.g. (-1,-0.5)** — `random.uniform(-1,-0.5)` gives negative; particles immediately die | particles.py:201 | Create emitter with `lifetime=(-1,-0.5)`, burst, assert particles die on first update |
| **NaN lifetime e.g. (float('nan'), float('nan'))** — `random.uniform(NaN, NaN)` returns NaN → `NaN <= 0` is False → **particle never dies (memory leak)** | particles.py:201 | **POTENTIAL BUG PB1**: burst 5, tick 100s, assert all dead → would fail |
| **Inf lifetime** — particle lives forever (`inf - dt = inf`, never ≤ 0) | particles.py:201 | May be intentional for immortal particles, but untested |
| **continuous_rate + lifetime=0** — spawns particles that die immediately each frame | particles.py:190–195 | Stress test: continuous_rate=100, lifetime=(0,0), tick 1s, assert no buildup |

### Gap 4: Widget Edge Cases (Grid 0×0, TabGroup empty, DataTable empty)

**Source:** `saga2d/ui/widgets.py`

#### Grid 0×0

| Aspect | Line | Status |
|--------|------|--------|
| Grid(0, 0) construction | 911 | SAFE — no validation needed, loops empty |
| `selected` setter with 0 cols/rows | 966–968 | GUARDED: sets `_selected = None` |
| `_cell_at(x, y)` with 0 cell_stride | 1159–1160 | GUARDED: returns `None` |
| `on_draw()` with 0×0 | 1070 | SAFE — `range(0)` produces nothing |
| `set_cell(0, 0, comp)` on 0×0 grid | 977 | ALLOWED but never drawn |

**Existing tests:** `tests/test_kodo_widget_edge.py` Tests 9–13

**Remaining test gaps:**

| Gap | Fixture idea |
|-----|-------------|
| Grid(0,0) + keyboard navigation (arrow keys) | Inject key events, verify no crash, selection stays None |
| Grid negative dimensions e.g. Grid(-1, -1) | Verify behavior (likely safe: `range(-1)` → empty) |

#### TabGroup empty

| Aspect | Line | Status |
|--------|------|--------|
| `TabGroup()` construction | 1420–1443 | SAFE — `_active_tab = None` |
| `select_tab(unknown)` | 1479–1489 | Raises `KeyError` with available tabs list |
| `on_draw()` empty | 1543 | SAFE — iterates empty `_tab_labels` |
| `active_tab` property with no tabs | 1452 | Returns `None` |

**Existing tests:** `tests/test_kodo_widget_edge.py` Tests 14–17

**Remaining test gaps:**

| Gap | Fixture idea |
|-----|-------------|
| `add_tab()` then `select_tab()` on previously-empty TabGroup | Verify first tab becomes active, second can be selected |
| `select_tab()` on empty TabGroup | Should raise KeyError with empty list message |

#### DataTable empty/0 columns

| Aspect | Line | Status |
|--------|------|--------|
| `DataTable(columns=[], rows=[])` | 1717 | SAFE — `_columns = []` |
| `_effective_col_widths(padding)` with 0 cols | 1982–1983 | Returns `[]` |
| `on_draw()` with 0 cols | 1854 | SAFE — `range(0)` for columns |
| `_visible_data_rows()` with row_height=0 | 1993–1995 | GUARDED: returns 0 |
| Short rows (fewer cells than columns) | 1947 | GUARDED: falls back to `""` |

**Existing tests:** `tests/test_kodo_widget_edge.py` Tests 32–33

**Remaining test gaps:**

| Gap | Fixture idea |
|-----|-------------|
| DataTable click on empty table | Inject click event, verify no crash, no selection |
| DataTable with 1 column, 100 rows — scroll behavior | Add rows, verify scroll offset calculations |
| DataTable add_row after draw | Verify row appears on next draw |

### Gap 5: Tween Duration Edge Cases

**Source:** `saga2d/util/tween.py`

| Validation | Line | Status |
|------------|------|--------|
| `duration` NaN/Inf → ValueError | 112–114 | ✅ Fixed in Stage 10 |
| `duration < 0` → ValueError | 112–114 | ✅ Fixed in Stage 10 |
| `duration = 0` → completes on first update | 157 | ✅ Works, tested |
| `from_val`/`to_val` NaN/Inf → ValueError | 108–110 | ✅ Original code |
| `dt` NaN/Inf → silent skip | 150–151 | ✅ Safe |

**Existing tests:** `tests/actions/test_tween.py` (417 lines), `tests/test_kodo_animation_tween_edge.py` (535 lines), `tests/test_kodo_regression.py::TestF21TweenDurationValidation`

**Remaining test gaps:**

| Gap | Fixture idea |
|-----|-------------|
| Tween with `from_val == to_val` (no-op tween) | Create tween where start = end, verify completes, on_complete fires |
| Multiple tweens on same property simultaneously | Create two tweens on `obj.x`, verify last-write-wins behavior |
| Cancel tween inside `on_complete` callback | Verify no crash, tween manager state consistent |
| Tween target property raises on set | Use `@property` with setter that raises, verify tween removed gracefully |
| Tween with dt=0 (zero-time step) | Verify tween does not advance, no division issues |

### Gap 6: Camera Advanced Scenarios

**Source:** `saga2d/rendering/camera.py`

| Feature | Status | Existing Tests |
|---------|--------|----------------|
| follow() removed sprite | ✅ Covered | test_follow_removed_sprite_clears_follow |
| pan_to() NaN target | ✅ Covered | test_pan_to_nan_raises_value_error |
| pan_to() duration=0 | ✅ Covered | test_pan_to_duration_zero_instant |
| shake() duration≤0 reset | ✅ Covered | test_shake_duration_zero_resets |
| shake + screen_to_world | ✅ Covered | TestShakePickingRegression (7 tests) |
| Inverted world_bounds | ✅ Covered | test_inverted_bounds_clamps_to_left_top |
| pan_to during shake | ✅ Covered | test_shake_during_pan_to |
| Double pan_to | ✅ Covered | test_pan_to_interrupted_by_another_pan_to |

**Remaining test gaps:**

| Gap | File/Line | Fixture idea |
|-----|-----------|-------------|
| `pan_to(duration=Inf)` | camera.py:300 | TweenManager rejects Inf duration (ValueError from tween.py:112). Verify camera propagates ValueError |
| `pan_to(duration=very_small)` e.g. 0.0001 | camera.py:300 | Verify completes within 1–2 frames |
| `shake(decay=0)` — constant intensity | camera.py:230 | `(1 - progress)^0 = 1.0` always → offsets stay at full intensity. Verify behavior |
| `update(dt=0)` — zero time step | camera.py:366 | Verify no division, no movement, state unchanged |
| `follow()` then `pan_to()` in same frame | camera.py | Verify follow is disabled, pan takes over |
| Camera with viewport larger than world_bounds | camera.py:458–467 | Verify clamp behavior (locks to top-left) |
| `center_on(NaN, NaN)` | camera.py:131 | Should raise ValueError — verify |

### Gap 7: Audio Crossfade State Corruption

**Source:** `saga2d/audio.py`

| Scenario | Lines | Status |
|----------|-------|--------|
| Crossfade same track → no-op | 248–249 | ✅ Covered |
| Crossfade with no current music → play_music | 250–252 | ✅ Covered |
| Crossfade during active crossfade | 255 (`_cancel_crossfade`) | ✅ Covered (test_kodo_systems_edge.py:546–580) |
| stop_music() during crossfade | 228–234 | ✅ Covered |
| play_music() during crossfade (calls stop_music first) | 201–226 | ✅ Covered |

**`_CrossfadeProxy` (lines 30–72):** bridges tweens to backend volume updates. `new_volume` setter also updates `_current_player_base_volume`.

**Remaining test gaps:**

| Gap | File/Line | Fixture idea |
|-----|-----------|-------------|
| **Channel volume change mid-crossfade** | audio.py:140–150, proxy:52–72 | Start crossfade, tick 50%, call set_volume("master", 0.5), tick to completion. Verify final volume is master×music×1.0 |
| **crossfade_music(duration=0.0)** — instant crossfade | audio.py:236, tween.py:157 | Both tweens complete on first update. Old player stopped, new at full volume |
| **crossfade_music() with missing asset** — AssetNotFoundError | audio.py:262 | Crossfade track_a→nonexistent: should raise. Verify track_a state consistency |
| **Sound pool duplicate names** — `register_pool("hit", ["a", "a", "b"])` | audio.py:308–317 | Verify no-repeat logic still works (could pick "a" twice since two indices map to "a") |
| **play_pool on re-registered pool** | audio.py:308–317 | Re-register with different sounds, verify `_pool_last` behavior |

### Potential Bugs (Unconfirmed)

| ID | Area | Description | Risk |
|----|------|-------------|------|
| **PB1** | Particles | `lifetime=(NaN, NaN)` → `random.uniform(NaN, NaN)` returns NaN → `remaining=NaN` → `NaN <= 0` is False → **particle never dies (memory leak)** | Medium — no production path likely produces NaN lifetime, but no validation exists |
| **PB2** | Particles | `lifetime=(Inf, Inf)` → particle lives forever (`inf - dt = inf`, never ≤ 0) — intentional? | Low — could be valid use case for immortal particles |
| **PB3** | Audio | `crossfade_music(duration=0.0)` → tween completes instantly → should work but untested | Low — behavior correct by construction |
| **PB4** | Camera | `pan_to(x, y, duration=Inf)` → `TweenManager.create()` raises `ValueError` on Inf duration — camera silently fails to pan? | Low — should propagate ValueError to caller |
| **PB5** | Audio | `crossfade_music("missing_track")` → `_cancel_crossfade()` runs first, then `AssetNotFoundError` — state consistent but old crossfade interrupted | Low — error handling is correct |

### Test File Plan

New test file: `tests/test_kodo_stage11_gaps.py`

**Proposed test classes:**

| Class | Est. Tests | Gap |
|-------|-----------|-----|
| `TestParticleLifetimeEdgeCases` | 5–6 | Gap 3: NaN lifetime (PB1), negative lifetime, (0,0)+fade_out, continuous+lifetime=0 |
| `TestGridAdvancedEdgeCases` | 2–3 | Gap 4: Grid(0,0) keyboard nav, negative dimensions |
| `TestTabGroupAdvancedEdgeCases` | 2–3 | Gap 4: add_tab on empty, select_tab on empty |
| `TestDataTableAdvancedEdgeCases` | 3–4 | Gap 4: click on empty, add_row after draw |
| `TestTweenAdvancedEdgeCases` | 4–5 | Gap 5: from==to, concurrent tweens, cancel in callback, dt=0 |
| `TestCameraAdvancedEdgeCases` | 5–6 | Gap 6: pan_to(Inf), shake(decay=0), update(dt=0), center_on(NaN) |
| `TestAudioCrossfadeEdgeCases` | 5–7 | Gap 7: volume mid-crossfade, duration=0, missing asset, pool duplicates |

**Estimated total: ~30–35 new tests**

## Stage 11B — Focused Code Audit: 5 Core Modules (2026-03-23)

### Scope

Line-by-line audit of `saga2d/actions.py`, `saga2d/util/tween.py`, `saga2d/util/timer.py`, `saga2d/ui/widgets.py`, `saga2d/ui/component.py` across four edge-case categories.

### Audit Results Summary

| Category | Entry Points Audited | OK | Already Fixed | New Findings |
|----------|---------------------|-----|---------------|-------------|
| Zero-duration / zero-value | 13 | 10 | 1 (F24) | 1 (EC1) |
| NaN / Inf (constructor + runtime) | 15 | 3 | 10 (F15–F25R) | 1 (EC2) |
| Empty / zero-sized widgets | 11 | 10 | 0 | 0 |
| Mutation-during-dispatch | 11 | 6 | 1 (F6) | 3 (EC3–EC5) |

### New Edge Cases (EC1–EC5)

| ID | Sev | File | Class.Method | Description | Repro |
|----|-----|------|-------------|-------------|-------|
| **EC1** | Med | `ui/widgets.py` | `DataTable.on_event()` | `row_height=0` → `ZeroDivisionError` at `int(relative_y // self._row_height)`. Missing guard matching List's F24 fix. | `DataTable(["A"], [["x"]], row_height=0)`, click at `y > header_height` |
| **EC2** | Low | `actions.py` | `MoveTo.update()` | `dt=NaN` → `sprite.position = (NaN, NaN)`. No production path (Game clock never yields NaN). | `MoveTo((100,100), 100).update(float('nan'))` after start on sprite |
| **EC3** | Med | `ui/component.py` | `_UIRoot._update_recursive()` | Iterates `component._children` directly (no snapshot). `update(dt)` adding/removing children → skip/double-visit. | Child's `update()` calls `parent.remove(sibling)` |
| **EC4** | Med | `ui/component.py` | `Component.draw()` | Same: `for child in self._children` without snapshot. Mutation during `on_draw()` → corrupted iteration. | Child's `on_draw()` removes a sibling |
| **EC5** | Med | `ui/component.py` | `Component.handle_event()` | `reversed(self._children)` without snapshot. Child removing sibling during dispatch → stale iterator. | Child's `handle_event()` calls `parent.remove(other_child)` |

### Confirmed Safe Patterns (same modules)

| Site | Snapshot? | Notes |
|------|-----------|-------|
| `TweenManager.update()` | `list(self._tweens.items())` | Callbacks safe to create/cancel |
| `TimerManager.update()` | `list(self._timers.items())` | Callbacks safe to schedule/cancel |
| `Game._update_actions()` | `list(self._action_sprites)` | Action callbacks safe to add/remove sprites |
| `Sequence.update()` | Index-based | No list iteration |
| `Parallel.update()` | Constructor-fixed list | Never mutated |
| `Repeat.update()` | `deepcopy` per iteration | Fresh copy |

### Recommendations

1. **EC1 (quick fix):** Add `if self._row_height <= 0: return True` in `DataTable.on_event()` click path.
2. **EC3–EC5 (defensive):** Change `list(self._children)` snapshot in `draw()`, `handle_event()`, `_update_recursive()`.
3. **EC2 (low priority):** Add `isfinite(dt)` guard in action `update()` methods.

### Tests Needed for New Findings

| Finding | Test | Assert |
|---------|------|--------|
| EC1 | `test_datatable_row_height_zero_click` | No ZeroDivisionError |
| EC1 | `test_datatable_row_height_zero_scroll` | Scroll doesn't crash |
| EC3 | `test_update_tree_child_removal_during_update` | No crash on sibling removal |
| EC4 | `test_draw_child_removal_during_draw` | No crash on sibling removal |
| EC5 | `test_handle_event_child_removal_during_dispatch` | No crash on sibling removal |
| EC2 | `test_moveto_update_nan_dt` | Position unchanged or error |

### Full report: `.kodo/test-report.md`

## Stage 11C — Focused execution: particles, empty widgets, tween, camera (2026-03-23)

**Goal:** Re-run automated coverage for non-browser edge cases called out in Stage 11 discovery, plus a few manual API probes (no `game.run()`, no pyglet window).

### Import / API smoke

```bash
cd /path/to/saga2d
SAGA2D_HEADLESS=1 uv run python -c "
from saga2d import Game, Scene
from saga2d.ui.widgets import Grid, TabGroup, DataTable
from saga2d.rendering.camera import Camera
from saga2d.util.tween import TweenManager
g = Game('t', backend='mock', resolution=(400, 300))
g.push(Scene())
Grid(0, 0)
TabGroup()
DataTable(columns=[], rows=[], width=100, height=100)
Camera((800, 600))
tm = TweenManager()
class O: pass
o = O(); o.x = 0.0
tm.create(o, 'x', 0.0, 1.0, duration=0.0)
tm.update(0.0)
assert o.x == 1.0
g.tick(0.016)
g._teardown()
print('import_smoke_ok')
"
```

| Result | Notes |
|--------|--------|
| **pass** | `Label` is **not** exported from `saga2d.ui.widgets` (use `saga2d.ui.components` / package re-exports). |

### Focused pytest bundle (449 tests)

```bash
SAGA2D_HEADLESS=1 uv run python -m pytest \
  tests/rendering/test_particles.py \
  tests/rendering/test_camera.py \
  tests/actions/test_tween.py \
  tests/test_kodo_animation_tween_edge.py \
  tests/test_kodo_widget_edge.py \
  tests/test_kodo_systems_edge.py \
  tests/test_kodo_camera_drag_edge.py \
  tests/test_kodo_rendering_ui_fresh.py::TestParticleBurst \
  tests/test_kodo_rendering_ui_fresh.py::TestParticleContinuous \
  tests/test_kodo_rendering_ui_fresh.py::TestParticleLifetime \
  tests/test_kodo_rendering_ui_fresh.py::TestParticleRemoveDuringBurst \
  tests/test_kodo_rendering_ui_fresh.py::TestParticlePositionUpdate \
  tests/test_kodo_rendering_ui_fresh.py::TestCameraCenterOn \
  tests/test_kodo_rendering_ui_fresh.py::TestCameraFollow \
  tests/test_kodo_rendering_ui_fresh.py::TestCameraPanTo \
  tests/test_kodo_rendering_ui_fresh.py::TestCameraShake \
  tests/test_kodo_rendering_ui_fresh.py::TestCameraEdgeScroll \
  tests/test_kodo_rendering_ui_fresh.py::TestCameraKeyScroll \
  tests/test_kodo_rendering_ui_fresh.py::TestCameraCoordinateConversion \
  tests/test_kodo_rendering_ui_fresh.py::TestCameraWorldBounds \
  tests/test_kodo_edge_cases.py::TestParticleEdgeCases \
  tests/test_kodo_edge_cases.py::TestCameraEdgeCases \
  tests/test_kodo_timer_widget_edge.py::TestGridEdgeCases \
  tests/test_kodo_timer_widget_edge.py::TestTabGroupEdgeCases \
  tests/test_kodo_timer_widget_edge.py::TestDataTableEdgeCases \
  -q --tb=no
```

| Metric | Value |
|--------|-------|
| Passed | **449** |
| Failed | **0** |
| Duration | ~0.4 s (local) |

**What this exercises (high level):**

| Area | Automated coverage |
|------|-------------------|
| **Particle lifetime edges** | `(0,0)` immediate death; burst 0; inverted lifetime range; large `dt` kills all; continuous rate 0 / negative; NaN position → fail at `Sprite` creation |
| **Grid / TabGroup / DataTable empty** | `Grid(0,0)` draw, selection, `_cell_at`, preferred size; empty `TabGroup` draw/update, `select_tab` → `KeyError`; empty rows/columns DataTable, click on empty |
| **Tween duration** | `duration=0` completes on first update (including `dt=0`); negative / NaN / Inf rejected at `create()`; large `dt`; concurrent tweens same property |
| **Camera advanced** | shake intensity/duration/decay edge cases; follow removed/`None`; pan during shake; inverted bounds; edge scroll margin 0; `center_on` NaN/Inf; pan cancel; narrow bounds; screen/world NaN (drag_edge); fresh-file camera suites |

### Manual probes (not separate pytest tests)

| Probe | Command / snippet | Result |
|-------|-------------------|--------|
| **`Camera.pan_to` + `duration=inf`** | Create `Game(mock)` + `push(Scene())` so `tween()` has a manager; `Camera((800,600)).pan_to(400, 300, float('inf'))` | **`ValueError`** — `duration must be a finite number >= 0, got inf` (from `TweenManager.create` via `tween()`) |
| **PB1 — NaN `lifetime` on particles** | `ParticleEmitter(..., lifetime=(nan,nan))` then **`burst(n)`** (constructor `count` does not auto-spawn); `update` in a loop | Particles keep `remaining=nan`; **`nan <= 0` is false** → **never expire** until `remove()` — confirms documented leak risk for invalid lifetime |
| **Grid 0×0 in live scene + click** | `Scene.on_enter`: `ui.add(Grid(0,0,...))`, `compute_layout` with `g._resolution`, `inject_click`, `tick` | **pass** — no crash |
| **Grid + keyboard** | — | **N/A** — `Grid.on_event` only handles click/motion; no arrow-key path to test for 0×0 |

**Verdict:** All selected automated tests **pass**. **PB1** (NaN lifetime + burst) remains a **sharp edge** (immortal particles until `remove()`); **not** a regression from this pass.

## Stage 12 — Audio Crossfade State Corruption Investigation + Fix Verification (2026-03-23)

### Scope

Independent investigation of three areas with concrete executable reproductions:

1. **Audio crossfade state corruption** — systematic probing for bugs in `_CrossfadeProxy`, channel volume changes mid-crossfade, duration=0, missing assets, rapid interruptions, pool edge cases
2. **AnimationPlayer frame_duration=0** — sanity-check that the Stage 9 fix (F21/F22/F23) is still in place via executable repros
3. **List item_height=0** — sanity-check that the Stage 9 fix (F24) is still in place via executable repros

### Environment

| Field | Value |
|-------|-------|
| Commit | `4227501` (same as Stage 11) |
| Python | `.venv/bin/python` (3.13.2) |
| Test cmd | `SAGA2D_HEADLESS=1 .venv/bin/python -m pytest tests/test_kodo_crossfade_repro.py -v` |

### Test file: `tests/test_kodo_crossfade_repro.py` — 39 tests, all pass

| Class | Tests | What's Tested |
|-------|-------|---------------|
| `TestCrossfadeVolumeChangeMidFade` | 5 | master/music/both channel volume change mid-crossfade; old player updated on next tick; rapid volume changes between ticks |
| `TestCrossfadeDurationZero` | 2 | duration=0 instant crossfade completes on first tick; respects channel volumes |
| `TestCrossfadeMissingAsset` | 2 | AssetNotFoundError preserves state; missing asset during active crossfade cleans up properly |
| `TestCrossfadeRapidInterruption` | 3 | 4 rapid crossfades no player leak; crossfade→play_music cleanup; stop→crossfade from nothing |
| `TestCrossfadeSetVolumeOnlyUpdatesCurrentPlayer` | 1 | **Documents known one-frame desync**: set_volume() immediately updates _current_player but NOT _crossfade_old_player; next tick corrects it via proxy |
| `TestSoundPoolDuplicateNames` | 2 | Duplicate names in pool; re-register pool resets _pool_last |
| `TestCrossfadeCompletionCallback` | 2 | _finish_crossfade stops old player; base volume reaches 1.0 |
| `TestCrossfadeWithDurationNegative` | 1 | Negative duration raises ValueError (via TweenManager validation) |
| `TestAnimationPlayerFrameDurationZero` | 10 | AnimationDef + AnimationPlayer reject 0, negative, NaN, Inf, -Inf; normal operation still works; loop=True with valid duration does not hang |
| `TestListItemHeightZero` | 5 | item_height=0 click/motion no crash; negative item_height guarded; _visible_count returns 0; normal click still works |
| `TestCrossfadeProxyDirectly` | 2 | _CrossfadeProxy uses live _volumes dict; new_volume setter updates _current_player_base_volume |
| `TestCrossfadeEdgeStates` | 4 | _cancel_crossfade when no crossfade; double stop_music; crossfade to same name after stop+play; _teardown during crossfade |

### Findings

#### Audio Crossfade: No State Corruption Bug Found

The crossfade system is well-designed and resilient:

| Scenario | Result | Detail |
|----------|--------|--------|
| **Volume change mid-crossfade** | **SAFE** | `_CrossfadeProxy` reads `_volumes` dict live on each setter call, so the next tween tick automatically picks up new channel volumes. `set_volume()` itself immediately re-applies to `_current_player_id` (the new player). The fading-out old player gets updated on the next tick via the proxy. |
| **One-frame desync (documented)** | **Sharp edge** | Between `set_volume()` and the next `game.tick()`, the old player has stale effective volume. This is at most one frame (~16ms) of desync — not audible, not a bug. |
| **duration=0 crossfade** | **SAFE** | Both tweens complete on first `game.tick()`. Old player stopped, new at full volume, state cleaned up. |
| **Missing asset during crossfade** | **SAFE** | `_cancel_crossfade()` cleans up first (cancels tweens, stops old player), then `AssetNotFoundError` propagates. Current player (the one that was being faded in) remains valid. |
| **Rapid interruptions** | **SAFE** | Each `crossfade_music()` calls `_cancel_crossfade()` first, stopping the previous old player and cancelling tweens. No player leak even after 4 rapid crossfades. |
| **_teardown during crossfade** | **SAFE** | `stop_music()` → `_cancel_crossfade()` chain cleans everything up. |
| **Negative duration** | **SAFE** | `TweenManager.create()` raises `ValueError` on negative duration. |
| **Pool duplicate names** | **SAFE** | No-repeat logic uses index-based exclusion, not name-based. Duplicate names can play "same sound" twice in a row (by different indices). Not a bug — design intent. |

#### AnimationPlayer frame_duration=0: Fix Verified ✅

Both `AnimationDef.__init__` and `AnimationPlayer.__init__` contain:
```python
if not math.isfinite(frame_duration) or frame_duration <= 0:
    raise ValueError(...)
```
All 10 executable repros (0, negative, NaN, Inf, -Inf for both classes) confirm the fix rejects invalid values and normal operation still works.

#### List item_height=0: Fix Verified ✅

`List.on_event()` contains guards at two points:
```python
if self._item_height <= 0:
    return True
```
All 5 executable repros (item_height=0 click, motion, _visible_count; item_height=-10 click; normal click) confirm the fix prevents ZeroDivisionError.

### Test Counts After Stage 12

| Suite | Count | Result |
|-------|-------|--------|
| Full suite (excluding visual/screenshot) | **2236** | pass |
| Skipped (SAGA2D_HEADLESS) | **3** | skip |
| New crossfade/fix-verification tests | **39** | pass |

### Updated Cumulative Totals

- **2236 tests passing**, 3 skipped, 0 failures
- **22 bugs found and fixed** (unchanged — no new bugs in crossfade)
- **5 documented behaviors** (F11, F13, F14, F17, F20)
- **11 sharp edges** (SE1–SE10, plus **SE11**: one-frame volume desync during crossfade on old player)
- **0 known defects remaining** in source code

## Stage 13 — F26: ParticleEmitter NaN/Inf Lifetime Bug Fix (2026-03-23)

### Bug: `lifetime=(nan, nan)` allows `burst()` particles to never expire

**ID:** F26
**Severity:** Medium (memory/sprite leak risk)
**Source:** `saga2d/rendering/particles.py` — `ParticleEmitter.__init__` (no validation) + `update()` line 201 (`nan <= 0` is `False` under IEEE 754)

**Root cause:** `random.uniform(nan, nan)` returns `nan`. Particle `remaining` is set to `nan`. In `update()`, the death check `if p.remaining <= 0:` evaluates to `False` for NaN (IEEE 754 standard: all comparisons with NaN return False except `!=`). The particle never enters the death branch and lives forever — a sprite and memory leak.

Additionally, `random.uniform(inf, inf)`, `random.uniform(-inf, -inf)`, and `random.uniform(-inf, inf)` all return `nan`, so **any non-finite lifetime value** triggers the same immortal-particle bug.

**Reproduction:**
```python
from saga2d.rendering.particles import ParticleEmitter
em = ParticleEmitter("sprites/knight", position=(100,100), lifetime=(float("nan"), float("nan")))
em.burst(5)
for _ in range(100):
    em.update(1.0)  # 100 seconds of updates
len(em._particles)  # Still 5 — never expires
```

### Fix

**File changed:** `saga2d/rendering/particles.py`

Added validation in `ParticleEmitter.__init__` after unpacking the lifetime tuple:
```python
lt_min, lt_max = lifetime
if not math.isfinite(lt_min) or not math.isfinite(lt_max):
    raise ValueError(
        f"lifetime values must be finite numbers, got ({lt_min}, {lt_max})"
    )
if lt_min < 0 or lt_max < 0:
    raise ValueError(
        f"lifetime values must be >= 0, got ({lt_min}, {lt_max})"
    )
```

This follows the same `math.isfinite()` validation pattern used for:
- `AnimationDef`/`AnimationPlayer` frame_duration (F21–F23)
- `TweenManager.create()` duration (F21R)
- `TimerManager.after()`/`every()` (F22R, F23R)
- `FadeOut`/`FadeIn` duration (F24R)
- `Delay` duration (F15)
- `MoveTo` speed (F16)

### Existing test updated

**File:** `tests/test_kodo_systems_edge.py`

`TestParticleEmitterNaNLifetime::test_nan_lifetime_burst_never_expires_via_game_tick` — previously documented the pre-fix behavior (NaN particles surviving forever). Updated to `test_nan_lifetime_raises_value_error` expecting `ValueError` on construction.

### Regression tests: `tests/test_kodo_particle_nan_lifetime.py` — 20 tests, all pass

| Class | Tests | What's Tested |
|-------|-------|---------------|
| `TestF26NaNLifetimeRejection` | 8 | NaN/NaN, NaN/valid, valid/NaN, Inf/Inf, -Inf/valid, Inf/NaN, negative/valid, negative/negative — all raise ValueError |
| `TestValidLifetimeStillWorks` | 5 | Normal range, (0,0) immediate death, equal min/max, very small (1e-10), very large (1e6) — all accepted |
| `TestRealParticleWorkflow` | 7 | Full Game.tick() lifecycle: burst→move→fade→expire, continuous spawn/expire, auto-deregister, burst after NaN rejection, multiple bursts, remove cleanup |

All 7 workflow tests exercise the **real particle pipeline**: `Game` + `Scene` + `Sprite` + `ParticleEmitter` + `game.tick()` — not just unit-level `emitter.update()`.

### Test counts after Stage 13

| Suite | Count | Result |
|-------|-------|--------|
| Full suite (excluding visual/screenshot) | **2257** | pass |
| Skipped (SAGA2D_HEADLESS) | **3** | skip |
| New F26 regression tests | **20** | pass |
| Updated existing test | **1** | pass |

### Updated Cumulative Totals (Stage 13)

- **2257 tests passing**, 3 skipped, 0 failures
- **23 bugs found and fixed** (F1, F3–F10, F12, F15–F16, F18–F19, F21–F26)
- **5 documented behaviors** (F11, F13, F14, F17, F20)
- **11 sharp edges** (SE1–SE11)
- **0 known defects remaining** in source code

## Stage 14 — Mini-App Integration Test & F27 Fix (2026-03-23)

### Approach

Built a realistic "dungeon crawler" mini-app (`tests/test_kodo_mini_app.py`) that exercises **every major Saga2D system** end-to-end in a single integrated test suite. The mini-app defines three interconnected scenes (TitleScene, GameScene, InventoryScene) that use all 12+ systems together.

### Test File: `tests/test_kodo_mini_app.py` — 47 tests, all pass

| Class | Tests | Systems Exercised |
|-------|-------|-------------------|
| `TestMiniAppFullWorkflow` | 3 | All systems: title→game→inventory→save→pause E2E |
| `TestSpriteActionsIntegration` | 4 | Sprites + Actions (Sequence, Parallel, MoveTo, PlayAnim, FadeOut, Remove, Repeat) |
| `TestCameraIntegration` | 4 | Camera (follow, pan_to, shake, screen/world coords) |
| `TestParticleIntegration` | 2 | Particles (burst, continuous, fade, lifecycle) |
| `TestUIWidgetsIntegration` | 5 | UI (List, DataTable, ProgressBar, TextBox, HUD) |
| `TestTweenIntegration` | 3 | Tweening (property interpolation, on_complete, cancel) |
| `TestAudioIntegration` | 3 | Audio (crossfade, sound pools, volume channels) |
| `TestTimerIntegration` | 3 | Timers (one-shot, repeating, cleanup on scene exit) |
| `TestFSMIntegration` | 2 | FSM (valid transitions, invalid event) |
| `TestInputIntegration` | 3 | Input (key bindings, click world coords, escape pop) |
| `TestMultiSystemStress` | 4 | Stress: rapid scene transitions, 50 sprites, simultaneous particles+tweens+sprites |
| `TestBugDiscovery` | 11 | F27 regression (4 tests), EC3-EC5 edge cases, sprite removal mid-action, camera follow removal, particle cleanup, tween across scene transition |

### Finding: F27 — DataTable(row_height=0) ZeroDivisionError

**ID:** F27 (previously EC1 from Stage 11B audit)
**Severity:** Medium (crash)
**Source:** `saga2d/ui/widgets.py`, `DataTable.on_event()` line 1830

**Root cause:** `int(relative_y // self._row_height)` divides by zero when `row_height=0`. Same class as F24 (List widget).

**Fix:** Added `if self._row_height <= 0: return True` guard in `DataTable.on_event()` click handler.

**File changed:** `saga2d/ui/widgets.py` — 1 line added

### Feature Map Update

| # | Feature / Workflow | Test File(s) | Test Count | Last Tested | Status | Findings |
|---|-------------------|-------------|-----------|-------------|--------|----------|
| 51 | Multi-system integration (all systems together) | test_kodo_mini_app.py | 47 | 2026-03-23 | pass | F27 DataTable row_height=0 |
| 52 | Scene lifecycle (push/pop/replace in integrated workflow) | test_kodo_mini_app.py | (in #51) | 2026-03-23 | pass | |
| 53 | Sprite + Actions + Camera combined | test_kodo_mini_app.py | (in #51) | 2026-03-23 | pass | |
| 54 | Particles + Tweens + Sprites concurrent | test_kodo_mini_app.py | (in #51) | 2026-03-23 | pass | |
| 55 | Stress: rapid scene transitions, 50 sprites, simultaneous systems | test_kodo_mini_app.py | (in #51) | 2026-03-23 | pass | |

### Test Counts After Stage 14

| Suite | Count | Result |
|-------|-------|--------|
| Full suite (excluding visual/screenshot) | **2304** | pass |
| Skipped (SAGA2D_HEADLESS) | **3** | skip |
| New mini-app integration tests | **47** | pass |

### Updated Cumulative Totals

- **2304 tests passing**, 3 skipped, 0 failures
- **24 bugs found and fixed** (F1, F3–F10, F12, F15–F16, F18–F19, F21–F27)
- **5 documented behaviors** (F11, F13, F14, F17, F20)
- **11 sharp edges** (SE1–SE11)
- **0 known defects remaining** in source code
