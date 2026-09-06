"""The game's presentation: shard, stronghold and a separate tactical scene.

Scenes translate input into model commands. Saga2D owns the UI tree,
scene lifetimes, hotkeys, geometry, drawing and save files.
"""

from __future__ import annotations

from collections import Counter

from saga2d import Anchor, Button, HexGrid, InputEvent, SaveError, Scene

from eador import art
from eador.content import RELICS, SITES, SKILLS
from eador.difficulty import DIFFICULTIES
from eador.model import BUILDINGS, HERO_CLASSES, RECRUITABLE, UNITS, RuleError, State
from eador.persistence import MANUAL_SLOTS, CampaignSaves
from eador.style import BLUE, DANGER, GOLD, INK, LINE, MUTED, PANEL, PRIMARY, RED, TEAL, TEXT, build_theme
from eador.worldgen import THEMES
from eador.sound import set_music
from eador.preferences import reduced_motion


class OrderPending(RuleError):
    """The network accepted an order for asynchronous host resolution."""


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
        if getattr(getattr(self, "root", self), "live_match", False):
            return True
        try:
            self.saves.checkpoint(state)
        except SaveError as error:
            self.message = f"Autosave failed: {error}"
            return False
        return True

    def load_game(self, slot=1, *, backup=False):
        if getattr(getattr(self, "root", self), "live_match", False):
            self.message = "Leave co-op before loading an offline save."
            return False
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

    def command(self, callback, *, cue="confirm"):
        try:
            callback()
        except OrderPending as pending:
            self.message = str(pending)
            return False
        except RuleError as error:
            self.message = str(error)
            self.game.audio.play_sound("refuse")
            return False
        self.message = ""
        if cue:
            self.game.audio.play_sound(cue)
        self.refresh()
        return True

    def open_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene())

    def about(self):
        from eador.diagnostics import DiagnosticScene
        from eador.release import about_text
        self.game.push(DiagnosticScene(about_text(self.game), title='About Shardbound', body_color=TEXT))


