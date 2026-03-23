# Worker Smart Notes

## Project
- Location: `/Users/ikamen/ai-workspace/experiments/by_kodo/saga2d`
- Python: `.venv/bin/python` (3.13.2) — do NOT use system python3
- Package manager: `uv` (`uv pip install -e ".[dev]"`)
- Current commit: `4227501`
- `SAGA2D_HEADLESS=1` is set in environment — causes 3 game.run() test failures (skipped)

## Test Commands
- Full suite: `SAGA2D_HEADLESS=1 .venv/bin/python -m pytest --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q`
- Crossfade repro: `SAGA2D_HEADLESS=1 .venv/bin/python -m pytest tests/test_kodo_crossfade_repro.py -v`
- Clean run: `SAGA2D_HEADLESS= .venv/bin/python -m pytest --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -v`

## Test Results (updated 2026-03-23, post Stage 16)
- **25 bugs found and fixed** (F1, F3-F10, F12, F15-F16, F18-F19, F21-F28)
- 5 documented behaviors (F11, F13, F14, F17, F20), 11 sharp edges (SE1-SE11; SE12→F28)

## Stage 14 — Mini-App Integration Test & F27 Fix (2026-03-23)
- **Created**: `tests/test_kodo_mini_app.py` — 47 tests exercising all 12+ Saga2D systems together in a realistic "dungeon crawler" mini-app
- **Three scenes**: TitleScene (menu), GameScene (sprites/camera/particles/actions/timers/FSM/audio), InventoryScene (overlay with List/DataTable/TextBox)
- **F27 found and fixed**: DataTable(row_height=0) ZeroDivisionError — same class as F24 (List widget). Added `if self._row_height <= 0: return True` guard in `DataTable.on_event()`
- **File changed**: `saga2d/ui/widgets.py`
- **Key integration patterns**: FSM transitions use nested dict `{state: {event: target}}`, Label uses `.text` property setter not `._text`, List uses `.selected_index` not `.selected`, Camera follow updates during `camera.update(dt)` not immediately, audio crossfade needs patched `audio._assets.music`/`audio._assets.sound` lambdas for mock backend

## Stage 12 Investigation (2026-03-23) — Audio Crossfade + Fix Verification

### Audio Crossfade: No State Corruption Bug Found
- `_CrossfadeProxy` reads `_volumes` dict **live** on each setter call — channel volume changes propagate on next tween tick automatically
- **SE11 (sharp edge)**: `set_volume()` mid-crossfade immediately re-applies to `_current_player_id` (new player) but NOT `_crossfade_old_player`. The old player has stale effective volume for **one frame** until the next tween tick via proxy. Not audible, not a bug.
- `duration=0`: both tweens complete on first `game.tick()`, old player stopped, state clean
- Missing asset during crossfade: `_cancel_crossfade()` runs first (cancels tweens, stops old player), then `AssetNotFoundError` propagates — state consistent
- Rapid interruptions (4 crossfades): each cancels the previous, no player leak
- `_teardown` during crossfade: clean shutdown via `stop_music()` → `_cancel_crossfade()`
- Pool duplicate names: no-repeat uses index exclusion, not name — can "repeat" same sound via different indices. Design intent.
- Negative duration → `ValueError` from `TweenManager.create()`

### AnimationPlayer frame_duration=0: Fix Verified ✅
- `AnimationDef.__init__` + `AnimationPlayer.__init__`: `if not math.isfinite(frame_duration) or frame_duration <= 0: raise ValueError`
- 10 repros: 0, negative, NaN, Inf, -Inf for both classes, normal operation, loop-doesn't-hang

### List item_height=0: Fix Verified ✅
- `List.on_event()`: `if self._item_height <= 0: return True` at click and motion paths
- `_visible_count()`: returns 0 when item_height ≤ 0
- 5 repros: 0 click, 0 motion, 0 visible_count, -10 click, normal click

### Test File
`tests/test_kodo_crossfade_repro.py` — 39 tests (all pass)

## Stage 11B Audit (2026-03-23) — New Edge Cases
- **EC1**: DataTable(row_height=0) click → ZeroDivisionError (widgets.py on_event, no guard like List has)
- **EC2**: MoveTo.update(dt=NaN) silently corrupts sprite.position to (NaN,NaN) — no production path
- **EC3–EC5**: component.py iterates _children directly in draw(), handle_event(), _update_recursive() — no snapshot copy like TweenManager/TimerManager use → mutation during dispatch can skip/crash
- All details in `.kodo/test-report.md` and `.kodo/test-coverage.md` Stage 11B section

