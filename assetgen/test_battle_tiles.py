"""Quick visual test for battle tiles — display a grid of all generated tiles.

Run from project root::

    python assetgen/test_battle_tiles.py
"""

from pathlib import Path

from PIL import Image

# Tile directory
TILES_DIR = (
    Path(__file__).resolve().parents[1]
    / "examples"
    / "battle_vignette"
    / "assets"
    / "images"
    / "tiles"
)

# All tile files
TILE_FILES = [
    "tile_grass.png",
    "tile_dirt.png",
    "tile_stone.png",
    "tile_move.png",
    "tile_attack.png",
]

HEALTH_BAR_FILES = [
    "health_bar_bg.png",
    "health_bar_fill.png",
]


def test_tiles() -> None:
    """Load and verify all tiles can be read."""
    print("=== Testing Battle Tiles ===\n")

    for filename in TILE_FILES:
        path = TILES_DIR / filename
        if not path.exists():
            print(f"❌ MISSING: {filename}")
            continue

        img = Image.open(path)
        w, h = img.size
        mode = img.mode

        status = "✓" if (w == 64 and h == 64 and mode == "RGBA") else "⚠"
        print(f"{status} {filename:20s} — {w}×{h} {mode}")

    print()

    for filename in HEALTH_BAR_FILES:
        path = TILES_DIR / filename
        if not path.exists():
            print(f"❌ MISSING: {filename}")
            continue

        img = Image.open(path)
        w, h = img.size
        mode = img.mode

        status = "✓" if (w == 40 and h == 6 and mode == "RGBA") else "⚠"
        print(f"{status} {filename:20s} — {w}×{h} {mode}")

    print("\n=== All tiles loaded successfully! ===")


def create_tile_sheet() -> None:
    """Create a composite image showing all tiles for visual inspection."""
    print("\n=== Creating Tile Sheet ===\n")

    # Layout: 3×2 grid of 64×64 tiles, plus health bars below
    # Grid size: 192×128 (3 tiles wide, 2 tiles tall)
    # Health bar area: 192×20 (centered bars)
    sheet_w = 64 * 3
    sheet_h = 64 * 2 + 30  # extra space for health bars

    sheet = Image.new("RGBA", (sheet_w, sheet_h), (30, 30, 40, 255))

    # Place terrain tiles in top row
    terrain_tiles = ["tile_grass.png", "tile_dirt.png", "tile_stone.png"]
    for i, filename in enumerate(terrain_tiles):
        path = TILES_DIR / filename
        if path.exists():
            tile = Image.open(path)
            sheet.paste(tile, (i * 64, 0), tile)

    # Place indicator tiles in bottom row
    indicator_tiles = ["tile_move.png", "tile_attack.png"]
    for i, filename in enumerate(indicator_tiles):
        path = TILES_DIR / filename
        if path.exists():
            tile = Image.open(path)
            # Place starting at position 0 and 1 in second row
            sheet.paste(tile, (i * 64, 64), tile)

    # Place health bars in the extra space below
    # Center them horizontally
    health_y = 64 * 2 + 8
    health_x_start = (sheet_w - 40 * 2 - 10) // 2  # center two bars with gap

    bg_path = TILES_DIR / "health_bar_bg.png"
    if bg_path.exists():
        bg = Image.open(bg_path)
        sheet.paste(bg, (health_x_start, health_y), bg)

    fill_path = TILES_DIR / "health_bar_fill.png"
    if fill_path.exists():
        fill = Image.open(fill_path)
        sheet.paste(fill, (health_x_start + 50, health_y), fill)

    # Save the tile sheet
    output_path = TILES_DIR / "tile_sheet_preview.png"
    sheet.save(output_path)
    print(f"Created tile sheet: {output_path}")
    print("Open this file to visually inspect all tiles at once.")


if __name__ == "__main__":
    test_tiles()
    create_tile_sheet()