class TitleScene(Screen):
    controls = {("return", "space"): "start", "tab": "next_class", "f9": "load_game", "f6": "browse_saves",
                "left": "previous_theme", "right": "next_theme"}

    def __init__(self, seed=7, *, theme="frontier", hero_class="Commander", difficulty="standard"):
        super().__init__()
        self.seed = seed
        self.hero_class = hero_class
        self.world_theme = theme
        self.difficulty = difficulty
        self.notice = ''
        self.notice_page = 0
        self.notice_pages = ('',)

    def on_enter(self):
        from eador.preferences import load_preferences
        self.preferences = load_preferences(self.game)
        set_music(self.game, "campaign")
        super().on_enter()

    def on_reveal(self):
        from eador.preferences import load_preferences
        self.preferences = load_preferences(self.game)
        self.refresh()

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus='codex_text_scale'))

    def previous_notice(self):
        self.notice_page = max(0, self.notice_page - 1)
        self.refresh()

    def next_notice(self):
        self.notice_page = min(len(self.notice_pages) - 1, self.notice_page + 1)
        self.refresh()

    def refresh(self):
        from saga2d import Column, Label, Row
        from eador.preferences import reading_scale
        from eador.reading import reading_text_pages

        super().refresh()
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100
        w, h = self.game.resolution
        x, width = w / 2 - 100, w / 2 + 40

        def label(text, size=13, *, width=width, color=MUTED):
            return Label(text, width=width, wrap=True, font='Verdana',
                         font_size=round(size * scale), text_color=color)

        heroes = Row(*(Button(name, width=(width - 36) / 4, height=40,
                              on_click=lambda name=name: self.choose(name),
                              style=PRIMARY if name == self.hero_class else None)
                       for name in HERO_CLASSES), spacing=12)
        themes = Row(*(Button(theme.name, width=(width - 24) / 3, height=40,
                              on_click=lambda ident=ident: self.choose_theme(ident),
                              style=PRIMARY if ident == self.world_theme else None)
                       for ident, theme in THEMES.items()), spacing=12)
        modes = Row(*(Button(rules.title, width=(width - 24) / 3, height=40, shortcut=str(i + 1),
                             on_click=lambda ident=ident: self.choose_difficulty(ident),
                             style=PRIMARY if ident == self.difficulty else None)
                      for i, (ident, rules) in enumerate(DIFFICULTIES.items())), spacing=12)
        body = Column(
            Column(label('CHOOSE YOUR HERO · Tab to cycle', 11, color=GOLD), heroes,
                   label(HERO_CLASSES[self.hero_class].description), spacing=6),
            Column(label('CHOOSE YOUR WORLD · Left / Right to cycle', 11, color=GOLD), themes,
                   label(THEMES[self.world_theme].description), spacing=6),
            Column(label('DIFFICULTY · Fixed for this run', 11, color=GOLD), modes,
                   label(DIFFICULTIES[self.difficulty].description, 12), spacing=6), spacing=14)
        if self.measure(body)[1] > h - 148 - 226:
            raise ValueError('Title choices exceed the available reading space')
        self.ui.add(Column(body, anchor=Anchor.TOP_LEFT, margin=(round(x), 226)))
        message = self.message or ('Settings could not be read. Open Settings (O) to recover them.'
                                  if self.preferences.error else '')
        offset = sum(map(len, self.notice_pages[:self.notice_page])) if message == self.notice else 0
        self.notice = message
        content = self.notice or f'Seed {self.seed} · Linked: three stages from Frontier. Single shard: your selected world.'
        notice = label(content, 11, width=412, color=RED if self.notice else MUTED)
        notice_top = 250 if self.notice else 539
        self.notice_pages = reading_text_pages(content, 334, measure=lambda text: self.measure(label(text, 11, width=412))[1]) if (
            notice_top + self.measure(notice)[1] > h - 148) else (content,)
        self.notice_page, consumed = 0, 0
        for index, page in enumerate(self.notice_pages):
            if consumed <= offset:
                self.notice_page = index
            consumed += len(page)
        notice = label(self.notice_pages[self.notice_page], 11, width=412, color=RED if self.notice else MUTED)
        self.ui.add(Column(notice, anchor=Anchor.TOP_LEFT, margin=(74, notice_top)))
        if len(self.notice_pages) > 1:
            self.button('Previous', 74, 605, 186, self.previous_notice, shortcut='PageUp', enabled=self.notice_page > 0)
            self.button('Next', 280, 605, 186, self.next_notice, shortcut='PageDown',
                        enabled=self.notice_page + 1 < len(self.notice_pages))
        self.button('Linked campaign', w / 2 - 348, h - 124, 336, self.start_campaign, shortcut='L', primary=True)
        self.button('Enter single shard', w / 2 + 12, h - 124, 336, self.start, hotkey='Enter')
        self.button('Load shard', w / 2 - 202, h - 72, 196, self.browse_saves, hotkey='F6')
        self.button('New seed', w / 2 + 6, h - 72, 196, self.next_seed, shortcut='N')
        self.button('Settings', w - 178, 26, 152, self.open_settings, shortcut='O')
        self.button('Text size', 26, 26, 176, self.open_text_settings, shortcut='T')
        self.button('About this build', 26, h - 72, 232, self.about, shortcut='A')
        self.button('Co-op', w - 232, h - 72, 206, self.multiplayer, shortcut='M')

    def load_game(self, slot=1, *, backup=False):
        loaded = super().load_game(slot, backup=backup)
        if not loaded:
            self.refresh()
        return loaded

    def choose(self, name):
        self.hero_class = name
        self.refresh()

    def next_class(self):
        names = list(HERO_CLASSES)
        self.choose(names[(names.index(self.hero_class) + 1) % len(names)])

    def next_seed(self):
        self.seed += 1
        self.refresh()

    def choose_theme(self, theme):
        self.world_theme = theme
        self.refresh()

    def choose_difficulty(self, difficulty):
        self.difficulty = difficulty
        self.refresh()

    def next_theme(self):
        themes = list(THEMES)
        self.choose_theme(themes[(themes.index(self.world_theme) + 1) % len(themes)])

    def previous_theme(self):
        themes = list(THEMES)
        self.choose_theme(themes[(themes.index(self.world_theme) - 1) % len(themes)])

    def start(self):
        state = State.new(self.seed, self.hero_class, theme=self.world_theme, difficulty=self.difficulty)
        self.enter_state(state)

    def multiplayer(self):
        from saga2d import MatchMenu
        from eador.multiplayer import ShardboundMatch, NetworkShardScene
        self.game.push(MatchMenu("Shardbound co-op", "shardbound-v1",
                                lambda: ShardboundMatch(self.seed, self.hero_class, theme=self.world_theme,
                                                       difficulty=self.difficulty, campaign=True), NetworkShardScene))

    def start_campaign(self):
        self.enter_state(State.new_campaign(self.seed, self.hero_class, difficulty=self.difficulty))

    def enter_state(self, state):
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
        if len(self.notice_pages) > 1:
            self.text(f'Error details · Page {self.notice_page + 1}/{len(self.notice_pages)}', 74, 219, size=11, color=RED)
        if not self.notice:
            self.text(THEMES[self.world_theme].name.upper(), w * .245, 244, size=12, color=GOLD, center=True)
            cells = [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1), (-1, 1), (1, -1)]
            grid = HexGrid(cells, size=42, origin=(w * .245, 385))
            from types import SimpleNamespace
            terrains = {"frontier": ("forest", "hills", "plains"), "elderwild": ("forest", "marsh", "forest"),
                        "ruins": ("hills", "plains", "hills")}[self.world_theme]
            for i, pos in enumerate(sorted(cells, key=lambda c: grid.center(c)[1])):
                data = SimpleNamespace(terrain=terrains[i % 3], owner="player" if pos == (0, 0) else "neutral",
                                       capital=pos == (0, 0), site=None, explored=False, name="Westwatch" if pos == (0, 0) else "")
                art.province(self, grid, pos, data)
            self.text("A realm to establish. A rival to overcome.", w * .245, 514, size=11, color=MUTED, center=True)


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
        return self.game.width - 400

    def on_enter(self):
        from eador.preferences import load_preferences
        self.preferences = load_preferences(self.game)
        super().on_enter()
        self.follow_state()

    def on_reveal(self):
        if self.state.hero.pos != self._last_hero_pos:
            self.selected = self.state.hero.pos
        self.refresh()
        self.follow_state()

    def follow_state(self):
        set_music(self.game, "battle" if self.state.battle and not self.state.battle.outcome else
                  None if self.state.battle or self.state.status != "playing" else "campaign")
        if self.state.battle is not None:
            self.game.push(BattleScene(self))
        elif self.state.choice is not None:
            self.game.push(ChoiceScene(self))
        elif self.state.campaign and self.state.campaign.phase != "playing":
            from eador.campaign_scene import CampaignScene
            self.game.push(CampaignScene(self))
        elif self.state.status != "playing":
            self.game.push(ResultScene(self))

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._display != (self.game.window_size, reading_scale(self.game), self.message):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus='codex_text_scale'))

    def read_message(self):
        from eador.diagnostics import DiagnosticScene
        self.game.push(DiagnosticScene(self._notice, return_label='Return to map', title='Complete campaign message'))

    def refresh(self):
        from saga2d import Column, Label
        from eador.preferences import reading_scale
        from eador.rival_scene import rival_order

        super().refresh()
        s = self.state
        self._last_hero_pos = s.hero.pos
        scale = reading_scale(self.game) / 100
        self._display = self.game.window_size, reading_scale(self.game), self.message
        h, x, width = self.game.height, self.edge + 22, 356

        def label(text, width, *, size=12, color=TEXT, serif=False):
            return Label(text, width=width, wrap=True, font='Georgia' if serif else 'Verdana',
                         font_size=round(size * scale), text_color=color)

        def column(items, width, x, y, *, spacing=6):
            block = Column(*items, width=width, spacing=spacing, anchor=Anchor.TOP_LEFT, margin=(x, y))
            height = self.measure(block)[1]
            self.ui.add(block)
            return y + height

        # Treasury and the hero remain visible while province commands are reviewed.
        economy = [label('WESTWATCH ENCIRCLED' if s.encircled else 'YOUR DOMINION', 390,
                         size=10, color=RED if s.encircled else MUTED),
                   label(f'{s.gold} gold  ·  {s.crystals} crystals', 390, size=18, color=GOLD, serif=True),
                   label(f'Income +{s.income}  ·  Upkeep −{s.upkeep} / turn', 390,
                         color=RED if s.upkeep_shortfall else MUTED),
                   label(f'Realm gold yield: {s.rules.gold_percent}% of base production', 390, size=10, color=MUTED)]
        if s.upkeep_shortfall:
            economy.append(label(f'{s.upkeep_shortfall} gold short: unpaid troops will leave.', 390, color=RED))
        elif s.encircled:
            economy.append(label('Capital supply blocked · V for breakout routes', 390, color=RED))
        treasury_bottom = column(economy, 390, 26, 108)
        hero_bottom = column([
            label(f'{s.hero.name}, the {s.hero.hero_class}', 390, size=18, serif=True),
            label(f'Level {s.hero.level} · {s.hero.xp} XP · {s.actions_left} actions left', 390, color=GOLD),
            label(f'Health {s.hero.hp}/{s.hero.max_hp}  ·  Mana {s.hero.mana}/{s.hero.max_mana}', 390),
            label(f'At {s.provinces[s.hero.pos].name}', 390, size=11, color=MUTED),
        ], 390, 452, 108)
        self._summary_bottom = max(treasury_bottom, hero_bottom) + 16

        p = s.provinces[self.selected]
        playing = s.status == 'playing'
        here = self.selected == s.hero.pos
        adjacent = self.selected in s.grid.neighbors(s.hero.pos)
        can_act = playing and s.actions_left > 0
        blocked = self.selected == (2, 0) and s.assault_blocked_reason
        expedition_here = s.rival.army and self.selected == s.rival.pos
        province_income = 0 if s.encircled and p.pos == (-2, 0) else p.income
        details = [label('SELECTED PROVINCE', width, size=10, color=MUTED),
                   label(p.name, width, size=22, serif=True),
                   label(f'{p.terrain.title()} · {p.owner.title()} · {province_income} base gold', width,
                         color=art.OWNERS[p.owner])]
        if expedition_here:
            details.append(label(f'Expedition: {len(s.rival.army)} troops · V for strengths', width, color=RED))
        elif p.owner != 'player':
            guards = ', '.join(f'{n} {UNITS[kind].name}' for kind, n in Counter(p.guards).items())
            details.append(label('Defenders: ' + (guards or 'None'), width, color=RED))
        else:
            details.append(label('Ruins cleared' if p.explored else p.site or 'No ruins in this province',
                                 width, color=GOLD))
        hint = 'Select a neighboring province. Tab cycles neighbors; Home selects your hero.'
        if not s.actions_left:
            hint = 'No actions left. End the turn.'
        elif not here and not adjacent:
            hint = 'Choose a province beside your hero.'
        elif blocked:
            hint = 'Assault locked. J lists objectives.'
        details.append(label(hint, width, size=11, color=MUTED))
        y = column(details, width, x, 108) + 14
        self.button('Hero is here' if here else 'Intercept expedition' if expedition_here else
                    'Travel here' if p.owner == 'player' else 'Invade province',
                    x, y, width, self.travel, hotkey='Enter', primary=True,
                    enabled=can_act and adjacent and not blocked)
        current = s.provinces[s.hero.pos]
        self.button('Explore current province', x, y + 50, width, self.explore, hotkey='X',
                    enabled=can_act and current.owner == 'player' and current.site is not None and not current.explored)
        y = column([label('YOUR STRONGHOLD', width, size=10, color=MUTED),
                    label(f'{len(s.buildings)}/{len(BUILDINGS)} buildings · {len(s.hero.army)}/{s.hero.max_army} troops',
                          width, color=MUTED)], width, x, y + 114) + 12
        self.button('Build stronghold', x, y, width, self.buildings, hotkey='B', enabled=playing)
        self.button('Recruit troops', x, y + 50, width, self.recruitment, hotkey='R', enabled=playing)
        self.button('End turn', x, y + 116, width, self.end_turn, hotkey='E', primary=True, enabled=playing)
        column([label(f'Turn {s.turn} · Rival expedition: {len(s.rival.army)} troops', width,
                      size=11, color=MUTED)], width, x, y + 172)

        self.button('Guide', 614, 28, 92, self.help, hotkey='F1')
        self.button('Hero', 716, 28, 84, self.hero_details, hotkey='H')
        self.button('Codex', 810, 28, 102, self.codex, shortcut='C')
        self.button('Text size', 922, 28, 140, self.open_text_settings, shortcut='F2')
        self.button('Save', 1072, 28, 82, lambda: self.browse_saves('save'))
        self.button('Load', 1164, 28, 90, self.browse_saves)
        column([label(f'{THEMES[s.theme].name.upper()} / SHARD {s.seed} / {s.rules.title.upper()}', 540, size=10, color=GOLD)],
               540, 26, 64)

        # Current objectives sit outside the map; selecting a province does not replace them.
        y = self._summary_bottom + 12
        if s.campaign:
            self.button('Campaign', 644, y, 210, self.campaign_plan, shortcut='J')
            y = column([label(f'Stage {s.campaign.stage} of 3', 210, size=11, color=MUTED)],
                       210, 644, y + 48) + 12
        else:
            y = column([label('Capture Duskspire', 210, size=14, color=GOLD, serif=True),
                        label('Protect Westwatch', 210, size=12, color=MUTED)], 210, 644, y) + 16
        self.button('Rival plan', 644, y, 210, self.rival_details, shortcut='V')
        column([label(rival_order(s), 210, size=11, color=RED)], 210, 644, y + 50)

        army_top = h - 158
        self.grid = HexGrid(s.provinces, size=min(59, (army_top - self._summary_bottom - 24) / 8),
                            origin=(326, (self._summary_bottom + army_top) / 2))
        self._province_name_boxes = []
        for pos, province in s.provinces.items():
            cx, cy = self.grid.center(pos)
            name_width = round(self.grid.size * 1.69)
            name = Label(province.name, width=name_width, wrap=True, align='center',
                         font='Verdana', font_size=9, text_color=TEXT)
            name_height = self.measure(name)[1]
            left, top = round(cx - name_width / 2), round(cy + self.grid.size * .60 - name_height)
            column([name], name_width, left, top)
            self._province_name_boxes.append((left, top - 1, name_width, name_height + 2))
        column([label('YOUR ARMY · Level / health', self.edge - 52, size=10, color=MUTED)],
               self.edge - 52, 26, army_top)
        army_y = army_top + round(22 * scale)
        self._army_art = []
        for i, troop in enumerate(s.hero.army):
            xx = 26 + i * 118
            name_bottom = column([label(UNITS[troop.kind].name, 112, size=11)], 112, xx, army_y)
            status_bottom = column([label(f'Lv {troop.level}\n{troop.hp}/{troop.max_hp}', 70, size=10, color=MUTED)],
                                   70, xx + 42, name_bottom + 4)
            self._army_art.append((xx, name_bottom + 38, status_bottom + 3))
        self._notice = self.message or ('Settings could not be read. Open Text size to recover them.'
                                       if self.preferences.error else s.log[-1])
        notice = label(self._notice, self.edge - 52, size=11, color=GOLD if self.message else MUTED)
        if self.measure(notice)[1] > 26:
            notice = label('Message available. Read the complete message for details.', self.edge - 228,
                           size=11, color=GOLD)
            self.button('Read message', self.edge - 186, h - 49, 160, self.read_message, shortcut='D')
        column([notice], self.measure(notice)[0], 26, h - 29)

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

    def campaign_plan(self):
        from eador.campaign_scene import CampaignPlanScene
        self.game.push(CampaignPlanScene(self))

    def order(self, action, *args, target="state", **kwargs):
        receiver = self.state if target == "state" else self.state.battle
        return getattr(receiver, action)(*args, **kwargs)

    def act(self, callback, *, cue="confirm"):
        before = self.state.status
        if self.command(callback, cue=cue):
            if self.state.status != before and self.state.status != "playing":
                self.game.audio.play_sound("victory" if self.state.status == "victory" else "defeat")
            self.checkpoint(self.state)
            self.follow_state()

    def travel(self):
        if (self.state.actions_left and self.selected in self.state.grid.neighbors(self.state.hero.pos)
                and not (self.selected == (2, 0) and self.state.assault_blocked_reason)
                and self.state.encounter_at(self.selected)):
            from eador.encounter_scene import EncounterScene
            self.game.push(EncounterScene(self, self.selected, kind="conquest"))
        else:
            self.act(lambda: self.order("travel", self.selected), cue="move")

    def explore(self):
        province = self.state.provinces[self.state.hero.pos]
        if (self.state.encounter_at(province.pos, kind="site") and not province.explored
                and province.owner == "player"):
            from eador.encounter_scene import EncounterScene
            self.game.push(EncounterScene(self))
        else:
            self.act(lambda: self.order("explore"))

    def end_turn(self):
        before = {troop.id: troop.kind for troop in self.state.hero.army}
        self.act(lambda: self.order("end_turn"), cue="end_turn")
        surviving = {troop.id for troop in self.state.hero.army}
        deserted = Counter(kind for ident, kind in before.items() if ident not in surviving)
        if deserted:
            names = ", ".join(f"{count} {UNITS[kind].name}" for kind, count in deserted.items())
            self.message = f"Unpaid upkeep: {names} deserted. Reopen supply or capture income before the next bill."

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
        s, h = self.state, self.game.height
        art.backdrop(self, self.edge, h)
        self.draw_rect(self.edge, 91, self.game.width - self.edge, h - 91, PANEL)
        self.draw_line(self.edge, 91, self.edge, h, LINE)
        self.draw_rect(0, 0, self.game.width, 91, INK)
        self.rule(24, 90, self.game.width - 48)
        self.text('SHARDBOUND', 26, 22, size=27, serif=True)
        self.rule(26, self._summary_bottom - 4, self.edge - 52)
        for pos in sorted(s.provinces, key=lambda c: self.grid.center(c)[1]):
            art.province(self, self.grid, pos, s.provinces[pos], selected=pos == self.selected,
                         hero=pos == s.hero.pos, hover=pos == self.hover, name_label=False)
        for box in self._province_name_boxes:
            self.draw_rect(*box, (23, 37, 33, 235), radius=3)
        if s.rival.army:
            art.expedition(self, self.grid, s.rival.pos, len(s.rival.army))
        art.compass(self, 75, self._summary_bottom + 60)
        if s.campaign:
            from eador.campaign_scene import campaign_targets
            for index, (pos, _, complete) in enumerate(campaign_targets(s)):
                cx, cy = self.grid.center(pos)
                cx, cy = cx + self.grid.size * .50, cy + self.grid.size * .05
                self.draw_circle(cx, cy, 10, INK)
                self.text(str(index + 1), cx, cy - 8, size=11, color=TEAL if complete else GOLD, center=True)
        for troop, (xx, piece_y, bar_y) in zip(s.hero.army, self._army_art):
            art.piece(self, xx + 19, piece_y, troop.kind, 'player', scale=.53)
            self.bar(xx + 42, bar_y, 66, troop.hp, troop.max_hp)
        self.rule(26, h - 168, self.edge - 52)


