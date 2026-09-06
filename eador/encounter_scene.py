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
        self.definition = ENCOUNTERS[root.state.encounter_at(self.destination, kind=kind)]
        self.guards = self.province.site_guards if kind == "site" else self.province.guards

    def refresh(self):
        super().refresh()
        self.x, self.y = (self.game.width - 900) / 2, (self.game.height - 610) / 2
        self.button("Return to shard", self.x + 28, self.y + 540, 210, self.game.pop, shortcut="Esc")
        self.button("Codex", self.x + 252, self.y + 540, 140, self.root.codex, shortcut="C")
        self.button("Enter expedition" if self.kind == "site" else "Assault Duskspire", self.x + 596, self.y + 540, 276, self.enter,
                    shortcut="Enter", primary=True, enabled=self.root.state.actions_left > 0)

    def enter(self):
        command = self.root.state.explore if self.kind == "site" else lambda: self.root.state.travel(self.destination)
        if self.command(command):
            if not self.checkpoint(self.root.state):
                self.root.message = self.message
            self.game.pop()  # Revealing the shard follows the newly created battle.

    def draw(self):
        x, y, p, definition = self.x, self.y, self.province, self.definition
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 222))
        self.box(x, y, 900, 610)
        self.text("BEFORE THE EXPEDITION", x + 28, y + 22, size=10, color=GOLD)
        self.text(self.definition.name, x + 28, y + 47, size=32, serif=True)
        self.text(f"{p.name} · Spend 1 hero action · {self.root.state.actions_left} remaining",
                  x + 28, y + 96, size=12, color=MUTED)
        self.rule(x + 28, y + 132, 844)
        self.text("Secure the seal", x + 28, y + 152, size=22, color=TEAL, serif=True)
        top = y + 191
        for paragraph in (
            f"Hold the marked hex with any living ally for {definition.hold_turns} consecutive enemy turns. "
            "Adjacent enemies contest it; empty or contested control resets progress.",
            f"Before round {definition.deadline} ends, secure the seal or defeat every defender. Hero death loses immediately.",
            "Guard shields a holder; Pikemen Brace against melee. Ranged attacks bypass Brace.",
        ):
            top += self.paragraph(paragraph, x + 28, top, width=450, size=12) + 14
        self.text("REWARDS", x + 28, y + 440, size=10, color=GOLD)
        reward = (f"{p.site_gold} gold · {p.site_crystals} crystals" if self.kind == "site" else
                  "Liberate Duskspire and complete the three-shard campaign.")
        if self.kind == "site" and p.site_relic:
            reward += f" · {RELICS[p.site_relic].name}"
        self.paragraph(reward, x + 28, y + 464, width=450, size=12, color=TEXT)
        self.text("THE APPROACH", x + 696, y + 152, size=10, color=GOLD, center=True)
        grid = HexGrid(dict(definition.terrain), size=21, origin=(x + 695, y + 300))
        for pos, terrain in definition.terrain:
            self.draw_polygon(grid.corners(pos), art.TERRAINS[terrain])
            art.outline(self, grid.corners(pos), INK)
        for pos in definition.player_positions[:len(self.root.state.hero.army) + 1]:
            cx, cy = grid.center(pos)
            self.draw_circle(cx, cy, 5, TEAL)
        for pos in definition.enemy_positions[:len(self.guards)]:
            cx, cy = grid.center(pos)
            self.draw_rect(cx - 4, cy - 4, 8, 8, RED)
        art.seal(self, grid, definition.seal)
        self.text("● Allies    ■ Defenders    ◎ Seal", x + 695, y + 429, size=10, color=MUTED, center=True)
        guards = ", ".join(f"{count} {UNITS[kind].name}" for kind, count in Counter(self.guards).items())
        self.paragraph(guards, x + 530, y + 458, width=340, size=12, color=RED)
        self.text(self.message or ("End your campaign turn to regain an action." if not self.root.state.actions_left else
                                  "Returning from this briefing costs nothing."),
                  x + 28, y + 513, size=11, color=MUTED)
