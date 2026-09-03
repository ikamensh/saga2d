"""Procedural textures: flat geometric shapes with soft glows.

Every texture is drawn with Pillow at the display's pixel density so it
stays crisp on HiDPI screens, then registered with the asset manager
under a short key (``"tile.field"``, ``"unit.warrior"``, ``"glow"``…).
Sprites tint the white textures with tribe colours at draw time.
"""

from __future__ import annotations

import math

from PIL import Image, ImageDraw, ImageFilter

from saga2d import Game
from tribes.rules import Resource, Terrain, UnitType

TILE = 64  # logical units per tile

TERRAIN_COLORS: dict[Terrain, tuple[int, int, int]] = {
    Terrain.WATER: (36, 78, 140),
    Terrain.FIELD: (124, 176, 92),
    Terrain.FOREST: (78, 132, 76),
    Terrain.MOUNTAIN: (142, 142, 150),
}
FOG = (24, 26, 38)
WHITE = (255, 255, 255, 255)
INK = (24, 28, 40, 255)


def _canvas(size: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _glow(size: int, radius_frac: float, color: tuple[int, int, int, int], blur_frac: float = 0.18) -> Image.Image:
    img, draw = _canvas(size)
    r = size * radius_frac
    c = size / 2
    draw.ellipse([c - r, c - r, c + r, c + r], fill=color)
    return img.filter(ImageFilter.GaussianBlur(size * blur_frac))


def _regular_polygon(draw: ImageDraw.ImageDraw, cx: float, cy: float, r: float, sides: int, rotation: float, fill) -> None:
    pts = [(cx + r * math.cos(rotation + 2 * math.pi * i / sides), cy + r * math.sin(rotation + 2 * math.pi * i / sides)) for i in range(sides)]
    draw.polygon(pts, fill=fill)


def _tile(px: int, terrain: Terrain, scale: float) -> Image.Image:
    base = TERRAIN_COLORS[terrain]
    img = Image.new("RGBA", (px, px), (*base, 255))
    draw = ImageDraw.Draw(img)
    dark = tuple(max(0, c - 22) for c in base)
    light = tuple(min(255, c + 18) for c in base)
    draw.rectangle([0, 0, px - 1, px - 1], outline=(*dark, 255), width=max(1, round(1.5 * scale)))
    if terrain is Terrain.FOREST:
        for fx, fy, s in ((0.3, 0.62, 0.22), (0.62, 0.7, 0.26), (0.5, 0.36, 0.2)):
            cx, cy, r = fx * px, fy * px, s * px
            draw.polygon([(cx, cy - r), (cx - r * 0.8, cy + r * 0.6), (cx + r * 0.8, cy + r * 0.6)], fill=(*dark, 255))
    elif terrain is Terrain.MOUNTAIN:
        cx, cy = px * 0.5, px * 0.72
        draw.polygon([(cx, px * 0.2), (cx - px * 0.34, cy), (cx + px * 0.34, cy)], fill=(*dark, 255))
        draw.polygon([(cx, px * 0.2), (cx - px * 0.11, px * 0.36), (cx + px * 0.11, px * 0.36)], fill=(235, 238, 245, 255))
    elif terrain is Terrain.WATER:
        for wy in (0.3, 0.55, 0.8):
            y = wy * px
            draw.line([(px * 0.2, y), (px * 0.45, y - px * 0.03), (px * 0.7, y)], fill=(*light, 255), width=max(1, round(1.5 * scale)))
    elif terrain is Terrain.FIELD:
        for fx, fy in ((0.25, 0.3), (0.7, 0.25), (0.5, 0.65), (0.2, 0.75), (0.8, 0.8)):
            x, y = fx * px, fy * px
            draw.line([(x, y), (x + px * 0.06, y - px * 0.04)], fill=(*light, 255), width=max(1, round(1.2 * scale)))
    return img


def _fog(px: int, scale: float) -> Image.Image:
    img = Image.new("RGBA", (px, px), (*FOG, 255))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, px - 1, px - 1], outline=(34, 37, 52, 255), width=max(1, round(1.5 * scale)))
    return img


