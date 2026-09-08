"""Original miniature map and battle pieces, drawn with Saga2D primitives.

Art belongs to the game. Nothing here knows the renderer or imports a
different reference game; all geometry uses Scene's drawing interface.
"""

import math
from pathlib import Path

from eador.style import BLUE, GOLD, INK, LINE, MUTED, RED, TEAL, TEXT
from eador.ui import icon_path

OWNERS = {"player": TEAL, "rival": RED, "neutral": (160, 160, 126, 255)}
IMAGES = Path(__file__).resolve().parent / 'assets' / 'images'


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


def backdrop(scene, width, height, *, title=False):
    """A shipped painting, cached by Assets; quiet enough for an atlas and its HUD."""
    with scene.screen_layer(0):
        scene.draw_image(str(IMAGES / 'shard-atmosphere.png'), 0, 0, width, height)
    if not title:
        with scene.screen_layer(1):
            scene.draw_rect(0, 0, width, height, (12, 22, 27, 155))


def ellipse(scene, x, y, rx, ry, color):
    """A shallow tabletop shadow or metal rim, using the ordinary shape renderer."""
    scene.draw_polygon([(x + math.cos(i * math.tau / 24) * rx,
                         y + math.sin(i * math.tau / 24) * ry) for i in range(24)], color)


def castle(scene, x, y, color, scale=1):
    ellipse(scene, x + 7 * scale, y + 8 * scale, 39 * scale, 13 * scale, (8, 18, 22, 130))
    stone, shadow = (188, 177, 145, 255), (105, 121, 115, 255)
    scene.draw_polygon([(x - 35 * scale, y + 6 * scale), (x - 26 * scale, y - 10 * scale),
                        (x + 26 * scale, y - 10 * scale), (x + 36 * scale, y + 8 * scale),
                        (x + 18 * scale, y + 14 * scale), (x - 23 * scale, y + 14 * scale)], shadow)
    for dx, rise in ((-20, 4), (0, -9), (20, 4)):
        xx, yy = x + dx * scale, y + rise * scale
        scene.draw_rect(xx - 8 * scale, yy - 27 * scale, 16 * scale, 30 * scale, stone)
        scene.draw_rect(xx + 2 * scale, yy - 27 * scale, 6 * scale, 30 * scale, shadow)
        for dy in (-20, -11, -2):
            scene.draw_line(xx - 8 * scale, yy + dy * scale, xx + 8 * scale, yy + dy * scale,
                            (125, 128, 111, 255), .6 * scale)
        scene.draw_line(xx - 8 * scale, yy - 26 * scale, xx - 8 * scale, yy + 2 * scale,
                        (224, 205, 159, 255), scale)
        scene.draw_polygon([(xx - 12 * scale, yy - 27 * scale), (xx, yy - 43 * scale),
                            (xx + 12 * scale, yy - 27 * scale)], shade(color, -40))
        scene.draw_polygon([(xx - 12 * scale, yy - 27 * scale), (xx, yy - 43 * scale),
                            (xx, yy - 27 * scale)], color)
        scene.draw_rect(xx - 2 * scale, yy - 19 * scale, 4 * scale, 9 * scale, INK)
        scene.draw_rect(xx - scale, yy - 18 * scale, scale, 6 * scale, GOLD)
    scene.draw_rect(x - 20 * scale, y - 12 * scale, 40 * scale, 17 * scale, (165, 164, 134, 255))
    scene.draw_rect(x - 7 * scale, y - 8 * scale, 14 * scale, 13 * scale, shadow, radius=5 * scale)
    scene.draw_rect(x - 5 * scale, y - 6 * scale, 10 * scale, 11 * scale, INK, radius=4 * scale)
    for dx in (-18, -10, 6, 14):
        scene.draw_rect(x + dx * scale, y - 15 * scale, 5 * scale, 6 * scale, stone)
    scene.draw_polygon([(x - 5 * scale, y + 5 * scale), (x + 5 * scale, y + 5 * scale),
                        (x + 10 * scale, y + 13 * scale), (x - 9 * scale, y + 13 * scale)], stone)
    scene.draw_line(x, y - 52 * scale, x, y - 74 * scale, GOLD, 1.5)
    scene.draw_polygon([(x, y - 74 * scale), (x + 20 * scale, y - 69 * scale),
                        (x, y - 63 * scale)], color)


