"""Procedural textures: low-poly props pre-rendered with :mod:`sagaforge.render3d`.

The map is drawn in a fixed dimetric view: every tile is a block whose
top face is a 2:1 diamond ``ISO_W`` wide and ``ISO_H`` tall; terrain
features, resources, buildings and units are separate props standing on
that face.  Everything is rendered with Pillow at the display's pixel
density so it stays crisp on HiDPI screens, then registered with the
asset manager under a short key (``"tile.field"``, ``"prop.forest.0"``,
``"unit.warrior"``, ``"glow"``…).  Units and city roofs are white so
sprites can tint them with tribe colours at draw time.

Units are game pieces: a chibi figure on a flat disc that lies on the
tile top, over a soft contact shadow.  The disc is what tells the eye
which tile a unit occupies — a tall figure alone reads as standing on
any of the tiles it overlaps in a dimetric view.

Sprites are anchored at the bottom centre.  :data:`placements` records,
per key, the sprite size and how far the image bottom lies below the
tile-centre reference point ("drop"); the drop doubles as the y-sort key
within a row, so on one tile terrain props draw first and units last.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageFilter

from saga2d import Game
from sagaforge import render3d as r3
from sagaforge.render3d import Mesh
from tribes.rules import Resource, Terrain, UnitType

TILE = 64  # base size: the top-face diamond is 2×TILE wide and TILE tall
ISO_W = 2 * TILE
ISO_H = TILE
PROJECTION = r3.Projection.dimetric(ISO_W)
VIEW = PROJECTION.view

BLOCK_Z = 0.28  # land block thickness in tile units
WATER_Z = 0.14  # how far the water surface sits below the land top
BLOCK_H = math.ceil(BLOCK_Z * PROJECTION.z_scale)
WATER_DROP = WATER_Z * PROJECTION.z_scale
PAD = 2  # transparent margin around every image, in logical units
TILE_SIZE = (ISO_W + 2 * PAD, PAD + ISO_H + BLOCK_H + PAD)
TILE_ORIGIN = (TILE_SIZE[0] / 2, PAD + ISO_H / 2)
DROP_TILE = TILE_SIZE[1] - TILE_ORIGIN[1]
#: Drop per prop class; all within one row spacing (ISO_H / 2) of each other.
DROP_TERRAIN, DROP_WALL, DROP_RESOURCE, DROP_SITE, DROP_UNIT = 32, 34, 36, 36, 44
FOREST_VARIANTS = 3
MOUNTAIN_VARIANTS = 2

#: Top-face shades per terrain; a tile picks one by position so fields are not one flat sheet.
TERRAIN_SHADES: dict[Terrain, tuple[tuple[int, int, int], ...]] = {
    Terrain.WATER: ((46, 104, 178),),
    Terrain.FIELD: ((132, 186, 98), (124, 180, 92), (140, 192, 106)),
    Terrain.FOREST: ((92, 148, 84), (86, 140, 78)),
    Terrain.MOUNTAIN: ((152, 152, 160),),
}
FOG = (24, 26, 38)
FOG_TOP = (31, 34, 48)
WHITE = (255, 255, 255)
INK = (34, 38, 52)
TREE_GREENS = ((50, 112, 66), (64, 128, 72), (44, 100, 60))
TRUNK = (112, 82, 54)
PLASTER = (242, 234, 216)
ROCK = (138, 138, 150)
SNOW = (238, 240, 248)
SHADOW = (0, 0, 0, 96)

TOKEN_RADIUS = 0.30  # base disc of a unit, in tile units
TOKEN_HEIGHT = 0.06
TOKEN_FRONT = TOKEN_RADIUS * math.sqrt(2) * ISO_H / 2  # how far below the tile centre the disc's front rim projects
_SIDE = (1 / math.sqrt(2), -1 / math.sqrt(2), 0.0)  # model direction that projects to screen-right


@dataclass(frozen=True)
class Placement:
    """How to place a prop sprite: its logical size and the image bottom's
    distance below the tile-centre reference point."""

    size: tuple[float, float]
    drop: float


placements: dict[str, Placement] = {}


# -- Tiles ---------------------------------------------------------------------


def _block(top_color: tuple[int, int, int], top_z: float, scale: float) -> Mesh:
    """Tile block from the base plane up to *top_z*, widened by two device pixels
    so neighbouring blocks overlap instead of showing an anti-aliased seam."""
    bleed = 4 / (ISO_W * scale)
    return r3.box((0, 0, (top_z - BLOCK_Z) / 2), (1 + bleed, 1 + bleed, BLOCK_Z + top_z), top_color)


def _waves(draw: ImageDraw.ImageDraw, to_px, ss: float) -> None:
    color = (118, 168, 226, 255)
    for x0, y0 in ((-0.28, 0.02), (0.05, -0.25), (0.02, 0.22)):
        pts = [(x0 + i * 0.06, y0 + (0.03 if i % 2 else 0.0), -WATER_Z) for i in range(5)]
        draw.line([to_px(p) for p in pts], fill=color, width=max(1, round(1.4 * ss)))


def tile_key(pos: tuple[int, int], terrain: Terrain) -> str:
    """Texture key of the block for *terrain* at *pos* (the shade varies by position)."""
    return f"tile.{terrain.value}.{_scatter(pos) % len(TERRAIN_SHADES[terrain])}"


def _scatter(pos: tuple[int, int]) -> int:
    """A small integer hash of a grid position with no visible stripes or checkers."""
    x, y = pos
    h = (x * 0x27D4EB2D ^ (y + 0x165667B1) * 0x9E3779B1) & 0xFFFFFFFF
    return (h ^ (h >> 15)) & 0xFFFF


def _tile(terrain: Terrain, shade: int, scale: float) -> Image.Image:
    top_z = -WATER_Z if terrain is Terrain.WATER else 0.0
    return r3.render(
        _block(TERRAIN_SHADES[terrain][shade], top_z, scale), PROJECTION, scale=scale, canvas=TILE_SIZE, origin=TILE_ORIGIN,
        decorate=_waves if terrain is Terrain.WATER else None,
    )


def _fog(scale: float) -> Image.Image:
    return r3.render(_block(FOG_TOP, 0.0, scale), PROJECTION, scale=scale, canvas=TILE_SIZE, origin=TILE_ORIGIN)


# -- Props -------------------------------------------------------------------


def _prop(key: str, mesh: Mesh, drop: float, scale: float) -> Image.Image:
    """Render *mesh* into a canvas symmetric about the model origin whose bottom
    edge is *drop* below it, and record the placement under *key*."""
    min_x, min_y, max_x, max_y = r3.bounds(mesh, PROJECTION)
    half_w = math.ceil(max(-min_x, max_x) + PAD)
    top = math.ceil(-min_y + PAD)
    if max_y + PAD > drop:
        raise ValueError(f"{key}: mesh extends {max_y:.1f} below the tile centre, more than its drop of {drop}")
    canvas = (2 * half_w, top + drop)
    placements[key] = Placement(canvas, drop)
    return r3.render(mesh, PROJECTION, scale=scale, canvas=canvas, origin=(half_w, top))


def _tree(x: float, y: float, height: float, color: tuple[int, int, int], rotation: float = 0.0) -> Mesh:
    radius = height * 0.36
    return (
        r3.cylinder((x, y, 0), radius * 0.22, 0.06, TRUNK, sides=6)
        + r3.cone((x, y, 0.05), radius, height, color, sides=7, rotation=rotation)
    )


def _forest(variant: int) -> Mesh:
    layouts = (
        ((-0.2, 0.12, 0.44), (0.18, -0.14, 0.38), (0.1, 0.24, 0.34)),
        ((0.05, -0.2, 0.46), (-0.22, 0.16, 0.36), (0.22, 0.14, 0.4)),
        ((-0.16, -0.16, 0.4), (0.2, 0.02, 0.46), (-0.1, 0.24, 0.32)),
    )
    mesh: Mesh = []
    for i, (x, y, h) in enumerate(layouts[variant]):
        mesh += _tree(x, y, h, TREE_GREENS[(i + variant) % 3], rotation=0.4 * i)
    return mesh


def _peak(x: float, y: float, width: float, height: float, *, color: tuple[int, int, int] = ROCK, snow: float = 0.38, lean: tuple[float, float] = (0.0, 0.0)) -> Mesh:
    """Square pyramid whose top *snow* fraction is capped in white; *lean* shifts the apex."""
    rock = r3.pyramid((x, y, 0), (width, width), height, color, apex_shift=lean)
    if snow == 0:
        return rock
    t = 1 - snow
    cap = r3.pyramid((x + lean[0] * t, y + lean[1] * t, height * t), (width * snow, width * snow), height * snow, SNOW,
                     apex_shift=(lean[0] * snow, lean[1] * snow))
    return rock + cap


def _mountain(variant: int) -> Mesh:
    if variant == 0:
        return _peak(0, 0, 0.88, 0.82, lean=(-0.04, 0.02))
    return _peak(-0.2, 0.2, 0.48, 0.42, color=(128, 128, 140), snow=0) + _peak(0.1, -0.08, 0.7, 0.72, snow=0.4)


def _walls(x: float, y: float, w: float, d: float, h: float, color: tuple[int, int, int]) -> Mesh:
    return r3.box((x, y, h / 2), (w, d, h), color)


def _roof(x: float, y: float, w: float, d: float, h: float, color: tuple[int, int, int]) -> Mesh:
    return r3.gable_roof((x, y, h), (w + 0.05, d + 0.06), h * 0.7, color)


def _village() -> Mesh:
    return _walls(0, 0, 0.34, 0.3, 0.22, PLASTER) + _roof(0, 0, 0.34, 0.3, 0.22, (192, 114, 82))


def _workshop() -> Mesh:
    """A dark smithy with a chimney at the front-right of a city tile, clear of the
    houses behind and just outside the token disc, so a garrison does not hide it."""
    x, y = 0.31, 0.13
    body = r3.box((x, y, 0.07), (0.17, 0.15, 0.14), (98, 88, 82))
    roof = r3.gable_roof((x, y, 0.14), (0.2, 0.18), 0.07, (70, 62, 60))
    chimney = r3.box((x - 0.05, y + 0.04, 0.2), (0.04, 0.04, 0.12), (60, 56, 56))
    ember = r3.facing(_facing_quad((x + 0.09, y + 0.09, 0.06), 0.03), (255, 150, 60), VIEW)
    return body + roof + chimney + ember


def _ruin() -> Mesh:
    """Three broken columns of different heights and a toppled block."""
    stone, dark = (176, 172, 168), (150, 146, 144)
    mesh: Mesh = []
    for (x, y), height in (((-0.16, -0.12), 0.34), ((0.14, -0.18), 0.22), ((0.18, 0.12), 0.14)):
        mesh += r3.cylinder((x, y, 0), 0.06, height, stone, sides=8)
        mesh += r3.cylinder((x, y, 0), 0.09, 0.04, dark, sides=8)
    mesh += r3.rotate_z(r3.box((-0.12, 0.2, 0.05), (0.3, 0.1, 0.1), dark), 25)
    return mesh


def _flag() -> Mesh:
    """Capital marker: an ink pole at the back corner of the tile with a white (tinted) pennant."""
    x, y = 0.0, -0.42
    sx, sy, _ = _SIDE
    pole = r3.box((x, y, 0.38), (0.03, 0.03, 0.76), INK)
    pennant = r3.facing([(x, y, 0.75), (x + sx * 0.26, y + sy * 0.26, 0.68), (x, y, 0.6)], WHITE, VIEW)
    return pole + pennant


def _city_walls() -> Mesh:
    """A ring of stone along the tile's edges with a post at each corner."""
    stone, cap = (146, 148, 160), (170, 172, 184)
    edge, thick, height = 0.43, 0.06, 0.13
    mesh: Mesh = []
    for x, y, w, d in ((0, -edge, 2 * edge, thick), (0, edge, 2 * edge, thick), (-edge, 0, thick, 2 * edge), (edge, 0, thick, 2 * edge)):
        mesh += r3.box((x, y, height / 2), (w, d, height), stone)
    for x in (-edge, edge):
        for y in (-edge, edge):
            mesh += r3.box((x, y, 0.1), (0.1, 0.1, 0.2), cap)
    return mesh


