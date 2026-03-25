# Feature Coverage

Tracked across `kodo test` runs. Previous runs: commit 477220f (2026-03-21), Stage 4 fixes (2026-03-22), Fresh re-test (2026-03-23), Stage 1 re-verify (2026-03-23), F29/F30 fixes (2026-03-23), F31-F33 fixes (2026-03-23), F34/F35 fixes (2026-03-25). **Stage 1 tester pass:** 2026-03-25. **Stage 2 tester pass:** 2026-03-25. **Stage 3 tester pass (UI/rendering edge cases):** 2026-03-25 — 13 bugs fixed (F44–F56), 84 new regression tests, 2 acceptable edge cases documented. **Stage 4 tester pass (integration/lifecycle):** 2026-03-25 — 2 bugs fixed (F57–F58), 37 new regression tests, 6 existing tests updated. **Stage 5 tester pass (resources / asset loading):** 2026-03-25 — **0 new bugs**; see § Stage 5 below.

## Stage 1 — Window, game loop, scenes (PLAN.md)

**PLAN goal:** running game loop with push/pop scenes, colored backgrounds; backend protocol + `Game` + `Scene`/`SceneStack`.

| Stage 1 area | Implementation (typical) | What exercised it (automated) |
|--------------|--------------------------|------------------------------|
| Backend protocol, frame lifecycle, events | `saga2d/backends/base.py`, `mock_backend.py`, `pyglet_backend.py` | `Game.tick()` paths in `tests/core/test_game.py`; mock backend fixtures (`tests/conftest.py`); pyglet paths exercised when screenshot/visual tests run (display-dependent) |
| `Game` constructor, `tick`, stack delegation, teardown | `saga2d/game.py` | `tests/core/test_game.py` (excluding `game.run()` under headless), `tests/kodo_test_core.py`, headless guard tests in `tests/test_kodo_core_fresh.py` |
| `Scene` / `SceneStack`: push, pop, replace, `clear_and_push`, deferred ops | `saga2d/scene.py` | `tests/core/test_scene.py`, `tests/core/test_scene_*.py`, `tests/integration/test_adversarial.py` (stack re-entrancy and related) |
| Lifecycle hooks (`on_enter` / `on_exit` / `on_reveal`), transparency, `pause_below` | `saga2d/scene.py`, draw/update orchestration in `game.py` | `tests/core/test_scene.py`, `tests/ui/test_ui.py` (transparent stack), `tests/ui/test_hud.py` |
| `game.run()` interactive loop | `saga2d/game.py` | **Skipped** when `SAGA2D_HEADLESS=1` (`tests/core/test_game.py` — 3 tests); manual / display-only |
| Pyglet window + push/pop demo | `PygletBackend`, scenes | `tests/visual/test_stage1_visual.py` — manual or display; not part of default headless CI |
| **E2E smoke: Game→Scene→Sprite→MoveTo** | `saga2d/game.py`, `scene.py`, `rendering/sprite.py`, `actions.py` | **`scripts/smoke_game_move_to.py`** — standalone headless script; creates Game (mock), pushes Scene, adds Sprite, runs MoveTo action via `tick()` loop, asserts target reached. Run: `uv run python scripts/smoke_game_move_to.py`. See `test-report.md` for full details. |

**Commands (Stage 1 tester, 2026-03-25):**

- Smoke script: `uv run python scripts/smoke_game_move_to.py` → `PASS — smoke: Game, Scene, Sprite, MoveTo`
- Full pytest (headless): `SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify -q` → **2631 passed, 3 skipped** (~34s)
- Full pytest (all): `SAGA2D_HEADLESS=1 uv run python -m pytest tests/ -q` → **2665** collected, **2649 passed, 11 failed, 5 skipped** — failures are AI/screenshot checks in `visual_verify`, not Stage 1 mock regressions.

## Current Run — Deep Edge Case Testing (2026-03-25)

### Baseline (re-measured 2026-03-25 — tester agent)
- **2665** tests collected; **2649 passed**, **11 failed** (`tests/visual_verify/*`), **5 skipped** with `SAGA2D_HEADLESS=1` (~45s full `tests/`)
- **2631 passed**, **3 skipped** if `tests/visual_verify/` is ignored (matches “automated mock + screenshot” focus)
- Older note **“2,522 passing, 1 visual failing”** is **stale** relative to this checkout

