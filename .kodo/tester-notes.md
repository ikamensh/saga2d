# Tester Notes - Saga2D

## Stage 3 — F54/F55/F56 ctor validation (tester agent, 2026-03-25)

**Implemented (matches `.kodo/test-coverage.md` / `test-report.md`):**

- **`DataTable`:** `row_height <= 0` → **`ValueError`** (`DataTable row_height must be positive, got …`) in `__init__` (`saga2d/ui/widgets.py`). `on_event` / `_visible_rows` still defensively guard `<= 0` if internal state ever violated.
- **`Grid`:** `cell_size` with **negative** width or height → **`ValueError`** (`Grid cell_size dimensions must be non-negative, got (…)`) in `__init__`. **`(0,0)`** still accepted (degenerate; `_cell_at` returns `None`).
- **`SaveLoadScreen`:** `slot_count <= 0` → **`ValueError`** (`slot_count must be positive, got …`) in `__init__` (`saga2d/ui/screens.py`).

**Commands (all PASS this run):**

- Regression file: `SAGA2D_HEADLESS=1 uv run python -m pytest tests/test_kodo_stage3_ui_rendering_regression.py -q` → **84 passed** (~0.8s). Includes F54–F56 + prior F44–F53-style cases.
- Stage 3 UI + mini_app + SaveLoad + Grid zero:  
  `pytest tests/test_kodo_stage3_ui_rendering.py tests/test_kodo_mini_app.py tests/ui/test_screens.py::TestSaveLoadScreen tests/test_kodo_widget_edge.py::TestGridZeroDimensions tests/test_kodo_widget_edge.py::TestGridPreferredSizeZero -q` → **83 passed**.
- Expanded spot-check (**279 passed**, ~0.9s):

```bash
SAGA2D_HEADLESS=1 uv run python -m pytest \
  tests/test_kodo_stage3_ui_rendering_regression.py \
  tests/test_kodo_stage3_ui_rendering.py \
  tests/test_kodo_mini_app.py \
  tests/test_kodo_ui_particle_edge.py \
  tests/test_kodo_systems_edge.py::TestParticleEmitterNaNLifetime \
  tests/test_kodo_particle_nan_lifetime.py \
  tests/test_kodo_widget_edge.py::TestGridZeroDimensions \
  tests/test_kodo_widget_edge.py::TestGridPreferredSizeZero \
  tests/ui/test_screens.py::TestSaveLoadScreen \
  -q
```
- One-liner ctor smoke: construct `DataTable(…, row_height=0)`, `Grid(…, cell_size=(-1,10))`, `SaveLoadScreen(…, slot_count=0)` → each raises **`ValueError`** with expected substring; `Grid(…, (0,0))` and `SaveLoadScreen(…, slot_count=1)` OK.

**Still acceptable (unchanged):** `DataTable` `col_widths` shorter than `columns` → missing columns draw at width **0** (overlap risk). **`Grid(cell_size=(0,0))`** — documented degenerate case.

**Env:** `uv run` from repo root; stray `VIRTUAL_ENV` from another repo → uv warns and uses **this** project `.venv`.

## UI / particles edge E2E (mock, 2026-03-25)

**Env:** repo root, `SAGA2D_HEADLESS=1`, `uv run python` (project `.venv`; ignore stray `VIRTUAL_ENV` from other repos).

**Singleton Game:** only one `Game` alive — call `g._teardown()` before constructing another. **InputEvent** lives in `saga2d.input`, not `backends.base`.

**ParticleEmitter** (`saga2d/rendering/particles.py`): non-finite **speed** / **direction** → **`ValueError`** at construction. **lifetime** with any negative component → **`ValueError`**. Finite but **negative speed range** `(min, max)` still constructs; `burst` + `tick` runs (velocity from `random.uniform` × trig — can be large finite values). **Requires** active `Game` + resolvable sprite image (`AssetManager` + temp `images/sprites/*.png` is enough for mock).

**ProgressBar:** assigning **`value=float('nan')`** → **`ValueError`** (`finite number`). **Negative value** with positive `max_value` → **`fraction` clamped to 0.0**. **`max_value<=0`** → **`fraction==0.0`** (no crash).

**DataTable:** **`row_height<=0`** → **`ValueError` at construction (F54)**. **`col_widths`** shorter than **`columns`** → missing columns get **width 0** in draw (overlap risk — silent).

**Grid:** **`cell_size=(0,0)`** → tiny preferred size; **`_cell_at`** returns **`None`**. **Negative `cell_size` component** → **`ValueError` at construction (F55)**.

**SaveLoadScreen:** **`slot_count<=0`** → **`ValueError` at construction (F56)**.

**Pytest bundle (same files; counts drift with suite):** `tests/test_kodo_stage3_ui_rendering.py`, `tests/test_kodo_widget_edge.py::TestGridZeroDimensions`, `::TestGridPreferredSizeZero`, `tests/test_kodo_mini_app.py::TestBugDiscovery::test_datatable_row_height_zero_raises`, `::test_datatable_row_height_negative_raises`, `tests/ui/test_screens.py::TestSaveLoadScreen`, `tests/test_kodo_systems_edge.py::TestParticleEmitterNaNLifetime`.

## Actions + `Game.tick(dt)` edge probes (2026-03-25)

**Env:** repo root, `SAGA2D_HEADLESS=1`, `uv run python` (project `.venv`).

**`Game.tick(dt)`** (`saga2d/game.py`): non-finite `dt` (`nan`, `±inf`) → **`ValueError`** (`dt must be a finite number, got …`). Negative `dt` → **`ValueError`** (`dt must not be negative, got …`). Rejected **before** `SceneStack.update(dt)`.