def terrain_tile(scene, grid, pos, terrain, *, mode='ground', inset=.95):
    """Paint one prebuilt diorama below interactive shapes; picking stays on HexGrid."""
    terrain = {'swamp': 'marsh', 'mountain': 'mountains'}.get(terrain, terrain)
    variant = (pos[0] * 7 + pos[1] * 11) % 4
    x, y = grid.center(pos)
    scale = grid.size * inset / 150
    with scene.screen_layer(1):
        scene.draw_image(str(IMAGES / 'terrain' / f'{mode}-{terrain}-{variant}.png'),
                         x - 160 * scale, y - 160 * scale, 320 * scale, 352 * scale)


def province(scene, grid, pos, data, *, selected=False, hero=False, hover=False, name_label=True):
    """Draw a province; compact maps may lay out the complete name separately."""
    x, y = grid.center(pos)
    s = grid.size / 78
    points = grid.corners(pos)
    inner = [(x + (px - x) * .99, y + (py - y) * .99) for px, py in points]
    terrain_tile(scene, grid, pos, data.terrain, mode='ground' if data.capital else 'province', inset=.99)
    if hover:
        scene.draw_polygon(inner, (238, 220, 165, 27))
    if data.owner != 'neutral':
        outline(scene, inner, OWNERS[data.owner], 2)
    if selected:
        outline(scene, [(x + (px - x) * .92, y + (py - y) * .92) for px, py in points], GOLD, 2.5)
    if data.capital:
        castle(scene, x, y + 4 * s, OWNERS[data.owner], .83 * s)
    if data.site and not data.explored:
        sx, sy = x + 39 * s, y - 24 * s
        scene.draw_image(icon_path('explore'), sx - 11 * s, sy - 11 * s, 22 * s, 22 * s)
    if data.name and name_label:
        scene.draw_rect(x - 53 * s, y + 25 * s, 106 * s, 21 * s, (23, 37, 33, 218), radius=3)
        scene.draw_text(data.name, x, y + 35 * s, font_size=max(9, round(10 * s)), color=TEXT,
                        anchor_x="center", anchor_y="center")
    if hero:
        hx, hy = x - 40 * s, y - 29 * s
        banner = [(hx + dx * s, hy + dy * s) for dx, dy in
                  ((-17, -18), (17, -18), (17, 10), (0, 22), (-17, 10))]
        scene.draw_polygon(banner, INK)
        outline(scene, banner, TEAL, 1.5)
        scene.draw_image(icon_path('hero'), hx - 15 * s, hy - 16 * s, 30 * s, 30 * s)


