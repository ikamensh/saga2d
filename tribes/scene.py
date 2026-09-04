"""saga2d scenes for Tribes: the map, and the overlays stacked on it."""

from __future__ import annotations

import math
import random
from collections import deque
from typing import Any

from saga2d import (
    Anchor, Button, Camera, Column, Delay, InputEvent, Label, Layout, MoveTo, Panel, ProgressBar, RenderLayer, Row,
    Scene, Sequence, Sprite, Style,
)
from tribes import ai, effects, mapgen
from tribes.effects import Banner, Burst, Dissolve, Effects, FloatingText, HitReaction, TilePulse, Toast, hop, play_sound
from tribes.model import City, CombatResult, Pos, RuleError, Unit, World
from tribes.rules import HARVEST, MAX_ROUNDS, TECHS, UNITS, Tech, UnitType
from tribes.textures import FOG, TILE
from tribes.view import MapView, Selection, rgba, tile_at, tile_center, tint

PANEL_BG = (22, 26, 40, 235)
PANEL_STYLE = Style(background_color=PANEL_BG, border_color=(70, 80, 110, 255), border_width=1, padding=12)
GHOST_BUTTON = Style(background_color=(40, 48, 72, 255), border_width=1, border_color=(90, 100, 140, 255), padding=8)
ACTION_BUTTON = Style(background_color=(52, 88, 150, 255), border_width=1, border_color=(120, 165, 235, 255), padding=8)
DANGER_BUTTON = Style(background_color=(140, 58, 58, 255), border_width=1, border_color=(225, 110, 100, 255), padding=8)

DEFAULT_SETTINGS: dict[str, Any] = {"music": 0.7, "sfx": 0.8, "confirm_end_turn": True}
DAMAGE_COLOR = (255, 96, 84, 255)
HEAL_COLOR = (130, 235, 130, 255)
GOLD = (255, 224, 120, 255)

HIT_TIME = 0.16  # seconds from the start of a lunge until the blow lands


def _plural(count: int, noun: str) -> str:
    return f"{count} {noun}{'' if count == 1 else 's'}"