### Runtime exercised — tick(dt), MoveTo, Repeat, Do (2026-03-25)

Manual `uv run python` probes + pytest bundle: `tests/test_kodo_stage2_core_actions.py` + `tests/test_kodo_stage5_regression.py::TestF40GameTickDtValidation`.

| Workflow | Outcome (runtime) |
|----------|-------------------|
| `Game.tick` with `nan` or `±inf` | **`ValueError`** before scene update — message `dt must be a finite number, got …` |
| `Game.tick(negative)` | **`ValueError`** — `dt must not be negative, got …` |
| `MoveTo` scalar / `()` / `(x,)` | **`TypeError`** with explicit messages (tuple type, element count); not `IndexError` for 1-tuple |
| `Repeat(..., times=float / nan / inf)` | **`TypeError`** — `Repeat times must be an int or None, got float` |
| `Repeat(..., times<0)` | **`ValueError`** — `Repeat times must be >= 0, got …` |
| `Repeat(..., times=True)` | **`TypeError`** — bool rejected (`… got bool`) |
| `Repeat(..., times=0)` | Constructs; **`start()`** no-ops child (finishes immediately) |
| `Do(non-callable)` | **`TypeError`** at **`__init__`** |

**Stage 2 fixes (F42–F43):** Tests updated to match stricter validation. Regression suite: `tests/test_kodo_stage2_regression.py` (20 tests). Headless total: **2651 passed, 3 skipped**.

### Stage 3 — UI/Rendering Edge-Case Validation (2026-03-25)

Runtime probes via `stage3_repro.py` + pytest regression suite: `tests/test_kodo_stage3_ui_rendering_regression.py` (84 tests).

| Workflow | Outcome |
|----------|---------|
| `ProgressBar(value=NaN)` constructor | **`ValueError`** — constructor now validates both `value` and `max_value` with `math.isfinite()` **(F44)** |
| `ProgressBar(max_value=NaN)` constructor | **`ValueError`** — NaN max_value no longer bypasses fraction guard **(F44)** |
| `ProgressBar(value=Inf)` constructor | **`ValueError`** — Inf rejected **(F44)** |
| `Button.text = None` | **`TypeError`** — None rejected at setter (was crashing downstream in `_estimate_text_width`) **(F45)** |
| `ParticleEmitter.position = (NaN, 0)` | **`ValueError`** — setter now validates with `math.isfinite()` **(F46)** |
| `AnimationPlayer.update(dt=NaN)` | **Returns None** — skips frame, preserves state, recovers on next valid dt **(F47)** |
| `Camera.enable_edge_scroll(NaN, NaN)` | **`ValueError`** — margin and speed validated **(F48)** |
| `Camera.enable_key_scroll(speed=NaN)` | **`ValueError`** — speed validated **(F49)** |
| `Camera.world_bounds = (NaN, 0, 800, 600)` | **`ValueError`** — all 4 values must be finite **(F50)** |
| `Camera.world_bounds = (100, 0, 50, 600)` inverted | **`ValueError`** — left must be <= right, top <= bottom **(F50)** |
| `Tooltip(delay=NaN)` | **`ValueError`** — delay must be finite **(F51)** |
| `Tooltip(delay=-1)` | **`ValueError`** — delay must be >= 0 **(F51)** |
| `Sprite.tint = (NaN, 0.5, 0.5)` | **`ValueError`** — NaN/Inf components rejected **(F52)** |
| `Sprite.move_to((NaN, 0), speed=100)` | **`ValueError`** — target position must be finite **(F53)** |
| `DataTable(row_height=0)` | **`ValueError`** — row_height must be positive **(F54)** |
| `DataTable(row_height=-10)` | **`ValueError`** — row_height must be positive **(F54)** |
| `DataTable(col_widths=[100])` with 3 columns | **Accepted** — graceful fallback: missing widths get 0; deliberate API flexibility (documented, not a bug) |
| `Grid(cell_size=(-10, 64))` | **`ValueError`** — cell_size dimensions must be non-negative **(F55)** |
| `Grid(cell_size=(0, 0))` | **Accepted** — degenerate but safe: `_cell_at` returns None, no crash (documented, not a bug) |
| `SaveLoadScreen(slot_count=0)` | **`ValueError`** — slot_count must be positive **(F56)** |
| `SaveLoadScreen(slot_count=-1)` | **`ValueError`** — slot_count must be positive **(F56)** |

