# Tester Notes - Saga2D

## Persistence / save-load / resources (verified 2026-03-22)

- **Environment:** `.venv` present; `backend="mock"`, `game.tick()` + `_teardown()` only (no `game.run()`).
- **Imports:** `from saga2d import Game, Scene, SaveManager, SaveError` — OK.
- **Suites run (all PASS):**
  - `pytest tests/kodo_test_persistence_resources.py tests/integration/test_resource_leaks.py -v` → **70** passed
  - `pytest tests/systems/test_save.py -v` → **48** passed
  - `pytest tests/ui/test_screens.py -k "SaveLoad or save_mgr" -v` → **9** passed (SaveLoadScreen)
  - `pytest tests/integration/test_adversarial.py::TestSaveSystemEdgeCases -v` → **10** passed
  - `python -m tests.harness.systems_util_harness J -v` → Scenario **J** PASS
- **F9 non-object JSON (verified 2026-03-22):** `SaveManager.load()` rejects top-level JSON that is not an object (`list`, `str`, `null`, number, bool) with **`SaveError`** (message includes slot path and type). `list_slots()` propagates that `SaveError` (no `TypeError`). **`SaveLoadScreen`:** `on_enter` calls `list_slots` uncaught → pushing the screen with a bad `save_1.json` raises **`SaveError`** at push time (screen does not mount); not an in-UI corruption banner. Regression: `pytest tests/kodo_test_persistence_resources_ext.py::TestMalformedSaveFiles -v` (10 passed).
- **Other manual checks:** Truncated/invalid JSON → `SaveError` with slot hint. JSON object **without** `"state"` → `Game.load` returns data, does **not** call `load_save_state` (documented).

## Stage 1 baseline (verified 2026-03-21)

- **Commit** `477220f` — matches external run `~/.kodo/runs/20260321_213413/test-report.md`.
- **Main suite** (ignores `visual_verify`, `visual`, `screenshot`): **1404** collected; **`SAGA2D_HEADLESS=1`** → **3 failed** (`tests/core/test_game.py` — all `game.run()` blocked by headless guard); **`env -u SAGA2D_HEADLESS`** → **1404 passed**. Failures are **only** those three when headless is set.
- **FakeGame / cursor**: `hasattr(scene.game, "cursor")` guard at `saga2d/scene.py` ~526 — **no** FakeGame-related failures. Adversarial 7-test subset and `kodo_test_core -k "FakeGame or cursor"` (5 tests) pass.
- **Kodo regression**: `kodo_test_{core,rendering,systems}.py` — **348 passed**.
- **Timing**: full run ~33s here vs ~29s in report — normal machine variance.
- **Doc nit**: live `RuntimeError` from `game.run()` includes an extra sentence (use `tick` / screenshot harness); report truncates the message.

## E2E: core engine + scene stack (2026-03-21)

**Scope:** Mock backend only (`backend="mock"`), `game.tick(dt)` — no `game.run()` (headless-safe). **Note:** Saga2D has **no `on_hide` hook**; coverage is `on_enter` / `on_exit` / `on_reveal` only.

### Commands run (all PASS)

```bash
cd /Users/ikamen/ai-workspace/experiments/by_kodo/saga2d

# Broad: lifecycle hooks, transparency draw chain, pause_below, deferred ops,
# empty stack, replace/clear edge cases, hook-time stack mutation
.venv/bin/python -m pytest tests/core/test_scene.py tests/integration/test_adversarial.py -v --tb=no
# → 130 passed (36 + 94)

# Lifecycle harness (push/pop/replace/clear_and_push ordering + deferred flush)
.venv/bin/python -m tests.harness.lifecycle_tester -v
# → US4, US10, US11, US12, US13 — 5/5

# Fuzz: invalid Game args + scene stack edge ops (pop/replace empty, etc.)
.venv/bin/python -m tests.harness.fuzz_harness
# → exit 0; stderr may show Game.__del__ teardown noise on partially-built Game instances

# Focused: clear_and_push resource cleanup, empty stack, FakeGame cursor
.venv/bin/python -m pytest tests/core/test_scene.py tests/core/test_scene_timers.py -k clear_and_push \
  tests/core/test_scene_sprites.py -k clear_and_push tests/integration/test_resource_leaks.py \
  tests/ui/test_hud.py -k "clear_and_push or empty_stack" \
  tests/kodo_test_core.py::TestSceneStackBasic tests/kodo_test_core.py::TestFakeGameCursorBug -v --tb=no
# → 16 passed (subset via -k)

# Transparent overlay + HUD ordering + tick-based game tests (excludes game.run())
.venv/bin/python -m pytest tests/ui/test_ui.py::TestSceneIntegration::test_ui_for_transparent_scene_stack \
  tests/ui/test_hud.py::TestHUDDrawOrder::test_hud_draws_before_overlay \
  tests/ui/test_hud.py::TestHUDDrawOrder::test_hud_hidden_by_overlay_show_hud_false \
  tests/ui/test_hud.py::TestHUDDrawOrder::test_hud_visible_with_show_hud_true_overlay \
  tests/core/test_game.py -k "not run and not window_close" -v --tb=no
# → 6 passed

# One-liner smoke (editable package from .venv)
.venv/bin/python -c "from saga2d import Game, Scene; g=Game('e2e', backend='mock'); g.push(Scene()); g.tick(0.016); g._teardown(); print('OK')"
```