**`MoveTo(position, speed)`** (`saga2d/actions.py`): scalar → **`TypeError`** (`position must be a (x, y) tuple, got int` / `float`). `()` → **`TypeError`** (`position must have at least 2 elements, got 0`). `(x,)` → **`TypeError`** (`… got 1`). (No `IndexError` on current code.)

**`Repeat(action, times)`**: `times` is **`None`** (infinite), or **`int` not `bool`**, and **`times >= 0`**. **`times < 0`** → **`ValueError`** (`Repeat times must be >= 0, got …`). **`float`** / **`nan`** / **`inf`** → **`TypeError`** (`Repeat times must be an int or None, got float`). **`bool`** (e.g. `True`) → **`TypeError`** (`… got bool`). **`times=0`**: constructs; `start()` leaves `_current` **None** → action completes immediately without running child.

**`Do(fn)`**: non-callable (`str`, `int`, `None`, …) → **`TypeError`** (`Do() requires a callable, got …`) at **`__init__`**.

**Pytest:** `SAGA2D_HEADLESS=1 uv run python -m pytest tests/test_kodo_stage2_core_actions.py tests/test_kodo_stage5_regression.py::TestF40GameTickDtValidation -q` → **49 passed, 2 failed** — failures are **expectations behind code**: `test_repeat_negative_times_finishes_immediately` (expects `Repeat(..., -5)` to construct; code now raises **`ValueError`**), `test_moveto_1tuple_raises_indexerror` (expects **`IndexError`**; code now raises **`TypeError`**). **`TestF40GameTickDtValidation`** (5 tests) → all **pass**.

## Stage 1 tester agent — install + full pytest (2026-03-25)

- **Install:** `uv sync --extra dev` at repo root → OK. **Uv quirk:** if shell `VIRTUAL_ENV` points outside the project (e.g. another repo’s `.venv`), uv warns and still uses **this** project’s `.venv`.
- **`scripts/smoke_game_move_to.py` (E2E, 2026-03-25):** `SAGA2D_HEADLESS=1 uv run python scripts/smoke_game_move_to.py` → **PASS** (`PASS — smoke: Game, Scene, Sprite, MoveTo`). Mock backend, temp `images/sprites/dot.png`; exercises `Game` → `push(SmokeScene)` → `on_enter` adds `Sprite` + `MoveTo` → ticks until within 1px of target → `_teardown()`. Imports: `from saga2d import Game, MoveTo, Scene, Sprite` → OK.
- **Docs:** repo **`test-report.md`** § Smoke script + commands; **`.kodo/test-coverage.md`** § Stage 1 table (E2E smoke row) + pytest commands.
- **Import smoke:** `SAGA2D_HEADLESS=1 uv run python -c "from saga2d import Game, Scene; g=Game('t',backend='mock'); g.push(Scene()); g.tick(0.016); g._teardown(); print('import_smoke OK')"` → OK.
- **Full `pytest tests/`:** **2665** collected; **2649 passed**, **11 failed**, **5 skipped** (~45s). Failures are **only** `tests/visual_verify/` (8× menu tutorial AI + 3× UI screenshot golden / AI). **Exclude `visual_verify`:** **2631 passed**, **3 skipped** (~34s) — skips are **`game.run()`** in `tests/core/test_game.py` under `SAGA2D_HEADLESS=1`. Two `test_ai_checker` tests skip without `ANTHROPIC_API_KEY`.
- **Artifacts:** exact commands and numbers → repo root **`test-report.md`**; Stage 1 PLAN mapping → **`.kodo/test-coverage.md`** § Stage 1.

## Stage 4 — camera / audio / tween / particles (headless E2E) — verified 2026-03-23

**Env:** repo root, `SAGA2D_HEADLESS=1`, `uv run`, **no GUI** (mock backend). **Stereo pan:** not in `saga2d/audio.py` — only scalar **volume** on channels / `play_sound` / crossfade.

**Import smoke**

```bash
SAGA2D_HEADLESS=1 uv run python -c "from saga2d import Game, Scene; g=Game('t',backend='mock'); g.push(Scene()); g.tick(0.016); g._teardown(); print('import_smoke OK')"
```

**Runnable scripts (user-style `Game.tick`)**

```bash
SAGA2D_HEADLESS=1 uv run python camera_advanced_edge_e2e_headless.py   # shake decay=0, 2nd pan replaces 1st, bounds shrink + follow, edge_scroll margin=0
SAGA2D_HEADLESS=1 uv run python tween_edge_e2e_probe.py                # invalid duration → ValueError; duration=0; large dt; non-finite dt; negative tick(dt)
SAGA2D_HEADLESS=1 uv run python e2e_multifeature_headless.py           # tween + particles + audio workflow
```

**F31/F32/F33 — camera NaN/Inf (worker_smart) — verified 2026-03-23**

- **Pytest (all behaviors):** `SAGA2D_HEADLESS=1 uv run python -m pytest tests/test_kodo_camera_nan_edge.py -v` → **30 passed** (~0.03s). Covers: `shake()` rejects non-finite intensity/duration/decay; `update()` ignores non-finite `dt` (key_scroll, edge_scroll, shake elapsed, follow); `follow()` skips non-finite target coords; coordinate helpers stay finite after guards.
- **User-style smoke (prints `user_probe F31/F32/F33 OK`):** exercise `Camera` directly — invalid `shake()` → `ValueError` (`finite`); `enable` key scroll + `update(nan)` → `_x/_y` unchanged; `follow` sprite then `target.x = nan` + `update` → camera position unchanged and finite. Run the same logic in a local `python -c` or copy from `tests/test_kodo_camera_nan_edge.py` examples.

