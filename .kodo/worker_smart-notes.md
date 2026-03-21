# Worker Smart Notes

## Project
- Location: `/Users/ikamen/soft/fun/easy_game`
- Use `python3` not `python`
- Current commit: `6b74177`
- Test stories: 14/41 pass, 2 fail (US22, US28), 25 untested
- Run tests: `python3 -m pytest --ignore=tests/visual_verify -x -q`
- tests/visual_verify requires display (fails in headless with pyglet EGL/cocoa errors)
- `render_vignette_screenshots.py` DOES work (uses pyglet visible=False, not EGL)

## Battle Sprites (assetgen/battle_sprites.py)
- Authored coordinate space: 64×64 units
- `_SS=4` (supersampling), `_SCALE=7.5` (content scale)
- `_s(v)` = `v * _SS * _SCALE` = `v * 30`
- `SIZE = (480, 480)`, **`CX, CY = 32, 32`** (authored-space center, NOT output center)
- **CRITICAL**: CX/CY must be authored-space center (32 for 64-unit space), NOT SIZE/2. Using SIZE/2 draws everything off-canvas!
- `RING_SIZE = (540, 540)`, `_RING_BBOX_1X = (24, 96, 402, 330)` (output-space coords, scaled by _SS only)
- Post-process expand=8, offset=(4,4), blur_radius=5.0
- `_valid_bbox()` guard needed for off-canvas scatter in death animation
- Warrior arms: two-segment with elbow joint (`elbow_bend=_s(4)`)
- Skeleton limbs: two-segment with knee/elbow joint (`joint_bend=_s(3)`)
- `SPRITE_SIZE` in `examples/battle_vignette/battle_unit.py` = 480
- Health bar: WIDTH=280, HEIGHT=24, Y_OFFSET=-36
- `_large` variants (960x960 = 2× base) generated in `generate_assets.py`

## Battle Tiles (assetgen/battle_tiles.py)
- TILE_SIZE = (128, 128), `_SS=4`, `_SCALE=2`
- Obstacle rock: SMALL pebble — `rock_rx=_s(12)`, `rock_ry=_s(10)` (units must dominate)
- battle_bg.png: 1920×1080 dark Slate-900 with radial vignette + noise

## Battle Demo Layout
- GRID_ORIGIN_Y = centered + 70 (prevents row-1 sprite clipping with 480px sprites)
- Grid: 10 cols × 6 rows, TILE_SIZE=128, on 1920×1080
- Side panel pip layout: pip_pad=30, pip_gap=6, centered group, clamped fill_w, adaptive font (12/14px)

## Screenshot Capture in Headless
- Need `DISPLAY=:0` env var for pyglet to work in headless environment
- `DISPLAY=:0 python3 -c "..."` for inline screenshot capture

## Gemini Visual Verification
- **CRITICAL PROMPT DESIGN**: Gemini is susceptible to anchoring bias from negative defect descriptions
- Must use two-step prompt: (1) analyze screenshot independently, (2) evaluate if defect still exists
- Simple "Is this defect FIXED?" prompts get biased by the defect's negative language
- `verify_screenshot_gemini.py` uses STEP 1 (observe) → STEP 2 (evaluate) pattern
- Needs GOOGLE_API_KEY env var, `-v` flag for detailed output
- maxOutputTokens=400 (needs room for observation + verdict)

## Battle Vignette Visual Polish
- Grid highlight colors: HIGHLIGHT_MOVE = Sky-400 (56,189,248,80), HIGHLIGHT_ATTACK = Rose-500 (244,63,94,80)
- Idle bobbing: 3px amplitude, 2 Hz, paused during sprite actions
- **Critical**: idle bob must skip when `sprite._current_action is not None`
- BattleScene.background_color = Slate-900 (15,23,42,255)

## Theme (saga2d/ui/theme.py)
- Tailwind CSS Slate/Sky palette (dark theme)
- Panel shadow: offset=4, color=(0,0,0,120)
- Button hover outline: color=(100,181,246,200), width=3

## Test Color Assertions
- When changing Theme defaults, update assertions in:
  - tests/ui/test_theme.py, tests/ui/test_ui.py, tests/ui/test_widgets.py

## Tower Defense (examples/tower_defense/)
- SCREEN_W, SCREEN_H = 1280, 960 (was 960×540, changed for viewport fill)
- TILE_SIZE = 64, `_SS=4`, `_SCALE=2`
- MANIFEST: 29 images + 6 audio = 35 total files
- `python3 examples/tower_defense/generate_assets.py` regenerates 35 TD files
- Title screen decorations use SCREEN_W/SCREEN_H-relative positioning
- Test fixture resolution: (1280, 960), click at (640, 530) for Play button

## Asset Generation
- `python3 generate_assets.py` regenerates all 63 files (61 battle + 2 large)
- Output dirs: assets/images/sprites/, examples/battle_vignette/assets/images/{sprites,tiles}/
