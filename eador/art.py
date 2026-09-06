"""Original miniature map and battle pieces, drawn with Saga2D primitives.

Art belongs to the game. Nothing here knows the renderer or imports a
different reference game; all geometry uses Scene's drawing interface.
"""

import math
import random

from eador.style import BLUE, GOLD, INK, LINE, MUTED, RED, TEAL, TEXT

TERRAINS = {
    "plains": (103, 121, 83, 255), "forest": (67, 102, 82, 255),
    "hills": (134, 122, 87, 255), "swamp": (73, 100, 99, 255),
    "marsh": (73, 100, 99, 255),
    "mountain": (112, 125, 131, 255), "mountains": (112, 125, 131, 255),
    "water": (58, 96, 120, 255),
}
OWNERS = {"player": TEAL, "rival": RED, "neutral": (160, 160, 126, 255)}


def shade(color, amount):
    return tuple(max(0, min(255, c + amount)) for c in color[:3]) + (255,)


def outline(scene, points, color, width=1):
    for a, b in zip(points, points[1:] + points[:1]):
        scene.draw_line(*a, *b, color, width)


def relic(scene, x, y, kind, *, scale=1):
    """Draw an original relic medallion in a 60 × 60 square about its center.

    The object silhouette identifies the item independently of its accent color.
    Scale .8 fits equipment rows; scale 1 fits reward headings. All shapes use
    the owning Scene's current drawing layer and need no image assets.
    """
    if kind not in ('wayfarer_boots', 'oak_standard', 'ember_lens', 'moonstone',
                    'iron_crown', 'merchant_seal', 'watch_bell', 'storm_quiver',
                    'veil_censer', 'porter_rune', 'mirror_badge', 'vanguard_drum'):
        raise ValueError(f'Unknown relic artwork: {kind}')
    if not math.isfinite(scale) or scale <= 0:
        raise ValueError('Relic scale must be finite and positive.')

    def poly(points, color):
        scene.draw_polygon([(x + a * scale, y + b * scale) for a, b in points], color)

    def line(a, b, color, width=2):
        scene.draw_line(x + a[0] * scale, y + a[1] * scale,
                        x + b[0] * scale, y + b[1] * scale, color, width * scale)

    def circle(a, b, radius, color):
        scene.draw_circle(x + a * scale, y + b * scale, radius * scale, color)

    circle(0, 1, 28, INK)
    rim = [(x + math.cos(i * math.tau / 32) * 27 * scale,
            y + math.sin(i * math.tau / 32) * 27 * scale) for i in range(32)]
    outline(scene, rim, LINE, scale)
    bronze, ivory, violet = (171, 132, 76, 255), (226, 218, 184, 255), (170, 145, 199, 255)

    if kind == 'wayfarer_boots':
        for dx, dy in ((-11, -3), (5, 3)):
            poly([(dx - 5, dy - 15), (dx + 5, dy - 15), (dx + 4, dy + 4),
                  (dx + 11, dy + 9), (dx + 10, dy + 15), (dx - 6, dy + 15)], bronze)
            line((dx - 5, dy - 11), (dx + 5, dy - 11), GOLD, 3)
            line((dx - 6, dy + 14), (dx + 10, dy + 14), ivory, 2)
            line((dx, dy - 4), (dx + 4, dy - 2), INK, 2)
    elif kind == 'oak_standard':
        line((-13, -20), (-13, 21), bronze, 3)
        circle(-13, -21, 3, GOLD)
        poly([(-11, -17), (17, -17), (14, -1), (18, 14), (3, 8), (-11, 14)], TEAL)
        poly([(1, -12), (6, -8), (4, -5), (10, -3), (8, 2), (2, 5), (-4, 1), (-5, -4)], ivory)
        line((2, -8), (2, 9), bronze, 1.5)
    elif kind == 'ember_lens':
        poly([(0, -20), (19, 13), (-19, 13)], bronze)
        poly([(0, -14), (12, 9), (-12, 9)], RED)
        poly([(0, -14), (0, 9), (-12, 9)], GOLD)
        line((-23, -4), (-8, -4), ivory, 2)
        for dy in (-8, 0, 8):
            line((12, 2), (23, 2 + dy), RED if dy else GOLD, 2)
        line((-10, 18), (10, 18), bronze, 3)
    elif kind == 'moonstone':
        poly([(0, -22), (17, -9), (16, 12), (0, 23), (-17, 10), (-17, -9)], violet)
        poly([(0, -22), (0, 23), (-17, 10), (-17, -9)], BLUE)
        circle(1, 0, 12, ivory)
        circle(6, -4, 10, violet)
        circle(-7, -14, 2, TEXT)
    elif kind == 'iron_crown':
        poly([(-20, -13), (-10, -3), (0, -20), (10, -3), (20, -13), (15, 14), (-15, 14)], bronze)
        poly([(-15, 10), (15, 10), (14, 18), (-14, 18)], GOLD)
        poly([(0, -8), (5, 0), (0, 7), (-5, 0)], RED)
        for dx in (-20, 0, 20):
            circle(dx, -20 if dx == 0 else -13, 2, ivory)
    elif kind == 'merchant_seal':
        poly([(-17, -21), (14, -21), (20, -15), (20, 12), (-17, 12)], ivory)
        poly([(14, -21), (14, -15), (20, -15)], bronze)
        for yy in (-12, -6):
            line((-10, yy), (9, yy), bronze, 1.5)
        poly([(-8, 8), (0, 10), (-3, 24), (-8, 19), (-13, 21)], RED)
        poly([(2, 10), (10, 8), (15, 20), (9, 18), (6, 24)], RED)
        circle(1, 8, 11, bronze)
        circle(1, 8, 8, GOLD)
        line((-3, 8), (5, 8), INK, 2)
        line((1, 4), (1, 12), INK, 2)
    elif kind == 'watch_bell':
        circle(0, -17, 6, GOLD)
        circle(0, -17, 3, INK)
        poly([(-3, -13), (3, -13), (12, -5), (14, 10), (20, 16), (-20, 16), (-14, 10), (-12, -5)], bronze)
        poly([(-3, -10), (2, -10), (4, 11), (-10, 11), (-8, -3)], GOLD)
        line((-20, 16), (20, 16), ivory, 3)
        circle(0, 20, 4, GOLD)
    elif kind == 'storm_quiver':
        for dx, dy in ((-7, -3), (0, 0), (7, -4)):
            line((dx, dy - 18), (dx - 5, 13), ivory, 2)
            poly([(dx, dy - 24), (dx + 4, dy - 17), (dx, dy - 19), (dx - 4, dy - 17)], BLUE)
        poly([(-13, -5), (10, -1), (6, 21), (-12, 18)], bronze)
        line((-13, -5), (10, -1), GOLD, 3)
        poly([(-2, 1), (-7, 9), (-2, 8), (-4, 16), (4, 6), (-1, 7)], BLUE)
    elif kind == 'veil_censer':
        circle(0, -20, 4, bronze)
        line((-3, -17), (-15, 5), GOLD, 1.5)
        line((3, -17), (15, 5), GOLD, 1.5)
        for dx, dy, radius in ((-1, -9, 5), (5, -5, 6), (0, 1, 7)):
            circle(dx, dy, radius, MUTED)
        poly([(-19, 5), (19, 5), (12, 18), (0, 22), (-12, 18)], bronze)
        line((-19, 5), (19, 5), GOLD, 3)
        for dx in (-8, 0, 8):
            circle(dx, 12, 2, INK)
    elif kind == 'porter_rune':
        poly([(-15, -21), (12, -23), (20, -8), (16, 20), (-12, 23), (-20, 8)], MUTED)
        poly([(-15, -21), (-8, -15), (-11, 13), (-12, 23), (-20, 8)], bronze)
        # An open doorway and outward stroke suggest displacement, not flight.
        line((-5, 12), (-5, -11), INK, 4)
        line((-5, -11), (8, -11), INK, 4)
        line((8, -11), (8, -3), INK, 4)
        line((-1, 4), (15, 4), GOLD, 3)
        line((9, -2), (15, 4), GOLD, 3)
        line((15, 4), (9, 10), GOLD, 3)
    elif kind == 'mirror_badge':
        poly([(0, -22), (14, -12), (14, 12), (0, 22), (-14, 12), (-14, -12)], bronze)
        poly([(0, -17), (9, -9), (9, 9), (0, 17), (-9, 9), (-9, -9)], BLUE)
        line((-5, 7), (5, -7), ivory, 2)
        line((-22, -6), (-15, -12), TEAL, 2)
        line((-22, -6), (-15, 0), TEAL, 2)
        line((22, 6), (15, 0), TEAL, 2)
        line((22, 6), (15, 12), TEAL, 2)
    else:  # vanguard_drum
        poly([(-17, -5), (17, -5), (17, 16), (0, 23), (-17, 16)], RED)
        for dx in (-15, -5, 5):
            line((dx, -3), (dx + 7, 17), ivory, 1.5)
            line((dx + 7, -3), (dx, 17), ivory, 1.5)
        poly([(-18, -5), (-10, -10), (10, -10), (18, -5), (10, 1), (-10, 1)], GOLD)
        line((-17, 16), (0, 23), bronze, 3)
        line((0, 23), (17, 16), bronze, 3)
        line((-15, -20), (10, -8), bronze, 3)
        line((15, -20), (-10, -8), bronze, 3)
        circle(-15, -20, 3, ivory)
        circle(15, -20, 3, ivory)