**Stage 3 fixes (F44–F56):** 16 existing tests updated to match stricter validation. Regression suite: `tests/test_kodo_stage3_ui_rendering_regression.py` (84 tests). Headless total: **2734 passed, 3 skipped**.

### NEW Gaps to Test This Run

| Feature / Workflow | Last tested | Status | Findings |
|--------------------|-------------|--------|----------|
| ParticleEmitter speed/direction NaN/Inf | 2026-03-25 | **verified** | **Ctor `ValueError`** (finite required); negative finite speed range still spawns; **pytest** + headless repro |
| Do() non-callable fn parameter | 2026-03-25 | **fixed** | **TypeError** at construction — already guarded before Stage 2 |
| Repeat() times negative/float/NaN | 2026-03-25 | **fixed (F42)** | Negative int now raises `ValueError`; float/NaN/bool raise `TypeError` |
| MoveTo bad position tuple (1-tuple, scalar) | 2026-03-25 | **fixed (F43)** | Clear `TypeError` with actionable message (was raw `IndexError`) |
| Game.tick(dt=NaN) propagation to scene | 2026-03-25 | **fixed** | Rejected at `Game.tick` level — already guarded before Stage 2 |
| ProgressBar value=NaN setter | 2026-03-25 | **fixed (F44)** | **`ValueError`** on assign AND at construction; `max_value` also validated |
| ProgressBar constructor NaN/Inf bypass | 2026-03-25 | **fixed (F44)** | Constructor now validates both `value` and `max_value` with `isfinite()` |
| Button.text = None crash | 2026-03-25 | **fixed (F45)** | `TypeError` at setter (was crashing downstream in `_estimate_text_width`) |
| ParticleEmitter.position NaN | 2026-03-25 | **fixed (F46)** | Setter now validates with `isfinite()`; was silently storing NaN |
| AnimationPlayer.update(dt=NaN) freeze | 2026-03-25 | **fixed (F47)** | Skips frame, preserves state, recovers on next valid dt |
| Camera.enable_edge_scroll NaN/Inf | 2026-03-25 | **fixed (F48)** | Margin and speed validated with `isfinite()` |
| Camera.enable_key_scroll NaN/Inf | 2026-03-25 | **fixed (F49)** | Speed validated with `isfinite()` |
| Camera.world_bounds NaN/inverted | 2026-03-25 | **fixed (F50)** | All 4 values validated finite; left<=right, top<=bottom enforced |
| Tooltip delay NaN/Inf/negative | 2026-03-25 | **fixed (F51)** | Delay must be finite and >= 0 |
| Sprite.tint NaN/Inf propagation | 2026-03-25 | **fixed (F52)** | Components validated with `isfinite()` before clamping |
| Sprite.move_to NaN target | 2026-03-25 | **fixed (F53)** | Target position validated with `isfinite()` |
| DataTable negative/zero row_height | 2026-03-25 | **fixed (F54)** | `row_height <= 0` now raises `ValueError`; positive values accepted normally |
| DataTable `col_widths` shorter than `columns` | 2026-03-25 | **acceptable** | Draw uses **width 0** for missing entries — graceful fallback, deliberate API flexibility; 3 documentation tests |
| Grid negative `cell_size` | 2026-03-25 | **fixed (F55)** | Negative dimensions now raise `ValueError`; zero accepted (guarded by `_cell_at`) |
| Grid zero `cell_size` | 2026-03-25 | **acceptable** | `_cell_at` returns None for zero stride; clicks select nothing; draw emits zero-rects; 3 documentation tests |
| SaveLoadScreen `slot_count<=0` | 2026-03-25 | **fixed (F56)** | `slot_count <= 0` now raises `ValueError`; positive values create slot buttons normally |
| flush_pending_ops exception stale ops | 2026-03-25 | **fixed (F57)** | Exception in flush now clears queue; prevents stale op leaks across ticks |
| Direct scene ops unflushed deferred ops | 2026-03-25 | **fixed (F58)** | push/pop/replace/clear_and_push now auto-flush deferred ops from on_exit/on_reveal |
| Deferred ops cap (1000) silent discard | 2026-03-25 | **fixed** | Now logs warning and clears remaining ops (was silently leaving them in queue) |
| Action stopped on scene pop (owned sprite) | 2026-03-25 | **verified** | Sprite removed → action stops; non-owned sprite survives |
| Timer cancelled on scene pop | 2026-03-25 | **verified** | Scene-owned timers cancelled; timer chains fully cancelled |
| Timer survives push-over | 2026-03-25 | **verified** | permanent=False preserves timers when scene is covered |
| clear_and_push kills all timers/actions | 2026-03-25 | **verified** | All owned resources cleaned up across multiple scenes |
| on_enter exception rollback | 2026-03-25 | **verified** | Failed scene popped from stack; exception propagates |
| on_exit exception cleanup | 2026-03-25 | **verified** | Cleanup runs in finally block; scene removed from stack |
| on_reveal exception | 2026-03-25 | **verified** | Exception propagates; popped scene still removed |
| on_exit exception in clear_and_push | 2026-03-25 | **verified** | All scenes cleaned up; first exception re-raised |
| update/draw exception propagation | 2026-03-25 | **verified** | Exceptions propagate; end_frame called via try/finally |
| Repeated Game init/teardown cycles | 2026-03-25 | **verified** | 5+ cycles work cleanly; singleton guard works |
| Teardown with on_exit exception | 2026-03-25 | **verified** | Logged and continues cleaning up remaining scenes |
| Double teardown | 2026-03-25 | **verified** | Safe no-op on second call |
| Sprite after teardown | 2026-03-25 | **verified** | Clean RuntimeError("No active Game") |
| Deferred ops FIFO order | 2026-03-25 | **verified** | Multiple deferred ops execute in queue order |
| Nested deferred ops (on_enter during flush) | 2026-03-25 | **verified** | New ops from on_enter picked up by flush loop |
| pop_on_cancel deferred correctly | 2026-03-25 | **verified** | Auto-pop deferred during input phase |
| Scene.add_sprite(None) | 2026-03-25 | pending | No None guard |
| Game invalid resolution | 2026-03-25 | pending | Negative/zero accepted |
| ColorSwap empty color lists | 2026-03-25 | pending | Silent no-op |
| DragDrop callback exceptions | 2026-03-25 | pending | May corrupt drag state |
| Game after teardown method calls | 2026-03-25 | pending | Methods still callable |
| Parallel.update() on unstarted children | 2026-03-25 | pending | No start() guarantee |

