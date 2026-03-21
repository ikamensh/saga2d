"""Generate all placeholder assets for the Tower Defense example.

Each public ``make_*`` function returns a ``PIL.Image.Image`` (RGBA mode).
``generate(output_dir)`` saves all files and returns the list of paths.

All visual assets use 4x supersampling with 2x content scale for crisp,
professional-quality output.  Coordinates are authored in 32-unit space
and scaled via ``_s()``/``_si()`` helpers.

Assets generated::

    Terrain (64x64):
        grass.png            -- emerald grass tile (= grass_0)
        grass_0.png          -- grass variant 0 (tufts + pebbles)
        grass_1.png          -- grass variant 1 (dense tufts + flower)
        grass_2.png          -- grass variant 2 (rocky, warm tint)
        grass_3.png          -- grass variant 3 (sparse, dead patch)
        path_straight.png    -- slate walkable path with border
        path_turn.png        -- path corner piece

    Towers (64x64):
        tower_basic.png      -- slate turret with sky-blue accent
        tower_sniper.png     -- long-range tower (indigo tint)
        tower_splash.png     -- area-of-effect cannon (red tint)
        tower_slot.png       -- empty buildable slot marker

    Enemies (48x48):
        enemy_basic.png      -- rose foot soldier
        enemy_fast.png       -- orange scout (diamond shape)
        enemy_tank.png       -- dark-rose heavy (armoured)

    Projectiles (16x16):
        projectile_basic.png -- yellow glow dot
        projectile_sniper.png -- cyan bolt
        projectile_splash.png -- orange ball

    Effects (various):
        explosion.png        -- 32x32 orange/yellow burst
        range_indicator.png  -- 128x128 semi-transparent circle

    UI elements:
        btn_normal.png       -- 160x64 dark button
        btn_hover.png        -- 160x64 lighter button
        btn_pressed.png      -- 160x64 darker pressed button
        panel_bg.png         -- 240x400 dark UI panel
        health_bar_bg.png    -- 48x8 dark health bar background
        health_bar_fill.png  -- 48x8 green health bar fill
        coin_icon.png        -- 32x32 gold coin
        heart_icon.png       -- 32x32 red heart
        wave_banner.png      -- 320x80 wave announcement banner

    HUD:
        hud_top_bar.png      -- 640x48 top HUD bar background

    Sound effects (WAV, assets/sounds/):
        sfx_shoot.wav        -- short click/pop for tower firing
        sfx_hit.wav          -- thud for projectile impact
        sfx_death.wav        -- descending tone for enemy death
        sfx_wave.wav         -- rising alert for wave start
        sfx_lose_life.wav    -- low buzz for life lost

    Music (WAV, assets/music/):
        bgm_game.wav         -- short looping placeholder

Run standalone::

    python examples/tower_defense/generate_assets.py
"""

from __future__ import annotations

import math
import struct
import sys
import wave
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so `assetgen` is importable
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from assetgen.primitives import (  # noqa: E402
    adjust_alpha,
    apply_noise,
    darken,
    filled_ellipse,
    filled_polygon,
    lighten,
    linear_gradient,
    outlined_ellipse,
    outlined_polygon,
    radial_gradient,
    supersample_draw,
    vertical_gradient,
)

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
Color = Tuple[int, int, int, int]  # RGBA

# ---------------------------------------------------------------------------
# Supersampling & scaling (match battle_tiles.py pattern)
# ---------------------------------------------------------------------------
_SS = 4  # supersampling factor
_SCALE = 2  # content scale (author at 32, output at 64)


def _s(v: float) -> float:
    """Scale a 1x coordinate to supersampled space."""
    return v * _SS * _SCALE


def _si(v: float) -> int:
    """Scale a 1x coordinate to supersampled space (integer)."""
    return int(v * _SS * _SCALE)


# ---------------------------------------------------------------------------
# Colour palette — Tailwind CSS inspired
# ---------------------------------------------------------------------------

# Grass — Emerald variants
GRASS_DARK = (4, 120, 87, 255)  # Emerald 800
GRASS_MID = (16, 185, 129, 255)  # Emerald 500
GRASS_LIGHT = (52, 211, 153, 255)  # Emerald 400
GRASS_BRIGHT = (110, 231, 183, 255)  # Emerald 300

# Path — Slate variants
PATH_DARK = (51, 65, 85, 255)  # Slate 700
PATH_MID = (100, 116, 139, 255)  # Slate 500
PATH_LIGHT = (148, 163, 184, 255)  # Slate 400
PATH_BRIGHT = (203, 213, 225, 255)  # Slate 300

# Towers — Slate base + Sky accent
TOWER_BASE = (71, 85, 105, 255)  # Slate 600
TOWER_DARK = (51, 65, 85, 255)  # Slate 700
TOWER_LIGHT = (100, 116, 139, 255)  # Slate 500
TOWER_ACCENT = (56, 189, 248, 255)  # Sky 400
TOWER_ACCENT_LIGHT = (125, 211, 252, 255)  # Sky 300
TOWER_SNIPER_ACCENT = (99, 102, 241, 255)  # Indigo 500
TOWER_SPLASH_ACCENT = (239, 68, 68, 255)  # Red 500

# Slot
SLOT_GREEN = (52, 211, 153, 100)  # Emerald 400 translucent
SLOT_BORDER = (110, 231, 183, 180)  # Emerald 300 translucent

# Enemies — NEON/HIGH CONTRAST variants for maximum visibility
ENEMY_PRIMARY = (255, 20, 147, 255)  # Neon Hot Pink/Magenta
ENEMY_DARK = (220, 20, 130, 255)  # Deep Magenta
ENEMY_LIGHT = (255, 105, 180, 255)  # Bright Pink
ENEMY_OUTLINE = (255, 255, 255, 255)  # Pure White (2px border)
ENEMY_FAST = (255, 140, 0, 255)  # Neon Orange
ENEMY_FAST_DARK = (255, 100, 0, 255)  # Deep Orange
ENEMY_FAST_OUTLINE = (255, 255, 255, 255)  # Pure White
ENEMY_TANK = (255, 0, 100, 255)  # Neon Red-Pink
ENEMY_TANK_DARK = (200, 0, 80, 255)  # Deep Red-Pink
ENEMY_TANK_OUTLINE = (255, 255, 255, 255)  # Pure White

# Projectiles
PROJ_YELLOW = (253, 224, 71, 255)  # Yellow 300
PROJ_CYAN = (34, 211, 238, 255)  # Cyan 400
PROJ_ORANGE = (251, 146, 60, 255)  # Orange 400

# Effects
EXPLOSION_ORANGE = (251, 146, 60, 220)  # Orange 400
EXPLOSION_YELLOW = (253, 224, 71, 200)  # Yellow 300
RANGE_COLOR = (56, 189, 248, 50)  # Sky 400 translucent
RANGE_BORDER_COLOR = (56, 189, 248, 100)  # Sky 400

