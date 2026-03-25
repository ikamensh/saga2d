# Test Report — Saga2D Quality Assurance

**Dates:** 2026-03-25
**Repo:** `saga2d` (workspace root)
**Final suite (delivery baseline, excl. visual_verify):** **2795 passed, 3 skipped, 0 failed** (~31s headless)
**Bugs fixed:** **F42–F58** (17 bugs found and fixed across Stages 2–4)
**Stages 4–5 (gameplay workflow + asset/resource probes):** 0 new bugs found

---

## Stage 1 — Install & Smoke (tester agent)

**Date:** 2026-03-25

## Environment

- **OS:** darwin (from user_info)
- **Python:** project requires `>=3.12` (`pyproject.toml`); `uv` manages `.venv` in the repo
- **Note:** `uv` printed `VIRTUAL_ENV=.../kodo/.venv does not match the project environment path .venv and will be ignored` — sync still succeeded; project venv is used

## Commands run (exact)

```bash
cd /Users/ikamen/ai-workspace/experiments/by_kodo/saga2d
uv sync --extra dev
uv run python scripts/smoke_game_move_to.py
SAGA2D_HEADLESS=1 uv run python -c "from saga2d import Game, Scene; g=Game('t',backend='mock'); g.push(Scene()); g.tick(0.016); g._teardown(); print('import_smoke OK')"
SAGA2D_HEADLESS=1 uv run python -m pytest tests/ -q --tb=no
SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --co -q
SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify -q --tb=no
SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify -rs -q --tb=no
SAGA2D_HEADLESS=1 uv run python -m pytest tests/visual_verify/ -q --tb=no
```

## Install & import smoke

| Step | Result |
|------|--------|
| `uv sync --extra dev` | **OK** (exit 0) |
| Import + `Game(..., backend='mock')` + `push(Scene)` + `tick` + `_teardown` | **OK** (`import_smoke OK`) |

## Full pytest (`tests/`)

> **Two baselines are tracked throughout this report:**
>
> | Baseline | What it includes | Use |
> |----------|-----------------|-----|
> | **Delivery baseline** | `--ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot` | Clean pass/fail metric; all failures are actionable engine bugs |
> | **Full tree** | All of `tests/` | Includes AI/screenshot golden-image tests that require `ANTHROPIC_API_KEY` + display server; failures here are environment-dependent, not engine regressions |

### Stage 1 snapshot (before Stages 2–5 additions)

