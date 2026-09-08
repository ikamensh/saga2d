"""Shardbound catalogue and plain saved values, shared by realm and battle rules."""
from __future__ import annotations

from dataclasses import dataclass, field

Pos = tuple[int, int]


class SaveFormatError(ValueError):
    """A save is incompatible or does not describe a valid campaign."""


class RuleError(ValueError):
    """A legal game command cannot be performed in the current state."""


@dataclass(frozen=True)
class UnitSpec:
    name: str
    hp: int
    attack: int
    defense: int
    move_range: int
    attack_range: int
    cost: int
    upkeep: int
    building: str | None
    color: tuple[int, int, int]
    abilities: tuple[str, ...] = ()
    skirmisher: bool = False
    crystals: int = 0


UNITS = {
    'militia': UnitSpec('Militia', 24, 8, 2, 3, 1, 20, 1, None, (208, 181, 127), ('rally',)),
    'swordsman': UnitSpec('Swordsman', 34, 11, 4, 3, 1, 45, 2, 'barracks', (131, 177, 185)),
    'archer': UnitSpec('Archer', 20, 8, 1, 3, 3, 35, 2, 'archery', (155, 185, 112), ('pin',)),
    'healer': UnitSpec('Acolyte', 22, 7, 2, 3, 2, 45, 2, 'temple', (210, 197, 233), ('heal',)),
    'brigand': UnitSpec('Brigand', 20, 7, 1, 3, 1, 0, 0, None, (185, 102, 91)),
    'goblin': UnitSpec('Goblin', 16, 6, 1, 3, 2, 0, 0, None, (144, 160, 89)),
    'wolf': UnitSpec('Wolf', 17, 8, 1, 4, 1, 0, 0, None, (176, 166, 162)),
    'guard': UnitSpec('Dread Guard', 42, 12, 4, 3, 1, 0, 0, None, (173, 130, 196)),
    'warden': UnitSpec('Warden', 38, 8, 4, 2, 1, 55, 2, 'barracks', (140, 164, 203), ('swap',)),
    'ranger': UnitSpec('Ranger', 22, 7, 1, 3, 3, 50, 2, 'archery', (118, 185, 157), skirmisher=True),
    'pikeman': UnitSpec('Pikeman', 28, 9, 3, 2, 1, 40, 2, 'barracks', (173, 188, 149)),
    'sapper': UnitSpec('Sapper', 26, 7, 2, 3, 1, 60, 2, 'market', (190, 161, 105), ('smoke',), crystals=1),
    'adept': UnitSpec('Rune Adept', 28, 6, 2, 3, 2, 65, 2, 'mage_tower', (173, 143, 206), ('repulse',), crystals=2),
    'skyrider': UnitSpec('Skyrider', 28, 10, 2, 4, 1, 85, 3, 'temple', (137, 189, 221), ('fly',), crystals=3),
}
RECRUITABLE = ('militia', 'swordsman', 'archer', 'healer', 'pikeman', 'ranger', 'warden', 'sapper', 'adept', 'skyrider')


@dataclass(frozen=True)
class BuildingSpec:
    name: str
    cost: int
    crystals: int
    description: str


BUILDINGS = {
    'barracks': BuildingSpec('Barracks', 45, 0, 'Recruit swordsmen, defensive pikemen and extracting wardens.'),
    'archery': BuildingSpec('Archery Range', 55, 0, 'Recruit pinning archers and mobile rangers.'),
    'temple': BuildingSpec('Temple', 65, 0, 'Recruit acolytes; learn Heal; faster recovery.'),
    'mage_tower': BuildingSpec('Mage Tower', 75, 2, 'Learn Arcane Bolt; +4 maximum mana. In your territory, H then I spends 3 crystals and 1 action to restore up to 8 mana. Encirclement blocks infusion at Westwatch.'),
    'market': BuildingSpec('Marketplace', 60, 0, '+8 gold income each turn.'),
}


@dataclass(frozen=True)
class HeroClass:
    name: str
    description: str


HERO_CLASSES = {
    'Commander': HeroClass('Commander', 'Army +1 attack; command six troops.'),
    'Warrior': HeroClass('Warrior', '+12 health and +4 attack in battle.'),
    'Scout': HeroClass('Scout', 'Three campaign actions; ranged hero attacks.'),
    'Wizard': HeroClass('Wizard', '+6 mana; ranged attacks; begin with Bolt and Heal.'),
}


@dataclass
class Troop:
    id: int
    kind: str
    hp: int
    max_hp: int
    level: int = 1
    xp: int = 0


@dataclass(frozen=True)
class TroopSnapshot:
    """A detached troop description for a camp decision, not a live army member."""
    id: int
    kind: str
    hp: int
    max_hp: int
    level: int
    xp: int


@dataclass(frozen=True)
class ReplacementPreview:
    outgoing: TroopSnapshot
    incoming: TroopSnapshot
    gold: int
    crystals: int
    actions: int
    upkeep_before: int
    upkeep_after: int
    blocked_reason: str | None = None


@dataclass(frozen=True)
class InfusionPreview:
    """Capped potential mana gain, fixed price, and the reason an order is blocked."""
    mana: int
    crystals: int
    actions: int
    blocked_reason: str | None = None


@dataclass
class Hero:
    name: str
    hero_class: str
    pos: Pos
    hp: int
    max_hp: int
    mana: int
    max_mana: int
    army: list[Troop]
    level: int = 1
    xp: int = 0

    skill_ranks: dict[str, int] = field(default_factory=dict)
    relic: str | None = None

    @property
    def skills(self) -> set[str]:
        return set(self.skill_ranks)

    @property
    def max_army(self) -> int:
        return 6 if self.hero_class == 'Commander' else 5


def starting_hero(hero_class: str, pos: Pos, *, name: str = 'Alden') -> Hero:
    """Create one independent starter army using the shared class and troop catalogue."""
    if not isinstance(hero_class, str) or hero_class not in HERO_CLASSES:
        raise RuleError('Choose Commander, Warrior, Scout or Wizard.')
    max_hp = 48 if hero_class == 'Warrior' else 36
    mana = 16 if hero_class == 'Wizard' else 10
    army = [Troop(i, kind, UNITS[kind].hp, UNITS[kind].hp)
            for i, kind in enumerate(('militia', 'militia', 'archer'), 1)]
    return Hero(name, hero_class, pos, max_hp, max_hp, mana, mana, army)


@dataclass
class Province:
    pos: Pos
    name: str
    terrain: str
    owner: str
    income: int
    crystals: int
    guards: list[str]
    site: str | None
    explored: bool = False
    capital: bool = False
    site_kind: str | None = None
    site_guards: list[str] = field(default_factory=list)
    site_relic: str | None = None
    site_gold: int = 0
    site_crystals: int = 0
    guard_hp: list[int] = field(default_factory=list)
    site_guard_hp: list[int] = field(default_factory=list)