def travel_arrow(scene, grid, origin, destination):
    """A short static direction cue across the selected journey's province edge."""
    x, y = grid.center(origin)
    end_x, end_y = grid.center(destination)
    dx, dy = end_x - x, end_y - y
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    start = x + dx * .40, y + dy * .40
    tip = x + dx * .68, y + dy * .68
    wings = [(tip[0] - ux * 7 + uy * side * 5, tip[1] - uy * 7 - ux * side * 5)
             for side in (-1, 1)]
    for color, width in ((INK, 5), (GOLD, 2)):
        scene.draw_line(*start, *tip, color, width)
        for wing in wings:
            scene.draw_line(*wing, *tip, color, width)


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
    """Paint a tabletop figure with upper-left light, inside the existing cell footprint.

    Broad equipment and material planes carry the role at retinue scale; fine
    face/armour details remain secondary. The base and tactical flags retain
    their established geometry. No image generation or state changes occur here.
    """
    s = scale
    color = TEAL if team == "player" else RED
    if spent:
        color = shade(color, -38)
    ellipse(scene, x + 5 * s, y + 15 * s, 27 * s, 11 * s, (6, 13, 18, 145))
    ellipse(scene, x, y + 12 * s, 23 * s, 10 * s, (42, 43, 36, 255))
    ellipse(scene, x, y + 8 * s, 23 * s, 10 * s, GOLD if selected else shade(color, -28))
    ellipse(scene, x, y + 7 * s, 19 * s, 7 * s, (31, 42, 40, 255))
    scene.draw_line(x - 15 * s, y + 13 * s, x + 4 * s, y + 15 * s,
                    GOLD if selected else color, 1.5 * s)
    lower = kind.lower()
    lower = {'acolyte': 'healer', 'mage': 'wizard', 'shaman': 'wizard', 'bow': 'archer'}.get(lower, lower)
    cloth = tuple(round(c * .60 + 18) for c in color[:3]) + (255,)
    metal, steel, metal_dark = (122, 143, 147, 255), (215, 225, 212, 255), (62, 79, 88, 255)
    wood, leather, brass = (111, 75, 46, 255), (139, 98, 60, 255), (187, 151, 88, 255)
    ivory, skin, edge = (233, 219, 181, 255), (205, 159, 117, 255), (26, 32, 32, 255)

    def poly(points, fill, *, rim=True):
        points = [(x + a * s, y + b * s) for a, b in points]
        scene.draw_polygon(points, fill)
        if rim:
            outline(scene, points, edge, 1.1 * s)

    def line(a, b, fill, width=1):
        scene.draw_line(x + a[0] * s, y + a[1] * s, x + b[0] * s, y + b[1] * s, fill, width * s)

    def circle(a, b, radius, fill):
        scene.draw_circle(x + a * s, y + b * s, radius * s, fill)

    def oval(a, b, rx, ry, fill):
        ellipse(scene, x + a * s, y + b * s, rx * s, ry * s, fill)

    def legs(spread=7):
        for direction in (-1, 1):
            d = direction
            poly([(d * 2, -3), (d * 9, -3), (d * (spread + 2), 9),
                  (d * (spread - 3), 10)], (95, 101, 94, 255))
            line((d * 5, 0), (d * spread, 8), (159, 164, 146, 255), 2)
            poly([(d * (spread - 4), 6), (d * (spread + 2), 6),
                  (d * (spread + 6), 12), (d * (spread - 4), 12)], shade(leather, -42))
            line((d * (spread - 3), 7), (d * (spread + 1), 7), leather, 1.5)

    def torso(coat=cloth, *, plate=False, broad=False):
        w = 16 if broad else 12
        poly([(-w, -17), (-8, -23), (7, -23), (w, -16), (w - 2, 4), (-w, 4)], shade(coat, -24))
        poly([(-w, -17), (-7, -22), (-1, -18), (-4, 3), (-w, 4)], shade(coat, 24), rim=False)
        poly([(2, -20), (7, -22), (w, -16), (w - 2, 4), (5, 2)], coat, rim=False)
        if plate:
            poly([(-11, -20), (9, -20), (12, -10), (7, -3), (-8, -3), (-13, -11)], metal)
            poly([(-11, -20), (-2, -18), (-4, -5), (-10, -7), (-13, -11)], steel, rim=False)
            poly([(1, -18), (9, -20), (12, -10), (7, -3), (2, -5)], metal_dark, rim=False)
            line((-8, -16), (7, -16), shade(metal, 28), 1)
            for dx in (-15, 13):
                poly([(dx - 4, -20), (dx + 3, -22), (dx + 5, -14), (dx - 4, -13)], metal)
                line((dx - 3, -19), (dx + 2, -20), steel, 1.5)
        else:
            line((-6, -17), (-8, -5), shade(coat, 40), 1.3)
            line((5, -17), (8, -7), shade(coat, -42), 1.5)
        line((-11, -2), (10, -2), shade(leather, -30), 3)
        poly([(-2, -4), (2, -4), (2, 0), (-2, 0)], brass, rim=False)

    def face(tone=skin, *, dx=0, dy=0):
        def shifted(points):
            return [(a + dx, b + dy) for a, b in points]
        poly(shifted([(-7, -30), (-3, -35), (4, -34), (8, -28), (6, -21), (-2, -19), (-7, -24)]), shade(tone, -34))
        poly(shifted([(-6, -30), (-3, -34), (2, -33), (2, -23), (-2, -20), (-6, -25)]), tone, rim=False)
        poly(shifted([(2, -30), (5, -28), (7, -25), (3, -25)]), shade(tone, 23), rim=False)
        line((dx - 3, dy - 28), (dx + 1, dy - 28), shade(tone, -72), 1)
        circle(dx + 4, dy - 28, .8, edge)
        line((dx, dy - 22), (dx + 4, dy - 22), shade(tone, -55), 1)

    def helmet(*, full=False, crest=False):
        poly([(-10, -29), (-9, -36), (-3, -40), (5, -39), (11, -32), (10, -27)], metal)
        poly([(-9, -35), (-3, -39), (0, -37), (-1, -30), (-10, -29)], steel, rim=False)
        poly([(2, -38), (5, -39), (11, -32), (10, -27), (4, -29)], metal_dark, rim=False)
        line((-12, -29), (12, -29), steel, 2)
        if full:
            poly([(-7, -29), (9, -29), (7, -20), (0, -17), (-7, -22)], metal)
            line((-5, -27), (6, -27), edge, 2.3)
            line((1, -24), (1, -20), metal_dark, 1.3)
        if crest:
            poly([(-3, -38), (-7, -44), (-3, -49), (3, -48), (7, -41), (3, -37)], color)
            line((-2, -46), (2, -42), shade(color, 42), 1.6)

    def shield(*, tower=False, wooden=False):
        points = [(-29, -25), (-7, -25), (-6, 4), (-17, 11), (-29, 4)] if tower else [(-25, -18), (-9, -18), (-10, -3), (-17, 4), (-25, -3)]
        fill = leather if wooden else shade(cloth, -5)
        poly(points, fill)
        poly([points[0], (-18, points[0][1] + 2), (-18, points[-2][1] - 2), points[-1]], shade(fill, 30), rim=False)
        outline(scene, [(x + a * s, y + b * s) for a, b in points], brass, 1.7 * s)
        if wooden:
            for xx in (-22, -17, -12):
                line((xx, -15), (xx, -3), shade(leather, -40), .9)
            circle(-17, -8, 3.4, metal_dark)
            circle(-18, -9, 2, steel)
        elif tower:
            for d, yy in ((1, -14), (-1, -3)):
                line((-18 - 6 * d, yy), (-18 + 6 * d, yy), ivory, 2)
                line((-18 + 2 * d, yy - 3), (-18 + 6 * d, yy), ivory, 2)
                line((-18 + 2 * d, yy + 3), (-18 + 6 * d, yy), ivory, 2)
        else:
            poly([(-17, -14), (-13, -9), (-17, -3), (-21, -9)], ivory, rim=False)

    def sword(*, heavy=False):
        width = 3.5 if heavy else 2.5
        poly([(19 - width, -8), (19 - width, -37), (19, -45), (19 + width, -37), (19 + width, -8)], metal)
        poly([(19 - width, -8), (19 - width, -37), (19, -45), (19, -8)], steel, rim=False)
        line((12, -9), (26, -9), brass, 3)
        line((19, -7), (19, 0), shade(leather, -28), 3)
        circle(19, 1, 2, brass)
        poly([(8, -17), (13, -18), (19, -11), (18, -5), (13, -8)], cloth)
        circle(18, -8, 2.5, skin)

    def bow(*, mobile=False):
        points = [(18, -38), (26, -28), (29, -14), (25, 0), (18, 7)]
        for a, b in zip(points, points[1:]):
            line(a, b, edge, 4)
            line(a, b, brass if mobile else leather, 2.4)
        line(points[0], points[-1], ivory, .9)
        line((4, -14), (24, -15), cloth, 5)
        circle(23, -15, 2.5, skin)
        line((2, -17), (31, -18), ivory, 1.1)
        poly([(30, -21), (35, -18), (30, -16)], steel, rim=False)

    if lower == 'wolf':
        fur, light, dark = (156, 165, 159, 255), (220, 218, 195, 255), (92, 107, 108, 255)
        poly([(-16, -12), (-29, -24), (-20, -24), (-9, -19)], dark)
        poly([(-29, -24), (-32, -33), (-20, -24)], dark)
        poly([(-29, -26), (-32, -33), (-25, -29), (-20, -23)], light, rim=False)
        for dx in (-13, -3, 10, 18):
            poly([(dx - 3, -5), (dx + 2, -4), (dx, 8), (dx - 5, 11), (dx - 7, 9)], dark)
            line((dx - 2, -2), (dx - 3, 7), fur, 2)
        poly([(-20, -12), (-12, -23), (9, -21), (20, -12), (13, 0), (-15, -2)], fur)
        poly([(-18, -6), (-8, -10), (13, -8), (13, 0), (-15, -2)], dark, rim=False)
        poly([(-14, -20), (-6, -24), (6, -22), (13, -14), (-3, -15)], light, rim=False)
        for dx in (-10, -3, 4):
            poly([(dx - 4, -19), (dx - 2, -26), (dx + 4, -20)], fur)
        poly([(7, -15), (7, -29), (13, -35), (21, -30), (28, -24), (26, -18), (17, -17)], fur)
        poly([(8, -29), (9, -40), (16, -32)], dark)
        poly([(16, -31), (20, -38), (23, -28)], dark)
        poly([(12, -27), (20, -29), (28, -24), (25, -21), (16, -23)], light, rim=False)
        circle(20, -28, 1.1, edge)
        circle(27, -24, 1.8, edge)
        line((20, -20), (25, -19), edge, 1.3)
        poly([(21, -20), (23, -20), (22, -17)], ivory, rim=False)
        line((8, -16), (16, -19), color, 3)
        return

    if lower == 'skyrider':
        feather = (182, 188, 169, 255)
        for d in (-1, 1):
            poly([(d * 3, -12), (d * 19, -31), (d * 37, -38), (d * 24, -4), (d * 12, 3)], shade(feather, -32))
            for tip, root in (((37, -38), (19, -10)), ((31, -28), (15, -4)), ((25, -18), (10, 0))):
                tx, ty = tip
                rx, ry = root
                poly([(d * (rx - 4), ry - 11), (d * tx, ty), (d * rx, ry)], feather)
                line((d * (rx - 2), ry - 10), (d * (tx - 3), ty + 2), ivory, 1.2)
        oval(1, -8, 12, 17, shade(feather, -40))
        poly([(-9, -8), (1, -13), (9, -4), (4, 6), (-7, 1)], feather)
        for dx in (-7, 0, 7):
            poly([(dx - 3, -2), (dx + 3, -2), (dx - 5, 13)], feather)
        poly([(5, -9), (8, -25), (16, -30), (22, -24), (22, -15), (13, -11)], ivory)
        poly([(20, -23), (30, -19), (22, -15)], brass)
        circle(17, -23, 1.1, edge)
        poly([(-10, -17), (-6, -32), (4, -32), (9, -17)], cloth)
        poly([(-7, -29), (-2, -31), (0, -20), (-8, -19)], metal, rim=False)
        line((-4, -17), (1, -2), metal_dark, 5)
        line((-3, -17), (2, -3), metal, 2)
        circle(-1, -37, 6, shade(skin, -35))
        circle(-3, -38, 4, skin)
        poly([(-8, -38), (-6, -44), (2, -46), (6, -39)], metal)
        line((-6, -40), (3, -41), steel, 1.4)
        line((8, -22), (22, -49), wood, 3)
        poly([(19, -48), (25, -56), (24, -45)], steel)
        return

    if lower in ('ranger', 'scout', 'brigand'):
        poly([(-7, -26), (-26, 4), (-9, 2), (12, -16)], shade(cloth, -34))
        poly([(-7, -26), (-22, 0), (-14, -3), (-4, -19)], shade(cloth, 10), rim=False)
    elif lower == 'commander':
        ochre = (172, 124, 57, 255)
        poly([(-10, -25), (-25, 7), (20, 7), (9, -25)], shade(ochre, -35))
        poly([(-10, -25), (-25, 7), (-13, 3), (-4, -23)], ochre, rim=False)
        line((-10, -22), (-19, 3), GOLD, 2)
    elif lower in ('warrior', 'swordsman'):
        poly([(-9, -23), (-23, 3), (-13, 7), (8, -20)], shade(cloth, -22))
        line((-11, -18), (-18, 1), color, 2)

    legs(14 if lower == 'ranger' else 8 if lower == 'goblin' else 7)
    if lower == 'guard':
        metal, steel, metal_dark = (76, 74, 97, 255), (164, 156, 173, 255), (44, 43, 62, 255)
    armored = lower in ('swordsman', 'warrior', 'warden', 'guard', 'commander', 'pikeman')
    torso((43, 60, 87, 255) if lower == 'wizard' else cloth, plate=armored, broad=lower in ('warden', 'guard'))

    if lower == 'goblin':
        green, dark = (157, 171, 101, 255), (85, 111, 66, 255)
        poly([(-11, -29), (-4, -36), (7, -34), (13, -24), (6, -18), (-8, -19)], dark)
        poly([(-10, -30), (-23, -34), (-12, -23)], green)
        poly([(8, -30), (22, -32), (12, -22)], green)
        poly([(-7, -31), (1, -34), (8, -30), (13, -24), (4, -23), (-5, -25)], green, rim=False)
        line((-5, -29), (1, -28), edge, 1.4)
        circle(6, -29, 1.2, ivory)
        circle(6, -29, .6, edge)
        poly([(5, -26), (15, -24), (7, -21)], shade(green, 23), rim=False)
        poly([(-2, -22), (0, -18), (2, -22)], ivory, rim=False)
        # The goblin's short ranged attack reads as a crude bow, not a sword.
        for a, b in (((18, -20), (25, -10)), ((25, -10), (18, 3))):
            line(a, b, wood, 3)
        line((18, -20), (18, 3), ivory, .9)
        line((8, -8), (28, -10), ivory, 1.2)
        poly([(27, -12), (32, -10), (27, -8)], metal, rim=False)
        return

    skin = {'warrior': (131, 87, 65, 255), 'commander': (156, 112, 83, 255),
            'scout': (177, 152, 105, 255), 'wizard': (218, 196, 171, 255),
            'adept': (164, 119, 87, 255), 'brigand': (191, 143, 100, 255)}.get(lower, skin)
    if lower not in ('guard', 'warden', 'healer', 'ranger', 'scout'):
        face(skin)

    if lower in ('archer', 'ranger', 'scout'):
        poly([(-18, -28), (-11, -25), (-10, -7), (-19, -10)], leather)
        for dx in (-18, -13):
            line((dx, -14), (dx - 2, -36), wood, 1.5)
            poly([(dx - 2, -37), (dx + 1, -32), (dx - 4, -32)], ivory, rim=False)
        if lower == 'archer':
            poly([(-11, -29), (-8, -35), (3, -40), (11, -31)], cloth)
            line((-12, -29), (12, -30), brass, 1.8)
            poly([(3, -38), (10, -43), (8, -34)], ivory, rim=False)
        else:
            dy = 3 if lower == 'ranger' else 0
            poly([(-11, -22 + dy), (-12, -34 + dy), (-3, -40 + dy), (8, -36 + dy), (12, -25 + dy), (8, -20 + dy)], shade(cloth, -20))
            face(skin, dy=dy)
            line((-9, -32 + dy), (-3, -37 + dy), shade(cloth, 40), 1.6)
            line((-9, -31 + dy), (-8, -23 + dy), shade(cloth, -20), 2.5)
            line((-7, -22 + dy), (7, -20 + dy), shade(cloth, -45), 3)
        line((-10, -17), (9, -4), leather, 2)
        bow(mobile=lower == 'ranger')
    elif lower == 'wizard':
        # Silver hair, long beard, dark robes and a grimoire match the portrait.
        poly([(-11, -17), (-19, 3), (14, 4), (8, -16)], (48, 66, 99, 255))
        line((-6, -13), (-11, 0), (109, 129, 158, 255), 2)
        line((8, -12), (11, 1), (27, 41, 64, 255), 2)
        poly([(-8, -29), (-6, -37), (3, -38), (8, -31), (7, -29)], (182, 190, 188, 255))
        line((-7, -29), (-7, -24), ivory, 2)
        poly([(-6, -25), (6, -24), (4, -12), (-1, -8), (-7, -17)], (177, 187, 186, 255))
        poly([(-6, -24), (-2, -22), (-3, -12), (-6, -17)], ivory, rim=False)
        line((20, 8), (20, -42), wood, 4)
        line((19, 5), (19, -41), brass, 1.2)
        circle(20, -45, 6, metal_dark)
        circle(19, -46, 4.2, BLUE)
        circle(17.5, -48, 1.3, ivory)
        poly([(-29, -17), (-15, -19), (-12, -3), (-27, -1)], shade(leather, -26))
        poly([(-26, -14), (-16, -15), (-14, -5), (-25, -3)], ivory, rim=False)
        line((-24, -10), (-17, -11), brass, 1)
    elif lower == 'healer':
        oval(0, -28, 11, 13, shade(cloth, -27))
        oval(-2, -29, 8, 10, ivory)
        face(skin)
        poly([(-10, -19), (-5, -19), (-1, 3), (-8, 3)], ivory)
        poly([(5, -19), (10, -18), (11, 3), (4, 3)], shade(ivory, -31))
        line((20, 8), (20, -34), wood, 4)
        line((19, 6), (19, -34), brass, 1.5)
        circle(20, -41, 8, brass)
        circle(20, -41, 5.5, edge)
        poly([(20, -45), (23, -41), (20, -37), (17, -41)], ivory, rim=False)
        poly([(-26, -13), (-15, -15), (-13, -3), (-25, -1)], leather)
        line((-23, -10), (-17, -11), ivory, 2)
    elif lower == 'sapper':
        poly([(-10, -19), (6, -19), (12, 4), (-13, 4)], leather)
        poly([(-10, -19), (-6, -19), (-8, 3), (-13, 4)], shade(leather, 34), rim=False)
        line((-8, -12), (7, -4), brass, 2)
        for dx in (-7, 2):
            poly([(dx, -7), (dx + 5, -7), (dx + 5, 0), (dx, 0)], shade(leather, -27))
        poly([(-13, -30), (-11, -37), (-3, -40), (6, -38), (10, -30)], brass)
        line((-15, -29), (12, -29), steel, 2.5)
        line((-9, -27), (8, -27), wood, 2)
        for dx in (-5, 3):
            circle(dx, -27, 3.6, edge)
            circle(dx - .5, -27.5, 2, BLUE)
        poly([(12, -9), (29, -9), (30, 8), (15, 10)], shade(leather, -28))
        poly([(14, -7), (20, -7), (21, 8), (15, 8)], brass, rim=False)
        line((13, -5), (29, -5), metal, 2)
        line((15, 5), (30, 5), metal, 2)
        line((23, -9), (23, -15), steel, 4)
        for dx, dy, radius in ((23, -21, 4), (19, -29, 5), (25, -38, 5.5)):
            circle(dx, dy, radius, (133, 151, 147, 255))
            circle(dx - 1.2, dy - 1.2, radius * .65, (191, 201, 187, 255))
    elif lower == 'adept':
        rune = (184, 165, 215, 255)
        poly([(-10, -20), (-18, 4), (14, 6), (10, -20)], shade(cloth, -15))
        line((-8, -17), (-1, 0), rune, 2)
        line((7, -16), (1, 0), brass, 2)
        poly([(-9, -29), (-9, -35), (1, -39), (10, -34), (10, -28)], shade(cloth, -15))
        line((-7, -32), (7, -32), brass, 2)
        poly([(-6, -25), (8, -25), (7, -19), (-4, -20)], rune)
        poly([(0, -53), (6, -47), (0, -41), (-6, -47)], shade(rune, -44))
        line((-4, -47), (0, -51), ivory, 1.3)
        poly([(-23, -24), (-11, -11), (-22, 1), (-32, -11)], rune)
        poly([(-23, -21), (-23, -2), (-29, -11)], shade(rune, 32), rim=False)
        line((-26, -11), (-19, -11), brass, 2)
        line((9, -14), (21, -22), cloth, 5)
        line((22, -16), (22, -28), skin, 4)
        for dx in (28, 34):
            line((dx, -28), (dx + 4, -22), rune, 1.5)
            line((dx + 4, -22), (dx, -16), rune, 1.5)
    elif lower == 'warden':
        helmet(full=True)
        shield(tower=True)
        poly([(12, -19), (19, -19), (27, -8), (21, -5), (15, -10)], metal)
        line((15, -17), (22, -10), steel, 2)
        poly([(22, -14), (28, -14), (29, -5), (22, -5)], metal)
        for dx in (23, 26):
            line((dx, -12), (dx, -19), steel, 2)
    elif lower == 'pikeman':
        helmet()
        line((8, 9), (24, -52), wood, 4)
        line((7, 8), (23, -52), brass, 1.3)
        poly([(20, -49), (26, -62), (28, -48)], metal)
        poly([(20, -49), (26, -62), (25, -48)], steel, rim=False)
        line((-12, -14), (15, -18), metal_dark, 6)
        line((-12, -15), (14, -19), metal, 3)
        circle(14, -18, 2.5, skin)
        line((5, -7), (12, -7), skin, 3)
    elif lower == 'brigand':
        poly([(-11, -26), (-9, -36), (0, -40), (10, -33), (11, -26)], shade(leather, -39))
        line((-8, -32), (-1, -37), leather, 2)
        poly([(-6, -30), (5, -30), (8, -25), (-6, -25)], skin)
        line((-4, -28), (-1, -28), edge, 1)
        circle(4, -28, .8, edge)
        poly([(-7, -25), (8, -25), (7, -18), (-5, -19)], shade(cloth, -42))
        poly([(17, -5), (20, -31), (27, -42), (26, -21), (21, -5)], metal)
        line((21, -30), (26, -38), steel, 1.7)
        line((15, -5), (24, -5), brass, 2)
        shield(wooden=True)
    elif lower == 'guard':
        helmet(full=True)
        for dx, direction in ((-9, -1), (8, 1)):
            poly([(dx, -34), (dx + direction * 8, -47), (dx + direction * 7, -37)], metal)
        line((-5, -27), (-1, -27), RED, 1.6)
        line((3, -27), (7, -27), RED, 1.6)
        shield()
        line((20, 7), (18, -42), wood, 4)
        poly([(18, -41), (28, -47), (32, -38), (25, -30), (18, -33)], metal)
        poly([(18, -41), (10, -47), (6, -37), (13, -30), (18, -33)], metal)
        line((28, -44), (30, -38), steel, 2)
        line((9, -43), (7, -37), steel, 2)
    elif lower == 'warrior':
        # The portrait's dark braided veteran wears plate without hiding her face.
        poly([(-8, -29), (-8, -36), (-3, -40), (5, -38), (8, -30)], (45, 37, 32, 255))
        for dx, dy in ((-7, -30), (-9, -26), (-10, -22), (-11, -18)):
            circle(dx, dy, 2.6, (46, 37, 31, 255))
            line((dx - 1, dy - 1), (dx + 1, dy), brass, .8)
        shield()
        sword(heavy=True)
    elif lower == 'commander':
        poly([(-8, -29), (-8, -35), (-1, -38), (6, -35), (9, -28)], (95, 100, 98, 255))
        line((-6, -34), (-1, -36), steel, 1.4)
        poly([(-5, -24), (6, -24), (5, -19), (0, -16), (-5, -20)], (94, 98, 91, 255))
        line((-3, -22), (0, -18), ivory, 1.1)
        sword()
        poly([(-22, -25), (-10, -23), (-12, -6), (-24, -4)], (175, 129, 65, 255))
        line((-20, -22), (-21, -7), GOLD, 2)
    else:
        helmet(crest=lower == 'swordsman')
        shield(wooden=lower == 'militia')
        if lower == 'militia':
            line((20, 8), (20, -44), wood, 3.5)
            line((19, 6), (19, -44), brass, 1)
            poly([(16, -43), (20, -54), (24, -43)], metal)
            poly([(16, -43), (20, -54), (20, -43)], steel, rim=False)
            poly([(20, -40), (29, -37), (20, -34)], color)
        else:
            sword()


def compass(scene, x, y):
    scene.draw_text("N", x, y - 37, font_size=11, color=MUTED, anchor_x="center")
    for angle in range(4):
        a = angle * math.pi / 2
        scene.draw_polygon([(x + math.sin(a) * 27, y - math.cos(a) * 27),
                            (x + math.sin(a + .5) * 8, y - math.cos(a + .5) * 8),
                            (x, y)], GOLD if angle % 2 == 0 else LINE)