#: House footprints per city size, kept to the back half of the tile so a
#: unit standing in the centre is not hidden.
_CITY_HOUSES = (
    ((-0.12, -0.12, 0.36, 0.3, 0.26),),
    ((-0.18, -0.18, 0.36, 0.3, 0.26), (0.24, -0.24, 0.2, 0.18, 0.16)),
    ((-0.18, -0.18, 0.36, 0.3, 0.26), (0.26, -0.26, 0.2, 0.18, 0.16), (-0.26, 0.26, 0.18, 0.2, 0.15)),
)
CITY_SIZES = len(_CITY_HOUSES)


def _city(size: int) -> tuple[Mesh, Mesh]:
    """``(walls, roofs)`` for a city of *size* houses; the roofs are white so
    the view can tint them with the tribe colour."""
    houses = _CITY_HOUSES[size - 1]
    walls = [f for x, y, w, d, h in houses for f in _walls(x, y, w, d, h, PLASTER)]
    roofs = [f for x, y, w, d, h in houses for f in _roof(x, y, w, d, h, WHITE)]
    return walls, roofs


def _resource(resource: Resource) -> Mesh:
    if resource is Resource.FRUIT:
        bush = r3.sphere((0, 0, 0.12), 0.15, (72, 138, 78), rings=4, sides=8)
        berries = [(0.09, 0.07, 0.2), (0.12, -0.04, 0.12), (-0.02, 0.14, 0.14), (0.02, 0.02, 0.27)]
        return bush + [f for x, y, z in berries for f in r3.sphere((x, y, z), 0.055, (232, 74, 86), rings=3, sides=6)]
    if resource is Resource.CROP:
        mesh: Mesh = []
        for x, y in ((-0.1, -0.1), (0.1, -0.1), (-0.1, 0.1), (0.1, 0.1)):
            mesh += r3.cylinder((x, y, 0), 0.03, 0.18, (214, 182, 76), sides=6)
            mesh += r3.cylinder((x, y, 0.18), 0.05, 0.1, (240, 214, 112), sides=6)
        return mesh
    if resource is Resource.GAME:
        top = r3.pyramid((0, 0, 0.2), (0.26, 0.26), 0.18, (156, 104, 62))
        bottom = r3.pyramid((0, 0, 0.2), (0.26, 0.26), -0.18, (156, 104, 62))
        return r3.rotate_z(bottom + top, 20)
    if resource is Resource.FISH:
        z = -WATER_Z + 0.004
        body = [(-0.14, 0.0), (-0.08, 0.07), (0.04, 0.08), (0.14, 0.02), (0.14, -0.02), (0.04, -0.08), (-0.08, -0.07)]
        tail = [(-0.12, 0.0), (-0.22, 0.07), (-0.22, -0.07)]
        return r3.rotate_z(r3.flat(body, z, (150, 220, 255)) + r3.flat(tail, z, (150, 220, 255)), -30)
    if resource is Resource.METAL:
        return (
            r3.cylinder((0, 0, 0), 0.16, 0.13, (198, 204, 216), sides=6, rotation=0.3)
            + r3.cylinder((0.02, -0.02, 0.13), 0.08, 0.08, (242, 246, 254), sides=6, rotation=0.3)
        )
    raise ValueError(resource)


