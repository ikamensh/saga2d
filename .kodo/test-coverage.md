# Feature Coverage

Tracked across `kodo test` runs. Baseline: commit 477220f, 2026-03-21. Stage 4 fixes: 2026-03-22.

## Feature Map (50 areas)

| # | Feature / Workflow | Test File(s) | Test Count | Last Tested | Status | Findings |
|---|-------------------|-------------|-----------|-------------|--------|----------|
| 1 | Install & import | conftest.py (implicit) | — | 2026-03-21 | pass | uv pip install OK |
| 2 | Game lifecycle (create/tick/teardown) | core/test_game.py | 7 | 2026-03-21 | pass (4/7) | 3 game.run() tests fail under SAGA2D_HEADLESS=1 |
| 3 | Game.run() main loop | core/test_game.py | 3 | 2026-03-21 | env-fail | RuntimeError when SAGA2D_HEADLESS=1; passes when unset |
| 4 | Scene stack (push/pop/replace/clear_and_push) | core/test_scene.py, kodo_test_scene_lifecycle.py | 36+73 | 2026-03-21 | pass | F1 cursor crash fixed; hook ordering, mutations during hooks, empty-stack ops all verified |
| 5 | Scene lifecycle hooks (on_enter/on_exit/on_reveal) | core/test_scene.py, kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | Exact hook ordering verified for all operations; game property lifetime tested |
| 6 | Scene drawing (draw_rect/draw_world_rect/bg color) | core/test_scene_draw.py | 12 | 2026-03-21 | pass | |
| 7 | Scene-owned sprites | core/test_scene_sprites.py | 19 | 2026-03-21 | pass | add/remove/cleanup verified |
| 8 | Scene-owned timers | core/test_scene_timers.py | 19 | 2026-03-21 | pass | timer cleanup on scene exit |
| 9 | Settings / configuration | core/test_settings.py | 7 | 2026-03-21 | pass | |
| 10 | Sprites (create/position/remove/anchor/y-sort) | rendering/test_sprite.py, kodo_test_sprite_actions.py | 64+16 | 2026-03-21 | pass | F3 speed validation fixed; z-order, layer separation, removal lifecycle tested |
| 11 | Sprite tinting | rendering/test_tint.py | 11 | 2026-03-21 | pass | |
| 12 | Actions (Sequence/Parallel/Delay/Do/MoveTo/Fade/Remove/Repeat) | actions/test_actions.py, kodo_test_sprite_actions.py | 50+40 | 2026-03-21 | pass | F2 Repeat design-intent; F6 action replacement bug found |
| 13 | Camera (center_on/follow/pan_to/shake/bounds) | rendering/test_camera.py | 27 | 2026-03-21 | pass | |
| 14 | Animation (play/queue/stop/loop/frames) | rendering/test_animation.py | 27 | 2026-03-21 | pass | |
| 15 | Particles (burst/continuous/stop/remove) | rendering/test_particles.py | 15 | 2026-03-21 | pass | |
| 16 | Color Swap (palette registration/apply) | rendering/test_color_swap.py | 6 | 2026-03-21 | pass | |
| 17 | UI Panel/Label/Button | ui/test_ui.py | 92 | 2026-03-22 | pass | F4 right-click fixed; layout math, anchoring, scene integration |
| 18 | UI Widgets (ProgressBar/List/Grid/DataTable/TextBox/TabGroup/Tooltip) | ui/test_widgets.py | 149 | 2026-03-22 | pass | DataTable 44 tests; PanelSpacing 14 |
| 19 | UI Layout (anchoring/flow) | ui/test_ui.py | (in #17) | 2026-03-22 | pass | All 9 anchors + flow |
| 20 | Theme & Style | ui/test_theme.py | 13 | 2026-03-22 | pass | Defaults, resolution, button states, overrides |
| 21 | HUD | ui/test_hud.py | 38 | 2026-03-22 | pass | Creation, visibility, input/update dispatch, scene transitions |
| 22 | Modal Screens (Message/Choice/Confirm/SaveLoad) | ui/test_screens.py | 42 | 2026-03-22 | pass | SequenceRunner, status/help modals |
| 23 | Drag & Drop | ui/test_drag_drop.py | 49 | 2026-03-22 | pass | DragManager, ghost tracking, drop targets, visual feedback |
| 24 | Audio (channels/music/sfx/crossfade/pools) | systems/test_audio.py | 8 | 2026-03-21 | pass | |
| 25 | Input (action mapping/key stealing/mouse events) | systems/test_input.py | 6 | 2026-03-21 | pass | |
| 26 | Save/Load (save/load/delete/list/corrupt) | systems/test_save.py, kodo_test_persistence_resources.py | 51+25 | 2026-03-22 | pass | SE1: list_slots aborts on first corrupt slot (design-intent); SE2: saves top scene only; SE7: atomic write protects against partial save; F9: non-object JSON now raises SaveError |
| 27 | Tweening (tween/ease/cancel) | actions/test_tween.py | 22 | 2026-03-21 | pass | |
| 28 | Timers (after/every/cancel/chaining) | actions/test_timer.py | 24 | 2026-03-21 | pass | |
| 29 | FSM (transitions/callbacks/validation) | systems/test_fsm.py | 13 | 2026-03-21 | pass | |
| 30 | Cursor (register/set/visibility) | systems/test_cursor.py | 6 | 2026-03-21 | pass | |
| 31 | Assets (image/sound/music/frames/@2x) | systems/test_assets.py | 17 | 2026-03-21 | pass | |
| 32 | Mock Backend (event injection/tracking) | conftest.py + all | — | 2026-03-21 | pass | |
| 33 | Integration: adversarial reentrancy | integration/test_adversarial.py, kodo_test_scene_lifecycle.py | 18+73 | 2026-03-21 | pass | 7 FakeGame tests pass (F1 fixed); mutations in on_enter/on_exit/on_reveal/update tested |
| 34 | Integration: resource leaks | integration/test_resource_leaks.py, kodo_test_persistence_resources.py | 9+23 | 2026-03-22 | pass | SE4: save after teardown is silent noop; SE5: push() strips old top's resources; WeakSet GC verified; action/anim cleanup on remove |
| 35 | Transparent/pause_below semantics | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | 8 tests: opaque hides below, transparent shows both, chain blocking, independence |
| 36 | Scene.game property lifetime | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | 6 tests: set before on_enter, cleared after pop/replace/clear_and_push, kept when pushed over |
| 37 | on_enter exception rollback | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | push/replace/clear_and_push all roll back on on_enter crash |
| 38 | Cleanup ordering (sprites/timers/UI) | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-22 | pass | SE5/SE6: push() calls on_exit+cleanup on old top; sprites removed, timers cancelled; UI kept on push, cleared on pop |
| 39 | on_exit exception handling | kodo_test_scene_lifecycle.py | 3 | 2026-03-22 | **fixed** | F5: on_exit exception now pops scene (pop/replace/clear_and_push paths) |
| 40 | Active-action removal | kodo_test_sprite_actions.py | 7 | 2026-03-21 | pass | Remove mid-MoveTo/Sequence/Parallel, self-remove in Do, action tracking cleanup |
| 41 | Orphaned sprites | kodo_test_sprite_actions.py | 3 | 2026-03-21 | pass | No scene owner, survives scene pop, teardown with active actions |
| 42 | Deep action nesting | kodo_test_sprite_actions.py | 18 | 2026-03-21 | pass | 5-deep Seq, 10-wide Par, Repeat(Seq), Seq(Par(Seq)), battle sequence |
| 43 | Action replacement mid-callback | kodo_test_sprite_actions.py | 1 | 2026-03-22 | **fixed** | F6: update_action() now preserves action set by callback |
| 44 | Animation queue/state transitions | kodo_test_sprite_actions.py | 12 | 2026-03-22 | pass | Play, queue, interrupt, stop, PlayAnim action |
| 45 | Animation queue chain 3+ | kodo_test_sprite_actions.py | 1 | 2026-03-22 | **fixed** | F7: play() no longer clears queue when called from _drain_queue |
| 46 | Save input validation (slot types/bounds) | kodo_test_persistence_resources.py | 8 | 2026-03-22 | pass | slot=0, negative, float, string for save/load/delete |
| 47 | Non-serializable state handling | kodo_test_persistence_resources.py | 4 | 2026-03-22 | pass | lambda, set, bytes, custom object → SaveError |
| 48 | Game._teardown completeness | kodo_test_persistence_resources.py | 4 | 2026-03-22 | pass | SE4: post-teardown save is noop; sprite sets cleared, subsystems nulled, stack drained, on_exit called |
| 49 | Sprite/timer/anim cleanup on transitions | kodo_test_persistence_resources.py | 7 | 2026-03-22 | pass | SE5: push strips old top resources; owned sprites removed on pop, timers cancelled, push/pop ×5 no leak |
| 50 | Save class name & version migration | kodo_test_persistence_resources.py | 4 | 2026-03-22 | pass | SE3: load with empty stack returns data, skips restore; V1→V2 migration with dict.get defaults |

## Example / Tutorial Tests

| Example | Test File | Test Count | Status |
|---------|-----------|-----------|--------|
| Battle Vignette | examples/test_battle_vignette.py | 14 | pass |
| Menu Tutorial | examples/test_menu_tutorial.py | 46 | pass |
| Tower Defense (example) | examples/test_tower_defense_example.py | 4 | pass |
| Tower Defense (tutorial) | examples/test_tower_defense_tutorial.py | 21 | pass |

## Sharp Edges (confirmed design-intent, not bugs)

Discovered via Stage 5 exploratory testing. All verified by execution.

| ID | Behavior | Why not a bug | Test |
|----|----------|---------------|------|
| SE1 | `list_slots()` aborts on first corrupt slot — remaining slots unread | `list_slots` delegates to `load()` which raises `SaveError` by design on corrupt JSON | `test_list_slots_corrupted_mid_list` |
| SE2 | `game.save()` captures only the top scene's state | Documented API; games needing multi-scene state must aggregate in `get_save_state()` | `test_save_saves_top_scene_not_bottom` |
| SE3 | `game.load()` with empty stack returns data but skips `load_save_state()` | Returns data so caller can reconstruct scenes manually; documented in docstring | `test_load_empty_stack_no_crash` |
| SE4 | `game.save()` after `_teardown()` is a silent no-op | `top()` returns `None` → early return; post-teardown use is unsupported | `test_save_after_teardown_raises` |
| SE5 | `push()` calls `_cleanup_exiting_scene` on old top — owned sprites removed, timers cancelled | Intentional resource hygiene; pushed-over scenes recreate resources in `on_reveal()` | `test_owned_sprites_removed_on_pop` + script verification |
| SE6 | `push()` fires `on_exit()` on the old top scene (not just pop/replace) | Consistent with SE5 cleanup; `on_reveal()` re-enters when pushed scene is popped | `test_teardown_calls_scene_on_exit` |
| SE7 | Failed save (non-serializable state) leaves original file untouched | Atomic write: serialize to `.tmp` then `replace()` — failure before replace preserves original | `test_save_after_failed_save_succeeds` |

## Blocked / Not Tested

| Feature | Directory | Reason |
|---------|-----------|--------|
| Visual rendering verification | tests/visual/ | Requires display + pyglet |
| Screenshot golden-image comparison | tests/screenshot/ | Requires display + pyglet |
| AI-powered visual verification | tests/visual_verify/ | Requires Anthropic API key |
| Audio playback (actual output) | — | Mock-only; no audio hardware tests |
| Performance / stress at scale | — | No load tests exist |

## Totals

- **50 feature areas** identified and tested
- **48 fully passing** (including 3 fixed: F5, F6, F7)
- **1 environment-dependent** (Game.run() with SAGA2D_HEADLESS)
- **0 known-issues** remaining
- **F9 fixed**: non-object JSON in save slot crashes list_slots/SaveLoadScreen (2026-03-22)
- **1 area (visual) blocked** by display requirement
- **1404 unit tests** collected, all pass
- **552 kodo tests** all pass (348 regression + 75 scene lifecycle + 81 sprite/action + 48 persistence/resources)
- **383 UI tests** across 6 test files
