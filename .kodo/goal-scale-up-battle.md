# Goal: Scale Up Battle Demo — Fill the Screen

## The Problem

The battle demo renders an 8x6 grid of 64px tiles (512x384 pixels) centered on a 1920x1080 screen. The grid occupies only ~25% of the screen area, with massive dead olive-green space around it. The sprites are 64x64 and hard to appreciate at that size. The overall impression is "tiny game lost in empty space."

Screenshot reference: The grid is a small rectangle in the center, warriors and skeletons are thumbnail-sized, and 75% of the screen is wasted background.

## Objective

Make the battle fill the screen by scaling up all visual elements 2x. The grid should dominate the viewport, units should be large and readable, and the background should be atmospheric instead of flat.

## Requirements

### 1. Double All Asset Sizes (assetgen/)

Update the asset generation pipeline to produce **128x128** tiles and sprites instead of 64x64.

- `assetgen/battle_tiles.py`: Change all tile generation to 128x128. The tiles already use supersampling (4x render then downsample), so this should be straightforward — change the target size from 64 to 128. Update the health bar assets proportionally too.
- `assetgen/battle_sprites.py`: Change all sprite generation to 128x128. Same approach — the rendering pipeline already uses supersampling. Update all frame sizes from 64 to 128.
- `assetgen/battle_tiles.py` also has `tile_sheet_preview.png` — update that to reflect 128px tiles.
- Run `python generate_assets.py` after changes to regenerate all assets.

### 2. Update Game Constants

In `examples/battle_vignette/`:

- `battle_grid.py`: Change `TILE_SIZE` from 64 to 128
- `battle_unit.py`: Change `SPRITE_SIZE` from 64 to 128. Scale health bar dimensions proportionally (width 48→96, height 6→10, offset -8→-12). Scale floating number font size from 24 to 36.
- `battle_demo.py`: Grid origin calculation should auto-adjust since it uses `(SCREEN_W - GRID_COLS * TILE_SIZE) / 2`, which will center the larger grid. No change needed there. But verify the turn label and hint label positioning still works (margin values might need adjustment since the grid is now larger and closer to the top).

### 3. Atmospheric Background

Replace the flat olive background `(50, 60, 40, 255)` in BattleScene with something more atmospheric:

- Use a dark gradient background — darker at edges, slightly lighter near center. Something like deep forest green `(20, 30, 15)` to `(35, 50, 25)`.
- OR generate a background tile pattern that extends beyond the grid (dark earth/grass texture).
- The key requirement: the area around the grid should NOT be flat solid color. It should have depth/atmosphere.

One approach: add a full-screen background sprite (a 1920x1080 procedurally generated image) to the BACKGROUND layer. Generate it in assetgen/ as `battle_bg.png`.

### 4. Grid Border / Frame

Add a visible border or frame around the tactical grid to separate it from the background. Options:
- Draw a 2-4px border rectangle around the grid area
- Or add corner decoration sprites
- Keep it subtle — functional, not distracting

### 5. UI Positioning Check

With the grid now ~1024x768 (centered), verify:
- Turn label at top isn't clipped and has enough room above the grid
- Hint label is readable
- End Turn button doesn't overlap the grid
- Game over panel still centers correctly

### 6. End Turn Button Repositioning

Move the End Turn button from BOTTOM_RIGHT (which is far from the action) to just below the grid, right-aligned. This keeps it accessible but near the gameplay.

## Technical Constraints

- Do NOT modify saga2d/ framework code — only modify examples/ and assetgen/
- All existing tests must pass: `uv run python -m pytest tests/ -v`
- After regenerating assets, verify the demo can still be imported: `python -c "from examples.battle_vignette.battle_demo import BattleScene; print('OK')"`
- The demo must still run: `python examples/battle_vignette/battle_demo.py`

## Acceptance Criteria

1. `python generate_assets.py` produces all assets without errors
2. All tile PNGs in `examples/battle_vignette/assets/images/tiles/` are 128x128
3. All sprite PNGs in `examples/battle_vignette/assets/images/sprites/` are 128x128
4. `TILE_SIZE` in battle_grid.py is 128
5. `SPRITE_SIZE` in battle_unit.py is 128
6. `uv run python -m pytest tests/ -v` passes
7. `python -c "from examples.battle_vignette.battle_demo import BattleScene; print('OK')"` works
8. The background is not a flat solid color