def _figure(x: float, y: float, z: float, body_r: float = 0.12, body_h: float = 0.2, head_r: float = 0.13) -> Mesh:
    """Chibi figure standing at ``(x, y)`` on height *z*: short body, big head."""
    return r3.cylinder((x, y, z), body_r, body_h, WHITE, sides=10) + r3.sphere((x, y, z + body_h + head_r * 0.85), head_r, WHITE, rings=5, sides=10)


FIGURE_TOP = TOKEN_HEIGHT + 0.2 + 0.13 * 1.85  # z of a standard figure's crown


def _ellipse(cx: float, cy: float, radius: float, sides: int = 20) -> list[tuple[float, float]]:
    return [(cx + radius * math.cos(2 * math.pi * i / sides), cy + radius * math.sin(2 * math.pi * i / sides)) for i in range(sides)]


def _token_base() -> Mesh:
    """Contact shadow (offset away from the light) under a flat disc in the tribe colour."""
    shadow = r3.flat(_ellipse(0.05, -0.04, TOKEN_RADIUS * 1.12), 0.0, SHADOW)
    return shadow + r3.cylinder((0, 0, 0), TOKEN_RADIUS, TOKEN_HEIGHT, WHITE, sides=20, rotation=math.pi / 20)



def _facing_quad(center: r3.Vec3, half: float) -> list[r3.Vec3]:
    """Corners of a square facing the camera, centred on *center*."""
    cx, cy, cz = center
    sx, sy, _ = _SIDE
    return [
        (cx - sx * half, cy - sy * half, cz - half), (cx + sx * half, cy + sy * half, cz - half),
        (cx + sx * half, cy + sy * half, cz + half), (cx - sx * half, cy - sy * half, cz + half),
    ]


