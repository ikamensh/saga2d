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

## Test Results (2026-03-21)
- 1404 existing tests: all pass (SAGA2D_HEADLESS unset)
- 348 kodo regression tests: all pass
- 73 scene lifecycle exploratory tests: all pass
- 81 sprite/action/animation tests: all pass
- Total kodo exploratory: 73 + 81 = 154

## Confirmed Findings
- F1: cursor crash on FakeGame → fixed (commit 477220f)
- F2: Repeat action yields 1/tick → design intent
- F3: Sprite.move_to() speed=0/negative → fixed (commit 477220f)
- F4: Button fires on right-click → fixed (commit 477220f)
- F5: on_exit exception leaves scene stuck on stack (KNOWN ISSUE)
- **F6: sprite.do() inside Do callback silently drops new action (BUG)**
  - In update_action(): old Sequence.update() continues after s.do() replaces _current_action
  - When Sequence returns True, update_action() overwrites _current_action=None
  - Repro: `.venv/bin/python -m pytest tests/kodo_test_sprite_actions.py::TestComplexNesting::test_do_replaces_action_during_sequence_bug_f6 -v`
  - Fix direction: update_action() should save ref before calling update(), check if _current_action changed
- **F7: Animation queue chains of 3+ broken (BUG)**
  - play() calls self._anim_queue.clear() (sprite.py line 438)
  - When _drain_queue() pops next and calls play(), remaining queue items are cleared
  - Repro: `.venv/bin/python -m pytest tests/kodo_test_sprite_actions.py::TestAnimationQueue::test_queue_chain_three_bug_f7 -v`
  - Fix direction: _drain_queue should save queue, or play() should not clear queue when called from _drain_queue

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