# UI — Slate 800 backgrounds, Sky 400 accents
UI_DARK = (30, 41, 59, 230)  # Slate 800
UI_MID = (51, 65, 85, 230)  # Slate 700
UI_LIGHT = (71, 85, 105, 230)  # Slate 600
UI_BORDER = (100, 116, 139, 255)  # Slate 500
GOLD = (253, 224, 71, 255)  # Yellow 300
GOLD_DARK = (202, 138, 4, 255)  # Yellow 600
HEALTH_GREEN = (34, 197, 94, 255)  # Green 500
HEALTH_BG = (30, 41, 59, 200)  # Slate 800
HEART_RED = (244, 63, 94, 255)  # Rose 500
HEART_DARK = (190, 18, 60, 255)  # Rose 700
BANNER_BORDER = (253, 224, 71, 255)  # Yellow 300
HUD_BG = (15, 23, 42, 220)  # Slate 900

# Trees — Brown trunks and Green canopy
TREE_TRUNK_DARK = (92, 64, 51, 255)  # Brown 800
TREE_TRUNK_MID = (120, 82, 66, 255)  # Brown 600
TREE_TRUNK_LIGHT = (161, 110, 89, 255)  # Brown 400
TREE_CANOPY_DARK = (21, 128, 61, 255)  # Green 700
TREE_CANOPY_MID = (34, 197, 94, 255)  # Green 500
TREE_CANOPY_LIGHT = (74, 222, 128, 255)  # Green 400


# ===================================================================
# Grass helpers
# ===================================================================


def _paint_grass(
    big: Image.Image,
    tuft_positions: list[tuple[int, int]],
    pebble_positions: list[tuple[int, int]],
    dark_positions: list[tuple[int, int]],
    extra_fn=None,
) -> None:
    """Shared grass-painting logic for all 4 variants."""
    # Flat base color (no gradient) — eliminates banding entirely
    # We'll rely on heavy noise for texture variation
    draw = ImageDraw.Draw(big, "RGBA")
    draw.rectangle(
        (0, 0, big.width - 1, big.height - 1),
        fill=GRASS_MID,
    )

    draw = ImageDraw.Draw(big, "RGBA")

    # Grass blade tufts
    for tx, ty in tuft_positions:
        sx, sy = _s(tx), _s(ty)
        blade_h = _s(3 + (tx % 3))
        draw.line(
            [(sx, sy), (sx, sy - blade_h)],
            fill=GRASS_BRIGHT,
            width=max(1, _si(0.8)),
        )
        if tx % 2 == 0:
            draw.line(
                [(sx - _s(1), sy), (sx - _s(1), sy - blade_h + _s(1))],
                fill=GRASS_LIGHT,
                width=max(1, _si(0.6)),
            )

    # Pebble details
    for px, py in pebble_positions:
        cx, cy = _si(px), _si(py)
        r = _si(1.2)
        filled_ellipse(
            big,
            (cx - r, cy - r, cx + r, cy + int(r * 0.8)),
            fill=darken(GRASS_DARK, 0.15),
        )

    # Per-variant extras
    if extra_fn is not None:
        extra_fn(big, draw)


# ===================================================================
# Terrain tiles (64x64 output)
# ===================================================================


def make_grass_0() -> Image.Image:
    """64x64 grass variant 0 — standard tufts and pebbles."""
    tufts = [
        (4, 6),
        (18, 3),
        (26, 12),
        (8, 20),
        (22, 24),
        (14, 14),
        (2, 28),
        (28, 28),
        (12, 8),
        (24, 18),
    ]
    pebbles = [(10, 25), (25, 7)]
    darks = [(6, 14), (20, 20), (30, 10)]

    def paint(big):
        _paint_grass(big, tufts, pebbles, darks)

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.20, monochrome=True, seed=100)


def make_grass_1() -> Image.Image:
    """64x64 grass variant 1 — denser tufts with small flower dots."""
    tufts = [
        (3, 8),
        (9, 4),
        (16, 10),
        (24, 6),
        (30, 14),
        (6, 18),
        (14, 22),
        (22, 16),
        (28, 24),
        (10, 28),
        (18, 30),
        (4, 14),
        (20, 8),
        (26, 28),
    ]
    pebbles = [(12, 20)]
    darks = [(8, 26), (24, 12)]

    def _flowers(big, draw):
        # Small bright flower dots
        for fx, fy, color in [
            (7, 12, (253, 224, 71, 200)),
            (21, 22, (251, 113, 133, 200)),
            (28, 8, (253, 224, 71, 180)),
        ]:
            cx, cy = _si(fx), _si(fy)
            r = _si(1)
            filled_ellipse(big, (cx - r, cy - r, cx + r, cy + r), fill=color)

    def paint(big):
        _paint_grass(big, tufts, pebbles, darks, extra_fn=_flowers)

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.19, monochrome=True, seed=101)


def make_grass_2() -> Image.Image:
    """64x64 grass variant 2 — more pebbles, slightly warm tint."""
    tufts = [
        (5, 10),
        (15, 5),
        (25, 15),
        (10, 25),
        (20, 28),
        (30, 6),
        (8, 16),
    ]
    pebbles = [
        (6, 8),
        (18, 14),
        (28, 22),
        (12, 28),
        (24, 4),
        (4, 22),
        (22, 10),
    ]
    darks = [(14, 18), (26, 26), (8, 4)]

    def _warm_tint(big, draw):
        # Subtle warm overlay in patches
        for wx, wy in [(10, 12), (24, 20)]:
            cx, cy = _si(wx), _si(wy)
            r = _si(5)
            filled_ellipse(
                big,
                (cx - r, cy - r, cx + r, cy + r),
                fill=(180, 160, 60, 25),
            )

    def paint(big):
        _paint_grass(big, tufts, pebbles, darks, extra_fn=_warm_tint)

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.21, monochrome=True, seed=102)


def make_grass_3() -> Image.Image:
    """64x64 grass variant 3 — sparse tufts with dead patch."""
    tufts = [
        (6, 8),
        (20, 4),
        (28, 18),
        (14, 26),
        (4, 20),
    ]
    pebbles = [(10, 14), (24, 24)]
    darks = [(16, 10), (8, 28), (26, 6)]

    def _dead_patch(big, draw):
        # Brown dead-grass patch
        cx, cy = _si(18), _si(16)
        rx, ry = _si(6), _si(4)
        filled_ellipse(
            big,
            (cx - rx, cy - ry, cx + rx, cy + ry),
            fill=(120, 100, 60, 100),
        )
        # A couple short dead blades
        for dx, dy in [(16, 15), (20, 17)]:
            sx, sy = _s(dx), _s(dy)
            draw.line(
                [(sx, sy), (sx, sy - _s(2))],
                fill=(140, 120, 70, 180),
                width=max(1, _si(0.7)),
            )

    def paint(big):
        _paint_grass(big, tufts, pebbles, darks, extra_fn=_dead_patch)

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.20, monochrome=True, seed=103)


def make_grass() -> Image.Image:
    """64x64 default grass tile (backward compat — delegates to variant 0)."""
    return make_grass_0()


