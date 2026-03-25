# Test report — Stage 1 install & smoke (tester agent)

**Date:** 2026-03-25  
**Repo:** `saga2d` (workspace root)

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

**Collection:** **2665** tests (`pytest tests/ --co -q`).

**With `SAGA2D_HEADLESS=1` (full tree):**

- **2649 passed**, **11 failed**, **5 skipped**, ~45s (first full run timing)
- **Failures:** all under `tests/visual_verify/` — `test_menu_tutorial_ai.py` (8 tests) and `test_ui_with_ai.py` (3 tests); failures are AI / screenshot golden assertions (not mock-backend regressions)
- **Skips:** 3× `tests/core/test_game.py` — `game.run()` disabled when `SAGA2D_HEADLESS` is set; 2× `tests/visual_verify/test_ai_checker.py` — requires `ANTHROPIC_API_KEY`

**Excluding optional AI visual bucket** (`--ignore=tests/visual_verify`):

- **2631 passed**, **3 skipped** (~34s)
- **Skips:** same three `game.run()` tests in `tests/core/test_game.py`

## Claimed “2,522 tests”

On this machine, **2,522 passing is not current**: the suite collected **2665** tests and **2649** passed with the full tree (before counting failures as “not pass”). The **2631** figure matches “everything except `tests/visual_verify`” with only the headless `game.run()` skips.

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
