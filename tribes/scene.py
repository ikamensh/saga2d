"""saga2d scenes for Tribes: the map, and the overlays stacked on it."""

from __future__ import annotations

import math
import random

from saga2d import (
    Anchor, Button, Camera, Column, InputEvent, Label, Layout, MoveTo, Panel, ParticleEmitter, RenderLayer, Row, Scene,
    Sequence, Sprite, Style,
)
from tribes import ai, mapgen, textures
from tribes.model import City, Pos, RuleError, Unit, World
from tribes.rules import HARVEST, MAX_ROUNDS, TECHS, UNITS, Tech, UnitType
from tribes.textures import TILE

Color = tuple[int, int, int, int]
PANEL_BG = (22, 26, 40, 235)
PANEL_STYLE = Style(background_color=PANEL_BG, border_color=(70, 80, 110, 255), border_width=1, padding=12)
GHOST_BUTTON = Style(background_color=(40, 48, 72, 255), border_width=1, border_color=(90, 100, 140, 255), padding=8)


def rgba(color: tuple[int, int, int], alpha: int = 255) -> Color:
    return (color[0], color[1], color[2], alpha)


def tint(color: tuple[int, int, int]) -> tuple[float, float, float]:
    return (color[0] / 255, color[1] / 255, color[2] / 255)


def tile_center(pos: Pos) -> tuple[float, float]:
    return (pos[0] * TILE + TILE / 2, pos[1] * TILE + TILE / 2)