class CatalogScene(Screen):
    """Measured complete purchase rows; number shortcuts belong to the visible page."""

    transparent = True
    pop_on_cancel = True
    controls = {('left', 'pageup'): 'previous_page', ('right', 'pagedown'): 'next_page'}

    def __init__(self, root, kind, *, outgoing_id=None):
        super().__init__()
        self.root, self.kind, self.page = root, kind, 0
        self.outgoing_id = outgoing_id
        self.items = list(BUILDINGS) if kind == 'build' else list(RECRUITABLE)
        self._page_items = [self.items]

    @property
    def visible_items(self):
        """Current purchasable item IDs in displayed order, including disabled rows."""
        return tuple(self._page_items[self.page])

    @property
    def pages(self):
        return len(self._page_items)

    def previous_page(self):
        self.page = max(0, self.page - 1)
        self.refresh()

    def next_page(self):
        self.page = min(self.pages - 1, self.page + 1)
        self.refresh()

    def on_reveal(self):
        self.refresh()

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus='codex_text_scale'))

    def _availability(self, name):
        """Explain current blockers; the model remains authoritative when purchasing."""
        s = self.root.state
        if self.outgoing_id is not None:
            return s.replacement_preview(self.outgoing_id, name).blocked_reason or ''
        if s.status != 'playing':
            return 'This campaign has ended. Start a new shard.'
        if s.battle is not None:
            return 'Finish or retreat from the battle first.'
        if s.choice is not None:
            return 'Resolve the pending choice first.'
        spec = BUILDINGS[name] if self.kind == 'build' else UNITS[name]
        if self.kind == 'build' and name in s.buildings:
            return 'Already built. This building is permanent.'
        reasons = []
        if self.kind == 'recruit':
            if s.provinces[s.hero.pos].owner != 'player':
                reasons.append('Recruit in a province you control.')
            if spec.building and spec.building not in s.buildings:
                reasons.append(f'Requires {BUILDINGS[spec.building].name}.')
            if len(s.hero.army) >= s.hero.max_army:
                reasons.append(f'Army full ({len(s.hero.army)}/{s.hero.max_army}).')
        gold = spec.cost if self.kind == 'build' else s.recruit_cost(name)
        crystals = spec.crystals if self.kind == 'build' else s.recruit_crystal_cost(name)
        missing = []
        if s.gold < gold:
            missing.append(f'{gold - s.gold} gold')
        if s.crystals < crystals:
            missing.append(f'{crystals - s.crystals} crystal' + ('s' if crystals - s.crystals != 1 else ''))
        if missing:
            reasons.append('Need ' + ' and '.join(missing) + ' more.')
        return ' '.join(reasons)

    def _description(self, name):
        spec = BUILDINGS[name] if self.kind == 'build' else UNITS[name]
        if self.kind == 'build':
            return spec.description
        facts = f'{spec.hp} HP · {spec.attack} attack · range {spec.attack_range} · upkeep {spec.upkeep} gold/turn.'
        role = {
            'pikeman': 'G: Brace strikes first against melee.',
            'healer': 'Heal uses its order and shared mana.',
            'ranger': 'Shoot before moving to retain movement.',
            'warden': 'S swaps places with an adjacent ally.',
            'militia': 'Q rallies an adjacent Pinned ally.',
            'sapper': 'D: one Smoke screen per battle.',
            'adept': 'R: one Repulse per battle; Guard anchors.',
            'skyrider': 'Fly over bodies and rough ground; land on empty hexes.',
        }.get(name, '')
        return facts + (' ' + role if role else '')

    def refresh(self):
        from saga2d import Column, Label, Row
        from eador.preferences import reading_scale
        from eador.reading import reading_pages

        anchor = self.items.index(self.visible_items[0])
        super().refresh()
        self.x, self.y = self.game.width / 2 - 520, self.game.height / 2 - 370
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100
        s = self.root.state

        def label(text, size=12, *, width=992, color=MUTED, serif=False):
            return Label(text, width=width, wrap=True, font='Georgia' if serif else 'Verdana',
                         font_size=round(size * scale), text_color=color)

        resources = label(f'{s.gold} gold · {s.crystals} crystals · {len(s.hero.army)}/{s.hero.max_army} troops')
        blocks, reasons, prices = {}, {}, {}
        for name in self.items:
            spec = BUILDINGS[name] if self.kind == 'build' else UNITS[name]
            reason = reasons[name] = self._availability(name)
            built = self.kind == 'build' and name in s.buildings
            cost = spec.cost if self.kind == 'build' else s.recruit_cost(name)
            crystals = spec.crystals if self.kind == 'build' else s.recruit_crystal_cost(name)
            prices[name] = f'{cost} gold' + (f' + {crystals} crystal' + ('s' if crystals != 1 else '') if crystals else '')
            blocks[name] = Column(label(spec.name, 19, width=736, color=TEXT, serif=True),
                                  label(self._description(name), width=736),
                                  label(prices[name] + (' · ' + reason if reason else ''), 11, width=736,
                                        color=MUTED if built else RED if reason else GOLD), spacing=6)
        policy = ('Buildings are permanent; build even while your hero is away.' if self.kind == 'build'
                  else 'Recruit in a province you control.')
        if self.outgoing_id is not None:
            troop = next(t for t in s.hero.army if t.id == self.outgoing_id)
            policy = f'Replacing {UNITS[troop.kind].name} #{troop.id}, rank {troop.level}, {troop.xp} XP. Review the full cost before retiring them.'
        hint = ('Numbers review replacements.' if self.outgoing_id is not None else 'Numbers buy the visible items.') + ' Left/Right changes page. ' + policy
        footer = Column(*([label(self.message, 11, color=GOLD)] if self.message else []), label(hint, 11), spacing=6)
        self.ui.add(Column(resources, *blocks.values(), footer))
        body_y = 99 + resources.get_preferred_size()[1] + 18
        footer_y = 666 - footer.get_preferred_size()[1]
        available = footer_y - 18 - body_y
        heights = {name: max(40, block.get_preferred_size()[1]) for name, block in blocks.items()}

        pages, self.page = reading_pages([heights[name] for name in self.items], available,
                                        anchor=anchor, spacing=18, max_items=9)
        self._page_items = [[self.items[index] for index in page] for page in pages]
        self.ui.clear()
        self.ui.add(Column(resources, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 24), round(self.y + 99))))
        rows = []
        for index, name in enumerate(self.visible_items):
            built = self.kind == 'build' and name in s.buildings
            control = Button('Review' if self.outgoing_id is not None else 'Built' if built else prices[name], on_click=lambda name=name: self.purchase(name),
                             shortcut=str(index + 1), enabled=self.outgoing_id is not None or not reasons[name], width=228, height=40)
            rows.append(Row(blocks[name], control, spacing=28))
        self.ui.add(Column(*rows, spacing=18, anchor=Anchor.TOP_LEFT,
                           margin=(round(self.x + 24), round(self.y + body_y))))
        self.ui.add(Column(footer, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 24), round(self.y + footer_y))))
        self.button('Text size', self.x + 830, self.y + 41, 186, self.open_text_settings, shortcut='T')
        self.button('Previous', self.x + 24, self.y + 684, 150, self.previous_page, hotkey='←', enabled=self.page > 0)
        self.button('Next', self.x + 184, self.y + 684, 150, self.next_page, hotkey='→', enabled=self.page + 1 < self.pages)
        if self.kind == 'recruit':
            self.button('Choose veteran' if self.outgoing_id is not None else 'Replace troop',
                        self.x + 548, self.y + 684, 222, self.replacement, shortcut='M', enabled=bool(s.hero.army))
        self.button('Back to shard', self.x + 794, self.y + 684, 222, self.game.pop, shortcut='Esc')

    def replacement(self):
        from eador.replacement_scene import ReplacementScene
        self.game.replace(ReplacementScene(self.root))

    def purchase(self, name):
        if self.outgoing_id is not None:
            from eador.replacement_scene import ReplacementScene
            self.game.push(ReplacementScene(self.root, outgoing_id=self.outgoing_id, kind=name,
                                            description=self._description(name)))
            return
        if self.command(lambda: self.root.order(self.kind, name)):
            if self.checkpoint(self.root.state):
                self.message = self.root.state.log[-1]
            self.refresh()

    def draw(self):
        x, y = self.x, self.y
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 200))
        self.box(x, y, 1040, 740)
        self.text('WESTWATCH / STRONGHOLD', x + 24, y + 22, size=10, color=GOLD)
        title = 'Choose a fresh recruit' if self.outgoing_id is not None else 'Build your kingdom' if self.kind == 'build' else 'Raise an army'
        self.text(title, x + 24, y + 46, size=31, serif=True)
        self.text(f'Page {self.page + 1}/{self.pages}', x + 400, y + 696, size=12, color=MUTED)


