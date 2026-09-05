"""The game's presentation: shard, stronghold and a separate tactical scene.

Scenes translate input into model commands. Saga2D owns the UI tree,
scene lifetimes, hotkeys, geometry, drawing and save files.
"""

from __future__ import annotations

import textwrap
from collections import Counter

from saga2d import Anchor, Button, HexGrid, InputEvent, SaveError, Scene

from eador import art
from eador.content import RELICS, SKILLS
from eador.model import BUILDINGS, HERO_CLASSES, RECRUITABLE, UNITS, RuleError, State
from eador.persistence import MANUAL_SLOTS, CampaignSaves
from eador.style import BLUE, DANGER, GOLD, INK, LINE, MUTED, PANEL, PRIMARY, RED, TEAL, TEXT, build_theme


class Screen(Scene):
    background_color = INK

    def __init__(self):
        self.message = ""

    def on_enter(self):
        self.game.theme = build_theme()
        self.refresh()

    def refresh(self):
        self.ui.clear()

    @property
    def saves(self):
        return CampaignSaves(self.game.save_manager)

    def checkpoint(self, state):
        try:
            self.saves.autosave(state)
        except SaveError as error:
            self.message = f"Autosave failed: {error}"
            return False
        return True

    def load_game(self, slot=1, *, backup=False):
        try:
            state = self.saves.load(slot, backup=backup)
        except SaveError as error:
            self.message = str(error)
            return False
        if state is None:
            self.message = "This slot is empty. Open Saves to choose another."
            return False
        self.game.clear_and_push(ShardScene(state))
        return True

    def button(self, text, x, y, width, callback, *, hotkey=None, shortcut=None, primary=False, danger=False, enabled=True):
        button = Button(text, on_click=callback, hotkey=hotkey, shortcut=shortcut, width=width, height=40,
                        anchor=Anchor.TOP_LEFT, margin=(round(x), round(y)), enabled=enabled,
                        style=PRIMARY if primary else DANGER if danger else None)
        self.ui.add(button)
        return button

    def text(self, text, x, y, *, size=14, color=TEXT, center=False, serif=False):
        self.draw_text(str(text), x, y, font_size=size, color=color, font="Georgia" if serif else "Verdana",
                       anchor_x="center" if center else "left", anchor_y="top")

    def paragraph(self, text, x, y, *, width=300, size=13, color=MUTED):
        return self.draw_paragraph(text, x, y, width, font_size=size, font="Verdana",
                                   color=color, line_spacing=1.25)

    def box(self, x, y, w, h):
        self.draw_rect(x, y, w, h, PANEL, border_color=LINE, border_width=1, radius=5)

    def rule(self, x, y, width):
        self.draw_line(x, y, x + width, y, LINE)

    def bar(self, x, y, width, value, maximum, color=TEAL):
        self.draw_rect(x, y, width, 4, (9, 20, 24, 255), radius=2)
        self.draw_rect(x, y, width * max(0, min(1, value / maximum)), 4, color, radius=2)

    def command(self, callback):
        try:
            callback()
        except RuleError as error:
            self.message = str(error)
            return False
        self.message = ""
        self.refresh()
        return True


class TitleScene(Screen):
    controls = {("return", "space"): "start", "tab": "next_class", "f9": "load_game", "f6": "browse_saves"}

    def __init__(self, seed=7):
        super().__init__()
        self.seed = seed
        self.hero_class = "Commander"

    def refresh(self):
        super().refresh()
        w, h = self.game.resolution
        for i, name in enumerate(HERO_CLASSES):
            self.button(name, w / 2 - 302 + i * 154, h - 240, 142,
                        lambda name=name: self.choose(name), primary=name == self.hero_class)
        self.button("Enter the shard", w / 2 - 170, h - 124, 340, self.start, hotkey="Enter", primary=True)
        self.button("Load shard", w / 2 - 170, h - 72, 164, self.browse_saves, hotkey="F6")
        self.button("New seed", w / 2 + 6, h - 72, 164, self.next_seed, shortcut="N")

    def choose(self, name):
        self.hero_class = name
        self.refresh()

    def next_class(self):
        names = list(HERO_CLASSES)
        self.choose(names[(names.index(self.hero_class) + 1) % len(names)])

    def next_seed(self):
        self.seed += 1

    def start(self):
        state = State.new(self.seed, self.hero_class)
        root = ShardScene(state)
        if not self.checkpoint(state):
            root.message = self.message
        self.game.replace(root)

    def browse_saves(self):
        self.game.push(SaveScene())

    def draw(self):
        w, h = self.game.resolution
        art.backdrop(self, w, h)
        self.text("C H R O N I C L E S   O F   T H E   S H A R D S", w / 2, 56, size=11, color=GOLD, center=True)
        self.text("SHARDBOUND", w / 2, 88, size=64, serif=True, center=True)
        self.text("One broken world. A kingdom to build.", w / 2, 169, size=17, color=MUTED, center=True)
        cells = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1), (-1, 1), (1, -1)]
        grid = HexGrid(cells, size=53, origin=(w / 2, 340))
        from types import SimpleNamespace
        for i, pos in enumerate(sorted(cells, key=lambda c: grid.center(c)[1])):
            data = SimpleNamespace(terrain=("forest", "hills", "plains")[i % 3], owner="player" if pos == (0, 0) else "neutral",
                                   capital=pos == (0, 0), site=None, explored=False, name="Westwatch" if pos == (0, 0) else "")
            art.province(self, grid, pos, data)
        self.text("CHOOSE YOUR HERO", w / 2, h - 277, size=11, color=GOLD, center=True)
        self.text(HERO_CLASSES[self.hero_class].description, w / 2, h - 181, size=14, color=MUTED, center=True)
        self.text(self.message or f"Shard {self.seed}  ·  Conquer provinces, explore ruins, command every battle.",
                  w / 2, h - 155, size=11, color=RED if self.message else MUTED, center=True)