def seal(scene, grid, pos, *, label=True):
    """An engraved objective with a distinct ring and name, also visible without color."""
    x, y = grid.center(pos)
    outline(scene, grid.corners(pos), GOLD, 3)
    scene.draw_circle(x, y, grid.size * .34, INK)
    ring = [(x + math.cos(i * math.tau / 24) * grid.size * .34,
             y + math.sin(i * math.tau / 24) * grid.size * .34) for i in range(24)]
    outline(scene, ring, GOLD, 2)
    if label:
        scene.text("SEAL" if grid.size >= 30 else "S", x, y - 6, size=8, color=GOLD, center=True)


def exit_marker(scene, grid, pos, number, *, label=True):
    """A numbered doorway remains distinguishable from the seal without color."""
    x, y = grid.center(pos)
    outline(scene, grid.corners(pos), TEAL, 3)
    size = grid.size
    left, top = x - size * .30, y - size * .40
    scene.draw_line(left, y + size * .24, left, top, TEAL, width=2)
    scene.draw_line(left, top, x + size * .30, top, TEAL, width=2)
    scene.draw_line(x + size * .30, top, x + size * .30, y + size * .24, TEAL, width=2)
    if label:
        scene.text(f'EXIT {number}' if size >= 30 else str(number), x, y + size * .34,
                   size=8 if size >= 30 else 7, color=TEAL, center=True)


