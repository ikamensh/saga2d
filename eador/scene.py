"""The game's presentation: shard, stronghold and a separate tactical scene.

Scenes translate input into model commands. Saga2D owns the UI tree,
scene lifetimes, hotkeys, geometry, drawing and save files.
"""

from __future__ import annotations

import textwrap
from collections import Counter

from saga2d import Anchor, Button, HexGrid, InputEvent, Scene

from eador import art
from eador.battle import SPELLS
from eador.model import BUILDINGS, HERO_CLASSES, RECRUITABLE, UNITS, RuleError, State
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

    def button(self, text, x, y, width, callback, *, hotkey=None, primary=False, danger=False, enabled=True):
        button = Button(text, on_click=callback, hotkey=hotkey, width=width, height=40,
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
    controls = {("return", "space"): "start", "tab": "next_class", "f9": "load_game"}

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
        self.button("Load shard", w / 2 - 170, h - 72, 164, self.load_game, hotkey="F9")
        self.button("New seed", w / 2 + 6, h - 72, 164, self.next_seed)

    def choose(self, name):
        self.hero_class = name
        self.refresh()

    def next_class(self):
        names = list(HERO_CLASSES)
        self.choose(names[(names.index(self.hero_class) + 1) % len(names)])

    def next_seed(self):
        self.seed += 1

    def start(self):
        self.game.replace(ShardScene(State.new(self.seed, self.hero_class)))

    def load_game(self):
        data = self.game.save_manager.load(1)
        if data is None:
            self.message = "No saved shard yet. Start a game and press F5 to save."
        else:
            self.game.replace(ShardScene(State.from_json(data["state"]["campaign"])))

    def draw(self):
        w, h = self.game.resolution
        art.backdrop(self, w, h)
        self.text("E A D O R   /   A  S A G A 2 D  G A M E", w / 2, 56, size=11, color=GOLD, center=True)
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
                "f5": "save_game", "f9": "load_game", ("f1", "escape"): "help"}

    def __init__(self, state):
        super().__init__()
        self.state = state
        self.selected = state.hero.pos
        self.hover = None
        self._resume_battle = state.battle is not None

    @property
    def edge(self):
        return self.game.width - 344

    def on_enter(self):
        super().on_enter()
        if self._resume_battle:
            self._resume_battle = False
            self.game.push(BattleScene(self))
        elif self.state.status != "playing":
            self.game.push(ResultScene(self))

    def on_reveal(self):
        self.selected = self.state.hero.pos
        self.refresh()
        if self.state.status != "playing":
            self.game.push(ResultScene(self))

    def refresh(self):
        super().refresh()
        w, h = self.game.resolution
        self.grid = HexGrid(self.state.provinces, size=min((h - 246) / 8, (self.edge - 130) / 8.67),
                            origin=(self.edge / 2, (h - 30) / 2))
        x = self.edge + 22
        province = self.state.provinces[self.selected]
        playing = self.state.status == "playing"
        here = self.selected == self.state.hero.pos
        adjacent = self.selected in self.grid.neighbors(self.state.hero.pos)
        can_act = playing and self.state.actions_left > 0
        self.button("Hero is here" if here else "Travel here" if province.owner == "player" else "Invade province",
                    x, 423, 300, self.travel, hotkey="Enter", primary=True, enabled=can_act and adjacent)
        current = self.state.provinces[self.state.hero.pos]
        self.button("Explore current province", x, 473, 300, self.explore, hotkey="X",
                    enabled=can_act and current.owner == "player" and current.site is not None and not current.explored)
        self.button("Build stronghold", x, 555, 300, self.buildings, hotkey="B", enabled=playing)
        self.button("Recruit troops", x, 605, 300, self.recruitment, hotkey="R", enabled=playing)
        self.button("End turn", x, h - 93, 300, self.end_turn, hotkey="E", primary=True, enabled=playing)
        self.button("Guide", 26, 30, 94, self.help, hotkey="F1")
        self.button("Save", self.edge - 177, 30, 72, self.save_game)
        self.button("Load", self.edge - 97, 30, 72, self.load_game)

    def get_save_state(self):
        return {"campaign": self.state.to_json()}

    def save_game(self):
        self.game.save(1, scene=self)
        self.message = "Shard saved. F9 restores the campaign, including an unfinished battle."

    def load_game(self):
        data = self.game.save_manager.load(1)
        if data is None:
            self.message = "No saved shard yet. Press F5 to save."
        else:
            self.game.clear_and_push(ShardScene(State.from_json(data["state"]["campaign"])))

    def act(self, callback):
        if self.command(callback):
            if self.state.battle is not None:
                self.game.push(BattleScene(self))
            elif self.state.status != "playing":
                self.game.push(ResultScene(self))

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
        s, h, x = self.state, self.game.height, self.edge + 22
        art.backdrop(self, self.edge, h)
        self.draw_rect(self.edge, 0, 344, h, PANEL)
        self.draw_line(self.edge, 0, self.edge, h, LINE)
        self.draw_rect(0, 0, self.edge, 91, INK)
        self.rule(24, 90, self.edge - 48)
        self.text("SHARDBOUND", self.edge / 2, 24, size=27, serif=True, center=True)
        self.text(f"THE VERDANT REACH   /   SHARD {s.seed}", self.edge / 2, 61, size=10, color=GOLD, center=True)
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
        if p.owner != "player":
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
        self.text(f"TURN {s.turn}  ·  Rival expands every few turns", x, h - 37, size=10, color=MUTED)
        # Back-to-front relief keeps the southern edge of the shard continuous.
        for pos in sorted(s.provinces, key=lambda c: self.grid.center(c)[1]):
            art.province(self, self.grid, pos, s.provinces[pos], selected=pos == self.selected,
                         hero=pos == s.hero.pos, hover=pos == self.hover)
        art.compass(self, 75, 162)
        self.text("Capture Duskspire", self.edge - 185, 122, size=13, color=GOLD, serif=True)
        self.text("Protect Westwatch", self.edge - 185, 146, size=11, color=MUTED)
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
            affordable = s.gold >= spec.cost and (self.kind != "build" or s.crystals >= spec.crystals)
            available = self.kind == "build" or (len(s.hero.army) < s.hero.max_army
                                                  and s.provinces[s.hero.pos].owner == "player")
            self.button("Built" if built else "Locked" if locked else f"{spec.cost} gold", self.x + 548,
                        self.y + 123 + i * 77, 143, lambda name=name: self.purchase(name), hotkey=str(i + 1),
                        enabled=not built and not locked and affordable and available)
            self.bind_key(str(i + 1), lambda name=name: self.purchase(name))
        self.button("Back to shard", self.x + 22, self.y + 535, 676, self.game.pop, hotkey="Esc")

    def purchase(self, name):
        callback = self.root.state.build if self.kind == "build" else self.root.state.recruit
        if self.command(lambda: callback(name)):
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
        self.button("Return to game", self.x + 26, self.y + 481, 306, self.game.pop, hotkey="Esc", primary=True)
        self.button("Save & title", self.x + 346, self.y + 481, 308, self.title)

    def title(self):
        self.root.save_game()
        self.game.clear_and_push(TitleScene(self.root.state.seed))

    def draw(self):
        x, y = self.x, self.y
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 210))
        self.box(x, y, 680, 560)
        self.text("A FIELD GUIDE", x + 28, y + 26, size=11, color=GOLD)
        self.text("Claim a broken world", x + 28, y + 54, size=32, serif=True)
        sections = [
            ("01   Establish your foothold", "Build a barracks or marketplace. Recruit in your territory. Troops cost upkeep; provinces provide income."),
            ("02   March and explore", "Select a neighboring province, then Invade. Travel and exploration spend hero actions. Explore owned provinces for treasure and experience."),
            ("03   Command the battle", "Select a friendly unit. Blue hexes show movement; red rings mark targets. Move, then attack. Forest and hills provide cover."),
            ("04   Keep your veterans alive", "End battle rounds with E. Spells use mana and a hero action. End campaign turns to recover. The rival advances toward Westwatch."),
        ]
        for i, (title, body) in enumerate(sections):
            yy = y + 119 + i * 84
            self.text(title, x + 28, yy, size=17, serif=True, color=TEAL)
            self.paragraph(body, x + 28, yy + 28, width=624, size=12)
        self.text("F5 save  /  F9 load  /  Tab cycle selection  /  Capture Duskspire to win", x + 28, y + 459, size=11, color=GOLD)