**Pytest bundles (last run: 20 + 135 + 66 = 221 passed)**

```bash
cd /Users/ikamen/ai-workspace/experiments/by_kodo/saga2d
SAGA2D_HEADLESS=1 uv run python -m pytest \
  tests/test_kodo_systems_edge.py::TestCameraShakeDecayZero \
  tests/test_kodo_systems_edge.py::TestCameraPanToDuringShake \
  tests/test_kodo_systems_edge.py::TestCameraEdgeScrollMarginZero \
  tests/test_kodo_systems_edge.py::TestParticleEmitterInvertedRanges \
  tests/test_kodo_systems_edge.py::TestParticleEmitterNaNPosition \
  tests/test_kodo_camera_drag_edge.py::TestCameraPanToCancels \
  tests/test_kodo_camera_drag_edge.py::TestCameraScrollNaNInf \
  tests/rendering/test_camera.py::TestPanTo::test_pan_to_replaces_previous_pan \
  tests/rendering/test_camera.py::TestFollow::test_follow_clamps_to_world_bounds \
  tests/rendering/test_camera.py::TestWorldBounds::test_world_bounds_setter_clamps_immediately \
  tests/rendering/test_camera.py::TestEdgeScroll::test_edge_scroll_via_game_tick \
  -q

SAGA2D_HEADLESS=1 uv run python -m pytest \
  tests/systems/test_audio.py \
  tests/integration/test_adversarial.py::TestAudioAdversarial \
  tests/integration/test_adversarial.py::TestAudioEdgeCases \
  tests/test_kodo_adversarial_fresh.py::TestAudioStress \
  tests/test_kodo_crossfade_repro.py \
  -q

SAGA2D_HEADLESS=1 uv run python -m pytest \
  tests/test_kodo_animation_tween_edge.py::TestTweenZeroDuration \
  tests/test_kodo_animation_tween_edge.py::TestTweenNegativeDuration \
  tests/test_kodo_animation_tween_edge.py::TestTweenLargeDt \
  tests/test_kodo_animation_tween_edge.py::TestTweenConflict \
  tests/test_kodo_animation_tween_edge.py::TestTweenExistingValidation \
  tests/actions/test_tween.py \
  tests/test_kodo_ui_particle_edge.py::TestParticleZeroLifetime \
  tests/test_kodo_ui_particle_edge.py::TestParticleSpeedZero \
  tests/test_kodo_ui_particle_edge.py::TestParticleFadeWithZeroLifetime \
  tests/test_kodo_particle_nan_lifetime.py \
  -q
```

**Findings (no bugs on mock paths)**

| Area | Result |
|------|--------|
| Camera | `decay=0` keeps amplitude until shake ends; second `pan_to` replaces tween ids; follow clamps after `world_bounds` shrink; `margin=0` scroll only when pointer is **strictly outside** viewport. |
| Audio | Concurrent crossfades, rapid play/stop/SFX, volume extremes covered in pytest; mock has no speaker. Py 3.13: `set_volume(..., nan)` can store **1.0** via `min`/`max` — sharp edge, not a crash. |
| Tweens | Invalid duration raises `ValueError`; `duration=0` snaps on first tick; overlapping tweens on same property **do not auto-cancel** (`TestTweenConflict`); negative `tick(dt)` can move value backward / below `from_val` (documented). |
| Particles | Inverted `(high, low)` ranges OK (`uniform`); NaN/Inf **lifetime** rejected in ctor; NaN **position** + `burst` → `ValueError` from `Sprite`. |
| Obsolete script | `reproduce_particle_nan_lifetime.py` — ctor now rejects non-finite lifetime; use `tests/test_kodo_particle_nan_lifetime.py`. |

## 2026-03-23 — Edge-case UX bundle (Grid / TabGroup / ProgressBar / particles / Animation / List)

- **Install:** `uv run` from repo root (deps via `uv sync --extra dev` if needed). **Headless:** `SAGA2D_HEADLESS=1`.
- **Pytest (36 passed, ~0.04s):**
  ```bash
  SAGA2D_HEADLESS=1 uv run python -m pytest \
    tests/test_kodo_widget_edge.py::TestGridZeroDimensions \
    tests/test_kodo_widget_edge.py::TestGridPreferredSizeZero \
    tests/test_kodo_widget_edge.py::TestTabGroupEmpty \
    tests/test_kodo_widget_edge.py::TestTabGroupInvalidKey \
    tests/test_kodo_widget_edge.py::TestProgressBarMaxZero \
    tests/test_kodo_timer_widget_edge.py::TestProgressBarEdgeCases \
    tests/test_kodo_particle_nan_lifetime.py::TestValidLifetimeStillWorks::test_zero_zero_lifetime_accepted \
    tests/test_kodo_crossfade_repro.py::TestAnimationPlayerFrameDurationZero \
    tests/test_kodo_crossfade_repro.py::TestListItemHeightZero \
    -q
  ```
- **One-shot mock E2E (no GUI):** same scenarios in one process — `uv run python -c '...'` in agent log; uses `g._scene_stack.top()` (**method**, not property) before `scene.ui.add(...)`.
- **Results:** No crashes/hangs. **TabGroup:** empty tabs → `active_tab is None`, draw/tick OK; `select_tab("missing")` → **`KeyError`** with message listing available tabs (intentional). **AnimationPlayer `frame_duration=0`** → **`ValueError`** (`positive finite`). **`AnimationPlayer([], frame_duration=0)`** raises **empty-frames first** (see `scripts/animation_edge_user_probe.py`). **ProgressBar:** `max_value<=0` → `fraction==0`; negative **value** → fraction clamped to 0. **ParticleEmitter `lifetime=(0,0)`, `fade_out=True`:** burst + `update` → all particles gone immediately. **List `item_height=0`:** click returns `True`, no `ZeroDivisionError`.
- **Extra:** `uv run python scripts/animation_edge_user_probe.py` — PASS; documents `update(nan)` stuck playback on valid player.