def make_tree() -> Image.Image:
    """64x64 decorative tree — brown trunk with irregular leafy canopy and shadow."""

    def paint(big: Image.Image) -> None:
        cx, cy = big.width // 2, big.height // 2
        draw = ImageDraw.Draw(big, "RGBA")

        # Shadow (subtle ellipse at base, offset right)
        shadow_r_x = _si(14)
        shadow_r_y = _si(6)
        shadow_cx = cx + _si(2)
        shadow_cy = big.height - _si(6)
        filled_ellipse(
            big,
            (
                shadow_cx - shadow_r_x,
                shadow_cy - shadow_r_y,
                shadow_cx + shadow_r_x,
                shadow_cy + shadow_r_y,
            ),
            fill=(0, 0, 0, 40),
        )

        # Trunk (centered, tapering slightly)
        trunk_w = _si(4)
        trunk_top = _si(18)
        trunk_bottom = big.height - _si(4)

        # Trunk gradient (vertical)
        for y in range(trunk_top, trunk_bottom):
            progress = (y - trunk_top) / (trunk_bottom - trunk_top)
            if progress < 0.5:
                color = TREE_TRUNK_LIGHT
            else:
                # Blend to darker at bottom
                blend = (progress - 0.5) * 2
                r = int(TREE_TRUNK_LIGHT[0] * (1 - blend) + TREE_TRUNK_DARK[0] * blend)
                g = int(TREE_TRUNK_LIGHT[1] * (1 - blend) + TREE_TRUNK_DARK[1] * blend)
                b = int(TREE_TRUNK_LIGHT[2] * (1 - blend) + TREE_TRUNK_DARK[2] * blend)
                color = (r, g, b, 255)

            draw.line(
                [(cx - trunk_w, y), (cx + trunk_w, y)],
                fill=color,
                width=1,
            )

        # Irregular canopy (multiple overlapping circles for leafy effect)
        # Base cluster (5 circles arranged asymmetrically)
        canopy_circles = [
            # (offset_x, offset_y, radius, color)
            (0, 0, _si(11), TREE_CANOPY_DARK),  # center large
            (-_si(7), _si(3), _si(8), TREE_CANOPY_DARK),  # left-bottom
            (_si(7), _si(2), _si(7), TREE_CANOPY_DARK),  # right-bottom
            (-_si(4), -_si(6), _si(9), TREE_CANOPY_MID),  # left-top
            (_si(5), -_si(5), _si(8), TREE_CANOPY_MID),  # right-top
        ]

        for ox, oy, r, color in canopy_circles:
            ccx, ccy = cx + ox, cy + oy
            filled_ellipse(
                big,
                (ccx - r, ccy - r, ccx + r, ccy + r),
                fill=color,
            )

        # Top highlight clusters (bright, smaller, for leafy texture)
        highlights = [
            (cx - _si(2), cy - _si(7), _si(5), TREE_CANOPY_LIGHT),
            (cx + _si(4), cy - _si(4), _si(4), TREE_CANOPY_LIGHT),
            (cx - _si(6), cy + _si(1), _si(4), TREE_CANOPY_LIGHT),
        ]

        for hx, hy, r, color in highlights:
            filled_ellipse(
                big,
                (hx - r, hy - r, hx + r, hy + r),
                fill=color,
            )

        # Leaf detail spots (dark gaps between foliage clusters)
        leaf_gaps = [
            (cx - _si(8), cy + _si(5)),
            (cx + _si(7), cy + _si(3)),
            (cx + _si(2), cy - _si(9)),
            (cx - _si(5), cy - _si(2)),
        ]
        for lx, ly in leaf_gaps:
            gap_r = _si(1.8)
            filled_ellipse(
                big,
                (int(lx - gap_r), int(ly - gap_r), int(lx + gap_r), int(ly + gap_r)),
                fill=darken(TREE_CANOPY_DARK, 0.3),
            )

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.08, monochrome=True, seed=200)


def make_path_straight() -> Image.Image:
    """64x64 straight path tile — darker slate with distinct borders."""

    def paint(big: Image.Image) -> None:
        # Base gradient — darker slate tones for better contrast
        linear_gradient(
            big,
            stops=[
                (0.0, darken(PATH_MID, 0.2)),
                (0.3, PATH_MID),
                (0.7, darken(PATH_MID, 0.1)),
                (1.0, darken(PATH_DARK, 0.1)),
            ],
            start=(0.0, 0.0),
            end=(0.0, 1.0),
        )

        draw = ImageDraw.Draw(big, "RGBA")

        # Distinct darker borders (6px) on top and bottom edges
        border_h = _si(6)
        darker_border = darken(PATH_DARK, 0.3)
        draw.rectangle((0, 0, big.width - 1, border_h - 1), fill=darker_border)
        draw.rectangle(
            (0, big.height - border_h, big.width - 1, big.height - 1),
            fill=darker_border,
        )

        # Inner highlight stripe (centre band)
        stripe_y0 = _si(14)
        stripe_y1 = _si(18)
        draw.rectangle(
            (_si(2), stripe_y0, big.width - _si(2), stripe_y1),
            fill=PATH_BRIGHT,
        )

        # Pebble details
        pebble_data = [
            (6, 8, 1.5),
            (20, 12, 1.2),
            (12, 22, 1.8),
            (26, 26, 1.3),
            (8, 28, 1.0),
            (18, 6, 1.4),
        ]
        for px, py, pr in pebble_data:
            cx, cy = _si(px), _si(py)
            r = _si(pr)
            filled_ellipse(
                big,
                (cx - r, cy - int(r * 0.7), cx + r, cy + int(r * 0.7)),
                fill=darken(PATH_DARK, 0.15),
            )

        # Worn crack lines
        crack_color = darken(PATH_DARK, 0.3)
        cracks = [
            [(8, 10), (16, 9)],
            [(22, 20), (28, 18)],
        ]
        for start, end in cracks:
            draw.line(
                [(_s(start[0]), _s(start[1])), (_s(end[0]), _s(end[1]))],
                fill=crack_color,
                width=max(1, _si(0.8)),
            )

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.10, monochrome=True, seed=110)


def make_path_turn() -> Image.Image:
    """64x64 path corner tile — top-to-right turn on grass base."""

    def paint(big: Image.Image) -> None:
        # Grass base
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

        draw = ImageDraw.Draw(big, "RGBA")

        # L-shaped path region (vertical top + horizontal right) - darker for contrast
        # Vertical leg: x=[6..25], y=[0..18]
        draw.rectangle(
            (_si(6), 0, _si(25), _si(18)),
            fill=darken(PATH_MID, 0.15),
        )
        # Horizontal leg: x=[14..32], y=[6..25]
        draw.rectangle(
            (_si(14), _si(6), big.width - 1, _si(25)),
            fill=darken(PATH_MID, 0.15),
        )

        # Distinct darker borders (wider) on outer edges
        bw = max(2, _si(2))
        border = darken(PATH_DARK, 0.3)
        # Left edge of vertical leg
        draw.line([(_si(6), 0), (_si(6), _si(18))], fill=border, width=bw)
        # Bottom edge of vertical leg into horizontal junction
        draw.line([(_si(6), _si(18)), (_si(14), _si(18))], fill=border, width=bw)
        # Left edge of horizontal leg
        draw.line([(_si(14), _si(18)), (_si(14), _si(25))], fill=border, width=bw)
        # Bottom edge of horizontal leg
        draw.line([(_si(14), _si(25)), (big.width - 1, _si(25))], fill=border, width=bw)
        # Right edge of vertical leg into horizontal junction
        draw.line([(_si(25), 0), (_si(25), _si(6))], fill=border, width=bw)
        # Top edge of horizontal leg
        draw.line([(_si(25), _si(6)), (big.width - 1, _si(6))], fill=border, width=bw)

        # Pebble texture in the path area
        for px, py in [(12, 8), (20, 14), (24, 20)]:
            cx, cy = _si(px), _si(py)
            r = _si(1.2)
            filled_ellipse(
                big,
                (cx - r, cy - int(r * 0.7), cx + r, cy + int(r * 0.7)),
                fill=darken(PATH_DARK, 0.15),
            )

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.08, monochrome=True, seed=111)