**Commands (tester agent UI/particle edge, 2026-03-25):**

```bash
cd /Users/ikamen/ai-workspace/experiments/by_kodo/saga2d
SAGA2D_HEADLESS=1 uv run python -c "from saga2d.rendering.particles import ParticleEmitter; from saga2d.ui.widgets import ProgressBar, DataTable, Grid; from saga2d.ui.screens import SaveLoadScreen; print('imports OK')"
SAGA2D_HEADLESS=1 uv run python -m pytest \
  tests/test_kodo_stage3_ui_rendering.py \
  tests/test_kodo_widget_edge.py::TestGridZeroDimensions \
  tests/test_kodo_widget_edge.py::TestGridPreferredSizeZero \
  tests/test_kodo_mini_app.py::TestBugDiscovery::test_datatable_row_height_zero_click \
  tests/test_kodo_mini_app.py::TestBugDiscovery::test_datatable_row_height_negative_click \
  tests/ui/test_screens.py::TestSaveLoadScreen \
  tests/test_kodo_systems_edge.py::TestParticleEmitterNaNLifetime \
  -q
# → 40 passed (local run)
```

### Previously Passing Features

| Feature / Workflow | Last tested | Status | Findings |
|--------------------|-------------|--------|----------|
| Game initialization (mock backend) | 2026-03-25 | pass | — |
| Game initialization (invalid backend) | 2026-03-25 | pass | ValueError raised correctly |
| Game.tick() basic cycle | 2026-03-25 | pass | — |
| Scene push/pop/replace/clear_and_push | 2026-03-25 | pass | — |
| Scene lifecycle hooks | 2026-03-25 | pass | — |
| Scene timer ownership | 2026-03-25 | pass | — |
| Actions: Sequence/Parallel/Delay/MoveTo/FadeIn/Out | 2026-03-25 | pass | F15/F16/F24 fixed |
| Camera follow/scroll/pan/shake | 2026-03-25 | pass | F31-33 fixed |
| Sprites creation/positioning/removal | 2026-03-25 | pass | — |
| Animation play/queue/stop/loop | 2026-03-25 | pass | F21-23 fixed |
| ParticleEmitter burst/continuous | 2026-03-25 | pass | F34 fixed |
| UI: All core widgets | 2026-03-25 | pass | — |
| Tween system | 2026-03-25 | pass | F21 fixed |
| Timer after/every/then | 2026-03-25 | pass | F22-23 fixed |
| FSM transitions | 2026-03-25 | pass | F18 fixed |
| Audio channels/crossfade | 2026-03-25 | pass | F35 fixed |
| SaveManager | 2026-03-25 | pass | F19 fixed |
| InputManager | 2026-03-25 | pass | — |
| Theme/Style/Layout | 2026-03-25 | pass | — |
| HUD visibility | 2026-03-25 | pass | — |