## 2026-03-23 — Stage 14 mini-app + F27 DataTable (tester re-verify)

- **Ran:** `SAGA2D_HEADLESS=1 uv run python -m pytest tests/test_kodo_mini_app.py -q` → **47 passed**; full tree  
  `uv run python -m pytest tests/ --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q` → **2304 passed, 3 skipped** (~29s).
- **F27 fix:** `DataTable.on_event()` early-returns when `_row_height <= 0` before `relative_y // _row_height` (`saga2d/ui/widgets.py`). Unguarded division → `ZeroDivisionError`; current `on_event(click)` returns `True` without crash.
- **Workflow nuance:** E2E title→game→inventory uses `InventoryScene.stats_table` with **`row_height=28`** only. **`row_height=0`** is exercised in **`TestBugDiscovery`** (synthetic table + direct `on_event`), not the story Inventory UI.
- **`~/.kodo/runs/20260323_163501/test-report.md`** matches repo **`.kodo/test-coverage.md`** Stage 14 on counts, F27 story, and `widgets.py` change; neither is a shell log — numbers **confirmed** by local pytest run above.

## 2026-03-23 — Multi-feature headless user workflow (tester agent)

- **Script:** `e2e_multifeature_headless.py` — `TitleScene` (Panel, Label, Button) → click → `WorldScene`: `Camera` + `pan_to` (tween), `enable_key_scroll`, `Sprite` + `Sequence`/`Parallel`/`PlayAnim`/`MoveTo`/`Do`, `ParticleEmitter.burst` + `stop`, `tween(ProgressBar)`, `play_sound` + `play_music` + `crossfade_music` + `stop_music` on exit. **Run:** `SAGA2D_HEADLESS=1 uv run python e2e_multifeature_headless.py` → prints `PASS`.
- **Pyglet/screenshots in agent/sandbox:** `render_scene()` can fail with `IndexError: list index out of range` in `display.get_default_screen()` when no display screens exist — not a Saga2D bug. Real macOS desktop: usually OK with `visible=False`.
- **Default input:** Camera key scroll uses **arrow keys** only (`InputManager` binds `left`/`right`/… to arrow keys, not WASD).

## 2026-03-23 — Focused E2E: particles, empty widgets, tween, camera (Stage 11C)

- **Automated:** Single pytest bundle → **449 passed, 0 failed** (~0.4s). Exact command and file list → `.kodo/test-coverage.md` § **Stage 11C**.
- **Smoke:** `Grid(0,0)`, `TabGroup()`, `DataTable(columns=[], rows=[])`, `TweenManager` `duration=0` + `update(0)` → target snaps; `Game` + `push(Scene)` + `tick` + `_teardown`. **`Label`** is not in `saga2d.ui.widgets` (import from `saga2d.ui.components` / top-level saga2d).
- **Manual:** With active `Game`, `Camera.pan_to(..., duration=inf)` → **`ValueError`** (tween duration validation). **PB1 — particle lifetime NaN (reproduced 2026-03-23):** `ParticleEmitter(..., lifetime=(nan,nan))` + **`burst()`** (burst required — ctor `count` does not spawn) → `random.uniform(nan,nan)` → nan; **`nan <= 0` is False** → particles **never** die; `is_active` stays True. **Repro:** `uv run python reproduce_particle_nan_lifetime.py`. **Pytest:** `tests/test_kodo_systems_edge.py::TestParticleEmitterNaNLifetime`. Mitigation until fix: validate lifetime in ctor or `remove()`.
- **Grid 0×0 + mock click** in a real `Scene.ui` → OK. **Keyboard on Grid:** no handler (only click/motion) — Stage 11 “arrow keys on 0×0 Grid” is N/A.

## 2026-03-23 — Tester agent: install + full suite (4227501)

- **Install:** README `pip install -e ".[dev]"` in a **clean venv** → OK (verified with system Python 3.13). Repo workflow: **`uv sync --extra dev`** + `uv run …` (requires `uv`). Smoke: `uv run python -c "from saga2d import Game, Scene; g=Game('t',backend='mock'); g.push(Scene()); g.tick(0.016); g._teardown()"` → OK.
- **Full automated suite (no display/screenshot dirs):**  
  `SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q` → **2200 collected, 2197 passed, 3 skipped** (~34s). Skips: `tests/core/test_game.py` — `game.run()` disabled under `SAGA2D_HEADLESS`.
- **Visual buckets:** `pytest tests/screenshot tests/visual tests/visual_verify` → **92 skipped** here (markers / no GPU path).
- **Artifacts / logs:** Pytest cache in **`.pytest_cache/`** (gitignored). No default JUnit/HTML output unless added to pytest config.
- **Gotcha:** `env -u SAGA2D_HEADLESS` → **2 failed** in `tests/test_kodo_core_fresh.py::TestHeadlessMode` (tests assert the var is set). **CI:** export `SAGA2D_HEADLESS=1`.

## Gap map — targeted areas → implementation (tests in parentheses)

