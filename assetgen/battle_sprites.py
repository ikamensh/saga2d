"""Generate 20 PNG sprite assets for the tactical battle vignette demo.

Each public ``make_*`` function returns a ``PIL.Image.Image`` (RGBA mode).
``generate(output_dir)`` saves all 20 files and returns the list of paths.

Filenames and sizes match the architecture contract::

    warrior_idle_01.png          64x64
    warrior_walk_{01..04}.png    64x64
    warrior_attack_{01..03}.png  64x64
    skeleton_idle_01.png         64x64
    skeleton_walk_{01..04}.png   64x64
    skeleton_hit_{01..03}.png    64x64
    skeleton_death_{01..03}.png  64x64
    select_ring.png              72x72

Run from project root::

    python -m assetgen.generate_all --battle
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import List, Tuple

from PIL import Image, ImageDraw

from assetgen.primitives import (
    filled_ellipse,
    filled_polygon,
    outlined_ellipse,
    outlined_polygon,
)
from assetgen.wireframe import (
    octahedron,
    render_wireframe,
    rotate_x,
    rotate_y,
    rotate_z,
)

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
BLUE = (30, 144, 255, 255)       # warrior body
BLUE_DARK = (15, 80, 160, 255)   # warrior shading / shield
BLUE_LIGHT = (80, 180, 255, 255) # warrior highlight
RED = (220, 20, 60, 255)         # skeleton body
RED_DARK = (140, 10, 30, 255)    # skeleton shading
WHITE = (255, 255, 255, 255)
YELLOW = (255, 255, 0, 255)      # select ring
GEM_CYAN = (0, 255, 220, 255)    # shield gem
BONE = (230, 220, 200, 255)      # skeleton bone colour
BONE_DARK = (180, 170, 150, 255)
SKULL_WHITE = (240, 235, 225, 255)
BLADE_SILVER = (200, 210, 220, 255)
BLADE_EDGE = (160, 170, 180, 255)

SIZE = (64, 64)  # all battle sprites are 64x64
CX, CY = 32, 32  # centre


# ===================================================================
# Internal drawing helpers
# ===================================================================

def _new() -> Image.Image:
    """Create a blank 64x64 RGBA canvas."""
    return Image.new("RGBA", SIZE, (0, 0, 0, 0))


def _draw_shield(img: Image.Image, cx: int, cy: int, size: int = 14) -> None:
    """Draw a small kite shield centred at (cx, cy)."""
    # Shield body — kite shape
    top = (cx, cy - size)
    left = (cx - size // 2, cy - size // 4)
    bottom = (cx, cy + size // 2)
    right = (cx + size // 2, cy - size // 4)
    filled_polygon(img, [top, right, bottom, left], fill=BLUE_DARK)
    outlined_polygon(img, [top, right, bottom, left], outline=BLUE_LIGHT, width=1)


def _draw_gem_wireframe(
    img: Image.Image,
    cx: float,
    cy: float,
    angle_index: int,
    gem_scale: float = 5.0,
) -> None:
    """Render a rotating octahedron wireframe as a shield gem.

    *angle_index* selects a distinct rotation angle so each frame looks
    different (0, 1, 2, ... give 45-degree increments).
    """
    verts, edges = octahedron()
    angle = angle_index * math.pi / 4  # 45 degree steps
    rotated = []
    for v in verts:
        v2 = rotate_x(v, angle * 0.7)
        v2 = rotate_y(v2, angle)
        v2 = rotate_z(v2, angle * 0.3)
        rotated.append(v2)
    render_wireframe(
        img,
        rotated,
        edges,
        color=GEM_CYAN,
        width=1,
        projection="orthographic",
        ortho_scale=1.0,
        center=(cx, cy),
        scale=gem_scale,
    )


def _draw_warrior_body(
    img: Image.Image,
    leg_offset: int = 0,
    arm_offset: float = 0.0,
) -> None:
    """Draw the warrior's body, legs, and arms.

    *leg_offset* is a signed pixel offset: positive = left leg forward,
    negative = right leg forward, 0 = neutral.
    *arm_offset* shifts arms vertically for attack poses.
    """
    draw = ImageDraw.Draw(img, "RGBA")

    # --- Legs ---
    left_foot_x = CX - 6 + leg_offset
    right_foot_x = CX + 6 - leg_offset
    # Thigh-to-foot lines
    draw.line([(CX - 4, 42), (left_foot_x, 58)], fill=BLUE_DARK, width=3)
    draw.line([(CX + 4, 42), (right_foot_x, 58)], fill=BLUE_DARK, width=3)
    # Feet
    draw.rectangle(
        (left_foot_x - 3, 56, left_foot_x + 3, 60),
        fill=BLUE_DARK,
    )
    draw.rectangle(
        (right_foot_x - 3, 56, right_foot_x + 3, 60),
        fill=BLUE_DARK,
    )

    # --- Torso (armour) ---
    torso_pts = [
        (CX - 10, 22),  # left shoulder
        (CX + 10, 22),  # right shoulder
        (CX + 8, 42),   # right hip
        (CX - 8, 42),   # left hip
    ]
    filled_polygon(img, torso_pts, fill=BLUE)
    outlined_polygon(img, torso_pts, outline=BLUE_LIGHT, width=1)

    # --- Arms ---
    arm_y = 26 + int(arm_offset)
    # Left arm (shield side)
    draw.line([(CX - 10, 24), (CX - 18, arm_y + 6)], fill=BLUE, width=3)
    # Right arm (weapon side)
    draw.line([(CX + 10, 24), (CX + 18, arm_y + 4)], fill=BLUE, width=3)

    # --- Head ---
    helmet_bbox = (CX - 7, 8, CX + 7, 22)
    filled_ellipse(img, helmet_bbox, fill=BLUE)
    # Visor slit
    draw.line([(CX - 4, 15), (CX + 4, 15)], fill=BLUE_DARK, width=1)


def _draw_warrior_shield_and_gem(
    img: Image.Image,
    gem_angle: int = 0,
) -> None:
    """Draw shield on the warrior's left arm with rotating gem."""
    _draw_shield(img, CX - 16, 30, size=11)
    _draw_gem_wireframe(img, CX - 16, 28, gem_angle, gem_scale=4.0)


