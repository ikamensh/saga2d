"""saga2d scenes for Tribes: the map, and the overlays stacked on it."""

from __future__ import annotations

import math
import json
import random
from collections import deque
from typing import Any
from uuid import NAMESPACE_URL, uuid4, uuid5

from saga2d import (
    Anchor, Button, Camera, Column, Delay, InputEvent, KeyHints, Label, Layout, MoveTo, Panel, ProgressBar, RenderLayer,
    Row, SaveError, Scene, Sequence, Sprite, Style,
)
from tribes import ai, effects, mapgen
from tribes.effects import Banner, Burst, Dissolve, Effects, FloatingText, HitReaction, TilePulse, Toast, hop, play_sound
from tribes.model import City, CombatResult, Pos, RuleError, Unit, World
from tribes.rules import HARVEST, MAX_ROUNDS, REWARDS, TECHS, UNITS, Reward, Tech, UnitType
from tribes.scores import HighScores
from tribes.score_scene import HighScoresScene
from tribes.style import ACTION_BUTTON, BAD, DANGER_BUTTON, GHOST_BUTTON, GOLD, GOOD, OVERLAY_STYLE, PANEL_STYLE, RESULTS_STYLE, SEMIBOLD
from tribes.textures import FOG, TILE
from tribes.view import MapView, Selection, rgba, tile_at, tile_center, tint

DEFAULT_SETTINGS: dict[str, Any] = {"music": 0.7, "sfx": 0.8, "confirm_end_turn": True}
DAMAGE_COLOR = (255, 96, 84, 255)
HEAL_COLOR = (130, 235, 130, 255)
HINT_BAR = 30  # height of the keycap strip along the bottom
PANEL_MARGIN = (16, HINT_BAR + 12)