### Coverage map (what the suite proves)

| Area | Where |
|------|--------|
| Hook order (push/pop/replace/clear) | `tests/core/test_scene.py`, `lifecycle_tester.py` |
| `on_reveal` after pop | `test_pop_calls_on_exit_and_on_reveal`, US4/US10/US11 |
| Deferred stack ops during `update` | `test_deferred_*`, US11 |
| Hooks mutating stack (`on_enter`/`on_exit`) | `test_push_during_on_enter_*`, `test_pop_during_on_exit_*`, `test_push_during_on_exit_*`, adversarial tests |
| Empty stack | `test_*empty*`, `TestSceneStackBasic`, fuzz harness |
| Transparency + draw chain | `test_draw_transparent_*`, `test_background_color_uses_base_scene_when_transparent_overlay` |
| `pause_below=False` updates below | `test_pause_below_false_updates_scenes_below` |
| `clear_and_push` teardown | on_exit all cleared scenes; timers/sprites tests; resource leak test |
| Re-entrancy / adversarial | `tests/integration/test_adversarial.py` (18 tests) |

### Sprite / Action / Animation (verified 2026-03-21)

- **pytest:** `tests/rendering/test_sprite.py` + `tests/actions/test_actions.py` + `tests/rendering/test_animation.py` → **209 passed**; `tests/integration/test_adversarial.py::TestSpriteLifecycleAdversarial` → **3 passed**; `tests/kodo_test_rendering.py` → **127 passed**.
- **Harness:** `python -m tests.harness.action_stress_tester` → **8/8** (US6–US9, US22–US23, NoHang, NaN). **Known behavior:** US22 documents `Parallel(only infinite children)` finishing in one tick (vacuous `all_finite_done`).
- **Manual:** Sprite never `scene.add_sprite` (`_owning_scene is None`) still runs `do(Sequence(MoveTo, Do))` + nested `Parallel(Sequence(Delay, Do), Do)` + layer order `BACKGROUND < EFFECTS` — all OK with explicit `game._teardown()`.

### F5 — `on_exit` exception (re-verified)

- **Exploratory file:** `tests/kodo_test_scene_lifecycle.py` (73 tests) — includes `TestComplexReentrancy::test_on_exit_exception_leaves_scene_on_stack` documenting F5.
- **Repro still valid:** `SceneStack.pop()` after `on_exit` raises → **`len(_stack) == 1`**, scene remains top (manual repro + that test both confirm).
- **Do not** `pytest tests/harness/lifecycle_tester.py` — those are script functions, not pytest tests; use `python -m tests.harness.lifecycle_tester`.

## Last Session: Harness & User Story Coverage (2026-03-18)

### Harness Verification — All Run Successfully Except One
- **Consumer**: PASS — imports 63 symbols, Game(mock), tick(0.016), _teardown()
- **Install**: PASS — pip install -e . in clean venv, import+Game+tick
- **Fuzz**: PASS — edge cases (Game args, scene ops, action params)
- **Integration**: PASS — A/B/C (Button→Scene push, action completion, camera)
- **UI (D–I)**: PASS — Theme, ChoiceScreen/ConfirmDialog, drag-drop, HUD, ParticleEmitter/ColorSwap, Camera
- **Systems (J–Q)**: PASS — Save, StateMachine, Cursor, Audio, Timer/tween, Input, Teardown, show_sequence
- **Bug Repro (R–Y)**: Scenario T FAIL — `scene.game` is None during _cleanup_exiting_scene (cursor.set)
- **Final Verification (AA–AE)**: PASS

### Consumer Harness vs US3
- US3: "Create a Game with mock backend, **push a Scene**, tick frames"
- Consumer harness does **not** push a Scene — it only Game(mock) + tick. Integration Scenario A covers push+pop.

