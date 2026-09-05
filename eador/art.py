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


def province(scene, grid, pos, data, *, selected=False, hero=False, hover=False):
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
    if data.name:
        scene.draw_rect(x - 53 * s, y + 25 * s, 106 * s, 21 * s, (23, 37, 33, 218), radius=3)
        scene.draw_text(data.name, x, y + 35 * s, font_size=max(9, round(10 * s)), color=TEXT,
                        anchor_x="center", anchor_y="center")
    if hero:
        scene.draw_circle(x - 40 * s, y - 29 * s, 16 * s, INK)
        scene.draw_circle(x - 40 * s, y - 29 * s, 13 * s, TEAL)
        scene.draw_polygon([(x - 40 * s, y - 39 * s), (x - 47 * s, y - 25 * s),
                            (x - 33 * s, y - 25 * s)], INK)


def piece(scene, x, y, kind, team, *, scale=1, selected=False, spent=False):
    """Distinct silhouettes for ranged troops, casters, infantry and heroes."""
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
    elif any(name in lower for name in ("mage", "wizard", "healer", "shaman")):
        scene.draw_line(x + 17 * s, y + 7 * s, x + 17 * s, y - 38 * s, GOLD, 3 * s)
        scene.draw_circle(x + 17 * s, y - 39 * s, 6 * s, BLUE)
        scene.draw_polygon([(x - 11 * s, y - 28 * s), (x + 1 * s, y - 48 * s),
                            (x + 9 * s, y - 28 * s)], color)
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