HIT_TIME = 0.16  # seconds from the start of a lunge until the blow lands
ZOOM_PER_LINE = 1.06  # zoom factor per wheel line; a trackpad swipe of ~30 lines spans the whole range
ZOOM_PER_KEY = 1.25
START_ZOOM = 1.3  # a game opens close on the capital; the whole map is a wheel-flick away
MAX_LINES_PER_EVENT = 4.0  # a flick delivers big deltas: cap each event so momentum cannot overshoot


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

    def __init__(self, world: World, seed: int, *, settings: dict[str, Any] | None = None,
                 stats: dict[str, int] | None = None, run_id: str | None = None) -> None:
        self.world = world
        self.seed = seed
        self.run_id = run_id if run_id is not None else str(uuid4())
        self._game_over_shown = False
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
        pad = TILE * 3.5  # slack so any tile can be scrolled out from under the HUD panels
        bounds = (left - pad, top - pad, right + pad, bottom + pad)
        self.camera = Camera((w, h), world_bounds=bounds, zoom=START_ZOOM, min_zoom=0.5, max_zoom=2.5)
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
        self.btn_end_turn = Button(lambda: "Confirm end turn" if self._end_turn_armed else "End turn", hotkey="E", on_click=self.end_turn, style=GHOST_BUTTON)
        self.ui.add(Panel(anchor=Anchor.TOP_LEFT, margin=12, layout=Layout.HORIZONTAL, spacing=18, style=PANEL_STYLE, children=[
            Label(tribe.name, text_style="title", text_color=rgba(tribe.color)),
            Row(Label(lambda: f"★ {tribe.stars}", text_style="hud", text_color=GOLD),
                Label(lambda: f"+{world.income(self.human)}/turn", text_style="sub"), spacing=6),
            Label(lambda: f"Round {world.round}/{MAX_ROUNDS}", text_style="hud"),
            Label(lambda: f"Units {len(world.tribe_units(self.human))}/{world.unit_cap(self.human)}", text_style="sub"),
            Label(self._score_text, text_style="sub"),
            Button("Tech", hotkey="T", on_click=self.open_tech, style=GHOST_BUTTON),
            self.btn_end_turn,
        ]))
        self.info_panel = Column(spacing=6, anchor=Anchor.BOTTOM_LEFT, margin=PANEL_MARGIN, style=PANEL_STYLE)
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
        self.btn_capture = Button("Capture", hotkey="C", on_click=self.capture, style=ACTION_BUTTON)
        self.btn_hold = Button("Hold", hotkey="H", on_click=self.hold_unit, style=GHOST_BUTTON)
        self.btn_harvest = Button(lambda: HARVEST[world.tile(self._harvest_pos).resource].label if self._harvest_pos else "Harvest",
                                  hotkey="Enter", on_click=self._harvest_button, style=ACTION_BUTTON)
        self.btn_attack = Button("Attack", hotkey="Enter", on_click=self._attack_button, style=DANGER_BUTTON)
        self.action_row = Row(self.btn_capture, self.btn_hold, self.btn_harvest, self.btn_attack, spacing=8)
        for button in (self.btn_capture, self.btn_hold, self.btn_harvest, self.btn_attack):
            button.visible = False
        self.action_row.visible = False
        self.info_panel.add(self.action_row)
        self.ui.add(self.info_panel)

        self.train_panel = Column(spacing=6, anchor=Anchor.BOTTOM_RIGHT, margin=PANEL_MARGIN, style=PANEL_STYLE)
        self.train_panel.add(Label("Train", text_style="heading"))
        self.train_buttons: dict[UnitType, Button] = {}
        for unit_type, info in UNITS.items():
            button = Button(f"{unit_type.value.title()}  {info.cost}★", hotkey=info.hotkey,
                            on_click=lambda ut=unit_type: self.train(ut), style=GHOST_BUTTON, width=170)
            self.train_buttons[unit_type] = button
            reason = Label(lambda ut=unit_type: self._train_reason(ut), text_style="caption", width=150)
            self.train_panel.add(Row(button, reason, spacing=8))
        self.train_panel.visible = False
        self.ui.add(self.train_panel)
        self.ui.add(KeyHints(self._hint, anchor=Anchor.BOTTOM_CENTER, margin=6))
        self.ui.add(Label(lambda: "   ·   ".join(self.visible_log()[-2:]), text_style="sub", anchor=Anchor.TOP_RIGHT, margin=14))

    def _score_text(self) -> str:
        """Score and standing: the round limit decides most games, so it stays in view."""
        world = self.world
        scores = sorted((world.score(t.id) for t in world.tribes if t.alive), reverse=True)
        mine = world.score(self.human)
        rank = scores.index(mine) + 1
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank, "th")
        return f"Score {mine} · {rank}{suffix} of {len(scores)}"

    def _hint(self) -> list[tuple[str, str]]:
        """Keycap hints for the current state; every action stays reachable from the keyboard."""
        if self.selected is not None:
            return [("Enter", "move / attack"), ("C", "capture"), ("H", "hold"), ("Tab", "next unit"), ("Esc", "deselect"), ("F1", "help")]
        if self._city() is not None:
            return [("1-7", "train"), ("Click", "a glowing resource to harvest"), ("Esc", "deselect"), ("F1", "help")]
        return [("Enter", "act"), ("Tab", "next unit"), ("E", "end turn"), ("T", "tech"), ("WASD", "pan"), ("Wheel", "zoom"), ("Esc", "menu"), ("F1", "help")]

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
        self.train_panel.visible = city is not None
        self.city_bar_row.visible = city is not None
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
        self._show_findings()
        if not unit.can_act:
            self.select_unit(None)

    def _show_findings(self) -> None:
        """Celebrate whatever the player's units just found in ruins."""
        for finding in self.world.take_findings():
            center = tile_center(finding.pos)
            self.effects.add(Burst(center, GOLD, 22, rng=self.rng))
            self.effects.add(TilePulse(center, GOLD, radius=(10, TILE), rings=2, duration=0.9))
            self.effects.add(FloatingText(finding.text, (center[0], center[1] - TILE * 0.7), GOLD, font_size=20, rise=36, duration=1.8))
            self.say(f"Ruins explored: {finding.text}")
            self.sfx("level_up")

    def _attack_selected(self, target: Unit) -> None:
        unit = self.selected
        assert unit is not None
        origin, target_pos = unit.pos, target.pos
        attacker_sprite, target_sprite = self.view.unit_sprite(unit.id), self.view.unit_sprite(target.id)
        blocked = self.world.defense_bonus(target) > 1.0
        result = self.world.attack(unit, target)
        self._animate_attack(result, origin, target_pos, attacker_sprite, target_sprite)
        self.view.sync()
        self._show_findings()  # a melee kill can carry the attacker onto ruins
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
        gained = self.world.harvest_yield(self.human, tile.resource)  # type: ignore[arg-type]
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
        if self.world.pending_rewards(self.human):
            self._offer_reward()  # the rules refuse to end a turn with a reward unpicked
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
        self.world.take_findings()  # the AI's finds stay in the log only
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
            if (line.endswith("has fallen") or "surrendered:" in line) and self.tribe.name not in line:
                news.append(line)
        return len(lost), news[:6]

    def _check_game_over(self) -> None:
        if self.world.winner is not None and not self._game_over_shown:
            self._game_over_shown = True
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
        self.game.save(1, scene=self)
        self.say("Saved to slot 1")
        self.sfx("button")

    def quick_load(self) -> None:
        if self.game.load(1, scene=self) is None:
            self.warn("No save in slot 1")

    def center_capital(self) -> None:
        capital = self.world.capital_of(self.human) or next(iter(self.world.tribe_cities(self.human)), None)
        if capital is not None:
            self.cursor = capital.pos
            self.camera.pan_to(*tile_center(capital.pos), duration=0.3)

    def zoom_in(self) -> None:
        self._zoom_by(ZOOM_PER_KEY)

    def zoom_out(self) -> None:
        self._zoom_by(1 / ZOOM_PER_KEY)

    def _zoom_by(self, factor: float, at: tuple[float, float] | None = None) -> None:
        """Ease the zoom target by *factor* about screen point *at* (default: the centre)."""
        if at is None:
            w, h = self.game.resolution
            at = (w / 2, h / 2)
        self.camera.zoom_toward(self.camera.zoom_target * factor, *at)

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
                lines = max(-MAX_LINES_PER_EVENT, min(MAX_LINES_PER_EVENT, event.dy))
                self._zoom_by(ZOOM_PER_LINE ** lines, (event.x, event.y))
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
        self._offer_reward()
        if self.game.scene is self:
            self._check_game_over()

    def _offer_reward(self) -> None:
        """A city that reached a new level asks for its reward as soon as the map is on top."""
        if self.game.scene is self and self.world.winner is None:
            pending = self.world.pending_rewards(self.human)
            if pending:
                self.game.push(RewardScene(self, pending[0]))

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
            lines.append(f"Income +{world.city_income(city)}★ per turn   Territory radius {city.radius}")
            lines.append(f"{city.next_level_population - city.population} more pop to level {city.level + 1}: harvest resources in your borders")
            built = [name for flag, name in ((city.workshop, "Workshop"), (city.walls, "City walls")) if flag]
            built += [f"{city.parks} park{'s' if city.parks > 1 else ''}"] if city.parks else []
            if built:
                lines.append(" · ".join(built))
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
                if tile.ruin:
                    lines.append("Ancient ruins — walk a unit onto them to see what they hold")
                if hovered is not None:
                    lines.append(f"{world.tribes[hovered.tribe].name} {hovered.type.value} {hovered.hp}/{hovered.max_hp} hp")
        if world.explored(self.human, self.cursor):
            tile = world.tile(self.cursor)
            if tile.resource is not None and not tile.harvested:
                reason = world.can_harvest(self.human, self.cursor)
                cost, pop = world.harvest_cost(self.human, tile.resource), world.harvest_yield(self.human, tile.resource)
                lines.append(f"{tile.resource.value.title()}: {HARVEST[tile.resource].label} for {cost}★ → +{pop} pop" + (f"  ({reason})" if reason else ""))
        if self.status_timer > 0:
            lines.append(self.status)
        self.info_title.text = title
        for label, text in zip(self.info_lines, lines + [""] * 4, strict=False):
            label.text = text
            label.visible = bool(text)
        self.btn_capture.visible = show_capture
        self.btn_hold.visible = show_hold
        self.btn_harvest.visible = harvestable
        self.btn_attack.visible = self._hover_target is not None
        self.action_row.visible = show_capture or show_hold or harvestable or self._hover_target is not None
        # End turn is the natural next step once nothing can act; it turns red while it waits for the confirming press.
        self.btn_end_turn.style = DANGER_BUTTON if self._end_turn_armed else GHOST_BUTTON if self._own_units_with_actions() else ACTION_BUTTON

    def draw(self) -> None:
        city = self._city()
        self.view.draw(Selection(
            cursor=self.cursor, unit=self.selected, city_pos=city.pos if city is not None else None,
            reachable=self.reachable, targets=self.targets, pulse=self.pulse,
        ))
        self._draw_harvest_markers()
        w, h = self.game.resolution
        self.draw_rect(0, h - HINT_BAR, w, HINT_BAR, (8, 10, 18, 175))
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
        return {"seed": self.seed, "world": self.world.to_dict(), "stats": self.stats, "settings": self.settings, "run_id": self.run_id}

    def load_save_state(self, state: dict) -> None:
        self.world = World.from_dict(state["world"])
        self.seed = state["seed"]
        self.run_id = _saved_run_id(state)
        self._game_over_shown = False
        self.stats = {**self.stats, **state.get("stats", {})}
        self.settings = {**self.settings, **state.get("settings", {})}
        self.effects.clear()
        self.view.reset(self.world)
        self._setup_camera()
        # Reactive labels evaluate while the HUD is built. Hover targets belong
        # to the old world and may be absent or out of bounds in the loaded one.
        self._harvest_pos = self._hover_target = None
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
        panel = Column(spacing=10, anchor=Anchor.CENTER, style=OVERLAY_STYLE)
        panel.add(Label(title, text_style="title"))
        self.ui.add(panel)
        return panel

    def draw(self) -> None:
        w, h = self.game.resolution
        self.draw_rect(0, 0, w, h, (4, 6, 12, 140))


