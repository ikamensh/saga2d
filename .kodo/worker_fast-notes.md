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

- Exploratory suite: `tests/kodo_test_scene_lifecycle.py` (73 tests). With core scene tests: `pytest tests/core/test_scene.py tests/kodo_test_scene_lifecycle.py`.
- Ordering harness: `python -m tests.harness.lifecycle_tester -v` (do not `pytest tests/harness/lifecycle_tester.py` — not pytest tests).
- **F5 (known issue, not fixed):** if `on_exit` raises, `SceneStack.pop()` does not remove the scene — stack unchanged. Covered by `test_on_exit_exception_leaves_scene_on_stack`.