def _draw_blade(
    img: Image.Image,
    extension: float = 0.0,
) -> None:
    """Draw the warrior's sword on the right side.

    *extension* 0.0 = resting, 1.0 = fully extended (thrust/swing).
    """
    draw = ImageDraw.Draw(img, "RGBA")
    # Blade extends from right hand
    hand_x, hand_y = CX + 18, 30
    blade_len = 10 + int(extension * 16)
    # Blade angle: resting = slightly down, extended = horizontal/forward
    angle = math.radians(60 - extension * 50)
    tip_x = hand_x + blade_len * math.cos(angle)
    tip_y = hand_y - blade_len * math.sin(angle)
    # Blade body
    draw.line([(hand_x, hand_y), (tip_x, tip_y)], fill=BLADE_SILVER, width=3)
    draw.line([(hand_x, hand_y), (tip_x, tip_y)], fill=BLADE_EDGE, width=1)
    # Crossguard
    draw.line(
        [(hand_x - 3, hand_y - 2), (hand_x + 3, hand_y + 2)],
        fill=BLUE_DARK,
        width=2,
    )


# ===================================================================
# Warrior sprites (8 images)
# ===================================================================

def make_warrior_idle() -> Image.Image:
    """Warrior idle frame — standing with shield and gem (angle 0)."""
    img = _new()
    _draw_warrior_body(img, leg_offset=0)
    _draw_warrior_shield_and_gem(img, gem_angle=0)
    _draw_blade(img, extension=0.0)
    return img


def make_warrior_walk(frame: int) -> Image.Image:
    """Warrior walk frame *frame* (1-4).

    Each frame has a distinct leg position and gem rotation.
    Frame 1: neutral, 2: left forward, 3: neutral-ish (slightly right),
    4: right forward — a clear 4-phase walk cycle.
    """
    img = _new()
    # Asymmetric offsets so all 4 frames are visually distinct
    leg_offsets = {1: 0, 2: 8, 3: 3, 4: -8}
    _draw_warrior_body(img, leg_offset=leg_offsets[frame])
    _draw_warrior_shield_and_gem(img, gem_angle=frame)
    _draw_blade(img, extension=0.0)
    return img


def make_warrior_attack(frame: int) -> Image.Image:
    """Warrior attack frame *frame* (1-3).

    Progressive blade extension: 1=windup, 2=mid-swing, 3=full thrust.
    """
    img = _new()
    extensions = {1: 0.2, 2: 0.6, 3: 1.0}
    arm_offsets = {1: -4, 2: -2, 3: 2}
    _draw_warrior_body(img, leg_offset=0, arm_offset=arm_offsets[frame])
    _draw_warrior_shield_and_gem(img, gem_angle=frame + 4)
    _draw_blade(img, extension=extensions[frame])
    return img


# ===================================================================
# Skeleton internal helpers
# ===================================================================