### Stage 4 — Integration/Lifecycle Edge Cases (2026-03-25)

**Investigation scope:** Scene stack transitions during active actions/timers, exceptions in scene hooks, repeated Game init/teardown, deferred operations safety/limits.

**Runtime probes:** `scripts/stage4_probe.py` — 41 probes covering all 4 areas. All PASS.

**Bugs found and fixed (F57–F58):**

| Bug | Description | Fix |
|-----|-------------|-----|
| **F57** | `flush_pending_ops` exception left stale ops in `_pending_ops` queue, leaking across ticks | Added `except` clause that clears `_pending_ops` before re-raising |
| **F58** | Direct scene ops (push/pop/replace/clear_and_push outside tick) didn't flush deferred ops from on_exit/on_reveal | Added `_flush_after_direct_op()` call after each direct `_apply_*` method |

**Also fixed:** Deferred ops cap (1000 iterations) now logs a warning and clears remaining ops instead of silently leaving them in the queue.

**Regression suite:** `tests/test_kodo_stage4_lifecycle_regression.py` — 37 tests. **6 existing tests updated** to match corrected behavior.

**Headless total (post-lifecycle fixes): 2771 passed, 3 skipped.**

**Runtime behavior (verified by tests + runtime probes):**

| Workflow | Outcome |
|----------|---------|
| `push`/`pop`/`replace` during `update` / `handle_input` | **Deferred**; `SceneStack.flush_pending_ops()` drains queue at end of `Game.tick` (`max_iterations = 1000`; excess ops logged + cleared). |
| `on_exit` calls `game.push(...)` **outside** `tick()` | Push is **queued** (`_in_on_exit` forces defer), then **auto-flushed** by `_flush_after_direct_op()` **(F58 fix)**. |
| `on_exit` calls `game.push(...)` **inside** `tick()` | Push is **deferred** until `flush_pending_ops()` at end of phase — same as before. |
| `on_reveal` calls `game.push(...)` **outside** `tick()` | Push is **queued** (`_in_on_exit` forces defer), then **auto-flushed** **(F58 fix)**. |
| `on_enter` calls `game.push(...)` directly | Executes **immediately** (not deferred — `on_enter` is NOT in a deferred context). Allows chaining: A.on_enter→push(B), B.on_enter→push(C). |
| `flush_pending_ops` raises exception | Remaining ops **cleared** (F57 fix); `_flushing` flag reset in `finally`. |
| Deferred ops cap (1000) hit | Warning logged; excess ops cleared. |
| Active action on owned sprite during scene pop | Sprite removed → action stops; callback never fires. |
| Scene-owned timer during scene pop | Timer cancelled (permanent=True); chain fully cancelled. |
| Timer survives push-over | Timer continues (permanent=False). |
| `clear_and_push` with timers/actions | All owned resources cleaned up across all cleared scenes. |
| `on_enter` raises | Failed scene rolled back off stack; exception propagates. |
| `on_exit` raises on `pop()` | Cleanup still runs (finally block); scene removed; exception propagates. |
| `on_exit` raises during `clear_and_push` | All scenes cleaned up; first exception re-raised. |
| `update()` raises | Exception propagates through `tick()`; scene remains on stack. |
| `draw()` raises | `end_frame()` called via try/finally; exception propagates. |
| Repeated Game init/teardown (5+ cycles) | Clean — singleton guard + `_teardown()` clears module globals. |
| Teardown with on_exit exception | Logged and continues; all scenes cleaned up. |
| Double teardown | Safe no-op. |
| Sprite creation after teardown | Clean `RuntimeError("No active Game")`. |
| Non-owned sprite survives scene pop | Sprite + action continue running after scene exit. |

