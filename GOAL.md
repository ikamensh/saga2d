# GOAL — Visual Verification and Demo Polish

## Why This Comes Before Continuing PLAN.md Stages 6-13

Stages 0-5 were built and verified entirely through mock backend assertions and
manual "eyeball" visual test scripts that were never actually eyeballed.  Result:
219 tests pass, but the demo is colored rectangles on a black void.  The mock
backend proves data flow correctness but cannot prove rendering works.

Without visual verification tooling, implementing stages 6-13 produces more of the
same: AI writes code, mock tests pass, nobody knows if it actually looks right.
The screenshot pipeline pays for itself immediately — every subsequent stage gets
real visual validation for free.

**Order: Goal 1 → Goal 2 → Goal 3 → then resume PLAN.md Stage 6+.**

---

## Goal 1 — Screenshot Testing Pipeline

**Objective:** Automated pytest tests that render real frames through the pyglet
backend, capture screenshots, and compare against golden reference images.

### 1.1 Backend: `capture_frame()` Method

Add to the Backend protocol and both implementations:

```python
# base.py — add to Protocol
def capture_frame(self) -> bytes:
    """Read back the current framebuffer as raw RGBA pixel data.
    Returns bytes of length width * height * 4.
    Must be called after end_frame() (or between begin_frame/end_frame)."""
    ...
```

**PygletBackend implementation:**
```python
def capture_frame(self) -> bytes:
    from pyglet.image import get_buffer_manager
    color_buffer = get_buffer_manager().get_color_buffer()
    image_data = color_buffer.get_image_data()
    return image_data.get_data("RGBA", image_data.width * 4)
```

**MockBackend implementation:**
```python
def capture_frame(self) -> bytes:
    # Return a blank frame — mock doesn't render, but satisfies the protocol
    return b'\x00' * (self.logical_width * self.logical_height * 4)
```

### 1.2 Hidden Window Support

Modify `PygletBackend.create_window()` to accept a `visible` parameter:

```python
def create_window(self, width, height, title, fullscreen, *, visible=True):
    self.window = pyglet.window.Window(
        width=width, height=height, caption=title,
        fullscreen=fullscreen if visible else False,
        vsync=False,  # no vsync needed for testing
        visible=visible,
    )
```

Update `Game.__init__` to pass through a `visible` flag (default True).  Tests
create the game with `visible=False`.

On macOS, `visible=False` creates a hidden window with a valid OpenGL context.
On Linux CI with EGL, we can later add `pyglet.options['headless'] = True` before
window creation.

### 1.3 Test Harness: `ScreenshotTestCase`

Create `tests/screenshot/harness.py`:

```python
"""Screenshot test harness — render real frames, compare to golden images."""

from pathlib import Path
from PIL import Image
import io

from easygame import Game

GOLDEN_DIR = Path(__file__).parent / "golden"
OUTPUT_DIR = Path(__file__).parent / "output"

def render_scene(scene, *, frames=1, dt=1/60, resolution=(800, 600)):
    """Create a real pyglet game, tick N frames, return captured PIL Image."""
    game = Game(
        "Screenshot Test",
        backend="pyglet",
        resolution=resolution,
        fullscreen=False,
        visible=False,
    )
    game.push(scene)

    for _ in range(frames):
        game.tick(dt=dt)

    raw = game.backend.capture_frame()
    w, h = resolution

    # Pyglet returns bottom-up RGBA; flip vertically for top-down
    img = Image.frombytes("RGBA", (w, h), raw)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)

    game.quit()
    return img

def assert_screenshot(img, name, *, threshold=0.99):
    """Compare image against golden reference.

    If golden doesn't exist, save it and pass (first run creates goldens).
    threshold: fraction of pixels that must match (0.99 = 99% match).
    """
    GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    golden_path = GOLDEN_DIR / f"{name}.png"
    output_path = OUTPUT_DIR / f"{name}.png"
    diff_path = OUTPUT_DIR / f"{name}_diff.png"

    img.save(output_path)

    if not golden_path.exists():
        img.save(golden_path)
        return  # First run — golden created, test passes

    golden = Image.open(golden_path)
    if golden.size != img.size:
        raise AssertionError(
            f"Size mismatch: golden {golden.size} vs actual {img.size}"
        )

    # Per-pixel comparison with tolerance
    import numpy as np
    a = np.array(img, dtype=np.int16)
    b = np.array(golden, dtype=np.int16)
    diff = np.abs(a - b)
    # A pixel matches if ALL channels are within tolerance (±5 per channel)
    pixel_match = np.all(diff <= 5, axis=2)
    match_ratio = pixel_match.sum() / pixel_match.size

    if match_ratio < threshold:
        # Save a visual diff for debugging
        diff_img = Image.fromarray(
            (diff[:, :, :3] * 10).clip(0, 255).astype(np.uint8)
        )
        diff_img.save(diff_path)
        raise AssertionError(
            f"Screenshot '{name}': {match_ratio:.1%} pixel match "
            f"(threshold {threshold:.1%}). Diff saved to {diff_path}"
        )
```