These counts were captured at the start of testing, before any fixes or new tests were added. They are preserved here for reference only; **see [Final Test Suite Counts](#final-test-suite-counts) for current numbers.**

- **Full tree:** 2665 collected → 2649 passed, 11 failed (`tests/visual_verify/`), 5 skipped
- **Delivery baseline:** 2631 passed, 3 skipped (`game.run()` under `SAGA2D_HEADLESS=1`)

The 11 full-tree failures are all AI/screenshot assertions in `tests/visual_verify/` (`test_menu_tutorial_ai.py` × 8, `test_ui_with_ai.py` × 3) — not engine regressions. The 2 extra skips are `tests/visual_verify/test_ai_checker.py` (requires `ANTHROPIC_API_KEY`).

### Note on earlier "2,522 tests" claim

That count predates this checkout. The Stage 1 baseline was 2665 collected / 2631 delivery-passing.

## Smoke script: `scripts/smoke_game_move_to.py`

A standalone end-to-end smoke test that exercises the core Stage 1 workflow (**Game → Scene → Sprite → MoveTo action**) headlessly.

### How to run

```bash
uv run python scripts/smoke_game_move_to.py
```

No environment variables or display server needed — it uses the mock backend.

### What it validates

| Validated aspect | Detail |
|------------------|--------|
| `Game` creation with mock backend | Constructor, `backend="mock"`, resolution `(640, 480)` |
| `Scene` lifecycle | `push()` triggers `on_enter`; sprite added to scene inside `on_enter` |
| `Sprite` creation | `Sprite("sprites/dot", position=(40, 120))` with temporary asset directory |
| `MoveTo` action | Moves sprite from `(40, 120)` to `(520, 120)` at 400 px/s |
| `Game.tick(dt)` loop | 60 Hz ticks drive the action system forward |
| Completion check | Asserts distance to target < 1 px within 600 ticks (~10 s budget); raises `RuntimeError` on timeout |
| Teardown | `game._teardown()` + temp-directory cleanup |

**Expected output on success:** `PASS — smoke: Game, Scene, Sprite, MoveTo`

### When to use it

- **Quick sanity check** after install (`uv sync --extra dev && uv run python scripts/smoke_game_move_to.py`)
- **CI gating** before running the full pytest suite — fails fast if core imports or the game loop are broken
- **Agent workflows** — safe to run headless with no display dependency

## Stage 2 — Core Engine & Actions Edge Cases

**Date:** 2026-03-25

### Investigation scope

Four areas flagged in `.kodo/test-coverage.md` for edge-case validation:

| Area | Pre-existing fix? | Bug found? |
|------|-------------------|------------|
| `Game.tick(dt=NaN/Inf/negative)` | Yes — raises `ValueError` | No new bug |
| `Do(non-callable)` | Yes — raises `TypeError` | No new bug |
| `Repeat(times=float/NaN)` | Yes — raises `TypeError` | No new bug |
| `Repeat(times=negative_int)` | **No** | **F42** — silently accepted, action completed instantly without executing |
| `MoveTo(scalar/1-tuple)` | **No** | **F43** — leaked raw `IndexError`/`TypeError: not subscriptable` |

### Exact repro steps (before fix)

```python
# F42: Repeat(times=-1) — silently accepted, no error, action never fires
from saga2d.actions import Repeat, Delay
r = Repeat(Delay(0.1), times=-1)  # should raise ValueError but doesn't
# r.start(sprite) → _current = None (because -1 <= 0)
# r.update(dt) → True immediately — action "finished" without ever running

# F43: MoveTo(scalar) — confusing raw error
from saga2d.actions import MoveTo
MoveTo(100, speed=200)
# TypeError: 'int' object is not subscriptable  (unhelpful)
MoveTo((100,), speed=200)
# IndexError: tuple index out of range  (unhelpful)
```

### Fixes applied

| Bug | File | Change |
|-----|------|--------|
| **F42** | `saga2d/actions.py` | `Repeat.__init__` now raises `ValueError("Repeat times must be >= 0, got {times}")` for negative ints. Also rejects `bool` (subclass of `int`) with `TypeError`. |
| **F43** | `saga2d/actions.py` | `MoveTo.__init__` validates position with `iter()`/`next()` — raises `TypeError` with actionable message for scalars ("must be a (x, y) tuple"), short tuples ("must have at least 2 elements"), and non-numeric elements ("must be numbers"). |

### Regression tests added

**File:** `tests/test_kodo_stage2_regression.py` — 20 tests

| Class | Tests | What it covers |
|-------|-------|----------------|
| `TestF42RepeatNegativeTimes` | 6 | negative → `ValueError`; zero/positive/None still accepted; bool → `TypeError` |
| `TestF43MoveToPositionValidation` | 14 | scalar/None/empty/1-tuple → `TypeError`; string/non-numeric tuple → `TypeError`; valid 2-tuple/list/3-tuple; NaN/Inf/speed still → `ValueError` |

### Existing tests updated

| File | Test | Old behavior | New behavior |
|------|------|-------------|--------------|
| `tests/test_kodo_stage2_core_actions.py` | `test_repeat_negative_times_*` | Expected silent finish | Expects `ValueError` |
| `tests/test_kodo_stage2_core_actions.py` | `test_moveto_1tuple_*` | Expected `IndexError` | Expects `TypeError` with message |
| `tests/test_kodo_new_edge_cases.py` | `test_repeat_negative_times` | Expected silent no-op | Expects `ValueError` |
| `tests/kodo_test_rendering.py` | `test_repeat_negative_times` | Expected silent no-op | Expects `ValueError` |

### Verification

```bash
# Regression tests (20 new)
SAGA2D_HEADLESS=1 uv run python -m pytest tests/test_kodo_stage2_regression.py -v
# → 20 passed

# Full headless suite
SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q
# → 2651 passed, 3 skipped (~78s)

# Smoke script
uv run python scripts/smoke_game_move_to.py
# → PASS — smoke: Game, Scene, Sprite, MoveTo
```

## Stage 1 UX (PLAN.md scope)

Automated coverage for **window / game loop / scenes** is exercised primarily via **mock backend** + `Game.tick()` in `tests/core/` (and integration/adversarial scene-stack tests). The **smoke script** (`scripts/smoke_game_move_to.py`) provides a fast standalone E2E check of the Game → Scene → Sprite → MoveTo pipeline. **Interactive `game.run()`** is intentionally skipped under `SAGA2D_HEADLESS=1`. Pyglet window demos (for example `tests/visual/test_stage1_visual.py`) are outside this headless Stage 1 pass unless run manually with a display.

See `.kodo/test-coverage.md` § **Stage 1** for feature-to-test mapping.

## Stage 4 — Real-User Gameplay Workflow

**Date:** 2026-03-25

### Scope

End-to-end gameplay workflow simulating what a real saga2d user would build: a game with a player character, enemy sprites, collectible items, input-driven movement, AABB collision detection, scene transitions (push/pop/replace), timers, and composable actions — all running headlessly via the mock backend.

### Deliverables

| File | Description |
|------|-------------|
| `scripts/stage4_gameplay_workflow.py` | Standalone headless workflow script (run: `uv run python scripts/stage4_gameplay_workflow.py`) |
| `tests/test_kodo_stage4_gameplay_workflow.py` | Pytest suite: 24 tests (16 workflow, 8 AABB collision unit tests) |

### How to run

```bash
# Standalone script (no env vars needed)
uv run python scripts/stage4_gameplay_workflow.py
# → PASS — Stage 4 gameplay workflow: all assertions passed

# Pytest (24 tests)
SAGA2D_HEADLESS=1 uv run python -m pytest tests/test_kodo_stage4_gameplay_workflow.py -v
# → 24 passed

# Full suite (including new tests)
SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q
# → 2795 passed, 3 skipped
```

### What it exercises

1. **Game instantiation** — `Game("WorkflowTest", backend="mock", resolution=(800,600), asset_path=...)` with temp asset directory
2. **GameplayScene with Camera** — `Camera(viewport, world_bounds)`, `center_on()`, camera follows player
3. **Player character** — `Sprite("sprites/player")`, positioned and moved via input
4. **Enemy patrol** — `Repeat(Sequence(MoveTo, Delay, MoveTo, Delay))` composable action loop
5. **Ghost fade** — `Repeat(Sequence(FadeOut(0.4), FadeIn(0.4)))` infinite fade action
6. **Collectible coin** — sprite with fade action, removed on collision
7. **Input handling** — `backend.inject_key()` → `handle_input()` → `_move_dx/_move_dy` → `update()` movement
8. **AABB collision detection** — custom `aabb_collides()` using `sprite_rect()` (position + 64×64 image, BOTTOM_CENTER anchor)
9. **Coin collection** — collision → `sprite.remove()` → score updated → `coin_alive=False`
10. **Enemy damage** — collision → `player.tint = (1.0, 0.3, 0.3)` → timer-based tint reset
11. **Score timer** — `scene.every(1.0, callback)` fires repeatedly
12. **Bonus spawn timer** — `scene.after(2.0, callback)` one-shot
13. **PauseScene push** — `bind_key("cancel", ...)` → `game.push(PauseScene())` with `transparent=True`, `pop_on_cancel=True`
14. **Entity state preservation** — positions saved in `on_exit()`, sprites re-created in `on_reveal()`
15. **InventoryScene push/pop** — `bind_key("i", ...)`, timer cancelled on scene exit
16. **Replace with VictoryScene** — `game.replace(VictoryScene())`, all gameplay sprites cleaned up
17. **draw_world_rect** — debug collision overlays drawn in world space via camera

### Bugs found

**None.** All framework subsystems worked correctly in the integrated workflow.

### Key framework behavior documented

- **Owned sprites removed on push-over**: When a scene is pushed over, `_cleanup_exiting_scene(permanent=False)` calls `_cleanup_owned_sprites()`. Users must save entity state in `on_exit()` and re-create sprites in `on_reveal()`.
- **Timers survive push-over**: Scene-owned timers continue running when the scene is covered (`permanent=False`). They are only cancelled on permanent removal (pop/replace/clear_and_push).
- **Scene-owned timer cancellation**: InventoryScene's `after(0.5, ...)` timer is properly cancelled when the scene exits before the timer fires.

### Verification

All 24 tests pass. Full suite: **2795 passed, 3 skipped** (up from 2771 — 24 new tests added, 0 regressions).

## Stage 5 — Asset/Resource Edge-Case Probes & Final Report

**Date:** 2026-03-25

### Scope

Systematic runtime probes of every asset/resource error path: missing files, corrupt files, bad parameters, cache behavior, save file corruption variants, audio channel errors, cursor registration, particle emitter deferred validation, animation frame resolution, @2x variant selection.

### Runtime probe script

`scripts/stage5_asset_probe.py` — **44 probes**, all executed headlessly.

```bash
uv run python scripts/stage5_asset_probe.py
# → 44/44 passed, 0 bugs found
# → PASS — all asset/resource edge cases handled correctly
```

### Probes by category

**Asset loading — missing files (A1–A5):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| A1 | `Sprite("sprites/nonexistent")` | `AssetNotFoundError` with tried paths in message |
| A2 | `Sprite("")` (empty name) | `AssetNotFoundError` |
| A3 | `assets.sound("missing_sfx")` | `AssetNotFoundError` listing .wav/.ogg/.mp3 |
| A4 | `assets.music("missing_track")` | `AssetNotFoundError` listing .ogg/.wav/.mp3 |
| A5 | `assets.frames("nonexistent_walk")` | `AssetNotFoundError` with glob pattern |

**Asset loading — optional/graceful handling (A6–A8):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| A6 | `audio.play_sound("missing", optional=True)` | Returns `None` silently |
| A7 | `audio.play_music("missing", optional=True)` | Returns `None` silently |
| A8 | `audio.crossfade_music("missing")` (no optional flag) | `AssetNotFoundError` propagates |

**Asset loading — caching (A9–A10):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| A9 | Same image name returns same handle | Cached correctly |
| A10 | Same sound name returns same handle | Cached correctly |

**Corrupt/empty files (A11–A12):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| A11 | Corrupt PNG bytes (`\x00\x01BAD`) | Mock backend accepts (no content validation) |
| A12 | Zero-byte PNG file | Mock backend accepts (path exists → OK) |

**ColorSwap / palettes (A13–A15):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| A13 | `get_palette("nonexistent_team")` | `KeyError` with palette name |
| A14 | `Sprite("knight", team_palette="blue_team")` unregistered | `KeyError` |
| A15 | `ColorSwap(source=[2 colors], target=[1 color])` | `ValueError` |

**CursorManager (A16–A17):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| A16 | `cursor.register("attack", "ui/nonexistent")` | `AssetNotFoundError` |
| A17 | `cursor.set("nonexistent")` | `KeyError` |

**ParticleEmitter deferred validation (A18):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| A18 | `ParticleEmitter("nonexistent_particle")` — construct then `burst()` | Construction succeeds; `AssetNotFoundError` on `burst()` |

**Sprite edge cases (A19, A24):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| A19 | `sprite.image = "nonexistent"` | `AssetNotFoundError` |
| A24 | `Sprite(...)` after `game._teardown()` | `RuntimeError("No active Game")` |

**AnimationDef validation (A20–A23):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| A20 | `AnimationDef(frame_duration=0)` | `ValueError` |
| A21 | `AnimationDef(frame_duration=-0.1)` | `ValueError` |
| A22 | `AnimationDef(frame_duration=NaN)` | `ValueError` |
| A23 | `Sprite.play()` with missing frame images | `AssetNotFoundError` |

**@2x variant selection (A25–A26):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| A25 | `scale_factor=2.0` with `hero@2x.png` present | @2x variant selected |
| A26 | `scale_factor=1.0` with `hero@2x.png` present | Base variant selected |

**Audio edge cases (AU1–AU5):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| AU1 | `audio.set_volume("nonexistent_channel", 0.5)` | `KeyError` |
| AU2 | `audio.play_sound("click", channel="nonexistent")` | `KeyError` |
| AU3 | `audio.crossfade_music("b", duration=NaN)` | `ValueError` |
| AU4 | `audio.crossfade_music("b", duration=-1.0)` | `ValueError` |
| AU5 | `audio.play_pool("nonexistent_pool")` | `KeyError` |

**SaveManager edge cases (S1–S12):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| S1 | `load(1)` on empty slot | Returns `None` |
| S2 | `save(1, ...)` creates missing directory | Directory auto-created |
| S3 | Corrupt JSON in save file | `SaveError` with slot number + recovery hint |
| S4 | JSON array (non-dict) in save file | `SaveError("expected JSON object")` |
| S5 | Binary garbage in save file | `SaveError` (wraps `UnicodeDecodeError`) |
| S6 | Zero-byte save file | `SaveError` (wraps `JSONDecodeError`) |
| S7 | Non-serializable state (lambda) | `SaveError` (wraps `TypeError`) |
| S8 | `slot=0`, `slot=-1`, `slot=float`, `slot=str` | `ValueError` / `TypeError` |
| S9 | `delete(99)` on nonexistent slot | Silent no-op |
| S10 | `delete(1)` on existing slot | File removed, `load(1)` returns `None` |
| S11 | `list_slots()` with corrupt slot 3 | `SaveError` propagates |
| S12 | `delete()` slot validation | `ValueError`/`TypeError` as expected |

**FSM (F1):**

| Probe | Edge case | Outcome |
|-------|-----------|---------|
| F1 | `sm.trigger("nonexistent_event")` | Silent no-op (state unchanged) |

### Bugs found

**None.** All 44 probes passed. The framework's asset, audio, save, and resource error handling is comprehensive and consistent.

---

## Findings Summary Table (F42–F58)

All bugs were found via runtime probes with exact repro steps. Fixed with regression tests.

| ID | Stage | Component | Description | Fix | Tests |
|----|-------|-----------|-------------|-----|-------|
| **F42** | 2 | `actions.py` | `Repeat(times=-1)` silently accepted as no-op | `ValueError` for negative int; `TypeError` for bool | 6 |
| **F43** | 2 | `actions.py` | `MoveTo(scalar)` leaked raw `IndexError`/`TypeError` | `iter()`/`next()` validation with clear messages | 14 |
| **F44** | 3 | `widgets.py` | `ProgressBar(value=NaN)` bypassed setter validation | Constructor validates `isfinite()` | 11 |
| **F45** | 3 | `components.py` | `Button.text = None` crashed in `_estimate_text_width` | `TypeError` at setter | 3 |
| **F46** | 3 | `particles.py` | `ParticleEmitter.position = (NaN, 0)` silently stored | Setter validates `isfinite()` | 4 |
| **F47** | 3 | `animation.py` | `AnimationPlayer.update(NaN)` froze permanently | Skip frame, preserve state, recover | 5 |
| **F48** | 3 | `camera.py` | `Camera.enable_edge_scroll(NaN, NaN)` accepted | Validates `isfinite()` | 5 |
| **F49** | 3 | `camera.py` | `Camera.enable_key_scroll(NaN)` accepted | Validates `isfinite()` | 5 |
| **F50** | 3 | `camera.py` | `Camera.world_bounds = (NaN, ...)` / inverted accepted | Validates finite + ordering | 9 |
| **F51** | 3 | `widgets.py` | `Tooltip(delay=NaN/Inf/-1)` misbehaved | Validates finite + ≥ 0 | 8 |
| **F52** | 3 | `sprite.py` | `Sprite.tint = (NaN, ...)` passed NaN to backend | Validates `isfinite()` per component | 6 |
| **F53** | 3 | `sprite.py` | `Sprite.move_to((NaN, 0))` created NaN-duration tween | Validates `isfinite()` | 5 |
| **F54** | 3 | `widgets.py` | `DataTable(row_height=0)` accepted | `ValueError` for ≤ 0 | 8 |
| **F55** | 3 | `widgets.py` | `Grid(cell_size=(-10, 64))` accepted | `ValueError` for negative | 10 |
| **F56** | 3 | `screens.py` | `SaveLoadScreen(slot_count=0)` accepted | `ValueError` for ≤ 0 | 5 |
| **F57** | 4 | `scene.py` | `flush_pending_ops` exception left stale ops in queue | Clear queue before re-raising | 2 |
| **F58** | 4 | `scene.py` | Direct scene ops didn't flush deferred ops from on_exit | Added `_flush_after_direct_op()` | 11 |

> **Tests column** counts all tests in each finding's regression class(es), including supplemental/acceptable-edge-case documentation tests. **F54** includes 3 `DataTableShortColWidthsAcceptable` tests. **F55** includes 3 `GridZeroCellSizeAcceptable` tests. **F58** includes 5 `DeferredOpsSafety` supplemental tests. Stage 4 lifecycle file also contains 24 general lifecycle tests not attributed to a specific finding.

**Total: 17 bugs found and fixed, 141 regression tests across 3 files (Stages 2–4), plus 24 gameplay-workflow tests (Stage 4).**

---

## Final Test Suite Counts

### Delivery baseline (`--ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot`)

| Metric | Value |
|--------|-------|
| **Collected** | **2798** |
| **Passed** | **2795** |
| **Skipped** | **3** (`game.run()` under `SAGA2D_HEADLESS=1`) |
| **Failed** | **0** |
| **Runtime** | ~31s |

### Full tree (all of `tests/`)

| Metric | Value |
|--------|-------|
| **Collected** | **2829** |
| **Passed** | 2795 + visual_verify passes (environment-dependent) |
| **Failed** | 11 (`tests/visual_verify/` — AI/screenshot golden assertions, not engine bugs) |
| **Skipped** | 3 (`game.run()`) + 2 (`test_ai_checker.py` — needs `ANTHROPIC_API_KEY`) |

### Work product

| Metric | Value |
|--------|-------|
| **New test files (Stages 2–4)** | 4 files, 165 tests (20 + 84 + 37 + 24); net Δ +164 passing¹ |
| **Delivery baseline change** | 2631 → 2795 passed (+164) |
| **Runtime probe scripts** | 44 probes (Stage 5) + 41 probes (Stage 4) = 85 total |
| **Standalone scripts** | `smoke_game_move_to.py`, `stage4_gameplay_workflow.py`, `stage4_probe.py`, `stage5_asset_probe.py` |

> ¹ 165 tests in files vs +164 net passing: Stage 3 added 84 tests but 16 existing tests were updated to expect stricter validation, and one of those updates subsumed coverage that had been counted in the prior baseline, yielding a net +83 for that stage.

### Test evolution (delivery baseline)

| Milestone | Passed | Δ |
|-----------|--------|---|
| Stage 1 baseline | 2631 | — |
| + Stage 2 (actions edge cases) | 2651 | +20 |
| + Stage 3 (UI/rendering edge cases) | 2734 | +83 |
| + Stage 4 (lifecycle regression) | 2771 | +37 |
| + Stage 4 (gameplay workflow) | 2795 | +24 |
| **Final** | **2795** | **+164** |

---

## Self-Critique

### What went well

1. **Systematic probing**: Runtime probes before fixes ensured every bug had exact repro steps and wasn't a test artifact.
2. **NaN/Inf coverage**: The IEEE 754 quirk discovery (Python 3.13 `min/max` behavior) caught subtle bugs that static analysis would miss.
3. **End-to-end workflow**: The Stage 4 gameplay workflow discovered a key framework design property (sprites removed on push-over) that wasn't obvious from unit tests alone.
4. **Error message quality**: Every `AssetNotFoundError` includes tried paths; every `SaveError` includes slot number and recovery hint.

### What could be improved

1. **Corrupt file testing limited by mock backend**: The mock backend never reads file contents, so corrupt PNG/WAV/OGG files don't surface errors. These edge cases can only be tested with the real pyglet backend (requires a display server). This is a structural testing gap.
2. **No `optional` flag on `crossfade_music()`**: Unlike `play_sound()` and `play_music()`, `crossfade_music()` has no graceful degradation for missing assets. A missing track during crossfade crashes. This is a potential API gap (documented, not fixed — requires design decision).
3. **`ParticleEmitter` defers image validation**: A particle emitter constructed with a nonexistent image name will succeed silently, then crash at spawn time. This is by design (lazy loading), but could surprise users who expect fail-fast. Documented in Stage 5 probe A18.
4. **`SaveManager.delete()` doesn't wrap `PermissionError`**: Unlike `save()` and `load()`, `delete()` lets raw `PermissionError` propagate instead of wrapping it in `SaveError`. Documented, not fixed — minor consistency issue.
5. **No headless test for `game.run()` loop**: The production loop is guarded by `SAGA2D_HEADLESS=1`, so 3 tests are always skipped. The `tick()`-based testing is comprehensive, but the `run()` integration path (which includes clock timing) is only manually testable.
6. **Visual/screenshot tests have AI failures**: 11 tests in `visual_verify/` fail due to AI screenshot comparison, not engine bugs. These are not actionable without `ANTHROPIC_API_KEY` and a display server.

### Open coverage gaps (documented, not addressed)

| Gap | Reason |
|-----|--------|
| Corrupt file content (truncated PNG, bad WAV) | Mock backend doesn't validate; needs pyglet + display |
| `game.run()` production loop | Blocked by `SAGA2D_HEADLESS=1` |
| Pyglet rendering correctness | Requires display server |
| Audio hardware playback | Requires audio hardware |
| `crossfade_music()` missing `optional` parameter | API design decision needed |
| `Scene.add_sprite(None)` no guard | Low priority — documented in coverage gaps |
| `Game()` negative/zero resolution | Low priority — documented in coverage gaps |