class BattleScene(Screen):
    controls = {"e": "end_turn", "tab": "next_unit", "1": "bolt", "2": "heal",
                "a": "auto_round", "f5": "save_game", "f9": "load_game", "escape": "cancel", "f1": "help"}

    def __init__(self, root):
        super().__init__()
        self.root = root
        self.selected = None
        self.spell = None
        self.hover = None
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
        self.button(f"Arcane Bolt · {SPELLS['bolt'].cost} mana", x, 378, 300, self.bolt, hotkey="1",
                    enabled="bolt" in b.spells and b.mana >= SPELLS["bolt"].cost and hero_ready)
        self.button(f"Healing light · {SPELLS['heal'].cost} mana", x, 428, 300, self.heal, hotkey="2",
                    enabled="heal" in b.spells and b.mana >= SPELLS["heal"].cost and hero_ready)
        self.button("Auto-play one round", x, 518, 300, self.auto_round, hotkey="A", enabled=b.outcome is None)
        self.button("Retreat", x, 568, 300, self.retreat, danger=True, enabled=b.outcome is None)
        self.button("Return to shard" if b.outcome else "End battle round", x, h - 93, 300,
                    self.finish if b.outcome else self.end_turn, hotkey="E", primary=True)
        self.button("Guide", 26, 29, 94, self.help, hotkey="F1")
        self.button("Save", self.edge - 105, 29, 79, self.save_game)

    def act(self, callback):
        before = {u.id: u.hp for u in self.battle.units}
        if self.command(callback):
            for u in self.battle.units:
                change = u.hp - before[u.id]
                if change:
                    self.floats.append((self.clock, u.pos, change))
            self.spell = None
            if self.battle.outcome:
                self.game.push(ResultScene(self.root, battle=True))

    def end_turn(self):
        if self.battle.outcome:
            self.finish()
        else:
            self.act(self.battle.end_turn)

    def auto_round(self):
        self.act(self.battle.auto_turn)

    def finish(self):
        if self.battle.outcome is not None:
            self.root.state.resolve_battle()
            self.game.pop()

    def retreat(self):
        try:
            self.root.state.retreat()
        except RuleError as error:
            self.message = str(error)
        else:
            self.game.pop()

    def save_game(self):
        self.root.save_game()
        self.message = self.root.message

    def load_game(self):
        self.root.load_game()

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
            self.spell = None

    def update(self, dt):
        self.clock += dt
        self.floats = [f for f in self.floats if self.clock - f[0] < 1.6]

    def handle_input(self, event):
        if event.type == "move":
            self.hover = self.grid.cell_at(event.x, event.y)
        if event.type != "click" or event.button != "left" or self.battle.outcome:
            return False
        pos = self.grid.cell_at(event.x, event.y)
        if pos is None:
            return False
        unit = next((u for u in self.battle.units if u.hp > 0 and u.pos == pos), None)
        if self.spell and unit:
            self.act(lambda: self.battle.cast(self.spell, unit.id))
        elif unit and unit.team == "player":
            self.selected = unit.id
        elif unit and self.selected is not None:
            self.act(lambda: self.battle.attack(self.selected, unit.id))
        elif self.selected is not None:
            self.act(lambda: self.battle.move(self.selected, pos))
        return True

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
        self.text("Click unit → move → attack  /  Tab next unit", x, h - 37, size=10, color=MUTED)
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


class ResultScene(Screen):
    """Results are true overlays, so their panels cover all underlying text."""

    transparent = True
    controls = {("e", "return", "space"): "continue_game", "f5": "save_game", "f9": "load_game"}

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
            game = self.game
            game.pop()  # result overlay
            game.pop()  # tactical battlefield; reveal the existing campaign
        else:
            self.game.clear_and_push(TitleScene(self.root.state.seed + 1))

    def save_game(self):
        self.root.save_game()
        self.message = "Saved. F9 restores this result."

    def load_game(self):
        self.root.load_game()

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