### 1.4 First Screenshot Tests

Create `tests/screenshot/test_rendering.py` with basic tests that exercise
the existing Stage 1-5 features through real rendering:

```python
"""Screenshot tests for Stages 1-5 features."""

from easygame import Scene, Sprite, RenderLayer, AnimationDef
from .harness import render_scene, assert_screenshot

class StaticSpritesScene(Scene):
    """Several sprites at known positions — tests layer ordering + placement."""
    def on_enter(self):
        Sprite("sprites/tree", position=(200, 300), layer=RenderLayer.OBJECTS)
        Sprite("sprites/knight", position=(400, 350), layer=RenderLayer.UNITS)
        Sprite("sprites/enemy", position=(600, 300), layer=RenderLayer.UNITS)

def test_static_sprites():
    img = render_scene(StaticSpritesScene(), frames=2)
    assert_screenshot(img, "static_sprites")

class AnimatedSpriteScene(Scene):
    """Sprite mid-animation — tests that frame cycling changes the image."""
    def on_enter(self):
        walk = AnimationDef(frames="sprites/knight_walk", frame_duration=0.15, loop=True)
        self.knight = Sprite("sprites/knight_walk_01", position=(400, 300))
        self.knight.play(walk)

def test_animated_sprite_frame3():
    # After ~0.5s at 60fps (30 frames), animation should have cycled
    img = render_scene(AnimatedSpriteScene(), frames=30, dt=1/60)
    assert_screenshot(img, "animated_sprite_frame30")

class TweenedSpriteScene(Scene):
    """Sprite mid-tween — tests position interpolation."""
    def on_enter(self):
        from easygame import tween, Ease
        self.box = Sprite("sprites/crate", position=(100, 300))
        tween(self.box, "x", 100, 700, duration=2.0, ease=Ease.LINEAR)

def test_tweened_sprite_at_1s():
    # At 1.0s into a 2.0s linear tween from 100→700, x should be ~400
    img = render_scene(TweenedSpriteScene(), frames=60, dt=1/60)
    assert_screenshot(img, "tweened_sprite_1s")
```

### 1.5 pytest Integration

- Screenshot tests go in `tests/screenshot/` directory
- They are **not excluded** from pytest (unlike the old `tests/visual/`)
- Mark with `@pytest.mark.screenshot` so they can be run selectively:
  `pytest -m screenshot` or skipped: `pytest -m "not screenshot"`
- Add `conftest.py` in `tests/screenshot/` that skips if pyglet unavailable:
  ```python
  import pytest
  try:
      import pyglet
  except ImportError:
      pytest.skip("pyglet not installed", allow_module_level=True)
  ```

### 1.6 Golden Image Management

- `tests/screenshot/golden/` — committed to git, serves as reference
- `tests/screenshot/output/` — gitignored, holds latest captures + diffs
- To update goldens after intentional visual changes: delete the golden file
  and re-run the test (first run without golden auto-creates it)
- Diff images are saved with 10x amplified differences for easy debugging

### 1.7 Validation

**Done when:**
- `pytest tests/screenshot/ -v` passes on macOS with no visible window
- At least 3 golden images exist covering: static sprites, animated sprite,
  tweened sprite
- A deliberately broken test (move a sprite 50px) fails with a clear diff image
- Mock backend tests still pass unchanged (`pytest tests/ -m "not screenshot"`)

---

## Goal 2 — Appealing Geometric Art Assets

**Objective:** Replace flat colored rectangles with procedurally generated
geometric art that looks visually interesting and makes animation frames
distinguishable.

### 2.1 Design Principles

Current placeholder art fails because:
- All frames look nearly identical (blue rect with "W1" vs "W2")
- No visual motion cues between animation frames
- Shapes don't suggest what they represent

New procedural art should:
- Use **geometry** — polygons, circles, arcs, rotation, scaling
- Make animation frames **visually distinct** from each other
- Suggest the entity type through shape language (sharp = aggressive, round = passive)
- Use **color palettes** not single flat colors
- Include **transparency and gradients** where Pillow supports them

### 2.2 Asset Generator: `generate_assets.py` (project root)

Rewrite the existing generator scripts.  One unified script at project root that
generates assets for both `assets/images/sprites/` (used by tests) and
`examples/battle_vignette/assets/images/sprites/` (used by demo).