- **Targeted gap areas:**
  | Area | Code |
  |------|------|
  | AnimationPlayer / `frame_duration` | `saga2d/animation.py` (`AnimationPlayer`, `AnimationDef`); wired from `saga2d/rendering/sprite.py`. Tests: `tests/rendering/test_animation.py`, `tests/test_kodo_animation_tween_edge.py`. |
  | List `item_height` | `saga2d/ui/widgets.py` (`List`). Tests: `tests/ui/test_widgets.py`, `tests/test_kodo_widget_edge.py`, `tests/test_kodo_timer_widget_edge.py`. |
  | Particle lifetime | `saga2d/rendering/particles.py` (`ParticleEmitter`, `_Particle`); tick in `saga2d/game.py` `_update_particles`. Tests: `tests/rendering/test_particles.py`, `tests/test_kodo_systems_edge.py`, `tests/test_kodo_rendering_ui_fresh.py`. |
  | Grid / TabGroup / DataTable empty states | `saga2d/ui/widgets.py` (`Grid`, `TabGroup`, `DataTable`). Tests: `tests/test_kodo_widget_edge.py`, `tests/test_kodo_timer_widget_edge.py`, `tests/test_kodo_rendering_ui_fresh.py`, `tests/kodo_test_systems.py`. |
  | Tween duration | `saga2d/util/tween.py` (`tween()`, `TweenManager`, duration validation). Tests: `tests/actions/test_tween.py`, `tests/test_kodo_animation_tween_edge.py`, `tests/test_kodo_core_fresh.py` (tween section). |
  | Camera “advanced” (no zoom/rotate) | `saga2d/rendering/camera.py` — follow, edge scroll, `world_bounds`, `pan_to` + tween cancel, shake coord mapping. Tests: `tests/rendering/test_camera.py`, `tests/test_kodo_camera_drag_edge.py`, `tests/kodo_test_rendering.py`. |
  | Audio crossfade state | `saga2d/audio.py` (`_crossfade_old_player`, `_crossfade_tween_ids`, `_cancel_crossfade`, `_finish_crossfade`, `crossfade_music`). Tests: `tests/systems/test_audio.py`, `tests/kodo_test_stage7_e2e.py`, `tests/test_kodo_systems_edge.py`, `tests/integration/test_adversarial.py`. |

## Stage 7 — F13/F14 adversarial + final report structure (verified 2026-03-22)

- **Commands (all PASS):**
  - `pytest tests/kodo_test_stage7_e2e.py::TestActionNaNEdgeCases tests/kodo_test_stage7_e2e.py::TestPlaySoundChannelValidation -v` → **8** passed (F13 + F14 regression tests).
  - `pytest tests/kodo_test_stage7_e2e.py -q` → **70** passed (full Stage 7 file: 62 base E2E + 8 adversarial).

- **F13 — NaN/Inf (and negative) `dt` in actions — reproduced; not “broken” tests, they document sharp edges:**
  - **`Delay.update(nan)`:** `_elapsed` becomes NaN; `>= seconds` is always False → action **stuck**; further finite `dt` does not recover.
  - **`FadeOut` / `FadeIn.update(nan)`:** raises **`ValueError`** (`cannot convert float NaN to integer` from opacity math).
  - **`Delay.update(inf)`:** returns **True** immediately (`inf >= seconds`).
  - **`Delay.update(negative)`:** subtracts from elapsed (documented in tests) — can delay completion.
  - **Expected if `dt` is always finite and non-negative from `Game.tick`:** no production path; hardening would be `math.isfinite(dt)` / `dt >= 0` at action or tick boundary.

- **F14 — `play_sound` channels — doc vs code:**
  - **`audio.py` docstring** says `channel` is **`"sfx"` or `"ui"`** only.
  - **Implementation** rejects only unknown keys: `channel not in self._volumes` where `_volumes` includes **`master`, `music`, `sfx`, `ui`** — so **`play_sound(..., channel="music"|"master")` succeeds** (uses that channel’s volume). **`bogus`** → **`KeyError`** with valid list in message.
  - **Impact:** documentation mismatch; behavior is **harmless** (wrong channel name would still raise).

- **Standalone repro (no pytest):** from repo root, run a **fresh** `Game` per step with `_teardown()` between (singleton). Temp dir: `images/sprites/knight.png`, `sounds/beep.wav`, `AssetManager` on that path — then exercise `Delay(1.0).update(nan)`, `FadeOut` + `update(nan)`, `play_sound` with `music`/`master`/`bogus`. Verified manually 2026-03-22 (stdout matches F13/F14 above).

- **Final report = `.kodo/test-coverage.md` Stage 7 block — required subsections present:** `## Stage 7 — Remaining Feature Areas E2E` → test file + area table (20 rows) → **Corrected test counts** → **Confirmed absent features** → **Findings (Stage 7 base)** → **Stage 7 Adversarial Pass** (F13/F14 table) → **Totals after Stage 7 + Adversarial**.

## Audio / Text·Fonts / Tilemaps / Util (independent pass, 2026-03-22)

- **Audio (mock backend — no speaker output):** `pytest tests/systems/test_audio.py -v` → **83** passed. Workflows: channel volume hierarchy (`master` / `music` / `sfx`), `play_sound` / `play_music` / `stop_music`, crossfade + replace, sound pools (`play_sound_from_pool`), `AssetManager` sound/music loaders + extensions, `Game.audio` integration. Harnesses: `python -m tests.harness.systems_util_harness M -v`; `python -m tests.harness.final_verification_harness AB -v` (optional missing sound + `AssetNotFoundError` on image); `python -m tests.harness.integration_harness all -v` (music persists across scene push/pop). **Doc gap:** `play_sound` accepts `music`/`master` despite docstring — see **Stage 7 F14** above.

