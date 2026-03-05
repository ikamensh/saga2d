"""Generate tile and UI assets for the tactical battle vignette demo.

Each public ``make_*`` function returns a ``PIL.Image.Image`` (RGBA mode).
``generate(output_dir)`` saves all files and returns the list of paths.

Filenames and sizes match the architecture contract::

    tile_grass.png           64x64  -- textured grass ground tile
    tile_dirt.png            64x64  -- brown earth/mud tile
    tile_stone.png           64x64  -- grey cobblestone tile
    tile_obstacle.png        64x64  -- grey rock obstacle on grass base
    tile_move.png            64x64  -- semi-transparent blue movement indicator
    tile_attack.png          64x64  -- semi-transparent red attack indicator
    health_bar_bg.png        40x6   -- dark health bar background
    health_bar_fill.png      40x6   -- green health bar fill with gradient

Run from project root::

    python -m assetgen.battle_tiles

All tiles use 4× supersampling and subtle noise for visual richness,
matching the rendering style of battle_sprites.py.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw

from assetgen.primitives import (
    adjust_alpha,
    apply_noise,
    darken,
    filled_ellipse,
    filled_polygon,
    lighten,
    linear_gradient,
    radial_gradient,
    supersample_draw,
)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------

# Grass — varied greens for natural look
GRASS_DARK = (45, 100, 35, 255)
GRASS_MID = (60, 130, 50, 255)
GRASS_LIGHT = (75, 155, 65, 255)
GRASS_BRIGHT = (90, 175, 80, 255)

# Dirt — brown earth tones
DIRT_DARK = (80, 60, 40, 255)
DIRT_MID = (110, 85, 60, 255)
DIRT_LIGHT = (135, 105, 75, 255)
DIRT_BRIGHT = (155, 125, 90, 255)

# Stone — grey cobblestone
STONE_DARK = (70, 75, 80, 255)
STONE_MID = (100, 105, 110, 255)
STONE_LIGHT = (130, 135, 140, 255)
STONE_BRIGHT = (155, 160, 165, 255)

# Movement indicator — blue tactical overlay
MOVE_BLUE = (80, 140, 255, 180)
MOVE_BLUE_LIGHT = (120, 180, 255, 180)
MOVE_BLUE_DARK = (50, 100, 200, 180)
MOVE_BORDER = (100, 160, 255, 220)

# Attack indicator — red tactical overlay
ATTACK_RED = (255, 80, 80, 180)
ATTACK_RED_LIGHT = (255, 120, 120, 180)
ATTACK_RED_DARK = (200, 40, 40, 180)
ATTACK_BORDER = (255, 100, 100, 220)

# Health bar
HEALTH_BG = (40, 40, 45, 220)
HEALTH_BG_BORDER = (25, 25, 30, 255)
HEALTH_GREEN_DARK = (50, 160, 50, 255)
HEALTH_GREEN_MID = (70, 200, 70, 255)
HEALTH_GREEN_LIGHT = (100, 240, 100, 255)

# Obstacle — grey rock
ROCK_DARK = (60, 62, 65, 255)
ROCK_MID = (90, 95, 100, 255)
ROCK_LIGHT = (120, 125, 130, 255)
ROCK_BRIGHT = (150, 155, 160, 255)

# Tile size
TILE_SIZE = (64, 64)
HEALTH_BAR_SIZE = (40, 6)

# Supersampling factor — all rendering is done at SS×
_SS = 4


# ===================================================================
# Scaling helpers (match battle_sprites.py pattern)
# ===================================================================

def _s(v: float) -> float:
    """Scale a 1× coordinate to supersampled space."""
    return v * _SS


def _si(v: float) -> int:
    """Scale a 1× coordinate to supersampled space (integer)."""
    return int(v * _SS)


# ===================================================================
# Grass tile (64×64)
# ===================================================================

def make_tile_grass() -> Image.Image:
    """Generate a grass tile with varied green tones and blade details.

    Uses a multi-stop vertical gradient for depth, random grass tufts
    for texture, and subtle noise for organic feel.
    """
    def paint(big: Image.Image) -> None:
        # Base gradient — darker at bottom, lighter at top for depth
        linear_gradient(
            big,
            stops=[
                (0.0, GRASS_LIGHT),
                (0.4, GRASS_MID),
                (1.0, GRASS_DARK),
            ],
            start=(0.0, 0.0),
            end=(0.0, 1.0),
        )

        # Grass blade tufts — thin vertical lines with slight variation
        draw = ImageDraw.Draw(big, "RGBA")
        tuft_positions = [
            (8, 48), (18, 12), (26, 56), (38, 22), (48, 44),
            (12, 32), (32, 8), (52, 36), (6, 18), (42, 52),
            (22, 40), (56, 14), (14, 58), (44, 26), (28, 50),
        ]

        for tx, ty in tuft_positions:
            sx, sy = _s(tx), _s(ty)
            # Vertical blade (3-5 pixels tall at 1× scale)
            blade_h = _s(3 + (tx % 3))
            draw.line(
                [(sx, sy), (sx, sy - blade_h)],
                fill=GRASS_BRIGHT,
                width=max(1, _si(0.8)),
            )
            # Small offset blade for depth
            if tx % 2 == 0:
                draw.line(
                    [(sx - _s(1), sy), (sx - _s(1), sy - blade_h + _s(1))],
                    fill=GRASS_LIGHT,
                    width=max(1, _si(0.6)),
                )

        # Dark accent spots for variation
        dark_spots = [(10, 24), (40, 50), (20, 8), (50, 32), (16, 44)]
        for dx, dy in dark_spots:
            sx, sy = _si(dx), _si(dy)
            r = _si(2)
            filled_ellipse(
                big,
                (sx - r, sy - r, sx + r, sy + r),
                fill=darken(GRASS_DARK, 0.2),
            )

    sprite = supersample_draw(TILE_SIZE[0], TILE_SIZE[1], paint, factor=_SS)
    # Add organic texture noise
    sprite = apply_noise(sprite, amount=0.08, monochrome=True, seed=200)
    return sprite


# ===================================================================
# Dirt tile (64×64)
# ===================================================================

def make_tile_dirt() -> Image.Image:
    """Generate a dirt/earth tile with brown tones and pebble details.

    Uses a gradient for earthen depth, small pebbles/rocks for texture,
    and moderate noise for a rough, natural surface.
    """
    def paint(big: Image.Image) -> None:
        # Base gradient — brown earth tones
        linear_gradient(
            big,
            stops=[
                (0.0, DIRT_LIGHT),
                (0.5, DIRT_MID),
                (1.0, DIRT_DARK),
            ],
            start=(0.0, 0.0),
            end=(0.0, 1.0),
        )

        # Pebbles — small irregular ellipses scattered across the tile
        pebble_data = [
            (12, 16, 3.5, DIRT_DARK),
            (38, 10, 2.5, STONE_DARK),
            (22, 44, 4.0, DIRT_BRIGHT),
            (50, 28, 3.0, DIRT_LIGHT),
            (8, 52, 2.8, STONE_MID),
            (44, 48, 3.2, DIRT_MID),
            (28, 20, 2.2, DIRT_DARK),
            (56, 14, 2.6, STONE_LIGHT),
            (18, 36, 3.8, DIRT_LIGHT),
            (34, 58, 3.4, DIRT_DARK),
        ]

        for px, py, pr, color in pebble_data:
            cx, cy = _s(px), _s(py)
            r = _s(pr)
            # Slightly elongated ellipse for natural look
            filled_ellipse(
                big,
                (int(cx - r), int(cy - r * 0.8),
                 int(cx + r), int(cy + r * 0.8)),
                fill=color,
            )
            # Highlight on top-left for depth
            filled_ellipse(
                big,
                (int(cx - r * 0.4), int(cy - r * 0.5),
                 int(cx + r * 0.2), int(cy + r * 0.1)),
                fill=lighten(color, 0.2),
            )

        # Cracks/lines for weathered look
        draw = ImageDraw.Draw(big, "RGBA")
        crack_lines = [
            [(8, 30), (24, 28)],
            [(40, 42), (52, 38)],
            [(14, 8), (18, 18)],
            [(48, 56), (58, 62)],
        ]
        for start, end in crack_lines:
            draw.line(
                [(_s(start[0]), _s(start[1])), (_s(end[0]), _s(end[1]))],
                fill=darken(DIRT_DARK, 0.3),
                width=max(1, _si(0.8)),
            )

    sprite = supersample_draw(TILE_SIZE[0], TILE_SIZE[1], paint, factor=_SS)
    # Heavier noise for rough texture
    sprite = apply_noise(sprite, amount=0.12, monochrome=True, seed=201)
    return sprite


# ===================================================================
# Stone tile (64×64)
# ===================================================================

def make_tile_stone() -> Image.Image:
    """Generate a cobblestone tile with grey tones and mortar lines.

    Creates 4 stone blocks with gradient fills separated by dark mortar,
    with subtle highlights and noise for a weathered stone appearance.
    """
    def paint(big: Image.Image) -> None:
        # Base fill — mid-grey
        draw = ImageDraw.Draw(big, "RGBA")
        draw.rectangle((0, 0, big.width, big.height), fill=STONE_MID)

        # Four stone blocks separated by mortar lines
        # Block layout (in 1× coords):
        #   [0-30, 0-30]  [34-64, 0-30]
        #   [0-30, 34-64] [34-64, 34-64]

        blocks = [
            (0, 0, 30, 30),      # top-left
            (34, 0, 64, 30),     # top-right
            (0, 34, 30, 64),     # bottom-left
            (34, 34, 64, 64),    # bottom-right
        ]

        for i, (x0, y0, x1, y1) in enumerate(blocks):
            # Scale to supersampled coords
            bx0, by0 = _si(x0), _si(y0)
            bx1, by1 = _si(x1), _si(y1)
            bbox = (bx0, by0, bx1, by1)

            # Gradient for each stone block (lighter top, darker bottom)
            grad_img = Image.new("RGBA", big.size, (0, 0, 0, 0))
            linear_gradient(
                grad_img,
                stops=[
                    (0.0, STONE_BRIGHT),
                    (0.4, STONE_LIGHT),
                    (1.0, STONE_DARK),
                ],
                start=(0.0, 0.0),
                end=(0.0, 1.0),
                bbox=bbox,
            )

            # Create mask for this block
            mask = Image.new("L", big.size, 0)
            md = ImageDraw.Draw(mask)
            md.rectangle(bbox, fill=255)

            # Composite gradient onto base
            big.paste(Image.composite(grad_img, big, mask), (0, 0))

            # Add subtle edge highlight (top and left edges)
            draw.line(
                [(bx0, by0), (bx1, by0)],
                fill=lighten(STONE_LIGHT, 0.15),
                width=max(1, _si(1)),
            )
            draw.line(
                [(bx0, by0), (bx0, by1)],
                fill=lighten(STONE_LIGHT, 0.15),
                width=max(1, _si(1)),
            )

        # Mortar lines — dark gaps between blocks
        mortar_color = darken(STONE_DARK, 0.4)
        # Vertical mortar at x=32 (1× coord)
        draw.rectangle(
            (_si(31), 0, _si(33), big.height),
            fill=mortar_color,
        )
        # Horizontal mortar at y=32 (1× coord)
        draw.rectangle(
            (0, _si(31), big.width, _si(33)),
            fill=mortar_color,
        )

        # Small cracks/chips on some stones
        chip_positions = [(8, 24), (48, 12), (14, 52), (50, 50)]
        for cx, cy in chip_positions:
            scx, scy = _si(cx), _si(cy)
            r = _si(1.5)
            filled_ellipse(
                big,
                (scx - r, scy - r, scx + r, scy + r),
                fill=STONE_DARK,
            )

    sprite = supersample_draw(TILE_SIZE[0], TILE_SIZE[1], paint, factor=_SS)
    # Moderate noise for stone texture
    sprite = apply_noise(sprite, amount=0.1, monochrome=True, seed=202)
    return sprite


# ===================================================================
# Obstacle tile (64×64, grey rock on grass base)
# ===================================================================

def make_tile_obstacle() -> Image.Image:
    """Generate an obstacle tile with a large grey rock on grass base.

    Creates a 3D-looking boulder with gradient shading, rim lighting,
    and drop shadow. Placed on a grass background for integration.
    """
    def paint(big: Image.Image) -> None:
        # Base layer — grass background (reuse grass gradient)
        linear_gradient(
            big,
            stops=[
                (0.0, GRASS_LIGHT),
                (0.4, GRASS_MID),
                (1.0, GRASS_DARK),
            ],
            start=(0.0, 0.0),
            end=(0.0, 1.0),
        )

        # Rock — large irregular boulder in center
        # Main rock body (roughly elliptical)
        rock_cx, rock_cy = _s(32), _s(36)  # slightly lower than center
        rock_rx, rock_ry = _s(22), _s(18)  # wide ellipse

        # Drop shadow beneath rock (elongated dark ellipse)
        shadow_offset_x, shadow_offset_y = _s(2), _s(3)
        shadow_rx, shadow_ry = _s(20), _s(8)
        filled_ellipse(
            big,
            (
                int(rock_cx - shadow_rx + shadow_offset_x),
                int(rock_cy - shadow_ry + shadow_offset_y + _s(16)),
                int(rock_cx + shadow_rx + shadow_offset_x),
                int(rock_cy + shadow_ry + shadow_offset_y + _s(16)),
            ),
            fill=(0, 0, 0, 100),
        )

        # Rock radial gradient for 3D spherical look
        radial_gradient(
            big,
            (rock_cx - _s(6), rock_cy - _s(6)),  # offset light source top-left
            int(rock_rx * 1.8),
            stops=[
                (0.0, ROCK_BRIGHT),
                (0.3, ROCK_LIGHT),
                (0.7, ROCK_MID),
                (1.0, ROCK_DARK),
            ],
            bbox=(
                int(rock_cx - rock_rx),
                int(rock_cy - rock_ry),
                int(rock_cx + rock_rx),
                int(rock_cy + rock_ry),
            ),
        )

        # Create rock mask (irregular polygon for natural boulder shape)
        mask = Image.new("L", big.size, 0)
        md = ImageDraw.Draw(mask)

        # Irregular 12-point polygon approximating a boulder
        import math
        points = []
        for i in range(12):
            angle = (i / 12) * 2 * math.pi
            # Vary radius for irregular shape
            radius_variance = 0.85 + 0.15 * ((i % 3) / 2)
            rx_var = rock_rx * radius_variance
            ry_var = rock_ry * radius_variance * (0.9 + 0.1 * ((i % 2)))

            px = rock_cx + rx_var * math.cos(angle)
            py = rock_cy + ry_var * math.sin(angle)
            points.append((int(px), int(py)))

        md.polygon(points, fill=255)

        # Apply mask to isolate rock gradient
        rock_img = Image.new("RGBA", big.size, (0, 0, 0, 0))
        radial_gradient(
            rock_img,
            (rock_cx - _s(6), rock_cy - _s(6)),
            int(rock_rx * 1.8),
            stops=[
                (0.0, ROCK_BRIGHT),
                (0.3, ROCK_LIGHT),
                (0.7, ROCK_MID),
                (1.0, ROCK_DARK),
            ],
        )
        big.paste(Image.composite(rock_img, big, mask), (0, 0))

        # Rim lighting — bright highlight on top-left edge
        draw = ImageDraw.Draw(big, "RGBA")
        highlight_points = [
            (rock_cx - _s(18), rock_cy - _s(14)),
            (rock_cx - _s(10), rock_cy - _s(16)),
            (rock_cx, rock_cy - _s(17)),
            (rock_cx + _s(8), rock_cy - _s(15)),
        ]
        for i in range(len(highlight_points) - 1):
            draw.line(
                [highlight_points[i], highlight_points[i + 1]],
                fill=adjust_alpha(ROCK_BRIGHT, 180),
                width=max(1, _si(2)),
            )

        # Surface cracks/texture on rock
        crack_color = darken(ROCK_DARK, 0.3)
        cracks = [
            [(rock_cx - _s(8), rock_cy - _s(4)), (rock_cx + _s(2), rock_cy + _s(2))],
            [(rock_cx + _s(6), rock_cy - _s(8)), (rock_cx + _s(12), rock_cy - _s(2))],
            [(rock_cx - _s(14), rock_cy + _s(4)), (rock_cx - _s(8), rock_cy + _s(10))],
        ]
        for start, end in cracks:
            draw.line(
                [start, end],
                fill=crack_color,
                width=max(1, _si(1.2)),
            )

        # Small pebbles around base for scatter
        pebbles = [
            (rock_cx - _s(26), rock_cy + _s(12), _s(2.5)),
            (rock_cx + _s(24), rock_cy + _s(10), _s(3)),
            (rock_cx - _s(16), rock_cy + _s(18), _s(2)),
            (rock_cx + _s(18), rock_cy + _s(16), _s(2.8)),
        ]
        for px, py, pr in pebbles:
            filled_ellipse(
                big,
                (int(px - pr), int(py - pr), int(px + pr), int(py + pr)),
                fill=ROCK_MID,
            )
            # Tiny highlight
            filled_ellipse(
                big,
                (int(px - pr * 0.4), int(py - pr * 0.4),
                 int(px + pr * 0.2), int(py + pr * 0.2)),
                fill=lighten(ROCK_MID, 0.15),
            )

    sprite = supersample_draw(TILE_SIZE[0], TILE_SIZE[1], paint, factor=_SS)
    # Noise for texture integration
    sprite = apply_noise(sprite, amount=0.08, monochrome=True, seed=205)
    return sprite


# ===================================================================
# Movement indicator tile (64×64, semi-transparent blue)
# ===================================================================

def make_tile_move() -> Image.Image:
    """Generate a semi-transparent blue movement indicator tile.

    Shows a subtle radial gradient from bright centre to darker edges,
    with a border outline. Used for showing valid movement squares.
    """
    def paint(big: Image.Image) -> None:
        # Radial gradient from center — bright blue fading to darker edges
        cx, cy = _s(32), _s(32)
        radius = _s(32)

        radial_gradient(
            big,
            (cx, cy),
            radius,
            stops=[
                (0.0, MOVE_BLUE_LIGHT),
                (0.5, MOVE_BLUE),
                (1.0, MOVE_BLUE_DARK),
            ],
        )

        # Border outline for clarity
        draw = ImageDraw.Draw(big, "RGBA")
        border_inset = _si(2)
        draw.rectangle(
            (border_inset, border_inset,
             big.width - border_inset - 1, big.height - border_inset - 1),
            outline=MOVE_BORDER,
            width=max(1, _si(1.5)),
        )

        # Corner accent marks — small diagonal lines
        accent_len = _si(8)
        accent_color = adjust_alpha(MOVE_BORDER, 255)
        # Top-left corner
        draw.line(
            [(_si(4), _si(4)), (_si(4) + accent_len, _si(4))],
            fill=accent_color,
            width=max(1, _si(1.2)),
        )
        draw.line(
            [(_si(4), _si(4)), (_si(4), _si(4) + accent_len)],
            fill=accent_color,
            width=max(1, _si(1.2)),
        )
        # Bottom-right corner
        draw.line(
            [(big.width - _si(4) - accent_len, big.height - _si(4)),
             (big.width - _si(4), big.height - _si(4))],
            fill=accent_color,
            width=max(1, _si(1.2)),
        )
        draw.line(
            [(big.width - _si(4), big.height - _si(4) - accent_len),
             (big.width - _si(4), big.height - _si(4))],
            fill=accent_color,
            width=max(1, _si(1.2)),
        )

    sprite = supersample_draw(TILE_SIZE[0], TILE_SIZE[1], paint, factor=_SS)
    # Very light noise to avoid flat digital look
    sprite = apply_noise(sprite, amount=0.04, monochrome=True, seed=203)
    return sprite


# ===================================================================
# Attack indicator tile (64×64, semi-transparent red)
# ===================================================================

def make_tile_attack() -> Image.Image:
    """Generate a semi-transparent red attack indicator tile.

    Similar to move indicator but with red tones and a more aggressive
    crosshair pattern. Used for showing valid attack targets.
    """
    def paint(big: Image.Image) -> None:
        # Radial gradient from center — bright red fading to darker edges
        cx, cy = _s(32), _s(32)
        radius = _s(32)

        radial_gradient(
            big,
            (cx, cy),
            radius,
            stops=[
                (0.0, ATTACK_RED_LIGHT),
                (0.5, ATTACK_RED),
                (1.0, ATTACK_RED_DARK),
            ],
        )

        # Border outline
        draw = ImageDraw.Draw(big, "RGBA")
        border_inset = _si(2)
        draw.rectangle(
            (border_inset, border_inset,
             big.width - border_inset - 1, big.height - border_inset - 1),
            outline=ATTACK_BORDER,
            width=max(1, _si(1.5)),
        )

        # Crosshair pattern — centered cross
        crosshair_color = adjust_alpha(ATTACK_BORDER, 255)
        crosshair_thick = max(1, _si(2))
        crosshair_len = _si(12)

        # Horizontal crosshair
        draw.line(
            [(cx - crosshair_len, cy), (cx + crosshair_len, cy)],
            fill=crosshair_color,
            width=crosshair_thick,
        )
        # Vertical crosshair
        draw.line(
            [(cx, cy - crosshair_len), (cx, cy + crosshair_len)],
            fill=crosshair_color,
            width=crosshair_thick,
        )

        # Center dot
        dot_r = _si(2)
        filled_ellipse(
            big,
            (int(cx - dot_r), int(cy - dot_r),
             int(cx + dot_r), int(cy + dot_r)),
            fill=adjust_alpha(ATTACK_BORDER, 255),
        )

    sprite = supersample_draw(TILE_SIZE[0], TILE_SIZE[1], paint, factor=_SS)
    # Very light noise
    sprite = apply_noise(sprite, amount=0.04, monochrome=True, seed=204)
    return sprite


# ===================================================================
# Health bar background (40×6)
# ===================================================================

def make_health_bar_bg() -> Image.Image:
    """Generate a dark health bar background with subtle border.

    Simple dark rectangle with a darker border for depth.
    """
    def paint(big: Image.Image) -> None:
        # Fill with background color
        draw = ImageDraw.Draw(big, "RGBA")
        draw.rectangle((0, 0, big.width - 1, big.height - 1), fill=HEALTH_BG)

        # Dark border outline
        draw.rectangle(
            (0, 0, big.width - 1, big.height - 1),
            outline=HEALTH_BG_BORDER,
            width=max(1, _si(1)),
        )

    sprite = supersample_draw(HEALTH_BAR_SIZE[0], HEALTH_BAR_SIZE[1], paint, factor=_SS)
    return sprite


# ===================================================================
# Health bar fill (40×6, green gradient)
# ===================================================================

def make_health_bar_fill() -> Image.Image:
    """Generate a green health bar fill with vertical gradient and highlight.

    Uses a multi-stop gradient for a glossy, modern health bar appearance,
    with a bright highlight line on top.
    """
    def paint(big: Image.Image) -> None:
        # Vertical gradient — bright at top, darker at bottom
        linear_gradient(
            big,
            stops=[
                (0.0, HEALTH_GREEN_LIGHT),
                (0.4, HEALTH_GREEN_MID),
                (1.0, HEALTH_GREEN_DARK),
            ],
            start=(0.0, 0.0),
            end=(0.0, 1.0),
        )

        # Bright highlight line at the top for glossy effect
        draw = ImageDraw.Draw(big, "RGBA")
        highlight_color = adjust_alpha(HEALTH_GREEN_LIGHT, 255)
        draw.line(
            [(0, 0), (big.width - 1, 0)],
            fill=highlight_color,
            width=max(1, _si(1)),
        )

        # Subtle bright reflection zone in upper third
        reflection_h = big.height // 3
        for y in range(reflection_h):
            t = 1.0 - (y / reflection_h)  # fade out downward
            alpha = int(60 * t)
            draw.line(
                [(0, y), (big.width - 1, y)],
                fill=(255, 255, 255, alpha),
            )

    sprite = supersample_draw(HEALTH_BAR_SIZE[0], HEALTH_BAR_SIZE[1], paint, factor=_SS)
    return sprite


# ===================================================================
# generate() — save all PNGs
# ===================================================================

def generate(output_dir: Path) -> List[Path]:
    """Create all battle tile assets in *output_dir*.

    Returns a list of the written file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    def _save(img: Image.Image, name: str) -> None:
        path = output_dir / name
        img.save(path)
        print(f"Created {path}")
        written.append(path)

    # Terrain tiles
    _save(make_tile_grass(), "tile_grass.png")
    _save(make_tile_dirt(), "tile_dirt.png")
    _save(make_tile_stone(), "tile_stone.png")
    _save(make_tile_obstacle(), "tile_obstacle.png")

    # Tactical indicators
    _save(make_tile_move(), "tile_move.png")
    _save(make_tile_attack(), "tile_attack.png")

    # Health bar
    _save(make_health_bar_bg(), "health_bar_bg.png")
    _save(make_health_bar_fill(), "health_bar_fill.png")

    return written


# ===================================================================
# Main entry point
# ===================================================================

def main() -> None:
    """Entry point for standalone execution."""
    print("=== Battle Tiles & UI Assets ===\n")

    # Default output: examples/battle_vignette/assets/images/tiles/
    default_output = (
        Path(__file__).resolve().parents[1]
        / "examples"
        / "battle_vignette"
        / "assets"
        / "images"
        / "tiles"
    )

    files = generate(default_output)

    print(f"\n{'=' * 60}")
    print(f"Generated {len(files)} tile and UI asset files.")
    print(f"Output directory: {default_output}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
