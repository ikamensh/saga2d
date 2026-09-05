"""Shardbound's campaign rules; scenes issue commands and read this state.

The shard, economy, progression and save format belong to the game. Hex
geometry and movement search are the reusable Saga2D primitive.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field

from saga2d import HexGrid

Pos = tuple[int, int]


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


UNITS = {
    'militia': UnitSpec('Militia', 24, 8, 2, 3, 1, 20, 1, None, (208, 181, 127)),
    'swordsman': UnitSpec('Swordsman', 34, 11, 4, 3, 1, 45, 2, 'barracks', (131, 177, 185)),
    'archer': UnitSpec('Archer', 20, 8, 1, 3, 3, 35, 2, 'archery', (155, 185, 112)),
    'healer': UnitSpec('Acolyte', 22, 7, 2, 3, 2, 45, 2, 'temple', (210, 197, 233)),
    'brigand': UnitSpec('Brigand', 20, 7, 1, 3, 1, 0, 0, None, (185, 102, 91)),
    'goblin': UnitSpec('Goblin', 16, 6, 1, 3, 2, 0, 0, None, (144, 160, 89)),
    'wolf': UnitSpec('Wolf', 17, 8, 1, 4, 1, 0, 0, None, (176, 166, 162)),
    'guard': UnitSpec('Dread Guard', 32, 10, 4, 3, 1, 0, 0, None, (173, 130, 196)),
}
RECRUITABLE = ('militia', 'swordsman', 'archer', 'healer')


@dataclass(frozen=True)
class BuildingSpec:
    name: str
    cost: int
    crystals: int
    description: str


BUILDINGS = {
    'barracks': BuildingSpec('Barracks', 45, 0, 'Recruit durable swordsmen.'),
    'archery': BuildingSpec('Archery Range', 55, 0, 'Recruit ranged archers.'),
    'temple': BuildingSpec('Temple', 65, 0, 'Recruit acolytes; learn Heal; faster recovery.'),
    'mage_tower': BuildingSpec('Mage Tower', 75, 2, 'Learn Arcane Bolt; +4 maximum mana.'),
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
    'Wizard': HeroClass('Wizard', '+6 mana; begin with Arcane Bolt and Heal.'),
}


@dataclass
class Troop:
    id: int
    kind: str
    hp: int
    max_hp: int
    level: int = 1
    xp: int = 0


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

    @property
    def max_army(self) -> int:
        return 6 if self.hero_class == 'Commander' else 5


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


@dataclass
class State:
    seed: int
    provinces: dict[Pos, Province]
    hero: Hero
    gold: int = 100
    crystals: int = 4
    turn: int = 1
    buildings: set[str] = field(default_factory=set)
    actions_left: int = 2
    status: str = 'playing'
    log: list[str] = field(default_factory=list)
    battle: object | None = None
    battle_province: Pos | None = None
    battle_kind: str | None = None
    next_troop_id: int = 4

    @classmethod
    def new(cls, seed: int = 7, hero_class: str = 'Commander') -> State:
        if hero_class not in HERO_CLASSES:
            raise RuleError('Choose Commander, Warrior, Scout or Wizard.')
        rng = random.Random(seed)
        cells = [(q, r) for q in range(-2, 3) for r in range(-2, 3)
                 if abs(q + r) <= 2]
        names = ['Westwatch', 'Amber Fields', 'Old Hollow', 'Briarwood',
                 'Silverford', 'Winding Vale', 'Mossfell', 'Raven Hill',
                 'Greenwater', 'Heartwood', 'Stonecross', 'Sunken Road',
                 'Ashen Marsh', 'Frostmere', 'Cinderwood', 'High Pass',
                 'Lost Reach', 'Blackfen', 'Duskspire']
        provinces = {}
        for pos, name in zip(cells, names):
            terrain = rng.choice(('plains', 'forest', 'hills', 'marsh'))
            guards = [rng.choice(('brigand', 'goblin', 'wolf'))
                      for _ in range(1 if pos[0] < 0 else 2)]
            provinces[pos] = Province(pos, name, terrain, 'neutral',
                                      rng.randint(5, 9), int(terrain == 'hills'),
                                      guards, rng.choice(('Buried Shrine', 'Forgotten Tower', 'Old Barrow')))
        home, rival = provinces[(-2, 0)], provinces[(2, 0)]
        home.name, home.owner, home.capital, home.income = 'Westwatch', 'player', True, 16
        home.guards, home.site = [], 'Buried Shrine'
        rival.name, rival.owner, rival.capital, rival.income = 'Duskspire', 'rival', True, 16
        rival.guards, rival.site = ['guard', 'guard', 'archer', 'brigand'], None
        max_hp = 48 if hero_class == 'Warrior' else 36
        mana = 16 if hero_class == 'Wizard' else 10
        army = [Troop(i, kind, UNITS[kind].hp, UNITS[kind].hp)
                for i, kind in enumerate(('militia', 'militia', 'archer'), 1)]
        hero = Hero('Alden', hero_class, home.pos, max_hp, max_hp, mana, mana, army)
        state = cls(seed, provinces, hero, actions_left=3 if hero_class == 'Scout' else 2)
        state.log.append('Claim the shard: capture Duskspire before Westwatch falls.')
        return state

    @property
    def grid(self) -> HexGrid:
        return HexGrid(self.provinces)

    @property
    def income(self) -> int:
        return sum(p.income for p in self.provinces.values() if p.owner == 'player') + (8 if 'market' in self.buildings else 0)

    @property
    def upkeep(self) -> int:
        return sum(UNITS[t.kind].upkeep for t in self.hero.army)

    @property
    def spells(self) -> set[str]:
        spells = {'bolt', 'heal'} if self.hero.hero_class == 'Wizard' else set()
        if 'temple' in self.buildings:
            spells.add('heal')
        if 'mage_tower' in self.buildings:
            spells.add('bolt')
        return spells

    def _ready(self, action: bool = False) -> None:
        if self.status != 'playing':
            raise RuleError('This campaign has ended. Start a new shard.')
        if self.battle is not None:
            raise RuleError('Finish or retreat from the battle first.')
        if action and self.actions_left <= 0:
            raise RuleError('No campaign actions remain. End the turn.')

    def build(self, kind: str) -> None:
        self._ready()
        if kind not in BUILDINGS:
            raise RuleError('Unknown building.')
        if kind in self.buildings:
            raise RuleError('That building is already built.')
        spec = BUILDINGS[kind]
        if self.gold < spec.cost or self.crystals < spec.crystals:
            raise RuleError('Not enough gold or crystals.')
        self.gold -= spec.cost
        self.crystals -= spec.crystals
        self.buildings.add(kind)
        if kind == 'mage_tower':
            self.hero.max_mana += 4
            self.hero.mana += 4
        self.log.append(f'Built {spec.name}.')

    def recruit(self, kind: str) -> None:
        self._ready()
        if kind not in RECRUITABLE:
            raise RuleError('That unit cannot be recruited.')
        if self.provinces[self.hero.pos].owner != 'player':
            raise RuleError('Recruit in one of your provinces.')
        spec = UNITS[kind]
        if spec.building and spec.building not in self.buildings:
            raise RuleError(f'Build {BUILDINGS[spec.building].name} first.')
        if len(self.hero.army) >= self.hero.max_army:
            raise RuleError('Your army is full.')
        if self.gold < spec.cost:
            raise RuleError('Not enough gold.')
        self.gold -= spec.cost
        self.hero.army.append(Troop(self.next_troop_id, kind, spec.hp, spec.hp))
        self.next_troop_id += 1
        self.log.append(f'Recruited {spec.name}.')

    def to_json(self) -> str:
        data = asdict(self)
        data['provinces'] = [asdict(p) for p in self.provinces.values()]
        data['buildings'] = sorted(self.buildings)
        data['battle'] = self.battle.to_dict() if self.battle else None
        return json.dumps(data, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> State:
        data = json.loads(text)
        data['provinces'] = {tuple(p['pos']): Province(**{**p, 'pos': tuple(p['pos'])}) for p in data['provinces']}
        data['hero']['pos'] = tuple(data['hero']['pos'])
        data['hero']['army'] = [Troop(**t) for t in data['hero']['army']]
        data['hero'] = Hero(**data['hero'])
        data['buildings'] = set(data['buildings'])
        if data['battle'] is not None:
            from eador.battle import Battle
            data['battle'] = Battle.from_dict(data['battle'])
        if data['battle_province'] is not None:
            data['battle_province'] = tuple(data['battle_province'])
        return cls(**data)
