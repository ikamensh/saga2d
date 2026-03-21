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
- Persistence/resources: `.venv/bin/python -m pytest tests/kodo_test_persistence_resources.py -v`
- All kodo tests: `.venv/bin/python -m pytest tests/kodo_test_core.py tests/kodo_test_rendering.py tests/kodo_test_systems.py tests/kodo_test_scene_lifecycle.py tests/kodo_test_sprite_actions.py tests/kodo_test_persistence_resources.py -v`

## Test Results (updated 2026-03-22)
- 1404 existing tests: all pass (SAGA2D_HEADLESS unset)
- 589 kodo tests: all pass (348 regression + 75 scene lifecycle + 81 sprite/action + 48 persistence/resources + 37 persistence/resources ext)
- 383 UI tests: all pass across 6 files
- Stage 4: F5/F6/F7 fixed, 0 known-issues remaining, 0 new UI findings
- Stage 5 (final pass): persistence + resource lifecycle (48+37=85 tests), 1 new finding (F8)

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
- F8: Binary save file corruption → unhandled UnicodeDecodeError → **fixed 2026-03-22**
  - save.py load(): added UnicodeDecodeError to except clause
  - 2 regression tests: test_load_binary_content_raises_save_error, test_list_slots_with_binary_at_slot
- F9: Valid JSON non-object (e.g. [1,2,3]) crashes list_slots/SaveLoadScreen → **fixed 2026-03-22**
  - save.py load(): added `isinstance(data, dict)` check after json.loads(), raises SaveError if not dict
  - 6 regression tests: array, string, null, number, boolean non-objects + list_slots with array
  - Updated 3 existing tests that expected old buggy pass-through behavior

## Sharp Edges (design-intent, verified by execution)
- SE1: list_slots() aborts on first corrupt slot — no partial results
- SE2: game.save() saves top scene only — bottom scene state invisible
- SE3: game.load() with empty stack returns data but skips load_save_state()
- SE4: game.save() after _teardown() is silent noop (top()=None → early return)
- SE5: push() strips old top's resources (sprites removed, timers cancelled) — recreate in on_reveal()
- SE6: push() fires on_exit() on old top (not just pop/replace)
- SE7: failed save (non-serializable) leaves original file intact via atomic write
- SE8: SaveManager.load() now validates top-level is dict (F9 fix) — but doesn't validate envelope keys; wrong-typed "state" still loads fine
- SE9: Game.load() passes data["state"] to load_save_state without type-checking (list/None/string all passed through)
- SE10: Future version numbers (version=99) load without error — no version gating in load()

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