def _bow(z: float) -> Mesh:
    """An arc in the vertical plane facing the camera, plus its string."""
    cx, cy, cz, radius, thickness = 0.02, 0.2, z + 0.26, 0.2, 0.03
    sx, sy, _ = _SIDE

    def at(angle: float, r: float) -> r3.Vec3:
        return (cx + sx * r * math.cos(angle), cy + sy * r * math.cos(angle), cz + r * math.sin(angle))

    angles = [math.radians(a) for a in range(95, 266, 10)]
    mesh: Mesh = []
    for a0, a1 in zip(angles, angles[1:]):
        mesh += r3.facing([at(a0, radius - thickness), at(a1, radius - thickness), at(a1, radius), at(a0, radius)], INK, VIEW)
    return mesh + r3.ribbon([at(angles[0], radius), at(angles[-1], radius)], _SIDE, 0.014, INK, VIEW)


def _unit(unit_type: UnitType) -> Mesh:
    """Token base plus a white figure and the ink prop that identifies the unit type."""
    z = TOKEN_HEIGHT
    base = _token_base()
    if unit_type is UnitType.WARRIOR:
        sword = r3.box((0.17, -0.05, z + 0.3), (0.04, 0.04, 0.42), INK) + r3.box((0.17, -0.05, z + 0.14), (0.15, 0.045, 0.035), INK)
        return base + _figure(0, 0, z) + sword
    if unit_type is UnitType.ARCHER:
        return base + _figure(0, 0, z) + _bow(z)
    if unit_type is UnitType.RIDER:
        horse = r3.box((0.02, 0, z + 0.22), (0.42, 0.17, 0.17), WHITE)
        for x, y in ((-0.15, -0.05), (-0.15, 0.05), (0.15, -0.05), (0.15, 0.05)):
            horse += r3.box((x, y, z + 0.07), (0.045, 0.045, 0.14), WHITE)
        horse += r3.box((0.23, 0, z + 0.36), (0.1, 0.09, 0.15), WHITE) + r3.box((0.27, 0, z + 0.44), (0.15, 0.09, 0.08), WHITE)
        return base + horse + _figure(-0.05, 0, z + 0.3, body_r=0.09, body_h=0.16, head_r=0.1)
    if unit_type is UnitType.DEFENDER:
        shield = r3.rotate_z(r3.box((0, 0.2, z + 0.2), (0.28, 0.045, 0.3), WHITE), -45)
        emblem = r3.facing(_facing_quad((0.18, 0.18, z + 0.2), 0.07), INK, VIEW)
        return base + _figure(0, 0, z) + shield + emblem
    if unit_type is UnitType.KNIGHT:
        plume = r3.cone((0, 0, FIGURE_TOP - 0.03), 0.07, 0.2, INK, sides=8)
        lance = r3.box((0.17, -0.05, z + 0.4), (0.03, 0.03, 0.8), INK)
        sx, sy, _ = _SIDE
        pennant = r3.facing([(0.17, -0.05, z + 0.78), (0.17 + sx * 0.15, -0.05 + sy * 0.15, z + 0.73), (0.17, -0.05, z + 0.66)], INK, VIEW)
        return base + _figure(0, 0, z) + plume + lance + pennant
    if unit_type is UnitType.SWORDSMAN:
        blade = r3.box((0.18, -0.06, z + 0.34), (0.06, 0.06, 0.46), INK) + r3.box((0.18, -0.06, z + 0.13), (0.2, 0.06, 0.04), INK)
        shield = r3.facing(_facing_octagon((0.14, 0.14, z + 0.22), 0.12), INK, VIEW) + r3.facing(_facing_octagon((0.15, 0.15, z + 0.22), 0.08), WHITE, VIEW)
        return base + _figure(0, 0, z, body_r=0.13) + blade + shield
    if unit_type is UnitType.CATAPULT:
        frame = r3.box((0, 0, z + 0.05), (0.42, 0.24, 0.1), WHITE)
        wheels = [f for x, y in ((-0.16, -0.1), (-0.16, 0.1), (0.16, -0.1), (0.16, 0.1)) for f in r3.box((x, y, z + 0.05), (0.08, 0.05, 0.1), INK)]
        arm = r3.box((-0.1, 0, z + 0.36), (0.05, 0.05, 0.54), INK)
        bucket = r3.box((-0.1, 0, z + 0.65), (0.14, 0.14, 0.08), WHITE)
        crossbar = r3.box((0.06, 0, z + 0.2), (0.05, 0.28, 0.2), WHITE)
        return base + frame + wheels + arm + bucket + crossbar
    raise ValueError(unit_type)


