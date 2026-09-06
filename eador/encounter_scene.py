"""An authored expedition's objective, defenders and cost before committing."""

from collections import Counter

from saga2d import HexGrid
from eador import art
from eador.content import RELICS
from eador.encounters import ENCOUNTERS
from eador.model import UNITS
from eador.scene import Screen
from eador.style import GOLD, INK, MUTED, RED, TEAL, TEXT


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

    def refresh(self):
        super().refresh()
        self.height = 700 if self.approaches else 610
        self.x, self.y = (self.game.width - 900) / 2, (self.game.height - self.height) / 2
        for index, approach in enumerate(self.approaches):
            self.button(approach.title, self.x + 28 + index * 432, self.y + 136, 412,
                        lambda index=index: self.choose_approach(index), shortcut=str(index + 1),
                        primary=index == self.approach_index)
        bottom = self.y + self.height - 70
        self.button("Return to shard", self.x + 28, bottom, 210, self.game.pop, shortcut="Esc")
        self.button("Codex", self.x + 252, bottom, 140, self.root.codex, shortcut="C")
        self.button("Enter expedition" if self.kind == "site" else "Assault Duskspire", self.x + 596, bottom, 276, self.enter,
                    shortcut="Enter", primary=True, enabled=self.entry_blocked_reason is None)

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
        x, y, p, definition = self.x, self.y, self.province, self.definition
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 222))
        self.box(x, y, 900, self.height)
        self.text("BEFORE THE EXPEDITION", x + 28, y + 22, size=10, color=GOLD)
        self.text(self.definition.name, x + 28, y + 47, size=32, serif=True)
        state = self.root.state
        self.text(f"{p.name} · 1 hero action ({state.actions_left} left) · {state.gold} gold · {state.crystals} crystals",
                  x + 28, y + 96, size=12, color=MUTED)
        extraction = bool(definition.exits)
        offset = 112 if self.approaches else 0
        if self.approach:
            self.paragraph(self.approach.description, x + 28, y + 190, width=844, size=12, color=GOLD)
        self.rule(x + 28, y + 132 + offset, 844)
        self.text('Escape with the cargo' if extraction else 'Secure the seal',
                  x + 28, y + 152 + offset, size=22, color=TEAL, serif=True)
        top = y + 191 + offset
        instructions = (
            'Your hero carries the cargo. Reach an exit with an unspent hero action, then choose Evacuate.',
            f'Clear adjacent foes. Escape or rout all defenders by round {definition.deadline}. Hero death loses immediately.',
            'A Warden can deliver an unspent hero. Attacking, casting or Guarding prevents evacuation this turn.',
        ) if extraction else (
            f"Hold the marked hex with any living ally for {definition.hold_turns} consecutive enemy turns. "
            "Adjacent enemies contest it; empty or contested control resets progress.",
            f"Before round {definition.deadline} ends, secure the seal or defeat every defender. Hero death loses immediately.",
            "Guard shields a holder; Pikemen Brace against melee. Ranged attacks bypass Brace.",
        )
        for paragraph in instructions:
            top += self.paragraph(paragraph, x + 28, top, width=450, size=12) + 14
        reward_top = y + self.height - 170
        self.text("REWARDS ON SUCCESS", x + 28, reward_top, size=10, color=GOLD)
        bonus = self.approach.bonus_gold if self.approach else 0
        reward = (f"{p.site_gold + bonus} gold · {p.site_crystals} crystals" if self.kind == "site" else
                  "Liberate Duskspire and complete the three-shard campaign.")
        if self.kind == "site" and p.site_relic:
            reward += f" · {RELICS[p.site_relic].name}"
        self.paragraph(reward, x + 28, reward_top + 24, width=450, size=12, color=TEXT)
        self.text("THE APPROACH", x + 696, y + (140 if self.approaches else 152) + offset,
                  size=10, color=GOLD, center=True)
        grid = HexGrid(dict(definition.terrain), size=21, origin=(x + 695, y + 300 + (90 if self.approaches else 0)))
        for pos, terrain in definition.terrain:
            self.draw_polygon(grid.corners(pos), art.TERRAINS[terrain])
            art.outline(self, grid.corners(pos), INK)
        for pos in definition.player_positions[:len(self.root.state.hero.army) + 1]:
            cx, cy = grid.center(pos)
            self.draw_circle(cx, cy, 5, TEAL)
        for pos in definition.enemy_positions[:len(self.guards)]:
            cx, cy = grid.center(pos)
            self.draw_rect(cx - 4, cy - 4, 8, 8, RED)
        if extraction:
            for number, pos in enumerate(definition.exits, 1):
                art.exit_marker(self, grid, pos, number)
        else:
            art.seal(self, grid, definition.seal)
        self.text('● Allies    ■ Foes    Numbered exits' if extraction else '● Allies    ■ Defenders    ◎ Seal',
                  x + 695, reward_top - 11, size=10, color=MUTED, center=True)
        guards = ", ".join(f"{count} {UNITS[kind].name}" for kind, count in Counter(self.guards).items())
        self.paragraph(guards, x + 530, reward_top + 18, width=340, size=12, color=RED)
        if extraction:
            health = self.province.site_guard_hp
            total = sum(UNITS[kind].hp for kind in self.guards)
            self.text(f'Defenders: {sum(health)}/{total} HP; wounds persist.', x + 530, reward_top + 55, size=10, color=MUTED)
        self.text(self.message or self.entry_blocked_reason or 'Returning from this briefing costs nothing.',
                  x + 28, y + self.height - 97, size=11, color=MUTED)