## Remaining Gaps (from Stage 11 discovery, not yet tested)
- ~~**Gap 3**: Particle NaN lifetime (PB1) — immortal particles, memory leak risk~~ **FIXED as F26 in Stage 13**
- **Gap 4**: Widget edge cases — Grid(0,0) keyboard nav, TabGroup add/select empty, DataTable click empty
- **Gap 5**: Tween from==to no-op, concurrent tweens, cancel-in-callback
- **Gap 6**: Camera pan_to(Inf), shake(decay=0), update(dt=0), large viewport vs small bounds

## Stage 13 — F26: ParticleEmitter NaN Lifetime Fix (2026-03-23)
- **Bug**: `lifetime=(nan, nan)` → `random.uniform(nan,nan)` returns NaN → `NaN <= 0` is False → particle never dies
- **Fix**: Added `math.isfinite()` + `>= 0` validation in `ParticleEmitter.__init__` for both lifetime tuple values
- **File changed**: `saga2d/rendering/particles.py`
- **Tests**: `tests/test_kodo_particle_nan_lifetime.py` (20 tests) — 8 rejection, 5 valid-still-works, 7 real workflow via Game.tick()
- **Updated**: `tests/test_kodo_systems_edge.py` — changed pre-fix documentation test to expect ValueError

## Stage 15 — Real User App Integration Test (2026-03-23)
- **Created**: `real_user_app.py` — 23-phase realistic game with simulated input
- **Systems exercised**: All 12+ systems end-to-end via mock backend with injected input
- **23 phases**: Title→Settings→World→Combat→Collect→Inventory→Timers→Save/Load→Camera→Rapid clicks→Rapid transitions→HUD→Tweens→Audio→Coordinates→Sprite removal→Camera follow removal→Game restart→Quit-to-title→Many sprites→Window close
- **64/64 state checks pass, 0 crashes, 0 bugs found**
- **API discovery pitfalls** (useful for developers):
  - `Style(bg_color=...)` is WRONG — use `Style(background_color=...)`
  - `Anchor` enum does NOT have `BOTTOM_CENTER` — use `Anchor.BOTTOM`
  - `SaveManager` slots are 1-indexed (`slot >= 1`), not 0-indexed
  - `game.save()` saves the **top** scene's state — if a PauseScene overlay is on top, it saves PauseScene's empty state, not the game scene below
  - Camera `_follow_target` is cleared lazily during `update()`, not immediately on `sprite.remove()`

## Stage 16 — F28: Scene-owned timers survive overlay push/pop (2026-03-23)
- **Bug**: SE12 promoted to F28. `_cleanup_exiting_scene()` unconditionally cancelled timers on push-over
- **Fix**: Added `permanent: bool = True` param to `_cleanup_exiting_scene()`, `_apply_push()` passes `permanent=False`
- **File changed**: `saga2d/scene.py` — 2 edits
- **Tests**: 1 updated + 4 new in `tests/core/test_scene_timers.py`, 1 updated in `tests/kodo_test_scene_lifecycle.py`
- **Also updated**: `real_user_app.py` (removed SE12 workaround), `scripts/overlay_timer_se12_repro.py` (flipped expected outcome)

## Key Architecture & API Notes
- Sprite("sprites/knight", position=(x,y)) — needs real asset in assets/images/sprites/
- Available test images: knight, knight_walk_01-03, knight_attack_01-03, enemy, crate, background
- Tick order: input → scene update → actions → particles → timers → tweens → animations → draw
- Removed sprite: _removed=True, deregistered from all game sets
- FakeGame can't call draw() (no _backend) — use real Game fixture for draw tests
- MockBackend.inject_key(key, type="key_press") — NOT pressed=True
- Game is a singleton — `_teardown()` between instances
- Camera is per-scene, not per-game
- `tween()` is module-level function
- `SaveManager(save_dir)` requires `Path`, not `str` (fixed F19: now auto-converts)
- `_CrossfadeProxy` in `audio.py` bridges tween system to backend player volumes
- `_cancel_crossfade()` stops old player tweens AND the old fading-out player
- List `on_event()` uses `InputEvent` (frozen dataclass from `saga2d.input`) — FakeEvent objects must include `action` attribute
- Widget `hit_test` needs `_computed_x/y/w/h` to be set manually in unit tests