def backdrop(scene, width, height):
    """Quiet star field and engraved orbit lines around the floating shard."""
    rng = random.Random(918)
    for _ in range(100):
        x, y = rng.randrange(24, width - 24), rng.randrange(100, height - 50)
        scene.draw_circle(x, y, rng.choice((0.7, 0.8, 1.2)), (85, 113, 119, rng.randrange(60, 150)))
    cx, cy = width * .49, height * .49
    for radius in (height * .35, height * .43):
        points = [(cx + math.cos(i * math.tau / 96) * radius * 1.12,
                   cy + math.sin(i * math.tau / 96) * radius) for i in range(96)]
        outline(scene, points, (39, 56, 61, 255))


def tree(scene, x, y, scale=1):
    scene.draw_line(x, y, x, y - 13 * scale, (68, 60, 41, 255), 3 * scale)
    for dy, w in ((4, 12), (11, 10), (18, 7)):
        scene.draw_polygon([(x - w * scale, y - dy * scale), (x, y - (dy + 17) * scale),
                            (x + w * scale, y - dy * scale)], (34, 65 + dy, 56, 255))
        scene.draw_polygon([(x, y - dy * scale), (x, y - (dy + 17) * scale),
                            (x + w * scale, y - dy * scale)], (56, 88 + dy, 67, 255))


def mountain(scene, x, y, scale=1):
    scene.draw_polygon([(x - 23 * scale, y), (x - 3 * scale, y - 40 * scale),
                        (x + 25 * scale, y)], (84, 92, 84, 255))
    scene.draw_polygon([(x - 3 * scale, y - 40 * scale), (x + 6 * scale, y),
                        (x + 25 * scale, y)], (164, 166, 139, 255))
    scene.draw_polygon([(x - 10 * scale, y - 26 * scale), (x - 3 * scale, y - 40 * scale),
                        (x + 7 * scale, y - 26 * scale), (x - 1 * scale, y - 29 * scale)], TEXT)


def castle(scene, x, y, color, scale=1):
    scene.draw_circle(x, y + 5 * scale, 27 * scale, (22, 32, 29, 70))
    for dx, rise in ((-20, 4), (0, -9), (20, 4)):
        xx, yy = x + dx * scale, y + rise * scale
        scene.draw_rect(xx - 8 * scale, yy - 27 * scale, 16 * scale, 30 * scale, (185, 181, 151, 255))
        scene.draw_rect(xx + 2 * scale, yy - 27 * scale, 6 * scale, 30 * scale, (118, 126, 117, 255))
        scene.draw_polygon([(xx - 12 * scale, yy - 27 * scale), (xx, yy - 43 * scale),
                            (xx + 12 * scale, yy - 27 * scale)], color)
        scene.draw_rect(xx - 2 * scale, yy - 19 * scale, 4 * scale, 9 * scale, INK)
    scene.draw_rect(x - 20 * scale, y - 12 * scale, 40 * scale, 17 * scale, (165, 164, 134, 255))
    scene.draw_rect(x - 5 * scale, y - 6 * scale, 10 * scale, 11 * scale, INK)
    scene.draw_line(x, y - 52 * scale, x, y - 74 * scale, GOLD, 1.5)
    scene.draw_polygon([(x, y - 74 * scale), (x + 20 * scale, y - 69 * scale),
                        (x, y - 63 * scale)], color)