class MapScene(Scene):
    """The whole game: map, HUD, selection, effects and the turn loop."""

    background_color = rgba(FOG)
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

    def __init__(self, world: World, seed: int, *, settings: dict[str, Any] | None = None, stats: dict[str, int] | None = None) -> None:
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
        self.effects = Effects()
        self.settings: dict[str, Any] = {**DEFAULT_SETTINGS, **(settings or {})}
        self.stats: dict[str, int] = {"units_lost": 0, "units_killed": 0, "cities_taken": 0, **(stats or {})}
        self.recent_sounds: deque[str] = deque(maxlen=32)
        self._end_turn_armed_until = 0.0
        self._dragging = False
        self._hover_target: Unit | None = None
        self._harvest_pos: Pos | None = None

    # -- Lifecycle -------------------------------------------------------------

    def on_enter(self) -> None:
        effects.apply_volumes(self.settings)
        self.view = MapView(self, self.world, self.human, self.rng)
        self.hover_glow = self.add_sprite(Sprite("glow.soft", position=tile_center(self.cursor), size=(TILE * 1.7, TILE * 1.7),
                                                 layer=RenderLayer.OBJECTS, opacity=0))
        self._setup_camera()
        self._build_hud()
        capital = self.world.capital_of(self.human)
        if capital is not None:
            self.cursor = capital.pos
            self.camera.center_on(*tile_center(capital.pos))
        self._turn_banner()

    def _setup_camera(self) -> None:
        w, h = self.game.resolution
        left, top, right, bottom = self.view.world_bounds
        fit = min(w, h) / (right - left)
        pad = TILE * 3.5  # slack so any tile can be scrolled out from under the HUD panels
        bounds = (left - pad, top - pad, right + pad, bottom + pad)
        self.camera = Camera((w, h), world_bounds=bounds, zoom=max(0.75, min(1.25, fit)), min_zoom=0.5, max_zoom=2.5)
        self.camera.enable_key_scroll(speed=700, bindings={"left": ("a",), "right": ("d",), "up": ("w",), "down": ("s",)})

    def on_reveal(self) -> None:
        self._refresh_selection()

    def sync(self) -> None:
        self.view.sync()

    @property
    def tribe(self):
        return self.world.tribes[self.human]

    def sfx(self, name: str) -> None:
        """Every sound event passes through here (see :func:`tribes.effects.play_sound`)."""
        self.recent_sounds.append(name)
        if self.settings["sfx"] > 0:
            play_sound(name)

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
            Button(lambda: "Confirm end turn" if self._end_turn_armed else "End turn", hotkey="[E]", on_click=self.end_turn, style=GHOST_BUTTON),
        ]))
        self.info_panel = Column(spacing=6, anchor=Anchor.BOTTOM_LEFT, margin=30, style=PANEL_STYLE)
        self.info_title = Label("", text_style="heading")
        self.info_panel.add(self.info_title)
        self.city_bar = ProgressBar(value=lambda: self._city().population if self._city() else 0,
                                    max_value=lambda: self._city().next_level_population if self._city() else 1,
                                    width=220, height=10, bar_color=(255, 215, 110, 255))
        self.city_bar_row = Row(Label("Growth", text_style="sub"), self.city_bar,
                                Label(lambda: f"{self._city().population}/{self._city().next_level_population}" if self._city() else "", text_style="sub"),
                                spacing=10)
        self.city_bar_row.visible = False
        self.info_panel.add(self.city_bar_row)
        self.info_lines = [Label("", text_style="body") for _ in range(4)]
        for line in self.info_lines:
            self.info_panel.add(line)
        self.btn_capture = Button("Capture", hotkey="[C]", on_click=self.capture, style=ACTION_BUTTON)
        self.btn_hold = Button("Hold", hotkey="[H]", on_click=self.hold_unit, style=GHOST_BUTTON)
        self.btn_harvest = Button(lambda: HARVEST[world.tile(self._harvest_pos).resource].label if self._harvest_pos else "Harvest",
                                  hotkey="[Enter]", on_click=self._harvest_button, style=ACTION_BUTTON)
        self.btn_attack = Button("Attack", hotkey="[Enter]", on_click=self._attack_button, style=DANGER_BUTTON)
        self.action_row = Row(self.btn_capture, self.btn_hold, self.btn_harvest, self.btn_attack, spacing=8)
        for button in (self.btn_capture, self.btn_hold, self.btn_harvest, self.btn_attack):
            button.visible = False
        self.action_row.visible = False
        self.info_panel.add(self.action_row)
        self.ui.add(self.info_panel)

        self.train_panel = Column(spacing=6, anchor=Anchor.BOTTOM_RIGHT, margin=30, style=PANEL_STYLE)
        self.train_panel.add(Label("Train", text_style="heading"))
        self.train_buttons: dict[UnitType, Button] = {}
        for unit_type, info in UNITS.items():
            button = Button(f"{unit_type.value.title()}  {info.cost}★", hotkey=f"[{info.hotkey}]",
                            on_click=lambda ut=unit_type: self.train(ut), style=GHOST_BUTTON, width=170)
            self.train_buttons[unit_type] = button
            reason = Label(lambda ut=unit_type: self._train_reason(ut), text_style="caption", width=150)
            self.train_panel.add(Row(button, reason, spacing=8))
        self.train_panel.visible = False
        self.ui.add(self.train_panel)
        self.ui.add(Label(self._hint, text_style="caption", anchor=Anchor.BOTTOM_CENTER, margin=6))
        self.ui.add(Label(lambda: "   ·   ".join(self.visible_log()[-2:]), text_style="sub", anchor=Anchor.TOP_RIGHT, margin=14))

    def _hint(self) -> str:
        if self.selected is not None:
            return "Enter/click move or attack · C capture · H hold · Tab next unit · Esc deselect · F1 help"
        if self._city() is not None:
            return "1-5 train · click a glowing resource to harvest · Esc deselect · F1 help"
        return "Click/Enter act · Tab next unit · E end turn · T tech · WASD pan · wheel zoom · Esc menu · F1 help"

    def _city(self) -> City | None:
        return self.world.cities.get(self.selected_city) if self.selected_city is not None else None

    def _train_reason(self, unit_type: UnitType) -> str:
        city = self._city()
        if city is None:
            return ""
        reason = self.world.can_train(city, unit_type)
        if reason is None:
            return ""
        if reason.startswith("Costs"):
            return f"{reason[6:]} needed, have {self.tribe.stars}★"
        return reason[0].lower() + reason[1:]

    def visible_log(self) -> list[str]:
        """Log lines the player is entitled to see: those naming their tribe."""
        return [line for line in self.world.log if self.tribe.name in line]

    @staticmethod
    def _set_visible(component, visible: bool) -> None:
        if component.visible != visible:
            component.visible = visible
            component.invalidate_layout()

    def _over_ui(self, x: float, y: float) -> bool:
        return any(child.visible and child.hit_test(x, y) for child in self.ui.children)

    # -- Selection ---------------------------------------------------------------

    def _refresh_selection(self) -> None:
        self._end_turn_armed_until = 0.0
        unit = self.world.units.get(self.selected_unit) if self.selected_unit is not None else None
        if unit is None or unit.tribe != self.human:
            self.selected_unit = None
            self.reachable, self.targets = {}, []
        else:
            self.reachable = self.world.reachable(unit)
            self.targets = self.world.attack_targets(unit)
        city = self._city()
        if city is None or city.tribe != self.human:
            self.selected_city = None
            city = None
        self._set_visible(self.train_panel, city is not None)
        self._set_visible(self.city_bar_row, city is not None)
        if city is not None:
            for unit_type, button in self.train_buttons.items():
                button.enabled = self.world.can_train(city, unit_type) is None
        self.view.sync()

    def select_unit(self, unit: Unit | None) -> None:
        changed = unit is not None and unit.id != self.selected_unit
        self.selected_unit = unit.id if unit is not None else None
        self.selected_city = None
        self._refresh_selection()
        if changed and unit is not None:
            hop(self.view.unit_sprite(unit.id), tile_center(unit.pos))
            self.sfx("select")

    def select_city(self, city: City | None) -> None:
        changed = city is not None and city.id != self.selected_city
        self.selected_city = city.id if city is not None else None
        self.selected_unit = None
        self._refresh_selection()
        if changed and city is not None:
            self.effects.add(TilePulse(tile_center(city.pos), rgba(self.tribe.color, 160), radius=(10, 40), rings=1, duration=0.5))
            self.sfx("select")

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

    def warn(self, text: str) -> None:
        """A refused action: say why and play the error sound."""
        self.say(text)
        self.sfx("error")

    def _turn_banner(self) -> None:
        self.effects.add(Banner(f"Round {self.world.round}", subtitle=f"{self.tribe.name} — your turn", accent=rgba(self.tribe.color)))

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
        self.view.animate_move(unit, path)
        self.sfx("move")
        self.cursor = pos
        self._refresh_selection()
        if not unit.can_act:
            self.select_unit(None)

    def _attack_selected(self, target: Unit) -> None:
        unit = self.selected
        assert unit is not None
        origin, target_pos = unit.pos, target.pos
        attacker_sprite, target_sprite = self.view.unit_sprite(unit.id), self.view.unit_sprite(target.id)
        blocked = self.world.defense_bonus(target) > 1.0
        result = self.world.attack(unit, target)
        self._animate_attack(result, origin, target_pos, attacker_sprite, target_sprite)
        self.view.sync()
        if result.defender_killed:
            self.stats["units_killed"] += 1
            self.say(f"{unit.type.value.title()} destroyed the {target.type.value}")
            self.after(HIT_TIME, lambda: self.sfx("attack_kill"))
        else:
            self.say(f"Dealt {result.damage_dealt}, took {result.damage_taken}")
            self.after(HIT_TIME, lambda: self.sfx("attack_blocked" if blocked else "attack_hit"))
        if result.attacker_killed:
            self.stats["units_lost"] += 1
        self._refresh_selection()
        if unit.id not in self.world.units or not unit.can_act:
            self.select_unit(None)
        self._check_game_over()

    def _animate_attack(self, result: CombatResult, origin: Pos, target_pos: Pos, attacker_sprite: Sprite | None, target_sprite: Sprite | None) -> None:
        """Lunge, flash, damage numbers, knockback, dissolve — timed around ``HIT_TIME``."""
        world, effects = self.world, self.effects
        attacker, defender = result.attacker, result.defender
        home, there = tile_center(origin), tile_center(target_pos)
        lunge = (home[0] + (there[0] - home[0]) * 0.45, home[1] + (there[1] - home[1]) * 0.45)
        speed = max(1.0, math.dist(home, lunge) / HIT_TIME)
        defender_tint = tint(world.tribes[defender.tribe].color)
        attacker_tint = tint(world.tribes[attacker.tribe].color)

        victim = target_sprite
        if result.defender_killed and target_sprite is not None:
            victim = self._ghost(target_sprite)  # the view removes the real sprite on sync
        if victim is not None:
            effects.add(HitReaction(victim, defender_tint, source=home, delay=HIT_TIME))
            if result.defender_killed:
                effects.add(Dissolve(victim, delay=HIT_TIME + 0.2))
        effects.add(FloatingText(f"-{result.damage_dealt}", (there[0], there[1] - TILE * 0.45), DAMAGE_COLOR, font_size=20, delay=HIT_TIME))
        effects.add(Burst(there, rgba(world.tribes[defender.tribe].color), 18 if result.defender_killed else 12, rng=self.rng, delay=HIT_TIME))
        self.after(HIT_TIME, lambda: self.camera.shake(5 if result.defender_killed else 3, 0.2))

        if attacker_sprite is None:
            return
        if result.attacker_killed:
            ghost = self._ghost(attacker_sprite)
            ghost.do(Sequence(MoveTo(lunge, speed=speed), MoveTo(home, speed=speed)))
            effects.add(HitReaction(ghost, attacker_tint, knockback=0.0, delay=HIT_TIME + 0.25))
            effects.add(Dissolve(ghost, delay=HIT_TIME + 0.45))
        elif attacker.pos != origin:
            self.view.animate_move(attacker, [origin, attacker.pos])  # registers the new tile with the view
            attacker_sprite.do(Sequence(MoveTo(lunge, speed=speed), Delay(0.12), MoveTo(tile_center(attacker.pos), speed=420)))
        else:
            attacker_sprite.do(Sequence(MoveTo(lunge, speed=speed), MoveTo(home, speed=speed)))
            if result.damage_taken > 0:
                effects.add(HitReaction(attacker_sprite, attacker_tint, knockback=0.0, wobble=8.0, delay=HIT_TIME + 0.25))
        if result.damage_taken > 0:
            effects.add(FloatingText(f"-{result.damage_taken}", (home[0], home[1] - TILE * 0.45), DAMAGE_COLOR, delay=HIT_TIME + 0.25))

    def _ghost(self, sprite: Sprite) -> Sprite:
        """A scene-owned copy of a unit sprite that outlives the model's unit."""
        return self.add_sprite(Sprite(sprite.image, position=sprite.position, size=sprite.size, layer=sprite.layer, tint=sprite.tint, opacity=sprite.opacity))

    def _attack_button(self) -> None:
        target = self._hover_target
        if target is not None and target in self.targets and self.selected is not None:
            self._attack_selected(target)

    def _harvest_button(self) -> None:
        if self._harvest_pos is not None:
            self.harvest(self._harvest_pos)

    def capture(self) -> None:
        unit = self.selected
        if unit is None:
            unit = self.world.unit_at(self.cursor)
        if unit is None or unit.tribe != self.human:
            self.warn("Select a unit standing on a village or enemy city")
            return
        try:
            city = self.world.capture(unit)
        except RuleError as exc:
            self.warn(str(exc))
            return
        self.stats["cities_taken"] += 1
        color = rgba(self.tribe.color)
        center = tile_center(city.pos)
        self.effects.add(Burst(center, color, 24, rng=self.rng))
        self.effects.add(TilePulse(center, color, radius=(12, TILE * 1.2), rings=3, duration=1.1))
        self.effects.add(FloatingText(city.name, (center[0], center[1] - TILE * 0.8), GOLD, font_size=22, rise=36, duration=1.4))
        self.camera.shake(3, 0.25)
        self.say(f"{city.name} is yours")
        self.sfx("capture")
        self.select_unit(None)
        self._check_game_over()

    def hold_unit(self) -> None:
        unit = self.selected
        if unit is None:
            self.warn("No unit selected")
            return
        unit.done = True
        self.say(f"{unit.type.value.title()} holds position")
        self.sfx("button")
        self.select_unit(None)

    def train(self, unit_type: UnitType) -> None:
        city = self._city()
        if city is None:
            self.warn("Select one of your cities first")
            return
        try:
            unit = self.world.train(city, unit_type)
        except RuleError as exc:
            self.warn(str(exc))
            return
        self.say(f"Trained a {unit_type.value} in {city.name}")
        self.sfx("train")
        self._refresh_selection()
        hop(self.view.unit_sprite(unit.id), tile_center(unit.pos), height=14, speed=320)
        self.effects.add(TilePulse(tile_center(city.pos), rgba(self.tribe.color, 150), radius=(8, 34), rings=1, duration=0.45))

    def harvest(self, pos: Pos) -> None:
        tile = self.world.tile(pos)
        level_before = self.world.cities[tile.owner_city].level if tile.owner_city is not None else 0
        try:
            city = self.world.harvest(self.human, pos)
        except RuleError as exc:
            self.warn(str(exc))
            return
        gained = HARVEST[tile.resource].population  # type: ignore[index]
        center = tile_center(pos)
        self.effects.add(Burst(center, (255, 230, 120, 255), 12, rng=self.rng))
        self.effects.add(FloatingText(f"+{gained} pop", (center[0], center[1] - TILE * 0.2), HEAL_COLOR))
        self.sfx("harvest")
        self.say(f"{city.name}: {city.population}/{city.next_level_population} to level {city.level + 1}")
        if city.level > level_before:
            self._celebrate_level(city)
        self._refresh_selection()

    def _celebrate_level(self, city: City) -> None:
        center = tile_center(city.pos)
        color = rgba(self.tribe.color)
        self.effects.add(TilePulse(center, color, radius=(14, TILE * 1.4), rings=3, duration=1.2, delay=0.35))
        self.effects.add(FloatingText(f"Level {city.level}!", (center[0], center[1] - TILE * 0.8), GOLD, font_size=24, rise=40, duration=1.6, delay=0.4))
        self.effects.add(Burst(center, color, 26, rng=self.rng, delay=0.4))
        self.after(0.4, lambda: self.sfx("level_up"))

    @property
    def _end_turn_armed(self) -> bool:
        return self.pulse < self._end_turn_armed_until

    def end_turn(self) -> None:
        if self.world.winner is not None:
            return
        waiting = self._own_units_with_actions()
        if waiting and self.settings["confirm_end_turn"] and not self._end_turn_armed:
            self._end_turn_armed_until = self.pulse + 3.5
            self.say(f"{_plural(len(waiting), 'unit')} can still act — press E again to end turn")
            return
        self._end_turn_armed_until = 0.0
        self.select_unit(None)
        before = self._snapshot()
        self.sfx("end_turn")
        self.world.end_turn()
        while self.world.winner is None and not self.world.current_tribe.human:
            ai.take_turn(self.world, self.world.current, self.rng)
        self.view.sync()
        lost, news = self._while_away(before)
        self.stats["units_lost"] += lost
        if news:
            self.effects.add(Toast("While you were away", news))
        self._turn_banner()
        self.sfx("turn_start")
        self._check_game_over()

    def _snapshot(self) -> dict[str, Any]:
        return {
            "units": {u.id: (u.type, u.hp) for u in self.world.tribe_units(self.human)},
            "cities": {c.id: c.name for c in self.world.tribe_cities(self.human)},
            "log": len(self.world.log),
        }

    def _while_away(self, before: dict[str, Any]) -> tuple[int, list[str]]:
        """``(units lost, news lines)`` comparing the world with a pre-AI snapshot."""
        world = self.world
        news: list[str] = []
        for city_id, name in before["cities"].items():
            city = world.cities[city_id]
            if city.tribe != self.human:
                news.append(f"Lost {name} to {world.tribes[city.tribe].name}")
        lost = [t for uid, (t, _hp) in before["units"].items() if uid not in world.units]
        for unit_type in sorted(set(lost), key=lambda t: t.value):
            news.append(f"Lost {_plural(lost.count(unit_type), unit_type.value)}")
        for uid, (unit_type, hp) in before["units"].items():
            unit = world.units.get(uid)
            if unit is not None and unit.hp < hp:
                where = world.city_at(unit.pos)
                place = f"in {where.name}" if where is not None and where.tribe == self.human else f"at ({unit.x}, {unit.y})"
                news.append(f"{unit_type.value.title()} {place} took {hp - unit.hp} damage")
        for line in world.log[before["log"]:]:
            if line.endswith("has fallen") and self.tribe.name not in line:
                news.append(line)
        return len(lost), news[:6]

    def _check_game_over(self) -> None:
        if self.world.winner is not None:
            self.sfx("victory" if self.world.winner == self.human else "defeat")
            self.game.push(GameOverScene(self))

    # -- Overlays / navigation -----------------------------------------------------

    def open_tech(self) -> None:
        self.game.push(TechScene(self))

    def open_help(self) -> None:
        self.game.push(HelpScene())

    def open_settings(self) -> None:
        self.game.push(SettingsScene(self))

    def quick_save(self) -> None:
        self.game.save(1)
        self.say("Saved to slot 1")
        self.sfx("button")

    def quick_load(self) -> None:
        if self.game.save_manager.load(1) is None:
            self.warn("No save in slot 1")
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
            over_ui = event.type in ("click", "move") and self._over_ui(event.x, event.y)
            if event.type == "click" and event.button == "left":
                if pos is not None and not over_ui:
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
            if event.type == "move":
                if pos is not None and not over_ui:
                    self.cursor = pos
                return True
            if event.type == "scroll":
                self.camera.zoom_at(1.1 if event.dy > 0 else 1 / 1.1, event.x, event.y)
                return True
        return False

    def _tile_at(self, wx: float | None, wy: float | None) -> Pos | None:
        if wx is None or wy is None:
            return None
        pos = tile_at(wx, wy)
        return pos if self.world.in_bounds(pos) else None

    # -- Frame -------------------------------------------------------------------

    def update(self, dt: float) -> None:
        self.pulse += dt
        self.status_timer = max(0.0, self.status_timer - dt)
        self.effects.update(dt)
        self._update_hover()
        self._update_info()

    def _update_hover(self) -> None:
        glow = self.hover_glow
        if not self.world.explored(self.human, self.cursor):
            glow.visible = False
            return
        glow.visible = True
        glow.position = tile_center(self.cursor)
        glow.opacity = int(55 + 30 * (0.5 + 0.5 * math.sin(self.pulse * 4)))

    def _update_info(self) -> None:
        world = self.world
        lines: list[str] = []
        unit = self.selected
        city = self._city()
        hovered = world.unit_at(self.cursor)
        self._hover_target = hovered if unit is not None and hovered in self.targets else None
        harvestable = world.can_harvest(self.human, self.cursor) is None
        self._harvest_pos = self.cursor if harvestable else None
        show_capture = unit is not None and world.can_capture(unit)
        show_hold = unit is not None and unit.can_act
        if unit is not None:
            info = unit.info
            title = f"{unit.type.value.title()}  {unit.hp}/{unit.max_hp} hp"
            lines.append(f"Attack {info.attack:g}  Defense {info.defense:g}  Move {info.movement}  Range {info.range}")
            state = []
            if unit.can_move:
                state.append("can move")
            if unit.can_attack:
                state.append("can attack")
            if show_capture:
                state.append("can capture")
            lines.append(", ".join(state) if state else "done for this turn")
            if self._hover_target is not None:
                dealt, taken = world.combat_preview(unit, hovered)
                retaliates = world.distance(unit.pos, hovered.pos) <= hovered.info.range
                verdict = "kills it" if dealt >= hovered.hp else f"leaves it at {hovered.hp - dealt} hp"
                lines.append(f"Attack {hovered.type.value} ({hovered.hp} hp): deal {dealt}, take {taken if retaliates and dealt < hovered.hp else 0} — {verdict}")
        elif city is not None:
            title = f"{city.name}  level {city.level}" + ("  (capital)" if city.capital else "")
            lines.append(f"Income +{city.income}★ per turn   Territory radius {city.radius}")
            lines.append(f"{city.next_level_population - city.population} more pop to level {city.level + 1}: harvest resources in your borders")
        else:
            tile = world.tile(self.cursor)
            title = f"{tile.terrain.value.title()} ({self.cursor[0]}, {self.cursor[1]})"
            if not world.explored(self.human, self.cursor):
                title = "Unexplored"
            else:
                owner = world.owner_of(self.cursor)
                if owner is not None:
                    lines.append(f"Territory of {world.tribes[owner].name}")
                if tile.village:
                    lines.append("Village — capture with a unit that starts its turn here")
                if hovered is not None:
                    lines.append(f"{world.tribes[hovered.tribe].name} {hovered.type.value} {hovered.hp}/{hovered.max_hp} hp")
        if world.explored(self.human, self.cursor):
            tile = world.tile(self.cursor)
            if tile.resource is not None and not tile.harvested:
                h = HARVEST[tile.resource]
                reason = world.can_harvest(self.human, self.cursor)
                lines.append(f"{tile.resource.value.title()}: {h.label} for {h.cost}★ → +{h.population} pop" + (f"  ({reason})" if reason else ""))
        if self.status_timer > 0:
            lines.append(self.status)
        self.info_title.text = title
        for label, text in zip(self.info_lines, lines + [""] * 4, strict=False):
            label.text = text
            self._set_visible(label, bool(text))
        self._set_visible(self.btn_capture, show_capture)
        self._set_visible(self.btn_hold, show_hold)
        self._set_visible(self.btn_harvest, harvestable)
        self._set_visible(self.btn_attack, self._hover_target is not None)
        self._set_visible(self.action_row, show_capture or show_hold or harvestable or self._hover_target is not None)

    def draw(self) -> None:
        city = self._city()
        self.view.draw(Selection(
            cursor=self.cursor, unit=self.selected, city_pos=city.pos if city is not None else None,
            reachable=self.reachable, targets=self.targets, pulse=self.pulse,
        ))
        self._draw_harvest_markers()
        w, h = self.game.resolution
        self.draw_rect(0, h - 26, w, 26, (0, 0, 0, 150))
        self.effects.draw(self)

    def _draw_harvest_markers(self) -> None:
        """Pulsing marker on every resource the player could harvest right now."""
        world = self.world
        glow = 0.5 + 0.5 * math.sin(self.pulse * 3)
        for tile in world.all_tiles():
            if tile.resource is None or tile.harvested or tile.owner_city is None:
                continue
            if world.can_harvest(self.human, tile.pos) is not None:
                continue
            cx, cy = tile_center(tile.pos)
            self.draw_circle(cx, cy, TILE * (0.30 + 0.05 * glow), (255, 225, 120, int(40 + 55 * glow)), space="world", layer=RenderLayer.OBJECTS)

    # -- Save / load ---------------------------------------------------------------

    def get_save_state(self) -> dict:
        return {"seed": self.seed, "world": self.world.to_dict(), "stats": self.stats, "settings": self.settings}

    def load_save_state(self, state: dict) -> None:
        self.world = World.from_dict(state["world"])
        self.seed = state["seed"]
        self.stats = {**self.stats, **state.get("stats", {})}
        self.settings = {**self.settings, **state.get("settings", {})}
        self.effects.clear()
        self.view.reset(self.world)
        self._setup_camera()
        self.ui.clear()
        self._build_hud()
        self.cursor = (0, 0)
        self.select_unit(None)
        self.center_capital()
        self.say("Loaded slot 1")