class ShardScene(Screen):
    controls = {"e": "end_turn", "b": "buildings", "r": "recruitment", "x": "explore",
                ("return", "space"): "travel", "tab": "next_province", "home": "home",
                "f5": "save_game", "f9": "load_game", "f6": "browse_saves", "h": "hero_details",
                ("f1", "escape"): "help"}

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.selected = state.hero.pos
        self._last_hero_pos = state.hero.pos
        self.hover = None

    @property
    def edge(self):
        return self.game.width - 344

    def on_enter(self):
        super().on_enter()
        self.follow_state()

    def on_reveal(self):
        if self.state.hero.pos != self._last_hero_pos:
            self.selected = self.state.hero.pos
        self.refresh()
        self.follow_state()

    def follow_state(self):
        if self.state.battle is not None:
            self.game.push(BattleScene(self))
        elif self.state.choice is not None:
            self.game.push(ChoiceScene(self))
        elif self.state.status != "playing":
            self.game.push(ResultScene(self))

    def refresh(self):
        super().refresh()
        self._last_hero_pos = self.state.hero.pos
        w, h = self.game.resolution
        self.grid = HexGrid(self.state.provinces, size=min((h - 246) / 8, (self.edge - 130) / 8.67),
                            origin=(self.edge / 2, (h - 30) / 2))
        x = self.edge + 22
        province = self.state.provinces[self.selected]
        playing = self.state.status == "playing"
        here = self.selected == self.state.hero.pos
        adjacent = self.selected in self.grid.neighbors(self.state.hero.pos)
        can_act = playing and self.state.actions_left > 0
        expedition_here = self.state.rival.army and self.selected == self.state.rival.pos
        self.button("Hero is here" if here else "Intercept expedition" if expedition_here else
                    "Travel here" if province.owner == "player" else "Invade province",
                    x, 423, 300, self.travel, hotkey="Enter", primary=True, enabled=can_act and adjacent)
        current = self.state.provinces[self.state.hero.pos]
        self.button("Explore current province", x, 473, 300, self.explore, hotkey="X",
                    enabled=can_act and current.owner == "player" and current.site is not None and not current.explored)
        self.button("Build stronghold", x, 555, 300, self.buildings, hotkey="B", enabled=playing)
        self.button("Recruit troops", x, 605, 300, self.recruitment, hotkey="R", enabled=playing)
        self.button("End turn", x, h - 93, 300, self.end_turn, hotkey="E", primary=True, enabled=playing)
        self.button("Guide", 26, 30, 94, self.help, hotkey="F1")
        self.button("Hero", 130, 30, 88, self.hero_details, hotkey="H")
        self.button("Codex", 228, 30, 110, self.codex, shortcut="C")
        self.button("Save", self.edge - 177, 30, 72, lambda: self.browse_saves("save"))
        self.button("Load", self.edge - 97, 30, 72, self.browse_saves)
        self.button("Rival plan", self.edge - 185, 180, 160, self.rival_details, shortcut="V")

    def get_save_state(self):
        return {"campaign": self.state.to_json()}

    def save_game(self):
        try:
            self.saves.save(self.state)
        except SaveError as error:
            self.message = str(error)
        else:
            self.message = "Saved to Manual 1. F9 restores it; F6 opens all manual saves and autosaves."

    def browse_saves(self, mode="load"):
        self.game.push(SaveScene(self, mode=mode))

    def hero_details(self):
        self.game.push(HeroScene(self))

    def codex(self):
        from eador.codex import CodexScene
        self.game.push(CodexScene(self))

    def rival_details(self):
        from eador.rival_scene import RivalScene
        self.game.push(RivalScene(self))

    def act(self, callback):
        if self.command(callback):
            self.checkpoint(self.state)
            self.follow_state()

    def travel(self):
        self.act(lambda: self.state.travel(self.selected))

    def explore(self):
        self.act(self.state.explore)

    def end_turn(self):
        self.act(self.state.end_turn)

    def buildings(self):
        self.game.push(CatalogScene(self, "build"))

    def recruitment(self):
        self.game.push(CatalogScene(self, "recruit"))

    def help(self):
        self.game.push(HelpScene(self))

    def home(self):
        self.selected = self.state.hero.pos
        self.refresh()

    def next_province(self):
        neighbors = list(self.grid.neighbors(self.state.hero.pos))
        i = neighbors.index(self.selected) + 1 if self.selected in neighbors else 0
        self.selected = neighbors[i % len(neighbors)]
        self.refresh()

    def handle_input(self, event: InputEvent):
        if event.type == "move":
            self.hover = self.grid.cell_at(event.x, event.y)
        if event.type == "click" and event.button == "left" and self.state.status == "playing":
            pos = self.grid.cell_at(event.x, event.y)
            if pos is not None:
                self.selected = pos
                self.refresh()
                return True
        return False

    def draw(self):
        from eador.rival_scene import rival_order

        s, h, x = self.state, self.game.height, self.edge + 22
        art.backdrop(self, self.edge, h)
        self.draw_rect(self.edge, 0, 344, h, PANEL)
        self.draw_line(self.edge, 0, self.edge, h, LINE)
        self.draw_rect(0, 0, self.edge, 91, INK)
        self.rule(24, 90, self.edge - 48)
        header_center = (338 + self.edge - 177) / 2
        self.text("SHARDBOUND", header_center, 24, size=27, serif=True, center=True)
        self.text(f"THE VERDANT REACH   /   SHARD {s.seed}", header_center, 61, size=10, color=GOLD, center=True)
        self.text("YOUR DOMINION", x, 24, size=10, color=MUTED)
        self.text(f"{s.gold} gold", x, 48, size=22, color=GOLD, serif=True)
        self.text(f"{s.crystals} crystals", x + 160, 52, size=15, color=BLUE)
        self.text(f"Income +{s.income}   ·   Upkeep −{s.upkeep}   / turn", x, 84, size=11, color=MUTED)
        self.rule(x, 112, 300)
        self.text(f"{s.hero.name}, the {s.hero.hero_class}", x, 132, size=21, serif=True)
        self.text(f"LEVEL {s.hero.level}  ·  {s.hero.xp} XP  ·  {s.actions_left} ACTIONS LEFT", x, 166, size=10, color=GOLD)
        self.text(f"Health {s.hero.hp}/{s.hero.max_hp}", x, 192, size=12, color=TEAL)
        self.text(f"Mana {s.hero.mana}/{s.hero.max_mana}", x + 166, 192, size=12, color=BLUE)
        self.bar(x, 216, 134, s.hero.hp, s.hero.max_hp)
        self.bar(x + 166, 216, 134, s.hero.mana, s.hero.max_mana, BLUE)
        self.text(f"At {s.provinces[s.hero.pos].name}", x, 231, size=11, color=MUTED)
        self.rule(x, 259, 300)
        p = s.provinces[self.selected]
        self.text("SELECTED PROVINCE", x, 279, size=10, color=MUTED)
        self.text(p.name, x, 302, size=27, serif=True)
        self.text(f"{p.terrain.title()}  ·  {p.owner.title()}  ·  +{p.income} gold", x, 344, size=12, color=art.OWNERS[p.owner])
        if s.rival.army and self.selected == s.rival.pos:
            self.text(f"Expedition: {len(s.rival.army)} troops · V for strengths", x, 369, size=11, color=RED)
        elif p.owner != "player":
            guards = ", ".join(f"{n} {UNITS[kind].name}" for kind, n in Counter(p.guards).items())
            self.text(textwrap.shorten(guards, width=40, placeholder="…"), x, 369, size=11, color=RED)
        else:
            self.text("Ruins cleared" if p.explored else p.site or "No ruins in this province", x, 369, size=12, color=GOLD)
        hint = "Select a neighboring province to travel."
        if not s.actions_left:
            hint = "No hero actions left. End the turn to recover."
        elif self.selected != s.hero.pos and self.selected not in self.grid.neighbors(s.hero.pos):
            hint = "This province is not adjacent to your hero."
        self.text(hint, x, 395, size=11, color=MUTED)
        self.text("YOUR STRONGHOLD", x, 531, size=10, color=MUTED)
        self.text(f"{len(s.buildings)}/{len(BUILDINGS)} buildings  ·  {len(s.hero.army)}/{s.hero.max_army} troops", x, 662, size=11, color=MUTED)
        self.text(f"TURN {s.turn}  ·  Rival expedition: {len(s.rival.army)} troops", x, h - 37, size=10, color=MUTED)
        # Back-to-front relief keeps the southern edge of the shard continuous.
        for pos in sorted(s.provinces, key=lambda c: self.grid.center(c)[1]):
            art.province(self, self.grid, pos, s.provinces[pos], selected=pos == self.selected,
                         hero=pos == s.hero.pos, hover=pos == self.hover)
        if s.rival.army:
            art.expedition(self, self.grid, s.rival.pos, len(s.rival.army))
        art.compass(self, 75, 162)
        self.text("Capture Duskspire", self.edge - 185, 122, size=13, color=GOLD, serif=True)
        self.text("Protect Westwatch", self.edge - 185, 146, size=11, color=MUTED)
        self.paragraph(rival_order(s), self.edge - 185, 232, width=160, size=11, color=RED)
        self.text("YOUR ARMY", 28, h - 112, size=10, color=MUTED)
        for i, troop in enumerate(s.hero.army):
            xx = 100 + i * 124
            art.piece(self, xx, h - 61, troop.kind, "player", scale=.61)
            self.text(UNITS[troop.kind].name, xx + 23, h - 88, size=10)
            self.text(f"Lv{troop.level} · {troop.hp}/{troop.max_hp}", xx + 23, h - 69, size=9, color=MUTED)
            self.bar(xx + 23, h - 50, 66, troop.hp, troop.max_hp)
        self.rule(26, h - 124, self.edge - 52)
        message = self.message or s.log[-1]
        self.text(textwrap.shorten(message, width=110, placeholder="…"), 28, h - 26, size=11,
                  color=GOLD if self.message else MUTED)