### User Story → Harness Mapping
- Harnesses cover scenarios; many user stories remain **untested** (31/35) because harnesses exercise code paths but test-stories.md status is not auto-updated from harness runs.
- See test-stories.md Notes column for which harness/scenario maps to each story.

---

## Previous: Battle Unit Visibility Verification (2026-03-13)

### Battle Unit Visual Prominence - VERIFIED ✓ (Updated: 480px sprites)
- **Sprite sizes**: 480×480 pixels (both warriors and skeletons)
- **Tile size**: 128×128 pixels
- **Obstacle size**: 24×20 pixel pebbles (intentionally small)
- **Result**: Units fill ~3.75x their grid cell area, **massively** prominent
- **Screenshot**: `baseline_battle.png` (3840×2160 HiDPI)
- **Visual**: Blue warriors and red/white skeletons dominate the grid; gray rocks are tiny pebbles
- **Row-1 clipping check**: ✓ Top row units fully visible with health bars, 182px top margin
- **Gemini verification**: ✅ **FIXED** using exact acceptance criteria description

### Gemini Vision API - Acceptance Criteria PASSED
- **Test**: `verify_screenshot_gemini.py` with defect-first phrasing (original format)
- **Description**: "Units are nearly invisible on the battle grid. The warrior and skeleton sprites are tiny colored specks on the green grass. The gray rock obstacles are far more prominent than the actual playable units. Units should be the most visually prominent elements on the grid."
- **Result**: ✅ **FIXED** (after prompt engineering improvement)
- **Reasoning**: "The units are no longer tiny specks. They are large enough to be easily seen and are more prominent than the obstacles. The reported defect condition no longer exists."

### Gemini Prompt Engineering Fix
- **Issue**: Original prompt treated description as requirement to match
- **Solution**: Updated prompt with 2-step process:
  1. Analyze screenshot independently (unit size, prominence, obstacles)
  2. Evaluate whether REPORTED DEFECT still exists
- **Key insight**: Frame description as "reported defect" to check if it's FIXED, not as requirement to match
- **Token limit**: Increased from 200 to 400 to allow detailed reasoning

### Environment
- macOS with display (pyglet screenshot capture works)
- Use `capture_battle_screenshot.py` for pyglet screenshots
- Screenshot harness available at `tests/screenshot/harness.py`

## Previous Session: UI Polish Verification (2026-03-11)

### Environment
- Headless SSH environment (no display)
- Use `scripts/repro_menu.py --simulate` for PIL-based screenshots
- Screenshot harness available at `tests/screenshot/harness.py`

### UI Requirements Verified
1. **Label text clipping** - Fixed via `anchor_y="top"` in Label.on_draw() (line 223)
2. **Panel shadow** - Implemented in Panel.on_draw() (lines 605-615), offset=4px
3. **Button borders** - Clear borders via theme border_width=2, color Slate 600
4. **Hover outline** - Blue glow (100,181,246,200) on hovered buttons (lines 389-402)
5. **Color palette** - Slate/Sky Material Design colors in theme.py (lines 66-95)

### Key Patterns
- **Screenshot generation**: Use `--simulate` flag for headless PIL rendering
- **Hover state verification**: Check `repro_menu_final.png` (Load Game button hovered)
- **Text positioning**: Labels use `anchor_y="top"`, Buttons use `anchor_y="center"`
- **Panel shadows**: 4px offset, color (0,0,0,120)
- **Button hover**: Background color + 3px outline glow, -2px offset

### Files
- `scripts/repro_menu.py` - Menu screenshot generator
- `repro_menu_final.png` - Screenshot with hover state
- `VERIFICATION_COMPLETE.md` - Full verification document

## Display Environment Test (2026-03-11)

### Pyglet Headless Test Result
**Status**: ✗ NO DISPLAY AVAILABLE (True Headless)

**Environment**: SSH session, no macOS display server access
**Pyglet version**: 2.1.13
**Error**: `IndexError: list index out of range` when trying to get screens

### Implications
- Cannot create pyglet windows (even with `visible=False`)
- Cannot use OpenGL contexts for rendering
- Screenshot harness (`render_scene`) requires display
- Must use alternative methods:
  - PIL-based simulation (like `scripts/repro_menu.py --simulate`)
  - Pre-generated golden screenshots
  - Mock backend validation

### Working Methods
✅ PIL simulation scripts (repro_menu.py --simulate, ui_gallery.py)
✅ Pre-captured screenshots in tests/visual_verify/output/
✅ Mock backend tests (tests/screenshot/test_*.py with @pytest.mark.screenshot)
✅ Code inspection and validation

### Not Available
✗ Live pyglet screenshot capture
✗ Screenshot harness (tests/screenshot/harness.py render_scene)
✗ Real-time GPU rendering tests