WHEEL_RADII = (105, 205, 305)  # rings for tiers 1, 2 and 3; 100 px apart leaves room for a node and its label
NODE = 62  # diameter of a tech node


def tech_wheel(center: tuple[float, float], radii: tuple[float, float, float] = WHEEL_RADII) -> dict[Tech, tuple[float, float]]:
    """Where every tech sits on the research wheel: roots evenly spaced from the
    top, their children fanned out on the next ring, grandchildren on the outer
    ring at their parent's angle."""
    cx, cy = center
    roots = [t for t, info in TECHS.items() if info.requires is None]
    step = 2 * math.pi / len(roots)
    positions: dict[Tech, tuple[float, float]] = {}

    def place(tech: Tech, angle: float, ring: int) -> None:
        positions[tech] = (cx + radii[ring] * math.cos(angle), cy + radii[ring] * math.sin(angle))
        children = [t for t, info in TECHS.items() if info.requires is tech]
        for j, child in enumerate(children):
            place(child, angle + (j - (len(children) - 1) / 2) * step / 2 ** (ring + 1), ring + 1)

    for i, root in enumerate(roots):
        place(root, -math.pi / 2 + i * step, 0)
    return positions


_NODE = dict(font=SEMIBOLD, radius=NODE // 2, border_width=2, padding=0)
KNOWN_NODE = Style(background_color=(46, 128, 84, 255), hover_color=(56, 146, 98, 255), border_color=(130, 225, 140, 210), **_NODE)
OPEN_NODE = Style(background_color=(58, 122, 224, 255), hover_color=(86, 148, 242, 255), border_color=(160, 200, 255, 220), **_NODE)
PRICEY_NODE = Style(background_color=(30, 46, 84, 255), hover_color=(40, 60, 104, 255), border_color=(90, 130, 200, 200),
                    text_color=(170, 190, 230, 255), **_NODE)
LOCKED_NODE = Style(background_color=(255, 255, 255, 12), hover_color=(255, 255, 255, 24), border_color=(255, 255, 255, 40),
                    text_color=(140, 148, 172, 255), **_NODE)


class TechScene(_Overlay):
    """The research wheel: five branches around the centre, like the original.

    Tab cycles through what can be researched right now, the arrows walk the
    wheel geometrically, Enter researches the focused tech; clicking a node does
    the same.  The map's HUD hides while the wheel is up.
    """

    controls = {
        ("t", "escape"): "close", "tab": "focus_next", "shift+tab": "focus_prev", ("return", "space"): "buy_focused",
        "up": "focus_up", "down": "focus_down", "left": "focus_left", "right": "focus_right",
    }
    pop_on_cancel = False

    def __init__(self, map_scene: MapScene) -> None:
        self.map_scene = map_scene
        self.focus: Tech = next(iter(TECHS))
        self.nodes: dict[Tech, Button] = {}

    def on_enter(self) -> None:
        self.map_scene.ui.visible = False
        w, h = self.game.resolution
        self.positions = tech_wheel((w / 2, h / 2 - 5))
        for tech, (x, y) in self.positions.items():
            node = Button(lambda t=tech: self._node_text(t), on_click=lambda t=tech: self.activate(t), width=NODE, height=NODE,
                          anchor=Anchor.TOP_LEFT, margin=(round(x - NODE / 2), round(y - NODE / 2)))
            self.nodes[tech] = node
            self.ui.add(node)
            self.ui.add(Label(tech.value.title(), text_style="sub", width=130, align="center", anchor=Anchor.TOP_LEFT,
                              margin=(round(x - 65), round(y + NODE / 2 + 1))))
        tribe = self.map_scene.tribe
        self.ui.add(Panel(anchor=Anchor.TOP_LEFT, margin=12, layout=Layout.HORIZONTAL, spacing=16, style=PANEL_STYLE, children=[
            Label("Research", text_style="title"), Label(lambda: f"★ {tribe.stars}", text_style="hud", text_color=GOLD),
        ]))
        self.ui.add(Label(self._detail_text, text_style="body", anchor=Anchor.BOTTOM_CENTER, margin=(0, HINT_BAR + 12)))
        self.ui.add(KeyHints([("Tab", "next affordable"), ("↑↓←→", "move"), ("Enter", "research"), ("Esc", "close")],
                             anchor=Anchor.BOTTOM_CENTER, margin=7))
        self.focus = next(iter(self._researchable()), self.focus)
        self._restyle()

    def on_exit(self) -> None:
        self.map_scene.ui.visible = True

    # -- State ---------------------------------------------------------------------

    @property
    def world(self) -> World:
        return self.map_scene.world

    def _researchable(self) -> list[Tech]:
        return [t for t in TECHS if self.world.can_research(self.map_scene.human, t) is None]

    def _node_text(self, tech: Tech) -> str:
        if tech in self.map_scene.tribe.techs:
            return "✓"
        return f"{self.world.tech_cost(self.map_scene.human, tech)}★"

    def _detail_text(self) -> str:
        tech, tribe = self.focus, self.map_scene.tribe
        info = TECHS[tech]
        if tech in tribe.techs:
            state = "known"
        else:
            reason = self.world.can_research(tribe.id, tech)
            state = f"{self.world.tech_cost(tribe.id, tech)}★" + (f" · {reason[0].lower()}{reason[1:]}" if reason else " · press Enter to research")
        return f"{tech.value.title()} — {info.summary} · {state}"

    def _restyle(self) -> None:
        tribe = self.map_scene.tribe
        for tech, node in self.nodes.items():
            reason = self.world.can_research(tribe.id, tech)
            if tech in tribe.techs:
                node.style = KNOWN_NODE
            elif reason is None:
                node.style = OPEN_NODE
            elif reason.startswith("Costs"):
                node.style = PRICEY_NODE
            else:
                node.style = LOCKED_NODE

    # -- Actions -------------------------------------------------------------------

    def activate(self, tech: Tech) -> None:
        """Click or Enter: research when possible, otherwise just focus and explain."""
        self.focus = tech
        reason = self.world.can_research(self.map_scene.human, tech)
        if reason is not None:
            self.map_scene.sfx("error")
            return
        self.buy(tech)

    def buy(self, tech: Tech) -> None:
        world, scene = self.world, self.map_scene
        world.research(scene.human, tech)
        scene.say(f"Learned {tech.value.title()}")
        scene.sfx("research")
        capital = world.capital_of(scene.human)
        if capital is not None:
            center = tile_center(capital.pos)
            scene.effects.add(FloatingText(f"{tech.value.title()} learned", (center[0], center[1] - TILE * 0.8), GOLD, font_size=20, rise=34, duration=1.4))
        scene.sync()
        scene._refresh_selection()
        self._restyle()

    def buy_focused(self) -> None:
        self.activate(self.focus)

    def focus_next(self, step: int = 1) -> None:
        order = self._researchable() or [t for t in TECHS if t not in self.map_scene.tribe.techs] or list(TECHS)
        index = (order.index(self.focus) + step) % len(order) if self.focus in order else (0 if step > 0 else -1)
        self.focus = order[index]

    def focus_prev(self) -> None:
        self.focus_next(-1)

    def _focus_toward(self, dx: float, dy: float) -> None:
        """Move the focus to the nearest node lying roughly in direction ``(dx, dy)``."""
        fx, fy = self.positions[self.focus]
        best: tuple[float, Tech] | None = None
        for tech, (x, y) in self.positions.items():
            vx, vy = x - fx, y - fy
            distance = math.hypot(vx, vy)
            if tech is self.focus or (vx * dx + vy * dy) / distance < 0.5:
                continue  # behind, or outside a 60° cone
            score = distance ** 2 / (vx * dx + vy * dy)  # near and well aligned wins
            if best is None or score < best[0]:
                best = (score, tech)
        if best is not None:
            self.focus = best[1]

    def focus_up(self) -> None:
        self._focus_toward(0, -1)

    def focus_down(self) -> None:
        self._focus_toward(0, 1)

    def focus_left(self) -> None:
        self._focus_toward(-1, 0)

    def focus_right(self) -> None:
        self._focus_toward(1, 0)

    def close(self) -> None:
        self.game.pop()

    # -- Drawing --------------------------------------------------------------------

    def draw(self) -> None:
        super().draw()
        w, h = self.game.resolution
        self.draw_rect(0, 0, w, h, (4, 6, 12, 110))  # the wheel wants a quieter backdrop than a small dialog
        tribe = self.map_scene.tribe
        for tech, info in TECHS.items():
            if info.requires is None:
                continue
            (x1, y1), (x2, y2) = self.positions[info.requires], self.positions[tech]
            if tech in tribe.techs:
                color = (130, 225, 140, 200)
            elif info.requires in tribe.techs:
                color = (150, 195, 255, 200)
            else:
                color = (255, 255, 255, 45)
            self.draw_line(x1, y1, x2, y2, color, 3)
        fx, fy = self.positions[self.focus]
        self.draw_circle(fx, fy, NODE / 2 + 7, (255, 255, 255, 110))


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
            marker = Label(lambda i=index: "›" if self.focus == i else "", text_style="hud", width=18, text_color=GOLD)
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
        panel.add(KeyHints([("↑↓", "select"), ("←→", "adjust"), ("Enter", "toggle"), ("Esc", "close")]))

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


class RewardScene(_Overlay):
    """A city reached a new level: pick one of two rewards.  Escape does not skip it."""

    pop_on_cancel = False
    controls = {"1": "pick_first", "2": "pick_second"}

    def __init__(self, map_scene: MapScene, city: City) -> None:
        self.map_scene = map_scene
        self.city = city

    def on_enter(self) -> None:
        self.options = self.map_scene.world.reward_options(self.city)
        panel = self.panel(f"{self.city.name} reached level {self.city.level}")
        panel.add(Label("Choose a reward", text_style="sub"))
        row = Row(spacing=14)
        for index, reward in enumerate(self.options):
            info = REWARDS[reward]
            row.add(Column(
                Button(info.name, hotkey=str(index + 1), on_click=lambda r=reward: self.pick(r), style=ACTION_BUTTON, width=240),
                Label(info.summary, text_style="sub", width=240, align="center"),
                spacing=6,
            ))
        panel.add(row)

    def pick(self, reward: Reward) -> None:
        scene = self.map_scene
        scene.world.choose_reward(self.city, reward)
        center = tile_center(self.city.pos)
        scene.effects.add(TilePulse(center, rgba(scene.tribe.color), radius=(12, TILE * 1.3), rings=3, duration=1.0))
        scene.say(f"{self.city.name}: {REWARDS[reward].name}")
        scene.sfx("research")
        scene.sync()
        scene._refresh_selection()
        self.game.pop()

    def pick_first(self) -> None:
        self.pick(self.options[0])

    def pick_second(self) -> None:
        self.pick(self.options[1])


class PauseScene(_Overlay):
    controls = {"n": "new_game", "q": "quit", "f5": "save", "f9": "load", "s": "settings", "t": "back_to_title"}

    def __init__(self, map_scene: MapScene) -> None:
        self.map_scene = map_scene

    def on_enter(self) -> None:
        panel = self.panel("Paused")
        panel.add(Button("Resume", hotkey="Esc", on_click=self.game.pop, style=ACTION_BUTTON, width=260))
        panel.add(Button("Save", hotkey="F5", on_click=self.save, style=GHOST_BUTTON, width=260))
        panel.add(Button("Load", hotkey="F9", on_click=self.load, style=GHOST_BUTTON, width=260))
        panel.add(Button("Settings", hotkey="S", on_click=self.settings, style=GHOST_BUTTON, width=260))
        panel.add(Button("New game", hotkey="N", on_click=self.new_game, style=GHOST_BUTTON, width=260))
        panel.add(Button("Back to title", hotkey="T", on_click=self.back_to_title, style=GHOST_BUTTON, width=260))
        panel.add(Button("Quit", hotkey="Q", on_click=self.quit, style=GHOST_BUTTON, width=260))

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


HELP_INTRO = (
    "Capture villages to grow your empire; take every enemy city to win.",
    "Harvest glowing resources inside your borders to level cities up; each new level offers a reward.",
    "Walk onto ruins to find treasure, knowledge, settlers or a map of the land.",
)
HELP_KEYS = (
    ("Enter / click", "act at the cursor: select, move, attack, harvest, capture"),
    ("Arrows", "move the cursor"),
    ("WASD / right-drag", "pan the map"),
    ("Tab / Shift+Tab", "next / previous unit"),
    ("Wheel / + / −", "zoom"),
    ("E", "end turn (twice while units can still act)"),
    ("T", "research wheel: Tab / arrows pick a tech, Enter learns it"),
    ("C", "capture a village or an enemy city"),
    ("H", "hold: the unit rests and heals"),
    ("1-7", "train in the selected city"),
    ("F5 / F9", "save / load"),
    ("Home", "jump to the capital"),
    ("Esc", "cancel, or the pause menu (settings and title live there)"),
)


class HelpScene(_Overlay):
    def on_enter(self) -> None:
        panel = self.panel("How to play")
        for line in HELP_INTRO:
            panel.add(Label(line, text_style="body", width=640))
        table = Column(spacing=4)
        for keys, what in HELP_KEYS:
            table.add(Row(Label(keys, text_style="hud", width=190, align="right", text_color=GOLD), Label(what, text_style="body", width=440), spacing=14))
        panel.add(table)
        panel.add(KeyHints([("Esc", "close")]))


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
        panel.style = RESULTS_STYLE
        rounds = min(world.round, MAX_ROUNDS)
        cities = len(world.tribe_cities(scene.human))
        panel.add(Label(
            f"{_plural(rounds, 'round')} · {cities} {'city' if cities == 1 else 'cities'} held · "
            f"{_plural(scene.stats['cities_taken'], 'capture')} · {_plural(scene.stats['units_killed'], 'kill')} · "
            f"{_plural(scene.stats['units_lost'], 'unit')} lost",
            text_style="body",
        ))
        points = world.score_breakdown(scene.human, final=True)
        report = Column(spacing=2, width=330)
        report.add(Label("Your score", text_style="heading"))
        report.add(Label(f"{sum(points.values()):,}", text_style="banner", font_size=30, text_color=GOLD))
        for name, value in points.items():
            report.add(Row(Label(name, text_style="body", font_size=13, width=235),
                           Label(f"{value:,}", text_style="hud", font_size=13, width=80, align="right"), spacing=0))
        standings = Column(spacing=6, width=330, height=self.measure(report)[1])
        standings.add(Label("Final standings", text_style="heading"))
        standings.add(Row(Label("Tribe", text_style="caption", width=90),
                          Label("Result", text_style="caption", width=115),
                          Label("Empire", text_style="caption", width=95, align="right"), spacing=0))
        for tribe in sorted(world.tribes, key=lambda t: (t.id != world.winner, not t.alive, -world.score(t.id))):
            status = "Winner" if tribe.id == world.winner else "Surrendered" if tribe.surrendered else "Fallen" if not tribe.alive else "Survived"
            standings.add(Row(Label(tribe.name, text_style="body", width=90, text_color=rgba(tribe.color)),
                              Label(status, text_style="sub", width=115),
                              Label(f"{world.score(tribe.id):,}", text_style="sub", width=95, align="right"), spacing=0))
        reason = "Round limit reached; highest empire score wins." if world.round > MAX_ROUNDS else "All rival tribes defeated." if won else "Your last city fell."
        standings.add(Label(reason, text_style="sub", width=300, wrap=True))
        panel.add(Row(report, standings, spacing=24))
        panel.add(Label("Victory +1,000 · Early finish +50 per round remaining", text_style="sub"))
        self.score_error = None
        try:
            rank = HighScores(self.game.data_dir).record(world, tribe=scene.human, seed=scene.seed, run_id=scene.run_id)
            message = f"Your run's best: #{rank} locally" if rank is not None else "Outside the local top 10"
            panel.add(Label(f"{message} · {world.size}×{world.size} · {len(world.tribes)} tribes", text_style="hud", text_color=GOLD))
        except SaveError as error:
            self.score_error = str(error)
            panel.add(Label("Score could not be saved. Open High scores for details.", text_style="sub", text_color=BAD))
        panel.add(Row(Button("New game", hotkey="N", on_click=self.new_game, style=ACTION_BUTTON, width=165),
                      Button("High scores", shortcut="L", on_click=self.high_scores, style=GHOST_BUTTON, width=165),
                      Button("Back to title", hotkey="T", on_click=self.back_to_title, style=GHOST_BUTTON, width=165),
                      Button("Quit", hotkey="Q", on_click=self.quit, style=GHOST_BUTTON, width=165), spacing=8))

    def high_scores(self) -> None:
        scene = self.map_scene
        self.game.push(HighScoresScene(size=scene.world.size, tribes=len(scene.world.tribes), highlight=scene.run_id, error=self.score_error))

    def new_game(self) -> None:
        scene = self.map_scene
        self.game.clear_and_push(new_game(scene.seed + 1, size=scene.world.size, tribes=len(scene.world.tribes), settings=scene.settings))

    def back_to_title(self) -> None:
        from tribes.title import TitleScene

        scene = self.map_scene
        self.game.clear_and_push(TitleScene(size=scene.world.size, tribes=len(scene.world.tribes), settings=scene.settings))

    def quit(self) -> None:
        self.game.quit()


def new_game(seed: int, size: int = 14, tribes: int = 3, *, settings: dict[str, Any] | None = None, first_tribe: int = 0) -> MapScene:
    return MapScene(mapgen.generate(seed=seed, size=size, tribe_count=tribes, first_tribe=first_tribe), seed, settings=settings)


def load_game(state: dict[str, Any], *, settings: dict[str, Any] | None = None) -> MapScene:
    """A map scene from a save slot's ``state`` (see :meth:`MapScene.get_save_state`)."""
    return MapScene(World.from_dict(state["world"]), state["seed"], settings={**state.get("settings", {}), **(settings or {})},
                    stats=state.get("stats"), run_id=_saved_run_id(state))


def _saved_run_id(state: dict[str, Any]) -> str:
    """Old saves get a stable identity so repeatedly loading one cannot flood the board."""
    if "run_id" in state:
        return state["run_id"]
    return str(uuid5(NAMESPACE_URL, json.dumps(state["world"], sort_keys=True)))