- **Text / fonts:** There is **no standalone typography module** — text is UI `Label` / `Button` / `TextBox` / `DataTable` etc., resolved `Style` (`font`, `font_size`, `text_color`) → `backend.draw_text(...)`. Mock tests assert recorded `texts[]` payloads (size, color, string). Commands: `pytest tests/ui/test_theme.py tests/ui/test_ui.py -k "Label or font or Style or text" -q` → **41**; `pytest tests/ui/test_widgets.py -k "TextBox or font or Label" -q` → **14**; `pytest tests/kodo_test_systems.py -k "TabGroup or Label or text_width" -q` → **12** (uses `_estimate_text_width`). **Real GPU font rasterization** still untested here (blocked: visual/screenshot marks). **No bugs found** in exercised paths.

- **Tilemaps:** **No engine `TileMap` API** in `saga2d/` — maps are **app-level** (sprites + logic). Battle vignette uses `SquareGrid` + terrain sprites; tower defense uses grid helpers. Commands: `pytest tests/examples/test_battle_vignette.py tests/examples/test_tower_defense_tutorial.py tests/examples/test_tower_defense_example.py -q` → **44** passed (~28s; loads real example assets under mock `Game`). `pytest assetgen/test_battle_tiles.py -v` → **1** passed — **gap:** `test_tiles()` only prints; it **does not assert** on missing files or wrong dimensions, so pytest can pass while tiles are broken (repro: delete a PNG under `examples/battle_vignette/assets/images/tiles/` and re-run — still green).

- **Utility modules (`saga2d.util`):** Re-exports `Ease`, `StateMachine`, `TimerHandle`; `tween()` lives on **`saga2d`** (not `saga2d.util`) by design. `pytest tests/actions/test_tween.py tests/actions/test_timer.py tests/systems/test_fsm.py -q` → **63** passed. Smoke: `from saga2d.util import Ease, StateMachine; StateMachine(...).trigger(...)` — OK. **No bugs found.**

## Stage 6 — Input / Camera / shake+picking (verified / re-verified 2026-03-22)

- **No interactive `game.run()`** — all checks via `backend="mock"`, `inject_*`, `game.tick()`, harnesses (AGENTS.md).
- **Shake vs picking (F12 — fixed):** `Camera.screen_to_world` / `world_to_screen` include `_shake_offset_x/_y`, matching `_sync_sprites_to_camera` (`game.py`). Regression: `tests/rendering/test_camera.py::TestShakePickingRegression` (7 tests), including E2E click at drawn sprite pixel → correct `world_x`/`world_y` during shake.
- **Suites (re-run, all PASS):** `pytest tests/rendering/test_camera.py::TestShakePickingRegression tests/systems/test_input.py tests/rendering/test_camera.py tests/kodo_test_persistence_resources.py::TestTeardownCompleteness -v` → **173**; `pytest tests/kodo_test_rendering.py -k "Camera or screen_to_world or world" -v` → **17**; `pytest tests/kodo_test_systems.py -k "world_coords or _with_world" -v` → **2**; `pytest tests/ui/test_drag_drop.py -q` → **49**; `python -m tests.harness.integration_harness all -v`; `python -m tests.harness.systems_util_harness O -v`; `python -m tests.harness.ui_rendering_harness I -v`; full non-visual `pytest tests/ --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q` (`env -u SAGA2D_HEADLESS`) → **1411**.
- **Camera model:** Translation only; **no zoom or rotation**. `screen_to_world` = `sx + camera.x + shake_x` (and symmetric `world_to_screen`) while shake is active.
- **Mouse ↔ world E2E:** `Game.tick` applies `_with_world_coords` before HUD/UI/camera key-scroll/scene `handle_input`; tests cover clicks/moves/drags with scroll, `center_on`, multi-event ticks, no-camera scenes (world = screen).
- **Teardown (F10):** `TestTeardownCompleteness` includes `_teardown()` / `__del__` safe after partial `Game` init — part of the same regression run above.
- **Framework “physics”:** No collision engine in `saga2d/` — Stage 6B physics scope = **N/A** at engine level.

## Persistence / save-load / resources (verified 2026-03-22)

- **Environment:** `.venv` present; `backend="mock"`, `game.tick()` + `_teardown()` only (no `game.run()`).
- **Imports:** `from saga2d import Game, Scene, SaveManager, SaveError` — OK.
- **Suites run (all PASS):**
  - `pytest tests/kodo_test_persistence_resources.py tests/integration/test_resource_leaks.py -v` → **70** passed
  - `pytest tests/systems/test_save.py -v` → **48** passed
  - `pytest tests/ui/test_screens.py -k "SaveLoad or save_mgr" -v` → **9** passed (SaveLoadScreen)
  - `pytest tests/integration/test_adversarial.py::TestSaveSystemEdgeCases -v` → **10** passed
  - `python -m tests.harness.systems_util_harness J -v` → Scenario **J** PASS
- **F9 non-object JSON (verified 2026-03-22):** `SaveManager.load()` rejects top-level JSON that is not an object (`list`, `str`, `null`, number, bool) with **`SaveError`** (message includes slot path and type). `list_slots()` propagates that `SaveError` (no `TypeError`). **`SaveLoadScreen`:** `on_enter` calls `list_slots` uncaught → pushing the screen with a bad `save_1.json` raises **`SaveError`** at push time (screen does not mount); not an in-UI corruption banner. Regression: `pytest tests/kodo_test_persistence_resources_ext.py::TestMalformedSaveFiles -v` (10 passed).
- **Other manual checks:** Truncated/invalid JSON → `SaveError` with slot hint. JSON object **without** `"state"` → `Game.load` returns data, does **not** call `load_save_state` (documented).

