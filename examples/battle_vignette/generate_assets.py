"""Generate PNG sprite assets for the tactical battle demo.

Run from project root::

    python examples/battle_vignette/generate_assets.py

Creates examples/battle_vignette/assets/images/sprites/ with warrior, skeleton,
and select_ring assets.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "images" / "sprites"

BLUE = (30, 144, 255, 255)   # player team
RED = (220, 20, 60, 255)    # enemy team
WHITE = (255, 255, 255, 255)
YELLOW = (255, 255, 0, 255)


def _rect_image(size: tuple[int, int], color: tuple[int, int, int, int], label: str) -> Image.Image:
    """Create a colored rectangle with centered text label."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), fill=color)
    # Dark text on white (hit flash), white on colored backgrounds
    fill = (50, 50, 50, 255) if color[:3] == (255, 255, 255) else WHITE
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    tw = len(label) * 6
    th = 10
    tx = (size[0] - tw) // 2
    ty = (size[1] - th) // 2
    draw.text((tx, ty), label, fill=fill, font=font)
    return img


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. warrior_idle_01.png
    img = _rect_image((64, 64), BLUE, "W")
    img.save(ASSETS_DIR / "warrior_idle_01.png")
    print(f"Created {ASSETS_DIR / 'warrior_idle_01.png'}")

    # 2. warrior_walk_01..04
    for i in range(1, 5):
        img = _rect_image((64, 64), BLUE, f"W{i}")
        img.save(ASSETS_DIR / f"warrior_walk_{i:02d}.png")
        print(f"Created {ASSETS_DIR / f'warrior_walk_{i:02d}.png'}")

    # 3. warrior_attack_01..03
    for i in range(1, 4):
        img = _rect_image((64, 64), BLUE, f"A{i}")
        img.save(ASSETS_DIR / f"warrior_attack_{i:02d}.png")
        print(f"Created {ASSETS_DIR / f'warrior_attack_{i:02d}.png'}")

    # 4. skeleton_idle_01.png
    img = _rect_image((64, 64), RED, "S")
    img.save(ASSETS_DIR / "skeleton_idle_01.png")
    print(f"Created {ASSETS_DIR / 'skeleton_idle_01.png'}")

    # 5. skeleton_walk_01..04
    for i in range(1, 5):
        img = _rect_image((64, 64), RED, f"S{i}")
        img.save(ASSETS_DIR / f"skeleton_walk_{i:02d}.png")
        print(f"Created {ASSETS_DIR / f'skeleton_walk_{i:02d}.png'}")

    # 6. skeleton_hit_01..03 — white/red alternating
    hit_colors = [WHITE, RED, WHITE]
    for i in range(1, 4):
        img = _rect_image((64, 64), hit_colors[i - 1], f"H{i}")
        img.save(ASSETS_DIR / f"skeleton_hit_{i:02d}.png")
        print(f"Created {ASSETS_DIR / f'skeleton_hit_{i:02d}.png'}")

    # 7. skeleton_death_01..03 — decreasing opacity
    for i in range(1, 4):
        opacity = int(255 * (4 - i) / 3)  # 255, 170, 85
        color = (RED[0], RED[1], RED[2], opacity)
        img = _rect_image((64, 64), color, f"D{i}")
        img.save(ASSETS_DIR / f"skeleton_death_{i:02d}.png")
        print(f"Created {ASSETS_DIR / f'skeleton_death_{i:02d}.png'}")

    # 8. select_ring.png — 72x72 transparent with yellow circle outline
    img = Image.new("RGBA", (72, 72), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((4, 4, 67, 67), outline=YELLOW, width=4)
    img.save(ASSETS_DIR / "select_ring.png")
    print(f"Created {ASSETS_DIR / 'select_ring.png'}")


if __name__ == "__main__":
    main()