def _facing_octagon(center: r3.Vec3, radius: float) -> list[r3.Vec3]:
    """Corners of a regular octagon facing the camera, centred on *center*."""
    cx, cy, cz = center
    sx, sy, _ = _SIDE
    return [
        (cx + sx * radius * math.cos(a), cy + sy * radius * math.cos(a), cz + radius * math.sin(a))
        for a in (math.radians(22.5 + 45 * i) for i in range(8))
    ]


# -- 2-D effects -------------------------------------------------------------------


def _glow(size: int, radius_frac: float, color: tuple[int, int, int, int], blur_frac: float = 0.18) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    r = size * radius_frac
    c = size / 2
    draw.ellipse([c - r, c - r, c + r, c + r], fill=color)
    return img.filter(ImageFilter.GaussianBlur(size * blur_frac))


def _ring(px: int, scale: float) -> Image.Image:
    img = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    c = px / 2
    r = px * 0.42
    draw.ellipse([c - r, c - r, c + r, c + r], outline=(*WHITE, 255), width=max(2, round(3 * scale)))
    return img


# -- Registration --------------------------------------------------------------------


def register_all(game: Game) -> None:
    """Generate every texture at the backend's pixel density and register it."""
    scale = game.backend.scale_factor
    assets = game.assets
    if assets.has_image("glow"):
        return
    for terrain, shades in TERRAIN_SHADES.items():
        for shade in range(len(shades)):
            assets.image_from_pil(f"tile.{terrain.value}.{shade}", _tile(terrain, shade, scale))
    assets.image_from_pil("tile.fog", _fog(scale))
    for i in range(FOREST_VARIANTS):
        assets.image_from_pil(f"prop.forest.{i}", _prop(f"prop.forest.{i}", _forest(i), DROP_TERRAIN, scale))
    for i in range(MOUNTAIN_VARIANTS):
        assets.image_from_pil(f"prop.mountain.{i}", _prop(f"prop.mountain.{i}", _mountain(i), DROP_TERRAIN, scale))
    for resource in Resource:
        key = f"resource.{resource.value}"
        assets.image_from_pil(key, _prop(key, _resource(resource), DROP_RESOURCE, scale))
    assets.image_from_pil("village", _prop("village", _village(), DROP_SITE, scale))
    assets.image_from_pil("ruin", _prop("ruin", _ruin(), DROP_SITE, scale))
    assets.image_from_pil("workshop", _prop("workshop", _workshop(), DROP_SITE + 1, scale))
    assets.image_from_pil("flag", _prop("flag", _flag(), DROP_SITE + 2, scale))
    assets.image_from_pil("walls", _prop("walls", _city_walls(), DROP_WALL, scale))
    for size in range(1, CITY_SIZES + 1):
        walls, roofs = _city(size)
        assets.image_from_pil(f"city.{size}.base", _prop(f"city.{size}.base", walls, DROP_SITE, scale))
        assets.image_from_pil(f"city.{size}", _prop(f"city.{size}", roofs, DROP_SITE + 1, scale))
    for unit_type in UnitType:
        key = f"unit.{unit_type.value}"
        assets.image_from_pil(key, _prop(key, _unit(unit_type), DROP_UNIT, scale))
    px = int(TILE * scale)
    assets.image_from_pil("glow", _glow(px * 2, 0.24, (*WHITE, 255)))
    assets.image_from_pil("glow.soft", _glow(px * 2, 0.3, (255, 255, 255, 160), 0.22))
    assets.image_from_pil("ring", _ring(px, scale))
    assets.image_from_pil("blank", Image.new("RGBA", (px, px), (*WHITE, 255)))
    assets.image_from_pil("spark", _glow(int(px * 0.5), 0.3, (*WHITE, 255), 0.15))