class _Overlay(Scene):
    """Transparent modal panel; Escape closes.  The map keeps animating below."""

    transparent = True
    pause_below = False
    pop_on_cancel = True

    def panel(self, title: str) -> Column:
        panel = Column(spacing=8, anchor=Anchor.CENTER, style=PANEL_STYLE)
        panel.add(Label(title, text_style="title"))
        self.ui.add(panel)
        return panel

    def draw(self) -> None:
        w, h = self.game.resolution
        self.draw_rect(0, 0, w, h, (0, 0, 0, 120))


def _tech_rows() -> list[tuple[Tech, int]]:
    """Techs in tree order: each root followed by the techs it unlocks, with depth."""
    rows: list[tuple[Tech, int]] = []
    for root, info in TECHS.items():
        if info.requires is None:
            rows.append((root, 0))
            rows.extend((child, 1) for child, child_info in TECHS.items() if child_info.requires is root)
    return rows


class TechScene(_Overlay):
    controls = {"t": "close"}

    def __init__(self, map_scene: MapScene) -> None:
        self.map_scene = map_scene

    def on_enter(self) -> None:
        world = self.map_scene.world
        tribe = self.map_scene.tribe
        panel = self.panel(f"Research   ★ {tribe.stars}")
        panel.add(Label("Techs unlock harvests and units; indented techs need the one above them.", text_style="sub"))
        for index, (tech, depth) in enumerate(_tech_rows()):
            key = str((index + 1) % 10)
            known = tech in tribe.techs
            reason = world.can_research(tribe.id, tech)
            button = Button(tech.value.title(), hotkey=f"[{key}]", on_click=lambda t=tech: self.buy(t),
                            style=ACTION_BUTTON if reason is None else GHOST_BUTTON, width=170)
            button.enabled = reason is None
            cost = "✓ known" if known else f"{world.tech_cost(tribe.id, tech)}★"
            leads = [t.value.title() for t, i in TECHS.items() if i.requires is tech]
            detail = TECHS[tech].summary + (f"  →  {', '.join(leads)}" if leads else "")
            status = "" if reason is None or known else reason[0].lower() + reason[1:]
            if reason is not None and reason.startswith("Costs"):
                status = f"need {reason[6:]}, have {tribe.stars}★"
            panel.add(Row(
                Label("└" if depth else "", text_style="body", font="Menlo", width=22, align="right"),
                button,
                Label(cost, text_style="hud", width=80, align="right", text_color=GOLD if not known else (130, 220, 130, 255)),
                Label(detail, text_style="body", width=370),
                Label(status, text_style="sub", width=190, text_color=(230, 150, 130, 255)),
                spacing=12,
            ))
            self.bind_key(key, lambda t=tech: self.buy(t))
        panel.add(Label("1-0 research · Esc / T close", text_style="caption"))

    def buy(self, tech: Tech) -> None:
        world = self.map_scene.world
        reason = world.can_research(self.map_scene.human, tech)
        if reason is not None:
            self.map_scene.warn(reason)
            return
        world.research(self.map_scene.human, tech)
        self.map_scene.say(f"Learned {tech.value.title()}")
        self.map_scene.sfx("research")
        capital = world.capital_of(self.map_scene.human)
        if capital is not None:
            center = tile_center(capital.pos)
            self.map_scene.effects.add(FloatingText(f"{tech.value.title()} learned", (center[0], center[1] - TILE * 0.8), GOLD, font_size=20, rise=34, duration=1.4))
        self.game.pop()

    def close(self) -> None:
        self.game.pop()


