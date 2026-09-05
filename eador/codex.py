"""Read-only Shardbound reference, built from the game's current rule tables."""

from collections import Counter
from dataclasses import dataclass

from eador.battle import Battle, SPELLS
from eador.content import RELICS, SITES, SKILLS
from eador.model import BUILDINGS, HERO_CLASSES, RECRUITABLE, UNITS
from eador.scene import Screen
from eador.style import GOLD, MUTED, TEAL, TEXT


CATEGORIES = ("Troops", "Spells", "Buildings", "Skills", "Sites", "Relics")
PAGE_SIZE = 3


@dataclass(frozen=True)
class _Entry:
    title: str
    facts: str
    description: str


class CodexScene(Screen):
    """Inspect rules without changing the root campaign or writing save files.

    Number keys select a category; Tab/Shift+Tab cycle categories. Left/Right
    or Page Up/Page Down turn pages. Escape closes this overlay.
    """

    transparent = True
    pop_on_cancel = True
    controls = {"tab": "next_category", "shift+tab": "previous_category",
                ("left", "pageup"): "previous_page", ("right", "pagedown"): "next_page",
                "home": "first_page", "end": "last_page"}

    def __init__(self, root):
        super().__init__()
        self.root = root
        self.category = 0
        self.page = 0

    @property
    def pages(self):
        return max(1, (len(self.entries) + PAGE_SIZE - 1) // PAGE_SIZE)

    def refresh(self):
        super().refresh()
        self.entries = self.read_entries()
        self.page = min(self.page, self.pages - 1)
        self.x, self.y = self.game.width / 2 - 520, self.game.height / 2 - 350
        for i, category in enumerate(CATEGORIES):
            self.button(category, self.x + 24 + i * 167, self.y + 104, 157,
                        lambda i=i: self.select_category(i), hotkey=str(i + 1), primary=i == self.category)
            self.bind_key(str(i + 1), lambda i=i: self.select_category(i))
        self.button("Previous", self.x + 24, self.y + 634, 150, self.previous_page,
                    hotkey="←", enabled=self.page > 0)
        self.button("Next", self.x + 184, self.y + 634, 150, self.next_page,
                    hotkey="→", enabled=self.page + 1 < self.pages)
        self.button("Close codex", self.x + 830, self.y + 634, 186, self.game.pop, hotkey="Esc")

    def select_category(self, index):
        self.category, self.page = index, 0
        self.refresh()

    def next_category(self):
        self.select_category((self.category + 1) % len(CATEGORIES))

    def previous_category(self):
        self.select_category((self.category - 1) % len(CATEGORIES))

    def previous_page(self):
        self.page = max(0, self.page - 1)
        self.refresh()

    def next_page(self):
        self.page = min(self.pages - 1, self.page + 1)
        self.refresh()

    def first_page(self):
        self.page = 0
        self.refresh()

    def last_page(self):
        self.page = self.pages - 1
        self.refresh()

    def read_entries(self):
        state = self.root.state
        category = CATEGORIES[self.category]
        if category == "Troops":
            entries = []
            for kind, spec in UNITS.items():
                facts = (f"Base: {spec.hp} health · {spec.attack} attack · {spec.defense} defense · "
                         f"{spec.move_range} movement · {spec.attack_range} range")
                role = "Ranged attacker." if spec.attack_range > 1 else "Melee fighter."
                if kind in RECRUITABLE:
                    requirement = f"Requires {BUILDINGS[spec.building].name}." if spec.building else "No building required."
                    description = (f"{role} Recruit for {state.recruit_cost(kind)} gold now (base {spec.cost}); "
                                   f"upkeep {spec.upkeep} gold/turn. {requirement}")
                    if kind == "healer":
                        description += " An acolyte adds 2 army recovery each resting turn."
                else:
                    description = f"{role} Encountered as a guardian; cannot be recruited."
                entries.append(_Entry(spec.name, facts, description))
            return entries
        if category == "Spells":
            # The public battle factory applies current skills/equipment without mutating the hero.
            battle = state.battle or Battle.create(state.hero, [], "plains", state.spells)
            sources = {"bolt": "Wizard, Mage Tower or equipped Ember Lens",
                       "heal": "Wizard, Temple or equipped Moonstone"}
            return [_Entry(spec.name,
                          f"Your hero: {battle.spell_cost(kind)} mana · {battle.spell_power[kind]} "
                          f"{'damage' if kind == 'bolt' else 'healing'} · {'Learned' if kind in battle.spells else 'Not learned'}",
                          f"Base cost: {spec.cost} mana. {spec.description} Requires {sources[kind]}. "
                          "Casting spends the hero's action and movement.")
                    for kind, spec in SPELLS.items()]
        if category == "Buildings":
            return [_Entry(spec.name, f"{spec.cost} gold · {spec.crystals} crystals · "
                          f"{'Built' if kind in state.buildings else 'Not built'}", spec.description)
                    for kind, spec in BUILDINGS.items()]
        if category == "Skills":
            return [_Entry(spec.name, f"{spec.hero_class} only · {spec.max_rank} ranks · "
                          f"Your rank: {state.hero.skill_ranks.get(kind, 0)}", spec.description)
                    for kind, spec in SKILLS.items()]
        if category == "Sites":
            return [_Entry(spec.name, f"Reward: {spec.gold} gold · {spec.crystals} "
                          f"{'crystal' if spec.crystals == 1 else 'crystals'} · {RELICS[spec.relic].name}",
                          f"{spec.description} Base guardians: " + ", ".join(
                              f"{UNITS[kind].name} ×{count}" for kind, count in Counter(spec.guards).items()) + ".")
                    for spec in SITES.values()]
        return [_Entry(spec.name, f"Sell when found: {spec.value} gold · "
                      f"{'Equipped' if state.hero.relic == kind else 'Owned' if kind in state.inventory else 'Not owned'}",
                      spec.description)
                for kind, spec in RELICS.items()]

    def draw(self):
        x, y = self.x, self.y
        state = self.root.state
        self.draw_rect(0, 0, self.game.width, self.game.height, (6, 14, 19, 225))
        self.box(x, y, 1040, 700)
        self.text("THE FIELD CODEX", x + 24, y + 20, size=10, color=GOLD)
        self.text("Know your forces", x + 24, y + 41, size=30, serif=True)
        self.text(f"{state.hero.hero_class} · {HERO_CLASSES[state.hero.hero_class].description}",
                  x + 24, y + 81, size=12, color=MUTED)
        introductions = (
            "Level-one base stats. Veterans and your hero's abilities can improve them. Recruit in a province you control.",
            "Current mana costs and power include your hero's skills and equipped relic. Spell range is four hexes.",
            "Stronghold buildings are permanent. Each can be constructed once, even while your hero is away.",
            "Each earned hero level offers a discipline. Deepen one path or develop both; skills belong to a hero class.",
            "Explore an owned, uncleared site using one hero action. Eastern sites have an additional Dread Guard.",
            "Keep or sell each find. Equip one relic between battles. Distill duplicates for 4 crystals.",
        )
        self.paragraph(introductions[self.category], x + 24, y + 163, width=992, size=13)
        start = self.page * PAGE_SIZE
        for i, entry in enumerate(self.entries[start:start + PAGE_SIZE]):
            top = y + 223 + i * 134
            self.rule(x + 24, top - 13, 992)
            top += self.paragraph(entry.title, x + 24, top, width=992, size=19, color=TEAL) + 7
            top += self.paragraph(entry.facts, x + 24, top, width=992, size=12, color=GOLD) + 9
            self.paragraph(entry.description, x + 24, top, width=992, size=13, color=TEXT)
        self.text(f"{CATEGORIES[self.category]} · Page {self.page + 1} of {self.pages} · {len(self.entries)} entries",
                  x + 354, y + 640, size=13, color=MUTED)
        self.text("1–6 tabs  /  Tab, Shift+Tab cycle  /  ← → pages", x + 354, y + 664,
                  size=10, color=MUTED)
