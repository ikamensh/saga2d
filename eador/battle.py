"""Small deterministic hex battles with terrain, retaliation and hero magic."""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from saga2d import HexGrid

from eador.model import Hero, Pos, RuleError, UNITS
from eador.encounters import ENCOUNTERS


@dataclass(frozen=True)
class SpellSpec:
    name: str
    cost: int
    description: str


PLAYER_POSITIONS = ((-3, 1), (-2, 0), (-3, 2), (-2, 1), (-2, 2), (-3, 0), (-2, 3))
ENEMY_POSITIONS = ((3, -1), (2, 0), (3, -2), (2, -1), (2, 1), (3, -3), (2, -2))


SPELLS = {
    'bolt': SpellSpec('Arcane Bolt', 4, 'Deal 14 damage to an enemy within 4 hexes.'),
    'heal': SpellSpec('Heal', 4, 'Restore 16 health to a living ally within 4 hexes.'),
}


@dataclass
class BattleUnit:
    id: int
    team: str
    kind: str
    pos: Pos
    hp: int
    max_hp: int
    attack: int
    defense: int
    move_range: int
    attack_range: int
    moved: bool = False
    acted: bool = False
    retaliated: bool = False
    level: int = 1
    safe_attacks: int = 0
    terrain_walk: bool = False
    skirmisher: bool = False
    source_id: int | None = None
    stance: str | None = None
    abilities: tuple[str, ...] = ()
    pinned: bool = False
    pin_cooldown: int = 0

    @property
    def can_pin(self) -> bool:
        return 'pin' in self.abilities

    @property
    def can_brace(self) -> bool:
        return self.kind == 'pikeman' or 'brace' in self.abilities

    @property
    def effective_move_range(self) -> int:
        return max(1, self.move_range - (2 if self.pinned else 0))

    @property
    def alive(self) -> bool:
        return self.hp > 0

    @property
    def effective_defense(self) -> int:
        """Armor including the current stance, before terrain cover."""
        return self.defense + (2 if self.stance == 'guard' else 0)

    @property
    def name(self) -> str:
        return 'Hero' if self.kind == 'hero' else UNITS[self.kind].name


@dataclass
class BattleObjective:
    kind: str = 'rout'
    target: Pos | None = None
    progress: int = 0
    required: int = 0
    deadline: int | None = None