class CatalogScene(Screen):
    transparent = True
    pop_on_cancel = True

    def __init__(self, root, kind):
        super().__init__()
        self.root, self.kind = root, kind

    def refresh(self):
        super().refresh()
        self.x, self.y = self.game.width / 2 - 360, self.game.height / 2 - 300
        self.items = list(BUILDINGS) if self.kind == "build" else list(RECRUITABLE)
        s = self.root.state
        for i, name in enumerate(self.items):
            spec = BUILDINGS[name] if self.kind == "build" else UNITS[name]
            built = self.kind == "build" and name in s.buildings
            locked = self.kind == "recruit" and spec.building and spec.building not in s.buildings
            available = self.kind == "build" or (len(s.hero.army) < s.hero.max_army
                                                  and s.provinces[s.hero.pos].owner == "player")
            cost = spec.cost if self.kind == "build" else s.recruit_cost(name)
            affordable = s.gold >= cost and (self.kind != "build" or s.crystals >= spec.crystals)
            self.button("Built" if built else "Locked" if locked else f"{cost} gold", self.x + 548,
                        self.y + 123 + i * 77, 143, lambda name=name: self.purchase(name), shortcut=str(i + 1),
                        enabled=not built and not locked and affordable and available)
        self.button("Back to shard", self.x + 22, self.y + 535, 676, self.game.pop, hotkey="Esc")

    def purchase(self, name):
        callback = self.root.state.build if self.kind == "build" else self.root.state.recruit
        if self.command(lambda: callback(name)):
            if self.checkpoint(self.root.state):
                self.message = self.root.state.log[-1]

    def draw(self):
        x, y, s = self.x, self.y, self.root.state
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 200))
        self.box(x, y, 720, 600)
        self.text("WESTWATCH / STRONGHOLD", x + 24, y + 22, size=10, color=GOLD)
        self.text("Build your kingdom" if self.kind == "build" else "Raise an army", x + 24, y + 46, size=31, serif=True)
        self.text(f"{s.gold} gold   ·   {s.crystals} crystals   ·   {len(s.hero.army)}/{s.hero.max_army} troops", x + 24, y + 94, size=12, color=MUTED)
        for i, name in enumerate(self.items):
            yy = y + 127 + i * 77
            spec = BUILDINGS[name] if self.kind == "build" else UNITS[name]
            self.rule(x + 22, yy - 9, 676)
            self.text(spec.name, x + 26, yy, size=19, serif=True)
            if self.kind == "build":
                description = spec.description + (f" Costs {spec.crystals} crystals." if spec.crystals else "")
            else:
                description = f"{spec.hp} HP  /  {spec.attack} attack  /  range {spec.attack_range}  /  upkeep {spec.upkeep}"
                if spec.building and spec.building not in s.buildings:
                    description = f"Requires {BUILDINGS[spec.building].name}. " + description
            self.paragraph(description, x + 26, yy + 29, width=500, size=11)
        self.text(textwrap.shorten(self.message or "Buildings are permanent. Recruit in any province you control.", width=93, placeholder="…"),
                  x + 24, y + 507, size=11, color=GOLD)


