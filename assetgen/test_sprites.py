"""
Generate the 12 test sprite PNGs consumed by visual tests.

Output directory: ``<project_root>/assets/images/sprites/``

Consumers:
    - ``tests/visual/test_stage2_visual.py`` (tree, knight, enemy, crate)
    - ``tests/visual/test_stage3_visual.py`` (knight_walk, knight_attack frames)
    - ``tests/visual/test_stage45_visual.py`` (knight, crate, enemy + animations)

Each ``make_*`` function returns a ``PIL.Image.Image`` (RGBA) so callers can
inspect or compose them without touching the filesystem.  ``generate(output_dir)``
saves all 12 PNGs and returns the list of written paths.

Filenames, sizes, and colours match the architecture spec exactly.
"""

from __future__ import annotations

from pathlib import Path
from typing import List

from PIL import Image, ImageDraw

from assetgen.primitives import (
    circle,
    crosshatch,
    labeled_rect,
    solid_rect,
    triangle,
    vertical_gradient,
)
from assetgen.wireframe import (
    cube,
    render_wireframe,
    rotate_x,
    rotate_y,
)

# ---------------------------------------------------------------------------
# Colour constants (RGBA)
# ---------------------------------------------------------------------------
FOREST_GREEN  = (34, 139, 34, 255)
DODGER_BLUE   = (30, 144, 255, 255)
CRIMSON       = (220, 20, 60, 255)
SADDLE_BROWN  = (139, 90, 43, 255)

# Tree foliage gradient (lighter at top, darker at base)
TREE_GREEN_TOP    = (80, 180, 80, 255)
TREE_GREEN_BASE   = (25, 100, 25, 255)
TREE_TRUNK_BROWN  = (101, 67, 33, 255)

# Knight walk frame colours (per-frame tint variation)
KNIGHT_WALK_COLORS = [
    (30, 144, 255, 255),   # frame 01
    (50, 164, 255, 255),   # frame 02
    (30, 144, 255, 255),   # frame 03
    (10, 124, 235, 255),   # frame 04
]

# Knight attack frame colours
KNIGHT_ATTACK_COLORS = [
    (20, 80, 180, 255),    # frame 01
    (40, 100, 200, 255),   # frame 02
    (20, 80, 180, 255),    # frame 03
]


# ---------------------------------------------------------------------------
# Individual sprite generators — each returns a Pillow Image
# ---------------------------------------------------------------------------