### Stage 4 — Real-User Gameplay Workflow (2026-03-25)

**Scope:** End-to-end gameplay workflow simulating what a real saga2d user would build — player character, input handling, game loop, AABB collision detection, scene transitions, timers, and composable actions.

**Standalone script:** `scripts/stage4_gameplay_workflow.py` — headless, no env vars needed.

**Pytest suite:** `tests/test_kodo_stage4_gameplay_workflow.py` — 24 tests (16 workflow + 8 AABB collision unit tests).

**No bugs found.** All framework subsystems worked correctly in the integrated workflow.

| Workflow | Outcome |
|----------|---------|
| Game creation (mock backend, custom asset_path) | Works correctly |
| GameplayScene with Camera, player/enemy/ghost/coin sprites | on_enter lifecycle correct |
| Enemy patrol via `Repeat(Sequence(MoveTo, Delay, MoveTo, Delay))` | Actions advance every tick |
| Player movement via injected key_press/key_release input events | handle_input → update loop moves player |
| AABB collision: player vs coin (collectible) | Detected, coin removed, score updated |
| AABB collision: player vs enemy (damage) | Detected, player tint changed, timer-based reset |
| Score timer (scene.every 1.0s) | Fires correctly, score increments |
| Bonus spawn timer (scene.after 2.0s) | Fires correctly, bonus sprite created |
| Push PauseScene via bind_key("cancel") | on_exit called, **owned sprites removed** (framework design) |
| Pop PauseScene (pop_on_cancel) | on_reveal called, **sprites re-created** from preserved entity state |
| Entity position preservation across push/pop | Positions saved in on_exit, restored in _create_sprites |
| Collected coin not re-created after reveal | `coin_alive` flag prevents re-creation |
| Push InventoryScene via bind_key("i") | Inventory timer starts, scene entered |
| Pop InventoryScene (pop_on_cancel) | **Inventory timer cancelled on exit** (scene-owned timer cleanup) |
| Ghost fade action (Repeat(FadeOut, FadeIn)) runs after reveal | Re-created in on_reveal, opacity varies |
| Replace gameplay → VictoryScene | All gameplay sprites cleaned up (permanent exit) |
| Camera follows player movement | camera.center_on updates in update() |
| draw_world_rect debug overlays | 3+ rects drawn per frame in draw() |
| Multiple transition lifecycle counting | 3 exits, 2 reveals across pause+inventory+replace |

**Key framework behavior documented:**
- Owned sprites are **always removed** when a scene is pushed over (`_cleanup_exiting_scene(permanent=False)` still calls `_cleanup_owned_sprites()`). Users must save entity state in on_exit and re-create sprites in on_reveal.
- Scene-owned timers survive push-over (permanent=False) but are cancelled on permanent exit (pop/replace/clear_and_push).
- Inventory timers cancelled on scene exit — verified by running 60 ticks after exit, timer never fires.

**Headless total: 2795 passed, 3 skipped.**

### Stage 5 — Resources / asset loading (tester, 2026-03-25)

**Scope:** Missing images/sounds/music, animation `frames()`, audio `optional=True` vs strict, wrong sound extensions, corrupt-on-disk files vs mock backend, scene path (`Sprite` in `on_enter`).

**Pytest executed (all PASS this run):**