class SettingsScene(_Overlay):
    """Keyboard-navigable options: ↑↓ pick a row, ←→ adjust, Enter toggles."""

    controls = {"up": "focus_up", "down": "focus_down", "left": "decrease", "right": "increase", ("return", "space"): "toggle"}
    ROWS = (("Confirm end turn", "confirm_end_turn"), ("Music volume", "music"), ("Sound volume", "sfx"))

    def __init__(self, map_scene: MapScene) -> None:
        self.map_scene = map_scene
        self.focus = 0

    @property
    def settings(self) -> dict[str, Any]:
        return self.map_scene.settings

    def on_enter(self) -> None:
        panel = self.panel("Settings")
        for index, (name, key) in enumerate(self.ROWS):
            marker = Label(lambda i=index: "▸" if self.focus == i else "", text_style="hud", width=18, text_color=GOLD)
            label = Label(name, text_style="body", width=170)
            if key == "confirm_end_turn":
                control = Row(Button(lambda k=key: "On" if self.settings[k] else "Off", on_click=lambda k=key: self._toggle(k), style=GHOST_BUTTON, width=190))
            else:
                control = Row(
                    Button("−", on_click=lambda k=key: self._adjust(k, -0.1), style=GHOST_BUTTON, width=48),
                    Label(lambda k=key: f"{round(self.settings[k] * 100)}%", text_style="hud", width=70, align="center"),
                    Button("+", on_click=lambda k=key: self._adjust(k, 0.1), style=GHOST_BUTTON, width=48),
                    spacing=8,
                )
            panel.add(Row(marker, label, control, spacing=12))
        panel.add(Label("Skip the end-turn check to end your turn with units still waiting.", text_style="sub"))
        panel.add(Label("↑↓ select · ←→ adjust · Enter toggle · Esc close", text_style="caption"))

    def _toggle(self, key: str) -> None:
        self.settings[key] = not self.settings[key]
        effects.apply_volumes(self.settings)
        self.map_scene.sfx("button")

    def _adjust(self, key: str, delta: float) -> None:
        self.settings[key] = round(max(0.0, min(1.0, self.settings[key] + delta)), 2)
        effects.apply_volumes(self.settings)
        self.map_scene.sfx("button")

    def focus_up(self) -> None:
        self.focus = (self.focus - 1) % len(self.ROWS)

    def focus_down(self) -> None:
        self.focus = (self.focus + 1) % len(self.ROWS)

    def _step(self, delta: float) -> None:
        key = self.ROWS[self.focus][1]
        if key == "confirm_end_turn":
            self._toggle(key)
        else:
            self._adjust(key, delta)

    def decrease(self) -> None:
        self._step(-0.1)

    def increase(self) -> None:
        self._step(0.1)

    def toggle(self) -> None:
        self._step(0.1)


