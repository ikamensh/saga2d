# Worker Smart Notes — Saga2D

## Project
- 2D game framework (Python 3.12+, pyglet backend, mock backend for headless testing)
- Repo: `/Users/ikamen/ai-workspace/experiments/by_kodo/saga2d`
- Run tests: `SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q`
- Smoke test: `uv run python scripts/smoke_game_move_to.py` (no env vars needed)

## Key Architecture
- `saga2d/` — core package: Game, Scene, Sprite, actions, audio, UI components, util (tween, timer, fsm)
- `saga2d/rendering/` — camera.py, sprite.py, particles.py, animation.py, layers.py
- `saga2d/ui/` — component.py (base Component + _UIRoot), components.py (Label/Button/Panel), widgets.py (List/Grid/DataTable/etc), layout.py, theme.py
- `saga2d/backends/` — mock_backend.py (headless), pyglet_backend.py
- `tests/` — 2651+ tests (headless), organized by area (actions/, core/, rendering/, systems/, ui/, integration/, kodo_test_*.py, test_kodo_*.py)

## Test Counts (2026-03-25, post-Stage 2)
- 2651 passed, 3 skipped (game.run() under SAGA2D_HEADLESS), 0 failures (excluding visual_verify)
- ~78s runtime (headless)

## Stage 1 Status — COMPLETE (2026-03-25)
- Scope: Environment Setup & Smoke Testing — game loop, push/pop scenes, backend protocol, Game + Scene/SceneStack
- Smoke script `scripts/smoke_game_move_to.py` validates Game→Scene→Sprite→MoveTo E2E

## Stage 2 — Core Engine & Actions Edge Cases (2026-03-25)
### Investigation results
- Game.tick(NaN/Inf/negative): already guarded with ValueError — no new bug
- Do(non-callable): already guarded with TypeError — no new bug
- Repeat(times=float/NaN): already guarded with TypeError — no new bug
- **F42**: Repeat(times=negative_int) silently accepted — no-op instead of error
- **F43**: MoveTo(scalar/1-tuple) leaked raw IndexError/TypeError

### Fixes applied
- F42: `saga2d/actions.py` — Repeat.__init__ raises ValueError for negative times, TypeError for bool
- F43: `saga2d/actions.py` — MoveTo.__init__ validates position with iter()/next(), gives clear TypeError messages

### Files changed
- `saga2d/actions.py` — F42 + F43 fixes
- `tests/test_kodo_stage2_regression.py` — NEW, 20 regression tests (6 for F42, 14 for F43)
- `tests/test_kodo_stage2_core_actions.py` — updated 2 tests to expect new exceptions
- `tests/test_kodo_new_edge_cases.py` — updated 1 test to expect ValueError
- `tests/kodo_test_rendering.py` — updated 1 test to expect ValueError; fixed 2 stale timer regex patterns
- `test-report.md` — added Stage 2 section with repro steps, fixes, verification
- `.kodo/test-coverage.md` — updated gap table statuses for exercised/fixed items

## Bugs Fixed (F-numbered)
- F1-F10, F12, F15-F16, F18-F19, F21-F33, F42-F43 (31 total)
- F42: Repeat(times=negative_int) now raises ValueError (actions.py)
- F43: MoveTo position validation — clear TypeError for scalar/short-tuple/non-numeric (actions.py)

## Key Patterns
- NaN/Inf: All public APIs validate with `math.isfinite()` (actions, tween, timer, camera, particles, widgets)
- Camera: all input paths now guarded — center_on, scroll, pan_to, shake (params), update (dt), follow (target pos)
- Iteration safety: TweenManager, TimerManager, Component draw/update/handle_event all use `list()` snapshots
- Sprite.position setter validates finite values — prevents silent NaN corruption
- MockBackend for all headless tests; `_current_game` module-level singleton pattern
- Assets: `Sprite('sprites/knight')` resolves to `assets/images/sprites/knight.png`
- Repeat: bool is subclass of int — must check `isinstance(times, bool)` explicitly to reject it
- MoveTo: use iter()/next() for position validation — avoids index-based access that leaks raw errors

## Gotchas
- `Game.__del__` prints ImportError during Python shutdown (known F11, cosmetic)
- `Sprite` requires real asset file even with mock backend
- `SaveManager` requires `Path` not `str`
- `reversed()` on a live list does NOT protect against mutation — must use `list()` first
- Python 3.13: `min(1.0, nan)` → 1.0; `max(0.0, nan)` → 0.0 (IEEE 754 quirk)
- IEEE 754: `NaN <= 0` is False AND `NaN > 0` is False — both branches of if/else can be skipped!
- Camera.follow() NaN: without the guard, `_clamp()` with world_bounds gave platform-dependent results