```bash
cd /Users/ikamen/ai-workspace/experiments/by_kodo/saga2d
SAGA2D_HEADLESS=1 uv run python -m pytest tests/systems/test_assets.py -q
# → 17 passed

SAGA2D_HEADLESS=1 uv run python -m pytest tests/test_kodo_systems_fresh.py \
  -k "TestLoadImage or TestLoadSound or TestFramesNo or TestAssetMusic or TestPlaySoundOptional or TestAssetCaching" -q
# → 14 passed, 102 deselected

SAGA2D_HEADLESS=1 uv run python -m pytest tests/integration/test_adversarial.py::TestAudioAdversarial -q
# → 6 passed

SAGA2D_HEADLESS=1 uv run python -m pytest tests/test_kodo_systems_edge.py::TestAudioPlaySoundEmptyString -q
# → 1 passed
```

**Manual probes (same session):** temp asset roots under `/var/folders/.../T/...` via `tempfile.mkdtemp()` — (1) `push` scene whose `on_enter` adds `Sprite("sprites/missing_hero")` → **`AssetNotFoundError`** with path hint; (2) `garbage.png` containing non-PNG bytes → **mock** `Game` + `tick` succeeds (backend does not decode); same bytes → **PIL `UnidentifiedImageError`** (proves real decode would fail); (3) `audio.play_sound("ghost", optional=True)` → **`None`**, `optional=False` → **`AssetNotFoundError`**; (4) `audio.play_music("no_track")` on empty `music/` → **`AssetNotFoundError`**; (5) `assets.frames("sprites/walk")` with no `_*` PNGs → **`AssetNotFoundError`** (“No animation frames”); (6) only `sounds/beep.txt` → **`AssetNotFoundError`** listing tried `.wav`/`.ogg`/`.mp3`.

**Extended runtime probes:** `scripts/stage5_asset_probe.py` — 44 probes covering 7 subsystems. All PASS, 0 bugs found.

| Category | Probes | Result |
|----------|--------|--------|
| Missing files (image/sound/music/frames) | A1-A5 | AssetNotFoundError with tried paths |
| Optional handling (play_sound/music optional=True) | A6-A8 | Returns None gracefully; crossfade has no optional flag |
| Cache behavior | A9-A10 | Same handle returned for repeated loads |
| Corrupt/empty files | A11-A12 | Mock backend accepts (never reads contents); PIL rejects |
| ColorSwap/palettes | A13-A15 | Proper KeyError/TypeError for invalid palettes |
| CursorManager/ParticleEmitter | A16-A19 | Missing images: AssetNotFoundError; ParticleEmitter defers to burst() |
| AnimationDef/Sprite edge cases | A20-A26 | frame_duration≤0 → ValueError; @2x preferred when available |
| Audio channels | AU1-AU5 | Invalid channel ops graceful (no crash) |
| SaveManager | S1-S12 | Corrupt JSON/binary/zero-byte → SaveError; non-serializable → SaveError; empty slots clean |
| FSM | F1 | Unknown event → ignored (no crash) |

**Findings:** **No bugs.** Behavior matches design: **`AssetManager`** validates **filesystem presence** and **extension search order** before calling the backend; **`AssetNotFoundError`** subclasses **`FileNotFoundError`** and messages list tried paths. **`play_sound(..., optional=True)`** is the intended user-facing soft path for missing SFX. **Gap (not a failure):** **mock** `load_image` / `load_sound` never validate file contents — **pyglet** would still raise when decoding corrupt media (`pyglet.image.load` / `pyglet.media.load`); headless CI relies on mock. **Fonts:** default theme uses logical names (`serif`); **mock** `load_font` does not open files — TTF path failures are a **pyglet / display** concern.

**Final headless total: 2795 passed, 3 skipped.**

### Blocked Workflows
| Workflow | Reason |
|----------|--------|
| Pyglet backend rendering | Requires display server (X11/Wayland) |
| Screenshot golden-image comparison | Requires pyglet + display |
| AI visual verification | Requires ANTHROPIC_API_KEY |
| Interactive game examples | Requires windowed display |
| Audio hardware playback | Requires audio hardware |
| game.run() loop | Blocked by SAGA2D_HEADLESS=1 |
