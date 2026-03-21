# Feature Coverage

Tracked across `kodo test` runs. Baseline: commit 477220f, 2026-03-21.

## Feature Map (45 areas)

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
| 17 | UI Panel/Label/Button | ui/test_ui.py, ui/test_widgets.py | 21 | 2026-03-21 | pass | F4 right-click bug fixed |
| 18 | UI Widgets (ProgressBar/List/Grid/DataTable/TextBox/TabGroup/Tooltip) | ui/test_widgets.py | (in #17) | 2026-03-21 | pass | |
| 19 | UI Layout (anchoring/flow) | ui/test_ui.py | (in #17) | 2026-03-21 | pass | All 9 anchors + flow |
| 20 | Theme & Style | ui/test_theme.py | 2 | 2026-03-21 | pass | |
| 21 | HUD | ui/test_hud.py | 8 | 2026-03-21 | pass | |
| 22 | Modal Screens (Message/Choice/Confirm/SaveLoad) | ui/test_screens.py | 5 | 2026-03-21 | pass | |
| 23 | Drag & Drop | ui/test_drag_drop.py | 14 | 2026-03-21 | pass | |
| 24 | Audio (channels/music/sfx/crossfade/pools) | systems/test_audio.py | 8 | 2026-03-21 | pass | |
| 25 | Input (action mapping/key stealing/mouse events) | systems/test_input.py | 6 | 2026-03-21 | pass | |
| 26 | Save/Load (save/load/delete/list/corrupt) | systems/test_save.py | 10 | 2026-03-21 | pass | |
| 27 | Tweening (tween/ease/cancel) | actions/test_tween.py | 22 | 2026-03-21 | pass | |
| 28 | Timers (after/every/cancel/chaining) | actions/test_timer.py | 24 | 2026-03-21 | pass | |
| 29 | FSM (transitions/callbacks/validation) | systems/test_fsm.py | 13 | 2026-03-21 | pass | |
| 30 | Cursor (register/set/visibility) | systems/test_cursor.py | 6 | 2026-03-21 | pass | |
| 31 | Assets (image/sound/music/frames/@2x) | systems/test_assets.py | 17 | 2026-03-21 | pass | |
| 32 | Mock Backend (event injection/tracking) | conftest.py + all | — | 2026-03-21 | pass | |
| 33 | Integration: adversarial reentrancy | integration/test_adversarial.py, kodo_test_scene_lifecycle.py | 18+73 | 2026-03-21 | pass | 7 FakeGame tests pass (F1 fixed); mutations in on_enter/on_exit/on_reveal/update tested |
| 34 | Integration: resource leaks | integration/test_resource_leaks.py | 9 | 2026-03-21 | pass | |
| 35 | Transparent/pause_below semantics | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | 8 tests: opaque hides below, transparent shows both, chain blocking, independence |
| 36 | Scene.game property lifetime | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | 6 tests: set before on_enter, cleared after pop/replace/clear_and_push, kept when pushed over |
| 37 | on_enter exception rollback | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | push/replace/clear_and_push all roll back on on_enter crash |
| 38 | Cleanup ordering (sprites/timers/UI) | kodo_test_scene_lifecycle.py | (in #4) | 2026-03-21 | pass | Sprites+timers cleaned on push-over; UI kept on push-over, cleared on pop |
| 39 | on_exit exception handling | kodo_test_scene_lifecycle.py | 1 | 2026-03-21 | known-issue | F5: on_exit exception leaves scene stuck on stack (confirmed) |
| 40 | Active-action removal | kodo_test_sprite_actions.py | 7 | 2026-03-21 | pass | Remove mid-MoveTo/Sequence/Parallel, self-remove in Do, action tracking cleanup |
| 41 | Orphaned sprites | kodo_test_sprite_actions.py | 3 | 2026-03-21 | pass | No scene owner, survives scene pop, teardown with active actions |
| 42 | Deep action nesting | kodo_test_sprite_actions.py | 18 | 2026-03-21 | pass | 5-deep Seq, 10-wide Par, Repeat(Seq), Seq(Par(Seq)), battle sequence |
| 43 | Action replacement mid-callback | kodo_test_sprite_actions.py | 1 | 2026-03-21 | known-issue | F6: sprite.do() inside Do callback silently drops new action |
| 44 | Animation queue/state transitions | kodo_test_sprite_actions.py | 12 | 2026-03-21 | pass (with bug) | Play, queue, interrupt, stop, PlayAnim action; F7: queue chain 3+ broken |
| 45 | Animation queue chain 3+ | kodo_test_sprite_actions.py | 1 | 2026-03-21 | known-issue | F7: play() clears queue — _drain_queue loses remaining items |

## Example / Tutorial Tests

| Example | Test File | Test Count | Status |
|---------|-----------|-----------|--------|
| Battle Vignette | examples/test_battle_vignette.py | 14 | pass |
| Menu Tutorial | examples/test_menu_tutorial.py | 46 | pass |
| Tower Defense (example) | examples/test_tower_defense_example.py | 4 | pass |
| Tower Defense (tutorial) | examples/test_tower_defense_tutorial.py | 21 | pass |

## Blocked / Not Tested

| Feature | Directory | Reason |
|---------|-----------|--------|
| Visual rendering verification | tests/visual/ | Requires display + pyglet |
| Screenshot golden-image comparison | tests/screenshot/ | Requires display + pyglet |
| AI-powered visual verification | tests/visual_verify/ | Requires Anthropic API key |
| Audio playback (actual output) | — | Mock-only; no audio hardware tests |
| Performance / stress at scale | — | No load tests exist |

## Totals

- **45 feature areas** identified and tested
- **40 fully passing** in baseline
- **1 environment-dependent** (Game.run() with SAGA2D_HEADLESS)
- **3 known-issues** (F5: on_exit stuck, F6: action replacement dropped, F7: queue chain broken)
- **1 area (visual) blocked** by display requirement
- **1404 unit tests** collected, 1401 pass with SAGA2D_HEADLESS=1, 1404 pass without
- **348 kodo regression tests** all pass
- **73 exploratory scene lifecycle tests** all pass (kodo_test_scene_lifecycle.py)
- **81 sprite/action/animation tests** all pass (kodo_test_sprite_actions.py)