class HelpScene(Screen):
    transparent = True
    pop_on_cancel = True

    def __init__(self, root):
        super().__init__()
        self.root = root

    def on_reveal(self):
        self.refresh()

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._reading_display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def refresh(self):
        from saga2d import Column, Label, Row
        from eador.preferences import reading_scale

        super().refresh()
        self.x, self.y = self.game.width / 2 - 520, self.game.height / 2 - 350
        self._reading_display = self.game.window_size, reading_scale(self.game)
        scale = self._reading_display[1] / 100
        sections = (
            ("01   Establish your foothold", "Build a barracks or marketplace. Recruit in your territory. Troops cost upkeep; provinces provide income."),
            ("02   March and explore", "Select a neighboring province, then Invade. Travel and exploration spend hero actions. Explore owned provinces for treasure and experience."),
            ("03   Command the battle", "Select a unit, move, then attack. A surviving adjacent defender can retaliate once a round. Read Deal / Take; Tab selects units. G Guards; Pikemen Brace. Spells use shared mana and the caster's order."),
            ("04   Grow and counterattack", "Win battles for skills; H equips relics. A Mage Tower unlocks H → I: spend crystals and an action for mana. V shows rival orders; strike while it rebuilds."),
        )
        blocks = [Column(
            Label(title, width=472, wrap=True, font="Georgia", font_size=round(17 * scale), text_color=TEAL),
            Label(body, width=472, wrap=True, font="Verdana", font_size=round(12 * scale), text_color=MUTED),
            spacing=8,
        ) for title, body in sections]
        # Attach before measuring. Equal measured row heights align section tops;
        # Columns then place all prose and the following quick-reference line.
        for block in blocks:
            self.ui.add(block)
        rows = []
        for pair in (blocks[:2], blocks[2:]):
            height = max(block.get_preferred_size()[1] for block in pair)
            rows.append(Row(*(Column(block, height=height) for block in pair), spacing=40))
        objective = "J campaign objectives" if self.root.state.campaign else "Capture Duskspire to win"
        content = Column(*rows, Label("F5 quicksave  /  F9 quickload  /  F6 save slots  /  " + objective,
                                     width=984, wrap=True, font="Verdana", font_size=round(11 * scale), text_color=GOLD),
                         spacing=28, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(self.y + 142)))
        self.ui.add(content)
        if content.get_preferred_size()[1] > 464:
            raise ValueError(f"Field Guide does not fit at {scale:.0%}")
        self.button("Return to game", self.x + 28, self.y + 634, 260, self.game.pop, shortcut="Esc", primary=True)
        self.button("Codex", self.x + 402, self.y + 634, 200, self.root.codex, shortcut="C")
        self.button("Leave co-op" if getattr(self.root, "live_match", False) else "Save & title", self.x + 752, self.y + 634, 260, self.title, shortcut="S")
        self.button("Settings", self.x + 862, self.y + 26, 150, self.open_settings, shortcut="O")
        self.button('About this build', self.x + 602, self.y + 26, 244, self.about, shortcut='A')

    def title(self):
        if getattr(self.root, "live_match", False):
            self.game.clear_and_push(TitleScene())
        else:
            self.game.push(SaveScene(self.root, mode="save", return_to_title=True))

    def draw(self):
        x, y = self.x, self.y
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 210))
        self.box(x, y, 1040, 700)
        self.text("A FIELD GUIDE", x + 28, y + 26, size=11, color=GOLD)
        self.text("Claim a broken world", x + 28, y + 54, size=32, serif=True)
        self.rule(x + 28, y + 118, 984)
        self.rule(x + 28, y + 620, 984)