**Entity designs using geometry:**

**Knight / Warrior (player units):**
- Shield shape: rounded pentagon body, lighter inner area
- Idle: single static frame, small "breathing" pulsing would be in animation
- Walk frames (4): shield shape shifts left-right with a small bounce, feet
  indicators (chevrons or triangles below) alternate position
- Attack frames (3): shield lunges forward, a sharp triangular "blade" extends
  from the right side, progressively longer across frames

**Skeleton / Enemy:**
- Diamond or angular shape body (sharp = hostile)
- Skull-like circle on top with dark eye-dots
- Walk frames (4): body tilts alternately, small floating animation (hover)
- Hit frames (3): body compresses/flashes white, fragments offset
- Death frames (3): body breaks apart — pieces scatter outward, opacity decreases

**Tree:**
- Triangle top (dark green) on a brown rectangle trunk
- Add a subtle gradient: darker green at base of foliage, lighter at top
- Maybe 2-3 triangle layers for depth

**Crate:**
- Brown square with cross-hatch lines (two diagonal lines)
- Slight 3D effect: lighter top-left edge, darker bottom-right edge

**Select ring:**
- Keep the current yellow ellipse — it works fine

**Background elements (new):**
- Simple ground plane: a gradient rectangle from brown to dark gray
- Could be used as a scene background to replace the black void

### 2.3 Polyhedron Idea: 3D Wireframe Rotation

The user specifically asked about rotating tetrahedra.  This is feasible with
Pillow + basic 3D math:

```python
import math
from PIL import Image, ImageDraw

def project_3d(x, y, z, angle_y, angle_x, scale=30, cx=32, cy=32):
    """Rotate point around Y then X axis, project to 2D."""
    # Rotate around Y
    cos_y, sin_y = math.cos(angle_y), math.sin(angle_y)
    x2 = x * cos_y - z * sin_y
    z2 = x * sin_y + z * cos_y
    # Rotate around X
    cos_x, sin_x = math.cos(angle_x), math.sin(angle_x)
    y2 = y * cos_x - z2 * sin_x
    z3 = y * sin_x + z2 * cos_x
    # Project
    return (cx + x2 * scale, cy + y2 * scale)

def draw_tetrahedron(size, angle_y, angle_x=0.3):
    """Draw a wireframe tetrahedron at a given rotation."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Tetrahedron vertices (unit)
    verts = [(1,1,1), (1,-1,-1), (-1,1,-1), (-1,-1,1)]
    projected = [project_3d(*v, angle_y, angle_x, scale=size//4, cx=size//2, cy=size//2) for v in verts]
    edges = [(0,1),(0,2),(0,3),(1,2),(1,3),(2,3)]
    for i, j in edges:
        draw.line([projected[i], projected[j]], fill=(100, 200, 255, 200), width=2)
    return img
```

Use this for:
- **Idle animation**: slowly rotating polyhedron (8-12 frames at different angles)
- **Attack animation**: polyhedron spins fast + grows then shrinks
- **Death animation**: polyhedron dissolves (fewer edges drawn per frame, fading)
- **Different unit types**: tetrahedron for warrior, octahedron for enemy,
  cube for crate

This creates animation frames that are **obviously different** from each other
while being entirely procedural.  Can be mixed with the 2D shape approach — e.g.,
a shield body with a rotating tetrahedron as a "power gem" on it.

### 2.4 Validation

**Done when:**
- `python generate_assets.py` produces all needed PNGs for both test and demo
- Visually examining the PNGs shows distinguishable animation frames
- Knight walk frames show obvious motion between frames
- Knight attack frames show progressive extension/strike
- Skeleton death frames show obvious decomposition
- Screenshot tests with new assets produce golden images that a human reviewer
  can identify as "knight," "enemy," "tree" without reading labels

---

## Goal 3 — Demo of Already-Built Features

**Objective:** Rewrite `examples/battle_vignette/battle_demo.py` to fully
showcase Stages 1-5 using the new geometric art, making it look like an actual
game prototype rather than a test harness.

### 3.1 What to Demonstrate

Everything already implemented in Stages 1-5, exercised visually:

| Feature | How to showcase |
|---------|----------------|
| **Scene stack** (Stage 1) | Title scene → push Battle scene → ESC to pop back |
| **Sprites + layers** (Stage 2) | Background on BACKGROUND layer, trees on OBJECTS, units on UNITS, effects on EFFECTS |
| **Y-sorting** (Stage 2) | Units at different Y positions render in correct depth order |
| **Animation** (Stage 3) | Idle breathing loops, walk cycles, attack animations, death sequences |
| **Timers** (Stage 4) | Timed spawn of damage numbers, periodic idle fidgets |
| **Tweening** (Stage 4) | Smooth movement, fade in/out, possibly scaling effects |
| **Input mapping** (Stage 5) | Click to select, click to attack, ESC to go back |

