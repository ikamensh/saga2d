"""Generate Ring of Pain's sprite assets procedurally via PIL.

Same editorial approach as ``scripts/generate_sfx.py`` (iter-32): no
external downloads, no licensing attribution, no hand-painted art.
The repo's own images, reproducible from this script.

Run once from the project root::

    python scripts/generate_sprites.py

Produces ``assets/images/player_token.png`` — a 64×64 gold disc used
as Ring of Pain's "YOU ARE HERE" marker (replacing the primitive
``draw_circle`` triplet that predated the sprite subsystem).

PIL is already a transitive saga2d dependency (via the screenshot
harness) so no new packages are pulled in.
"""

from __future__ import annotations

import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "This script needs Pillow. Saga2D already depends on it via the "
        "screenshot harness, so ``pip install -e .`` should cover it."
    ) from exc


def _ellipse(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int,
             fill) -> None:
    draw.ellipse(
        [(cx - r, cy - r), (cx + r, cy + r)],
        fill=fill,
    )


def generate_player_token(out: Path) -> None:
    """Gold disc with a subtle halo and a dark dot in the middle.

    Matches the tri-circle pip Ring of Pain used to draw procedurally:
    a translucent gold halo at r=18, solid gold at r=13, dark centre
    at r=8 — but now the whole thing is one sprite the player can
    style via a color_swap or replace with hand-painted art.
    """
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx = cy = size // 2

    # Halo (translucent gold).
    _ellipse(draw, cx, cy, 28, fill=(255, 215, 100, 50))
    _ellipse(draw, cx, cy, 22, fill=(255, 215, 100, 90))

    # Solid gold disc.
    _ellipse(draw, cx, cy, 18, fill=(255, 215, 100, 255))

    # Slightly deeper gold rim (one pixel inside the disc) for
    # definition against dark backgrounds.
    _ellipse(draw, cx, cy, 16, fill=(255, 230, 140, 255))

    # Dark centre.
    _ellipse(draw, cx, cy, 10, fill=(20, 20, 30, 255))

    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)


def generate(root: Path) -> None:
    images_dir = root / "assets" / "images"
    generate_player_token(images_dir / "player_token.png")
    print(f"Wrote sprites under {images_dir}")


if __name__ == "__main__":
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    generate(root)