class BattleScene(Screen):
    accepts_orders = True
    unit_orders = {
        'pin': ('Pin', 'P', 'attack_hit', 'Choose an unpinned enemy in sight within 3 hexes.'),
        'swap': ('Swap ally', 'S', 'move', 'Choose an adjacent ally. Both moves are spent; its unspent action remains.'),
        'smoke': ('Smoke', 'D', 'confirm', 'Choose a hex in sight within 3. Smoke blocks both sides until your next turn.'),
        'rally': ('Rally ally', 'Q', 'confirm', 'Clear an adjacent ally’s Pin. Its spent orders stay spent.'),
        'repulse': ('Repulse', 'R', 'move', 'Push an adjacent enemy into the marked empty hex. Guard and Brace anchor it.'),
    }
    controls = {"e": "end_turn", "tab": "next_unit", "1": "bolt", "2": "heal",
                "a": "auto_round", "f5": "save_game", "f9": "load_game", "f6": "browse_saves",
                "escape": "cancel", "f1": "help", "t": "retreat", "f": "next_target",
                ("return", "space"): "activate_cursor",
                ("left", "right", "up", "down", "pageup", "pagedown"): "aim"}

    def __init__(self, root):
        super().__init__()
        self.root = root
        self.selected = None
        self.targeting = None
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
        from saga2d import Column
        objective = self._objective_content()
        self.objective_bottom = 100 + self.measure(objective)[1] + 24
        self.ui.add(Column(objective, anchor=Anchor.TOP_LEFT, margin=(38, 112)))
        alive = [u for u in b.units if u.team == "player" and u.hp > 0]
        if self.selected is None or not any(u.id == self.selected for u in alive):
            self.selected = alive[0].id if alive else None
        command = self._command_content()
        if self.measure(command)[1] > h - 118:
            raise ValueError('Tactical commands exceed the available reading space')
        self.ui.add(Column(command, anchor=Anchor.TOP_LEFT, margin=(x, 60)))
        footer = self._footer_content()
        self.footer_top = h - 16 - self.measure(footer)[1]
        self.ui.add(Column(footer, anchor=Anchor.TOP_LEFT, margin=(30, round(self.footer_top))))
        # Fit any finite battle board; topology, picking and polygons share one grid.
        geometry = HexGrid(b.terrain)
        centers = [geometry.center(p) for p in b.terrain]
        left, right = min(p[0] for p in centers) - .866, max(p[0] for p in centers) + .866
        top, bottom = min(p[1] for p in centers) - 1, max(p[1] for p in centers) + 1
        board_top, board_bottom = self.objective_bottom + 16, self.footer_top - 36
        size = min((self.edge - 100) / (right - left), (board_bottom - board_top) / (bottom - top))
        origin = (self.edge / 2 - (left + right) / 2 * size,
                  (board_top + board_bottom) / 2 - (top + bottom) / 2 * size)
        self.grid = HexGrid(b.terrain, size=size, origin=origin)
        self._phase_button(x, h - 46)
        self.button("Guide", 26, 29, 94, self.help, hotkey="F1")
        self.button("Codex", 130, 29, 110, self.root.codex, shortcut="C")
        self.button("Save", self.edge - 105, 29, 79, self.save_game)
        self.button('Text size', x + 126, 16, 174, self.open_text_settings, shortcut='F2')
        from eador.preferences import reading_scale
        self._reading_view = self.hover, self.message, self.game.window_size, reading_scale(self.game)

    def _command_content(self):
        from saga2d import Column, Label, Row
        from eador.preferences import reading_scale
        b = self.battle
        selected = b.unit(self.selected) if self.selected is not None else None
        scale = reading_scale(self.game) / 100

        def label(text, *, size=12, color=MUTED, width=300):
            return Label(text, width=width, wrap=True, font='Verdana',
                         font_size=round(size * scale), text_color=color)

        allies = sum(u.hp > 0 and u.team == 'player' for u in b.units)
        enemies = sum(u.hp > 0 and u.team != 'player' for u in b.units)
        sections = [label(f'{allies} allies · {enemies} foes · Tab selects')]
        if selected:
            name = self.root.state.hero.hero_class if selected.id == 0 else UNITS[selected.kind].name
            status = ('Guard +2' if selected.stance == 'guard' else 'Braced' if selected.stance == 'brace' else
                      'Can move' if selected.acted and b.reachable(selected.id) else
                      'Spent' if selected.acted else 'Moved' if selected.moved else 'Ready')
            penalties = ['Pinned'] if selected.pinned else []
            if selected.cargo_penalty:
                penalties.append(f'Cargo −{selected.cargo_penalty}')
            movement = f"{'Fly' if selected.can_fly else 'Move'} {selected.effective_move_range}"
            if penalties:
                movement += f" ({', '.join(penalties)})"
            sections.append(Column(Label(name, width=300, wrap=True, font='Georgia', font_size=25, text_color=TEXT),
                                   Row(label(f'{selected.hp} / {selected.max_hp} HP', color=TEAL, width=180),
                                       label(status, color=GOLD, width=108), spacing=12),
                                   label(f'Attack {selected.attack}   Defense {selected.effective_defense}', color=TEXT),
                                   label(f'{movement}   Range {selected.attack_range}'), spacing=6))
        orders = []
        if self.unit_order:
            name = self.unit_order
            title, key, _, _ = self.unit_orders[name]
            if name == 'pin' and selected.pin_cooldown:
                title += ' · wait'
            elif name in ('smoke', 'repulse'):
                title += ' · 0' if name in selected.spent_abilities else ' · 1'
            orders.append(Button(title, width=172, height=40, shortcut=key,
                                 on_click=lambda: self.choose_order(name),
                                 style=PRIMARY if self.targeting == name else None,
                                 enabled=bool(getattr(b, name + '_targets')(selected.id))))
        orders.append(Button('Brace' if selected and selected.can_brace else 'Guard', width=116, height=40,
                             shortcut='G', on_click=self.guard,
                             enabled=selected is not None and not selected.acted and b.outcome is None))
        sections.append(Row(*orders, spacing=12))
        healer = 'Acolyte' if self.heal_caster != 0 else 'Hero'
        sections.append(Column(label(f'SHARED MANA   /   {b.mana} REMAINING', size=10, color=BLUE),
                               Button(f"Arcane Bolt · {b.spell_cost('bolt')} mana", width=300, height=40,
                                      hotkey='1', on_click=self.bolt, enabled=bool(b.spell_targets('bolt'))),
                               Button(f"{healer} Heal · {b.spell_cost('heal')} mana", width=300, height=40,
                                      hotkey='2', on_click=self.heal,
                                      enabled=bool(b.spell_targets('heal', caster_id=self.heal_caster))),
                               label('Heal spends this Acolyte’s order.' if self.heal_caster != 0 else
                                     'Spells spend the hero’s order.', size=11), spacing=8))
        sections.append(self._forecast())
        return Column(*sections, spacing=18)

    def _footer_content(self):
        from saga2d import Column, Label, Row
        from eador.preferences import reading_scale
        scale, width = reading_scale(self.game) / 100, self.edge - 60

        def label(text, *, width=380, color=MUTED):
            return Label(text, width=width, wrap=True, font='Verdana', font_size=round(11 * scale), text_color=color)

        logs = Column(*(label(line) for line in self.battle.log[-3:]), spacing=4)
        if self.measure(logs)[1] > 100:
            logs = label('Open the battle log to read the latest entries.')
        hint = label(self.message or ('Click a target for ' + self.targeting if self.targeting else self.order_hint()),
                     width=width - 396, color=GOLD)
        overflow = self.measure(hint)[1] > 100
        if overflow:
            hint = label('A complete battle message is available below.', width=width - 396, color=GOLD)
        controls = Row(Button('Auto-play one round', width=270, height=40, shortcut='A', on_click=self.auto_round,
                              enabled=self.battle.outcome is None and self.accepts_orders),
                       Button('Retreat', width=150, height=40, shortcut='T', style=DANGER,
                              on_click=self.retreat, enabled=self.battle.outcome is None and self.accepts_orders),
                       Button('Battle log', width=170, height=40, shortcut='L', on_click=self.read_log), spacing=12)
        if overflow:
            controls.add(Button('Read message', width=242, height=40, shortcut='M', on_click=self.read_message))
        # Reserve the same footer height after every order, so the board cannot
        # move underneath a pointer when recent events or guidance change.
        return Column(Row(logs, hint, spacing=16, height=100), controls, spacing=12)

    def read_log(self):
        from eador.diagnostics import DiagnosticScene
        self.game.push(DiagnosticScene('\n'.join(self.battle.log), title='Battle log',
                                       body_color=MUTED, return_label='Return to battle'))

    def read_message(self):
        from eador.diagnostics import DiagnosticScene
        self.game.push(DiagnosticScene(self.message, title='Complete battle message', return_label='Return to battle'))

    def _objective_content(self):
        from saga2d import Column, Label, Row
        from eador.preferences import reading_scale
        b, width = self.battle, self.edge - 76
        scale = reading_scale(self.game) / 100

        def label(text, *, size=10, color=MUTED, width=width):
            return Label(text, width=width, wrap=True, font='Verdana', font_size=round(size * scale), text_color=color)

        if b.objective.kind == 'hold':
            objective = b.objective
            title = label(f'HOLD THE SEAL · {objective.progress}/{objective.required} turns · By round {objective.deadline}',
                          size=12, color=GOLD, width=width - 174)
            heading = Row(title, Button('Locate seal', width=162, height=40, shortcut='O',
                                        on_click=self.locate_objective), spacing=12)
            detail = 'Keep an ally on the seal after consecutive enemy turns, with no adjacent foe. Losing control resets progress; rout also wins.'
        elif b.objective.kind == 'extract':
            title = label(f'ESCAPE WITH CARGO · By round {b.objective.deadline}', size=12,
                          color=GOLD, width=width - 336)
            heading = Row(title, Button('Locate exit', width=156, height=40, shortcut='O', on_click=self.locate_objective),
                          Button('Evacuate', width=156, height=40, shortcut='V', on_click=self.evacuate,
                                 style=PRIMARY, enabled=b.evacuation_blocked_reason is None and self.accepts_orders), spacing=12)
            detail = 'Hero on an exit, no adjacent foes, unspent hero order; rout also wins.'
        else:
            heading = label('ROUT THE DEFENDERS', size=12, color=GOLD)
            detail = 'Defeat every defender. Keep your hero alive. Exhaustion after 80 rounds.'
        content = Column(heading, label(detail), spacing=8)
        if b.objective.kind == 'extract':
            content.add(label(b.evacuation_blocked_reason or 'Ready: V evacuates your hero and surviving army.',
                              color=GOLD if b.evacuation_blocked_reason else TEAL))
        return content

    def locate_objective(self):
        objective = self.battle.objective
        if objective.kind == 'extract':
            index = (objective.exits.index(self.cursor) + 1) % len(objective.exits) if self.cursor in objective.exits else 0
            self.cursor = self.hover = objective.exits[index]
        else:
            self.cursor = self.hover = objective.target

    def evacuate(self):
        self.act(lambda: self.root.order("evacuate", target="battle"), checkpoint=True, cue='confirm')

    def act(self, callback, *, checkpoint=False, cue="attack_hit"):
        before = {u.id: u.hp for u in self.battle.units}
        if self.command(callback, cue=cue):
            for u in self.battle.units:
                change = u.hp - before[u.id]
                if change:
                    self.floats.append((self.clock, u.pos, change))
            self.targeting = None
            self.refresh()
            if checkpoint or self.battle.outcome:
                self.checkpoint(self.root.state)
            if self.battle.outcome:
                set_music(self.game, None)
                self.game.audio.play_sound("victory" if self.battle.outcome == "player" else "defeat")
                self.game.push(ResultScene(self.root, battle=True))

    def _phase_button(self, x, y):
        self.button("End battle round", x, y, 300, self.end_turn,
                    hotkey="E", primary=True, enabled=self.battle.outcome is None)

    def play_phase(self, command):
        from eador.battle_playback_scene import BattlePlaybackScene
        recorded = []
        if self.command(lambda: recorded.append(self.battle.trace(command)), cue='end_turn'):
            self.targeting = None
            self.checkpoint(self.root.state)
            self.refresh()
            if recorded[0].events:
                self.game.push(BattlePlaybackScene(self, recorded[0]))
            else:
                self.finish_phase()

    def finish_phase(self):
        if self.battle.outcome:
            set_music(self.game, None)
            self.game.audio.play_sound('victory' if self.battle.outcome == 'player' else 'defeat')
            self.game.push(ResultScene(self.root, battle=True))

    def end_turn(self):
        self.play_phase(lambda: self.root.order("end_turn", target="battle"))

    def auto_round(self):
        self.play_phase(lambda: self.root.order("auto_turn", target="battle"))

    def guard(self):
        self.act(lambda: self.root.order("guard", self.selected, target="battle"), cue="guard")

    def retreat(self):
        try:
            self.root.order("retreat")
        except RuleError as error:
            self.message = str(error)
        else:
            self.game.audio.play_sound("defeat")
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
        if self.targeting:
            self.targeting = None
            self.message = ""
            self.refresh()
        else:
            self.help()

    @property
    def unit_order(self):
        if self.selected is None:
            return None
        return next((name for name in self.unit_orders if name in self.battle.unit(self.selected).abilities), None)

    def choose_order(self, name):
        self.targeting = None if self.targeting == name else name
        self.message = self.unit_orders[name][3] + ' F aims; Enter acts; Esc cancels.' if self.targeting else ''
        self.refresh()

    def order_hint(self):
        selected = self.battle.unit(self.selected) if self.selected is not None else None
        name = self.unit_order
        if name:
            label, key, _, hint = self.unit_orders[name]
            if name in selected.spent_abilities:
                return f'{label} charge spent. It returns next battle.'
            if selected.acted:
                return f'{label} needs an unspent unit action. End the round to regain an order.'
            if name == 'pin' and selected.pin_cooldown:
                return 'Pin is cooling down this turn. You may still move, attack or Guard.'
            return f'{key}: {label}. {hint}'
        if selected and selected.can_fly:
            return 'Flight crosses bodies and rough ground; land on empty hexes. Pin slows flight, and Brace still strikes first.'
        return 'Select a unit. Blue hexes are reachable; red rings are attack targets.'

    @property
    def heal_caster(self):
        selected = self.battle.unit(self.selected) if self.selected is not None else None
        return selected.id if selected and selected.can_heal else 0

    def action_targets(self):
        if self.targeting == 'smoke':
            return []  # Smoke targets hexes, including empty ground.
        if self.targeting in self.unit_orders:
            return getattr(self.battle, self.targeting + '_targets')(self.selected)
        if self.targeting in ('bolt', 'heal'):
            return self.battle.spell_targets(self.targeting, caster_id=self.heal_caster if self.targeting == 'heal' else 0)
        return self.battle.targets(self.selected) if self.selected is not None else []

    def choose_spell(self, name):
        caster = self.heal_caster if name == 'heal' else 0
        if caster == 0 and name not in self.battle.spells:
            self.message = "Build a Temple for Heal or a Mage Tower for Arcane Bolt."
            return
        self.targeting = None if self.targeting == name else name
        source = 'the selected Acolyte' if caster != 0 else 'your hero'
        self.message = (("Choose a wounded ally" if name == "heal" else "Choose an enemy") +
                        f" within 4 hexes of {source}. Casting spends that unit's order." if self.targeting else '')
        self.refresh()

    def bolt(self):
        self.choose_spell("bolt")

    def heal(self):
        self.choose_spell("heal")

    def next_unit(self):
        units = [u for u in self.battle.units if u.team == "player" and u.hp > 0
                 and (not u.acted or self.battle.reachable(u.id))]
        if units:
            ids = [u.id for u in units]
            self.selected = ids[(ids.index(self.selected) + 1) % len(ids)] if self.selected in ids else ids[0]
            self.cursor = self.hover = self.battle.unit(self.selected).pos
            self.targeting = None
            self.message = ''
            self.refresh()

    def aim(self, event):
        directions = {"left": (-1, 0), "right": (1, 0), "up": (0, -1), "down": (0, 1),
                      "pageup": (1, -1), "pagedown": (-1, 1)}
        dq, dr = directions[event.key]
        pos = self.cursor[0] + dq, self.cursor[1] + dr
        if pos in self.battle.terrain:
            self.cursor = self.hover = pos

    def next_target(self):
        targets = sorted(self.battle.smoke_targets(self.selected)) if self.targeting == 'smoke' else [
            u.pos for u in self.action_targets()] if self.targeting else [
            u.pos for u in self.battle.units if u.hp > 0 and u.team == 'enemy']
        if targets:
            index = (targets.index(self.cursor) + 1) % len(targets) if self.cursor in targets else 0
            self.cursor = self.hover = targets[index]

    def activate_cursor(self):
        self.hover = self.cursor
        self.act_at(self.cursor)

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._reading_view != (self.hover, self.message, self.game.window_size, reading_scale(self.game)):
            self.refresh()
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
        if self.targeting:
            if self.targeting == 'smoke':
                self.act(lambda: self.root.order("smoke", self.selected, pos, target="battle"), cue='confirm')
            elif unit:
                if self.targeting in self.unit_orders:
                    name = self.targeting
                    self.act(lambda: self.root.order(name, self.selected, unit.id, target="battle"), cue=self.unit_orders[name][2])
                else:
                    self.act(lambda: self.root.order("cast", self.targeting, unit.id,
                             caster_id=self.heal_caster if self.targeting == 'heal' else 0, target="battle"), cue=self.targeting)
            else:
                self.message = "Aim at a unit. F cycles targets; Esc cancels targeting."
        elif unit and unit.team == "player":
            self.selected = unit.id
            self.message = ''
            self.refresh()
        elif unit and self.selected is not None:
            self.act(lambda: self.root.order("attack", self.selected, unit.id, target="battle"))
        elif self.selected is not None:
            self.act(lambda: self.root.order("move", self.selected, pos, target="battle"), cue="move")

    def _forecast(self):
        from saga2d import Column, Label
        from eador.preferences import reading_scale
        b = self.battle
        selected = b.unit(self.selected) if self.selected is not None else None
        scale, labels = reading_scale(self.game) / 100, []

        def line(text, *, size=13, color=MUTED):
            labels.append(Label(text, width=300, wrap=True, font='Verdana',
                                font_size=round(size * scale), text_color=color))

        def casualties(attacker, target, damage, reaction):
            if reaction >= attacker.hp:
                loss = ' Battle lost.' if attacker.id == b.hero_id else ''
                another = any(u.alive and u.team == attacker.team and u.id != attacker.id and not u.acted for u in b.units)
                hint = 'Tab selects another unit.' if another else 'Choose another order.'
                line(f'{attacker.name} falls.{loss} {hint}', size=11, color=RED)
            if damage >= target.hp:
                line(f'{target.name} defeated.', size=11, color=TEAL)

        hovered = next((u for u in b.units if u.hp > 0 and u.pos == self.hover), None)
        if self.targeting == 'smoke':
            legal = self.hover in b.smoke_targets(self.selected)
            line('Smoke screen' if legal else 'Choose a highlighted hex', size=13, color=BLUE)
            line('Blocks both sides’ shots and spells until your next turn. One charge per battle.', size=10, color=MUTED)
        elif hovered:
            line(f"{hovered.name}  ·  {hovered.hp}/{hovered.max_hp} HP", size=13, color=GOLD)
            pin_target = selected and self.targeting == "pin" and hovered in b.pin_targets(selected.id)
            pin_survives = False
            caster = b.unit(self.heal_caster if self.targeting == 'heal' else 0) if self.targeting in ('bolt', 'heal') else selected
            sight_blocked = caster and (self.targeting in ('bolt', 'heal', 'pin') or caster.attack_range > 1) and not b.has_sight(caster.pos, hovered.pos)
            if pin_target:
                damage, retaliation = b.pin_preview(selected.id, hovered.id)
                line(f"Pin {damage}  /  Take {retaliation}", size=12, color=RED)
                casualties(selected, hovered, damage, retaliation)
                pin_survives = damage < hovered.hp
            elif self.targeting in ('bolt', 'heal') and hovered in self.action_targets():
                amount = b.spell_preview(self.targeting, hovered.id, caster_id=self.heal_caster if self.targeting == 'heal' else 0)
                line(f'Restore {amount} HP' if self.targeting == 'heal' else f'Deal {amount} HP damage', size=12, color=TEAL if self.targeting == 'heal' else RED)
            elif self.targeting == 'swap' and hovered in self.action_targets():
                line('Exchange positions', size=12, color=TEAL)
            elif self.targeting == 'rally' and hovered in self.action_targets():
                forecast = b.rally_preview(selected.id, hovered.id)
                line(f'Rally: Move {forecast.move_range} · {len(forecast.reachable)} reachable hexes', size=11, color=TEAL)
            elif self.targeting == 'repulse' and hovered in self.action_targets():
                landing = b.repulse_preview(selected.id, hovered.id)
                line(f'Repulse to {landing} · No damage', size=12, color=BLUE)
            elif selected and not self.targeting and hovered in b.targets(selected.id):
                damage, retaliation = b.preview(selected.id, hovered.id)
                line(f"Deal {damage}  /  Take {retaliation}", size=12, color=RED)
                casualties(selected, hovered, damage, retaliation)
            elif sight_blocked:
                line('Sight blocked', size=12, color=GOLD)
            else:
                line(f"Attack {hovered.attack}  ·  Defense {hovered.effective_defense}  ·  Range {hovered.attack_range}", size=11, color=MUTED)
            detail = ('Ally keeps order; both moves spent.' if self.targeting == 'swap' else
                      'Clears Pin; spent orders stay spent.' if self.targeting == 'rally' else
                      'One charge; target keeps its orders.' if self.targeting == 'repulse' else
                      'Forest and smoke block ranged orders.' if sight_blocked else
                      f'{b.spell_cost(self.targeting)} shared mana · caster spends its order.' if self.targeting in ('bolt', 'heal') else
                      f"Next turn: Move {max(1, hovered.move_range - 2 - hovered.cargo_penalty)} · may still attack." if pin_survives else
                      f"Pinned: Move {hovered.effective_move_range} · may still attack." if hovered.pinned else
                      "Brace strikes first against melee." if hovered.stance == "brace" else
                      'Smoke clears before its team’s next turn.' if hovered.pos in {cloud.pos for cloud in b.smoke_clouds} else
                      f"Terrain: {b.terrain[hovered.pos].title()}" + (" · Guard +2 defense" if hovered.stance == "guard" else ""))
            line(detail, size=11, color=MUTED)
        else:
            sight_hint = ('Forest and smoke block ranged orders.' if b.sight_rules == 'terrain' else
                          'Saved rules allow ranged orders through terrain.')
            line('Arrows aim. F targets. Enter acts. Esc cancels. C: Codex. ' + sight_hint, size=11)
        return Column(*labels, spacing=5)

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus='codex_text_scale'))

    def on_reveal(self):
        # Accepting a result clears the battle before the two queued scenes pop.
        if self.battle is not None:
            self.refresh()

    def _unit_center(self, unit):
        return self.grid.center(unit.pos)

    def _unit_layer(self, unit):
        return 0

    def draw(self):
        b, s, h, x = self.battle, self.root.state, self.game.height, self.edge + 22
        art.backdrop(self, self.edge, h)
        self.draw_rect(self.edge, 0, 344, h, PANEL)
        self.draw_line(self.edge, 0, self.edge, h, LINE)
        header_center = (self.edge + 135) / 2
        self.text("BATTLE FOR " + s.provinces[s.battle_province].name.upper(), header_center, 26,
                  size=25, serif=True, center=True)
        self.text(f"{s.battle_kind.upper()}   /   ROUND {b.round}", header_center, 63, size=10, color=GOLD, center=True)
        self.rule(26, 90, self.edge - 52)
        self.box(26, 100, self.edge - 52, self.objective_bottom - 100)
        self.text("COMMAND", x, 30, size=10, color=GOLD)
        selected = b.unit(self.selected) if self.selected is not None else None
        hovered = next((u for u in b.units if u.hp > 0 and u.pos == self.hover), None)
        reachable = b.reachable(self.selected) if selected and b.outcome is None and not self.targeting and self.accepts_orders else set()
        targets = {u.id for u in self.action_targets()} if b.outcome is None else set()
        rally_reachable = b.rally_preview(selected.id, hovered.id).reachable if (
            self.targeting == 'rally' and hovered and hovered.id in targets) else set()
        repulse_landing = b.repulse_preview(selected.id, hovered.id) if (
            self.targeting == 'repulse' and hovered and hovered.id in targets) else None
        smoke_targets = b.smoke_targets(self.selected) if self.targeting == 'smoke' else set()
        cloudy = {cloud.pos for cloud in b.smoke_clouds}
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
            if pos in rally_reachable:
                self.draw_polygon(points, (104, 207, 162, 53))
                art.outline(self, points, TEAL, 1.5)
            if b.terrain[pos] in ("forest", "hills", "marsh"):
                art.terrain_detail(self, b.terrain[pos], cx, cy + 12, pos[0] * 23 + pos[1], .35)
            if pos in smoke_targets:
                art.outline(self, points, BLUE, 2)
                self.draw_circle(cx, cy, 3, BLUE)
            if pos in cloudy:
                self.draw_polygon(points, (160, 177, 194, 95))
                for dx, dy in ((-12, 4), (8, 5), (0, -9)):
                    self.draw_circle(cx + dx, cy + dy, self.grid.size * .35, (182, 192, 206, 130))
                art.outline(self, points, BLUE, 2)
            if pos == repulse_landing:
                art.outline(self, points, BLUE, 3)
                self.draw_line(*self.grid.center(hovered.pos), cx, cy, BLUE, width=3)
                self.draw_circle(cx, cy, 6, BLUE)
                self.text('LANDS HERE', cx, cy + 14, size=8, color=TEXT, center=True)
            if pos == b.objective.target:
                art.seal(self, self.grid, pos, label=not any(unit.alive and unit.pos == pos for unit in b.units))
            elif b.objective.kind == 'extract' and pos in b.objective.exits:
                art.exit_marker(self, self.grid, pos, b.objective.exits.index(pos) + 1,
                                label=not any(unit.alive and unit.pos == pos for unit in b.units))
            if pos == self.hover:
                art.outline(self, points, GOLD, 2)
            if selected and pos == selected.pos:
                # Corner ticks keep selection distinct from the pointer's full outline.
                corners = [(cx + (px - cx) * .84, cy + (py - cy) * .84) for px, py in points]
                for index, (px, py) in enumerate(corners):
                    for neighbor in (corners[index - 1], corners[(index + 1) % 6]):
                        self.draw_line(px, py, px + (neighbor[0] - px) * .25,
                                       py + (neighbor[1] - py) * .25, GOLD, 2)
        for u in sorted((u for u in b.units if u.hp > 0), key=lambda u: self.grid.center(u.pos)[1]):
            cx, cy = self._unit_center(u)
            size = self.grid.size
            if u.id in targets:
                self.draw_circle(cx, cy + 7, 25, TEAL if self.targeting in ('heal', 'swap', 'rally') else RED)
            layer = self._unit_layer(u)
            with self.screen_layer(layer):
                art.piece(self, cx, cy + size * .22, s.hero.hero_class if u.id == 0 else u.kind, u.team, scale=min(1, size / 56),
                          selected=u.id == self.selected, spent=u.acted)
            with self.screen_layer(layer + 1):
                if u.stance:
                    self.draw_circle(cx + size * .62, cy + 4, 7, INK)
                    self.text("B" if u.stance == "brace" else "G", cx + size * .62, cy - 2, size=9, color=GOLD, center=True)
                if u.pinned:
                    self.draw_circle(cx - size * .62, cy + 4, 7, INK)
                    self.text("P", cx - size * .62, cy - 2, size=9, color=BLUE, center=True)
                if u.pos in cloudy:
                    self.draw_circle(cx, cy + 7, 10, INK)
                    for dx, dy in ((-3, 7), (3, 7), (0, 3)):
                        self.draw_circle(cx + dx, cy + dy, 4, BLUE)
                # Keep persistent health on the base, inside this unit's hex.
                # The selected/hovered panel retains exact current/maximum HP.
                width, height, top = min(32, size * .82), min(18, size * .48), cy + size * .23
                self.draw_rect(cx - width / 2, top, width, height, INK, radius=3)
                self.text(u.hp, cx, top, size=min(10, size * .27), center=True)
                self.bar(cx - width / 2 + 3, top + height - 4, width - 6, u.hp, u.max_hp,
                         TEAL if u.team == "player" else RED)
        with self.screen_layer(2):
            for started, pos, change in self.floats:
                cx, cy = self.grid.center(pos)
                drift = 0 if reduced_motion(self.game) else (self.clock - started) * 20
                yy = cy - 48 - drift
                self.draw_rect(cx - 31, yy - 2, 62, 35, INK, radius=4)
                self.text(f"{change:+}", cx, yy, size=23,
                          color=TEAL if change > 0 else RED, center=True)
        self.rule(26, self.footer_top - 12, self.edge - 52)