# ===================================================================
# Tower sprites (64x64 output)
# ===================================================================


def _draw_tower_base(big: Image.Image, base_color: Color, accent: Color) -> None:
    """Draw a common tower platform/base with gradient fill."""
    draw = ImageDraw.Draw(big, "RGBA")

    # Platform rectangle with vertical gradient
    px0, py0 = _si(6), _si(18)
    px1, py1 = _si(25), _si(30)
    linear_gradient(
        big,
        stops=[
            (0.0, lighten(base_color, 0.15)),
            (0.5, base_color),
            (1.0, darken(base_color, 0.2)),
        ],
        start=(0.0, 0.0),
        end=(0.0, 1.0),
        bbox=(px0, py0, px1, py1),
    )

    # Top edge highlight
    draw.line(
        [(px0, py0), (px1, py0)],
        fill=accent,
        width=max(1, _si(1)),
    )
    # Bottom shadow
    draw.line(
        [(px0, py1), (px1, py1)],
        fill=darken(base_color, 0.35),
        width=max(1, _si(1)),
    )

    # Crenellations (3 blocks with gradient)
    for bx in (7, 13, 19):
        bx0, by0 = _si(bx), _si(15)
        bx1, by1 = _si(bx + 4), _si(18)
        linear_gradient(
            big,
            stops=[
                (0.0, lighten(base_color, 0.1)),
                (1.0, base_color),
            ],
            start=(0.0, 0.0),
            end=(0.0, 1.0),
            bbox=(bx0, by0, bx1, by1),
        )
        draw.line(
            [(bx0, by0), (bx1, by0)],
            fill=accent,
            width=max(1, _si(0.8)),
        )


def make_tower_basic() -> Image.Image:
    """64x64 basic tower — slate base with barrel and sky-blue accent."""

    def paint(big: Image.Image) -> None:
        _draw_tower_base(big, TOWER_BASE, TOWER_ACCENT)

        draw = ImageDraw.Draw(big, "RGBA")

        # Barrel — vertical gradient (metallic look)
        bx0, by0 = _si(13), _si(4)
        bx1, by1 = _si(18), _si(17)
        linear_gradient(
            big,
            stops=[
                (0.0, TOWER_LIGHT),
                (0.5, TOWER_BASE),
                (1.0, TOWER_DARK),
            ],
            start=(0.0, 0.0),
            end=(1.0, 0.0),
            bbox=(bx0, by0, bx1, by1),
        )
        # Barrel highlight
        draw.line(
            [(bx0, by0), (bx1, by0)],
            fill=TOWER_ACCENT_LIGHT,
            width=max(1, _si(1)),
        )

        # Muzzle block
        mx0, my0 = _si(12), _si(2)
        mx1, my1 = _si(19), _si(5)
        draw.rectangle((mx0, my0, mx1, my1), fill=TOWER_BASE)
        draw.line(
            [(mx0, my0), (mx1, my0)],
            fill=TOWER_ACCENT,
            width=max(1, _si(0.8)),
        )

        # Muzzle flash dot
        cx = (_si(12) + _si(19)) // 2
        r = _si(1)
        filled_ellipse(
            big,
            (cx - r, _si(1), cx + r, _si(3)),
            fill=TOWER_ACCENT_LIGHT,
        )

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.06, monochrome=True, seed=120)


def make_tower_sniper() -> Image.Image:
    """64x64 sniper tower — indigo-tinted, long narrow barrel with scope."""
    sniper_base = (79, 70, 129, 255)  # indigo-ish
    sniper_light = (129, 120, 179, 255)
    sniper_accent = TOWER_SNIPER_ACCENT

    def paint(big: Image.Image) -> None:
        _draw_tower_base(big, sniper_base, sniper_accent)

        draw = ImageDraw.Draw(big, "RGBA")

        # Long narrow barrel
        bx0, by0 = _si(14), _si(1)
        bx1, by1 = _si(17), _si(17)
        linear_gradient(
            big,
            stops=[
                (0.0, sniper_light),
                (0.5, sniper_base),
                (1.0, darken(sniper_base, 0.2)),
            ],
            start=(0.0, 0.0),
            end=(1.0, 0.0),
            bbox=(bx0, by0, bx1, by1),
        )

        # Barrel tip highlight
        draw.line(
            [(bx0, by0), (bx1, by0)],
            fill=sniper_accent,
            width=max(1, _si(1)),
        )

        # Scope lens — small circle on barrel
        scope_cx = _si(15.5)
        scope_cy = _si(6)
        scope_r = _si(2)
        filled_ellipse(
            big,
            (
                scope_cx - scope_r,
                scope_cy - scope_r,
                scope_cx + scope_r,
                scope_cy + scope_r,
            ),
            fill=darken(sniper_base, 0.3),
        )
        # Cyan glow dot in scope
        gr = _si(1)
        filled_ellipse(
            big,
            (scope_cx - gr, scope_cy - gr, scope_cx + gr, scope_cy + gr),
            fill=PROJ_CYAN,
        )

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.06, monochrome=True, seed=121)


def make_tower_splash() -> Image.Image:
    """64x64 splash tower — red-tinted wide cannon."""
    splash_base = (159, 70, 60, 255)  # warm red-brown
    splash_light = (200, 120, 110, 255)
    splash_accent = TOWER_SPLASH_ACCENT

    def paint(big: Image.Image) -> None:
        _draw_tower_base(big, splash_base, splash_accent)

        draw = ImageDraw.Draw(big, "RGBA")

        # Wide cannon barrel
        bx0, by0 = _si(11), _si(6)
        bx1, by1 = _si(20), _si(17)
        linear_gradient(
            big,
            stops=[
                (0.0, splash_light),
                (0.5, splash_base),
                (1.0, darken(splash_base, 0.25)),
            ],
            start=(0.0, 0.0),
            end=(1.0, 0.0),
            bbox=(bx0, by0, bx1, by1),
        )

        # Barrel top highlight
        draw.line(
            [(bx0, by0), (bx1, by0)],
            fill=splash_accent,
            width=max(1, _si(1)),
        )

        # Wide muzzle opening
        mx0, my0 = _si(9), _si(4)
        mx1, my1 = _si(22), _si(7)
        draw.rectangle((mx0, my0, mx1, my1), fill=splash_base)
        draw.line(
            [(mx0, my0), (mx1, my0)],
            fill=splash_light,
            width=max(1, _si(0.8)),
        )

        # Dark muzzle hole
        cx = (_si(9) + _si(22)) // 2
        cy = _si(3)
        rx, ry = _si(3), _si(1.5)
        filled_ellipse(
            big,
            (cx - rx, cy - ry, cx + rx, cy + ry),
            fill=darken(splash_base, 0.5),
        )

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.06, monochrome=True, seed=122)


