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
- Stage 7 E2E: `.venv/bin/python -m pytest tests/kodo_test_stage7_e2e.py -v`
- All kodo tests: `.venv/bin/python -m pytest tests/kodo_test_core.py tests/kodo_test_rendering.py tests/kodo_test_systems.py tests/kodo_test_scene_lifecycle.py tests/kodo_test_sprite_actions.py tests/kodo_test_persistence_resources.py tests/kodo_test_persistence_resources_ext.py tests/kodo_test_stage7_e2e.py -v`

## Test Results (updated 2026-03-22, Stage 7 + Adversarial)
- 1411 main tests: all pass (SAGA2D_HEADLESS unset)
- 664 kodo tests: all pass (8 files: core, rendering, systems, scene_lifecycle, sprite_actions, persistence, persistence_ext, stage7_e2e)
- 78 example tests: all pass
- 383 UI tests: all pass across 6 files
- Stage 7: 62 base E2E + 8 adversarial = 70 tests in kodo_test_stage7_e2e.py
- F13: NaN dt in Delay/FadeOut/FadeIn — documented, not fixed (5 tests)
- F14: play_sound channel='music'/'master' accepted — documented, not fixed (3 tests)

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

- F10: Game.__del__ crashes on partial init → **fixed 2026-03-22**
  - game.py _teardown(): hasattr guards for _timer_manager, _tween_manager, _scene_stack
  - 2 regression tests: test_teardown_safe_after_partial_init_f10, test_del_safe_after_partial_init_f10
- F11: Game.__del__ stderr on normal exit → **not fixed** (low value, try/except already catches)
- F12: Camera shake vs mouse picking → **fixed 2026-03-22**
  - camera.py: screen_to_world/world_to_screen now include _shake_offset_x/_y
  - 7 regression tests in TestShakePickingRegression (unit + E2E)
- F13: NaN dt in Delay/FadeOut/FadeIn → **not fixed** (documented with 5 tests)
  - Delay.update(NaN): elapsed=NaN, action stuck forever (NaN >= seconds is False)
  - FadeOut/FadeIn.update(NaN): ValueError from int(NaN)
  - No known production path produces NaN dt; fix would be math.isfinite guard
- F14: play_sound channel='music'/'master' accepted → **not fixed** (documented with 3 tests)
  - Docstring says only sfx/ui, but validation uses `channel not in self._volumes` which includes all 4
  - Functionally harmless — just applies different channel volume

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

## Stage 6C: Shake vs Picking + F10/F11 (2026-03-22)
- **F12**: Camera shake vs mouse picking — `screen_to_world`/`world_to_screen` now include shake offsets
  - camera.py: both methods add `_shake_offset_x/_y` to match rendering in `_sync_sprites_to_camera`
  - 7 regression tests in `tests/rendering/test_camera.py::TestShakePickingRegression`
  - E2E test proves click at rendered sprite position → correct world coords during shake
- **F10**: Game.__del__ crash on partial init — `_teardown()` now uses `hasattr` guards
  - game.py: guards `_timer_manager`, `_tween_manager`, `_scene_stack` with hasattr checks
  - 2 regression tests in `tests/kodo_test_persistence_resources.py::TestTeardownCompleteness`
- **F11**: Game.__del__ stderr on normal exit — NOT FIXED (low value)
  - Only fires if user forgets `_teardown()` + script exit with scenes on stack
  - `game.run()` always calls `_teardown()` in finally block, so production code unaffected
  - Existing `try/except` in `__del__` prevents propagation; just stderr noise

## Stage 6A: Clean-Room Install Findings (2026-03-22)
- `pip install .` works cleanly, installs saga2d + numpy + Pillow + pyglet
- `pip install -e ".[dev]"` also works, 1401/1404 tests pass (3 SAGA2D_HEADLESS failures)
- **F10**: Game.__del__ crashes on partial init — if Game() throws (e.g. wrong kwargs), `_teardown()` in `__del__` hits `AttributeError: 'Game' object has no attribute '_timer_manager'`. Repro: `Game('x', width=320)` → stderr noise.
- **F11**: Game.__del__ stderr noise on normal script exit — if user forgets `_teardown()` and script ends with scene on stack, `__del__` → `_teardown()` → `_cleanup_exiting_scene` → `ImportError: sys.meta_path is None` during Python shutdown. Repro: push a scene, don't teardown, exit script.
- Game is a singleton — second `Game()` without teardown raises RuntimeError
- No public `top()` on Game — must use `g._scene_stack.top()` (private API)
- No `camera` on Game — camera is per-scene (accessed via `getattr(scene, 'camera', None)`)
- No `tween` on Game — `tween()` is a module-level function
- `SaveManager(save_dir)` requires `Path`, not `str`
- `MoveTo((x,y), speed=n)` — position is a tuple, not two args
- `Panel()` doesn't take `x=`/`y=` kwargs — use `layout=`/`anchor=` based construction
- `Scene.add_sprite()` not `Scene.add()` for sprites; `scene.ui.add()` for UI
- `StateMachine(states_list, initial, transitions=dict)` not `StateMachine(initial)`

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