## E2E: core engine + scene stack (2026-03-21)

**Scope:** Mock backend only (`backend="mock"`), `game.tick(dt)` — no `game.run()` (headless-safe). **Note:** Saga2D has **no `on_hide` hook**; coverage is `on_enter` / `on_exit` / `on_reveal` only.

### Commands run (all PASS)

```bash
cd /Users/ikamen/ai-workspace/experiments/by_kodo/saga2d

# Broad: lifecycle hooks, transparency draw chain, pause_below, deferred ops,
# empty stack, replace/clear edge cases, hook-time stack mutation
.venv/bin/python -m pytest tests/core/test_scene.py tests/integration/test_adversarial.py -v --tb=no
# → 130 passed (36 + 94)

# Lifecycle harness (push/pop/replace/clear_and_push ordering + deferred flush)
.venv/bin/python -m tests.harness.lifecycle_tester -v
# → US4, US10, US11, US12, US13 — 5/5

# Fuzz: invalid Game args + scene stack edge ops (pop/replace empty, etc.)
.venv/bin/python -m tests.harness.fuzz_harness
# → exit 0; stderr may show Game.__del__ teardown noise on partially-built Game instances

# Focused: clear_and_push resource cleanup, empty stack, FakeGame cursor
.venv/bin/python -m pytest tests/core/test_scene.py tests/core/test_scene_timers.py -k clear_and_push \
  tests/core/test_scene_sprites.py -k clear_and_push tests/integration/test_resource_leaks.py \
  tests/ui/test_hud.py -k "clear_and_push or empty_stack" \
  tests/kodo_test_core.py::TestSceneStackBasic tests/kodo_test_core.py::TestFakeGameCursorBug -v --tb=no
# → 16 passed (subset via -k)

# Transparent overlay + HUD ordering + tick-based game tests (excludes game.run())
.venv/bin/python -m pytest tests/ui/test_ui.py::TestSceneIntegration::test_ui_for_transparent_scene_stack \
  tests/ui/test_hud.py::TestHUDDrawOrder::test_hud_draws_before_overlay \
  tests/ui/test_hud.py::TestHUDDrawOrder::test_hud_hidden_by_overlay_show_hud_false \
  tests/ui/test_hud.py::TestHUDDrawOrder::test_hud_visible_with_show_hud_true_overlay \
  tests/core/test_game.py -k "not run and not window_close" -v --tb=no
# → 6 passed

# One-liner smoke (editable package from .venv)
.venv/bin/python -c "from saga2d import Game, Scene; g=Game('e2e', backend='mock'); g.push(Scene()); g.tick(0.016); g._teardown(); print('OK')"
```

### Coverage map (what the suite proves)

| Area | Where |
|------|--------|
| Hook order (push/pop/replace/clear) | `tests/core/test_scene.py`, `lifecycle_tester.py` |
| `on_reveal` after pop | `test_pop_calls_on_exit_and_on_reveal`, US4/US10/US11 |
| Deferred stack ops during `update` | `test_deferred_*`, US11 |
| Hooks mutating stack (`on_enter`/`on_exit`) | `test_push_during_on_enter_*`, `test_pop_during_on_exit_*`, `test_push_during_on_exit_*`, adversarial tests |
| Empty stack | `test_*empty*`, `TestSceneStackBasic`, fuzz harness |
| Transparency + draw chain | `test_draw_transparent_*`, `test_background_color_uses_base_scene_when_transparent_overlay` |
| `pause_below=False` updates below | `test_pause_below_false_updates_scenes_below` |
| `clear_and_push` teardown | on_exit all cleared scenes; timers/sprites tests; resource leak test |
| Re-entrancy / adversarial | `tests/integration/test_adversarial.py` (18 tests) |

### Sprite / Action / Animation (verified 2026-03-21)

- **pytest:** `tests/rendering/test_sprite.py` + `tests/actions/test_actions.py` + `tests/rendering/test_animation.py` → **209 passed**; `tests/integration/test_adversarial.py::TestSpriteLifecycleAdversarial` → **3 passed**; `tests/kodo_test_rendering.py` → **127 passed**.
- **Harness:** `python -m tests.harness.action_stress_tester` → **8/8** (US6–US9, US22–US23, NoHang, NaN). **Known behavior:** US22 documents `Parallel(only infinite children)` finishing in one tick (vacuous `all_finite_done`).
- **Manual:** Sprite never `scene.add_sprite` (`_owning_scene is None`) still runs `do(Sequence(MoveTo, Do))` + nested `Parallel(Sequence(Delay, Do), Do)` + layer order `BACKGROUND < EFFECTS` — all OK with explicit `game._teardown()`.

### F5 — `on_exit` exception (re-verified)

- **Exploratory file:** `tests/kodo_test_scene_lifecycle.py` (73 tests) — includes `TestComplexReentrancy::test_on_exit_exception_leaves_scene_on_stack` documenting F5.
- **Repro still valid:** `SceneStack.pop()` after `on_exit` raises → **`len(_stack) == 1`**, scene remains top (manual repro + that test both confirm).
- **Do not** `pytest tests/harness/lifecycle_tester.py` — those are script functions, not pytest tests; use `python -m tests.harness.lifecycle_tester`.

## Last Session: Harness & User Story Coverage (2026-03-18)