def _resource(px: int, resource: Resource, scale: float) -> Image.Image:
    img, draw = _canvas(px)
    c = px / 2
    if resource is Resource.FRUIT:
        for dx, dy in ((-0.14, 0.06), (0.14, 0.06), (0, -0.12)):
            r = px * 0.11
            draw.ellipse([c + dx * px - r, c + dy * px - r, c + dx * px + r, c + dy * px + r], fill=(235, 80, 90, 255))
    elif resource is Resource.CROP:
        for i in range(3):
            x = c + (i - 1) * px * 0.14
            draw.line([(x, c + px * 0.2), (x, c - px * 0.2)], fill=(245, 210, 90, 255), width=max(2, round(3 * scale)))
            draw.ellipse([x - px * 0.06, c - px * 0.26, x + px * 0.06, c - px * 0.14], fill=(250, 225, 120, 255))
    elif resource is Resource.GAME:
        _regular_polygon(draw, c, c, px * 0.2, 4, 0, (150, 100, 60, 255))
        _regular_polygon(draw, c, c, px * 0.1, 4, 0, (220, 180, 130, 255))
    elif resource is Resource.FISH:
        draw.polygon([(c - px * 0.2, c), (c + px * 0.08, c - px * 0.12), (c + px * 0.08, c + px * 0.12)], fill=(150, 220, 255, 255))
        draw.polygon([(c + px * 0.06, c), (c + px * 0.22, c - px * 0.12), (c + px * 0.22, c + px * 0.12)], fill=(150, 220, 255, 255))
    elif resource is Resource.METAL:
        _regular_polygon(draw, c, c, px * 0.2, 6, math.pi / 6, (200, 205, 215, 255))
        _regular_polygon(draw, c, c, px * 0.1, 6, math.pi / 6, (245, 248, 255, 255))
    return img


def _house(px: int, scale: float, color: tuple[int, int, int, int], roof: tuple[int, int, int, int]) -> Image.Image:
    img, draw = _canvas(px)
    c = px / 2
    w, h = px * 0.42, px * 0.3
    draw.rectangle([c - w / 2, c - h * 0.1, c + w / 2, c + h * 0.9], fill=color)
    draw.polygon([(c - w * 0.65, c - h * 0.1), (c, c - h * 1.1), (c + w * 0.65, c - h * 0.1)], fill=roof)
    return img


def _unit(px: int, unit_type: UnitType, scale: float) -> Image.Image:
    """White disc (tinted with the tribe colour at draw time) with an ink glyph."""
    img, draw = _canvas(px)
    c = px / 2
    body = px * 0.34
    draw.ellipse([c - body, c - body, c + body, c + body], fill=WHITE)
    r = px * 0.17
    width = max(2, round(2.5 * scale))
    if unit_type is UnitType.WARRIOR:
        draw.polygon([(c, c - r * 1.1), (c - r, c + r * 0.8), (c + r, c + r * 0.8)], fill=INK)
    elif unit_type is UnitType.ARCHER:
        draw.arc([c - r, c - r, c + r, c + r], start=300, end=60, fill=INK, width=width)
        draw.line([(c - r * 0.2, c), (c + r * 1.1, c)], fill=INK, width=width)
    elif unit_type is UnitType.RIDER:
        _regular_polygon(draw, c, c, r * 1.15, 4, 0, INK)
    elif unit_type is UnitType.DEFENDER:
        draw.rounded_rectangle([c - r, c - r, c + r, c + r], radius=r * 0.3, fill=INK)
    elif unit_type is UnitType.KNIGHT:
        pts = []
        for i in range(10):
            rr = r * 1.2 if i % 2 == 0 else r * 0.5
            a = -math.pi / 2 + i * math.pi / 5
            pts.append((c + rr * math.cos(a), c + rr * math.sin(a)))
        draw.polygon(pts, fill=INK)
    return img


def _ring(px: int, scale: float) -> Image.Image:
    img, draw = _canvas(px)
    c = px / 2
    r = px * 0.42
    draw.ellipse([c - r, c - r, c + r, c + r], outline=WHITE, width=max(2, round(3 * scale)))
    return img


def register_all(game: Game) -> None:
    """Generate every texture at the backend's pixel density and register it."""
    scale = game.backend.scale_factor
    px = int(TILE * scale)
    assets = game.assets
    if assets.has_image("glow"):
        return
    for terrain in Terrain:
        assets.image_from_pil(f"tile.{terrain.value}", _tile(px, terrain, scale))
    assets.image_from_pil("tile.fog", _fog(px, scale))
    for resource in Resource:
        assets.image_from_pil(f"resource.{resource.value}", _resource(px, resource, scale))
    assets.image_from_pil("village", _house(px, scale, (240, 236, 224, 255), (200, 190, 170, 255)))
    assets.image_from_pil("city", _house(px, scale, WHITE, (225, 225, 235, 255)))
    for unit_type in UnitType:
        assets.image_from_pil(f"unit.{unit_type.value}", _unit(px, unit_type, scale))
    assets.image_from_pil("glow", _glow(px * 2, 0.24, WHITE))
    assets.image_from_pil("glow.soft", _glow(px * 2, 0.3, (255, 255, 255, 160), 0.22))
    assets.image_from_pil("ring", _ring(px, scale))
    assets.image_from_pil("blank", Image.new("RGBA", (px, px), WHITE))
    assets.image_from_pil("spark", _glow(int(px * 0.5), 0.3, WHITE, 0.15))