class HelpScene(Screen):
    transparent = True
    pop_on_cancel = True

    def __init__(self, root):
        super().__init__()
        self.root = root

    def refresh(self):
        super().refresh()
        self.x, self.y = self.game.width / 2 - 340, self.game.height / 2 - 280
        self.button("Return to game", self.x + 26, self.y + 481, 212, self.game.pop, shortcut="Esc", primary=True)
        self.button("Codex", self.x + 249, self.y + 481, 192, self.root.codex, shortcut="C")
        self.button("Save & title", self.x + 452, self.y + 481, 202, self.title, shortcut="S")

    def title(self):
        self.game.push(SaveScene(self.root, mode="save", return_to_title=True))

    def draw(self):
        x, y = self.x, self.y
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 210))
        self.box(x, y, 680, 560)
        self.text("A FIELD GUIDE", x + 28, y + 26, size=11, color=GOLD)
        self.text("Claim a broken world", x + 28, y + 54, size=32, serif=True)
        sections = [
            ("01   Establish your foothold", "Build a barracks or marketplace. Recruit in your territory. Troops cost upkeep; provinces provide income."),
            ("02   March and explore", "Select a neighboring province, then Invade. Travel and exploration spend hero actions. Explore owned provinces for treasure and experience."),
            ("03   Command the battle", "Select a unit, move to a blue hex, then attack a marked enemy. Terrain gives cover. Spells cost mana and the hero's action."),
            ("04   Grow and counterattack", "Win battles to choose skills; H equips relics. V reveals the rival's army and next order. Intercept it or defend its target, then advance while it pays to rebuild."),
        ]
        for i, (title, body) in enumerate(sections):
            yy = y + 119 + i * 84
            self.text(title, x + 28, yy, size=17, serif=True, color=TEAL)
            self.paragraph(body, x + 28, yy + 28, width=624, size=12)
        self.text("F5 quicksave  /  F9 quickload  /  F6 save slots  /  Capture Duskspire to win", x + 28, y + 459, size=11, color=GOLD)