### 3.2 Title Scene (NEW — demonstrates scene stack)

A simple title scene that the current demo lacks:

```
┌─────────────────────────────────────┐
│                                     │
│         ◆ BATTLE VIGNETTE ◆         │
│                                     │
│   [rendered as sprites/geometry,    │
│    not UI components since those    │
│    aren't built yet]                │
│                                     │
│      Press ENTER to start           │
│      Press ESC to quit              │
│                                     │
│   Rotating tetrahedron decoration   │
│                                     │
└─────────────────────────────────────┘
```

Since the UI system (Stage 8) doesn't exist, the title "screen" uses:
- Sprites for decorative elements (rotating geometric shapes)
- `backend.draw_text()` for the title and instructions (raw text rendering)
- Animation and tweening for visual flair (pulsing, floating)

Pressing ENTER does `game.push(BattleScene())`.  Pressing ESC does `game.quit()`.
Pressing ESC from BattleScene does `game.pop()` — returning to title.

### 3.3 Battle Scene Improvements

Keep the existing click-to-select + click-to-attack gameplay, but:

1. **Background**: A gradient ground plane sprite instead of black void
2. **Formation**: Warriors on the left, skeletons on the right, in a proper
   formation (2-3 per side), with slight Y-offset staggering for depth
3. **Idle animations**: All units play idle animation loops (not static single
   frames) — use the rotating polyhedron or breathing/pulsing geometry
4. **Selection**: Clearer visual feedback — selection ring pulses (tween opacity)
5. **Attack choreography**: Same callback chain, but with better art it will
   look like something is actually happening
6. **Damage numbers**: Float upward and fade out (this already works)
7. **Victory/defeat**: When all enemies die, briefly show "VICTORY" text
   (using draw_text + a tween to fade it in), then pop back to title

### 3.4 Screenshot Coverage for Demo

Add screenshot tests that capture key moments of the demo:

```python
def test_demo_title_screen():
    img = render_scene(TitleScene(), frames=1)
    assert_screenshot(img, "demo_title")

def test_demo_battle_formation():
    img = render_scene(BattleScene(), frames=5)
    assert_screenshot(img, "demo_battle_formation")

def test_demo_attack_in_progress():
    # Inject click events to trigger an attack, tick to mid-choreography
    scene, img = render_scene_with_input(...)
    assert_screenshot(img, "demo_attack_midway")
```

### 3.5 Validation

**Done when:**
- `python -m examples.battle_vignette.battle_demo` shows a title screen with
  animated geometric decorations
- ENTER transitions to a battle scene with visible formation, background,
  and animated idle loops on all units
- Clicking a warrior selects it (visual feedback), clicking a skeleton attacks
- The attack choreography is visually clear: walk, strike, hit reaction, death
- ESC from battle returns to title (scene stack pop)
- All existing 219+ mock tests still pass
- Screenshot tests capture all key visual states and golden images look
  recognizably game-like

---

## After Goals 1-3: Resume PLAN.md

With the screenshot pipeline in place and appealing art assets, continue with
PLAN.md stages:

- **Stage 6 (Camera)** — screenshot tests verify scrolling, edge-scroll, clamping
- **Stage 7 (Audio)** — audio can't be screenshot-tested, but mock tests cover it
- **Stage 8 (UI)** — screenshot tests verify button rendering, panel layout, theme
- **Stage 10 (Actions)** — rewrite battle demo with composable actions, screenshot
  tests confirm identical visual output to the callback version

The visual verification tooling makes every subsequent stage cheaper to validate
correctly.

---

## Notes for the Implementing AI

- **Read DESIGN.md and BACKEND.md** before writing code — they are the source of
  truth for API design.
- **Read RETROSPECTIVE.md** — it documents friction points and bugs already found.
- **Do not change the public API** of existing Stage 1-5 code unless necessary
  for these goals (e.g., adding `visible` parameter to Game constructor).
- **Run `pytest tests/ -v` after every change** — the 219 existing tests must
  continue to pass.
- **Pillow is already a dependency** (used by existing generate_assets.py scripts
  and color swap system in DESIGN.md). numpy will be needed for image comparison.
- **macOS note**: `Window(visible=False)` works for offscreen rendering.  Do not
  attempt `pyglet.options['headless'] = True` on macOS — it only works on
  Linux with EGL.
- **Coordinate flip**: pyglet renders bottom-up (OpenGL), framework uses top-down.
  The `capture_frame()` output must be flipped vertically before comparison.