def village(scene, x, y, scale=1):
    for dx, dy in ((-10, 2), (7, -5), (14, 8)):
        xx, yy = x + dx * scale, y + dy * scale
        scene.draw_rect(xx - 7 * scale, yy - 10 * scale, 14 * scale, 13 * scale, (199, 184, 135, 255))
        scene.draw_polygon([(xx - 10 * scale, yy - 10 * scale), (xx, yy - 21 * scale),
                            (xx + 10 * scale, yy - 10 * scale)], (104, 77, 55, 255))
        scene.draw_rect(xx - 2 * scale, yy - 4 * scale, 4 * scale, 7 * scale, (57, 69, 56, 255))


def terrain_detail(scene, terrain, x, y, seed, scale=1):
    rng = random.Random(seed)
    if terrain == "forest":
        for dx, dy in ((-29, 0), (20, -8), (32, 7), (-15, 10), (2, 5)):
            tree(scene, x + dx * scale, y + dy * scale, .75 * scale)
    elif terrain in ("hills", "mountain", "mountains"):
        mountain(scene, x - 15 * scale, y + 9 * scale, .8 * scale)
        mountain(scene, x + 17 * scale, y + 13 * scale, .65 * scale)
    elif terrain in ("swamp", "marsh", "water"):
        for _ in range(7):
            dx, dy = rng.randrange(-35, 26) * scale, rng.randrange(-17, 18) * scale
            scene.draw_line(x + dx, y + dy, x + dx + 14 * scale, y + dy, (109, 152, 144, 255), 2)
    else:
        for _ in range(12):
            dx, dy = rng.randrange(-40, 40) * scale, rng.randrange(-17, 23) * scale
            scene.draw_line(x + dx, y + dy, x + dx + 3 * scale, y + dy - 5 * scale,
                            (167, 169, 106, 255), 1)
        village(scene, x, y + 6 * scale, .8 * scale)


def province(scene, grid, pos, data, *, selected=False, hero=False, hover=False, name_label=True):
    """Draw a province; compact maps may lay out the complete name separately."""
    x, y = grid.center(pos)
    s = grid.size / 78
    points = grid.corners(pos)
    inner = [(x + (px - x) * .963, y + (py - y) * .963) for px, py in points]
    base = TERRAINS[data.terrain]
    under = [(px, py + 13 * s) for px, py in inner]
    scene.draw_polygon(under, shade(base, -46))
    scene.draw_polygon(inner, shade(base, 9 if hover else 0))
    # Each cell has slight relief, engraved seams, and its own small landscape.
    scene.draw_polygon([inner[0], inner[1], (x, y), inner[-1]], shade(base, 8))
    outline(scene, inner, OWNERS[data.owner] if data.owner != "neutral" else shade(base, 24),
            2 if data.owner != "neutral" else 1)
    if selected:
        outline(scene, [(x + (px - x) * .92, y + (py - y) * .92) for px, py in points], GOLD, 2.5)
    if data.capital:
        castle(scene, x, y + 4 * s, OWNERS[data.owner], .83 * s)
    else:
        terrain_detail(scene, data.terrain, x, y - 7 * s, pos[0] * 991 + pos[1] * 41, s)
    if data.site and not data.explored:
        scene.draw_circle(x + 39 * s, y - 24 * s, 9 * s, INK)
        scene.draw_text("?", x + 39 * s, y - 24 * s, color=GOLD, font_size=12,
                        anchor_x="center", anchor_y="center")
    if data.name and name_label:
        scene.draw_rect(x - 53 * s, y + 25 * s, 106 * s, 21 * s, (23, 37, 33, 218), radius=3)
        scene.draw_text(data.name, x, y + 35 * s, font_size=max(9, round(10 * s)), color=TEXT,
                        anchor_x="center", anchor_y="center")
    if hero:
        scene.draw_circle(x - 40 * s, y - 29 * s, 16 * s, INK)
        scene.draw_circle(x - 40 * s, y - 29 * s, 13 * s, TEAL)
        scene.draw_polygon([(x - 40 * s, y - 39 * s), (x - 47 * s, y - 25 * s),
                            (x - 33 * s, y - 25 * s)], INK)


def expedition(scene, grid, pos, troops):
    """A numbered diamond distinguishes the moving army from province ownership."""
    x, y = grid.center(pos)
    scale = grid.size / 78
    x, y = x - 40 * scale, y - 29 * scale
    points = [(x, y - 19 * scale), (x + 19 * scale, y),
              (x, y + 19 * scale), (x - 19 * scale, y)]
    scene.draw_polygon(points, INK)
    outline(scene, points, RED, 2)
    scene.draw_text(str(troops), x, y, font_size=12, color=RED,
                    anchor_x="center", anchor_y="center")


