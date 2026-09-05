"""Shardbound's campaign rules; scenes issue commands and read this state.

The shard, economy, progression and save format belong to the game. Hex
geometry and movement search are the reusable Saga2D primitive.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

from saga2d import HexGrid

if TYPE_CHECKING:
    from eador.battle import Battle

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
    battle: Battle | None = None
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

    def travel(self, destination: Pos) -> None:
        self._ready(action=True)
        if destination not in self.grid.neighbors(self.hero.pos):
            raise RuleError('Travel to an adjacent province.')
        province = self.provinces[destination]
        self.actions_left -= 1
        if province.owner == 'player':
            self.hero.pos = destination
            self.log.append(f'Travelled to {province.name}.')
        else:
            self._start_battle(destination, 'conquest', province.guards)

    def explore(self) -> None:
        self._ready(action=True)
        province = self.provinces[self.hero.pos]
        if province.owner != 'player':
            raise RuleError('Explore a province you control.')
        if province.explored or province.site is None:
            raise RuleError('This province has no unexplored site.')
        self.actions_left -= 1
        guards = ['brigand', 'goblin'] if province.pos[0] < 1 else ['guard', 'goblin']
        self._start_battle(province.pos, 'site', guards)

    def _start_battle(self, province: Pos, kind: str, enemies: list[str]) -> None:
        from eador.battle import Battle
        self.battle_province, self.battle_kind = province, kind
        self.battle = Battle.create(self.hero, enemies, self.provinces[province].terrain,
                                    self.spells, seed=self.seed + self.turn * 37 + province[0] * 7 + province[1])
        title = self.provinces[province].site if kind == 'site' else self.provinces[province].name
        self.log.append(f'Battle at {title}.')

    def resolve_battle(self) -> str:
        if self.battle is None or self.battle.outcome is None:
            raise RuleError('The battle is not finished.')
        battle = self.battle
        province = self.provinces[self.battle_province]
        victory = battle.outcome == 'player'
        self.hero.hp = battle.unit(0).hp
        self.hero.mana = battle.mana
        casualties = []
        survivors = []
        for troop in self.hero.army:
            troop.hp = battle.unit(troop.id).hp
            if troop.hp <= 0:
                casualties.append(UNITS[troop.kind].name)
            else:
                survivors.append(troop)
        self.hero.army = survivors
        if victory:
            self.hero.xp += 8
            while self.hero.xp >= self.hero.level * 12:
                self.hero.xp -= self.hero.level * 12
                self.hero.level += 1
                self.hero.max_hp += 4
                self.hero.hp += 4
                self.hero.max_mana += 2
                self.hero.mana += 2
                self.log.append(f'{self.hero.name} reached level {self.hero.level}.')
            for troop in survivors:
                troop.xp += 3
                while troop.xp >= troop.level * 6:
                    troop.xp -= troop.level * 6
                    troop.level += 1
                    troop.max_hp += 4
                    troop.hp += 4
            if self.battle_kind == 'site':
                province.explored = True
                self.gold += 55
                self.crystals += 2
                message = f'Explored {province.site}: +55 gold, +2 crystals.'
            else:
                province.owner, province.guards = 'player', []
                self.hero.pos = province.pos
                self.gold += 25
                message = f'Claimed {province.name}: +25 gold.'
                if province.capital and province.pos == (2, 0):
                    self.status = 'victory'
                    message = 'Duskspire has fallen. The shard is yours!'
        else:
            self.hero.hp = max(self.hero.hp, self.hero.max_hp // 3)
            lost_gold = min(max(0, self.gold), 20)
            self.gold -= lost_gold
            message = f'Retreated. Lost {lost_gold} gold; the survivors keep their wounds.'
            if self.battle_kind == 'defense':
                province.owner = 'rival'
                province.guards = ['guard', 'brigand']
                self.hero.pos = (-2, 0)
                if province.capital:
                    self.status = 'defeat'
                    message = 'Westwatch has fallen. The rival claims the shard.'
        if casualties:
            self.log.append('Fallen: ' + ', '.join(casualties) + '.')
        self.log.append(message)
        self.battle = None
        self.battle_kind = None
        self.battle_province = None
        return message

    def retreat(self) -> str:
        if self.battle is None:
            raise RuleError('There is no battle to retreat from.')
        if self.battle.outcome is not None:
            raise RuleError('The battle is over; accept its result.')
        self.battle.outcome = 'enemy'
        return self.resolve_battle()

    def end_turn(self) -> None:
        self._ready()
        earnings = self.income - self.upkeep
        self.gold += earnings
        self.crystals += sum(p.crystals for p in self.provinces.values() if p.owner == 'player')
        self.turn += 1
        self.actions_left = 3 if self.hero.hero_class == 'Scout' else 2
        if self.provinces[self.hero.pos].owner == 'player':
            recovery = 6 + (3 if 'temple' in self.buildings else 0)
            if any(t.kind == 'healer' for t in self.hero.army):
                recovery += 2
            self.hero.hp = min(self.hero.max_hp, self.hero.hp + recovery + 2)
            for troop in self.hero.army:
                troop.hp = min(troop.max_hp, troop.hp + recovery)
        self.hero.mana = min(self.hero.max_mana, self.hero.mana + 4)
        self.log.append(f'Turn {self.turn}: {earnings:+d} gold after upkeep; army rests.')
        if self.turn >= 9 and (self.turn - 9) % 4 == 0:
            self._rival_turn()

    def _rival_turn(self) -> None:
        frontier = {neighbor for pos, province in self.provinces.items() if province.owner == 'rival'
                    for neighbor in self.grid.neighbors(pos) if self.provinces[neighbor].owner != 'rival'}
        if not frontier:
            return
        target = min(frontier, key=lambda pos: (HexGrid.distance(pos, (-2, 0)), pos))
        province = self.provinces[target]
        if target == self.hero.pos:
            self._start_battle(target, 'defense', ['guard', 'brigand', 'archer'])
            self.log.append(f'The rival attacks your army at {province.name}!')
            return
        province.owner, province.guards = 'rival', ['guard', 'brigand']
        self.log.append(f'The rival seized {province.name}.')
        if province.capital:
            self.status = 'defeat'
            self.log.append('Westwatch has fallen. The rival claims the shard.')

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