def _draw_skeleton_body(
    img: Image.Image,
    leg_offset: int = 0,
    body_alpha: int = 255,
    scatter: float = 0.0,
) -> None:
    """Draw the skeleton's diamond body, limbs, and skull.

    *leg_offset* — signed pixel offset for leg spread (positive = left forward).
    *body_alpha* — alpha for fade-out in death frames.
    *scatter*    — 0.0 = intact, 1.0 = fully scattered (death decomposition).
    """
    draw = ImageDraw.Draw(img, "RGBA")
    base_r, base_g, base_b = RED[:3]

    # Apply scatter offset to body parts
    scatter_dx = int(scatter * 6)
    scatter_dy = int(scatter * 4)

    # --- Skull (circle at top) ---
    skull_y_off = int(scatter * -8)
    skull_x_off = int(scatter * 3)
    skull_bbox = (
        CX - 9 + skull_x_off,
        6 + skull_y_off,
        CX + 9 + skull_x_off,
        24 + skull_y_off,
    )
    skull_color = (SKULL_WHITE[0], SKULL_WHITE[1], SKULL_WHITE[2], body_alpha)
    filled_ellipse(img, skull_bbox, fill=skull_color)
    # Eye sockets
    if body_alpha > 100:
        eye_a = min(body_alpha, 255)
        eye_color = (40, 0, 0, eye_a)
        sx = (skull_bbox[0] + skull_bbox[2]) // 2
        sy = (skull_bbox[1] + skull_bbox[3]) // 2
        draw.ellipse((sx - 6, sy - 3, sx - 2, sy + 1), fill=eye_color)
        draw.ellipse((sx + 2, sy - 3, sx + 6, sy + 1), fill=eye_color)
        # Jaw line
        jaw_color = (BONE_DARK[0], BONE_DARK[1], BONE_DARK[2], eye_a)
        draw.line([(sx - 4, sy + 4), (sx + 4, sy + 4)], fill=jaw_color, width=1)

    # --- Diamond torso (ribcage) ---
    body_color = (base_r, base_g, base_b, body_alpha)
    diamond_top = (CX + scatter_dx, 22 - scatter_dy)
    diamond_right = (CX + 12 + scatter_dx, 34)
    diamond_bottom = (CX + scatter_dx, 46 + scatter_dy)
    diamond_left = (CX - 12 + scatter_dx, 34)
    filled_polygon(
        img,
        [diamond_top, diamond_right, diamond_bottom, diamond_left],
        fill=body_color,
    )
    # Rib lines inside diamond
    if body_alpha > 80:
        rib_color = (BONE[0], BONE[1], BONE[2], min(body_alpha, 200))
        for ry in (28, 32, 36, 40):
            ry_adj = ry + scatter_dy // 2
            # Width narrows toward top and bottom of diamond
            dist_from_center = abs(ry_adj - 34)
            half_w = max(2, 10 - dist_from_center)
            draw.line(
                [(CX - half_w + scatter_dx, ry_adj),
                 (CX + half_w + scatter_dx, ry_adj)],
                fill=rib_color,
                width=1,
            )

    # --- Arms (bones) ---
    arm_color = (BONE[0], BONE[1], BONE[2], body_alpha)
    la_scatter = int(scatter * -8)
    ra_scatter = int(scatter * 10)
    draw.line(
        [(CX - 12 + scatter_dx, 28),
         (CX - 20 + la_scatter, 38 + scatter_dy)],
        fill=arm_color, width=2,
    )
    draw.line(
        [(CX + 12 + scatter_dx, 28),
         (CX + 20 + ra_scatter, 38 + scatter_dy)],
        fill=arm_color, width=2,
    )

    # --- Legs ---
    ll_scatter = int(scatter * -5)
    rl_scatter = int(scatter * 7)
    leg_color = (BONE[0], BONE[1], BONE[2], body_alpha)
    # Left leg
    draw.line(
        [(CX - 5 + scatter_dx, 44 + scatter_dy),
         (CX - 7 + leg_offset + ll_scatter, 58 + scatter_dy * 2)],
        fill=leg_color, width=2,
    )
    # Right leg
    draw.line(
        [(CX + 5 + scatter_dx, 44 + scatter_dy),
         (CX + 7 - leg_offset + rl_scatter, 58 + scatter_dy * 2)],
        fill=leg_color, width=2,
    )


# ===================================================================
# Skeleton sprites (11 images)
# ===================================================================

def make_skeleton_idle() -> Image.Image:
    """Skeleton idle frame — standing with diamond body and skull."""
    img = _new()
    _draw_skeleton_body(img, leg_offset=0)
    return img


def make_skeleton_walk(frame: int) -> Image.Image:
    """Skeleton walk frame *frame* (1-4).

    Each frame has a distinct leg stride position.
    Frame 1: neutral, 2: left forward, 3: slightly right, 4: right forward.
    """
    img = _new()
    # Asymmetric offsets so all 4 frames differ
    leg_offsets = {1: 0, 2: 7, 3: 3, 4: -7}
    _draw_skeleton_body(img, leg_offset=leg_offsets[frame])
    return img