def make_tower_slot() -> Image.Image:
    """64x64 empty tower slot — LIGHT stone foundation with distinct border."""
    # MUCH lighter stone colors (Slate 300/400 - clearly not emerald)
    stone_base = (203, 213, 225, 255)  # Slate 300 - very light
    stone_light = (241, 245, 249, 255)  # Slate 100 - nearly white
    stone_dark = (148, 163, 184, 255)  # Slate 400 - medium
    stone_border = (71, 85, 105, 255)  # Slate 600 - distinct dark border

    def paint(big: Image.Image) -> None:
        draw = ImageDraw.Draw(big, "RGBA")

        # Stone base (circular foundation)
        cx, cy = big.width // 2, big.height // 2
        radius = _si(28)

        # Distinct dark border (3px)
        border_width = _si(3)
        filled_ellipse(
            big,
            (cx - radius, cy - radius, cx + radius, cy + radius),
            fill=stone_border,
        )

        # Main stone body (very light)
        inner_radius = radius - border_width
        filled_ellipse(
            big,
            (
                cx - inner_radius,
                cy - inner_radius,
                cx + inner_radius,
                cy + inner_radius,
            ),
            fill=stone_base,
        )

        # Top-left highlight (nearly white for 3D effect)
        highlight_radius = inner_radius - _si(2)
        highlight_offset_x = -_si(4)
        highlight_offset_y = -_si(4)
        filled_ellipse(
            big,
            (
                cx + highlight_offset_x - highlight_radius // 2,
                cy + highlight_offset_y - highlight_radius // 2,
                cx + highlight_offset_x + highlight_radius // 2,
                cy + highlight_offset_y + highlight_radius // 2,
            ),
            fill=stone_light,
        )

        # Inner circle (foundation hole) - darker for depth
        hole_radius = _si(10)
        filled_ellipse(
            big,
            (cx - hole_radius, cy - hole_radius, cx + hole_radius, cy + hole_radius),
            fill=stone_dark,
        )
        # Inner hole shadow
        inner_hole = hole_radius - _si(2)
        filled_ellipse(
            big,
            (cx - inner_hole, cy - inner_hole, cx + inner_hole, cy + inner_hole),
            fill=darken(stone_dark, 0.3),
        )

    sprite = supersample_draw(64, 64, paint, factor=_SS)
    return apply_noise(sprite, amount=0.06, monochrome=True, seed=123)


# ===================================================================
# Enemy sprites (48x48 output)
# ===================================================================


