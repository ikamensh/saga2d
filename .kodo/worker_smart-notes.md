# Worker Smart Notes

## Project
- Location: `/Users/ikamen/ai-workspace/experiments/by_kodo/saga2d`
- Python: `.venv/bin/python` (3.13.2) — do NOT use system python3
- Package manager: `uv` (`uv pip install -e ".[dev]"`)
- Current commit: `477220f`
- `SAGA2D_HEADLESS=1` is set in environment — causes 3 game.run() test failures

## Test Commands
- Full suite: `.venv/bin/python -m pytest --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -v`
- Clean run (0 failures): `SAGA2D_HEADLESS= .venv/bin/python -m pytest --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -v`
- Kodo tests only: `.venv/bin/python -m pytest tests/kodo_test_core.py tests/kodo_test_rendering.py tests/kodo_test_systems.py -v`
- Visual tests require display + pyglet (headless blocked)

## Baseline Results (2026-03-21)
- 1404 tests collected, 1401 pass (SAGA2D_HEADLESS=1), 1404 pass (unset)
- 3 failures: test_run_pushes_start_scene_and_loops, test_run_calls_backend_quit_after_loop, test_window_close_stops_run_loop — all in tests/core/test_game.py — RuntimeError from SAGA2D_HEADLESS guard
- 348 kodo regression tests: all pass
- FakeGame cursor bug (F1): already fixed (hasattr guard in scene.py:526)
- 7 adversarial FakeGame tests + 4 kodo FakeGame tests all pass

## Key Architecture
- `saga2d/scene.py:526` — `_cleanup_exiting_scene()` has `hasattr(scene.game, 'cursor')` guard
- FakeGame in test_adversarial.py (7 uses) and kodo_test_core.py (4 uses): minimal stand-in with `_hud = None` only
- conftest.py: `mock_game` fixture → `Game("Test", backend="mock", resolution=(1920, 1080))`
- Test dirs excluded from default collection: visual/, screenshot/, visual_verify/

## Previously Fixed Bugs
- F1: cursor crash on FakeGame (commit 477220f)
- F2: Repeat action yields 1/tick (design intent, documented)
- F3: Sprite.move_to() speed=0/negative (commit 477220f)
- F4: Button fires on right-click (commit 477220f)

## Asset Generation
- `python3 generate_assets.py` regenerates all assets
- Battle sprites: 64×64 authored space, CX/CY = 32 (center)
- Tower defense: SCREEN 1280×960, TILE_SIZE 64