def make_skeleton_hit(frame: int) -> Image.Image:
    """Skeleton hit frame *frame* (1-3).

    Alternates between white flash and red to show damage.
    Frame 1: white flash (centred), frame 2: red recoil, frame 3: white flash (shifted — recovery).
    """
    img = _new()

    if frame == 1:
        # White flash — full silhouette
        _draw_skeleton_body_flash(img, flash_color=WHITE)
    elif frame == 2:
        # Red recoil — skeleton with slight leg shift
        _draw_skeleton_body(img, leg_offset=3)
        # Red tint overlay on body area
        overlay = Image.new("RGBA", SIZE, (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay, "RGBA")
        od.rectangle((CX - 14, 6, CX + 14, 60), fill=(255, 0, 0, 60))
        img = Image.alpha_composite(img, overlay)
    else:
        # Frame 3: recovery flash — shifted silhouette to distinguish from frame 1
        _draw_skeleton_body_flash(img, flash_color=WHITE, x_shift=3, y_shift=2)
    return img


def _draw_skeleton_body_flash(
    img: Image.Image,
    flash_color: Tuple[int, int, int, int] = WHITE,
    x_shift: int = 0,
    y_shift: int = 0,
) -> None:
    """Draw skeleton silhouette in a single flat colour (hit flash effect).

    *x_shift* / *y_shift* offset the whole silhouette (for recovery frames).
    """
    draw = ImageDraw.Draw(img, "RGBA")
    fc = flash_color
    dx, dy = x_shift, y_shift

    # Skull
    filled_ellipse(
        img, (CX - 9 + dx, 6 + dy, CX + 9 + dx, 24 + dy), fill=fc,
    )

    # Diamond torso
    filled_polygon(
        img,
        [(CX + dx, 22 + dy), (CX + 12 + dx, 34 + dy),
         (CX + dx, 46 + dy), (CX - 12 + dx, 34 + dy)],
        fill=fc,
    )

    # Arms
    draw.line([(CX - 12 + dx, 28 + dy), (CX - 20 + dx, 38 + dy)], fill=fc, width=3)
    draw.line([(CX + 12 + dx, 28 + dy), (CX + 20 + dx, 38 + dy)], fill=fc, width=3)

    # Legs
    draw.line([(CX - 5 + dx, 44 + dy), (CX - 7 + dx, 58 + dy)], fill=fc, width=3)
    draw.line([(CX + 5 + dx, 44 + dy), (CX + 7 + dx, 58 + dy)], fill=fc, width=3)


def make_skeleton_death(frame: int) -> Image.Image:
    """Skeleton death frame *frame* (1-3).

    Progressive decomposition: body scatters outward and fades.
    Frame 1: intact (full alpha), frame 2: scattering (alpha 170),
    frame 3: scattered fragments (alpha 85).
    """
    img = _new()
    alphas = {1: 255, 2: 170, 3: 85}
    scatters = {1: 0.0, 2: 0.4, 3: 1.0}
    _draw_skeleton_body(
        img,
        leg_offset=0,
        body_alpha=alphas[frame],
        scatter=scatters[frame],
    )
    return img


# ===================================================================
# Select ring
# ===================================================================

def make_select_ring() -> Image.Image:
    """Yellow elliptical selection ring — 72x72 transparent with yellow outline."""
    img = Image.new("RGBA", (72, 72), (0, 0, 0, 0))
    # Elliptical ring (wider than tall to suggest ground plane)
    outlined_ellipse(img, (4, 16, 67, 55), outline=YELLOW, width=4)
    return img


# ===================================================================
# generate() — save all 20 PNGs
# ===================================================================

def generate(output_dir: Path) -> List[Path]:
    """Create all 20 battle-vignette sprite PNGs in *output_dir*.

    Returns a list of the written file paths.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    written: List[Path] = []

    def _save(img: Image.Image, name: str) -> None:
        path = output_dir / name
        img.save(path)
        print(f"Created {path}")
        written.append(path)

    # --- Warrior (8 files) ---
    _save(make_warrior_idle(), "warrior_idle_01.png")

    for i in range(1, 5):
        _save(make_warrior_walk(i), f"warrior_walk_{i:02d}.png")

    for i in range(1, 4):
        _save(make_warrior_attack(i), f"warrior_attack_{i:02d}.png")

    # --- Skeleton (12 files) ---
    _save(make_skeleton_idle(), "skeleton_idle_01.png")

    for i in range(1, 5):
        _save(make_skeleton_walk(i), f"skeleton_walk_{i:02d}.png")

    for i in range(1, 4):
        _save(make_skeleton_hit(i), f"skeleton_hit_{i:02d}.png")

    for i in range(1, 4):
        _save(make_skeleton_death(i), f"skeleton_death_{i:02d}.png")

    # --- Select ring (1 file) ---
    _save(make_select_ring(), "select_ring.png")

    return written