class SaveScene(Screen):
    """File errors stay visible without replacing the campaign being played."""

    transparent = True
    pop_on_cancel = True
    controls = {('left', 'pageup'): 'previous_page', ('right', 'pagedown'): 'next_page'}

    def __init__(self, root=None, *, mode="load", return_to_title=False):
        super().__init__()
        self.root, self.mode = root, mode
        self.return_to_title = return_to_title
        self.page = 0
        self.entries = []
        self._shown_diagnostic = None
        self._next_anchor = None
        self._page_indices = [()]

    @property
    def visible_entries(self):
        """Complete slots on the current page; their original 1–6 shortcuts stay stable."""
        return tuple(self.entries[index] for index in self._page_indices[self.page])

    @property
    def pages(self):
        return len(self._page_indices)

    def previous_page(self):
        self.page = max(0, self.page - 1)
        self.refresh()

    def next_page(self):
        self.page = min(self.pages - 1, self.page + 1)
        self.refresh()

    def on_reveal(self):
        self.refresh()

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus='codex_text_scale'))

    def read_error(self):
        from eador.diagnostics import DiagnosticScene
        self._shown_diagnostic = self.message
        self.game.push(DiagnosticScene(self.message, return_label="Return to saves"))

    def refresh(self):
        from saga2d import Column, Label, Row
        from eador.preferences import reading_scale
        from eador.reading import reading_pages

        anchor = self.entries.index(self.visible_entries[0]) if self.visible_entries else 0
        if self._next_anchor is not None:
            anchor, self._next_anchor = self._next_anchor, None
        super().refresh()
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100
        self.x, self.y = self.game.width / 2 - 560, self.game.height / 2 - 380
        self.entries = self.saves.entries()
        x, y = self.x, self.y

        def label(text, size=12, *, width=1064, color=MUTED):
            return Label(text, width=width, wrap=True, font='Verdana',
                         font_size=round(size * scale), text_color=color)

        introduction = label('Choose a manual slot to save, then return to the title.' if self.return_to_title else
                             'Three manual slots. Autosaves rotate after campaign actions and battle rounds.')
        blocks = []
        for entry in self.entries:
            heading = entry.label
            if entry.timestamp:
                heading += ' · ' + entry.timestamp[:19].replace('T', '  ') + ' UTC'
            detail = entry.detail
            if entry.error:
                detail += (' · Choose Backup or another slot.' if self.mode == 'load' and entry.backup_available
                           else ' · Choose another slot.')
            elif entry.backup_error:
                detail += ' · Previous version is damaged.'
            blocks.append(Column(label(heading, 13, width=744, color=GOLD),
                                 label(detail, 12, width=744, color=RED if entry.error else MUTED), spacing=8))
        hint = ('Choose a shown manual slot to save and return to the title. Esc keeps your current game open.' if self.return_to_title else
                'Shown slot numbers select a save. Shift + number opens its previous version. Left/Right changes page. Loading never overwrites a file.')
        footer = label(self.message or hint, 11, color=GOLD if self.message else MUTED)
        body_y = 99 + self.measure(introduction)[1] + 18
        heights = [max(40, self.measure(block)[1]) for block in blocks]
        diagnostic = bool(self.message) and self.measure(footer)[1] + max(heights) + 18 > 670 - body_y
        if diagnostic:
            footer = Row(label('Save/load failed. Read the complete error, then choose another slot or an available backup.',
                               11, width=824, color=GOLD),
                         Button('Read error', width=216, height=40, shortcut='D', on_click=self.read_error), spacing=24)
        elif not self.message:
            self._shown_diagnostic = None
        footer_y = 670 - self.measure(footer)[1]
        self._page_indices, self.page = reading_pages(heights, footer_y - 18 - body_y, anchor=anchor, spacing=20)
        self.ui.clear()
        self.ui.add(Column(introduction, anchor=Anchor.TOP_LEFT, margin=(round(x + 28), round(y + 99))))
        rows = []
        for i in self._page_indices[self.page]:
            entry = self.entries[i]
            can_save = self.mode == "save" and entry.slot in MANUAL_SLOTS
            can_load = self.mode == "load" and entry.exists
            controls = Row(Button('Save' if can_save else 'Load', width=132, height=40,
                                  on_click=lambda i=i: self.activate(i), shortcut=str(i + 1), enabled=can_save or can_load),
                           Button('Backup', width=156, height=40, on_click=lambda i=i: self.recover(i),
                                  shortcut=f'Shift+{i + 1}', enabled=entry.backup_available and self.mode == 'load'), spacing=12)
            rows.append(Row(blocks[i], controls, spacing=20))
        self.ui.add(Column(*rows, spacing=20, anchor=Anchor.TOP_LEFT, margin=(round(x + 28), round(y + body_y))))
        self.ui.add(Column(footer, anchor=Anchor.TOP_LEFT, margin=(round(x + 28), round(y + footer_y))))
        if self.root is not None and not self.return_to_title:
            self.button("Save slots" if self.mode == "load" else "Load slots", x + 28, y + 692, 200, self.toggle, shortcut="Tab")
        self.button('Previous', x + 248, y + 692, 150, self.previous_page, hotkey='←', enabled=self.page > 0)
        self.button('Next', x + 418, y + 692, 150, self.next_page, hotkey='→', enabled=self.page + 1 < self.pages)
        self.button('Text size', x + 886, y + 32, 206, self.open_text_settings, shortcut='T')
        self.button("Close", x + 892, y + 692, 200, self.game.pop, shortcut="Esc")

        if diagnostic and self.message != self._shown_diagnostic and self.game.scene is self:
            self.read_error()

    def load_game(self, slot=1, *, backup=False):
        self._shown_diagnostic = None
        loaded = super().load_game(slot, backup=backup)
        if not loaded:
            self.refresh()
        return loaded

    def toggle(self):
        if self.root is None or self.return_to_title:
            return
        self.mode = "save" if self.mode == "load" else "load"
        self.message = ""
        self.refresh()

    def recover(self, index):
        if self.mode == "load" and self.entries[index].backup_available:
            self._next_anchor = index
            self.load_game(self.entries[index].slot, backup=True)

    def activate(self, index):
        if getattr(self.root, "live_match", False):
            self.message = "Offline saves are separate. Rejoin the live host to resume co-op."
            self.refresh()
            return
        entry = self.entries[index]
        self._shown_diagnostic = None
        self._next_anchor = index
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
                    self.game.clear_and_push(TitleScene(self.root.state.seed, theme=self.root.state.theme,
                                                       hero_class=self.root.state.hero.hero_class,
                                                       difficulty=self.root.state.difficulty))
                    return
            self.refresh()

    def draw(self):
        x, y = self.x, self.y
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 205))
        self.box(x, y, 1120, 760)
        self.text('Save your chronicle' if self.mode == 'save' else 'Return to a chronicle', x + 28, y + 34,
                  size=30, serif=True, color=GOLD)
        self.text(f'Page {self.page + 1}/{self.pages}', x + 592, y + 704, size=12, color=MUTED)