class BattleScene(Screen):
    controls = {"e": "end_turn", "tab": "next_unit", "1": "bolt", "2": "heal",
                "a": "auto_round", "f5": "save_game", "f9": "load_game", "f6": "browse_saves",
                "escape": "cancel", "f1": "help", "t": "retreat", "f": "next_target",
                ("return", "space"): "activate_cursor",
                ("left", "right", "up", "down", "pageup", "pagedown"): "aim"}

    def __init__(self, root):
        super().__init__()
        self.root = root
        self.selected = None
        self.spell = None
        self.hover = None
        self.cursor = self.battle.unit(0).pos
        self.floats = []
        self.clock = 0.0

    @property
    def battle(self):
        return self.root.state.battle

    @property
    def edge(self):
        return self.game.width - 344

    def on_enter(self):
        super().on_enter()
        if self.battle.outcome:
            self.game.push(ResultScene(self.root, battle=True))

    def refresh(self):
        super().refresh()
        b = self.battle
        x, h = self.edge + 22, self.game.height
        # Fit any finite battle board; topology, picking and polygons share one grid.
        geometry = HexGrid(b.terrain)
        centers = [geometry.center(p) for p in b.terrain]
        left, right = min(p[0] for p in centers) - .866, max(p[0] for p in centers) + .866
        top, bottom = min(p[1] for p in centers) - 1, max(p[1] for p in centers) + 1
        size = min((self.edge - 100) / (right - left), (h - 288) / (bottom - top))
        origin = (self.edge / 2 - (left + right) / 2 * size, (h - 50) / 2 - (top + bottom) / 2 * size)
        self.grid = HexGrid(b.terrain, size=size, origin=origin)
        alive = [u for u in b.units if u.team == "player" and u.hp > 0]
        if self.selected is None or not any(u.id == self.selected for u in alive):
            self.selected = alive[0].id if alive else None
        hero_ready = b.unit(0).hp > 0 and not b.unit(0).acted and b.outcome is None
        self.button(f"Arcane Bolt · {b.spell_cost('bolt')} mana", x, 378, 300, self.bolt, hotkey="1",
                    enabled="bolt" in b.spells and b.mana >= b.spell_cost("bolt") and hero_ready)
        self.button(f"Healing light · {b.spell_cost('heal')} mana", x, 428, 300, self.heal, hotkey="2",
                    enabled="heal" in b.spells and b.mana >= b.spell_cost("heal") and hero_ready)
        self.button("Auto-play one round", x, 518, 300, self.auto_round, hotkey="A", enabled=b.outcome is None)
        self.button("Retreat", x, 568, 300, self.retreat, hotkey="T", danger=True, enabled=b.outcome is None)
        self.button("End battle round", x, h - 93, 300, self.end_turn,
                    hotkey="E", primary=True, enabled=b.outcome is None)
        self.button("Guide", 26, 29, 94, self.help, hotkey="F1")
        self.button("Codex", 130, 29, 110, self.root.codex, shortcut="C")
        self.button("Save", self.edge - 105, 29, 79, self.save_game)

    def act(self, callback, *, checkpoint=False):
        before = {u.id: u.hp for u in self.battle.units}
        if self.command(callback):
            for u in self.battle.units:
                change = u.hp - before[u.id]
                if change:
                    self.floats.append((self.clock, u.pos, change))
            self.spell = None
            if checkpoint or self.battle.outcome:
                self.checkpoint(self.root.state)
            if self.battle.outcome:
                self.game.push(ResultScene(self.root, battle=True))

    def end_turn(self):
        self.act(self.battle.end_turn, checkpoint=True)

    def auto_round(self):
        self.act(self.battle.auto_turn, checkpoint=True)

    def retreat(self):
        try:
            self.root.state.retreat()
        except RuleError as error:
            self.message = str(error)
        else:
            if not self.checkpoint(self.root.state):
                self.root.message = self.message
            self.game.pop()

    def save_game(self):
        self.root.save_game()
        self.message = self.root.message

    def browse_saves(self):
        self.game.push(SaveScene(self.root))

    def help(self):
        self.game.push(HelpScene(self.root))

    def cancel(self):
        if self.spell:
            self.spell = None
        else:
            self.help()

    def choose_spell(self, name):
        if name not in self.battle.spells:
            self.message = "Build a Temple for Heal or a Mage Tower for Arcane Bolt."
            return
        self.spell = None if self.spell == name else name
        self.message = ("Choose a wounded ally" if name == "heal" else "Choose an enemy") + " within 4 hexes of your hero."

    def bolt(self):
        self.choose_spell("bolt")

    def heal(self):
        self.choose_spell("heal")

    def next_unit(self):
        units = [u for u in self.battle.units if u.team == "player" and u.hp > 0 and not u.acted]
        if units:
            ids = [u.id for u in units]
            self.selected = ids[(ids.index(self.selected) + 1) % len(ids)] if self.selected in ids else ids[0]
            self.cursor = self.hover = self.battle.unit(self.selected).pos
            self.spell = None

    def aim(self, event):
        directions = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1),
                      "pageup": (1, -1), "pagedown": (-1, 1)}
        dq, dr = directions[event.key]
        pos = self.cursor[0] + dq, self.cursor[1] + dr
        if pos in self.battle.terrain:
            self.cursor = self.hover = pos

    def next_target(self):
        team = "player" if self.spell == "heal" else "enemy"
        targets = [u.pos for u in self.battle.units if u.hp > 0 and u.team == team]
        if targets:
            index = (targets.index(self.cursor) + 1) % len(targets) if self.cursor in targets else 0
            self.cursor = self.hover = targets[index]

    def activate_cursor(self):
        self.hover = self.cursor
        self.act_at(self.cursor)

    def update(self, dt):
        self.clock += dt
        self.floats = [f for f in self.floats if self.clock - f[0] < 1.6]

    def handle_input(self, event):
        if event.type == "move":
            self.hover = self.grid.cell_at(event.x, event.y)
            if self.hover is not None:
                self.cursor = self.hover
        if event.type != "click" or event.button != "left" or self.battle.outcome:
            return False
        pos = self.grid.cell_at(event.x, event.y)
        if pos is None:
            return False
        self.cursor = self.hover = pos
        self.act_at(pos)
        return True

    def act_at(self, pos):
        if self.battle.outcome is not None:
            return
        unit = next((u for u in self.battle.units if u.hp > 0 and u.pos == pos), None)
        if self.spell:
            if unit:
                self.act(lambda: self.battle.cast(self.spell, unit.id))
            else:
                self.message = "Aim at a unit to cast. F cycles targets; Esc cancels targeting."
        elif unit and unit.team == "player":
            self.selected = unit.id
        elif unit and self.selected is not None:
            self.act(lambda: self.battle.attack(self.selected, unit.id))
        elif self.selected is not None:
            self.act(lambda: self.battle.move(self.selected, pos))

    def draw(self):
        b, s, h, x = self.battle, self.root.state, self.game.height, self.edge + 22
        art.backdrop(self, self.edge, h)
        self.draw_rect(self.edge, 0, 344, h, PANEL)
        self.draw_line(self.edge, 0, self.edge, h, LINE)
        self.text("BATTLE FOR " + s.provinces[s.battle_province].name.upper(), self.edge / 2, 26,
                  size=25, serif=True, center=True)
        self.text(f"{s.battle_kind.upper()}   /   ROUND {b.round}", self.edge / 2, 63, size=10, color=GOLD, center=True)
        self.rule(26, 90, self.edge - 52)
        self.text("TACTICAL COMMAND", x, 30, size=10, color=GOLD)
        self.text("Your army", x, 57, size=30, serif=True)
        allies = sum(u.hp > 0 and u.team == "player" for u in b.units)
        enemies = sum(u.hp > 0 and u.team != "player" for u in b.units)
        self.text(f"{allies} standing  ·  {enemies} enemies", x, 104, size=12, color=MUTED)
        self.rule(x, 138, 300)
        selected = b.unit(self.selected) if self.selected is not None else None
        if selected:
            self.text(s.hero.hero_class if selected.id == 0 else UNITS[selected.kind].name,
                      x, 159, size=25, serif=True)
            self.text(f"Health {selected.hp} / {selected.max_hp}", x, 198, size=13, color=TEAL)
            self.bar(x, 225, 300, selected.hp, selected.max_hp)
            self.text(f"Attack {selected.attack}   Defense {selected.defense}", x, 246, size=13)
            self.text(f"Movement {selected.move_range}   Range {selected.attack_range}", x, 272, size=13, color=MUTED)
            self.text("Action spent" if selected.acted else "Moved · attack available" if selected.moved else "Ready to move and attack",
                      x, 301, size=12, color=GOLD)
        self.rule(x, 336, 300)
        self.text(f"SPELLBOOK   /   {b.mana} MANA", x, 353, size=10, color=BLUE)
        self.text("Spells use mana and the hero's action.", x, 479, size=11, color=MUTED)
        hovered = next((u for u in b.units if u.hp > 0 and u.pos == self.hover), None)
        if hovered:
            self.text(f"{hovered.name}  ·  {hovered.hp}/{hovered.max_hp} HP", x, 630, size=13, color=GOLD)
            if selected and hovered in b.targets(selected.id):
                damage, retaliation = b.preview(selected.id, hovered.id)
                self.text(f"Deal {damage}  /  Take {retaliation} in retaliation", x, 655, size=12, color=RED)
            else:
                self.text(f"Attack {hovered.attack}  ·  Defense {hovered.defense}  ·  Range {hovered.attack_range}",
                          x, 655, size=11, color=MUTED)
            self.text(f"Terrain: {b.terrain[hovered.pos].title()}", x, 679, size=11, color=MUTED)
        else:
            self.paragraph("Forest and hills grant cover. Marsh slows movement. Melee defenders retaliate once per round.",
                           x, 630, size=11)
        self.text("Arrows aim · Enter act · F target · Tab unit", x, h - 37, size=10, color=MUTED)
        reachable = b.reachable(self.selected) if selected and not selected.acted and b.outcome is None else set()
        targets = {u.id for u in b.targets(self.selected)} if selected and not selected.acted and b.outcome is None else set()
        for pos in sorted(b.terrain, key=lambda p: self.grid.center(p)[1]):
            cx, cy = self.grid.center(pos)
            points = [(cx + (px - cx) * .95, cy + (py - cy) * .95) for px, py in self.grid.corners(pos)]
            color = art.TERRAINS[b.terrain[pos]]
            self.draw_polygon([(px, py + 8) for px, py in points], art.shade(color, -47))
            self.draw_polygon(points, art.shade(color, -13))
            art.outline(self, points, art.shade(color, 5))
            if pos in reachable:
                self.draw_polygon(points, (104, 182, 207, 53))
                art.outline(self, points, (125, 181, 185, 150), 1.5)
                self.draw_circle(cx, cy, 2, (168, 223, 211, 255))
            if b.terrain[pos] in ("forest", "hills", "marsh"):
                art.terrain_detail(self, b.terrain[pos], cx, cy + 12, pos[0] * 23 + pos[1], .35)
            if pos == self.hover:
                art.outline(self, points, GOLD, 2)
        for u in sorted((u for u in b.units if u.hp > 0), key=lambda u: self.grid.center(u.pos)[1]):
            cx, cy = self.grid.center(u.pos)
            if u.id in targets:
                self.draw_circle(cx, cy + 7, 25, RED)
            art.piece(self, cx, cy - 1, s.hero.hero_class if u.id == 0 else u.kind, u.team, scale=min(1, self.grid.size / 43),
                      selected=u.id == self.selected, spent=u.acted)
            self.draw_rect(cx - 29, cy + 29, 58, 16, INK, radius=3)
            self.text(f"{u.hp}/{u.max_hp}", cx, cy + 29, size=10, center=True)
            self.bar(cx - 26, cy + 46, 52, u.hp, u.max_hp, TEAL if u.team == "player" else RED)
        for started, pos, change in self.floats:
            cx, cy = self.grid.center(pos)
            self.text(f"{change:+}", cx, cy - 48 - (self.clock - started) * 20, size=23,
                      color=TEAL if change > 0 else RED, center=True)
        self.rule(26, h - 122, self.edge - 52)
        for i, line in enumerate(b.log[-3:]):
            self.text(textwrap.shorten(line, width=105, placeholder="…"), 30, h - 102 + i * 24,
                      size=11, color=MUTED)
        self.text(self.message or ("Click a target for " + self.spell if self.spell else "Select a unit. Blue hexes are reachable; red rings are attack targets."),
                  30, h - 26, size=11, color=GOLD)


