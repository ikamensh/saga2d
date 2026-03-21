# Visual Polish Plan — Battle Vignette

## Analysis of Current State

Looking at the screenshots and code:

- **Grid**: 8×6 tiles at 128px = 1024×768 on 1920×1080 screen → 448px margins each side
- **Sprites**: 128×128 PNG (same as tile size), but the actual drawn character is much smaller than the canvas — lots of transparent padding. This makes units look small on the grid.
- **Tile seams**: Grass gradient goes LIGHT(top) → MID → DARK(bottom). When tiles stack vertically, the dark bottom edge meets the light top edge of the tile below = visible seam. Same for dirt.
- **Side panels**: 408px wide, font sizes 13-24px — small on a 1920×1080 canvas
- **Title screen**: Lots of empty dark space at top and bottom; sprites decorating left/right are tiny

## Plan (5 Steps)

### Step 1: Fix Tile Seams in `assetgen/battle_tiles.py`
Change `make_tile_grass()` and `make_tile_dirt()` gradient stops from one-directional (LIGHT→MID→DARK) to **mirrored** (MID→LIGHT→MID) so top and bottom edges are the same colour, eliminating visible seams when tiles are tiled vertically.

**Grass** — current:
```python
stops=[(0.0, GRASS_LIGHT), (0.4, GRASS_MID), (1.0, GRASS_DARK)]
```
Change to:
```python
stops=[(0.0, GRASS_MID), (0.5, GRASS_LIGHT), (1.0, GRASS_MID)]
```

**Dirt** — current:
```python
stops=[(0.0, DIRT_LIGHT), (0.5, DIRT_MID), (1.0, DIRT_DARK)]
```
Change to:
```python
stops=[(0.0, DIRT_MID), (0.5, DIRT_LIGHT), (1.0, DIRT_MID)]
```

Also apply the same fix to the obstacle tile's grass background gradient.

### Step 2: Scale Up Sprites in `assetgen/battle_sprites.py`
Increase `SIZE` from `(128, 128)` to `(160, 160)` and `_SCALE` from `2` to `2.5`. Update `CX, CY` from `64, 64` to `80, 80`. Update `RING_SIZE` from `(144, 144)` to `(180, 180)`.

This makes the character art 25% larger within the sprite canvas. Sprites will extend slightly beyond their tile (which is common in tactical games — units are larger than cells for visibility).

### Step 3: Update Unit Constants in `examples/battle_vignette/battle_unit.py`
- `SPRITE_SIZE`: 128 → 160
- `HEALTH_BAR_WIDTH`: 96 → 120
- `HEALTH_BAR_HEIGHT`: 10 → 14
- `HEALTH_BAR_Y_OFFSET`: -12 → -18 (push bar up to accommodate taller sprite)

### Step 4: UI Improvements in `examples/battle_vignette/battle_demo.py`

**Side panels:**
- Increase panel title font: 24 → 28
- Increase alive count font: 16 → 20
- Increase stats font: 13 → 16
- Increase turn info font: 18 → 22 (label), 14 → 18 (detail)
- Reduce panel width calculation: `int(GRID_ORIGIN_X - 40)` → `int(GRID_ORIGIN_X - 20)` (slightly wider panels by reducing gap)

**Title screen:**
- Increase main title font: 72 → 96
- Increase subtitle font: 32 → 44
- Increase controls font: 20 → 26
- Increase start prompt font: 28 → 36
- Adjust vertical positions to fill more screen (reduce top margin from 180 → 120, spread elements more evenly)

**Bottom info bar:**
- Increase unit type font: 22 → 26
- Increase HP/stats font: 16 → 20

### Step 5: Verify
1. Regenerate assets: `python3 -m assetgen.battle_tiles` and `python3 -m assetgen.battle_sprites` (or the combined generate command)
2. Render screenshots: `python3 render_vignette_screenshots.py`
3. Run Gemini critique: `python3 critique_vignette.py`
4. Run existing tests: `python3 -m pytest tests/ -x -q` to make sure nothing broke
