"""The rival's visible orders and finite expedition, using ordinary game UI."""

from eador import art
from eador.model import UNITS
from eador.rival import RECRUIT_COSTS
from eador.scene import Screen
from eador.style import GOLD, MUTED, RED, TEAL


def rival_order(state):
    rival = state.rival
    if state.status == "victory":
        return "Duskspire has fallen"
    if state.status == "defeat":
        return "The rival holds the shard"
    if state.battle_kind in ("intercept", "defense"):
        return "Expedition in battle"
    target = state.provinces[rival.target].name if rival.target is not None else None
    action = {
        "march": f"March to {target}",
        "attack": f"Attack {target}",
        "return": f"Return via {target}",
        "recruit": "Recruit at Duskspire",
        "recover": "Heal at Duskspire",
        "watch": "Reassess its orders",
        "defeated": "Duskspire has fallen",
    }[rival.intent]
    when = "next turn" if rival.turns_until_action == 1 else f"in {rival.turns_until_action} turns"
    return f"{action} {when}"


class RivalScene(Screen):
    transparent = True
    pop_on_cancel = True

    def __init__(self, root):
        super().__init__()
        self.root = root

    def refresh(self):
        super().refresh()
        self.x, self.y = self.game.width / 2 - 440, self.game.height / 2 - 326
        self.button("Locate expedition", self.x + 28, self.y + 584, 250,
                    self.locate, shortcut="L")
        self.button("Close", self.x + 702, self.y + 584, 150,
                    self.game.pop, shortcut="Esc")

    def locate(self):
        self.root.selected = self.root.state.rival.pos
        self.game.pop()

    def draw(self):
        s, x, y = self.root.state, self.x, self.y
        rival = s.rival
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 215))
        self.box(x, y, 880, 652)
        self.text("THE DUSKSPIRE EXPEDITION", x + 28, y + 28, size=11, color=RED)
        self.text(rival_order(s), x + 28, y + 57, size=25, serif=True)
        self.text(f"At {s.provinces[rival.pos].name}  ·  {len(rival.army)} surviving troops",
                  x + 28, y + 100, size=12, color=MUTED)
        self.rule(x + 28, y + 131, 824)
        self.text(f"{rival.gold} gold", x + 28, y + 150, size=24, serif=True, color=GOLD)
        self.text(f"Income +{rival.income(s)}  ·  Upkeep −{rival.upkeep} / turn",
                  x + 220, y + 156, size=13, color=MUTED)
        costs = " / ".join(f"{UNITS[kind].name} {cost}" for kind, cost in RECRUIT_COSTS.items())
        self.paragraph(f"Refits at Duskspire: {costs} gold. Healing costs 1 gold per health restored.",
                       x + 28, y + 195, width=824, size=11, color=MUTED)
        self.rule(x + 28, y + 239, 824)
        if rival.army:
            for i, troop in enumerate(rival.army):
                xx, yy = x + 28 + (i % 2) * 420, y + 255 + (i // 2) * 56
                art.piece(self, xx + 26, yy + 21, troop.kind, "enemy", scale=.72)
                self.text(UNITS[troop.kind].name, xx + 66, yy, size=16, serif=True)
                self.text(f"{troop.hp}/{troop.max_hp} health", xx + 238, yy + 3, size=11, color=MUTED)
                self.bar(xx + 66, yy + 30, 286, troop.hp, troop.max_hp, RED)
        else:
            self.text("Its expedition is broken.", x + 28, y + 274, size=25, serif=True, color=TEAL)
            self.paragraph("The rival must buy a new army. Advance on Duskspire while it remusters; "
                           "the capital's garrison is a separate force.",
                           x + 28, y + 319, width=790, size=14)
        self.rule(x + 28, y + 464, 824)
        if s.encircled:
            routes = ", ".join(s.provinces[pos].name for pos in s.grid.neighbors((-2, 0)))
            advice = ("Westwatch is encircled: its gold, crystals, Marketplace and rest are blocked. "
                      f"Reclaim any of: {routes}. If gold and income cannot pay upkeep, "
                      "less experienced troops leave first.")
        else:
            advice = ("Travel into the expedition's province to intercept it. Stand in its target province "
                      "to defend. Casualties and wounds persist after every fight; a weakened expedition "
                      "returns home to pay for recovery. Its orders may change after a battle.")
        self.paragraph(advice, x + 28, y + 483, width=824, size=13)