class SaveScene(Screen):
    """File errors stay visible without replacing the campaign being played."""

    transparent = True
    pop_on_cancel = True

    def __init__(self, root=None, *, mode="load", return_to_title=False):
        super().__init__()
        self.root, self.mode = root, mode
        self.return_to_title = return_to_title

    def refresh(self):
        super().refresh()
        self.x, self.y = self.game.width / 2 - 410, self.game.height / 2 - 324
        self.entries = self.saves.entries()
        x, y = self.x, self.y
        for i, entry in enumerate(self.entries):
            can_save = self.mode == "save" and entry.slot in MANUAL_SLOTS
            can_load = self.mode == "load" and entry.exists
            self.button("Save" if can_save else "Load", x + 540, y + 100 + i * 70, 92,
                        lambda i=i: self.activate(i), shortcut=str(i + 1), enabled=can_save or can_load)
            self.button("Backup", x + 642, y + 100 + i * 70, 150,
                        lambda i=i: self.recover(i), shortcut=f"Shift+{i + 1}",
                        enabled=entry.backup_available and self.mode == "load")
        if self.root is not None and not self.return_to_title:
            self.button("Save slots" if self.mode == "load" else "Load slots", x + 28, y + 590, 164, self.toggle, shortcut="Tab")
        self.button("Close", x + 650, y + 590, 140, self.game.pop, shortcut="Esc")

    def toggle(self):
        if self.root is None or self.return_to_title:
            return
        self.mode = "save" if self.mode == "load" else "load"
        self.message = ""
        self.refresh()

    def recover(self, index):
        if self.mode == "load" and self.entries[index].backup_available:
            self.load_game(self.entries[index].slot, backup=True)

    def activate(self, index):
        entry = self.entries[index]
        if self.mode == "load":
            self.load_game(entry.slot)
        elif entry.slot in MANUAL_SLOTS:
            try:
                self.saves.save(self.root.state, entry.slot)
            except SaveError as error:
                self.message = str(error)
            else:
                self.message = f"Saved to {entry.label}."
                if self.return_to_title:
                    self.game.clear_and_push(TitleScene(self.root.state.seed))
                    return
            self.refresh()

    def draw(self):
        x, y = self.x, self.y
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 205))
        self.box(x, y, 820, 648)
        self.text("SAVE YOUR CHRONICLE" if self.mode == "save" else "RETURN TO A CHRONICLE", x + 28, y + 21,
                  size=26, serif=True, color=GOLD)
        self.text("Choose a manual slot to save, then return to the title." if self.return_to_title else
                  "Three manual slots. Autosaves rotate after campaign actions and battle rounds.",
                  x + 28, y + 63, size=11, color=MUTED)
        for i, entry in enumerate(self.entries):
            top = y + 94 + i * 70
            self.rule(x + 28, top - 7, 764)
            self.text(entry.label, x + 28, top, size=13, color=GOLD)
            if entry.timestamp:
                self.text(entry.timestamp[:19].replace("T", "  ") + " UTC", x + 168, top + 2, size=10, color=MUTED)
            detail = entry.detail
            if entry.error:
                detail += (" · Choose Backup or another slot." if self.mode == "load" and entry.backup_available else
                           " · Choose another slot.")
            elif entry.backup_error:
                detail += " · Previous version is damaged."
            self.paragraph(detail, x + 28, top + 24, width=500, size=10, color=RED if entry.error else MUTED)
        hint = ("Choose 1–3 to save and return to the title. Esc keeps your current game open." if self.return_to_title else
                "Shift + 1–6 opens a slot’s previous version. Tab switches Save / Load. Loading never overwrites a file.")
        if self.root is None:
            hint = "1–6 opens a saved campaign. Shift + 1–6 opens its previous version. Loading never overwrites a file."
        self.paragraph(self.message or hint,
                       x + 28, y + 523, width=764, size=11, color=GOLD if self.message else MUTED)