def make_tree() -> Image.Image:
    """64x96 tree: layered foliage triangles with gradient, brown trunk.

    Foliage: 3 overlapping triangles (wider toward bottom) with vertical
    gradient (lighter green at top, darker at base). Brown rectangle trunk
    at bottom. Optional wireframe overlay for texture.
    """
    w, h = 64, 96
    trunk_height = 18
    foliage_top, foliage_base = 0, h - trunk_height

    # Foliage layers (back to front): each (apex, base_left, base_right)
    layers = [
        ((w // 2, foliage_top + 8), (12, foliage_base), (52, foliage_base)),
        ((w // 2, foliage_top + 4), (8, foliage_base + 2), (56, foliage_base + 2)),
        ((w // 2, foliage_top), (2, foliage_base + 4), (62, foliage_base + 4)),
    ]

    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    grad_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    mask_layer = Image.new("L", (w, h), 0)
    draw_mask = ImageDraw.Draw(mask_layer)

    for points in layers:
        vertical_gradient(grad_layer, TREE_GREEN_TOP, TREE_GREEN_BASE)
        draw_mask.rectangle((0, 0, w, h), fill=0)
        draw_mask.polygon([tuple(p) for p in points], fill=255)
        img = Image.composite(grad_layer, img, mask_layer)

    # Trunk
    trunk_y0 = h - trunk_height
    trunk_x0 = (w - 14) // 2
    draw = ImageDraw.Draw(img, "RGBA")
    draw.rectangle((trunk_x0, trunk_y0, trunk_x0 + 14, h - 1), fill=TREE_TRUNK_BROWN)

    # Wireframe overlay
    verts, edges = cube()
    rotated = [rotate_y(rotate_x(v, 0.6), 0.8) for v in verts]
    render_wireframe(
        img, rotated, edges,
        color=(24, 100, 24, 80),
        width=1,
        center=(32.0, 40.0),
        scale=14.0,
    )
    return img


def make_knight() -> Image.Image:
    """48x64 dodger-blue filled rectangle."""
    return solid_rect(48, 64, DODGER_BLUE)


def make_enemy() -> Image.Image:
    """48x48 crimson filled ellipse."""
    return circle(48, CRIMSON)


def make_crate() -> Image.Image:
    """32x32 saddle-brown filled rectangle with pseudo-3D bevel.

    Lighter strip along top/left edges, darker along bottom/right for
    beveled 3D appearance. Overlays cross-hatching and wireframe cube.
    """
    img = solid_rect(32, 32, SADDLE_BROWN)
    draw = ImageDraw.Draw(img, "RGBA")
    strip = 2
    lighten, darken = 45, -35
    r, g, b, a = SADDLE_BROWN
    light = (min(255, r + lighten), min(255, g + lighten), min(255, b + lighten), a)
    dark = (max(0, r + darken), max(0, g + darken), max(0, b + darken), a)
    for i in range(strip):
        # Top edge
        draw.line([(i, i), (31 - i, i)], fill=light, width=1)
        # Left edge
        draw.line([(i, i), (i, 31 - i)], fill=light, width=1)
        # Bottom edge
        draw.line([(i, 31 - i), (31 - i, 31 - i)], fill=dark, width=1)
        # Right edge
        draw.line([(31 - i, i), (31 - i, 31 - i)], fill=dark, width=1)
    crosshatch(img, spacing=5, color=(90, 55, 20, 100), width=1)
    verts, edges = cube()
    rotated = [rotate_y(rotate_x(v, 0.5), 0.7) for v in verts]
    render_wireframe(
        img, rotated, edges,
        color=(90, 55, 20, 120),
        width=1,
        center=(16.0, 16.0),
        scale=10.0,
    )
    return img


def make_knight_walk_frame(frame_number: int) -> Image.Image:
    """48x64 labelled rectangle for knight walk animation.

    Args:
        frame_number: 1-based frame index (1..4).

    Returns:
        RGBA Image with the frame number as centred label.
    """
    color = KNIGHT_WALK_COLORS[frame_number - 1]
    return labeled_rect(48, 64, color, str(frame_number))


def make_background() -> Image.Image:
    """256x224 ground plane: brown at top to dark gray at bottom.

    Earth/ground perspective gradient for use as a background sprite.
    """
    w, h = 256, 224
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    vertical_gradient(img, (139, 90, 43, 255), (60, 55, 50, 255))
    return img


def make_knight_attack_frame(frame_number: int) -> Image.Image:
    """48x64 labelled rectangle for knight attack animation.

    Args:
        frame_number: 1-based frame index (1..3).

    Returns:
        RGBA Image with the frame number as centred label.
    """
    color = KNIGHT_ATTACK_COLORS[frame_number - 1]
    return labeled_rect(48, 64, color, str(frame_number))


# ---------------------------------------------------------------------------
# Batch generator
# ---------------------------------------------------------------------------

# Complete manifest: (filename, factory_callable)
MANIFEST: list[tuple[str, callable]] = [
    ("background.png",       make_background),
    ("tree.png",             make_tree),
    ("knight.png",           make_knight),
    ("enemy.png",            make_enemy),
    ("crate.png",            make_crate),
    ("knight_walk_01.png",   lambda: make_knight_walk_frame(1)),
    ("knight_walk_02.png",   lambda: make_knight_walk_frame(2)),
    ("knight_walk_03.png",   lambda: make_knight_walk_frame(3)),
    ("knight_walk_04.png",   lambda: make_knight_walk_frame(4)),
    ("knight_attack_01.png", lambda: make_knight_attack_frame(1)),
    ("knight_attack_02.png", lambda: make_knight_attack_frame(2)),
    ("knight_attack_03.png", lambda: make_knight_attack_frame(3)),
]


def generate(output_dir: Path | None = None) -> List[Path]:
    """Generate all 12 test sprite PNGs and save them to *output_dir*.

    Args:
        output_dir: Target directory.  Defaults to
                    ``<project_root>/assets/images/sprites/``.

    Returns:
        List of ``Path`` objects for every file written.
    """
    if output_dir is None:
        project_root = Path(__file__).resolve().parents[1]
        output_dir = project_root / "assets" / "images" / "sprites"

    output_dir.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []
    for filename, factory in MANIFEST:
        img = factory()
        path = output_dir / filename
        img.save(path)
        print(f"Created {path}")
        written.append(path)

    return written
