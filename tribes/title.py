"""Title screen and the new-game setup overlay.

The title drifts over a fully revealed map so the game shows what it is
before a button is pressed.  Every option has a hotkey.
"""

from __future__ import annotations

import math
import random
from dataclasses import replace
from typing import Any

from saga2d import Anchor, Button, Camera, Column, Label, Row, Scene
from tribes import mapgen
from tribes.effects import play_sound
from tribes.rules import TRIBES
from tribes.scene import HelpScene, load_game, new_game
from tribes.style import ACTION_BUTTON, GHOST_BUTTON, MENU_BUTTON, OVERLAY_STYLE
from tribes.textures import FOG, TILE
from tribes.view import MapView, rgba, tile_center

MAP_SIZES: dict[str, int] = {"Small": 11, "Medium": 14, "Large": 18}
TRIBE_COUNTS = (2, 3, 4)
OPTION_WIDTH = 180
DRIFT_SECONDS = 26.0


class TitleScene(Scene):
    background_color = rgba(FOG)
    controls = {("n", "return"): "new_game", "c": "continue_game", "h": "how_to_play", "q": "quit"}

    def __init__(self, *, size: int = 14, tribes: int = 3, settings: dict[str, Any] | None = None) -> None:
        self.size = size
        self.tribes = tribes
        self.settings = settings
        self.time = 0.0
        self._drift_index = 0

    def on_enter(self) -> None:
        seed = random.randrange(1, 10_000)
        self.backdrop = mapgen.generate(seed=seed, size=16, tribe_count=4)
        every_tile = {tile.pos for tile in self.backdrop.all_tiles()}
        for tribe in self.backdrop.tribes:
            tribe.explored = set(every_tile)
        self.view = MapView(self, self.backdrop, 0, random.Random(seed))
        w, h = self.game.resolution
        left, top, right, bottom = self.view.world_bounds
        inset = TILE  # keep the view inside the map, never on the fog margin
        self.camera = Camera((w, h), world_bounds=(left + inset, top + inset, right - inset, bottom - inset), zoom=1.35, min_zoom=1.35, max_zoom=1.35)
        self._stops = [tile_center(city.pos) for city in self.backdrop.cities.values()]
        self.camera.center_on(*self._stops[0])
        self._drift()
        self._build_menu()

    def _drift(self) -> None:
        self._drift_index = (self._drift_index + 1) % len(self._stops)
        self.camera.pan_to(*self._stops[self._drift_index], duration=DRIFT_SECONDS)
        self.after(DRIFT_SECONDS, self._drift)

    def _build_menu(self) -> None:
        has_save = self.game.save_manager.load(1) is not None
        menu = Column(spacing=10, anchor=Anchor.CENTER, margin=0)
        menu.add(Label("", height=150))  # leaves room for the title drawn above
        menu.add(Button("New game", hotkey="N", on_click=self.new_game, style=ACTION_BUTTON, width=300))
        cont = Button("Continue", hotkey="C", on_click=self.continue_game, style=MENU_BUTTON, width=300)
        cont.enabled = has_save
        menu.add(cont)
        menu.add(Button("Multiplayer", shortcut="M", on_click=self.multiplayer, style=MENU_BUTTON, width=300))
        menu.add(Button("How to play", hotkey="H", on_click=self.how_to_play, style=MENU_BUTTON, width=300))
        menu.add(Button("Quit", hotkey="Q", on_click=self.quit, style=MENU_BUTTON, width=300))
        menu.add(Label("Continue resumes save slot 1" if has_save else "No saved game yet — F5 saves during play", text_style="caption"))
        self.ui.add(menu)
        self.ui.add(Label("Every action in the game has a hotkey — the keycaps show them · F1 in game for help",
                          text_style="caption", anchor=Anchor.BOTTOM_CENTER, margin=12))

    def update(self, dt: float) -> None:
        self.time += dt

    def draw(self) -> None:
        w, h = self.game.resolution
        self.draw_rect(0, 0, w, h, (10, 12, 22, 150))
        cy = h / 2 - 185
        glow = 0.5 + 0.5 * math.sin(self.time * 1.6)
        for spread, alpha in ((3, 40), (2, 70)):
            self.draw_text("TRIBES", w / 2 + spread, cy + spread, style="hero", color=(0, 0, 0, alpha + int(20 * glow)), anchor_x="center", anchor_y="center")
        self.draw_text("TRIBES", w / 2, cy, style="hero", anchor_x="center", anchor_y="center")
        self.draw_text("Capture villages · Harvest · Research · Conquer", w / 2, cy + 58, style="hero_sub", anchor_x="center", anchor_y="center")

    def sfx(self, name: str) -> None:
        if self.settings is None or self.settings["sfx"] > 0:
            play_sound(name)

    # -- Menu actions ------------------------------------------------------------

    def multiplayer(self) -> None:
        from saga2d import MatchMenu
        from tribes.multiplayer import TribesMatch, NetworkMapScene
        self.game.push(MatchMenu("Tribes multiplayer", "tribes-v1", TribesMatch, NetworkMapScene))

    def new_game(self) -> None:
        self.sfx("button")
        self.game.push(NewGameScene(self))

    def continue_game(self) -> None:
        save = self.game.save_manager.load(1)
        if save is None:
            self.sfx("error")
            return
        self.sfx("button")
        self.game.clear_and_push(load_game(save["state"], settings=self.settings))

    def how_to_play(self) -> None:
        self.sfx("button")
        self.game.push(HelpScene())

    def quit(self) -> None:
        self.game.quit()


