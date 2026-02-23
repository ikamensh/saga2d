"""Generate simple geometric test PNG images for visual testing.

Run from project root::

    python tests/generate_test_assets.py

Creates assets/images/sprites/ with tree.png, knight.png, enemy.png, crate.png,
and animation frames: knight_walk_01..04, knight_attack_01..03.
"""

from pathlib import Path

from PIL import Image, ImageDraw

# Output directory (relative to project root)
ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets" / "images" / "sprites"


def _frame_image(size: tuple[int, int], color: tuple[int, int, int, int], label: str) -> Image.Image:
    """Create a colored rectangle with frame number label."""
    from PIL import ImageFont

    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), fill=color)
    try:
        font = ImageFont.load_default()
        draw.text((size[0] // 2 - 4, size[1] // 2 - 6), label, fill=(255, 255, 255, 255), font=font)
    except Exception:
        draw.text((size[0] // 2 - 4, size[1] // 2 - 6), label, fill=(255, 255, 255, 255))
    return img


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # tree.png: green triangle on transparent background, 64x96
    tree = Image.new("RGBA", (64, 96), (0, 0, 0, 0))
    draw = ImageDraw.Draw(tree)
    draw.polygon(
        [(32, 0), (64, 96), (0, 96)],  # apex center-top, base corners
        fill=(34, 139, 34, 255),  # forest green
    )
    tree.save(ASSETS_DIR / "tree.png")
    print(f"Created {ASSETS_DIR / 'tree.png'}")

    # knight.png: blue rectangle, 48x64
    knight = Image.new("RGBA", (48, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(knight)
    draw.rectangle((0, 0, 47, 63), fill=(30, 144, 255, 255))  # dodger blue
    knight.save(ASSETS_DIR / "knight.png")
    print(f"Created {ASSETS_DIR / 'knight.png'}")

    # enemy.png: red circle, 48x48
    enemy = Image.new("RGBA", (48, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(enemy)
    draw.ellipse((0, 0, 47, 47), fill=(220, 20, 60, 255))  # crimson
    enemy.save(ASSETS_DIR / "enemy.png")
    print(f"Created {ASSETS_DIR / 'enemy.png'}")

    # crate.png: brown rectangle, 32x32
    crate = Image.new("RGBA", (32, 32), (0, 0, 0, 0))
    draw = ImageDraw.Draw(crate)
    draw.rectangle((0, 0, 31, 31), fill=(139, 90, 43, 255))  # saddle brown
    crate.save(ASSETS_DIR / "crate.png")
    print(f"Created {ASSETS_DIR / 'crate.png'}")

    # knight_walk_01..04: blue rectangles with frame number (48x64)
    walk_colors = [(30, 144, 255, 255), (50, 164, 255, 255), (30, 144, 255, 255), (10, 124, 235, 255)]
    for i, color in enumerate(walk_colors, 1):
        frame = _frame_image((48, 64), color, str(i))
        path = ASSETS_DIR / f"knight_walk_{i:02d}.png"
        frame.save(path)
        print(f"Created {path}")

    # knight_attack_01..03: darker blue rectangles with frame number (48x64)
    attack_colors = [(20, 80, 180, 255), (40, 100, 200, 255), (20, 80, 180, 255)]
    for i, color in enumerate(attack_colors, 1):
        frame = _frame_image((48, 64), color, str(i))
        path = ASSETS_DIR / f"knight_attack_{i:02d}.png"
        frame.save(path)
        print(f"Created {path}")


if __name__ == "__main__":
    main()