class ChoiceScene(Screen):
    """A saved decision must be resolved before continuing campaign actions."""

    transparent = True
    controls = {"h": "hero_details", "f5": "save_game", "f9": "load_game", "f6": "browse_saves"}

    def __init__(self, root):
        super().__init__()
        self.root = root

    def refresh(self):
        super().refresh()
        self.x, self.y = self.game.width / 2 - 400, self.game.height / 2 - 235
        for i, option in enumerate(self.root.state.choice.options):
            self.button("Choose this path" if self.root.state.choice.kind == "skill" else "Choose reward",
                        self.x + 28 + i * 382, self.y + 310, 362,
                        lambda option=option: self.choose(option.id), shortcut=str(i + 1), primary=True)
        self.button("Hero & relics", self.x + 28, self.y + 405, 174,
                    self.hero_details, hotkey="H")
        self.button("Saves", self.x + 612, self.y + 405, 160, self.browse_saves, hotkey="F6")
        self.button("Codex", self.x + 216, self.y + 405, 154, self.root.codex, shortcut="C")

    def choose(self, option_id):
        try:
            self.root.state.choose(option_id)
        except RuleError as error:
            self.message = str(error)
            return
        self.message = ""
        self.checkpoint(self.root.state)
        if self.root.state.choice is not None:
            self.refresh()
        else:
            self.root.message = self.message
            self.game.pop()

    def save_game(self):
        self.root.save_game()
        self.message = self.root.message

    def browse_saves(self):
        self.game.push(SaveScene(self.root))

    def hero_details(self):
        self.game.push(HeroScene(self.root))

    def draw(self):
        x, y, choice = self.x, self.y, self.root.state.choice
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 205))
        self.box(x, y, 800, 470)
        self.text("A TURN IN YOUR STORY", x + 28, y + 24, size=10, color=MUTED)
        self.text(choice.title, x + 28, y + 51, size=30, serif=True, color=GOLD)
        self.paragraph(choice.description, x + 28, y + 104, width=744, size=12)
        for i, option in enumerate(choice.options):
            left = x + 28 + i * 382
            self.box(left, y + 157, 362, 197)
            self.paragraph(option.name, left + 18, y + 177, width=326, size=17, color=TEXT)
            self.paragraph(option.description, left + 18, y + 229, width=326, size=12)
        self.paragraph(self.message or "Choose before taking your next campaign action. Your decision is saved automatically.",
                       x + 28, y + 370, width=744, size=10, color=GOLD if self.message else MUTED)


