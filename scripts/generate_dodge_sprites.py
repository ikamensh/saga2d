"""Generate the ``dodge`` example's sprite assets procedurally.

Same approach as iter-33's :mod:`generate_sprites`: no external
downloads, no licensing, everything reproducible from a short
PIL script.

Run::

    python scripts/generate_dodge_sprites.py

Produces:

*   ``assets/images/dodge_ship.png`` — 48×48 triangular player ship.
*   ``assets/images/dodge_rock.png`` — 36×36 greyscale asteroid.

Both have soft edges via alpha so they don't read as pixel-harsh
sprites against the example's dark background.
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

from PIL import Image, ImageDraw


def generate_ship(out: Path) -> None:
    size = 48
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Triangular hull, pointing up. Silver-blue with a thin bright
    # outline so it reads as a player sprite, not a decorative triangle.
    hull = [
        (size // 2, 4),              # top
        (4, size - 6),                # bottom-left
        (size - 4, size - 6),         # bottom-right
    ]
    draw.polygon(hull, fill=(160, 200, 255, 255))

    # Engine glow — a soft circle at the back of the ship.
    cx = size // 2
    cy = size - 8
    draw.ellipse([(cx - 10, cy - 5), (cx + 10, cy + 5)], fill=(255, 180, 80, 200))
    draw.ellipse([(cx - 6, cy - 3), (cx + 6, cy + 3)], fill=(255, 240, 160, 255))

    # Cockpit — small dark oval in the middle.
    cy_cockpit = size // 2 + 2
    draw.ellipse(
        [(cx - 4, cy_cockpit - 6), (cx + 4, cy_cockpit + 6)],
        fill=(40, 50, 80, 255),
    )

    # Outline — one-pixel bright rim around the hull for contrast.
    draw.polygon(hull, outline=(230, 240, 255, 255))

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)


def generate_rock(out: Path, seed: int = 42) -> None:
    size = 36
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    rng = random.Random(seed)

    cx = cy = size // 2
    r = 15

    # Main rocky disc — slightly irregular polygon around a circle
    # gives it an asteroid feel without being obviously-a-circle.
    n_points = 9
    import math
    points = []
    for i in range(n_points):
        angle = i * 2 * math.pi / n_points
        rr = r + rng.uniform(-2.5, 2.5)
        points.append((cx + rr * math.cos(angle), cy + rr * math.sin(angle)))
    draw.polygon(points, fill=(110, 100, 95, 255))

    # A few darker pits to give texture.
    for _ in range(4):
        px = cx + rng.randint(-7, 7)
        py = cy + rng.randint(-7, 7)
        pr = rng.randint(2, 4)
        draw.ellipse([(px - pr, py - pr), (px + pr, py + pr)],
                     fill=(75, 68, 65, 255))

    # Highlight — one brighter edge for directional lighting.
    highlight = [
        (cx - 10, cy - 8),
        (cx - 4, cy - 12),
        (cx + 2, cy - 10),
    ]
    draw.polygon(highlight, fill=(150, 140, 135, 200))

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)


def generate_particle_spark(
    out: Path,
    rgb: tuple[int, int, int],
    *,
    size: int = 16,
) -> None:
    """Soft disc particle — used as the emit sprite for explosions and
    the ship's thruster trail. ParticleEmitter accepts a list of asset
    names and picks one per particle, so generating three variants
    (yellow, orange, dim-red for explosion; one grey for the thruster)
    gives a natural colour variation without a shader.

    iter-45 default size is 16 px; iter-45 initial try at 8 px was too
    faint to read at an 800-tall canvas (visible only under zoom).
    """
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = size / 2
    # Three-pass soft disc. Radii scale with size so the glow looks
    # right at any requested dimension.
    r, g, b = rgb
    outer_r = size * 0.45
    mid_r = size * 0.30
    core_r = size * 0.18
    draw.ellipse([(cx - outer_r, cy - outer_r), (cx + outer_r, cy + outer_r)],
                 fill=(r, g, b, 60))
    draw.ellipse([(cx - mid_r, cy - mid_r), (cx + mid_r, cy + mid_r)],
                 fill=(r, g, b, 180))
    draw.ellipse([(cx - core_r, cy - core_r), (cx + core_r, cy + core_r)],
                 fill=(r, g, b, 255))
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)


def generate(root: Path) -> None:
    images_dir = root / "assets" / "images"
    generate_ship(images_dir / "dodge_ship.png")
    generate_rock(images_dir / "dodge_rock.png")
    # iter-45 additions: three 16-px explosion spark variants + one
    # 8-px dust for the ship thruster trail (dust stays small so it
    # reads as exhaust rather than competing with the explosion).
    generate_particle_spark(images_dir / "dodge_spark_yellow.png",
                            (255, 230, 90), size=16)
    generate_particle_spark(images_dir / "dodge_spark_orange.png",
                            (255, 150, 60), size=16)
    generate_particle_spark(images_dir / "dodge_spark_red.png",
                            (230, 70, 60), size=16)
    generate_particle_spark(images_dir / "dodge_dust.png",
                            (200, 210, 230), size=8)
    print(f"Wrote dodge sprites under {images_dir}")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    generate(root)
