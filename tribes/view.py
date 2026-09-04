"""MapView — everything drawn in world space for the Tribes map.

The map is laid out in a fixed dimetric view: grid ``(x, y)`` maps to a
diamond ``ISO_W`` wide and ``ISO_H`` tall (:func:`tile_center`), rows
of constant ``x + y`` run across the screen, and larger ``x + y`` is
nearer the camera.  Draw order uses the render layer bands:

* ``BACKGROUND`` — tile blocks, y-sorted so nearer rows overlap the sides
  of the row behind.
* ``OBJECTS`` — per-frame overlay shapes on the tile tops (territory,
  move range, attack targets, selection, cursor).
* ``UNITS`` — every prop standing on a tile (trees, mountains, resources,
  houses, units), y-sorted by row; within a row the per-class *drop* from
  :mod:`tribes.textures` puts terrain first and units last.
* ``UI_WORLD`` — city names, level pips, health bars.

The view owns the sprites, keeps them in step with the model
(:meth:`sync`), converts between grid and world coordinates and draws the
overlays.  The scene owns input, selection state and the HUD.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from saga2d import MoveTo, ParticleEmitter, RenderLayer, Scene, Sequence, Sprite, SpriteAnchor
from tribes import textures
from tribes.model import Pos, Unit, World
from tribes.rules import Terrain
from tribes.textures import DROP_TILE, DROP_UNIT, ISO_H, ISO_W, TILE, TILE_SIZE, WATER_DROP

Color = tuple[int, int, int, int]

HALF_W, HALF_H = ISO_W / 2, ISO_H / 2


def rgba(color: tuple[int, int, int], alpha: int = 255) -> Color:
    return (color[0], color[1], color[2], alpha)


def tint(color: tuple[int, int, int]) -> tuple[float, float, float]:
    return (color[0] / 255, color[1] / 255, color[2] / 255)


def tile_center(pos: Pos) -> tuple[float, float]:
    """World coordinates of the centre of tile *pos*'s top face (land level).

    Tile ``(0, 0)`` has its top corner at the origin; ``x`` runs down-right
    and ``y`` down-left.
    """
    x, y = pos
    return ((x - y) * HALF_W, (x + y) * HALF_H + HALF_H)


def tile_at(wx: float, wy: float) -> Pos:
    """Grid position whose top-face diamond contains world point ``(wx, wy)``
    (may be out of bounds).  Inverse of :func:`tile_center`."""
    u = wx / HALF_W
    v = (wy - HALF_H) / HALF_H
    return (int(math.floor((u + v) / 2 + 0.5)), int(math.floor((v - u) / 2 + 0.5)))


def diamond(cx: float, cy: float, scale: float = 1.0) -> list[tuple[float, float]]:
    """Top, right, bottom and left corners of a tile-top diamond centred on ``(cx, cy)``."""
    hw, hh = HALF_W * scale, HALF_H * scale
    return [(cx, cy - hh), (cx + hw, cy), (cx, cy + hh), (cx - hw, cy)]


#: Neighbour offset → which diamond edge (corner indices into :func:`diamond`) the two tiles share.
_SHARED_EDGES: tuple[tuple[Pos, tuple[int, int]], ...] = (((0, -1), (0, 1)), ((1, 0), (1, 2)), ((0, 1), (2, 3)), ((-1, 0), (3, 0)))


@dataclass
class Selection:
    """What the scene wants highlighted this frame."""

    cursor: Pos
    unit: Unit | None = None
    city_pos: Pos | None = None
    reachable: dict[Pos, Pos] = field(default_factory=dict)
    targets: list[Unit] = field(default_factory=list)
    pulse: float = 0.0


class MapView:
    def __init__(self, scene: Scene, world: World, human: int, rng: random.Random) -> None:
        self.scene = scene
        self.world = world
        self.human = human
        self.rng = rng
        self._tile_sprites: dict[Pos, Sprite] = {}
        self._terrain_sprites: dict[Pos, Sprite] = {}
        self._resource_sprites: dict[Pos, Sprite] = {}
        self._site_sprites: dict[Pos, Sprite] = {}  # village, or city walls
        self._roof_sprites: dict[Pos, Sprite] = {}  # city roofs, tinted with the tribe colour
        self._unit_sprites: dict[int, Sprite] = {}
        self._unit_targets: dict[int, Pos] = {}
        textures.register_all(scene.game)
        self._build_tiles()
        self.sync()

    def _build_tiles(self) -> None:
        for tile in self.world.all_tiles():
            self._tile_sprites[tile.pos] = self.scene.add_sprite(Sprite(
                "tile.fog", position=self._anchor(tile.pos, DROP_TILE), size=TILE_SIZE, anchor=SpriteAnchor.BOTTOM_CENTER,
                layer=RenderLayer.BACKGROUND, y_sort=True,
            ))

    @staticmethod
    def _anchor(pos: Pos, drop: float) -> tuple[float, float]:
        """Bottom-centre position of a sprite whose image bottom is *drop* below the tile centre."""
        cx, cy = tile_center(pos)
        return (cx, cy + drop)

    def _prop(self, key: str, pos: Pos, **kwargs) -> Sprite:
        placement = textures.placements[key]
        return self.scene.add_sprite(Sprite(
            key, position=self._anchor(pos, placement.drop), size=placement.size, anchor=SpriteAnchor.BOTTOM_CENTER,
            layer=RenderLayer.UNITS, y_sort=True, **kwargs,
        ))

    def _reconcile(self, sprites: dict[Pos, Sprite], pos: Pos, key: str | None) -> Sprite | None:
        """Make ``sprites[pos]`` show *key* (or nothing); returns the sprite."""
        sprite = sprites.get(pos)
        if key is None:
            if sprite is not None:
                sprites.pop(pos).remove()
            return None
        if sprite is None or sprite.image != key:
            if sprite is not None:
                sprite.remove()
            sprite = sprites[pos] = self._prop(key, pos)
        return sprite

    @property
    def world_bounds(self) -> tuple[float, float, float, float]:
        size = self.world.size
        return (-size * HALF_W - TILE, -2 * TILE, size * HALF_W + TILE, size * ISO_H + DROP_TILE + TILE)

    @property
    def explored(self) -> set[Pos]:
        return self.world.tribes[self.human].explored

    def tile_sprite(self, pos: Pos) -> Sprite:
        return self._tile_sprites[pos]

    def surface_center(self, pos: Pos) -> tuple[float, float]:
        """Like :func:`tile_center`, but on the water surface for explored water tiles."""
        cx, cy = tile_center(pos)
        if pos in self.explored and self.world.tile(pos).terrain is Terrain.WATER:
            cy += WATER_DROP
        return (cx, cy)

    def reset(self, world: World) -> None:
        """Point the view at a different world (after loading a save)."""
        for group in (self._terrain_sprites, self._resource_sprites, self._site_sprites, self._roof_sprites, self._unit_sprites):
            for sprite in group.values():
                sprite.remove()
            group.clear()
        self._unit_targets.clear()
        if world.size != self.world.size:
            for sprite in self._tile_sprites.values():
                sprite.remove()
            self._tile_sprites.clear()
            self.world = world
            self._build_tiles()
        else:
            for sprite in self._tile_sprites.values():
                sprite.image = "tile.fog"
            self.world = world
        self.sync()

    # -- Sprite reconciliation -------------------------------------------------

    @staticmethod
    def _terrain_key(pos: Pos, terrain: Terrain) -> str | None:
        seed = pos[0] * 7 + pos[1] * 13
        if terrain is Terrain.FOREST:
            return f"prop.forest.{seed % textures.FOREST_VARIANTS}"
        if terrain is Terrain.MOUNTAIN:
            return f"prop.mountain.{seed % textures.MOUNTAIN_VARIANTS}"
        return None

    def sync(self) -> None:
        """Make sprites match the model (idempotent)."""
        world = self.world
        explored = self.explored
        for pos in explored:
            tile = world.tile(pos)
            tile_sprite = self._tile_sprites[pos]
            if tile_sprite.image != f"tile.{tile.terrain.value}":
                tile_sprite.image = f"tile.{tile.terrain.value}"
            self._reconcile(self._terrain_sprites, pos, self._terrain_key(pos, tile.terrain))
            has_resource = tile.resource is not None and not tile.harvested
            self._reconcile(self._resource_sprites, pos, f"resource.{tile.resource.value}" if has_resource else None)
            city = world.city_at(pos)
            if city is not None:
                size = min(city.level, textures.CITY_SIZES)
                self._reconcile(self._site_sprites, pos, f"city.{size}.base")
                roofs = self._reconcile(self._roof_sprites, pos, f"city.{size}")
                roofs.tint = tint(world.tribes[city.tribe].color)
            else:
                self._reconcile(self._site_sprites, pos, "village" if tile.village else None)
                self._reconcile(self._roof_sprites, pos, None)
        for unit_id, sprite in list(self._unit_sprites.items()):
            unit = world.units.get(unit_id)
            if unit is None or unit.pos not in explored:
                sprite.remove()
                del self._unit_sprites[unit_id]
                self._unit_targets.pop(unit_id, None)
        for unit in world.units.values():
            if unit.pos not in explored:
                continue
            sprite = self._unit_sprites.get(unit.id)
            if sprite is None:
                sprite = self._prop(f"unit.{unit.type.value}", unit.pos, tint=tint(world.tribes[unit.tribe].color))
                self._unit_sprites[unit.id] = sprite
                self._unit_targets[unit.id] = unit.pos
            elif self._unit_targets[unit.id] != unit.pos:
                sprite.stop_actions()
                sprite.position = self._anchor(unit.pos, DROP_UNIT)
                self._unit_targets[unit.id] = unit.pos
            sprite.opacity = 255 if unit.tribe != self.human or unit.can_act else 150

    def unit_sprite(self, unit_id: int) -> Sprite | None:
        return self._unit_sprites.get(unit_id)

    def animate_move(self, unit: Unit, path: list[Pos]) -> None:
        sprite = self._unit_sprites.get(unit.id)
        if sprite is None:
            return
        self._unit_targets[unit.id] = path[-1]
        sprite.do(Sequence(*[MoveTo(self._anchor(p, DROP_UNIT), speed=420) for p in path[1:]]))

    def burst(self, pos: Pos, color: Color, count: int) -> None:
        cx, cy = self.surface_center(pos)
        emitter = ParticleEmitter("spark", position=(cx, cy - 12), speed=(60, 220), lifetime=(0.25, 0.6),
                                  size=(14, 14), shrink=True, tint=tint(color[:3]), rng=self.rng)
        emitter.burst(count)

    # -- Per-frame overlays ------------------------------------------------------

    def _fill(self, pos: Pos, color: Color, scale: float = 1.0) -> None:
        cx, cy = self.surface_center(pos)
        self.scene.draw_polygon(diamond(cx, cy, scale), color, space="world", layer=RenderLayer.OBJECTS)

    def _outline(self, pos: Pos, color: Color, width: float, scale: float = 1.0, layer: RenderLayer = RenderLayer.OBJECTS) -> None:
        cx, cy = self.surface_center(pos)
        corners = diamond(cx, cy, scale)
        for i in range(4):
            (x1, y1), (x2, y2) = corners[i], corners[(i + 1) % 4]
            self.scene.draw_line(x1, y1, x2, y2, color, width, space="world", layer=layer)

    def _draw_territory(self) -> None:
        scene, world = self.scene, self.world
        left, top, right, bottom = scene.camera.visible_world_rect()
        for pos in self.explored:
            owner = world.owner_of(pos)
            if owner is None:
                continue
            cx, cy = self.surface_center(pos)
            if not (left - ISO_W < cx < right + ISO_W and top - ISO_H < cy < bottom + ISO_H):
                continue
            color = world.tribes[owner].color
            corners = diamond(cx, cy)
            scene.draw_polygon(corners, rgba(color, 40), space="world", layer=RenderLayer.OBJECTS)
            for (dx, dy), (a, b) in _SHARED_EDGES:
                n = (pos[0] + dx, pos[1] + dy)
                if not world.in_bounds(n) or world.owner_of(n) != owner:
                    scene.draw_line(*corners[a], *corners[b], rgba(color, 210), 3, space="world", layer=RenderLayer.OBJECTS)

    def draw(self, selection: Selection) -> None:
        scene = self.scene
        world = self.world
        explored = self.explored
        self._draw_territory()
        for pos in selection.reachable:
            self._fill(pos, (255, 255, 255, 70), 0.86)
        for target in selection.targets:
            self._fill(target.pos, (255, 70, 70, 80), 0.86)
            self._outline(target.pos, (255, 80, 80, 230), 2.5, 0.86)
        human_color = world.tribes[self.human].color
        if selection.unit is not None:
            glow = 0.55 + 0.45 * math.sin(selection.pulse * 6)
            self._fill(selection.unit.pos, rgba(human_color, int(140 * glow)), 0.9)
        if selection.city_pos is not None:
            self._fill(selection.city_pos, rgba(human_color, 70))
            self._outline(selection.city_pos, rgba(human_color, 230), 2.5)
        for city in world.cities.values():
            if city.pos not in explored:
                continue
            # Name and level pips sit on the front half of the tile, clear of the
            # houses behind the centre and of any unit standing there.
            cx, cy = tile_center(city.pos)
            color = world.tribes[city.tribe].color
            pip_w, pip_gap, pip_y = 8, 3, cy + 18
            total = city.level * (pip_w + pip_gap) - pip_gap
            for i in range(city.level):
                scene.draw_rect(cx - total / 2 + i * (pip_w + pip_gap), pip_y, pip_w, 5, rgba(color, 255), space="world", layer=RenderLayer.UI_WORLD)
            name_y = pip_y + 7
            scene.draw_text(city.name, cx + 1, name_y + 1, style="city", color=(0, 0, 0, 200), anchor_x="center", anchor_y="top", space="world", layer=RenderLayer.UI_WORLD)
            scene.draw_text(city.name, cx, name_y, style="city", anchor_x="center", anchor_y="top", space="world", layer=RenderLayer.UI_WORLD)
        for u in world.units.values():
            if u.pos not in explored or u.hp >= u.max_hp:
                continue
            sprite = self._unit_sprites.get(u.id)
            if sprite is None:
                continue
            sx, sy = sprite.position
            feet_y = sy - DROP_UNIT
            bar_w = 32
            scene.draw_rect(sx - bar_w / 2, feet_y + 6, bar_w, 5, (0, 0, 0, 160), space="world", layer=RenderLayer.UI_WORLD)
            scene.draw_rect(sx - bar_w / 2, feet_y + 6, bar_w * u.hp / u.max_hp, 5, (110, 230, 110, 255), space="world", layer=RenderLayer.UI_WORLD)
        self._outline(selection.cursor, (255, 255, 255, 230), 2.5, layer=RenderLayer.UI_WORLD)