class PauseScene(_Overlay):
    controls = {"n": "new_game", "q": "quit", "f5": "save", "f9": "load", "s": "settings", "t": "back_to_title"}

    def __init__(self, map_scene: MapScene) -> None:
        self.map_scene = map_scene

    def on_enter(self) -> None:
        panel = self.panel("Paused")
        panel.add(Button("Resume", hotkey="[Esc]", on_click=self.game.pop, style=GHOST_BUTTON, width=260))
        panel.add(Button("Save", hotkey="[F5]", on_click=self.save, style=GHOST_BUTTON, width=260))
        panel.add(Button("Load", hotkey="[F9]", on_click=self.load, style=GHOST_BUTTON, width=260))
        panel.add(Button("Settings", hotkey="[S]", on_click=self.settings, style=GHOST_BUTTON, width=260))
        panel.add(Button("New game", hotkey="[N]", on_click=self.new_game, style=GHOST_BUTTON, width=260))
        panel.add(Button("Back to title", hotkey="[T]", on_click=self.back_to_title, style=GHOST_BUTTON, width=260))
        panel.add(Button("Quit", hotkey="[Q]", on_click=self.quit, style=GHOST_BUTTON, width=260))

    def save(self) -> None:
        self.game.pop()
        self.map_scene.quick_save()

    def load(self) -> None:
        self.game.pop()
        self.map_scene.quick_load()

    def settings(self) -> None:
        self.game.push(SettingsScene(self.map_scene))

    def new_game(self) -> None:
        self.game.clear_and_push(new_game(self.map_scene.seed + 1, size=self.map_scene.world.size, tribes=len(self.map_scene.world.tribes),
                                          settings=self.map_scene.settings))

    def back_to_title(self) -> None:
        from tribes.title import TitleScene

        self.game.clear_and_push(TitleScene(settings=self.map_scene.settings))

    def quit(self) -> None:
        self.game.quit()