### Harness Verification — All Run Successfully Except One
- **Consumer**: PASS — imports 63 symbols, Game(mock), tick(0.016), _teardown()
- **Install**: PASS — pip install -e . in clean venv, import+Game+tick
- **Fuzz**: PASS — edge cases (Game args, scene ops, action params)
- **Integration**: PASS — A/B/C (Button→Scene push, action completion, camera)
- **UI (D–I)**: PASS — Theme, ChoiceScreen/ConfirmDialog, drag-drop, HUD, ParticleEmitter/ColorSwap, Camera
- **Systems (J–Q)**: PASS — Save, StateMachine, Cursor, Audio, Timer/tween, Input, Teardown, show_sequence
- **Bug Repro (R–Y)**: Scenario T FAIL — `scene.game` is None during _cleanup_exiting_scene (cursor.set)
- **Final Verification (AA–AE)**: PASS

### Consumer Harness vs US3
- US3: "Create a Game with mock backend, **push a Scene**, tick frames"
- Consumer harness does **not** push a Scene — it only Game(mock) + tick. Integration Scenario A covers push+pop.

### User Story → Harness Mapping
- Harnesses cover scenarios; many user stories remain **untested** (31/35) because harnesses exercise code paths but test-stories.md status is not auto-updated from harness runs.
- See test-stories.md Notes column for which harness/scenario maps to each story.

---

## Previous: Battle Unit Visibility Verification (2026-03-13)

### Battle Unit Visual Prominence - VERIFIED ✓ (Updated: 480px sprites)
- **Sprite sizes**: 480×480 pixels (both warriors and skeletons)
- **Tile size**: 128×128 pixels
- **Obstacle size**: 24×20 pixel pebbles (intentionally small)
- **Result**: Units fill ~3.75x their grid cell area, **massively** prominent
- **Screenshot**: `baseline_battle.png` (3840×2160 HiDPI)
- **Visual**: Blue warriors and red/white skeletons dominate the grid; gray rocks are tiny pebbles
- **Row-1 clipping check**: ✓ Top row units fully visible with health bars, 182px top margin
- **Gemini verification**: ✅ **FIXED** using exact acceptance criteria description

### Gemini Vision API - Acceptance Criteria PASSED
- **Test**: `verify_screenshot_gemini.py` with defect-first phrasing (original format)
- **Description**: "Units are nearly invisible on the battle grid. The warrior and skeleton sprites are tiny colored specks on the green grass. The gray rock obstacles are far more prominent than the actual playable units. Units should be the most visually prominent elements on the grid."
- **Result**: ✅ **FIXED** (after prompt engineering improvement)
- **Reasoning**: "The units are no longer tiny specks. They are large enough to be easily seen and are more prominent than the obstacles. The reported defect condition no longer exists."

### Gemini Prompt Engineering Fix
- **Issue**: Original prompt treated description as requirement to match
- **Solution**: Updated prompt with 2-step process:
  1. Analyze screenshot independently (unit size, prominence, obstacles)
  2. Evaluate whether REPORTED DEFECT still exists
- **Key insight**: Frame description as "reported defect" to check if it's FIXED, not as requirement to match
- **Token limit**: Increased from 200 to 400 to allow detailed reasoning

### Environment
- macOS with display (pyglet screenshot capture works)
- Use `capture_battle_screenshot.py` for pyglet screenshots
- Screenshot harness available at `tests/screenshot/harness.py`

## Previous Session: UI Polish Verification (2026-03-11)

### Environment
- Headless SSH environment (no display)
- Use `scripts/repro_menu.py --simulate` for PIL-based screenshots
- Screenshot harness available at `tests/screenshot/harness.py`

### UI Requirements Verified
1. **Label text clipping** - Fixed via `anchor_y="top"` in Label.on_draw() (line 223)
2. **Panel shadow** - Implemented in Panel.on_draw() (lines 605-615), offset=4px
3. **Button borders** - Clear borders via theme border_width=2, color Slate 600
4. **Hover outline** - Blue glow (100,181,246,200) on hovered buttons (lines 389-402)
5. **Color palette** - Slate/Sky Material Design colors in theme.py (lines 66-95)

### Key Patterns
- **Screenshot generation**: Use `--simulate` flag for headless PIL rendering
- **Hover state verification**: Check `repro_menu_final.png` (Load Game button hovered)
- **Text positioning**: Labels use `anchor_y="top"`, Buttons use `anchor_y="center"`
- **Panel shadows**: 4px offset, color (0,0,0,120)
- **Button hover**: Background color + 3px outline glow, -2px offset

### Files
- `scripts/repro_menu.py` - Menu screenshot generator
- `repro_menu_final.png` - Screenshot with hover state
- `VERIFICATION_COMPLETE.md` - Full verification document

## Display Environment Test (2026-03-11)

### Pyglet Headless Test Result
**Status**: ✗ NO DISPLAY AVAILABLE (True Headless)

**Environment**: SSH session, no macOS display server access
**Pyglet version**: 2.1.13
**Error**: `IndexError: list index out of range` when trying to get screens

### Implications
- Cannot create pyglet windows (even with `visible=False`)
- Cannot use OpenGL contexts for rendering
- Screenshot harness (`render_scene`) requires display
- Must use alternative methods:
  - PIL-based simulation (like `scripts/repro_menu.py --simulate`)
  - Pre-generated golden screenshots
  - Mock backend validation

### Working Methods
✅ PIL simulation scripts (repro_menu.py --simulate, ui_gallery.py)
✅ Pre-captured screenshots in tests/visual_verify/output/
✅ Mock backend tests (tests/screenshot/test_*.py with @pytest.mark.screenshot)
✅ Code inspection and validation

### Not Available
✗ Live pyglet screenshot capture
✗ Screenshot harness (tests/screenshot/harness.py render_scene)
✗ Real-time GPU rendering tests
