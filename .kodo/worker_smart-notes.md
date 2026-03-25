# Worker Smart Notes — Saga2D

## Project
- 2D game framework (Python 3.12+, pyglet backend, mock backend for headless testing)
- Repo: `/Users/ikamen/ai-workspace/experiments/by_kodo/saga2d`
- Run tests: `SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify --ignore=tests/visual --ignore=tests/screenshot -q`
- Smoke test: `uv run python scripts/smoke_game_move_to.py` (no env vars needed)

## Key Architecture
- `saga2d/` — core package: Game, Scene, Sprite, actions, audio, UI components, util (tween, timer, fsm)
- `saga2d/rendering/` — camera.py, sprite.py, particles.py, animation.py, layers.py
- `saga2d/ui/` — component.py (base Component + _UIRoot), components.py (Label/Button/Panel), widgets.py (List/Grid/DataTable/etc), layout.py, theme.py
- `saga2d/backends/` — mock_backend.py (headless), pyglet_backend.py
- `tests/` — 2631+ tests (headless), organized by area (actions/, core/, rendering/, systems/, ui/, integration/, kodo_test_*.py, test_kodo_*.py)

## Test Counts (2026-03-25)
- 2631 passed, 3 skipped (game.run() under SAGA2D_HEADLESS), 0 failures (excluding visual_verify)
- Full tree: 2665 collected, 2649 passed, 11 failed (AI visual_verify only), 5 skipped
- ~34s runtime (headless)

## Stage 1 Status — COMPLETE (2026-03-25)
- Scope: Environment Setup & Smoke Testing — game loop, push/pop scenes, backend protocol, Game + Scene/SceneStack
- Smoke script `scripts/smoke_game_move_to.py` validates Game→Scene→Sprite→MoveTo E2E
- Documented in: `test-report.md` (how to run, what it validates), `.kodo/test-coverage.md` (Stage 1 table row + commands), `.kodo/run-status.md` (marked COMPLETE)

## Changes Made (2026-03-25 — Stage 1 completion)
- `test-report.md`: Added § "Smoke script" with how-to-run, validation table, usage guidance; added smoke command to commands-run list; updated Stage 1 UX paragraph to reference smoke script
- `.kodo/test-coverage.md`: Added E2E smoke row to Stage 1 table; restructured Commands section with smoke + pytest commands
- `.kodo/run-status.md`: Rewrote with current test counts (2631), marked Stage 1 COMPLETE, added smoke/pytest verification lines
- `.kodo/worker_smart-notes.md`: Updated test counts, added Stage 1 status, recorded changes

## Bugs Fixed (F-numbered)
- F1-F10, F12, F15-F16, F18-F19, F21-F33 (29 total)
- F29: Camera.scroll() NaN/Inf guard (camera.py)
- F30: Component tree iteration snapshot safety (component.py) — draw/update/handle_event all use list() snapshot now
- F31: Camera.shake() NaN/Inf guard on intensity, duration, decay (camera.py)
- F32: Camera.update() NaN/Inf dt early-return guard (camera.py)
- F33: Camera.follow() NaN target position guard — skips frame, preserves last valid position (camera.py)

## Key Patterns
- NaN/Inf: All public APIs validate with `math.isfinite()` (actions, tween, timer, camera, particles, widgets)
- Camera: all input paths now guarded — center_on, scroll, pan_to, shake (params), update (dt), follow (target pos)
- Iteration safety: TweenManager, TimerManager, Component draw/update/handle_event all use `list()` snapshots
- Sprite.position setter validates finite values — prevents silent NaN corruption
- MockBackend for all headless tests; `_current_game` module-level singleton pattern
- Assets: `Sprite('sprites/knight')` resolves to `assets/images/sprites/knight.png`

## Gotchas
- `Game.__del__` prints ImportError during Python shutdown (known F11, cosmetic)
- `Sprite` requires real asset file even with mock backend
- `SaveManager` requires `Path` not `str`
- `reversed()` on a live list does NOT protect against mutation — must use `list()` first
- Python 3.13: `min(1.0, nan)` → 1.0; `max(0.0, nan)` → 0.0 (IEEE 754 quirk)
- IEEE 754: `NaN <= 0` is False AND `NaN > 0` is False — both branches of if/else can be skipped!
- Camera.follow() NaN: without the guard, `_clamp()` with world_bounds gave platform-dependent results
