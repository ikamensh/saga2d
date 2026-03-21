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
- Scene lifecycle tests: `.venv/bin/python -m pytest tests/kodo_test_scene_lifecycle.py -v`
- Visual tests require display + pyglet (headless blocked)

## Test Results (2026-03-21)
- 1404 existing tests: 1401 pass (SAGA2D_HEADLESS=1), 1404 pass (unset)
- 348 kodo regression tests: all pass
- 73 scene lifecycle exploratory tests: all pass
- 3 env-dependent failures: game.run() tests in tests/core/test_game.py

## Key Architecture
- `saga2d/scene.py:526` — `_cleanup_exiting_scene()` has `hasattr(scene.game, 'cursor')` guard
- FakeGame in test_adversarial.py (7 uses) and kodo_test_core.py (4 uses): minimal stand-in with `_hud = None` only
- FakeGame can't call draw() (no `_backend` attr) — use real Game fixture for draw tests
- conftest.py: `mock_game` fixture → `Game("Test", backend="mock", resolution=(1920, 1080))`
- Test dirs excluded from default collection: visual/, screenshot/, visual_verify/
- Scene.add_sprite() needs real Sprite with valid image; use MagicMock(is_removed=False) for unit tests
- MockBackend.inject_key(key, type="key_press") — NOT inject_key(key, pressed=True)
- Scene owned timers: `_get_owned_timers()` (lazy set), NOT `_owned_timer_ids`

## Confirmed Findings
- F1: cursor crash on FakeGame → fixed (commit 477220f, hasattr guard)
- F2: Repeat action yields 1/tick → design intent
- F3: Sprite.move_to() speed=0/negative → fixed (commit 477220f)
- F4: Button fires on right-click → fixed (commit 477220f)
- F5: on_exit exception leaves scene stuck on stack (KNOWN ISSUE, NOT FIXED)
  - In `_apply_pop()`: on_exit() raises → `self._stack.pop()` never executes → scene stays
  - Repro: `scene with on_exit raising RuntimeError → st.pop() raises, stack unchanged`
  - Same issue exists in US28 from prior test report

## SceneStack Behavior Notes (from exploratory testing)
- Mutations in on_enter: IMMEDIATE (not deferred)
- Mutations in on_exit: DEFERRED (_in_on_exit=True → _should_defer())
- Mutations in on_reveal: DEFERRED (on_reveal is inside _apply_pop which has _in_on_exit=True)
- Mutations in update: DEFERRED (_in_tick=True)
- Deferred ops flushed FIFO order in flush_pending_ops()
- on_enter exception → scene rolled back (popped from stack)
- replace on empty stack → acts as push
- clear_and_push exits in REVERSE order (top to bottom)
- transparent and pause_below are INDEPENDENT flags
- scene.game set BEFORE on_enter, cleared AFTER pop/replace/clear (in _teardown_exited_scene)
- scene.game kept alive when pushed over (not popped)
- Sprites+timers cleaned on push-over; UI preserved (may be revealed)
- UI cleared only in _teardown_exited_scene (permanent removal)