class ChoiceScene(Screen):
    """Both earned options stay complete at the shared reading size."""

    transparent = True
    controls = {"h": "hero_details", "f5": "save_game", "f9": "load_game", "f6": "browse_saves"}

    def __init__(self, root):
        super().__init__()
        self.root = root
        self._applied = None

    def on_reveal(self):
        self.refresh()

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus='codex_text_scale'))

    def refresh(self):
        from saga2d import Column, Component, Label, Row, Style
        from eador.preferences import reading_scale

        super().refresh()
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100
        choice = self._applied[0] if self._applied else self.root.state.choice
        options = (self._applied[1],) if self._applied else choice.options

        def label(text, size, *, width=1064, color=MUTED):
            return Label(text, width=width, wrap=True, font='Verdana',
                         font_size=round(size * scale), text_color=color)

        title = Label('Decision applied' if self._applied else choice.title,
                      width=988 if choice.kind == 'relic' else 1064,
                      wrap=True, font='Georgia', font_size=30, text_color=GOLD)
        self._relic_space = Component(width=64, height=64) if choice.kind == 'relic' else None
        heading = Row(self._relic_space, title, spacing=12) if self._relic_space else title
        introduction = Column(heading, label(self._applied[2] if self._applied else choice.description, 12), spacing=12)
        blocks = [Column(label(option.name, 17, width=484, color=TEXT),
                         label(option.description, 12, width=484), spacing=12)
                  for option in options]
        footer = label(self.message or
                       'Choose before taking your next campaign action. Your decision is saved automatically.',
                       11, color=GOLD if self.message else MUTED)
        # Measure complete option prose together, then give both cards equal space
        # so their numbered actions remain aligned without shortening either option.
        self.ui.add(Column(introduction, *blocks, footer))
        option_height = max(block.get_preferred_size()[1] for block in blocks)
        cards = []
        for index, (option, block) in enumerate(zip(options, blocks)):
            controls = [] if self._applied else [Button(
                'Choose this path' if choice.kind == 'skill' else 'Choose reward',
                on_click=lambda option=option: self.choose(option.id),
                shortcut=str(index + 1), width=484, height=40, style=PRIMARY)]
            cards.append(Column(Column(block, height=option_height), *controls, spacing=24,
                                style=Style(background_color=PANEL, border_color=LINE, border_width=1,
                                            padding=18, radius=5)))
        content = Column(introduction, Row(*cards, spacing=24), footer, spacing=24)
        self.ui.add(content)
        height = content.get_preferred_size()[1]
        self.panel_height = height + 150
        if self.panel_height > self.game.height - 40:
            raise ValueError(f'Choice {choice.title!r} does not fit at {scale:.0%}')
        self.x, self.y = self.game.width / 2 - 560, (self.game.height - self.panel_height) / 2
        self.ui.clear()
        self.ui.add(Column(content, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(self.y + 48))))
        bottom = self.y + self.panel_height - 68
        self.button('Hero & relics', self.x + 28, bottom, 200, self.hero_details, hotkey='H')
        self.button('Codex', self.x + 248, bottom, 170, self.root.codex, shortcut='C')
        self.button('Text size', self.x + 438, bottom, 200, self.open_text_settings, shortcut='T')
        self.button('Saves', self.x + 892, bottom, 200, self.browse_saves, hotkey='F6')
        if self._applied:
            self.button('Return', self.x + 658, bottom, 214, self.game.pop, shortcut=('Enter', 'Esc'))

    def choose(self, option_id):
        choice = self.root.state.choice
        try:
            self.root.order("choose", option_id)
        except OrderPending as pending:
            self.message = str(pending)
            self.refresh()
            return
        except RuleError as error:
            self.message = str(error)
            self.game.audio.play_sound("refuse")
            self.refresh()
            return
        self.message = ""
        self.game.audio.play_sound("level_up" if choice.kind == "skill" else "reward")
        saved = self.checkpoint(self.root.state)
        if self.root.state.choice is not None:
            self.refresh()
        elif not saved:
            self._applied = choice, next(option for option in choice.options if option.id == option_id), self.root.state.log[-1]
            self.refresh()
        else:
            self.root.message = self.message
            self.game.pop()

    def save_game(self):
        self.root.save_game()
        self.message = self.root.message
        self.refresh()

    def load_game(self, slot=1, *, backup=False):
        loaded = super().load_game(slot, backup=backup)
        if not loaded:
            self.refresh()
        return loaded

    def browse_saves(self):
        self.game.push(SaveScene(self.root, mode='save' if self._applied else 'load'))

    def hero_details(self):
        self.game.push(HeroScene(self.root))

    def draw(self):
        x, y = self.x, self.y
        choice = self._applied[0] if self._applied else self.root.state.choice
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 205))
        self.box(x, y, 1120, self.panel_height)
        self.text('A TURN IN YOUR STORY', x + 28, y + 22, size=10, color=MUTED)
        if self._relic_space:
            rx, ry, rw, rh = self._relic_space.bounds
            art.relic(self, rx + rw / 2, ry + rh / 2, choice.context)


