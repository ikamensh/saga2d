# Feature Coverage

Tracked across `kodo test` runs. Previous runs: commit 477220f (2026-03-21), Stage 4 fixes (2026-03-22), Fresh re-test (2026-03-23), Stage 1 re-verify (2026-03-23), F29/F30 fixes (2026-03-23), F31-F33 fixes (2026-03-23), F34/F35 fixes (2026-03-25). **Stage 1 tester pass:** 2026-03-25 (see repo `test-report.md`).

## Stage 1 — Window, game loop, scenes (PLAN.md)

**PLAN goal:** running game loop with push/pop scenes, colored backgrounds; backend protocol + `Game` + `Scene`/`SceneStack`.

| Stage 1 area | Implementation (typical) | What exercised it (automated) |
|--------------|--------------------------|------------------------------|
| Backend protocol, frame lifecycle, events | `saga2d/backends/base.py`, `mock_backend.py`, `pyglet_backend.py` | `Game.tick()` paths in `tests/core/test_game.py`; mock backend fixtures (`tests/conftest.py`); pyglet paths exercised when screenshot/visual tests run (display-dependent) |
| `Game` constructor, `tick`, stack delegation, teardown | `saga2d/game.py` | `tests/core/test_game.py` (excluding `game.run()` under headless), `tests/kodo_test_core.py`, headless guard tests in `tests/test_kodo_core_fresh.py` |
| `Scene` / `SceneStack`: push, pop, replace, `clear_and_push`, deferred ops | `saga2d/scene.py` | `tests/core/test_scene.py`, `tests/core/test_scene_*.py`, `tests/integration/test_adversarial.py` (stack re-entrancy and related) |
| Lifecycle hooks (`on_enter` / `on_exit` / `on_reveal`), transparency, `pause_below` | `saga2d/scene.py`, draw/update orchestration in `game.py` | `tests/core/test_scene.py`, `tests/ui/test_ui.py` (transparent stack), `tests/ui/test_hud.py` |
| `game.run()` interactive loop | `saga2d/game.py` | **Skipped** when `SAGA2D_HEADLESS=1` (`tests/core/test_game.py` — 3 tests); manual / display-only |
| Pyglet window + push/pop demo | `PygletBackend`, scenes | `tests/visual/test_stage1_visual.py` — manual or display; not part of default headless CI |
| **E2E smoke: Game→Scene→Sprite→MoveTo** | `saga2d/game.py`, `scene.py`, `rendering/sprite.py`, `actions.py` | **`scripts/smoke_game_move_to.py`** — standalone headless script; creates Game (mock), pushes Scene, adds Sprite, runs MoveTo action via `tick()` loop, asserts target reached. Run: `uv run python scripts/smoke_game_move_to.py`. See `test-report.md` for full details. |

**Commands (Stage 1 tester, 2026-03-25):**

- Smoke script: `uv run python scripts/smoke_game_move_to.py` → `PASS — smoke: Game, Scene, Sprite, MoveTo`
- Full pytest (headless): `SAGA2D_HEADLESS=1 uv run python -m pytest tests/ --ignore=tests/visual_verify -q` → **2631 passed, 3 skipped** (~34s)
- Full pytest (all): `SAGA2D_HEADLESS=1 uv run python -m pytest tests/ -q` → **2665** collected, **2649 passed, 11 failed, 5 skipped** — failures are AI/screenshot checks in `visual_verify`, not Stage 1 mock regressions.

## Current Run — Deep Edge Case Testing (2026-03-25)

### Baseline (re-measured 2026-03-25 — tester agent)
- **2665** tests collected; **2649 passed**, **11 failed** (`tests/visual_verify/*`), **5 skipped** with `SAGA2D_HEADLESS=1` (~45s full `tests/`)
- **2631 passed**, **3 skipped** if `tests/visual_verify/` is ignored (matches “automated mock + screenshot” focus)
- Older note **“2,522 passing, 1 visual failing”** is **stale** relative to this checkout

### NEW Gaps to Test This Run

| Feature / Workflow | Last tested | Status | Findings |
|--------------------|-------------|--------|----------|
| ParticleEmitter speed/direction NaN/Inf | 2026-03-25 | pending | No validation on speed/direction tuples |
| Do() non-callable fn parameter | 2026-03-25 | pending | No callable validation |
| Repeat() times negative/float/NaN | 2026-03-25 | pending | No validation in __init__ |
| MoveTo bad position tuple (1-tuple, scalar) | 2026-03-25 | pending | No length validation |
| Game.tick(dt=NaN) propagation to scene | 2026-03-25 | pending | dt not validated at Game level |
| ProgressBar value=NaN setter | 2026-03-25 | pending | No setter validation |
| DataTable negative row_height | 2026-03-25 | pending | Wrong row index calculation |
| Grid zero cell_size | 2026-03-25 | pending | Layout calculations fail |
| Scene.add_sprite(None) | 2026-03-25 | pending | No None guard |
| Game invalid resolution | 2026-03-25 | pending | Negative/zero accepted |
| ColorSwap empty color lists | 2026-03-25 | pending | Silent no-op |
| DragDrop callback exceptions | 2026-03-25 | pending | May corrupt drag state |
| Game after teardown method calls | 2026-03-25 | pending | Methods still callable |
| Parallel.update() on unstarted children | 2026-03-25 | pending | No start() guarantee |

### Previously Passing Features

| Feature / Workflow | Last tested | Status | Findings |
|--------------------|-------------|--------|----------|
| Game initialization (mock backend) | 2026-03-25 | pass | — |
| Game initialization (invalid backend) | 2026-03-25 | pass | ValueError raised correctly |
| Game.tick() basic cycle | 2026-03-25 | pass | — |
| Scene push/pop/replace/clear_and_push | 2026-03-25 | pass | — |
| Scene lifecycle hooks | 2026-03-25 | pass | — |
| Scene timer ownership | 2026-03-25 | pass | — |
| Actions: Sequence/Parallel/Delay/MoveTo/FadeIn/Out | 2026-03-25 | pass | F15/F16/F24 fixed |
| Camera follow/scroll/pan/shake | 2026-03-25 | pass | F31-33 fixed |
| Sprites creation/positioning/removal | 2026-03-25 | pass | — |
| Animation play/queue/stop/loop | 2026-03-25 | pass | F21-23 fixed |
| ParticleEmitter burst/continuous | 2026-03-25 | pass | F34 fixed |
| UI: All core widgets | 2026-03-25 | pass | — |
| Tween system | 2026-03-25 | pass | F21 fixed |
| Timer after/every/then | 2026-03-25 | pass | F22-23 fixed |
| FSM transitions | 2026-03-25 | pass | F18 fixed |
| Audio channels/crossfade | 2026-03-25 | pass | F35 fixed |
| SaveManager | 2026-03-25 | pass | F19 fixed |
| InputManager | 2026-03-25 | pass | — |
| Theme/Style/Layout | 2026-03-25 | pass | — |
| HUD visibility | 2026-03-25 | pass | — |

### Blocked Workflows
| Workflow | Reason |
|----------|--------|
| Pyglet backend rendering | Requires display server (X11/Wayland) |
| Screenshot golden-image comparison | Requires pyglet + display |
| AI visual verification | Requires ANTHROPIC_API_KEY |
| Interactive game examples | Requires windowed display |
| Audio hardware playback | Requires audio hardware |
| game.run() loop | Blocked by SAGA2D_HEADLESS=1 |
