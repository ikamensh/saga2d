# Asset Generation (assetgen/)

Procedural asset generation for Saga2D using Pillow (PIL).

All sprites are generated as **RGBA PNG files** with 4× supersampling for smooth anti-aliased edges, matching the visual quality of hand-drawn assets while remaining version-controllable as code.

## Modules

### `primitives.py`
Core drawing primitives and effects:

**Shapes:**
- `filled_polygon()`, `outlined_polygon()`
- `filled_ellipse()`, `outlined_ellipse()`

**Gradients:** (numpy-accelerated)
- `linear_gradient()` — multi-stop, arbitrary angle
- `radial_gradient()` — multi-stop, from center point

**Effects:**
- `apply_blur()` — Gaussian blur
- `apply_drop_shadow()` — soft shadow with offset
- `apply_glow()` — rim lighting effect
- `apply_noise()` — organic texture grain

**Color Utilities:**
- `lighten()`, `darken()`, `adjust_alpha()`

**Supersampling:**
- `supersample_draw()` — render at 4× → LANCZOS downsample

### `wireframe.py`
3D wireframe rendering for sprites (gem overlays, etc.):

**Platonic Solids:**
- `tetrahedron()`, `octahedron()`, `cube()`

**Transforms:**
- `rotate_x()`, `rotate_y()`, `rotate_z()`

**Projection:**
- `project_perspective()`, `project_orthographic()`
- `render_wireframe()` — draw edges onto Pillow image

### `battle_sprites.py`
Complete battle demo sprite set (20 files):

**Warriors (8):**
- `warrior_idle_01.png` (64×64)
- `warrior_walk_{01..04}.png` (64×64, 4-frame cycle)
- `warrior_attack_{01..03}.png` (64×64, 3-frame attack with motion trails)

**Skeletons (12):**
- `skeleton_idle_01.png` (64×64)
- `skeleton_walk_{01..04}.png` (64×64, 4-frame cycle)
- `skeleton_hit_{01..03}.png` (64×64, flash → recoil → recover)
- `skeleton_death_{01..03}.png` (64×64, crumbling/dissolve effect)

**UI:**
- `select_ring.png` (72×72, golden magical ring)

**Features:**
- Metallic armor gradients (warriors)
- Glowing gems with rotating octahedron wireframes
- Bone texture with glowing red eyes (skeletons)
- Motion blur trails on attack frames
- Death animations with scatter/fade/noise

### `battle_tiles.py` ✨ NEW
Terrain tiles and UI elements for tactical battles (7 files):

**Terrain (64×64):**
- `tile_grass.png` — textured green grass with blade tufts
- `tile_dirt.png` — brown earth with pebbles and cracks
- `tile_stone.png` — grey cobblestone with mortar lines

**Tactical Overlays (64×64, semi-transparent):**
- `tile_move.png` — blue radial gradient with corner accents
- `tile_attack.png` — red radial gradient with crosshair

**Health Bars (40×6):**
- `health_bar_bg.png` — dark background with border
- `health_bar_fill.png` — green gradient with glossy highlight

All tiles use the same 4× supersampling + noise workflow as battle sprites for visual consistency.

### `test_sprites.py`
Simple colored rectangles for framework validation (12 files):
- red/green/blue (32×32)
- small/large variants (16×16, 64×64)
- labeled boxes for debugging

## Usage

### Generate All Assets
From project root:
```bash
python generate_assets.py
```

Generates:
- 12 test sprites → `assets/images/sprites/`
- 20 battle sprites → `assets/images/sprites/` + `examples/battle_vignette/assets/images/sprites/`
- 7 battle tiles → `examples/battle_vignette/assets/images/tiles/`

Total: **59 files**

### Generate Specific Modules
```bash
# Battle sprites only
python -m assetgen.battle_sprites

# Battle tiles only
python -m assetgen.battle_tiles

# Test sprites only
python -m assetgen.test_sprites
```

### Use in Game Code
```python
from saga2d import Game, AssetManager, Sprite

game = Game("My Game", resolution=(1920, 1080))
game.assets = AssetManager(game.backend, base_path="examples/battle_vignette/assets")

# Load a sprite
warrior = Sprite("sprites/warrior_idle_01", position=(100, 200))

# Load a tile
grass = Sprite("tiles/tile_grass", position=(0, 0))
```

## Design Patterns

### 1. Supersampling (4× render → downsample)
```python
def make_my_sprite() -> Image.Image:
    def paint(big: Image.Image) -> None:
        # All coords scaled by _s() for 4× rendering
        filled_ellipse(big, (_s(10), _s(10), _s(54), _s(54)), fill=COLOR)

    sprite = supersample_draw(64, 64, paint, factor=4)
    return sprite
```

### 2. Multi-Stop Gradients
```python
linear_gradient(
    img,
    stops=[
        (0.0, LIGHT_COLOR),
        (0.5, MID_COLOR),
        (1.0, DARK_COLOR),
    ],
    start=(0.0, 0.0),  # top
    end=(0.0, 1.0),    # bottom
)
```

### 3. Noise for Texture
```python
sprite = apply_noise(sprite, amount=0.08, monochrome=True, seed=100)
```

### 4. Post-Processing Pipeline
```python
# Rim glow
sprite = apply_glow(sprite, radius=1.2, glow_color=ACCENT, intensity=0.25)

# Drop shadow
sprite = apply_drop_shadow(sprite, offset=(2, 2), blur_radius=2.5)
```

## Adding New Assets

1. **Create generator function:**
   ```python
   def make_my_tile() -> Image.Image:
       def paint(big: Image.Image) -> None:
           # Draw at 4× scale
           linear_gradient(big, stops=[...], ...)
           filled_polygon(big, points, fill=color)

       sprite = supersample_draw(64, 64, paint, factor=4)
       sprite = apply_noise(sprite, amount=0.1, seed=300)
       return sprite
   ```

2. **Add to `generate()` function:**
   ```python
   def generate(output_dir: Path) -> List[Path]:
       output_dir.mkdir(parents=True, exist_ok=True)
       written: List[Path] = []

       def _save(img: Image.Image, name: str) -> None:
           path = output_dir / name
           img.save(path)
           print(f"Created {path}")
           written.append(path)

       _save(make_my_tile(), "my_tile.png")
       return written
   ```

3. **Update `generate_assets.py`** to include your module

## Benefits vs. Hand-Drawn Assets

✅ **Version controlled** — asset changes tracked in git diffs
✅ **Parameterized** — easy to adjust colors, sizes, gradients
✅ **Consistent style** — same rendering pipeline across all assets
✅ **No external tools** — pure Python + Pillow
✅ **Reproducible** — deterministic generation (seeded RNG)
✅ **Fast iteration** — regenerate all assets in seconds

## Dependencies

- **Pillow** (PIL) — image manipulation
- **NumPy** — gradient acceleration
- Python 3.10+ (for type hints)

All dependencies already required by Saga2D framework.