def make_enemy_basic() -> Image.Image:
    """48x48 basic enemy — neon magenta circle with 2px white border."""

    def paint(big: Image.Image) -> None:
        cx, cy = big.width // 2, big.height // 2

        # 20% larger body radius (10 → 12)
        body_r = _si(12)

        # 2px white outline for maximum visibility
        outline_r = body_r + _si(2)
        filled_ellipse(
            big,
            (cx - outline_r, cy - outline_r, cx + outline_r, cy + outline_r),
            fill=ENEMY_OUTLINE,
        )

        # Outer body: radial gradient (brighter colors)
        radial_gradient(
            big,
            (cx, cy),
            body_r,
            stops=[
                (0.0, ENEMY_LIGHT),
                (0.5, ENEMY_PRIMARY),
                (1.0, ENEMY_DARK),
            ],
        )

        # Mask to ellipse
        mask = Image.new("L", big.size, 0)
        md = ImageDraw.Draw(mask)
        md.ellipse(
            (cx - body_r, cy - body_r, cx + body_r, cy + body_r),
            fill=255,
        )
        bg = Image.new("RGBA", big.size, (0, 0, 0, 0))
        result = Image.composite(big, bg, mask)
        big.paste(result, (0, 0))

        # Lighter inner core (not as dark)
        inner_r = _si(6)
        filled_ellipse(
            big,
            (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
            fill=ENEMY_PRIMARY,
        )

        # Larger, more visible eyes
        draw = ImageDraw.Draw(big, "RGBA")
        eye_r = _si(1.8)
        for ex in (cx - _si(3), cx + _si(3)):
            ey = cy - _si(2.5)
            filled_ellipse(
                big,
                (int(ex - eye_r), int(ey - eye_r), int(ex + eye_r), int(ey + eye_r)),
                fill=(255, 255, 255, 255),
            )
            # Pupils
            pupil_r = _si(0.8)
            filled_ellipse(
                big,
                (
                    int(ex - pupil_r),
                    int(ey - pupil_r),
                    int(ex + pupil_r),
                    int(ey + pupil_r),
                ),
                fill=(50, 50, 50, 255),
            )

        # Bottom shadow
        shadow_y = cy + body_r - _si(2)
        shadow_rx = _si(10)
        shadow_ry = _si(2)
        filled_ellipse(
            big,
            (cx - shadow_rx, shadow_y, cx + shadow_rx, shadow_y + shadow_ry),
            fill=(0, 0, 0, 40),
        )

    sprite = supersample_draw(48, 48, paint, factor=_SS)
    return apply_noise(sprite, amount=0.06, monochrome=True, seed=130)


def make_enemy_fast() -> Image.Image:
    """48x48 fast enemy — neon orange diamond with 2px white border and speed lines."""

    def paint(big: Image.Image) -> None:
        cx, cy = big.width // 2, big.height // 2

        # 20% larger diamond (10 → 12)
        outer_size = _si(12)

        # 2px white outline diamond
        outline_size = outer_size + _si(2)
        outline = [
            (cx - outline_size, cy),
            (cx, cy - outline_size),
            (cx + outline_size, cy),
            (cx, cy + outline_size),
        ]
        filled_polygon(big, outline, fill=ENEMY_FAST_OUTLINE)

        # Outer diamond (brighter orange)
        outer = [
            (cx - outer_size, cy),
            (cx, cy - outer_size),
            (cx + outer_size, cy),
            (cx, cy + outer_size),
        ]
        filled_polygon(big, outer, fill=ENEMY_FAST)

        # Inner diamond (lighter than before)
        inner_size = _si(6)
        inner = [
            (cx - inner_size, cy),
            (cx, cy - inner_size),
            (cx + inner_size, cy),
            (cx, cy + inner_size),
        ]
        filled_polygon(big, inner, fill=ENEMY_FAST_DARK)

        # Brighter speed lines behind (left side)
        draw = ImageDraw.Draw(big, "RGBA")
        for sy_off in (-_si(4), 0, _si(4)):
            y = cy + sy_off
            draw.line(
                [(cx - _si(16), int(y)), (cx - outer_size, int(y))],
                fill=adjust_alpha(ENEMY_FAST, 180),
                width=max(2, _si(1.2)),
            )

    sprite = supersample_draw(48, 48, paint, factor=_SS)
    return apply_noise(sprite, amount=0.05, monochrome=True, seed=131)


def make_enemy_tank() -> Image.Image:
    """48x48 tank enemy — neon red-pink armored square with 2px white border."""

    def paint(big: Image.Image) -> None:
        draw = ImageDraw.Draw(big, "RGBA")

        # 2px white outline
        outline_width = _si(2)
        draw.rectangle(
            (0, 0, big.width - 1, big.height - 1),
            fill=ENEMY_TANK_OUTLINE,
        )

        # Outer square body (20% larger - reduce inset)
        inset = outline_width

        # Outer square (brighter)
        draw.rectangle(
            (inset, inset, big.width - inset - 1, big.height - inset - 1),
            fill=ENEMY_TANK,
        )

        # Inner square (lighter than before)
        inner_inset = _si(4)
        draw.rectangle(
            (
                inner_inset,
                inner_inset,
                big.width - inner_inset - 1,
                big.height - inner_inset - 1,
            ),
            fill=ENEMY_TANK_DARK,
        )

        # Brighter cross armour pattern
        cx, cy = big.width // 2, big.height // 2
        cross_w = max(2, _si(2))
        cross_color = lighten(ENEMY_TANK, 0.2)
        draw.line(
            [(inner_inset, cy), (big.width - inner_inset, cy)],
            fill=cross_color,
            width=cross_w,
        )
        draw.line(
            [(cx, inner_inset), (cx, big.height - inner_inset)],
            fill=cross_color,
            width=cross_w,
        )

        # Larger, brighter corner rivets
        rivet_r = _si(1.8)
        rivet_color = lighten(ENEMY_TANK, 0.5)
        for rx, ry in [
            (inset + _si(3), inset + _si(3)),
            (big.width - inset - _si(3), inset + _si(3)),
            (inset + _si(3), big.height - inset - _si(3)),
            (big.width - inset - _si(3), big.height - inset - _si(3)),
        ]:
            filled_ellipse(
                big,
                (
                    int(rx - rivet_r),
                    int(ry - rivet_r),
                    int(rx + rivet_r),
                    int(ry + rivet_r),
                ),
                fill=rivet_color,
            )

    sprite = supersample_draw(48, 48, paint, factor=_SS)
    return apply_noise(sprite, amount=0.07, monochrome=True, seed=132)


# ===================================================================
# Projectiles (16x16 output)
# ===================================================================


def make_projectile_basic() -> Image.Image:
    """16x16 basic projectile — bright yellow glow dot."""

    def paint(big: Image.Image) -> None:
        cx, cy = big.width // 2, big.height // 2
        # Outer glow
        outer_r = _si(3.5)
        filled_ellipse(
            big,
            (cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r),
            fill=(253, 224, 71, 100),
        )
        # Core
        inner_r = _si(2)
        filled_ellipse(
            big,
            (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
            fill=PROJ_YELLOW,
        )

    return supersample_draw(16, 16, paint, factor=_SS)


def make_projectile_sniper() -> Image.Image:
    """16x16 sniper projectile — cyan bolt with trail."""

    def paint(big: Image.Image) -> None:
        draw = ImageDraw.Draw(big, "RGBA")
        cy = big.height // 2

        # Trail (fading left)
        trail_w = max(1, _si(1))
        draw.line(
            [(_si(0), cy), (_si(2), cy)],
            fill=adjust_alpha(PROJ_CYAN, 80),
            width=trail_w,
        )

        # Main bolt body
        bolt_w = max(2, _si(1.5))
        draw.line(
            [(_si(1), cy), (_si(6), cy)],
            fill=PROJ_CYAN,
            width=bolt_w,
        )

        # Bright tip
        tip_r = _si(1)
        filled_ellipse(
            big,
            (_si(6), cy - tip_r, _si(8), cy + tip_r),
            fill=(200, 255, 255, 255),
        )

    return supersample_draw(16, 16, paint, factor=_SS)


def make_projectile_splash() -> Image.Image:
    """16x16 splash projectile — orange ball with glow."""

    def paint(big: Image.Image) -> None:
        cx, cy = big.width // 2, big.height // 2
        # Outer glow
        outer_r = _si(3.5)
        filled_ellipse(
            big,
            (cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r),
            fill=(251, 146, 60, 80),
        )
        # Core
        inner_r = _si(2.5)
        filled_ellipse(
            big,
            (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
            fill=PROJ_ORANGE,
        )

    return supersample_draw(16, 16, paint, factor=_SS)


# ===================================================================
# Effects
# ===================================================================


def make_explosion() -> Image.Image:
    """32x32 explosion burst — orange/yellow radial with spikes."""

    def paint(big: Image.Image) -> None:
        cx, cy = big.width // 2, big.height // 2

        # Outer orange ring
        outer_r = _si(7)
        filled_ellipse(
            big,
            (cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r),
            fill=EXPLOSION_ORANGE,
        )
        # Mid yellow ring
        mid_r = _si(4.5)
        filled_ellipse(
            big,
            (cx - mid_r, cy - mid_r, cx + mid_r, cy + mid_r),
            fill=EXPLOSION_YELLOW,
        )
        # White core
        core_r = _si(2.5)
        filled_ellipse(
            big,
            (cx - core_r, cy - core_r, cx + core_r, cy + core_r),
            fill=(255, 255, 200, 255),
        )

        # Spike rays
        draw = ImageDraw.Draw(big, "RGBA")
        spike_color = (255, 200, 60, 160)
        for angle_deg in range(0, 360, 45):
            angle = math.radians(angle_deg)
            ex = cx + int(_s(7) * math.cos(angle))
            ey = cy + int(_s(7) * math.sin(angle))
            draw.line(
                [(cx, cy), (ex, ey)],
                fill=spike_color,
                width=max(1, _si(0.8)),
            )

    return supersample_draw(32, 32, paint, factor=_SS)


def make_range_indicator() -> Image.Image:
    """128x128 semi-transparent range circle — Sky 400 tones."""

    def paint(big: Image.Image) -> None:
        cx, cy = big.width // 2, big.height // 2
        r = _si(30)

        # Filled circle
        filled_ellipse(
            big,
            (cx - r, cy - r, cx + r, cy + r),
            fill=RANGE_COLOR,
        )
        # Border ring
        outlined_ellipse(
            big,
            (cx - r, cy - r, cx + r, cy + r),
            outline=RANGE_BORDER_COLOR,
            width=max(1, _si(1)),
        )

    return supersample_draw(128, 128, paint, factor=_SS)


# ===================================================================
# UI elements
# ===================================================================


def _make_button(
    w: int, h: int, base: Color, lighter: Color, darker: Color
) -> Image.Image:
    """Create a beveled button with gradient fill."""

    def paint(big: Image.Image) -> None:
        draw = ImageDraw.Draw(big, "RGBA")

        # Gradient fill
        linear_gradient(
            big,
            stops=[
                (0.0, lighter),
                (0.5, base),
                (1.0, darker),
            ],
            start=(0.0, 0.0),
            end=(0.0, 1.0),
        )

        # Bevel edges
        bw = max(1, _si(0.5))
        draw.line([(0, 0), (big.width - 1, 0)], fill=lighter, width=bw)
        draw.line([(0, 0), (0, big.height - 1)], fill=lighter, width=bw)
        draw.line(
            [(0, big.height - 1), (big.width - 1, big.height - 1)],
            fill=darker,
            width=bw,
        )
        draw.line(
            [(big.width - 1, 0), (big.width - 1, big.height - 1)],
            fill=darker,
            width=bw,
        )

    return supersample_draw(w, h, paint, factor=_SS)


def make_btn_normal() -> Image.Image:
    """160x64 button in normal/idle state."""
    return _make_button(
        160, 64, base=UI_MID, lighter=UI_LIGHT, darker=(20, 30, 45, 230)
    )


def make_btn_hover() -> Image.Image:
    """160x64 button in hover state."""
    return _make_button(
        160, 64, base=UI_LIGHT, lighter=(85, 100, 120, 230), darker=UI_MID
    )


def make_btn_pressed() -> Image.Image:
    """160x64 button in pressed state."""
    return _make_button(
        160, 64, base=UI_DARK, lighter=(20, 30, 45, 230), darker=UI_LIGHT
    )


def make_panel_bg() -> Image.Image:
    """240x400 dark UI panel with Slate border."""
    w, h = 240, 400

    def paint(big: Image.Image) -> None:
        draw = ImageDraw.Draw(big, "RGBA")
        draw.rectangle((0, 0, big.width - 1, big.height - 1), fill=UI_DARK)
        outlined_polygon(
            big,
            [
                (0, 0),
                (big.width - 1, 0),
                (big.width - 1, big.height - 1),
                (0, big.height - 1),
            ],
            outline=UI_BORDER,
            width=max(1, _si(0.5)),
        )
        # Top highlight
        draw.line(
            [(_si(0.5), _si(0.5)), (big.width - _si(1), _si(0.5))],
            fill=UI_MID,
            width=max(1, _si(0.5)),
        )

    return supersample_draw(w, h, paint, factor=_SS)


def make_health_bar_bg() -> Image.Image:
    """48x8 dark health bar background."""

    def paint(big: Image.Image) -> None:
        draw = ImageDraw.Draw(big, "RGBA")
        draw.rectangle((0, 0, big.width - 1, big.height - 1), fill=HEALTH_BG)
        draw.rectangle(
            (0, 0, big.width - 1, big.height - 1),
            outline=darken(HEALTH_BG, 0.3),
        )

    return supersample_draw(48, 8, paint, factor=_SS)


def make_health_bar_fill() -> Image.Image:
    """48x8 green health bar fill with gradient."""

    def paint(big: Image.Image) -> None:
        linear_gradient(
            big,
            stops=[
                (0.0, lighten(HEALTH_GREEN, 0.3)),
                (0.4, HEALTH_GREEN),
                (1.0, darken(HEALTH_GREEN, 0.2)),
            ],
            start=(0.0, 0.0),
            end=(0.0, 1.0),
        )
        # Top highlight
        draw = ImageDraw.Draw(big, "RGBA")
        draw.line(
            [(0, 0), (big.width - 1, 0)],
            fill=lighten(HEALTH_GREEN, 0.5),
            width=max(1, _si(0.5)),
        )

    return supersample_draw(48, 8, paint, factor=_SS)


def make_coin_icon() -> Image.Image:
    """32x32 gold coin icon."""

    def paint(big: Image.Image) -> None:
        draw = ImageDraw.Draw(big, "RGBA")
        cx, cy = big.width // 2, big.height // 2
        r = _si(7)

        # Coin body
        filled_ellipse(
            big,
            (cx - r, cy - r, cx + r, cy + r),
            fill=GOLD,
        )
        # Inner ring
        inner_r = _si(5)
        outlined_ellipse(
            big,
            (cx - inner_r, cy - inner_r, cx + inner_r, cy + inner_r),
            outline=GOLD_DARK,
            width=max(1, _si(0.8)),
        )
        # Dollar sign
        lw = max(1, _si(0.8))
        draw.line([(_si(8), _si(5)), (_si(8), _si(11))], fill=GOLD_DARK, width=lw)
        draw.line([(_si(6), _si(7)), (_si(10), _si(7))], fill=GOLD_DARK, width=lw)
        draw.line([(_si(6), _si(9)), (_si(10), _si(9))], fill=GOLD_DARK, width=lw)

    return supersample_draw(32, 32, paint, factor=_SS)


def make_heart_icon() -> Image.Image:
    """32x32 red heart icon."""

    def paint(big: Image.Image) -> None:
        cx, cy = big.width // 2, big.height // 2

        # Heart shape from two ellipses + triangle
        lobe_r = _si(4)
        left_cx = cx - _si(2.5)
        right_cx = cx + _si(2.5)
        lobe_y = cy - _si(2)

        filled_ellipse(
            big,
            (left_cx - lobe_r, lobe_y - lobe_r, left_cx + lobe_r, lobe_y + lobe_r),
            fill=HEART_RED,
        )
        filled_ellipse(
            big,
            (right_cx - lobe_r, lobe_y - lobe_r, right_cx + lobe_r, lobe_y + lobe_r),
            fill=HEART_RED,
        )
        # Bottom triangle
        filled_polygon(
            big,
            [
                (cx - _si(6.5), cy - _si(1)),
                (cx + _si(6.5), cy - _si(1)),
                (cx, cy + _si(6)),
            ],
            fill=HEART_RED,
        )
        # Darker lower portion
        filled_polygon(
            big,
            [
                (cx - _si(4), cy + _si(1)),
                (cx + _si(4), cy + _si(1)),
                (cx, cy + _si(6)),
            ],
            fill=HEART_DARK,
        )

        # Highlight gleam
        draw = ImageDraw.Draw(big, "RGBA")
        gleam_r = _si(1)
        filled_ellipse(
            big,
            (
                left_cx - gleam_r,
                lobe_y - _si(1) - gleam_r,
                left_cx + gleam_r,
                lobe_y - _si(1) + gleam_r,
            ),
            fill=(255, 150, 170, 200),
        )

    return supersample_draw(32, 32, paint, factor=_SS)


def make_wave_banner() -> Image.Image:
    """320x80 wave announcement banner background."""
    w, h = 320, 80

    def paint(big: Image.Image) -> None:
        # Gradient fill
        vertical_gradient(
            big,
            (40, 30, 60, 220),
            (20, 15, 40, 220),
        )

        # Outer border
        outlined_polygon(
            big,
            [
                (0, 0),
                (big.width - 1, 0),
                (big.width - 1, big.height - 1),
                (0, big.height - 1),
            ],
            outline=BANNER_BORDER,
            width=max(2, _si(1)),
        )
        # Inner border
        inset = _si(1.5)
        outlined_polygon(
            big,
            [
                (inset, inset),
                (big.width - inset - 1, inset),
                (big.width - inset - 1, big.height - inset - 1),
                (inset, big.height - inset - 1),
            ],
            outline=(180, 150, 40, 160),
            width=max(1, _si(0.5)),
        )

    return supersample_draw(w, h, paint, factor=_SS)


def make_hud_top_bar() -> Image.Image:
    """640x48 top HUD bar background."""
    w, h = 640, 48

    def paint(big: Image.Image) -> None:
        draw = ImageDraw.Draw(big, "RGBA")
        draw.rectangle((0, 0, big.width - 1, big.height - 1), fill=HUD_BG)
        draw.line(
            [(0, big.height - 1), (big.width - 1, big.height - 1)],
            fill=UI_BORDER,
            width=max(1, _si(0.5)),
        )

    return supersample_draw(w, h, paint, factor=_SS)


# ===================================================================
# Audio helpers -- generate minimal WAV files
# ===================================================================

_AUDIO_SAMPLE_RATE = 22050


def _write_wav(
    path: Path,
    samples: list[int],
    sample_rate: int = _AUDIO_SAMPLE_RATE,
) -> None:
    """Write 16-bit mono WAV from a list of signed 16-bit sample values."""
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = struct.pack(f"<{len(samples)}h", *samples)
        wf.writeframes(data)


def _sine_samples(freq: float, duration: float, volume: float = 0.5) -> list[int]:
    """Generate sine wave samples."""
    n = int(_AUDIO_SAMPLE_RATE * duration)
    amp = int(32767 * volume)
    return [
        int(amp * math.sin(2 * math.pi * freq * i / _AUDIO_SAMPLE_RATE))
        for i in range(n)
    ]


def _fade(samples: list[int], fade_in: int = 0, fade_out: int = 0) -> list[int]:
    """Apply linear fade-in and fade-out to samples."""
    result = list(samples)
    for i in range(min(fade_in, len(result))):
        result[i] = int(result[i] * i / fade_in)
    for i in range(min(fade_out, len(result))):
        idx = len(result) - 1 - i
        result[idx] = int(result[idx] * i / fade_out)
    return result


def generate_sfx_shoot(path: Path) -> None:
    """Short high-pitched click -- tower firing."""
    samples = _sine_samples(800, 0.06, volume=0.4)
    samples = _fade(samples, fade_out=len(samples) // 2)
    _write_wav(path, samples)


def generate_sfx_hit(path: Path) -> None:
    """Low thud -- projectile impact."""
    samples = _sine_samples(200, 0.1, volume=0.5)
    samples = _fade(samples, fade_out=len(samples) * 2 // 3)
    _write_wav(path, samples)


def generate_sfx_death(path: Path) -> None:
    """Descending tone -- enemy death."""
    n = int(_AUDIO_SAMPLE_RATE * 0.25)
    amp = int(32767 * 0.4)
    samples = []
    for i in range(n):
        t = i / _AUDIO_SAMPLE_RATE
        freq = 600 - 1800 * t
        samples.append(int(amp * math.sin(2 * math.pi * freq * t)))
    samples = _fade(samples, fade_in=100, fade_out=n // 2)
    _write_wav(path, samples)


def generate_sfx_wave(path: Path) -> None:
    """Rising alert tone -- new wave starting."""
    n = int(_AUDIO_SAMPLE_RATE * 0.3)
    amp = int(32767 * 0.35)
    samples = []
    for i in range(n):
        t = i / _AUDIO_SAMPLE_RATE
        freq = 400 + 1667 * t
        samples.append(int(amp * math.sin(2 * math.pi * freq * t)))
    samples = _fade(samples, fade_in=200, fade_out=n // 3)
    _write_wav(path, samples)


def generate_sfx_lose_life(path: Path) -> None:
    """Low warning buzz -- life lost."""
    n = int(_AUDIO_SAMPLE_RATE * 0.2)
    amp = int(32767 * 0.3)
    samples = []
    for i in range(n):
        t = i / _AUDIO_SAMPLE_RATE
        val = math.sin(2 * math.pi * 120 * t)
        samples.append(int(amp * (1 if val > 0 else -1)))
    samples = _fade(samples, fade_in=100, fade_out=n // 2)
    _write_wav(path, samples)


def generate_bgm_game(path: Path) -> None:
    """Short looping background music placeholder -- gentle arpeggio."""
    notes = [262, 330, 392, 523]  # C4, E4, G4, C5
    note_dur = 1.0
    all_samples: list[int] = []
    for freq in notes:
        samps = _sine_samples(freq, note_dur, volume=0.15)
        samps = _fade(samps, fade_in=500, fade_out=2000)
        all_samples.extend(samps)
    _write_wav(path, all_samples)


# Audio file manifest: (subdir, filename, generator_func)
AUDIO_MANIFEST: list[tuple[str, str, callable]] = [
    ("sounds", "sfx_shoot.wav", generate_sfx_shoot),
    ("sounds", "sfx_hit.wav", generate_sfx_hit),
    ("sounds", "sfx_death.wav", generate_sfx_death),
    ("sounds", "sfx_wave.wav", generate_sfx_wave),
    ("sounds", "sfx_lose_life.wav", generate_sfx_lose_life),
    ("music", "bgm_game.wav", generate_bgm_game),
]


# ===================================================================
# Manifest and batch generation
# ===================================================================

MANIFEST: list[tuple[str, callable]] = [
    # Terrain
    ("grass.png", make_grass),
    ("grass_0.png", make_grass_0),
    ("grass_1.png", make_grass_1),
    ("grass_2.png", make_grass_2),
    ("grass_3.png", make_grass_3),
    ("path_straight.png", make_path_straight),
    ("path_turn.png", make_path_turn),
    ("tree.png", make_tree),
    # Towers
    ("tower_basic.png", make_tower_basic),
    ("tower_sniper.png", make_tower_sniper),
    ("tower_splash.png", make_tower_splash),
    ("tower_slot.png", make_tower_slot),
    # Enemies
    ("enemy_basic.png", make_enemy_basic),
    ("enemy_fast.png", make_enemy_fast),
    ("enemy_tank.png", make_enemy_tank),
    # Projectiles
    ("projectile_basic.png", make_projectile_basic),
    ("projectile_sniper.png", make_projectile_sniper),
    ("projectile_splash.png", make_projectile_splash),
    # Effects
    ("explosion.png", make_explosion),
    ("range_indicator.png", make_range_indicator),
    # UI
    ("btn_normal.png", make_btn_normal),
    ("btn_hover.png", make_btn_hover),
    ("btn_pressed.png", make_btn_pressed),
    ("panel_bg.png", make_panel_bg),
    ("health_bar_bg.png", make_health_bar_bg),
    ("health_bar_fill.png", make_health_bar_fill),
    ("coin_icon.png", make_coin_icon),
    ("heart_icon.png", make_heart_icon),
    ("wave_banner.png", make_wave_banner),
    # HUD
    ("hud_top_bar.png", make_hud_top_bar),
]


def generate(output_dir: Path | None = None) -> List[Path]:
    """Generate all Tower Defense assets and save to *output_dir*.

    Image files go into ``<output_dir>/images/``, sound effects into
    ``<output_dir>/sounds/``, and music into ``<output_dir>/music/``.

    Args:
        output_dir: Asset base directory.  Defaults to
                    ``examples/tower_defense/assets/``.

    Returns:
        List of ``Path`` objects for every file written.
    """
    if output_dir is None:
        output_dir = Path(__file__).resolve().parent / "assets"

    images_dir = output_dir / "images"
    images_dir.mkdir(parents=True, exist_ok=True)

    written: List[Path] = []

    # --- Image assets ---
    for filename, factory in MANIFEST:
        img = factory()
        path = images_dir / filename
        img.save(path)
        print(f"  Created {path}")
        written.append(path)

    # --- Audio assets ---
    for subdir, filename, gen_func in AUDIO_MANIFEST:
        audio_dir = output_dir / subdir
        audio_dir.mkdir(parents=True, exist_ok=True)
        path = audio_dir / filename
        gen_func(path)
        print(f"  Created {path}")
        written.append(path)

    return written


def main() -> None:
    """Entry point for standalone execution."""
    print("=== Tower Defense Example Assets ===\n")
    files = generate()
    print(f"\n{'=' * 50}")
    print(f"Generated {len(files)} asset files.")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
