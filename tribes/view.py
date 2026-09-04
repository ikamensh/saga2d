"""MapView — everything drawn in world space for the Tribes map.

The view owns the sprites for tiles, resources, villages/cities and units,
keeps them in step with the model (:meth:`sync`), converts between grid
positions and world coordinates, and draws the per-frame overlays
(territory, move/attack highlights, city names, health bars, cursor).
The scene owns input, selection state and the HUD.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

from saga2d import MoveTo, ParticleEmitter, RenderLayer, Scene, Sequence, Sprite
from tribes import textures
from tribes.model import Pos, Unit, World
from tribes.textures import TILE

Color = tuple[int, int, int, int]


def rgba(color: tuple[int, int, int], alpha: int = 255) -> Color:
    return (color[0], color[1], color[2], alpha)


def tint(color: tuple[int, int, int]) -> tuple[float, float, float]:
    return (color[0] / 255, color[1] / 255, color[2] / 255)


def tile_center(pos: Pos) -> tuple[float, float]:
    """World coordinates of the centre of grid tile *pos*."""
    return (pos[0] * TILE + TILE / 2, pos[1] * TILE + TILE / 2)


def tile_at(wx: float, wy: float) -> Pos:
    """Grid position under world point ``(wx, wy)`` (may be out of bounds)."""
    return (int(math.floor(wx / TILE)), int(math.floor(wy / TILE)))


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
        self._resource_sprites: dict[Pos, Sprite] = {}
        self._site_sprites: dict[Pos, Sprite] = {}
        self._unit_sprites: dict[int, Sprite] = {}
        self._unit_targets: dict[int, Pos] = {}
        textures.register_all(scene.game)
        for tile in world.all_tiles():
            self._tile_sprites[tile.pos] = scene.add_sprite(Sprite(
                "tile.fog", position=tile_center(tile.pos), size=(TILE, TILE), layer=RenderLayer.BACKGROUND,
            ))
        self.sync()

    @property
    def world_bounds(self) -> tuple[float, float, float, float]:
        extent = self.world.size * TILE
        return (-TILE, -TILE, extent + TILE, extent + TILE)

    @property
    def explored(self) -> set[Pos]:
        return self.world.tribes[self.human].explored

    def reset(self, world: World) -> None:
        """Point the view at a different world (after loading a save)."""
        for sprite in [*self._resource_sprites.values(), *self._site_sprites.values(), *self._unit_sprites.values()]:
            sprite.remove()
        self._resource_sprites.clear()
        self._site_sprites.clear()
        self._unit_sprites.clear()
        self._unit_targets.clear()
        if world.size != self.world.size:
            for sprite in self._tile_sprites.values():
                sprite.remove()
            self._tile_sprites.clear()
            self.world = world
            for tile in world.all_tiles():
                self._tile_sprites[tile.pos] = self.scene.add_sprite(Sprite(
                    "tile.fog", position=tile_center(tile.pos), size=(TILE, TILE), layer=RenderLayer.BACKGROUND,
                ))
        else:
            for sprite in self._tile_sprites.values():
                sprite.image = "tile.fog"
            self.world = world
        self.sync()

    # -- Sprite reconciliation -------------------------------------------------

    def sync(self) -> None:
        """Make sprites match the model (idempotent)."""
        world = self.world
        explored = self.explored
        for pos in explored:
            tile = world.tile(pos)
            tile_sprite = self._tile_sprites[pos]
            if tile_sprite.image != f"tile.{tile.terrain.value}":
                tile_sprite.image = f"tile.{tile.terrain.value}"
            has_resource = tile.resource is not None and not tile.harvested
            if has_resource and pos not in self._resource_sprites:
                self._resource_sprites[pos] = self.scene.add_sprite(Sprite(
                    f"resource.{tile.resource.value}", position=tile_center(pos), size=(TILE, TILE), layer=RenderLayer.OBJECTS,
                ))
            elif not has_resource and pos in self._resource_sprites:
                self._resource_sprites.pop(pos).remove()
            city = world.city_at(pos)
            want = "city" if city is not None else "village" if tile.village else None
            sprite = self._site_sprites.get(pos)
            if want is None and sprite is not None:
                self._site_sprites.pop(pos).remove()
            elif want is not None:
                if sprite is None or sprite.image != want:
                    if sprite is not None:
                        sprite.remove()
                    sprite = self.scene.add_sprite(Sprite(want, position=tile_center(pos), size=(TILE, TILE), layer=RenderLayer.OBJECTS))
                    self._site_sprites[pos] = sprite
                sprite.tint = tint(world.tribes[city.tribe].color) if city is not None else (1.0, 1.0, 1.0)
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
                sprite = self.scene.add_sprite(Sprite(
                    f"unit.{unit.type.value}", position=tile_center(unit.pos), size=(TILE, TILE),
                    layer=RenderLayer.UNITS, tint=tint(world.tribes[unit.tribe].color),
                ))
                self._unit_sprites[unit.id] = sprite
                self._unit_targets[unit.id] = unit.pos
            elif self._unit_targets[unit.id] != unit.pos:
                sprite.stop_actions()
                sprite.position = tile_center(unit.pos)
                self._unit_targets[unit.id] = unit.pos
            sprite.opacity = 255 if unit.tribe != self.human or unit.can_act else 150

    def unit_sprite(self, unit_id: int) -> Sprite | None:
        return self._unit_sprites.get(unit_id)

    def animate_move(self, unit: Unit, path: list[Pos]) -> None:
        sprite = self._unit_sprites.get(unit.id)
        if sprite is None:
            return
        self._unit_targets[unit.id] = path[-1]
        sprite.do(Sequence(*[MoveTo(tile_center(p), speed=420) for p in path[1:]]))

    def burst(self, pos: Pos, color: Color, count: int) -> None:
        emitter = ParticleEmitter("spark", position=tile_center(pos), speed=(60, 220), lifetime=(0.25, 0.6),
                                  size=(14, 14), shrink=True, tint=tint(color[:3]), rng=self.rng)
        emitter.burst(count)

    # -- Per-frame overlays ------------------------------------------------------

    def draw(self, selection: Selection) -> None:
        scene = self.scene
        world = self.world
        explored = self.explored
        cam = scene.camera
        left, top, right, bottom = cam.visible_world_rect()
        x0, y0 = max(0, int(left // TILE)), max(0, int(top // TILE))
        x1, y1 = min(world.size - 1, int(right // TILE)), min(world.size - 1, int(bottom // TILE))
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                pos = (x, y)
                if pos not in explored:
                    continue
                owner = world.owner_of(pos)
                if owner is None:
                    continue
                color = world.tribes[owner].color
                px, py = x * TILE, y * TILE
                scene.draw_rect(px, py, TILE, TILE, rgba(color, 40), space="world", layer=RenderLayer.BACKGROUND)
                for dx, dy, line in ((0, -1, (px, py, px + TILE, py)), (0, 1, (px, py + TILE, px + TILE, py + TILE)),
                                     (-1, 0, (px, py, px, py + TILE)), (1, 0, (px + TILE, py, px + TILE, py + TILE))):
                    n = (x + dx, y + dy)
                    if not world.in_bounds(n) or world.owner_of(n) != owner:
                        scene.draw_line(*line, rgba(color, 210), 3, space="world", layer=RenderLayer.BACKGROUND)
        for pos in selection.reachable:
            scene.draw_rect(pos[0] * TILE + 4, pos[1] * TILE + 4, TILE - 8, TILE - 8, (255, 255, 255, 70), space="world", layer=RenderLayer.OBJECTS)
        for target in selection.targets:
            cx, cy = tile_center(target.pos)
            scene.draw_circle(cx, cy, TILE * 0.44, (255, 70, 70, 90), space="world", layer=RenderLayer.OBJECTS)
        human_color = world.tribes[self.human].color
        if selection.unit is not None:
            cx, cy = tile_center(selection.unit.pos)
            glow = 0.55 + 0.45 * math.sin(selection.pulse * 6)
            scene.draw_circle(cx, cy, TILE * 0.46, rgba(human_color, int(120 * glow)), space="world", layer=RenderLayer.OBJECTS)
        if selection.city_pos is not None:
            cx, cy = tile_center(selection.city_pos)
            scene.draw_rect(cx - TILE / 2, cy - TILE / 2, TILE, TILE, rgba(human_color, 70), space="world", layer=RenderLayer.OBJECTS)
        for city in world.cities.values():
            if city.pos not in explored:
                continue
            cx, cy = tile_center(city.pos)
            color = world.tribes[city.tribe].color
            scene.draw_text(city.name, cx + 1, cy - TILE * 0.42 + 1, style="city", color=(0, 0, 0, 200), anchor_x="center", anchor_y="bottom", space="world", layer=RenderLayer.UI_WORLD)
            scene.draw_text(city.name, cx, cy - TILE * 0.42, style="city", anchor_x="center", anchor_y="bottom", space="world", layer=RenderLayer.UI_WORLD)
            pip_w = 8
            total = city.level * (pip_w + 3) - 3
            for i in range(city.level):
                scene.draw_rect(cx - total / 2 + i * (pip_w + 3), cy + TILE * 0.32, pip_w, 6, rgba(color, 255), space="world", layer=RenderLayer.UI_WORLD)
        for u in world.units.values():
            if u.pos not in explored or u.hp >= u.max_hp:
                continue
            sprite = self._unit_sprites.get(u.id)
            if sprite is None:
                continue
            sx, sy = sprite.position
            bar_w = TILE * 0.5
            scene.draw_rect(sx - bar_w / 2, sy + TILE * 0.36, bar_w, 5, (0, 0, 0, 160), space="world", layer=RenderLayer.UI_WORLD)
            scene.draw_rect(sx - bar_w / 2, sy + TILE * 0.36, bar_w * u.hp / u.max_hp, 5, (110, 230, 110, 255), space="world", layer=RenderLayer.UI_WORLD)
        cx, cy = selection.cursor[0] * TILE, selection.cursor[1] * TILE
        for line in ((cx, cy, cx + TILE, cy), (cx + TILE, cy, cx + TILE, cy + TILE), (cx + TILE, cy + TILE, cx, cy + TILE), (cx, cy + TILE, cx, cy)):
            scene.draw_line(*line, (255, 255, 255, 230), 2.5, space="world", layer=RenderLayer.UI_WORLD)
