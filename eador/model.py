"""Shardbound's campaign rules; scenes issue commands and read this state.

The shard, economy, progression and save format belong to the game. Hex
geometry and movement search are the reusable Saga2D primitive.
"""
from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field, fields
from typing import TYPE_CHECKING

from saga2d import HexGrid

from eador.content import Choice, ChoiceOption, RELICS, SITES, SKILLS

if TYPE_CHECKING:
    from eador.battle import Battle

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


UNITS = {
    'militia': UnitSpec('Militia', 24, 8, 2, 3, 1, 20, 1, None, (208, 181, 127)),
    'swordsman': UnitSpec('Swordsman', 34, 11, 4, 3, 1, 45, 2, 'barracks', (131, 177, 185)),
    'archer': UnitSpec('Archer', 20, 8, 1, 3, 3, 35, 2, 'archery', (155, 185, 112)),
    'healer': UnitSpec('Acolyte', 22, 7, 2, 3, 2, 45, 2, 'temple', (210, 197, 233)),
    'brigand': UnitSpec('Brigand', 20, 7, 1, 3, 1, 0, 0, None, (185, 102, 91)),
    'goblin': UnitSpec('Goblin', 16, 6, 1, 3, 2, 0, 0, None, (144, 160, 89)),
    'wolf': UnitSpec('Wolf', 17, 8, 1, 4, 1, 0, 0, None, (176, 166, 162)),
    'guard': UnitSpec('Dread Guard', 42, 12, 4, 3, 1, 0, 0, None, (173, 130, 196)),
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
    inventory: list[str] = field(default_factory=list)
    _choices: list[Choice] = field(default_factory=list, repr=False)

    @classmethod
    def new(cls, seed: int = 7, hero_class: str = 'Commander') -> State:
        if type(seed) is not int:
            raise RuleError('The shard seed must be an integer.')
        if not isinstance(hero_class, str) or hero_class not in HERO_CLASSES:
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
            if pos[0] == 0:
                guards = ['brigand', 'goblin', 'wolf']
            elif pos[0] == 1:
                guards = ['guard', 'guard', 'brigand', 'goblin']
            elif pos[0] == 2:
                guards = ['guard', 'guard', 'archer']
            owner = 'rival' if pos[0] == 2 else 'neutral'
            provinces[pos] = Province(pos, name, terrain, owner,
                                      rng.randint(5, 9), int(terrain == 'hills'),
                                      guards, None)
            kind = rng.choice(tuple(SITES))
            spec = SITES[kind]
            province = provinces[pos]
            province.site, province.site_kind = spec.name, kind
            province.site_guards = list(spec.guards) + (['guard'] if pos[0] >= 1 else [])
            province.site_relic = spec.relic
            province.site_gold, province.site_crystals = spec.gold, spec.crystals
        home, rival = provinces[(-2, 0)], provinces[(2, 0)]
        home.name, home.owner, home.capital, home.income = 'Westwatch', 'player', True, 16
        home.guards, home.site = [], 'Buried Shrine'
        home.site_kind, home.site_guards, home.site_relic = 'shrine', list(SITES['shrine'].guards), 'moonstone'
        home.site_gold, home.site_crystals = SITES['shrine'].gold, SITES['shrine'].crystals
        rival.name, rival.owner, rival.capital, rival.income = 'Duskspire', 'rival', True, 16
        rival.guards, rival.site = ['guard'] * 5 + ['archer'] * 2, None
        rival.site_kind, rival.site_guards, rival.site_relic = None, [], None
        rival.site_gold = rival.site_crystals = 0
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
        if 'mage_tower' in self.buildings or self.hero.relic == 'ember_lens':
            spells.add('bolt')
        if self.hero.relic == 'moonstone':
            spells.add('heal')
        return spells

    @property
    def choice(self) -> Choice | None:
        return self._choices[0] if self._choices else None

    def recruit_cost(self, kind: str) -> int:
        if kind not in RECRUITABLE:
            raise RuleError('That unit cannot be recruited.')
        discount = 15 * self.hero.skill_ranks.get('quartermaster', 0)
        if self.hero.relic == 'merchant_seal':
            discount += 25
        return max(1, (UNITS[kind].cost * (100 - discount) + 99) // 100)

    def _skill_choice(self) -> Choice | None:
        options = tuple(ChoiceOption(key, f'{spec.name} {self.hero.skill_ranks.get(key, 0) + 1}', spec.description)
                        for key, spec in SKILLS.items() if spec.hero_class == self.hero.hero_class
                        and self.hero.skill_ranks.get(key, 0) < spec.max_rank)
        if not options:
            return None
        return Choice('Shape your hero', 'Master your current path or learn a different discipline.', options, 'skill', self.hero.hero_class)

    def _relic_choice(self, relic: str) -> Choice:
        spec = RELICS[relic]
        first = (ChoiceOption('distill', 'Distill the duplicate', 'Gain 4 crystals instead of another copy.')
                 if relic in self.inventory else ChoiceOption('take', f'Keep {spec.name}', spec.description))
        return Choice(f'Discovered {spec.name}', 'Keep its power or fund your realm. Only one relic can be equipped.',
                      (first, ChoiceOption('sell', f'Sell for {spec.value} gold', 'Trade the relic for immediate resources.')),
                      'relic', relic)

    def choose(self, option_id: str) -> None:
        choice = self.choice
        if choice is None:
            raise RuleError('There is no pending choice.')
        if option_id not in {option.id for option in choice.options}:
            raise RuleError('Choose one of the offered options.')
        if choice.kind == 'skill':
            self.hero.skill_ranks[option_id] = self.hero.skill_ranks.get(option_id, 0) + 1
            self.log.append(f'Learned {SKILLS[option_id].name} {self.hero.skill_ranks[option_id]}.')
        elif option_id == 'take':
            self.inventory.append(choice.context)
            self.log.append(f'Kept {RELICS[choice.context].name}. Equip it in the hero panel.')
        elif option_id == 'sell':
            self.gold += RELICS[choice.context].value
            self.log.append(f'Sold {RELICS[choice.context].name}.')
        else:
            self.crystals += 4
            self.log.append('Distilled a duplicate relic into 4 crystals.')
        self._choices.pop(0)
        # Several levels from one reward must offer the newly learned rank next.
        for i, pending in enumerate(self._choices):
            if pending.kind == 'skill':
                self._choices[i] = self._skill_choice()

    def equip(self, relic_id: str | None) -> None:
        if self.battle is not None:
            raise RuleError('Change equipment between battles.')
        if relic_id is not None and relic_id not in self.inventory:
            raise RuleError('You do not own that relic.')
        self.hero.relic = relic_id
        self.log.append(f'Equipped {RELICS[relic_id].name}.' if relic_id else 'Unequipped the relic.')

    def _ready(self, action: bool = False) -> None:
        if self.status != 'playing':
            raise RuleError('This campaign has ended. Start a new shard.')
        if self.battle is not None:
            raise RuleError('Finish or retreat from the battle first.')
        if self.choice is not None:
            raise RuleError('Resolve the pending choice first.')
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
        cost = self.recruit_cost(kind)
        if self.gold < cost:
            raise RuleError('Not enough gold.')
        self.gold -= cost
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
        self._start_battle(province.pos, 'site', province.site_guards)

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
                choice = self._skill_choice()
                if choice:
                    self._choices.append(choice)
            for troop in survivors:
                troop.xp += 3
                while troop.xp >= troop.level * 6:
                    troop.xp -= troop.level * 6
                    troop.level += 1
                    troop.max_hp += 4
                    troop.hp += 4
            self.hero.hp = min(self.hero.max_hp, self.hero.hp + 6 * self.hero.skill_ranks.get('vigor', 0))
            if self.battle_kind == 'site':
                province.explored = True
                self.gold += province.site_gold
                self.crystals += province.site_crystals
                message = f'Explored {province.site}: +{province.site_gold} gold, +{province.site_crystals} crystals.'
                if province.site_relic:
                    self._choices.append(self._relic_choice(province.site_relic))
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
            recovery = 6 + (3 if 'temple' in self.buildings else 0) + self.hero.skill_ranks.get('quartermaster', 0)
            if self.hero.relic == 'oak_standard':
                recovery += 3
            if any(t.kind == 'healer' for t in self.hero.army):
                recovery += 2
            self.hero.hp = min(self.hero.max_hp, self.hero.hp + recovery + 2 + 2 * self.hero.skill_ranks.get('vigor', 0))
            for troop in self.hero.army:
                troop.hp = min(troop.max_hp, troop.hp + recovery)
        self.hero.mana = min(self.hero.max_mana, self.hero.mana + 4)
        self.log.append(f'Turn {self.turn}: {earnings:+d} gold after upkeep; army rests.')
        if self.turn >= 5 and (self.turn - 5) % 4 == 0:
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
        data['schema_version'] = 2
        data['choices'] = data.pop('_choices')
        data['buildings'] = sorted(self.buildings)
        data['battle'] = self.battle.to_dict() if self.battle else None
        return json.dumps(data, sort_keys=True)

    @classmethod
    def from_json(cls, text: str) -> State:
        if not isinstance(text, str):
            raise SaveFormatError('Save data must be JSON text.')
        try:
            data = json.loads(text)
        except ValueError as error:
            raise SaveFormatError('The save file contains invalid JSON or a number beyond the supported size.') from error
        except RecursionError as error:
            raise SaveFormatError('The save file is nested too deeply to read.') from error
        if not isinstance(data, dict):
            raise SaveFormatError('The save must contain a campaign object.')
        version = data.get('schema_version', 1)
        if type(version) is not int or version not in (1, 2):
            raise SaveFormatError(f'Unsupported save version {version}; this game reads versions 1 and 2.')
        _validate_save(data, version)
        data.pop('schema_version', None)
        if version == 1:
            data['inventory'], data['choices'] = [], []
            data['hero']['skill_ranks'], data['hero']['relic'] = {}, None
            if data['battle'] is not None:
                data['battle']['spell_costs'] = {'bolt': 4, 'heal': 4}
                data['battle']['spell_power'] = {'bolt': 14, 'heal': 16}
            old_sites = {'Buried Shrine': 'shrine', 'Forgotten Tower': 'tower', 'Old Barrow': 'barrow'}
            for province in data['provinces']:
                site = province['site']
                province.update(site_kind=old_sites.get(site), site_relic=None,
                                site_guards=(['brigand', 'goblin'] if province['pos'][0] < 1 else ['guard', 'goblin']) if site else [],
                                site_gold=55 if site else 0, site_crystals=2 if site else 0)
        data['_choices'] = [Choice(**{**choice, 'options': tuple(ChoiceOption(**option) for option in choice['options'])})
                            for choice in data.pop('choices')]
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


def _validate_save(data: dict, version: int) -> None:
    """Check the serialized public state before constructing mutable game objects."""
    from eador.battle import BattleUnit

    def require(condition, message):
        if not condition:
            raise SaveFormatError(message)

    def object_fields(value, expected, label, optional=()):
        require(isinstance(value, dict), f'{label} must be an object.')
        require(set(expected) <= value.keys() and value.keys() <= set(expected) | set(optional),
                f'{label} has missing or unsupported fields.')

    def integer(value, label, minimum=0, maximum=None):
        require(type(value) is int and value >= minimum and (maximum is None or value <= maximum),
                f'{label} is outside its valid range.')

    def strings(value, label, allowed=None, unique=False):
        require(isinstance(value, list) and all(isinstance(item, str) for item in value), f'{label} must be a list of text.')
        if allowed is not None:
            require(set(value) <= set(allowed), f'{label} contains unknown content IDs.')
        if unique:
            require(len(value) == len(set(value)), f'{label} contains duplicates.')

    def position(value, label):
        require(isinstance(value, list) and len(value) == 2 and all(type(n) is int for n in value),
                f'{label} must contain two grid coordinates.')
        return tuple(value)

    def text_fields(value, names, label):
        require(all(isinstance(value[name], str) for name in names), f'{label} contains invalid text.')

    new_state = {'inventory', '_choices'}
    state_keys = {f.name for f in fields(State)} - new_state
    if version == 2:
        state_keys |= {'inventory', 'choices', 'schema_version'}
    object_fields(data, state_keys, 'Campaign', optional={'schema_version'} if version == 1 else ())
    require(type(data['seed']) is int, 'The shard seed must be an integer.')
    for name in ('gold', 'crystals', 'actions_left'):
        integer(data[name], name)
    for name in ('turn', 'next_troop_id'):
        integer(data[name], name, minimum=1)
    require(data['status'] in ('playing', 'victory', 'defeat'), 'Unknown campaign status.')
    strings(data['log'], 'Campaign log')
    strings(data['buildings'], 'Buildings', BUILDINGS, unique=True)

    hero = data['hero']
    hero_keys = {f.name for f in fields(Hero)} - ({'skill_ranks', 'relic'} if version == 1 else set())
    object_fields(hero, hero_keys, 'Hero')
    text_fields(hero, ('name', 'hero_class'), 'Hero')
    require(hero['hero_class'] in HERO_CLASSES, 'Unknown hero class.')
    for name in ('hp', 'max_hp', 'level', 'max_mana'):
        integer(hero[name], f'Hero {name}', minimum=1)
    integer(hero['hp'], 'Hero health', maximum=hero['max_hp'])
    integer(hero['mana'], 'Hero mana', maximum=hero['max_mana'])
    integer(hero['xp'], 'Hero experience', maximum=hero['level'] * 12 - 1)
    hero_pos = position(hero['pos'], 'Hero position')
    require(data['actions_left'] <= (3 if hero['hero_class'] == 'Scout' else 2), 'Too many campaign actions.')
    require(isinstance(hero['army'], list) and len(hero['army']) <= (6 if hero['hero_class'] == 'Commander' else 5), 'Invalid army size.')
    troop_ids = set()
    troops_by_id = {}
    for troop in hero['army']:
        object_fields(troop, {f.name for f in fields(Troop)}, 'Troop')
        require(troop['kind'] in RECRUITABLE, 'Unknown recruited troop kind.')
        for name in ('id', 'hp', 'max_hp', 'level'):
            integer(troop[name], f'Troop {name}', minimum=1)
        integer(troop['hp'], 'Troop health', maximum=troop['max_hp'])
        integer(troop['xp'], 'Troop experience', maximum=troop['level'] * 6 - 1)
        require(troop['id'] not in troop_ids and troop['id'] < data['next_troop_id'], 'Invalid or duplicate troop ID.')
        troop_ids.add(troop['id'])
        troops_by_id[troop['id']] = troop

    expected_cells = {(q, r) for q in range(-2, 3) for r in range(-2, 3) if abs(q + r) <= 2}
    require(isinstance(data['provinces'], list) and len(data['provinces']) == len(expected_cells), 'The shard must contain 19 provinces.')
    provinces = {}
    site_fields = {'site_kind', 'site_guards', 'site_relic', 'site_gold', 'site_crystals'}
    for province in data['provinces']:
        object_fields(province, {f.name for f in fields(Province)} - (site_fields if version == 1 else set()), 'Province')
        pos = position(province['pos'], 'Province position')
        require(pos in expected_cells and pos not in provinces, 'Invalid or duplicate province position.')
        provinces[pos] = province
        text_fields(province, ('name', 'terrain', 'owner'), 'Province')
        require(province['terrain'] in ('plains', 'forest', 'hills', 'marsh'), 'Unknown terrain.')
        require(province['owner'] in ('player', 'neutral', 'rival'), 'Unknown province owner.')
        require(type(province['capital']) is bool and type(province['explored']) is bool, 'Invalid province flags.')
        require(province['capital'] == (pos in {(-2, 0), (2, 0)}), 'Invalid capital location.')
        integer(province['income'], 'Province income')
        integer(province['crystals'], 'Province crystal income')
        strings(province['guards'], 'Province guards', UNITS)
        require(len(province['guards']) <= 7, 'A garrison exceeds the battlefield capacity.')
        require(province['site'] is None or isinstance(province['site'], str), 'Invalid site name.')
        if version == 1:
            require(province['site'] in (None, 'Buried Shrine', 'Forgotten Tower', 'Old Barrow'), 'Unknown legacy site.')
        else:
            require(province['site_kind'] is None or isinstance(province['site_kind'], str) and province['site_kind'] in SITES, 'Unknown site content ID.')
            require((province['site'] is None) == (province['site_kind'] is None), 'Site identity is inconsistent.')
            strings(province['site_guards'], 'Site guards', UNITS)
            require(len(province['site_guards']) <= 7, 'A site exceeds battlefield capacity.')
            require(province['site_relic'] is None or isinstance(province['site_relic'], str) and province['site_relic'] in RELICS, 'Unknown site relic.')
            integer(province['site_gold'], 'Site gold')
            integer(province['site_crystals'], 'Site crystals')
    require(hero_pos in provinces, 'Hero is outside the shard.')
    require(data['status'] != 'playing' or provinces[hero_pos]['owner'] == 'player', 'The hero must be in a controlled province.')
    require(data['status'] != 'victory' or provinces[(2, 0)]['owner'] == 'player', 'Victory requires capturing Duskspire.')
    require(data['status'] != 'defeat' or provinces[(-2, 0)]['owner'] == 'rival', 'Defeat requires losing Westwatch.')

    if version == 2:
        strings(data['inventory'], 'Inventory', RELICS, unique=True)
        require(hero['relic'] is None or isinstance(hero['relic'], str) and hero['relic'] in data['inventory'], 'The equipped relic is not owned.')
        require(isinstance(hero['skill_ranks'], dict), 'Skill ranks must be an object.')
        for skill, rank in hero['skill_ranks'].items():
            require(skill in SKILLS and SKILLS[skill].hero_class == hero['hero_class'], 'Unknown or incompatible hero skill.')
            integer(rank, 'Skill rank', minimum=1, maximum=SKILLS[skill].max_rank)
        require(sum(hero['skill_ranks'].values()) <= hero['level'] - 1, 'The hero has more skill ranks than earned levels.')
        require(isinstance(data['choices'], list), 'Pending choices must be a list.')
        for choice in data['choices']:
            object_fields(choice, {f.name for f in fields(Choice)}, 'Choice')
            text_fields(choice, ('title', 'description', 'kind', 'context'), 'Choice')
            require(choice['kind'] in ('skill', 'relic'), 'Unknown choice kind.')
            require(isinstance(choice['options'], list) and len(choice['options']) in (1, 2), 'Invalid choice options.')
            for option in choice['options']:
                object_fields(option, {f.name for f in fields(ChoiceOption)}, 'Choice option')
                text_fields(option, ('id', 'name', 'description'), 'Choice option')
            option_ids = [option['id'] for option in choice['options']]
            require(len(option_ids) == len(set(option_ids)), 'Duplicate choice options.')
            if choice['kind'] == 'skill':
                require(choice['context'] == hero['hero_class'], 'Skill choice is for another hero class.')
                available = {key for key, spec in SKILLS.items() if spec.hero_class == hero['hero_class'] and hero['skill_ranks'].get(key, 0) < spec.max_rank}
                require(set(option_ids) == available, 'Skill choice contains unavailable ranks.')
            else:
                require(choice['context'] in RELICS, 'Choice names an unknown relic.')
                first = 'distill' if choice['context'] in data['inventory'] else 'take'
                require(set(option_ids) == {first, 'sell'}, 'Relic choice contains invalid options.')
        pending_ranks = sum(choice['kind'] == 'skill' for choice in data['choices'])
        require(sum(hero['skill_ranks'].values()) + pending_ranks <= hero['level'] - 1, 'Pending skill choices exceed earned levels.')

    battle = data['battle']
    if battle is None:
        require(data['battle_kind'] is None and data['battle_province'] is None, 'Battle context has no battle.')
        return
    require(data['status'] == 'playing', 'An ended campaign cannot contain a battle.')
    require(version == 1 or not data['choices'], 'A battle cannot begin during a reward choice.')
    require(data['battle_kind'] in ('conquest', 'site', 'defense'), 'Unknown battle context.')
    require(position(data['battle_province'], 'Battle province') in provinces, 'Battle province is outside the shard.')
    keys = {'units', 'terrain', 'mana', 'spells', 'round', 'outcome', 'log'}
    object_fields(battle, keys | ({'spell_costs', 'spell_power'} if version == 2 else set()), 'Battle')
    integer(battle['mana'], 'Battle mana', maximum=hero['max_mana'])
    integer(battle['round'], 'Battle round', minimum=1, maximum=81)
    require(battle['outcome'] in (None, 'player', 'enemy'), 'Unknown battle outcome.')
    strings(battle['log'], 'Battle log')
    strings(battle['spells'], 'Battle spells', ('bolt', 'heal'), unique=True)
    if version == 2:
        for key in ('spell_costs', 'spell_power'):
            object_fields(battle[key], {'bolt', 'heal'}, key)
            for value in battle[key].values():
                integer(value, key, minimum=1)
    require(isinstance(battle['terrain'], list), 'Battle terrain must be a list.')
    cells = set()
    for tile in battle['terrain']:
        object_fields(tile, {'pos', 'kind'}, 'Battle hex')
        pos = position(tile['pos'], 'Battle hex')
        require(pos not in cells and max(abs(pos[0]), abs(pos[1]), abs(sum(pos))) <= 3, 'Invalid or duplicate battle hex.')
        cells.add(pos)
        require(tile['kind'] in ('plains', 'forest', 'hills', 'marsh'), 'Unknown battle terrain.')
    require(len(cells) == 37, 'A battlefield must contain 37 hexes.')
    require(isinstance(battle['units'], list) and 2 <= len(battle['units']) <= 14, 'Invalid battle army size.')
    ids, occupied, player_ids, enemies = set(), set(), set(), []
    for unit in battle['units']:
        unit_keys = {f.name for f in fields(BattleUnit)} - ({'safe_attacks', 'terrain_walk', 'skirmisher'} if version == 1 else set())
        object_fields(unit, unit_keys, 'Battle unit')
        integer(unit['id'], 'Battle unit ID')
        require(unit['id'] not in ids, 'Duplicate battle unit ID.')
        ids.add(unit['id'])
        require(unit['team'] in ('player', 'enemy'), 'Unknown battle team.')
        require(isinstance(unit['kind'], str) and unit['kind'] in set(UNITS) | {'hero'}, 'Unknown battle unit kind.')
        require((unit['id'] == 0) == (unit['kind'] == 'hero'), 'Invalid battle hero identity.')
        for name in ('max_hp', 'attack', 'move_range', 'attack_range', 'level'):
            integer(unit[name], f'Battle unit {name}', minimum=1)
        integer(unit['hp'], 'Battle unit health', maximum=unit['max_hp'])
        integer(unit['defense'], 'Battle unit defense')
        for name in ('moved', 'acted', 'retaliated'):
            require(type(unit[name]) is bool, 'Invalid battle action flags.')
        if version == 2:
            integer(unit['safe_attacks'], 'Safe attacks')
            require(type(unit['terrain_walk']) is bool and type(unit['skirmisher']) is bool, 'Invalid battle traits.')
        pos = position(unit['pos'], 'Battle unit position')
        require(pos in cells, 'A battle unit is outside the battlefield.')
        if unit['hp'] > 0:
            require(pos not in occupied, 'Living battle units occupy the same hex.')
            occupied.add(pos)
        if unit['team'] == 'player':
            source = hero if unit['id'] == 0 else troops_by_id.get(unit['id'])
            require(source is not None, 'Battle contains a troop outside the campaign army.')
            require(unit['level'] == source['level'] and unit['max_hp'] == source['max_hp'], 'Battle progression does not match the campaign army.')
            require(unit['id'] == 0 or unit['kind'] == source['kind'], 'Battle troop kind differs from its campaign identity.')
            player_ids.add(unit['id'])
        else:
            enemies.append(unit)
    require(player_ids == troop_ids | {0} and enemies, 'Battle army does not match the campaign army.')
    hero_unit = next(unit for unit in battle['units'] if unit['id'] == 0)
    if battle['outcome'] == 'player':
        require(hero_unit['hp'] > 0 and all(unit['hp'] == 0 for unit in enemies), 'Battle victory is inconsistent.')
    elif battle['outcome'] is None:
        require(hero_unit['hp'] > 0 and any(unit['hp'] > 0 for unit in enemies), 'Unfinished battle already has a winner.')
    else:
        require(hero_unit['hp'] == 0 or battle['round'] == 81, 'Battle defeat is inconsistent.')
