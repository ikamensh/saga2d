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
- Scene lifecycle: `.venv/bin/python -m pytest tests/kodo_test_scene_lifecycle.py -v`
- Sprite/action/animation: `.venv/bin/python -m pytest tests/kodo_test_sprite_actions.py -v`
- All kodo tests: `.venv/bin/python -m pytest tests/kodo_test_core.py tests/kodo_test_rendering.py tests/kodo_test_systems.py tests/kodo_test_scene_lifecycle.py tests/kodo_test_sprite_actions.py -v`

## Test Results (updated 2026-03-22)
- 1404 existing tests: all pass (SAGA2D_HEADLESS unset)
- 504 kodo tests: all pass (348 regression + 75 scene lifecycle + 81 sprite/action)
- 383 UI tests: all pass across 6 files (test_ui 92, test_widgets 149, test_screens 42, test_hud 38, test_drag_drop 49, test_theme 13)
- Stage 4: F5/F6/F7 fixed, 0 known-issues remaining, 0 new UI findings

## Confirmed Findings
- F1: cursor crash on FakeGame → fixed (commit 477220f)
- F2: Repeat action yields 1/tick → design intent
- F3: Sprite.move_to() speed=0/negative → fixed (commit 477220f)
- F4: Button fires on right-click → fixed (commit 477220f)
- F5: on_exit exception leaves scene stuck → **fixed 2026-03-22**
  - scene.py: _apply_pop/replace use try/finally to pop before exception propagates
  - scene.py: _apply_clear_and_push catches on_exit errors, cleans all scenes, re-raises first error
  - 3 regression tests: pop, replace, clear_and_push paths
- F6: sprite.do() inside Do callback drops new action → **fixed 2026-03-22**
  - sprite.py update_action(): saves ref before update(dt), only clears if action unchanged
  - Regression test: test_do_replaces_action_during_sequence_f6
- F7: Animation queue chains of 3+ broken → **fixed 2026-03-22**
  - sprite.py play(): added `_from_drain` param, skips queue.clear() when called from _drain_queue
  - Regression test: test_queue_chain_three_f7

## Key Architecture & API Notes
- Sprite("sprites/knight", position=(x,y)) — needs real asset in assets/images/sprites/
- Available test images: knight, knight_walk_01-03, knight_attack_01-03, enemy, crate, background
- Sprite.do(action) → registers in game._action_sprites; update_action() called each tick
- Sprite.play(anim) → registers in game._animated_sprites; update_animation() each tick
- Tick order: input → scene update → actions → particles → timers → tweens → animations → draw
- Actions run before animations — action callbacks can queue animations for same frame
- Sequence chains instant actions (dt=0 for next child) — Delay first tick gets dt=0 if preceded by instant
- Parallel finishes when all *finite* children done, stops infinite ones
- Repeat yields after each iteration (1 per tick for instant children)
- Z-order: layer * 100_000 + int(y). Higher y → drawn in front.
- Removed sprite: _removed=True, deregistered from all game sets, property sets still work internally but don't sync to backend
- FakeGame can't call draw() (no _backend) — use real Game fixture for draw tests
- MockBackend.inject_key(key, type="key_press") — NOT pressed=True
- Scene owned timers: _get_owned_timers() (lazy set)