class MapScene(Scene):
    """The whole game: map, HUD, selection, and the turn loop."""

    background_color = rgba(textures.FOG)
    controls = {
        "e": "end_turn",
        ("tab", "n"): "next_unit",
        ("shift+tab", "shift+n"): "prev_unit",
        ("return", "space"): "act_at_cursor",
        "escape": "cancel",
        "t": "open_tech",
        "c": "capture",
        "h": "hold_unit",
        "up": "cursor_up",
        "down": "cursor_down",
        "left": "cursor_left",
        "right": "cursor_right",
        ("equal", "plus"): "zoom_in",
        "minus": "zoom_out",
        "home": "center_capital",
        "f5": "quick_save",
        "f9": "quick_load",
        ("f1", "slash", "question"): "open_help",
    }

    def __init__(self, world: World, seed: int) -> None:
        self.world = world
        self.seed = seed
        self.rng = random.Random(seed)
        self.human = next(t.id for t in world.tribes if t.human)
        self.cursor: Pos = (0, 0)
        self.selected_unit: int | None = None
        self.selected_city: int | None = None
        self.reachable: dict[Pos, Pos] = {}
        self.targets: list[Unit] = []
        self.status = ""
        self.status_timer = 0.0
        self.pulse = 0.0
        self.banner = ""
        self.banner_timer = 0.0
        self._tile_sprites: dict[Pos, Sprite] = {}
        self._resource_sprites: dict[Pos, Sprite] = {}
        self._site_sprites: dict[Pos, Sprite] = {}
        self._unit_sprites: dict[int, Sprite] = {}
        self._unit_targets: dict[int, Pos] = {}
        self._dragging = False

    # -- Lifecycle -------------------------------------------------------------

    def on_enter(self) -> None:
        textures.register_all(self.game)
        w, h = self.game.resolution
        extent = self.world.size * TILE
        fit = min(w, h) / (extent + TILE)
        self.camera = Camera((w, h), world_bounds=(-TILE, -TILE, extent + TILE, extent + TILE),
                             zoom=max(0.75, min(1.25, fit)), min_zoom=0.5, max_zoom=2.5)
        self.camera.enable_key_scroll(speed=700, bindings={"left": ("a",), "right": ("d",), "up": ("w",), "down": ("s",)})
        self._build_hud()
        for tile in self.world.all_tiles():
            self._tile_sprites[tile.pos] = self.add_sprite(Sprite(
                "tile.fog", position=tile_center(tile.pos), size=(TILE, TILE), layer=RenderLayer.BACKGROUND,
            ))
        self.sync()
        capital = self.world.capital_of(self.human)
        if capital is not None:
            self.cursor = capital.pos
            self.camera.center_on(*tile_center(capital.pos))
        self._show_banner(f"Round {self.world.round} — {self.tribe.name}")

    def on_reveal(self) -> None:
        self.sync()
        self._refresh_selection()

    @property
    def tribe(self):
        return self.world.tribes[self.human]

    # -- HUD -------------------------------------------------------------------

    def _build_hud(self) -> None:
        world = self.world
        tribe = self.tribe
        self.ui.add(Panel(anchor=Anchor.TOP_LEFT, margin=10, layout=Layout.HORIZONTAL, spacing=18, style=PANEL_STYLE, children=[
            Label(lambda: tribe.name, text_style="title"),
            Label(lambda: f"★ {tribe.stars}  (+{world.income(self.human)})", text_style="hud"),
            Label(lambda: f"Round {world.round}/{MAX_ROUNDS}", text_style="hud"),
            Label(lambda: f"Units {len(world.tribe_units(self.human))}/{world.unit_cap(self.human)}", text_style="sub"),
            Button("Tech", hotkey="[T]", on_click=self.open_tech, style=GHOST_BUTTON),
            Button("End turn", hotkey="[E]", on_click=self.end_turn, style=GHOST_BUTTON),
        ]))
        self.info_panel = Column(spacing=4, anchor=Anchor.BOTTOM_LEFT, margin=30, style=PANEL_STYLE)
        self.info_title = Label("", text_style="heading")
        self.info_lines = [Label("", text_style="body") for _ in range(4)]
        self.info_panel.add(self.info_title)
        for line in self.info_lines:
            self.info_panel.add(line)
        self.ui.add(self.info_panel)
        self.train_panel = Column(spacing=6, anchor=Anchor.BOTTOM_RIGHT, margin=30, style=PANEL_STYLE)
        self.train_panel.add(Label("Train", text_style="heading"))
        self.train_buttons: dict[UnitType, Button] = {}
        for unit_type, info in UNITS.items():
            button = Button(f"{unit_type.value.title()}  {info.cost}★", hotkey=f"[{info.hotkey}]",
                            on_click=lambda ut=unit_type: self.train(ut), style=GHOST_BUTTON, width=190)
            self.train_buttons[unit_type] = button
            self.train_panel.add(button)
        self.train_panel.visible = False
        self.ui.add(self.train_panel)
        self.ui.add(Label(
            "Click/Enter act · Tab next unit · E end turn · T tech · C capture · H hold · WASD pan · wheel zoom · F1 help",
            text_style="caption", anchor=Anchor.BOTTOM_CENTER, margin=6,
        ))
        self.ui.add(Label(lambda: "   ·   ".join(self.visible_log()[-2:]), text_style="sub", anchor=Anchor.TOP_RIGHT, margin=14))

    def visible_log(self) -> list[str]:
        """Log lines the player is entitled to see: those naming their tribe."""
        return [line for line in self.world.log if self.tribe.name in line]

    # -- Sprite reconciliation --------------------------------------------------

    def sync(self) -> None:
        """Make sprites match the model (idempotent)."""
        world = self.world
        explored = self.tribe.explored
        for pos in explored:
            tile = world.tile(pos)
            tile_sprite = self._tile_sprites[pos]
            if tile_sprite.image != f"tile.{tile.terrain.value}":
                tile_sprite.image = f"tile.{tile.terrain.value}"
            has_resource = tile.resource is not None and not tile.harvested
            if has_resource and pos not in self._resource_sprites:
                self._resource_sprites[pos] = self.add_sprite(Sprite(
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
                    sprite = self.add_sprite(Sprite(want, position=tile_center(pos), size=(TILE, TILE), layer=RenderLayer.OBJECTS))
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
                sprite = self.add_sprite(Sprite(
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

    def _animate_move(self, unit: Unit, path: list[Pos]) -> None:
        sprite = self._unit_sprites.get(unit.id)
        if sprite is None:
            return
        self._unit_targets[unit.id] = path[-1]
        sprite.do(Sequence(*[MoveTo(tile_center(p), speed=420) for p in path[1:]]))

    # -- Selection ---------------------------------------------------------------

    def _refresh_selection(self) -> None:
        unit = self.world.units.get(self.selected_unit) if self.selected_unit is not None else None
        if unit is None or unit.tribe != self.human:
            self.selected_unit = None
            self.reachable, self.targets = {}, []
        else:
            self.reachable = self.world.reachable(unit)
            self.targets = self.world.attack_targets(unit)
        city = self.world.cities.get(self.selected_city) if self.selected_city is not None else None
        if city is None or city.tribe != self.human:
            self.selected_city = None
        self.train_panel.visible = city is not None
        if city is not None:
            for unit_type, button in self.train_buttons.items():
                button.enabled = self.world.can_train(city, unit_type) is None
        self.sync()

    def select_unit(self, unit: Unit | None) -> None:
        self.selected_unit = unit.id if unit is not None else None
        self.selected_city = None
        self._refresh_selection()

    def select_city(self, city: City | None) -> None:
        self.selected_city = city.id if city is not None else None
        self.selected_unit = None
        self._refresh_selection()

    def cancel(self) -> None:
        if self.selected_unit is not None or self.selected_city is not None:
            self.select_unit(None)
        else:
            self.game.push(PauseScene(self))

    @property
    def selected(self) -> Unit | None:
        return self.world.units.get(self.selected_unit) if self.selected_unit is not None else None

    def _own_units_with_actions(self) -> list[Unit]:
        return sorted((u for u in self.world.tribe_units(self.human) if u.can_act), key=lambda u: u.id)

    def next_unit(self, step: int = 1) -> None:
        units = self._own_units_with_actions()
        if not units:
            self.say("No units left to move — press E to end the turn")
            return
        ids = [u.id for u in units]
        index = (ids.index(self.selected_unit) + step) % len(ids) if self.selected_unit in ids else (0 if step > 0 else -1)
        unit = units[index]
        self.select_unit(unit)
        self.cursor = unit.pos
        self.camera.pan_to(*tile_center(unit.pos), duration=0.25)

    def prev_unit(self) -> None:
        self.next_unit(-1)

    # -- Actions -----------------------------------------------------------------

    def say(self, text: str) -> None:
        self.status = text
        self.status_timer = 3.0

    def _show_banner(self, text: str) -> None:
        self.banner = text
        self.banner_timer = 2.0

    def act_at(self, pos: Pos) -> None:
        if self.world.winner is not None:
            return
        world = self.world
        self.cursor = pos
        unit = self.selected
        target = world.unit_at(pos)
        if unit is not None:
            if pos in self.reachable:
                self._move_selected(pos)
                return
            if target is not None and target in self.targets:
                self._attack_selected(target)
                return
            if pos == unit.pos:
                if world.can_capture(unit):
                    self.capture()
                else:
                    self.select_unit(None)
                return
        if target is not None and target.tribe == self.human and target is not unit:
            self.select_unit(target)
            if not target.can_act:
                self.say(f"{target.type.value.title()} has already acted this turn")
            return
        city = world.city_at(pos)
        if city is not None and city.tribe == self.human and target is None:
            self.select_city(city)
            return
        if world.owner_of(pos) == self.human and world.tile(pos).resource is not None and not world.tile(pos).harvested:
            self.harvest(pos)
            return
        if not world.explored(self.human, pos):
            self.say("Unexplored")
        self.select_unit(None)

    def act_at_cursor(self) -> None:
        self.act_at(self.cursor)

    def _move_selected(self, pos: Pos) -> None:
        unit = self.selected
        assert unit is not None
        path = self.world.move(unit, pos)
        self._animate_move(unit, path)
        self.cursor = pos
        self._refresh_selection()
        if not unit.can_act:
            self._advance_after_action(unit)

    def _attack_selected(self, target: Unit) -> None:
        unit = self.selected
        assert unit is not None
        result = self.world.attack(unit, target)
        self._burst(target.pos, rgba(self.world.tribes[target.tribe].color), 14)
        if result.defender_killed:
            self.say(f"{unit.type.value.title()} destroyed the {target.type.value}")
        else:
            self.say(f"Dealt {result.damage_dealt}, took {result.damage_taken}")
        if result.attacker_killed:
            self._burst(unit.pos, rgba(self.tribe.color), 14)
        self.camera.shake(4, 0.2)
        self.sync()
        self._refresh_selection()
        if unit.id in self.world.units and not unit.can_act:
            self._advance_after_action(unit)
        self._check_game_over()

    def _advance_after_action(self, unit: Unit) -> None:
        if self.world.unit_at(unit.pos) is unit and self.world.can_capture(unit):
            return
        self.select_unit(None)

    def capture(self) -> None:
        unit = self.selected
        if unit is None:
            unit = self.world.unit_at(self.cursor)
        if unit is None or unit.tribe != self.human:
            self.say("Select a unit standing on a village or enemy city")
            return
        try:
            city = self.world.capture(unit)
        except RuleError as exc:
            self.say(str(exc))
            return
        self._burst(city.pos, rgba(self.tribe.color), 24)
        self.say(f"{city.name} is yours")
        self.select_unit(None)
        self._check_game_over()

    def hold_unit(self) -> None:
        unit = self.selected
        if unit is None:
            self.say("No unit selected")
            return
        unit.done = True
        self.say(f"{unit.type.value.title()} holds position")
        self.select_unit(None)

    def train(self, unit_type: UnitType) -> None:
        city = self.world.cities.get(self.selected_city) if self.selected_city is not None else None
        if city is None:
            self.say("Select one of your cities first")
            return
        try:
            self.world.train(city, unit_type)
        except RuleError as exc:
            self.say(str(exc))
            return
        self.say(f"Trained a {unit_type.value} in {city.name}")
        self._refresh_selection()

    def harvest(self, pos: Pos) -> None:
        try:
            city = self.world.harvest(self.human, pos)
        except RuleError as exc:
            self.say(str(exc))
            return
        self._burst(pos, (255, 230, 120, 255), 12)
        self.say(f"{city.name}: {city.population}/{city.next_level_population} to level {city.level + 1}")
        self._refresh_selection()

    def end_turn(self) -> None:
        if self.world.winner is not None:
            return
        self.select_unit(None)
        self.world.end_turn()
        while self.world.winner is None and not self.world.current_tribe.human:
            ai.take_turn(self.world, self.world.current, self.rng)
        self.sync()
        self._show_banner(f"Round {self.world.round} — {self.tribe.name}")
        self._check_game_over()

    def _check_game_over(self) -> None:
        if self.world.winner is not None:
            self.game.push(GameOverScene(self))

    def _burst(self, pos: Pos, color: Color, count: int) -> None:
        emitter = ParticleEmitter("spark", position=tile_center(pos), speed=(60, 220), lifetime=(0.25, 0.6),
                                  size=(14, 14), shrink=True, tint=tint(color[:3]), rng=self.rng)
        emitter.burst(count)

    # -- Overlays / navigation -----------------------------------------------------

    def open_tech(self) -> None:
        self.game.push(TechScene(self))

    def open_help(self) -> None:
        self.game.push(HelpScene())

    def quick_save(self) -> None:
        self.game.save(1)
        self.say("Saved to slot 1")

    def quick_load(self) -> None:
        if self.game.save_manager.load(1) is None:
            self.say("No save in slot 1")
            return
        self.game.load(1)

    def center_capital(self) -> None:
        capital = self.world.capital_of(self.human) or next(iter(self.world.tribe_cities(self.human)), None)
        if capital is not None:
            self.cursor = capital.pos
            self.camera.pan_to(*tile_center(capital.pos), duration=0.3)

    def zoom_in(self) -> None:
        w, h = self.game.resolution
        self.camera.zoom_at(1.25, w / 2, h / 2)

    def zoom_out(self) -> None:
        w, h = self.game.resolution
        self.camera.zoom_at(0.8, w / 2, h / 2)

    def _move_cursor(self, dx: int, dy: int) -> None:
        x, y = self.cursor
        nx, ny = max(0, min(self.world.size - 1, x + dx)), max(0, min(self.world.size - 1, y + dy))
        self.cursor = (nx, ny)
        cx, cy = self.camera.world_to_screen(*tile_center(self.cursor))
        w, h = self.game.resolution
        margin = TILE * self.camera.zoom
        if not (margin < cx < w - margin and margin < cy < h - margin):
            self.camera.pan_to(*tile_center(self.cursor), duration=0.15)

    def cursor_up(self) -> None:
        self._move_cursor(0, -1)

    def cursor_down(self) -> None:
        self._move_cursor(0, 1)

    def cursor_left(self) -> None:
        self._move_cursor(-1, 0)

    def cursor_right(self) -> None:
        self._move_cursor(1, 0)

    # -- Raw input ---------------------------------------------------------------

    def handle_input(self, event: InputEvent) -> bool:
        if event.type == "key_press" and event.key is not None and event.key.isdigit():
            for unit_type, info in UNITS.items():
                if info.hotkey == event.key:
                    self.train(unit_type)
                    return True
        if event.type in ("click", "move", "drag", "release", "scroll"):
            pos = self._tile_at(event.world_x, event.world_y)
            if event.type == "click" and event.button == "left" and pos is not None:
                self.act_at(pos)
                return True
            if event.type == "click" and event.button == "right":
                self._dragging = True
                return True
            if event.type == "release" and event.button == "right":
                if self._dragging:
                    self._dragging = False
                    self.select_unit(None)
                return True
            if event.type == "drag" and event.button in ("right", "middle"):
                self._dragging = False
                self.camera.scroll(-event.dx / self.camera.zoom, -event.dy / self.camera.zoom)
                return True
            if event.type == "move" and pos is not None:
                self.cursor = pos
                return True
            if event.type == "scroll":
                self.camera.zoom_at(1.1 if event.dy > 0 else 1 / 1.1, event.x, event.y)
                return True
        return False

    def _tile_at(self, wx: float | None, wy: float | None) -> Pos | None:
        if wx is None or wy is None:
            return None
        pos = (int(math.floor(wx / TILE)), int(math.floor(wy / TILE)))
        return pos if self.world.in_bounds(pos) else None

    # -- Frame -------------------------------------------------------------------

    def update(self, dt: float) -> None:
        self.pulse += dt
        self.status_timer = max(0.0, self.status_timer - dt)
        self.banner_timer = max(0.0, self.banner_timer - dt)
        self._update_info()

    def _update_info(self) -> None:
        world = self.world
        lines: list[str] = []
        unit = self.selected
        city = world.cities.get(self.selected_city) if self.selected_city is not None else None
        hovered = world.unit_at(self.cursor)
        if unit is not None:
            info = unit.info
            title = f"{unit.type.value.title()}  {unit.hp}/{unit.max_hp} hp"
            lines.append(f"Attack {info.attack:g}  Defense {info.defense:g}  Move {info.movement}  Range {info.range}")
            state = []
            if unit.can_move:
                state.append("can move")
            if unit.can_attack:
                state.append("can attack")
            if world.can_capture(unit):
                state.append("can capture [C]")
            lines.append(", ".join(state) if state else "done for this turn")
            if hovered is not None and hovered in self.targets:
                dealt, taken = world.combat_preview(unit, hovered)
                lines.append(f"Attack {hovered.type.value}: deal {dealt}, take {taken if world.distance(unit.pos, hovered.pos) <= hovered.info.range else 0}")
        elif city is not None:
            title = f"{city.name}  level {city.level}" + ("  (capital)" if city.capital else "")
            lines.append(f"Population {city.population}/{city.next_level_population}   Income +{city.income}")
            lines.append("Pick a unit to train (1-5), or click a resource in your borders to harvest")
        else:
            tile = world.tile(self.cursor)
            title = f"{tile.terrain.value.title()} ({self.cursor[0]}, {self.cursor[1]})"
            if not world.explored(self.human, self.cursor):
                title = "Unexplored"
            else:
                owner = world.owner_of(self.cursor)
                if owner is not None:
                    lines.append(f"Territory of {world.tribes[owner].name}")
                if tile.resource is not None and not tile.harvested:
                    h = HARVEST[tile.resource]
                    reason = world.can_harvest(self.human, self.cursor)
                    lines.append(f"{tile.resource.value.title()}: {h.label} {h.cost}★ → +{h.population} pop" + (f"  ({reason})" if reason else "  [Enter]"))
                if tile.village:
                    lines.append("Village — capture with a unit that starts its turn here")
                if hovered is not None:
                    lines.append(f"{world.tribes[hovered.tribe].name} {hovered.type.value} {hovered.hp}/{hovered.max_hp} hp")
        if self.status_timer > 0:
            lines.append(self.status)
        self.info_title.text = title
        for label, text in zip(self.info_lines, lines + [""] * 4):
            label.text = text
            label.visible = bool(text)

    def draw(self) -> None:
        world = self.world
        explored = self.tribe.explored
        cam = self.camera
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
                self.draw_rect(px, py, TILE, TILE, rgba(color, 40), space="world", layer=RenderLayer.BACKGROUND)
                for dx, dy, line in ((0, -1, (px, py, px + TILE, py)), (0, 1, (px, py + TILE, px + TILE, py + TILE)),
                                     (-1, 0, (px, py, px, py + TILE)), (1, 0, (px + TILE, py, px + TILE, py + TILE))):
                    n = (x + dx, y + dy)
                    if not world.in_bounds(n) or world.owner_of(n) != owner:
                        self.draw_line(*line, rgba(color, 210), 3, space="world", layer=RenderLayer.BACKGROUND)
        for pos in self.reachable:
            self.draw_rect(pos[0] * TILE + 4, pos[1] * TILE + 4, TILE - 8, TILE - 8, (255, 255, 255, 70), space="world", layer=RenderLayer.OBJECTS)
        for target in self.targets:
            cx, cy = tile_center(target.pos)
            self.draw_circle(cx, cy, TILE * 0.44, (255, 70, 70, 90), space="world", layer=RenderLayer.OBJECTS)
        unit = self.selected
        if unit is not None:
            cx, cy = tile_center(unit.pos)
            glow = 0.55 + 0.45 * math.sin(self.pulse * 6)
            self.draw_circle(cx, cy, TILE * 0.46, rgba(self.tribe.color, int(120 * glow)), space="world", layer=RenderLayer.OBJECTS)
        city_sel = world.cities.get(self.selected_city) if self.selected_city is not None else None
        if city_sel is not None:
            cx, cy = tile_center(city_sel.pos)
            self.draw_rect(cx - TILE / 2, cy - TILE / 2, TILE, TILE, rgba(self.tribe.color, 70), space="world", layer=RenderLayer.OBJECTS)
        for city in world.cities.values():
            if city.pos not in explored:
                continue
            cx, cy = tile_center(city.pos)
            color = world.tribes[city.tribe].color
            self.draw_text(city.name, cx + 1, cy - TILE * 0.42 + 1, style="city", color=(0, 0, 0, 200), anchor_x="center", anchor_y="bottom", space="world", layer=RenderLayer.UI_WORLD)
            self.draw_text(city.name, cx, cy - TILE * 0.42, style="city", anchor_x="center", anchor_y="bottom", space="world", layer=RenderLayer.UI_WORLD)
            pip_w = 8
            total = city.level * (pip_w + 3) - 3
            for i in range(city.level):
                self.draw_rect(cx - total / 2 + i * (pip_w + 3), cy + TILE * 0.32, pip_w, 6, rgba(color, 255), space="world", layer=RenderLayer.UI_WORLD)
        for u in world.units.values():
            if u.pos not in explored or u.hp >= u.max_hp:
                continue
            sprite = self._unit_sprites.get(u.id)
            if sprite is None:
                continue
            sx, sy = sprite.position
            bar_w = TILE * 0.5
            self.draw_rect(sx - bar_w / 2, sy + TILE * 0.36, bar_w, 5, (0, 0, 0, 160), space="world", layer=RenderLayer.UI_WORLD)
            self.draw_rect(sx - bar_w / 2, sy + TILE * 0.36, bar_w * u.hp / u.max_hp, 5, (110, 230, 110, 255), space="world", layer=RenderLayer.UI_WORLD)
        cx, cy = self.cursor[0] * TILE, self.cursor[1] * TILE
        for line in ((cx, cy, cx + TILE, cy), (cx + TILE, cy, cx + TILE, cy + TILE), (cx + TILE, cy + TILE, cx, cy + TILE), (cx, cy + TILE, cx, cy)):
            self.draw_line(*line, (255, 255, 255, 230), 2.5, space="world", layer=RenderLayer.UI_WORLD)
        w, h = self.game.resolution
        self.draw_rect(0, h - 26, w, 26, (0, 0, 0, 150))
        if self.banner_timer > 0:
            alpha = int(255 * min(1.0, self.banner_timer / 0.5))
            self.draw_rect(0, h * 0.42, w, 60, (0, 0, 0, int(alpha * 0.55)))
            self.draw_text(self.banner, w / 2, h * 0.42 + 30, style="banner", color=(255, 255, 255, alpha), anchor_x="center", anchor_y="center")

    # -- Save / load ---------------------------------------------------------------

    def get_save_state(self) -> dict:
        return {"seed": self.seed, "world": self.world.to_dict()}

    def load_save_state(self, state: dict) -> None:
        self.world = World.from_dict(state["world"])
        self.seed = state["seed"]
        for sprite in [*self._resource_sprites.values(), *self._site_sprites.values(), *self._unit_sprites.values()]:
            sprite.remove()
        for sprite in self._tile_sprites.values():
            sprite.image = "tile.fog"
        self._resource_sprites.clear()
        self._site_sprites.clear()
        self._unit_sprites.clear()
        self._unit_targets.clear()
        self.ui.clear()
        self._build_hud()
        self.select_unit(None)
        self.say("Loaded slot 1")


class _Overlay(Scene):
    """Transparent modal panel; Escape closes."""

    transparent = True
    pop_on_cancel = True

    def panel(self, title: str) -> Column:
        panel = Column(spacing=8, anchor=Anchor.CENTER, style=PANEL_STYLE)
        panel.add(Label(title, text_style="title"))
        self.ui.add(panel)
        return panel

    def draw(self) -> None:
        w, h = self.game.resolution
        self.draw_rect(0, 0, w, h, (0, 0, 0, 120))


class TechScene(_Overlay):
    controls = {"t": "close"}

    def __init__(self, map_scene: MapScene) -> None:
        self.map_scene = map_scene

    def on_enter(self) -> None:
        world = self.map_scene.world
        tribe = self.map_scene.tribe
        panel = self.panel(f"Research   ★ {tribe.stars}")
        for index, (tech, info) in enumerate(TECHS.items()):
            key = str((index + 1) % 10)
            known = tech in tribe.techs
            reason = world.can_research(tribe.id, tech)
            button = Button(tech.value.title(), hotkey=f"[{key}]", on_click=lambda t=tech: self.buy(t), style=GHOST_BUTTON, width=180)
            button.enabled = reason is None
            cost = "known" if known else f"{world.tech_cost(tribe.id, tech)}★"
            requires = TECHS[tech].requires
            detail = info.summary if known or requires is None or requires in tribe.techs else f"{info.summary}  (needs {requires.value.title()})"
            panel.add(Row(button, Label(cost, text_style="hud", width=64, align="right"), Label(detail, text_style="body", width=330), spacing=14))
            self.bind_key(key, lambda t=tech: self.buy(t))
        panel.add(Label("Esc / T to close", text_style="caption"))

    def buy(self, tech: Tech) -> None:
        world = self.map_scene.world
        reason = world.can_research(self.map_scene.human, tech)
        if reason is not None:
            return
        world.research(self.map_scene.human, tech)
        self.map_scene.say(f"Learned {tech.value.title()}")
        self.game.pop()

    def close(self) -> None:
        self.game.pop()


class PauseScene(_Overlay):
    controls = {"n": "new_game", "q": "quit", "f5": "save", "f9": "load"}

    def __init__(self, map_scene: MapScene) -> None:
        self.map_scene = map_scene

    def on_enter(self) -> None:
        panel = self.panel("Paused")
        panel.add(Button("Resume", hotkey="[Esc]", on_click=self.game.pop, style=GHOST_BUTTON, width=260))
        panel.add(Button("Save", hotkey="[F5]", on_click=self.save, style=GHOST_BUTTON, width=260))
        panel.add(Button("Load", hotkey="[F9]", on_click=self.load, style=GHOST_BUTTON, width=260))
        panel.add(Button("New game", hotkey="[N]", on_click=self.new_game, style=GHOST_BUTTON, width=260))
        panel.add(Button("Quit", hotkey="[Q]", on_click=self.quit, style=GHOST_BUTTON, width=260))

    def save(self) -> None:
        self.game.pop()
        self.map_scene.quick_save()

    def load(self) -> None:
        self.game.pop()
        self.map_scene.quick_load()

    def new_game(self) -> None:
        self.game.clear_and_push(new_game(self.map_scene.seed + 1))

    def quit(self) -> None:
        self.game.quit()


class HelpScene(_Overlay):
    def on_enter(self) -> None:
        panel = self.panel("How to play")
        for line in (
            "Capture villages to grow your empire; take every enemy city to win.",
            "Harvest resources inside your borders to level cities up (more stars, more units).",
            "",
            "Enter / click      act at the cursor: select, move, attack, harvest, capture",
            "Arrows             move the cursor        WASD / right-drag   pan the map",
            "Tab / Shift+Tab    next / previous unit   Wheel, + / -        zoom",
            "E                  end turn               T                   research",
            "C                  capture                H                   hold (unit heals)",
            "1-5                train in selected city F5 / F9             save / load",
            "Home               jump to capital        Esc                 cancel / menu",
        ):
            panel.add(Label(line, text_style="body", font="Menlo", width=760))
        panel.add(Label("Esc to close", text_style="caption"))


class GameOverScene(_Overlay):
    pop_on_cancel = False
    controls = {"n": "new_game", "q": "quit"}

    def __init__(self, map_scene: MapScene) -> None:
        self.map_scene = map_scene

    def on_enter(self) -> None:
        world = self.map_scene.world
        winner = world.tribes[world.winner]
        verdict = "Victory!" if winner.id == self.map_scene.human else f"{winner.name} wins"
        panel = self.panel(verdict)
        for tribe in sorted(world.tribes, key=lambda t: -world.score(t.id)):
            panel.add(Label(f"{tribe.name:<8} {world.score(tribe.id):>5} points", text_style="body", font="Menlo", width=260))
        panel.add(Button("New game", hotkey="[N]", on_click=self.new_game, style=GHOST_BUTTON, width=260))
        panel.add(Button("Quit", hotkey="[Q]", on_click=self.game.quit, style=GHOST_BUTTON, width=260))

    def new_game(self) -> None:
        self.game.clear_and_push(new_game(self.map_scene.seed + 1))

    def quit(self) -> None:
        self.game.quit()


def new_game(seed: int, size: int = 14, tribes: int = 3) -> MapScene:
    return MapScene(mapgen.generate(seed=seed, size=size, tribe_count=tribes), seed)