class NewGameScene(Scene):
    """Map size, tribe count, which tribe to play, the seed, then Start."""

    transparent = True
    pause_below = False
    pop_on_cancel = True
    controls = {
        "s": "size_small", "m": "size_medium", "l": "size_large",
        "2": "tribes_2", "3": "tribes_3", "4": "tribes_4",
        "tab": "next_tribe", "r": "reroll", ("return", "space"): "start",
    }

    def __init__(self, title: TitleScene) -> None:
        self.title = title
        self.size = title.size
        self.tribes = title.tribes
        self.first_tribe = 0
        self.seed = random.randrange(1, 10_000)
        self._size_buttons: dict[int, Button] = {}
        self._tribe_buttons: dict[int, Button] = {}

    def on_enter(self) -> None:
        panel = Column(spacing=12, anchor=Anchor.CENTER, style=OVERLAY_STYLE)
        panel.add(Label("New game", text_style="title"))
        size_row = Row(Label("Map size", text_style="body", width=90), spacing=8)
        for name, size in MAP_SIZES.items():
            button = Button(f"{name} {size}×{size}", hotkey=name[0], on_click=lambda s=size: self.set_size(s), style=GHOST_BUTTON, width=OPTION_WIDTH)
            self._size_buttons[size] = button
            size_row.add(button)
        panel.add(size_row)
        tribe_row = Row(Label("Tribes", text_style="body", width=90), spacing=8)
        for count in TRIBE_COUNTS:
            button = Button(str(count), hotkey=str(count), on_click=lambda c=count: self.set_tribes(c), style=GHOST_BUTTON, width=OPTION_WIDTH)
            self._tribe_buttons[count] = button
            tribe_row.add(button)
        panel.add(tribe_row)
        self._play_as = Button(lambda: f"{TRIBES[self.first_tribe].name} — starts with {TRIBES[self.first_tribe].tech.value.title()}",
                               hotkey="Tab", on_click=self.next_tribe, width=2 * OPTION_WIDTH + 8)
        panel.add(Row(Label("Play as", text_style="body", width=90), self._play_as, spacing=8))
        panel.add(Row(Label(lambda: f"Seed {self.seed}", text_style="body", width=90 + 8 + OPTION_WIDTH),
                      Button("Reroll", hotkey="R", on_click=self.reroll, style=GHOST_BUTTON, width=OPTION_WIDTH), spacing=8))
        panel.add(Row(Button("Start", hotkey="Enter", on_click=self.start, style=ACTION_BUTTON, width=2 * OPTION_WIDTH + 8),
                      Button("Back", hotkey="Esc", on_click=self.game.pop, style=GHOST_BUTTON, width=OPTION_WIDTH), spacing=8))
        self.ui.add(panel)
        self._restyle()

    def _restyle(self) -> None:
        for size, button in self._size_buttons.items():
            button.style = ACTION_BUTTON if size == self.size else GHOST_BUTTON
        for count, button in self._tribe_buttons.items():
            button.style = ACTION_BUTTON if count == self.tribes else GHOST_BUTTON
        self._play_as.style = replace(GHOST_BUTTON, text_color=rgba(TRIBES[self.first_tribe].color))

    def next_tribe(self) -> None:
        self.first_tribe = (self.first_tribe + 1) % len(TRIBES)
        self.title.sfx("button")
        self._restyle()

    def draw(self) -> None:
        w, h = self.game.resolution
        self.draw_rect(0, 0, w, h, (4, 6, 12, 140))

    def set_size(self, size: int) -> None:
        self.size = size
        self.title.sfx("button")
        self._restyle()

    def set_tribes(self, count: int) -> None:
        self.tribes = count
        self.title.sfx("button")
        self._restyle()

    def size_small(self) -> None:
        self.set_size(MAP_SIZES["Small"])

    def size_medium(self) -> None:
        self.set_size(MAP_SIZES["Medium"])

    def size_large(self) -> None:
        self.set_size(MAP_SIZES["Large"])

    def tribes_2(self) -> None:
        self.set_tribes(2)

    def tribes_3(self) -> None:
        self.set_tribes(3)

    def tribes_4(self) -> None:
        self.set_tribes(4)

    def reroll(self) -> None:
        self.seed = random.randrange(1, 10_000)
        self.title.sfx("button")

    def start(self) -> None:
        self.title.sfx("button")
        self.game.clear_and_push(new_game(self.seed, size=self.size, tribes=self.tribes, settings=self.title.settings, first_tribe=self.first_tribe))