class HeroScene(Screen):
    transparent = True
    pop_on_cancel = True
    controls = {"left": "previous_page", "right": "next_page"}

    def __init__(self, root):
        super().__init__()
        self.root, self.page = root, 0

    @property
    def pages(self):
        return max(1, (len(self.root.state.inventory) + 3) // 4)

    def refresh(self):
        super().refresh()
        self.x, self.y = self.game.width / 2 - 410, self.game.height / 2 - 326
        x, y, s = self.x, self.y, self.root.state
        for i, relic in enumerate(s.inventory[self.page * 4:self.page * 4 + 4]):
            equipped = s.hero.relic == relic
            self.button("Equipped" if equipped else "Equip", x + 637, y + 260 + i * 75, 152,
                        lambda relic=relic: self.equip(relic), shortcut=str(i + 1), enabled=not equipped)
        self.button("Unequip", x + 637, y + 208, 152, self.unequip, shortcut="U", enabled=s.hero.relic is not None)
        self.button("Previous", x + 28, y + 589, 138, self.previous_page, enabled=self.page > 0)
        self.button("Next", x + 177, y + 589, 110, self.next_page, enabled=self.page + 1 < self.pages)
        self.button("Close", x + 650, y + 589, 140, self.game.pop, hotkey="Esc")
        self.button("Codex", x + 449, y + 589, 170, self.root.codex, shortcut="C")

    def previous_page(self):
        self.page = max(0, self.page - 1)
        self.refresh()

    def next_page(self):
        self.page = min(self.pages - 1, self.page + 1)
        self.refresh()

    def equip(self, relic):
        if self.root.state.hero.relic == relic:
            return
        if self.command(lambda: self.root.state.equip(relic)):
            self.checkpoint(self.root.state)

    def unequip(self):
        self.equip(None)

    def draw(self):
        x, y, s = self.x, self.y, self.root.state
        hero = s.hero
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 205))
        self.box(x, y, 820, 652)
        self.text(hero.name, x + 28, y + 24, size=29, color=GOLD, serif=True)
        self.text(f"Level {hero.level} {hero.hero_class}   ·   {hero.hp}/{hero.max_hp} health   ·   {hero.mana}/{hero.max_mana} mana",
                  x + 28, y + 68, size=12, color=MUTED)
        self.rule(x + 28, y + 103, 764)
        self.text("LEARNED DISCIPLINES", x + 28, y + 119, size=10, color=GOLD)
        if not hero.skill_ranks:
            self.paragraph("Win battles to gain experience. Each level lets you deepen a discipline or try the other path.",
                           x + 28, y + 148, width=744, size=12)
        for i, (skill, rank) in enumerate(hero.skill_ranks.items()):
            left = x + 28 + i * 382
            self.text(f"{SKILLS[skill].name} {rank}", left, y + 141, size=14)
            self.paragraph(SKILLS[skill].description, left, y + 166, width=360, size=10)
        self.rule(x + 28, y + 206, 764)
        self.text(f"RELICS   /   {len(s.inventory)} OWNED   /   ONE EQUIPPED AT A TIME", x + 28, y + 223, size=10, color=GOLD)
        if not s.inventory:
            self.paragraph("Explore sites and choose to keep their treasures. Equipment can change the spells, movement and economy available to your hero.",
                           x + 28, y + 274, width=580, size=13)
        for i, relic in enumerate(s.inventory[self.page * 4:self.page * 4 + 4]):
            top = y + 260 + i * 75
            self.text(RELICS[relic].name, x + 28, top, size=15, color=TEAL if hero.relic == relic else TEXT)
            self.paragraph(RELICS[relic].description, x + 28, top + 25, width=586, size=11)
        self.paragraph(self.message or "Find relics in adventure sites. Change equipment between battles.",
                       x + 28, y + 557, width=744, size=10, color=GOLD if self.message else MUTED)
        self.text(f"{self.page + 1} / {self.pages}", x + 332, y + 602, size=12, color=MUTED)


class ResultScene(Screen):
    """Results are true overlays, so their panels cover all underlying text."""

    transparent = True
    controls = {("e", "return", "space"): "continue_game", "f5": "save_game", "f9": "load_game", "f6": "browse_saves"}

    def __init__(self, root, *, battle=False):
        super().__init__()
        self.root, self.is_battle = root, battle

    def refresh(self):
        super().refresh()
        self.x, self.y = self.game.width / 2 - 270, self.game.height / 2 - 135
        self.button("Return to shard" if self.is_battle else "New shard", self.x + 28, self.y + 196,
                    484, self.continue_game, hotkey="E", primary=True)

    def continue_game(self):
        if self.is_battle:
            self.root.state.resolve_battle()
            if not self.checkpoint(self.root.state):
                self.root.message = self.message
            game = self.game
            game.pop()  # result overlay
            game.pop()  # tactical battlefield; reveal the existing campaign
        else:
            self.game.clear_and_push(TitleScene(self.root.state.seed + 1))

    def save_game(self):
        self.root.save_game()
        self.message = self.root.message

    def browse_saves(self):
        self.game.push(SaveScene(self.root))

    def draw(self):
        x, y, s = self.x, self.y, self.root.state
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 175))
        self.box(x, y, 540, 270)
        if self.is_battle:
            b = s.battle
            title = "Victory" if b.outcome == "player" else "The army is broken"
            standing = sum(u.hp > 0 for u in b.units if u.team == "player")
            lost = sum(u.hp == 0 for u in b.units if u.team == "player" and u.id != 0)
            detail = f"{standing} standing  ·  {lost} troops lost  ·  {b.round} battle rounds"
            subtitle = "Survivors carry their wounds and experience home."
        else:
            title = "The shard is yours" if s.status == "victory" else "Westwatch has fallen"
            detail = f"Turn {s.turn}  ·  Hero level {s.hero.level}"
            subtitle = "Begin another world with a different hero."
        self.text("CHRONICLE OF THE VERDANT REACH", x + 270, y + 23, size=10, color=MUTED, center=True)
        self.text(title, x + 270, y + 59, size=34, serif=True, color=GOLD, center=True)
        self.text(detail, x + 270, y + 117, size=13, center=True)
        self.text(self.message or subtitle, x + 270, y + 157, size=12, color=MUTED, center=True)