class HeroScene(Screen):
    transparent = True
    pop_on_cancel = True
    controls = {"left": "previous_page", "right": "next_page"}

    def __init__(self, root):
        super().__init__()
        self.root, self.page = root, 0
        self._relics, self._page_indices = (), ((),)

    @property
    def pages(self):
        return len(self._page_indices)

    @property
    def visible_relics(self):
        """Whole relics on this page, in the order of their visible shortcuts."""
        return tuple(self._relics[index] for index in self._page_indices[self.page])

    def on_reveal(self):
        self.refresh()

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus="codex_text_scale"))

    def refresh(self):
        from saga2d import Column, Component, Label, Row
        from eador.preferences import reading_scale
        from eador.reading import reading_pages

        first = self.visible_relics[0] if self.visible_relics else None
        super().refresh()
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100
        self.height = 760
        self.x, self.y = (self.game.width - 1120) / 2, (self.game.height - self.height) / 2
        s, hero = self.root.state, self.root.state.hero
        self._relics = tuple(s.inventory)

        def label(text, size=12, *, width=1064, color=MUTED, serif=False, scaled=True):
            return Label(text, width=width, wrap=True, font="Georgia" if serif else "Verdana",
                         font_size=round(size * scale) if scaled else size, text_color=color)

        title = Row(label(hero.name, 32, width=520, color=GOLD, serif=True, scaled=False),
                    label(f"{s.rules.title} realm", width=310, color=GOLD),
                    Button("Text size", width=186, height=40, shortcut="T", on_click=self.open_text_settings), spacing=24)
        stats = label(f"Level {hero.level} {hero.hero_class} · {hero.hp}/{hero.max_hp} health · {hero.mana}/{hero.max_mana} mana", 13)
        recovery = s.recovery_preview()
        rest = label(recovery.blocked_reason or
                     f"Rest before rival acts: hero +{recovery.hero_hp} HP · surviving troops up to {recovery.army_hp} HP each · mana +{recovery.mana}.",
                     11, color=RED if recovery.blocked_reason else MUTED)
        quote = s.infusion_preview()
        infusion = Row(Column(label(f"Tower infusion · +{quote.mana} mana", 14, width=818, color=TEAL),
                              label(f"{quote.crystals} crystals · {quote.actions} hero action · "
                                    f"available: {s.crystals} crystal{'s' if s.crystals != 1 else ''}, {s.actions_left} "
                                    f"hero action{'s' if s.actions_left != 1 else ''}", 11, width=818),
                              label(quote.blocked_reason or "Recover mana now; time and the rival advance only when you end the turn.",
                                    11, width=818, color=RED if quote.blocked_reason else MUTED), spacing=4),
                       Button("Infuse mana", width=222, height=40, shortcut="I", on_click=self.infuse,
                              enabled=quote.blocked_reason is None), spacing=24)
        skill_width = 520 if len(hero.skill_ranks) == 2 else 1064
        skills = [Column(label(f"{SKILLS[skill].name} {rank}", 16, width=skill_width, color=TEXT),
                         label(SKILLS[skill].description, width=skill_width), spacing=6)
                  for skill, rank in hero.skill_ranks.items()]
        if skills:
            for column in skills:
                self.ui.add(column)
            skill_height = max(column.get_preferred_size()[1] for column in skills)
            skill_body = Row(*(Column(column, height=skill_height) for column in skills), spacing=24)
        else:
            skill_body = label("Win battles to gain experience. Each level lets you deepen a discipline or try the other path.")
        learned = Column(label("LEARNED DISCIPLINES", 10, color=GOLD), skill_body, spacing=6)
        inventory_heading = Row(label(f"RELICS · {len(s.inventory)} OWNED · ONE EQUIPPED AT A TIME", 10,
                                      width=836, color=GOLD),
                                Button("Unequip", width=204, height=40, shortcut="U", on_click=self.unequip,
                                       enabled=hero.relic is not None), spacing=24)
        top = Column(Column(title, stats, rest, spacing=6), infusion, learned, inventory_heading, spacing=14)
        hint = self.message or (f"Rank limits: hero {s.hero_level_cap}, troops {s.troop_level_cap}. XP pauses at the limit. "
                               "Change equipment between battles." if s.campaign else
                               "Find relics in adventure sites. Change equipment between battles.")
        previous = Button("Previous", width=150, height=40, on_click=self.previous_page)
        following = Button("Next", width=130, height=40, on_click=self.next_page)
        page_label = label("", width=196)
        footer = Column(label(hint, 10, color=GOLD if self.message else MUTED),
                        Row(previous, following, page_label,
                            Button("Codex", width=220, height=40, shortcut="C", on_click=self.root.codex),
                            Button("Close", width=272, height=40, shortcut="Esc", on_click=self.game.pop), spacing=24), spacing=10)
        blocks = [Column(label(RELICS[relic].name, 17, width=742,
                               color=TEAL if hero.relic == relic else TEXT),
                         label(RELICS[relic].description, width=742), spacing=6) for relic in self._relics]
        for component in (top, footer, Column(*blocks)):
            self.ui.add(component)
        body_top = self.y + 24 + top.get_preferred_size()[1] + 14
        footer_top = self.y + self.height - 24 - footer.get_preferred_size()[1]
        available = footer_top - body_top - 16
        heights = [max(64, block.get_preferred_size()[1]) for block in blocks]
        for relic, height in zip(self._relics, heights):
            if height > available:
                raise ValueError(f"Hero relic does not fit at {scale:.0%}: {RELICS[relic].name}")
        anchor = self._relics.index(first) if first in self._relics else 0
        self._page_indices, self.page = reading_pages(heights, available, anchor=anchor, spacing=16, max_items=9)
        page_label.text = f"Page {self.page + 1}/{self.pages}"
        previous.enabled, following.enabled = self.page > 0, self.page + 1 < self.pages
        self.ui.clear()
        self._icons, rows = [], []
        for shortcut, index in enumerate(self._page_indices[self.page], 1):
            relic = self._relics[index]
            icon = Component(width=64, height=64)
            self._icons.append((icon, relic))
            rows.append(Row(icon, blocks[index], Button("Equipped" if hero.relic == relic else "Equip",
                            width=222, height=40, shortcut=str(shortcut), enabled=hero.relic != relic,
                            on_click=lambda relic=relic: self.equip(relic)), spacing=18, height=heights[index]))
        if not rows:
            rows.append(label("Explore sites and keep their treasures. Equipment changes the spells, movement and economy available to your hero.", 13))
        for component, top_y in ((top, self.y + 24), (Column(*rows, spacing=16), body_top), (footer, footer_top)):
            self.ui.add(Column(component, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(top_y))))

    def previous_page(self):
        self.page = max(0, self.page - 1)
        self.refresh()

    def next_page(self):
        self.page = min(self.pages - 1, self.page + 1)
        self.refresh()

    def equip(self, relic):
        if self.root.state.hero.relic == relic:
            return
        if self.command(lambda: self.root.order("equip", relic)):
            self.checkpoint(self.root.state)
        self.refresh()

    def unequip(self):
        self.equip(None)

    def infuse(self):
        if self.command(lambda: self.root.order("infuse"), cue="heal"):
            if self.checkpoint(self.root.state):
                self.message = self.root.state.log[-1]
        self.refresh()

    def draw(self):
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 205))
        self.box(self.x, self.y, 1120, self.height)
        for component, relic in self._icons:
            x, y, width, height = component.bounds
            art.relic(self, x + width / 2, y + height / 2, relic, scale=.8)


class ResultScene(Screen):
    """Results are true overlays, so their panels cover all underlying text."""

    transparent = True
    controls = {("e", "return", "space"): "continue_game", "f5": "save_game", "f9": "load_game", "f6": "browse_saves"}

    def __init__(self, root, *, battle=False):
        super().__init__()
        self.root, self.is_battle = root, battle

    def on_reveal(self):
        self.refresh()

    def update(self, dt):
        from eador.preferences import reading_scale
        if self._display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus="codex_text_scale"))

    def continue_game(self):
        if self.is_battle:
            try:
                self.root.order("resolve_battle")
            except RuleError as error:
                self.message = str(error)
                return
            if not self.checkpoint(self.root.state):
                self.root.message = self.message
            game = self.game
            game.pop()  # result overlay
            game.pop()  # tactical battlefield; reveal the existing campaign
        else:
            self.game.clear_and_push(TitleScene(self.root.state.seed + 1, theme=self.root.state.theme,
                                               hero_class=self.root.state.hero.hero_class,
                                               difficulty=self.root.state.difficulty))

    def save_game(self):
        self.root.save_game()
        self.message = self.root.message
        self.refresh()

    def load_game(self, slot=1, *, backup=False):
        loaded = super().load_game(slot, backup=backup)
        if not loaded:
            self.refresh()
        return loaded

    def browse_saves(self):
        self.game.push(SaveScene(self.root))

    def refresh(self):
        from saga2d import Column, Label, Row
        from eador.preferences import reading_scale

        super().refresh()
        self._display = self.game.window_size, reading_scale(self.game)
        scale = self._display[1] / 100
        s = self.root.state
        if self.is_battle:
            b = s.battle
            title = ('The cargo is safe' if b.outcome_reason == 'escape' else
                     "The seal is secured" if b.outcome_reason == "hold" else "Time has run out" if b.outcome_reason == "deadline"
                     else "Victory" if b.outcome == "player" else "The army is broken")
            standing = sum(u.hp > 0 for u in b.units if u.team == "player")
            lost = sum(u.hp == 0 for u in b.units if u.team == "player" and u.id != 0)
            detail = (f"{standing} standing · {lost} troop{'s' if lost != 1 else ''} lost · "
                      f"{b.round} battle round{'s' if b.round != 1 else ''}")
            subtitle = ('Your surviving army escapes with the recovered cargo.' if b.outcome_reason == 'escape' else
                        'The cargo was not extracted. The site remains uncleared.' if b.outcome_reason == 'deadline' and b.objective.kind == 'extract' else
                        ("Surviving defenders withdraw. Claim the site's reward." if s.battle_kind == "site" else
                         "The defenders withdraw. Duskspire and its seal are yours.") if b.outcome_reason == "hold" else
                        "The seal was not secured. The defenders retain their ground." if b.outcome_reason == "deadline" else
                        "Survivors carry their wounds and experience home.")
        else:
            title = "The shard is yours" if s.status == "victory" else "Westwatch has fallen"
            detail = f"Turn {s.turn}  ·  Hero level {s.hero.level}"
            subtitle = "Begin another world with a different hero."

        def label(text, size, *, width=744, color=MUTED, serif=False, scaled=True, align="center"):
            return Label(text, width=width, wrap=True, align=align,
                         font="Georgia" if serif else "Verdana", text_color=color,
                         font_size=round(size * scale) if scaled else size)

        content = Column(
            Row(label(f"CHRONICLE OF {THEMES[s.theme].name.upper()}", 10, width=534, align="left"),
                Button("Text size", width=186, height=40, shortcut="T", on_click=self.open_text_settings), spacing=24),
            label(title, 34, color=GOLD, serif=True, scaled=False),
            label(detail, 13, color=TEXT),
            label(self.message or subtitle, 12, color=GOLD if self.message else MUTED),
            Row(Button("Saves", width=220, height=40, hotkey="F6", on_click=self.browse_saves),
                Button("Codex", width=220, height=40, shortcut="C", on_click=self.root.codex),
                Button("Return to shard" if self.is_battle else "New shard", width=256, height=40,
                       hotkey="E", on_click=self.continue_game, style=PRIMARY), spacing=24), spacing=20)
        self.ui.add(content)
        self.height = content.get_preferred_size()[1] + 48
        if self.height > 760:
            raise ValueError(f"Battle result does not fit at {scale:.0%}")
        self.x, self.y = (self.game.width - 800) / 2, (self.game.height - self.height) / 2
        self.ui.clear()
        self.ui.add(Column(content, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(self.y + 24))))

    def draw(self):
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 175))
        self.box(self.x, self.y, 800, self.height)
