"""An authored expedition's objective, defenders and cost before committing."""

from collections import Counter

from saga2d import Anchor, Button, Column, Component, HexGrid, Label, Row
from eador import art
from eador.content import RELICS, SITES
from eador.encounters import ENCOUNTERS
from eador.model import UNITS
from eador.preferences import reading_scale
from eador.scene import Screen
from eador.style import GOLD, INK, MUTED, PRIMARY, RED, TEAL, TEXT


class EncounterScene(Screen):
    transparent = True

    def __init__(self, root, destination=None, *, kind="site"):
        super().__init__()
        self.root = root
        self.destination = root.state.hero.pos if destination is None else destination
        self.kind = kind
        self.province = root.state.provinces[self.destination]
        self.approaches = root.state.adventure_approaches(self.destination) if kind == 'site' else ()
        self.approach_index = 0
        self.guards = self.province.site_guards if kind == "site" else self.province.guards

    @property
    def approach(self):
        return self.approaches[self.approach_index] if self.approaches else None

    @property
    def definition(self):
        ident = self.approach.encounter if self.approach else self.root.state.encounter_at(self.destination, kind=self.kind)
        return ENCOUNTERS[ident]

    @property
    def entry_blocked_reason(self):
        state = self.root.state
        if not state.actions_left:
            return 'End your campaign turn to regain an action.'
        if self.approach and (state.gold < self.approach.gold_cost or state.crystals < self.approach.crystals_cost):
            return f'This approach needs {self.approach.gold_cost} gold and {self.approach.crystals_cost} crystals.'
        return None

    def choose_approach(self, index):
        self.approach_index = index
        self.message = ''
        self.refresh()

    def on_reveal(self):
        self.refresh()

    def update(self, dt):
        if self._reading_display != (self.game.window_size, reading_scale(self.game)):
            self.refresh()

    def open_text_settings(self):
        from eador.settings_scene import SettingsScene
        self.game.push(SettingsScene(focus="codex_text_scale"))

    def refresh(self):
        super().refresh()
        self._reading_display = self.game.window_size, reading_scale(self.game)
        scale = self._reading_display[1] / 100
        state, p, definition = self.root.state, self.province, self.definition
        extraction, holding = definition.objective == 'extract', definition.objective == 'hold'

        def label(text, size=12, *, width=1064, color=MUTED, serif=False, scaled=True):
            return Label(text, width=width, wrap=True, font="Georgia" if serif else "Verdana",
                         font_size=round(size * scale) if scaled else size, text_color=color)

        title = Column(label("BEFORE THE EXPEDITION", 10, width=836, color=GOLD, scaled=False),
                       label(definition.name, 32, width=836, color=TEXT, serif=True, scaled=False), spacing=6)
        heading = Column(Row(title, Button("Text size", width=186, height=40, shortcut="T", on_click=self.open_text_settings),
                             spacing=42),
                         label(f"{p.name} · 1 hero action ({state.actions_left} left) · {state.gold} gold · {state.crystals} crystals"), spacing=6)
        top = [heading]
        if self.approaches:
            width = (1064 - 20 * (len(self.approaches) - 1)) // len(self.approaches)
            top.append(Row(*(Button(approach.title, width=width, height=40, shortcut=str(index + 1),
                                   on_click=lambda index=index: self.choose_approach(index),
                                   style=PRIMARY if index == self.approach_index else None)
                             for index, approach in enumerate(self.approaches)), spacing=20))
            description = self.approach.description
            if p.site_kind in ('smuggler_screen', 'aerie_raid', 'relief_column') and Counter(self.guards) != Counter(SITES[p.site_kind].guards):
                description = f'Free. {self.approach.title} against the surviving defenders shown below.'
            top.append(label(description, color=GOLD))

        left_width, right_width = 640, 392
        orders = Column(
            label('Escape with the cargo' if extraction else 'Secure the seal' if holding else 'Rout the defenders',
                  22, width=left_width, color=TEAL, serif=True),
            *(label(text, width=left_width) for text in self.instructions()), spacing=12)
        self._preview = Component(width=right_width, height=231)
        legend = ('● Allies   ■ Foes   Numbered exits' if extraction else
                  '● Allies   ■ Defenders   ◎ Seal' if holding else '● Allies   ■ Defenders')
        preview = Column(label('THE APPROACH', 10, width=right_width, color=GOLD), self._preview,
                         label(legend, 10, width=right_width), spacing=8)

        bonus = self.approach.bonus_gold if self.approach else 0
        reward = (f"{p.site_gold + bonus} gold · {p.site_crystals} crystal{'s' if p.site_crystals != 1 else ''}" if self.kind == "site" else
                  "Liberate Duskspire and complete the three-shard campaign.")
        if self.kind == "site" and p.site_relic:
            reward += f" · {RELICS[p.site_relic].name}"
        rewards = Column(label("REWARDS ON SUCCESS", 10, width=left_width, color=GOLD),
                         label(reward, width=left_width, color=TEXT), spacing=6)
        counts = [f"{UNITS[kind].name} ×{count}" for kind, count in Counter(self.guards).items()]
        defenders = Column(spacing=4)
        if len(counts) > 3:
            for start in range(0, len(counts), 2):
                pair = [label(text, width=(right_width - 16) // 2, color=RED) for text in counts[start:start + 2]]
                if len(pair) == 1:
                    pair.append(Component(width=(right_width - 16) // 2))
                defenders.add(Row(*pair, spacing=16))
        else:
            for text in counts:
                defenders.add(label(text, width=right_width, color=RED))
        if self.kind == 'site':
            health = p.site_guard_hp
            total = sum(UNITS[kind].hp for kind in self.guards)
            defenders.add(label(f'Defenders: {sum(health)}/{total} HP; wounds persist.', 10, width=right_width))

        # Measure the paired columns while attached, then align their tops. This
        # keeps the real deployment at its original hex size while text reflows.
        rows = []
        for pair in ((orders, preview), (rewards, defenders)):
            for column in pair:
                self.ui.add(column)
            height = max(column.get_preferred_size()[1] for column in pair)
            rows.append(Row(*(Column(column, height=height) for column in pair), spacing=32))
        buttons = Row(Button("Return to shard", width=210, height=40, shortcut="Esc", on_click=self.game.pop),
                      Button("Codex", width=140, height=40, shortcut="C", on_click=self.root.codex),
                      Component(width=366, height=40),
                      Button("Enter expedition" if self.kind == "site" else "Assault Duskspire",
                             width=276, height=40, shortcut="Enter", on_click=self.enter, style=PRIMARY,
                             enabled=self.entry_blocked_reason is None), spacing=24)
        footer = Column(label(self.message or self.entry_blocked_reason or 'Returning from this briefing costs nothing.', 11),
                        buttons, spacing=12)
        content = Column(Column(*top, spacing=12), Column(*rows, spacing=16), footer, spacing=16)
        self.ui.add(content)
        self.height = content.get_preferred_size()[1] + 48
        if self.height > 780:
            raise ValueError(f"Expedition briefing does not fit at {scale:.0%}: {definition.name}")
        self.x, self.y = (self.game.width - 1120) / 2, (self.game.height - self.height) / 2
        self.ui.add(Column(content, anchor=Anchor.TOP_LEFT, margin=(round(self.x + 28), round(self.y + 24))))

    def instructions(self):
        definition = self.definition
        hold_advice = 'Guard shields a holder; Pikemen Brace against melee. Ranged attacks bypass Brace.'
        if self.province.site_kind == 'relief_column':
            advice = []
            if 'militia' in self.guards:
                advice.append("Militia clears adjacent allies' Pin.")
            if 'skyrider' in self.guards:
                advice.append('Skyrider crosses occupied cells; deny its landing or remove support.')
            hold_advice = ' '.join(advice) or 'The surviving defenders shown keep their wounds in either approach.'
        carrier = 'Your hero carries the cargo. Reach an exit with an unspent hero action, then choose Evacuate.'
        if self.province.site_kind == 'stranded_explorer':
            isolated = [f'{UNITS[troop.kind].name} (army slot {index})'
                        for index, (troop, pos) in enumerate(zip(self.root.state.hero.army, definition.player_positions[1:]), 1)
                        if pos[0] > 0]
            split = ('Isolated east: hero and ' + ', '.join(isolated) + '.' if isolated
                     else 'Hero starts alone east.')
            carrier = split + ' ' + carrier
        rout_advice = 'Protect your rear and rotate wounded allies. Forest blocks distant shots but provides cover at its edge.'
        if self.province.site_kind == 'smuggler_screen':
            advice = []
            if 'sapper' in self.guards:
                advice.append('Sapper: one Smoke charge per battle blocks both sides’ shots and spells.')
            if 'warden' in self.guards:
                advice.append('Warden swaps wounded allies to safety.')
            rout_advice = ' '.join(advice + ['Defeated guards stay defeated. Codex explains these orders.'])
        elif self.province.site_kind == 'aerie_raid':
            advice = []
            if 'skyrider' in self.guards:
                advice.append('Skyriders cross marsh and troops. Pin slows flight; Brace punishes melee landings.')
            if 'pikeman' in self.guards:
                advice.append('Their Pikeman can Brace. Ranged shots avoid its spear reaction.')
            rout_advice = ' '.join(advice + ['Codex explains these orders.'])
        return (
            carrier,
            f'Clear adjacent foes. Escape or rout all defenders by round {definition.deadline}. Hero death loses immediately.',
            'A Warden can deliver an unspent hero. Attacking, casting or Guarding prevents evacuation this turn.',
        ) if definition.objective == 'extract' else (
            f"Hold the marked hex with any living ally for {definition.hold_turns} consecutive enemy turns. "
            "Adjacent enemies contest it; empty or contested control resets progress.",
            f"Before round {definition.deadline} ends, secure the seal or defeat every defender. Hero death loses immediately.",
            hold_advice,
        ) if definition.objective == 'hold' else (
            'Defeat every defender to claim the reward. Exhaustion forces retreat after 80 rounds.',
            'Keep your hero alive. Hero death ends the expedition immediately.',
            rout_advice,
        )

    def enter(self):
        if self.kind == 'site':
            command = lambda: self.root.state.explore(approach=self.approach.id if self.approach else None)
        else:
            command = lambda: self.root.state.travel(self.destination)
        if self.command(command):
            if not self.checkpoint(self.root.state):
                self.root.message = self.message
            self.game.pop()  # Revealing the shard follows the newly created battle.

    def draw(self):
        definition = self.definition
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 222))
        self.box(self.x, self.y, 1120, self.height)
        x, y, width, height = self._preview.bounds
        grid = HexGrid(dict(definition.terrain), size=21, origin=(x + width / 2, y + height / 2))
        for pos, terrain in definition.terrain:
            self.draw_polygon(grid.corners(pos), art.TERRAINS[terrain])
            art.outline(self, grid.corners(pos), INK)
        for pos in definition.player_positions[:len(self.root.state.hero.army) + 1]:
            cx, cy = grid.center(pos)
            self.draw_circle(cx, cy, 5, TEAL)
        for pos in definition.enemy_positions[:len(self.guards)]:
            cx, cy = grid.center(pos)
            self.draw_rect(cx - 4, cy - 4, 8, 8, RED)
        if definition.objective == 'extract':
            for number, pos in enumerate(definition.exits, 1):
                art.exit_marker(self, grid, pos, number)
        elif definition.objective == 'hold':
            art.seal(self, grid, definition.seal)