@dataclass
class Battle:
    units: list[BattleUnit]
    terrain: dict[Pos, str]
    mana: int
    spells: set[str]
    round: int = 1
    outcome: str | None = None
    log: list[str] = field(default_factory=list)
    spell_costs: dict[str, int] = field(default_factory=lambda: {'bolt': 4, 'heal': 4})
    spell_power: dict[str, int] = field(default_factory=lambda: {'bolt': 14, 'heal': 16})
    hero_id: int | None = 0
    objective: BattleObjective = field(default_factory=BattleObjective)
    outcome_reason: str | None = None

    @classmethod
    def create(cls, hero: Hero, enemies: list[str], terrain: str,
               spells: set[str], seed: int = 0, *, enemy_hp: list[int] | None = None,
               encounter: str | None = None) -> Battle:
        definition = ENCOUNTERS[encounter] if encounter is not None else None
        tiles = dict(definition.terrain) if definition else cls._terrain(terrain, seed)
        player_positions = definition.player_positions if definition else PLAYER_POSITIONS
        enemy_positions = definition.enemy_positions if definition else ENEMY_POSITIONS
        hero_attack = 10 + (hero.level - 1) * 2 + (4 if hero.hero_class == 'Warrior' else 0)
        units = [BattleUnit(0, 'player', 'hero', player_positions[0], hero.hp,
                            hero.max_hp, hero_attack, 3 + hero.level // 2, 3,
                            3 if hero.hero_class == 'Scout' else 2 if hero.hero_class == 'Wizard' else 1, level=hero.level)]
        for troop, pos in zip(hero.army, player_positions[1:]):
            spec = UNITS[troop.kind]
            units.append(BattleUnit(troop.id, 'player', troop.kind, pos, troop.hp,
                                    troop.max_hp, spec.attack + troop.level - 1 + (hero.hero_class == 'Commander'),
                                    spec.defense + (troop.level - 1) // 2,
                                    spec.move_range, spec.attack_range, level=troop.level, abilities=('pin',) if troop.kind == 'archer' else ()))
        health = enemy_hp if enemy_hp is not None else [UNITS[kind].hp for kind in enemies]
        if len(health) != len(enemies):
            raise ValueError('Enemy health must match the enemy army.')
        units += cls._deploy(list(zip(enemies, health)), enemy_positions, 'enemy', max(u.id for u in units) + 1000)
        units[0].abilities = ('pin',) if hero.relic == 'storm_quiver' else ('brace',) if hero.relic == 'watch_bell' else ()
        ranks = hero.skill_ranks
        units[0].safe_attacks = ranks.get('duelist', 0) + (hero.relic == 'iron_crown')
        units[0].attack += 2 * ranks.get('duelist', 0)
        units[0].terrain_walk = bool(ranks.get('pathfinder', 0)) or hero.relic == 'wayfarer_boots'
        units[0].skirmisher = bool(ranks.get('skirmisher', 0))
        units[0].move_range += ranks.get('pathfinder', 0) + max(0, ranks.get('skirmisher', 0) - 1)
        for unit in units[1:]:
            if unit.team == 'player':
                unit.safe_attacks = ranks.get('tactician', 0)
                unit.terrain_walk = bool(ranks.get('pathfinder', 0))
        costs = {'bolt': max(1, 4 - ranks.get('channeling', 0)), 'heal': max(1, 4 - ranks.get('restoration', 0))}
        power = {'bolt': 14 + (6 if hero.relic == 'ember_lens' else 0),
                 'heal': 16 + 4 * ranks.get('restoration', 0) + (6 if hero.relic == 'moonstone' else 0)}
        objective = BattleObjective('hold', definition.seal, 0, definition.hold_turns, definition.deadline) if definition else BattleObjective()
        return cls(units, tiles, hero.mana, set(spells), log=['Advance, use cover, and protect your wounded.'],
                   spell_costs=costs, spell_power=power, objective=objective)

    @staticmethod
    def _terrain(terrain: str, seed: int) -> dict[Pos, str]:
        rng = random.Random(seed)
        return {(q, r): (rng.choice(('plains', terrain, terrain)) if abs(q) < 2 else 'plains')
                for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3}

    @staticmethod
    def _deploy(army: list[tuple[str, int]], positions, team: str, first_id: int) -> list[BattleUnit]:
        if len(army) > len(positions):
            raise ValueError('A battlefield holds at most seven units per army.')
        units = []
        for i, ((kind, hp), pos) in enumerate(zip(army, positions), first_id):
            spec = UNITS[kind]
            if not 0 < hp <= spec.hp:
                raise ValueError('A combatant must have positive health within its maximum.')
            units.append(BattleUnit(i, team, kind, pos, hp, spec.hp, spec.attack,
                                    spec.defense, spec.move_range, spec.attack_range, abilities=('pin',) if kind == 'archer' else ()))
        return units

    @classmethod
    def clash(cls, attackers: list[tuple[str, int]], defenders: list[tuple[str, int]],
              terrain: str, seed: int = 0) -> Battle:
        """Create a hero-free encounter for persistent rival and neutral armies."""
        if not attackers or not defenders:
            raise ValueError('A clash requires two nonempty armies.')
        units = cls._deploy(attackers, PLAYER_POSITIONS, 'player', 0)
        units += cls._deploy(defenders, ENEMY_POSITIONS, 'enemy', 1000)
        return cls(units, cls._terrain(terrain, seed), 0, set(), hero_id=None)

    @property
    def grid(self) -> HexGrid:
        return HexGrid(self.terrain)

    def unit(self, unit_id: int) -> BattleUnit:
        for unit in self.units:
            if unit.id == unit_id:
                return unit
        raise RuleError('Unknown unit.')

    def _actor(self, unit_id: int) -> BattleUnit:
        if self.outcome is not None:
            raise RuleError('The battle is over.')
        unit = self.unit(unit_id)
        if not unit.alive:
            raise RuleError('That unit has fallen.')
        if unit.team != 'player':
            raise RuleError('Choose one of your units.')
        return unit

    def reachable(self, unit_id: int) -> set[Pos]:
        unit = self.unit(unit_id)
        if not unit.alive or unit.moved or (unit.acted and not unit.skirmisher) or self.outcome:
            return set()
        occupied = {other.pos for other in self.units if other.alive and other.id != unit_id}
        cells = self.grid.reachable(unit.pos, unit.effective_move_range, blocked=occupied,
                                    cost=lambda pos: 2 if self.terrain[pos] in ('forest', 'marsh') and not unit.terrain_walk else 1)
        return set(cells) - {unit.pos}

    def targets(self, unit_id: int) -> list[BattleUnit]:
        unit = self.unit(unit_id)
        if not unit.alive or unit.acted or self.outcome:
            return []
        return [other for other in self.units if other.alive and other.team != unit.team
                and HexGrid.distance(unit.pos, other.pos) <= unit.attack_range]

    def move(self, unit_id: int, destination: Pos) -> None:
        unit = self._actor(unit_id)
        self._move(unit, destination)

    def _move(self, unit: BattleUnit, destination: Pos) -> None:
        if destination not in self.reachable(unit.id):
            raise RuleError('That hex is occupied, out of reach, or this unit already moved.')
        unit.pos = destination
        unit.moved = True

    def attack(self, unit_id: int, target_id: int) -> None:
        self._attack(self._actor(unit_id), self.unit(target_id))

    def pin_targets(self, unit_id: int) -> list[BattleUnit]:
        unit = self.unit(unit_id)
        if not unit.alive or not unit.can_pin or unit.pin_cooldown or unit.acted or self.outcome:
            return []
        return [other for other in self.units if other.alive and other.team != unit.team
                and not other.pinned and HexGrid.distance(unit.pos, other.pos) <= 3]

    def pin_preview(self, unit_id: int, target_id: int) -> tuple[int, int]:
        """Forecast actual Pin damage and any adjacent defensive reaction, without mutation."""
        damage, spear, retaliation = self._attack_effects(self.unit(unit_id), self.unit(target_id), pin=True)
        return damage, spear + retaliation

    def pin(self, unit_id: int, target_id: int) -> None:
        """Spend an action on a ranged slowing shot, then skip the next turn's Pin."""
        self._attack(self._actor(unit_id), self.unit(target_id), pin=True)

    def guard(self, unit_id: int) -> None:
        """Spend the remaining order to Guard, or Brace for a Pikeman, until its next turn."""
        self._guard(self._actor(unit_id))

    def _guard(self, unit: BattleUnit) -> None:
        if unit.acted:
            raise RuleError('That unit has already acted.')
        unit.stance = 'brace' if unit.can_brace else 'guard'
        unit.moved = unit.acted = True
        self.log.append(f'{unit.name} {"braces" if unit.stance == "brace" else "guards"} until its next turn.')

    def _damage(self, attacker: BattleUnit, target: BattleUnit, *, pin: bool = False) -> int:
        cover = 2 if self.terrain[target.pos] in ('forest', 'hills') else 0
        damage = max(1, attacker.attack - target.effective_defense - cover)
        return min(target.hp, (damage + 1) // 2 if pin else damage)

    def preview(self, unit_id: int, target_id: int) -> tuple[int, int]:
        """Return actual target and attacker HP loss for a legal attack, without mutation."""
        damage, spear, retaliation = self._attack_effects(self.unit(unit_id), self.unit(target_id))
        return damage, spear + retaliation

    def _attack_effects(self, unit: BattleUnit, target: BattleUnit, *, pin: bool = False) -> tuple[int, int, int]:
        """Resolve the ordered damage once for both forecasts and attacks."""
        if pin and target not in self.pin_targets(unit.id):
            raise RuleError('Pin needs a ready ability and an unpinned enemy within 3 hexes.')
        if not pin and target not in self.targets(unit.id):
            raise RuleError('Choose an enemy within attack range; each unit attacks once.')
        adjacent = HexGrid.distance(unit.pos, target.pos) == 1
        braces = target.stance == 'brace' and adjacent and unit.attack_range == 1 and not pin
        spear = self._damage(target, unit) if braces else 0
        if spear == unit.hp:
            return 0, spear, 0
        damage = self._damage(unit, target, pin=pin)
        # Brace reserves its one reaction for melee; ranged contact cannot
        # take an ordinary retaliation first and leave the spear ready too.
        retaliates = target.stance != 'brace' and unit.safe_attacks == 0 and target.hp > damage and not target.retaliated and adjacent
        return damage, spear, self._damage(target, unit) if retaliates else 0

    def _attack(self, unit: BattleUnit, target: BattleUnit, *, pin: bool = False) -> None:
        damage, spear, retaliation = self._attack_effects(unit, target, pin=pin)
        if spear:
            unit.hp -= spear
            target.stance = None
            target.retaliated = True
            self.log.append(f'{target.name} braces and strikes {unit.name} for {spear} before the attack.')
        target.hp -= damage
        if pin:
            unit.pin_cooldown = 2
            target.pinned = target.alive
        unit.acted = True
        if not unit.skirmisher:
            unit.moved = True
        if unit.safe_attacks:
            unit.safe_attacks -= 1
        if unit.alive:
            self.log.append(f'{unit.name} {"pins" if pin else "hits"} {target.name} for {damage}.')
        if retaliation:
            unit.hp -= retaliation
            target.retaliated = True
            self.log.append(f'{target.name} retaliates for {retaliation}.')
        self._check_outcome()

    def spell_cost(self, spell: str) -> int:
        if spell not in SPELLS:
            raise RuleError('Unknown spell.')
        return self.spell_costs[spell]

    def cast(self, spell: str, target_id: int) -> None:
        if self.hero_id is None:
            raise RuleError('This army has no spellcasting hero.')
        hero = self._actor(self.hero_id)
        if spell not in self.spells or spell not in SPELLS:
            raise RuleError('That spell has not been learned.')
        if hero.acted:
            raise RuleError('Your hero has already acted.')
        if self.mana < self.spell_cost(spell):
            raise RuleError('Not enough mana.')
        target = self.unit(target_id)
        if not target.alive or HexGrid.distance(hero.pos, target.pos) > 4:
            raise RuleError('Choose a living target within 4 hexes.')
        if spell == 'bolt' and target.team != 'enemy':
            raise RuleError('Arcane Bolt targets enemies.')
        if spell == 'heal' and (target.team != 'player' or target.hp == target.max_hp):
            raise RuleError('Heal targets a wounded ally.')
        self.mana -= self.spell_cost(spell)
        hero.acted = hero.moved = True
        if spell == 'bolt':
            damage = min(target.hp, self.spell_power['bolt'])
            target.hp -= damage
            self.log.append(f'Arcane Bolt strikes {target.name} for {damage}.')
        else:
            healed = min(self.spell_power['heal'], target.max_hp - target.hp)
            target.hp += healed
            self.log.append(f'Heal restores {healed} health to {target.name}.')
        self._check_outcome()

    def _check_outcome(self) -> None:
        if (self.hero_id is not None and not self.unit(self.hero_id).alive) or not any(u.alive and u.team == 'player' for u in self.units):
            self.outcome = 'enemy'
            self.outcome_reason = 'hero_death' if self.hero_id is not None else 'rout'
        elif not any(u.alive and u.team == 'enemy' for u in self.units):
            self.outcome = 'player'
            self.outcome_reason = 'rout'

    def _objective_turn(self) -> None:
        objective = self.objective
        if objective.kind != 'hold':
            return
        holding = any(unit.alive and unit.team == 'player' and unit.pos == objective.target for unit in self.units)
        contested = any(unit.alive and unit.team == 'enemy' and HexGrid.distance(unit.pos, objective.target) <= 1 for unit in self.units)
        objective.progress = objective.progress + 1 if holding and not contested else 0
        if objective.progress >= objective.required:
            self.outcome, self.outcome_reason = 'player', 'hold'
            self.log.append('The seal is secured. The surviving defenders withdraw.')
        elif self.round >= objective.deadline:
            self.outcome, self.outcome_reason = 'enemy', 'deadline'
            self.log.append('Time ran out before the seal could be secured.')

    def _contest_seal(self, unit: BattleUnit) -> None:
        """Defenders close on the seal unless they can immediately kill its holder or hero."""
        target = self.objective.target
        critical = [other for other in self.targets(unit.id)
                    if other.id == self.hero_id or other.pos == target]
        if any(self.preview(unit.id, other.id)[0] == other.hp for other in critical):
            return
        if unit.moved or self.grid.distance(unit.pos, target) <= 1:
            return
        choices = self.reachable(unit.id) | {unit.pos}
        destination = min(choices, key=lambda pos: (self.grid.distance(pos, target),
                          self.terrain[pos] not in ('forest', 'hills'), pos))
        if destination != unit.pos:
            self._move(unit, destination)

    def _play_team(self, team: str) -> None:
        for unit in self.units:
            if self.outcome:
                break
            if unit.team != team or not unit.alive or unit.acted:
                continue
            if unit.kind == 'hero':
                injured = [u for u in self.units if u.alive and u.team == team and u.max_hp - u.hp >= 12
                           and HexGrid.distance(unit.pos, u.pos) <= 4]
                if 'heal' in self.spells and self.mana >= self.spell_cost('heal') and injured:
                    self.cast('heal', min(injured, key=lambda u: u.hp / u.max_hp).id)
                    continue
                enemies = [u for u in self.units if u.alive and u.team != team and HexGrid.distance(unit.pos, u.pos) <= 4]
                if 'bolt' in self.spells and self.mana >= self.spell_cost('bolt') and enemies:
                    self.cast('bolt', min(enemies, key=lambda u: u.hp).id)
                    continue
            defending_seal = team == 'enemy' and self.objective.kind == 'hold'
            if defending_seal:
                self._contest_seal(unit)
            targets = self.targets(unit.id)
            if not targets and not unit.moved and not defending_seal:
                enemies = [u for u in self.units if u.alive and u.team != team]
                reachable = self.reachable(unit.id)
                if reachable and enemies:
                    def score(pos):
                        distances = [HexGrid.distance(pos, enemy.pos) for enemy in enemies]
                        distance = min(distances)
                        can_attack = distance <= unit.attack_range
                        cover = self.terrain[pos] in ('forest', 'hills')
                        return (not can_attack, max(0, distance - unit.attack_range), not cover,
                                -distance if can_attack else distance, pos)
                    destination = min(reachable | {unit.pos}, key=score)
                    if destination != unit.pos:
                        if team == 'player':
                            self.move(unit.id, destination)
                        else:
                            self._move(unit, destination)
                targets = self.targets(unit.id)
            if targets:
                if defending_seal:
                    target = min(targets, key=lambda other: (
                        not (other.id == self.hero_id and self.preview(unit.id, other.id)[0] == other.hp),
                        other.pos != self.objective.target, other.hp, other.id))
                else:
                    target = min(targets, key=lambda u: (u.hp, u.id))
                # Trade damage for control only when it prevents this target's
                # next melee approach. A kill or an occupied seal takes priority.
                distance = min(HexGrid.distance(ally.pos, target.pos) for ally in self.units
                               if ally.alive and ally.team == team)
                slow_stops_approach = (target.attack_range + max(1, target.move_range - 2) < distance
                                       <= target.attack_range + target.move_range)
                use_pin = (target in self.pin_targets(unit.id) and slow_stops_approach
                           and self.preview(unit.id, target.id)[0] < target.hp
                           and not (defending_seal and target.pos == self.objective.target))
                if use_pin:
                    if team == 'player':
                        self.pin(unit.id, target.id)
                    else:
                        self._attack(unit, target, pin=True)
                elif team == 'player':
                    self.attack(unit.id, target.id)
                else:
                    self._attack(unit, target)
            elif unit.kind == 'pikeman':
                self._guard(unit)

    def end_turn(self) -> None:
        if self.outcome:
            raise RuleError('The battle is over.')
        # Enemy actions begin fresh; retaliation refreshes once per full round.
        for unit in self.units:
            if unit.team == 'player':
                unit.pinned = False
            else:
                unit.pin_cooldown = max(0, unit.pin_cooldown - 1)
                unit.moved = unit.acted = False
                unit.stance = None
        self._play_team('enemy')
        for unit in self.units:
            if unit.team == 'enemy':
                unit.pinned = False
        if not self.outcome:
            self._objective_turn()
        if not self.outcome:
            self.round += 1
            for unit in self.units:
                unit.moved = unit.acted = unit.retaliated = False
                if unit.team == 'player':
                    unit.stance = None
                    unit.pin_cooldown = max(0, unit.pin_cooldown - 1)
            if self.round > 80:
                self.outcome = 'enemy'
                self.outcome_reason = 'exhaustion'
                self.log.append('The exhausted army must retreat.')

    def auto_turn(self) -> None:
        if self.outcome:
            raise RuleError('The battle is over.')
        self._play_team('player')
        if not self.outcome:
            self.end_turn()

    def to_dict(self) -> dict:
        return {'units': [asdict(unit) for unit in self.units],
                'terrain': [{'pos': list(pos), 'kind': kind} for pos, kind in self.terrain.items()],
                'mana': self.mana, 'spells': sorted(self.spells), 'round': self.round,
                'outcome': self.outcome, 'log': list(self.log),
                'spell_costs': dict(self.spell_costs), 'spell_power': dict(self.spell_power), 'hero_id': self.hero_id,
                'objective': asdict(self.objective), 'outcome_reason': self.outcome_reason}

    @classmethod
    def from_dict(cls, data: dict) -> Battle:
        return cls(units=[BattleUnit(**{**u, 'pos': tuple(u['pos']), 'abilities': tuple(u['abilities'])}) for u in data['units']],
                   terrain={tuple(t['pos']): t['kind'] for t in data['terrain']},
                   mana=data['mana'], spells=set(data['spells']), round=data['round'],
                   outcome=data['outcome'], log=list(data['log']),
                   spell_costs=dict(data['spell_costs']), spell_power=dict(data['spell_power']), hero_id=data['hero_id'],
                   objective=BattleObjective(**{**data['objective'], 'target': tuple(data['objective']['target']) if data['objective']['target'] is not None else None}),
                   outcome_reason=data['outcome_reason'])