def piece(scene, x, y, kind, team, *, scale=1, selected=False, spent=False):
    """Role silhouettes stay distinct at battle and smaller retinue scales."""
    s = scale
    color = TEAL if team == "player" else RED
    if spent:
        color = shade(color, -38)
    scene.draw_circle(x, y + 14 * s, 22 * s, (11, 21, 25, 140))
    scene.draw_circle(x, y + 10 * s, 21 * s, GOLD if selected else shade(color, -26))
    scene.draw_circle(x, y + 7 * s, 18 * s, INK)
    lower = kind.lower()
    if lower == "wolf":
        fur = (177, 184, 174, 255)
        scene.draw_polygon([(x - 18 * s, y - 7 * s), (x - 10 * s, y - 20 * s),
                            (x + 11 * s, y - 18 * s), (x + 20 * s, y - 7 * s),
                            (x + 10 * s, y), (x - 12 * s, y)], fur)
        for dx in (-12, -4, 8, 15):
            scene.draw_line(x + dx * s, y - 2 * s, x + (dx - 2) * s, y + 10 * s, fur, 3 * s)
        scene.draw_polygon([(x + 7 * s, y - 14 * s), (x + 11 * s, y - 34 * s),
                            (x + 17 * s, y - 27 * s), (x + 26 * s, y - 21 * s),
                            (x + 22 * s, y - 15 * s)], (207, 211, 193, 255))
        scene.draw_line(x - 14 * s, y - 12 * s, x - 26 * s, y - 24 * s, fur, 5 * s)
        scene.draw_circle(x + 18 * s, y - 23 * s, 1.5 * s, INK)
        return
    if lower == "sapper":
        # A low work helmet, apron, side canister and curling plume read as a
        # field engineer rather than another sword-and-shield infantry piece.
        leather = (170, 133, 87, 255)
        scene.draw_rect(x - 17 * s, y - 21 * s, 28 * s, 25 * s, color, radius=4 * s)
        for dx in (-8, 7):
            scene.draw_line(x + dx * s, y, x + dx * s, y + 12 * s, TEXT, 5 * s)
        scene.draw_polygon([(x - 10 * s, y - 18 * s), (x + 6 * s, y - 18 * s),
                            (x + 10 * s, y + 5 * s), (x - 14 * s, y + 5 * s)], leather)
        scene.draw_line(x - 12 * s, y - 15 * s, x + 7 * s, y - 5 * s, GOLD, 2 * s)
        scene.draw_circle(x - 3 * s, y - 27 * s, 9 * s, TEXT)
        scene.draw_rect(x - 16 * s, y - 36 * s, 26 * s, 8 * s, color, radius=3 * s)
        scene.draw_line(x - 19 * s, y - 28 * s, x + 13 * s, y - 28 * s, GOLD, 3 * s)
        for dx in (-7, 1):
            scene.draw_circle(x + dx * s, y - 26 * s, 3.5 * s, INK)
            scene.draw_circle(x + dx * s, y - 26 * s, 1.5 * s, BLUE)
        scene.draw_line(x + 7 * s, y - 14 * s, x + 20 * s, y - 6 * s, color, 6 * s)
        scene.draw_rect(x + 14 * s, y - 10 * s, 17 * s, 22 * s, shade(leather, -28), radius=4 * s)
        outline(scene, [(x + 14 * s, y - 7 * s), (x + 31 * s, y - 7 * s),
                        (x + 31 * s, y + 9 * s), (x + 14 * s, y + 9 * s)], GOLD, 2 * s)
        scene.draw_rect(x + 18 * s, y - 15 * s, 9 * s, 6 * s, TEXT)
        for dx, dy, radius in ((22, -21, 4), (18, -28, 5), (24, -36, 6)):
            scene.draw_circle(x + dx * s, y + dy * s, radius * s, (159, 173, 170, 255))
        return
    if lower == "adept":
        # No wizard hat or healer staff: a diamond tablet, floating rune and
        # extended palm give the Adept a compact, directional silhouette.
        rune = (192, 170, 222, 255)
        scene.draw_polygon([(x - 7 * s, y - 19 * s), (x - 17 * s, y + 9 * s),
                            (x, y + 3 * s), (x + 15 * s, y + 10 * s),
                            (x + 8 * s, y - 19 * s)], color)
        scene.draw_line(x - 6 * s, y - 16 * s, x, y + 1 * s, rune, 3 * s)
        scene.draw_line(x + 6 * s, y - 16 * s, x, y + 1 * s, rune, 3 * s)
        scene.draw_circle(x, y - 26 * s, 8 * s, TEXT)
        scene.draw_polygon([(x - 9 * s, y - 27 * s), (x - 7 * s, y - 36 * s),
                            (x + 7 * s, y - 36 * s), (x + 9 * s, y - 27 * s)], shade(color, -18))
        scene.draw_line(x - 5 * s, y - 29 * s, x + 5 * s, y - 29 * s, GOLD, 2 * s)
        outline(scene, [(x, y - 49 * s), (x + 6 * s, y - 43 * s),
                        (x, y - 37 * s), (x - 6 * s, y - 43 * s)], rune, 2 * s)
        scene.draw_polygon([(x - 20 * s, y - 23 * s), (x - 10 * s, y - 9 * s),
                            (x - 19 * s, y + 3 * s), (x - 28 * s, y - 10 * s)], shade(rune, -32))
        outline(scene, [(x - 20 * s, y - 23 * s), (x - 10 * s, y - 9 * s),
                        (x - 19 * s, y + 3 * s), (x - 28 * s, y - 10 * s)], GOLD, 2 * s)
        scene.draw_line(x + 8 * s, y - 13 * s, x + 20 * s, y - 21 * s, color, 5 * s)
        scene.draw_line(x + 22 * s, y - 14 * s, x + 22 * s, y - 28 * s, TEXT, 4 * s)
        for dx in (28, 34):
            scene.draw_line(x + dx * s, y - 28 * s, x + (dx + 4) * s, y - 21 * s, rune, 2 * s)
            scene.draw_line(x + (dx + 4) * s, y - 21 * s, x + dx * s, y - 14 * s, rune, 2 * s)
        return
    if lower == "skyrider":
        # A rider on an outstretched bird makes flight visible even when the
        # piece shrinks to a retinue slot; no mounted unit shares these wings.
        feather = (192, 197, 183, 255)
        for direction in (-1, 1):
            wing = [(x + direction * dx * s, y + dy * s) for dx, dy in
                    ((3, -12), (21, -33), (37, -38), (29, -17), (22, -3), (12, 3))]
            scene.draw_polygon(wing, feather)
            for dx, dy in ((14, -13), (21, -20), (28, -27)):
                scene.draw_line(x + direction * dx * s, y + dy * s,
                                x + direction * (dx + 2) * s, y + (dy + 11) * s, INK, 2 * s)
        scene.draw_polygon([(x - 7 * s, y - 16 * s), (x + 11 * s, y - 17 * s),
                            (x + 15 * s, y - 4 * s), (x + 4 * s, y + 8 * s),
                            (x - 13 * s, y + 2 * s)], shade(feather, -26))
        scene.draw_polygon([(x - 5 * s, y), (x - 16 * s, y + 13 * s),
                            (x - 3 * s, y + 8 * s), (x + 5 * s, y + 11 * s)], feather)
        scene.draw_circle(x + 13 * s, y - 15 * s, 7 * s, TEXT)
        scene.draw_polygon([(x + 18 * s, y - 18 * s), (x + 28 * s, y - 14 * s),
                            (x + 20 * s, y - 10 * s)], GOLD)
        scene.draw_circle(x + 15 * s, y - 17 * s, 1.5 * s, INK)
        scene.draw_polygon([(x - 8 * s, y - 15 * s), (x - 6 * s, y - 29 * s),
                            (x + 4 * s, y - 29 * s), (x + 9 * s, y - 13 * s)], color)
        scene.draw_line(x + 1 * s, y - 14 * s, x - 1 * s, y - 1 * s, color, 5 * s)
        scene.draw_circle(x - 1 * s, y - 34 * s, 6 * s, TEXT)
        scene.draw_polygon([(x - 8 * s, y - 35 * s), (x - 1 * s, y - 44 * s),
                            (x + 6 * s, y - 35 * s)], color)
        scene.draw_line(x + 7 * s, y - 22 * s, x + 20 * s, y - 44 * s, GOLD, 2 * s)
        scene.draw_polygon([(x + 17 * s, y - 43 * s), (x + 25 * s, y - 51 * s),
                            (x + 22 * s, y - 39 * s)], TEXT)
        return
    if lower == "ranger":
        # A low hood, trailing cloak and wide stride distinguish mobile fire
        # from the Archer's upright pose and pointed cap.
        scene.draw_polygon([(x - 5 * s, y - 28 * s), (x - 26 * s, y + 3 * s),
                            (x - 8 * s, y), (x + 8 * s, y - 17 * s)], shade(color, -24))
        scene.draw_line(x - 3 * s, y - 1 * s, x - 15 * s, y + 12 * s, GOLD, 5 * s)
        scene.draw_line(x + 5 * s, y - 1 * s, x + 14 * s, y + 10 * s, GOLD, 5 * s)
        scene.draw_polygon([(x - 10 * s, y + 1 * s), (x - 6 * s, y - 20 * s),
                            (x + 8 * s, y - 22 * s), (x + 13 * s, y - 2 * s)], color)
        scene.draw_polygon([(x - 10 * s, y - 20 * s), (x - 8 * s, y - 32 * s),
                            (x + 1 * s, y - 38 * s), (x + 11 * s, y - 31 * s),
                            (x + 13 * s, y - 19 * s)], color)
        scene.draw_polygon([(x - 3 * s, y - 29 * s), (x + 7 * s, y - 30 * s),
                            (x + 9 * s, y - 20 * s), (x - 3 * s, y - 21 * s)], INK)
        scene.draw_line(x + 1 * s, y - 27 * s, x + 7 * s, y - 27 * s, TEXT, 2 * s)
        bow = [(x + 17 * s, y - 36 * s), (x + 25 * s, y - 27 * s),
               (x + 28 * s, y - 13 * s), (x + 25 * s, y), (x + 20 * s, y + 6 * s)]
        for a, b in zip(bow, bow[1:]):
            scene.draw_line(*a, *b, GOLD, 3 * s)
        scene.draw_line(*bow[0], *bow[-1], TEXT, s)
        scene.draw_line(x + 5 * s, y - 12 * s, x + 26 * s, y - 14 * s, color, 4 * s)
        scene.draw_line(x + 7 * s, y - 17 * s, x + 32 * s, y - 19 * s, TEXT, 1.5 * s)
        scene.draw_polygon([(x + 32 * s, y - 22 * s), (x + 37 * s, y - 19 * s),
                            (x + 32 * s, y - 16 * s)], TEXT)
        return
    if lower == "warden":
        # Broad armor, a tower shield and an open gauntlet read as extraction,
        # rather than the Swordsman's narrow shield and raised blade.
        scene.draw_polygon([(x - 16 * s, y - 21 * s), (x + 14 * s, y - 21 * s),
                            (x + 17 * s, y + 5 * s), (x - 14 * s, y + 5 * s)], color)
        for dx in (-7, 10):
            scene.draw_line(x + dx * s, y + 1 * s, x + dx * s, y + 13 * s, TEXT, 6 * s)
        scene.draw_polygon([(x - 10 * s, y - 25 * s), (x - 9 * s, y - 35 * s),
                            (x, y - 40 * s), (x + 10 * s, y - 35 * s),
                            (x + 11 * s, y - 25 * s)], TEXT)
        scene.draw_rect(x - 6 * s, y - 30 * s, 13 * s, 4 * s, INK)
        scene.draw_line(x + 13 * s, y - 15 * s, x + 25 * s, y - 5 * s, color, 7 * s)
        scene.draw_rect(x + 22 * s, y - 12 * s, 7 * s, 10 * s, TEXT)
        scene.draw_line(x + 24 * s, y - 13 * s, x + 24 * s, y - 17 * s, TEXT, 3 * s)
        shield = [(x - 29 * s, y - 25 * s), (x - 3 * s, y - 25 * s),
                  (x, y + 8 * s), (x - 15 * s, y + 16 * s), (x - 29 * s, y + 8 * s)]
        scene.draw_polygon(shield, shade(color, -20))
        outline(scene, shield, GOLD, 2.5 * s)
        for direction, yy in ((1, -12), (-1, 0)):
            end = x + (-15 + 7 * direction) * s
            scene.draw_line(x + (-15 - 7 * direction) * s, y + yy * s, end, y + yy * s, TEXT, 2.5 * s)
            scene.draw_line(end - 4 * direction * s, y + (yy - 4) * s, end, y + yy * s, TEXT, 2.5 * s)
            scene.draw_line(end - 4 * direction * s, y + (yy + 4) * s, end, y + yy * s, TEXT, 2.5 * s)
        return
    if lower == "commander":
        scene.draw_polygon([(x - 11 * s, y - 21 * s), (x - 23 * s, y + 6 * s),
                            (x + 19 * s, y + 7 * s), (x + 8 * s, y - 21 * s)], GOLD)
    armor = (82, 77, 97, 255) if lower == "guard" else color
    scene.draw_polygon([(x - 13 * s, y + 4 * s), (x - 7 * s, y - 20 * s),
                        (x + 7 * s, y - 20 * s), (x + 13 * s, y + 4 * s)], armor)
    scene.draw_line(x - 5 * s, y + 3 * s, x - 7 * s, y + 12 * s, (209, 207, 174, 255), 4 * s)
    scene.draw_line(x + 5 * s, y + 3 * s, x + 7 * s, y + 12 * s, (209, 207, 174, 255), 4 * s)
    skin = (145, 176, 92, 255) if lower == "goblin" else (220, 199, 157, 255)
    scene.draw_circle(x, y - 24 * s, 8 * s, skin)
    if lower == "goblin":
        scene.draw_polygon([(x - 7 * s, y - 29 * s), (x - 19 * s, y - 32 * s), (x - 7 * s, y - 21 * s)], skin)
        scene.draw_polygon([(x + 7 * s, y - 29 * s), (x + 19 * s, y - 32 * s), (x + 7 * s, y - 21 * s)], skin)
    if any(name in lower for name in ("archer", "scout", "bow")):
        outline(scene, [(x + 13 * s, y - 28 * s), (x + 24 * s, y - 11 * s),
                        (x + 13 * s, y + 5 * s)], GOLD, 2 * s)
        scene.draw_line(x + 13 * s, y - 28 * s, x + 13 * s, y + 5 * s, TEXT, 1)
        scene.draw_polygon([(x - 10 * s, y - 24 * s), (x, y - 38 * s), (x + 10 * s, y - 24 * s)], color)
    elif lower in ("healer", "acolyte"):
        # Rounded vestments and a ring staff distinguish support from a wizard.
        scene.draw_circle(x, y - 25 * s, 11 * s, color)
        scene.draw_circle(x, y - 24 * s, 6 * s, skin)
        scene.draw_line(x - 6 * s, y - 17 * s, x - 3 * s, y + 1 * s, TEXT, 3 * s)
        scene.draw_line(x + 6 * s, y - 17 * s, x + 3 * s, y + 1 * s, TEXT, 3 * s)
        scene.draw_line(x + 18 * s, y + 7 * s, x + 18 * s, y - 32 * s, GOLD, 3 * s)
        scene.draw_circle(x + 18 * s, y - 37 * s, 8 * s, GOLD)
        scene.draw_circle(x + 18 * s, y - 37 * s, 5 * s, INK)
        scene.draw_polygon([(x + 18 * s, y - 41 * s), (x + 21 * s, y - 37 * s),
                            (x + 18 * s, y - 33 * s), (x + 15 * s, y - 37 * s)], TEXT)
    elif any(name in lower for name in ("mage", "wizard", "shaman")):
        scene.draw_line(x + 17 * s, y + 7 * s, x + 17 * s, y - 38 * s, GOLD, 3 * s)
        scene.draw_circle(x + 17 * s, y - 39 * s, 6 * s, BLUE)
        scene.draw_polygon([(x - 11 * s, y - 28 * s), (x + 1 * s, y - 48 * s),
                            (x + 9 * s, y - 28 * s)], color)
    elif lower == "pikeman":
        # A long angled pike and broad helmet distinguish the defensive recruit.
        scene.draw_rect(x - 10 * s, y - 33 * s, 20 * s, 9 * s, (187, 198, 184, 255))
        scene.draw_line(x - 13 * s, y - 25 * s, x + 13 * s, y - 25 * s, TEXT, 2 * s)
        scene.draw_line(x + 8 * s, y + 9 * s, x + 23 * s, y - 51 * s, (194, 159, 102, 255), 3 * s)
        scene.draw_polygon([(x + 17 * s, y - 48 * s), (x + 26 * s, y - 61 * s),
                            (x + 25 * s, y - 45 * s)], TEXT)
        scene.draw_line(x - 13 * s, y - 12 * s, x + 15 * s, y - 16 * s, color, 4 * s)
    else:
        if lower != "goblin":
            helmet = (111, 117, 129, 255) if lower == "guard" else (187, 198, 184, 255)
            scene.draw_rect(x - 9 * s, y - 32 * s, 18 * s, 9 * s, helmet)
        scene.draw_line(x + 19 * s, y - 2 * s, x + 19 * s, y - 42 * s, TEXT, 3 * s)
        scene.draw_line(x + 13 * s, y - 9 * s, x + 25 * s, y - 9 * s, GOLD, 3 * s)
        scene.draw_polygon([(x - 24 * s, y - 17 * s), (x - 9 * s, y - 17 * s),
                            (x - 10 * s, y - 1 * s), (x - 17 * s, y + 5 * s),
                            (x - 24 * s, y - 1 * s)], color)
        scene.draw_line(x - 17 * s, y - 14 * s, x - 17 * s, y, GOLD, 2)
        if lower in ("commander", "guard"):
            scene.draw_polygon([(x - 9 * s, y - 31 * s), (x - 11 * s, y - 42 * s),
                                (x - 3 * s, y - 36 * s), (x, y - 43 * s),
                                (x + 3 * s, y - 36 * s), (x + 11 * s, y - 42 * s),
                                (x + 9 * s, y - 31 * s)], GOLD if lower == "commander" else RED)
        elif lower in ("swordsman", "warrior"):
            scene.draw_rect(x - 3 * s, y - 42 * s, 6 * s, 13 * s, color)
        elif lower == "militia":
            scene.draw_line(x + 19 * s, y - 3 * s, x + 19 * s, y - 45 * s, (194, 159, 102, 255), 2 * s)
            scene.draw_polygon([(x + 15 * s, y - 40 * s), (x + 19 * s, y - 51 * s),
                                (x + 23 * s, y - 40 * s)], TEXT)


def compass(scene, x, y):
    scene.draw_text("N", x, y - 37, font_size=11, color=MUTED, anchor_x="center")
    for angle in range(4):
        a = angle * math.pi / 2
        scene.draw_polygon([(x + math.sin(a) * 27, y - math.cos(a) * 27),
                            (x + math.sin(a + .5) * 8, y - math.cos(a + .5) * 8),
                            (x, y)], GOLD if angle % 2 == 0 else LINE)