HELP_LINES = (
    "Capture villages to grow your empire; take every enemy city to win.",
    "Harvest glowing resources inside your borders to level cities up.",
    "",
    "Enter / click     act at the cursor: select, move, attack, harvest, capture",
    "Arrows            move the cursor          WASD / right-drag   pan the map",
    "Tab / Shift+Tab   next / previous unit     Wheel, + / -        zoom",
    "E                 end turn (twice while units can still act)",
    "T                 research                 C                   capture",
    "H                 hold (unit heals)        1-5                 train in city",
    "F5 / F9           save / load              Home                jump to capital",
    "Esc               cancel / pause menu      (settings and title live there)",
)


class HelpScene(_Overlay):
    def on_enter(self) -> None:
        panel = self.panel("How to play")
        size = self.game.theme.get_text_style("body").font_size
        width = max(self.game.backend.measure_text(line, size, "Menlo")[0] for line in HELP_LINES)
        for line in HELP_LINES:
            panel.add(Label(line, text_style="body", font="Menlo", width=width))
        panel.add(Label("Esc to close", text_style="caption"))


class GameOverScene(_Overlay):
    pop_on_cancel = False
    controls = {"n": "new_game", "q": "quit", ("t", "escape"): "back_to_title"}

    def __init__(self, map_scene: MapScene) -> None:
        self.map_scene = map_scene

    def on_enter(self) -> None:
        scene = self.map_scene
        world = scene.world
        winner = world.tribes[world.winner]
        won = winner.id == scene.human
        panel = self.panel("Victory!" if won else f"Defeat — {winner.name} wins")
        cities = len(world.tribe_cities(scene.human))
        panel.add(Label(
            f"{_plural(world.round, 'round')} · {cities} {'city' if cities == 1 else 'cities'} held · "
            f"{_plural(scene.stats['cities_taken'], 'capture')} · {_plural(scene.stats['units_killed'], 'kill')} · "
            f"{_plural(scene.stats['units_lost'], 'unit')} lost",
            text_style="body",
        ))
        for tribe in sorted(world.tribes, key=lambda t: -world.score(t.id)):
            panel.add(Label(f"{tribe.name:<8} {world.score(tribe.id):>5} points", text_style="body", font="Menlo", width=260,
                            text_color=rgba(tribe.color)))
        panel.add(Button("New game", hotkey="[N]", on_click=self.new_game, style=ACTION_BUTTON, width=260))
        panel.add(Button("Back to title", hotkey="[T]", on_click=self.back_to_title, style=GHOST_BUTTON, width=260))
        panel.add(Button("Quit", hotkey="[Q]", on_click=self.quit, style=GHOST_BUTTON, width=260))

    def new_game(self) -> None:
        scene = self.map_scene
        self.game.clear_and_push(new_game(scene.seed + 1, size=scene.world.size, tribes=len(scene.world.tribes), settings=scene.settings))

    def back_to_title(self) -> None:
        from tribes.title import TitleScene

        self.game.clear_and_push(TitleScene(settings=self.map_scene.settings))

    def quit(self) -> None:
        self.game.quit()


def new_game(seed: int, size: int = 14, tribes: int = 3, *, settings: dict[str, Any] | None = None) -> MapScene:
    return MapScene(mapgen.generate(seed=seed, size=size, tribe_count=tribes), seed, settings=settings)


def load_game(state: dict[str, Any], *, settings: dict[str, Any] | None = None) -> MapScene:
    """A map scene from a save slot's ``state`` (see :meth:`MapScene.get_save_state`)."""
    return MapScene(World.from_dict(state["world"]), state["seed"], settings={**state.get("settings", {}), **(settings or {})},
                    stats=state.get("stats"))
