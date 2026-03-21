# Worker Fast Notes — Saga2D

## Project structure (repo root)

```
saga2d/                  # Python package (public API in __init__.py)
│   ├── backends/        # Internal: base, mock, pyglet
│   ├── rendering/      # Camera, Sprite, layers, particles, color_swap
│   ├── ui/              # Components, layout, theme, screens, widgets
│   └── util/            # fsm, timer, tween
examples/                # battle_vignette, tower_defense, menugame
tutorials/               # menus, tower_defense (ch1–ch6)
assetgen/                # Asset generation (battle_tiles, sprites)
tests/                   # pytest, screenshot harness, visual_verify
desired_examples/        # API design sketches
```

## Public API (import from `saga2d`)

**Core:** `Game`, `Scene`, `RenderLayer`, `SpriteAnchor`, `AssetManager`, `Sprite`  
**Actions:** `Action`, `Delay`, `Do`, `FadeIn`, `FadeOut`, `MoveTo`, `Parallel`, `PlayAnim`, `Remove`, `Repeat`, `Sequence`  
**UI:** `Panel`, `Label`, `Button`, `Anchor`, `Layout`, `Style`, `Theme`, `HUD`, `ProgressBar`, `DataTable`, `Grid`, `List`, `TextBox`, `Tooltip`, `TabGroup`, `ImageBox`, `ChoiceScreen`, `ConfirmDialog`, `MessageScreen`, `SaveLoadScreen`, `DragManager`, `Component`  
**Rendering:** `Camera`, `ColorSwap`, `ParticleEmitter`, `get_palette`, `register_palette`  
**Other:** `AnimationDef`, `AudioManager`, `CursorManager`, `InputManager`, `SaveManager`, `StateMachine`, `TimerHandle`, `Ease`, `tween`, `compute_anchor_position`, `compute_content_size`, `compute_flow_layout`  
**Events:** `Event`, `KeyEvent`, `MouseEvent`, `WindowEvent`

## Constraints (AGENTS.md / CLAUDE.md)

- **Never** launch GUI windows (`game.run()`, pyglet.app.run()) — use `backend="mock"` or screenshot harness
- Visual changes require render-and-look: `render_scene()` → save PNG → inspect
- Pyglet event handlers must `return True` to prevent fallthrough (e.g. ESC closing window)
- Screenshot capture: between `batch.draw()` and `window.flip()` (double-buffering)

## Baseline (477220f, 2026-03-21)

- Main suite (ignore `visual_verify`, `visual`, `screenshot`): **1404** collected — **`SAGA2D_HEADLESS=1`** → **3** fails in `tests/core/test_game.py` (`game.run()` headless guard); **unset** → **1404** pass.
- FakeGame + cursor: `hasattr(scene.game, "cursor")` in `saga2d/scene.py` (~526) — no cursor regression; adversarial + kodo FakeGame tests pass.

## Scene lifecycle (kodo Stage 2, 2026-03-21)

- Exploratory suite: `tests/kodo_test_scene_lifecycle.py` (75 tests). With core scene tests: `pytest tests/core/test_scene.py tests/kodo_test_scene_lifecycle.py`.
- Ordering harness: `python -m tests.harness.lifecycle_tester -v` (do not `pytest tests/harness/lifecycle_tester.py` — not pytest tests).
- **F5 (fixed 2026-03-22):** `on_exit` exceptions no longer leave scenes stuck — `try/finally` in `_apply_pop` / `_apply_replace`; `clear_and_push` runs cleanup per scene and re-raises first error after stack clear. Tests: `test_on_exit_exception_pops_scene`, `..._during_replace_...`, `..._during_clear_and_push_...`.

## Sprites, actions, animations (kodo Stage 3–4, 2026-03-21–22)

- Exploratory suite: `tests/kodo_test_sprite_actions.py` (81 tests, mock backend). Same coverage as Stage 3 notes; **F6/F7 fixed 2026-03-22**.
- **F6:** `update_action()` only clears `_current_action` if it is still the same object after `action.update(dt)` — preserves `sprite.do()` from inside `Do` callbacks. Test: `test_do_replaces_action_during_sequence_f6`.
- **F7:** `play(..., _from_drain=True)` skips `_anim_queue.clear()` when `_drain_queue` chains queued anims. Test: `test_queue_chain_three_f7`.
- Action stress harness: `python -m tests.harness.action_stress_tester` (not a pytest module).

## UI / Stage 4 coverage (2026-03-22)

- No global focus manager — keyboard handling is widget-local; overlap/layout exercised via `tests/ui/` and tutorials; 0 new UI findings reported for this pass.

## Persistence & resources (kodo Stage 5, 2026-03-22)

- Suites: `tests/kodo_test_persistence_resources.py`, `tests/kodo_test_persistence_resources_ext.py` (malformed saves, version/envelope edge cases, stacked save/load, emitters, camera pan, `on_exit` resources, rapid deferred transitions).
- **F8:** Binary/invalid UTF-8 in slot files — `read_text` could raise `UnicodeDecodeError`; `SaveManager.load` now maps it to `SaveError` like other corruption.
- **F9:** Valid JSON that is not an object (`[]`, string, etc.) — previously crashed `list_slots` / `SaveLoadScreen` with `TypeError`; `load()` now requires `isinstance(data, dict)` and raises `SaveError` with a clear message.
