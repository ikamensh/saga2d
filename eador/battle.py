"""Small deterministic hex battles with terrain, retaliation and hero magic."""
from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field, replace

from saga2d import HexGrid

from eador.model import Hero, Pos, RuleError, UNITS
from eador.encounters import ENCOUNTERS
from eador.sight import line_of_sight


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


@dataclass(frozen=True)
class SmokeCloud:
    pos: Pos
    expires_before_team: str


@dataclass(frozen=True)
class RallyPreview:
    move_range: int
    reachable: frozenset[Pos]


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
    cargo_penalty: int = 0
    spent_abilities: tuple[str, ...] = ()

    @property
    def can_fly(self) -> bool:
        return 'fly' in self.abilities

    @property
    def can_repulse(self) -> bool:
        return 'repulse' in self.abilities

    @property
    def can_smoke(self) -> bool:
        return 'smoke' in self.abilities

    @property
    def can_rally(self) -> bool:
        return 'rally' in self.abilities

    @property
    def can_pin(self) -> bool:
        return 'pin' in self.abilities

    @property
    def can_swap(self) -> bool:
        return 'swap' in self.abilities

    @property
    def can_heal(self) -> bool:
        return 'heal' in self.abilities

    @property
    def can_brace(self) -> bool:
        return self.kind == 'pikeman' or 'brace' in self.abilities

    @property
    def effective_move_range(self) -> int:
        return max(1, self.move_range - (2 if self.pinned else 0) - self.cargo_penalty)

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
    exits: tuple[Pos, ...] = ()


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
    sight_rules: str = 'terrain'
    smoke_clouds: list[SmokeCloud] = field(default_factory=list)

    @classmethod
    def create(cls, hero: Hero, enemies: list[str], terrain: str,
               spells: set[str], seed: int = 0, *, enemy_hp: list[int] | None = None,
               encounter: str | None = None, cargo_penalty: int = 0) -> Battle:
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
                                    spec.move_range, spec.attack_range, level=troop.level, abilities=spec.abilities, skirmisher=spec.skirmisher))
        health = enemy_hp if enemy_hp is not None else [UNITS[kind].hp for kind in enemies]
        if len(health) != len(enemies):
            raise ValueError('Enemy health must match the enemy army.')
        units += cls._deploy(list(zip(enemies, health)), enemy_positions, 'enemy', max(u.id for u in units) + 1000)
        units[0].abilities = ('pin',) if hero.relic == 'storm_quiver' else ('brace',) if hero.relic == 'watch_bell' else ()
        units[0].cargo_penalty = cargo_penalty
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
        objective = (BattleObjective('extract', deadline=definition.deadline, exits=definition.exits) if definition and definition.exits
                     else BattleObjective('hold', definition.seal, 0, definition.hold_turns, definition.deadline) if definition
                     else BattleObjective())
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
                                    spec.defense, spec.move_range, spec.attack_range, abilities=spec.abilities, skirmisher=spec.skirmisher))
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
        return self._reachable(self.unit(unit_id))

    def _reachable(self, unit: BattleUnit) -> set[Pos]:
        if not unit.alive or unit.moved or (unit.acted and not unit.skirmisher) or self.outcome:
            return set()
        occupied = {other.pos for other in self.units if other.alive and other.id != unit.id}
        cells = self.grid.reachable(unit.pos, unit.effective_move_range, blocked=() if unit.can_fly else occupied,
                                    cost=lambda pos: 2 if self.terrain[pos] in ('forest', 'marsh')
                                    and not (unit.terrain_walk or unit.can_fly) else 1)
        return set(cells) - occupied - {unit.pos}

    def has_sight(self, source: Pos, target: Pos) -> bool:
        """Forest/cloud visibility shared by targeting, previews and route evaluation."""
        return self.sight_rules == 'open' or line_of_sight(self.terrain, source, target,
                                                          smoke={cloud.pos for cloud in self.smoke_clouds})

    def targets(self, unit_id: int) -> list[BattleUnit]:
        return self._targets_from(self.unit(unit_id), self.unit(unit_id).pos)

    def _targets_from(self, unit: BattleUnit, pos: Pos) -> list[BattleUnit]:
        if not unit.alive or unit.acted or self.outcome:
            return []
        return [other for other in self.units if other.alive and other.team != unit.team
                and HexGrid.distance(pos, other.pos) <= unit.attack_range
                and (unit.attack_range == 1 or self.has_sight(pos, other.pos))]

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
                and not other.pinned and HexGrid.distance(unit.pos, other.pos) <= 3
                and self.has_sight(unit.pos, other.pos)]

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

    def repulse_targets(self, unit_id: int) -> list[BattleUnit]:
        unit = self.unit(unit_id)
        if not unit.alive or not unit.can_repulse or unit.acted or 'repulse' in unit.spent_abilities or self.outcome:
            return []
        occupied = {other.pos for other in self.units if other.alive}
        return [other for other in self.units if other.alive and other.team != unit.team and other.stance is None
                and self.grid.distance(unit.pos, other.pos) == 1
                and (landing := self._repulse_destination(unit, other)) in self.terrain and landing not in occupied]

    @staticmethod
    def _repulse_destination(unit: BattleUnit, target: BattleUnit) -> Pos:
        return 2 * target.pos[0] - unit.pos[0], 2 * target.pos[1] - unit.pos[1]

    def repulse_preview(self, unit_id: int, target_id: int) -> Pos:
        target = self.unit(target_id)
        if target not in self.repulse_targets(unit_id):
            raise RuleError('Repulse needs an unused charge, an adjacent unanchored enemy and an empty landing hex.')
        return self._repulse_destination(self.unit(unit_id), target)

    def repulse(self, unit_id: int, target_id: int) -> None:
        self._repulse(self._actor(unit_id), self.unit(target_id))

    def _repulse(self, unit: BattleUnit, target: BattleUnit) -> None:
        target.pos = self.repulse_preview(unit.id, target.id)
        unit.spent_abilities += ('repulse',)
        unit.acted = unit.moved = True
        self.log.append(f'{unit.name} repulses {target.name} to {target.pos}.')

    def smoke_targets(self, unit_id: int) -> set[Pos]:
        unit = self.unit(unit_id)
        if not unit.alive or not unit.can_smoke or unit.acted or 'smoke' in unit.spent_abilities or self.outcome:
            return set()
        cloudy = {cloud.pos for cloud in self.smoke_clouds}
        return {pos for pos in self.terrain if pos not in cloudy and self.grid.distance(unit.pos, pos) <= 3
                and self.has_sight(unit.pos, pos)}

    def smoke_preview(self, unit_id: int, pos: Pos) -> SmokeCloud:
        if pos not in self.smoke_targets(unit_id):
            raise RuleError('Smoke needs an unused charge and a clear hex within three hexes.')
        return SmokeCloud(pos, self.unit(unit_id).team)

    def smoke(self, unit_id: int, pos: Pos) -> None:
        self._smoke(self._actor(unit_id), pos)

    def _smoke(self, unit: BattleUnit, pos: Pos) -> None:
        self.smoke_clouds.append(self.smoke_preview(unit.id, pos))
        unit.spent_abilities += ('smoke',)
        unit.acted = unit.moved = True
        self.log.append(f'{unit.name} screens {pos} with smoke until its next turn.')

    def rally_targets(self, unit_id: int) -> list[BattleUnit]:
        """Living pinned adjacent allies; clearing Pin never refreshes their orders."""
        unit = self.unit(unit_id)
        if not unit.alive or not unit.can_rally or unit.acted or self.outcome:
            return []
        return [other for other in self.units if other.alive and other.team == unit.team
                and other.pinned and self.grid.distance(unit.pos, other.pos) == 1]

    def rally_preview(self, unit_id: int, target_id: int) -> RallyPreview:
        target = self.unit(target_id)
        if target not in self.rally_targets(unit_id):
            raise RuleError('Rally needs a ready militia and an adjacent pinned ally.')
        released = replace(target, pinned=False)
        return RallyPreview(released.effective_move_range, frozenset(self._reachable(released)))

    def rally(self, unit_id: int, target_id: int) -> None:
        self._rally(self._actor(unit_id), self.unit(target_id))

    def _rally(self, unit: BattleUnit, target: BattleUnit) -> None:
        self.rally_preview(unit.id, target.id)
        target.pinned = False
        unit.acted = unit.moved = True
        self.log.append(f'{unit.name} rallies {target.name}; Pin is cleared.')

    def swap_targets(self, unit_id: int) -> list[BattleUnit]:
        """Adjacent living allies a ready Warden may replace, including spent allies."""
        unit = self.unit(unit_id)
        if not unit.alive or not unit.can_swap or unit.acted or self.outcome:
            return []
        return [other for other in self.units if other.alive and other.team == unit.team
                and self.grid.distance(unit.pos, other.pos) == 1]

    def swap(self, unit_id: int, target_id: int) -> None:
        """Exchange places, spending the Warden's order and the ally's remaining move."""
        self._swap(self._actor(unit_id), self.unit(target_id))

    def _swap(self, unit: BattleUnit, target: BattleUnit) -> None:
        if target not in self.swap_targets(unit.id):
            raise RuleError('A ready Warden can swap with an adjacent living ally.')
        unit.pos, target.pos = target.pos, unit.pos
        unit.acted = unit.moved = target.moved = True
        self.log.append(f'{unit.name} swaps places with {target.name}.')

    @property
    def evacuation_blocked_reason(self) -> str | None:
        if self.outcome is not None:
            return 'The battle is over.'
        if self.objective.kind != 'extract' or self.hero_id is None:
            return 'This battle has no cargo to evacuate.'
        hero = self.unit(self.hero_id)
        if not hero.alive:
            return 'The carrier has fallen.'
        if hero.acted:
            return 'The hero has already acted; evacuation needs an unspent action.'
        if hero.pos not in self.objective.exits:
            return 'Bring the hero to a marked exit.'
        if any(other.alive and other.team != hero.team and self.grid.distance(hero.pos, other.pos) == 1
               for other in self.units):
            return 'Clear adjacent enemies before evacuating.'
        return None

    def evacuate(self) -> None:
        """Spend the carrier's action at an uncontested exit; arrival alone never wins."""
        reason = self.evacuation_blocked_reason
        if reason is not None:
            raise RuleError(reason)
        hero = self.unit(self.hero_id)
        hero.acted = hero.moved = True
        self.outcome, self.outcome_reason = 'player', 'escape'
        self.log.append('The hero escapes with the recovered cargo. Surviving defenders withdraw.')

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

    def _caster(self, spell: str, caster_id: int | None) -> BattleUnit:
        if self.hero_id is None:
            raise RuleError('This army has no spellcasting hero or shared mana.')
        caster = self._actor(self.hero_id if caster_id is None else caster_id)
        learned = spell in self.spells if caster.id == self.hero_id else spell == 'heal' and caster.can_heal
        if spell not in SPELLS or not learned:
            raise RuleError('That spell has not been learned by this unit.')
        if caster.acted:
            raise RuleError('That unit has already acted.')
        if self.mana < self.spell_cost(spell):
            raise RuleError('Not enough mana.')
        return caster

    def spell_targets(self, spell: str, *, caster_id: int | None = None) -> list[BattleUnit]:
        """Legal targets for this ready caster, using the army's shared mana pool."""
        try:
            caster = self._caster(spell, caster_id)
        except RuleError:
            return []
        return [target for target in self.units if target.alive
                and HexGrid.distance(caster.pos, target.pos) <= 4
                and self.has_sight(caster.pos, target.pos)
                and (target.team != caster.team if spell == 'bolt'
                     else target.team == caster.team and target.hp < target.max_hp)]

    def spell_preview(self, spell: str, target_id: int, *, caster_id: int | None = None) -> int:
        """Actual health restored or removed by a legal spell, without spending it."""
        self._caster(spell, caster_id)
        target = self.unit(target_id)
        if target not in self.spell_targets(spell, caster_id=caster_id):
            raise RuleError('Choose a visible wounded ally for Heal or an enemy for Bolt within 4 hexes.')
        return min(self.spell_power[spell], target.max_hp - target.hp if spell == 'heal' else target.hp)

    def cast(self, spell: str, target_id: int, *, caster_id: int | None = None) -> None:
        """Cast with the hero, or let a capable Acolyte spend the same mana on Heal."""
        caster = self._caster(spell, caster_id)
        amount = self.spell_preview(spell, target_id, caster_id=caster.id)
        target = self.unit(target_id)
        self.mana -= self.spell_cost(spell)
        caster.acted = caster.moved = True
        if spell == 'bolt':
            target.hp -= amount
            self.log.append(f'Arcane Bolt strikes {target.name} for {amount}.')
        else:
            target.hp += amount
            self.log.append(f'Heal restores {amount} health to {target.name}.')
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
        if objective.kind == 'extract':
            if self.round >= objective.deadline:
                self.outcome, self.outcome_reason = 'enemy', 'deadline'
                self.log.append('Time ran out before the cargo could be evacuated.')
            return
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

    def _escape_costs(self) -> dict[Pos, float]:
        """Actual terrain and occupancy costs, compared by callers with the carrier’s move budget."""
        hero = self.unit(self.hero_id)
        occupied = {other.pos for other in self.units if other.alive and other.id != hero.id}
        costs = self.grid.reachable(hero.pos, 100, blocked=occupied,
                                    cost=lambda pos: 2 if self.terrain[pos] in ('forest', 'marsh') and not hero.terrain_walk else 1)
        return {pos: costs[pos] for pos in self.objective.exits if pos in costs}

    def _intercept_carrier(self, unit: BattleUnit) -> None:
        """Hold an exit or cut off the carrier's shortest currently open route."""
        hero = self.unit(self.hero_id)
        if hero in self.targets(unit.id) and self.preview(unit.id, hero.id)[0] == hero.hp:
            return
        if unit.moved or any(self.grid.distance(unit.pos, exit) <= 1 for exit in self.objective.exits):
            return
        costs = self._escape_costs()
        exit = min(self.objective.exits, key=lambda pos: (costs.get(pos, 100), self.grid.distance(hero.pos, pos), pos))
        choices = self.reachable(unit.id) | {unit.pos}
        destination = min(choices, key=lambda pos: (self.grid.distance(pos, exit) > 1,
                          self.grid.distance(pos, exit), self.grid.distance(pos, hero.pos) > unit.attack_range,
                          self.terrain[pos] not in ('forest', 'hills'), pos))
        if destination != unit.pos:
            self._move(unit, destination)

    def _withdraw(self, unit: BattleUnit) -> None:
        """Mobile ranged troops spend their unused move to reduce immediate exposure."""
        if self.objective.kind == 'hold' and (unit.team == 'enemy' or unit.pos == self.objective.target):
            return
        if self.objective.kind == 'extract' and unit.team == 'enemy' and any(
                self.grid.distance(unit.pos, exit) <= 1 for exit in self.objective.exits):
            return
        reachable = self.reachable(unit.id)
        enemies = [other for other in self.units if other.alive and other.team != unit.team]
        if not reachable or not enemies:
            return
        def exposure(pos):
            distances = [(other, self.grid.distance(pos, other.pos)) for other in enemies]
            return (sum(distance <= other.attack_range + other.effective_move_range for other, distance in distances),
                    -min(distance for _, distance in distances), self.terrain[pos] not in ('forest', 'hills'), pos)
        destination = min(reachable | {unit.pos}, key=exposure)
        if destination != unit.pos:
            self._move(unit, destination)

    def _useful_repulse(self, unit: BattleUnit, target: BattleUnit) -> bool:
        destination = self.repulse_preview(unit.id, target.id)
        if self.objective.kind == 'hold':
            seal = self.objective.target
            return (self.grid.distance(target.pos, seal) <= 1 < self.grid.distance(destination, seal)
                    if unit.team == 'player' else target.pos == seal)
        if self.objective.kind == 'extract':
            hero = self.unit(self.hero_id)
            if unit.team == 'enemy':
                return target.id == hero.id and min(self.grid.distance(destination, pos) for pos in self.objective.exits) > min(
                    self.grid.distance(target.pos, pos) for pos in self.objective.exits)
            approaches = self.reachable(hero.id) | {hero.pos}
            return not hero.acted and any(pos in approaches and self.grid.distance(target.pos, pos) <= 1
                       < self.grid.distance(destination, pos) for pos in self.objective.exits)
        # In a rout, clear immediate pressure from a wounded ally; never push
        # a foe closer to the hero while doing so.
        if self.hero_id is not None and unit.team == 'player':
            hero = self.unit(self.hero_id)
            if self.grid.distance(destination, hero.pos) < self.grid.distance(target.pos, hero.pos):
                return False
        return any(ally.alive and ally.team == unit.team and ally.hp * 2 <= ally.max_hp
                   and self.grid.distance(target.pos, ally.pos) == 1 < self.grid.distance(destination, ally.pos)
                   for ally in self.units)

    def _useful_rally(self, unit: BattleUnit, target: BattleUnit) -> bool:
        current = self.reachable(target.id) | {target.pos}
        extra = self.rally_preview(unit.id, target.id).reachable - current
        if not extra:
            return False
        foes = [foe for foe in self.units if foe.alive and foe.team != target.team]
        if self.objective.kind == 'extract' and target.id == self.hero_id and not target.acted:
            return any(pos in extra and not any(self.grid.distance(pos, foe.pos) <= 1 for foe in foes)
                       for pos in self.objective.exits)
        if self.objective.kind == 'hold':
            goal = self.objective.target
            if min(self.grid.distance(pos, goal) for pos in extra) < min(self.grid.distance(pos, goal) for pos in current):
                return True
        if any(self._targets_from(target, pos) for pos in extra) and not any(self._targets_from(target, pos) for pos in current):
            return True
        if target.skirmisher and foes:
            def exposure(pos):
                return sum(self.grid.distance(pos, foe.pos) <= foe.attack_range + foe.effective_move_range for foe in foes)
            return min(map(exposure, extra)) < min(map(exposure, current))
        return False

    def _smoke_choice(self, unit: BattleUnit) -> Pos | None:
        choices = self.smoke_targets(unit.id)
        if not choices:
            return None
        living = [other for other in self.units if other.alive]
        lanes = [(shooter, target) for shooter in living if shooter.attack_range > 1
                 and (shooter.team != unit.team or not shooter.acted)
                 for target in living if target.team != shooter.team
                 and self.grid.distance(shooter.pos, target.pos) <= shooter.attack_range
                 and self.has_sight(shooter.pos, target.pos)]
        friendly_magic = []
        if unit.team == 'player' and self.hero_id is not None:
            for caster in living:
                if caster.team == unit.team and (caster.id == self.hero_id or caster.can_heal):
                    for spell in ('bolt', 'heal'):
                        friendly_magic.extend((caster.pos, target.pos, self.spell_preview(spell, target.id, caster_id=caster.id))
                                              for target in self.spell_targets(spell, caster_id=caster.id))
        clouds = {cloud.pos for cloud in self.smoke_clouds}
        def benefit(pos):
            smoke = clouds | {pos}
            score = sum(self._damage(shooter, target) * (1 if shooter.team != unit.team else -1)
                        for shooter, target in lanes
                        if not line_of_sight(self.terrain, shooter.pos, target.pos, smoke=smoke))
            return score - sum(amount for source, target, amount in friendly_magic
                               if not line_of_sight(self.terrain, source, target, smoke=smoke))
        best = min(choices, key=lambda pos: (-benefit(pos), pos))
        attack_value = max((self.preview(unit.id, target.id)[0] for target in self.targets(unit.id)), default=0)
        return best if benefit(best) > attack_value else None

    def _control_orders(self, team: str) -> None:
        for unit in self.units:
            if unit.team == team:
                targets = [target for target in self.rally_targets(unit.id) if self._useful_rally(unit, target)]
                if targets:
                    self._rally(unit, min(targets, key=lambda target: (target.id != self.hero_id, target.id)))
        for unit in self.units:
            if unit.team == team:
                targets = [target for target in self.repulse_targets(unit.id) if self._useful_repulse(unit, target)]
                if targets:
                    self._repulse(unit, min(targets, key=lambda target: target.id))
        for unit in self.units:
            if unit.team == team:
                pos = self._smoke_choice(unit)
                if pos is not None:
                    self._smoke(unit, pos)

    def _play_team(self, team: str) -> None:
        self._control_orders(team)
        for unit in self.units:
            if self.outcome:
                break
            if unit.team != team or not unit.alive or unit.acted:
                continue
            if unit.kind == 'hero':
                if self.objective.kind == 'extract':
                    if self.evacuation_blocked_reason is None:
                        self.evacuate()
                        continue
                    escapes = [pos for pos in self.objective.exits if pos in self.reachable(unit.id)
                               and not any(other.alive and other.team == 'enemy' and self.grid.distance(pos, other.pos) <= 1
                                           for other in self.units)]
                    if escapes:
                        self.move(unit.id, min(escapes))
                        self.evacuate()
                        continue
                injured = [u for u in self.spell_targets('heal') if u.max_hp - u.hp >= 12]
                if 'heal' in self.spells and self.mana >= self.spell_cost('heal') and injured:
                    self.cast('heal', min(injured, key=lambda u: u.hp / u.max_hp).id)
                    continue
                enemies = self.spell_targets('bolt')
                if 'bolt' in self.spells and self.mana >= self.spell_cost('bolt') and enemies:
                    self.cast('bolt', min(enemies, key=lambda u: u.hp).id)
                    continue
            if unit.can_swap:
                enemies = [other for other in self.units if other.alive and other.team != team]
                endangered = [ally for ally in self.swap_targets(unit.id)
                              if ally.hp * 2 <= ally.max_hp and ally.hp < unit.hp
                              and any(self.grid.distance(ally.pos, enemy.pos) < self.grid.distance(unit.pos, enemy.pos)
                                      and self.grid.distance(ally.pos, enemy.pos) <= enemy.attack_range + enemy.effective_move_range
                                      for enemy in enemies)]
                if endangered:
                    self._swap(unit, min(endangered, key=lambda ally: (ally.hp / ally.max_hp, ally.id)))
                    continue
            if unit.can_heal:
                injured = [target for target in self.spell_targets('heal', caster_id=unit.id)
                           if target.max_hp - target.hp >= 8]
                if injured:
                    self.cast('heal', min(injured, key=lambda target: (target.hp / target.max_hp, target.id)).id,
                              caster_id=unit.id)
                    continue
            defending_exit = team == 'enemy' and self.objective.kind == 'extract'
            if defending_exit:
                self._intercept_carrier(unit)
            defending_seal = team == 'enemy' and self.objective.kind == 'hold'
            if defending_seal:
                self._contest_seal(unit)
            targets = self.targets(unit.id)
            if not targets and not unit.moved and not defending_seal and not defending_exit:
                enemies = [u for u in self.units if u.alive and u.team != team]
                reachable = self.reachable(unit.id)
                if reachable and enemies:
                    def score(pos):
                        distances = [HexGrid.distance(pos, enemy.pos) for enemy in enemies]
                        distance = min(distances)
                        can_attack = bool(self._targets_from(unit, pos))
                        cover = self.terrain[pos] in ('forest', 'hills')
                        landing_risk = sum(self._damage(enemy, replace(unit, pos=pos)) for enemy in enemies
                                           if self.grid.distance(pos, enemy.pos) <= enemy.attack_range
                                           and (enemy.attack_range == 1 or self.has_sight(enemy.pos, pos))) if unit.can_fly else 0
                        return (not can_attack, max(0, distance - unit.attack_range), landing_risk, not cover,
                                -distance if can_attack else distance, pos)
                    destination = min(reachable | {unit.pos}, key=score)
                    if destination != unit.pos:
                        if team == 'player':
                            self.move(unit.id, destination)
                        else:
                            self._move(unit, destination)
                targets = self.targets(unit.id)
            if targets:
                if defending_exit:
                    target = min(targets, key=lambda other: (other.id != self.hero_id, other.hp, other.id))
                elif defending_seal:
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
                slows_escape = (defending_exit and target.id == self.hero_id and any(
                    max(1, target.effective_move_range - 2) < cost <= target.effective_move_range
                    for cost in self._escape_costs().values()))
                use_pin = (target in self.pin_targets(unit.id) and (slows_escape or slow_stops_approach or target.kind == 'ranger' and distance > 1)
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
                if unit.kind == 'ranger':
                    self._withdraw(unit)
            elif unit.kind == 'pikeman':
                self._guard(unit)

    def end_turn(self) -> None:
        if self.outcome:
            raise RuleError('The battle is over.')
        self.smoke_clouds = [cloud for cloud in self.smoke_clouds if cloud.expires_before_team != 'enemy']
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
            self.smoke_clouds = [cloud for cloud in self.smoke_clouds if cloud.expires_before_team != 'player']
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
                'objective': asdict(self.objective), 'outcome_reason': self.outcome_reason,
                'sight_rules': self.sight_rules, 'smoke_clouds': [asdict(cloud) for cloud in self.smoke_clouds]}

    @classmethod
    def from_dict(cls, data: dict) -> Battle:
        return cls(units=[BattleUnit(**{**u, 'pos': tuple(u['pos']), 'abilities': tuple(u['abilities']), 'spent_abilities': tuple(u['spent_abilities'])}) for u in data['units']],
                   terrain={tuple(t['pos']): t['kind'] for t in data['terrain']},
                   mana=data['mana'], spells=set(data['spells']), round=data['round'],
                   outcome=data['outcome'], log=list(data['log']),
                   spell_costs=dict(data['spell_costs']), spell_power=dict(data['spell_power']), hero_id=data['hero_id'],
                   objective=BattleObjective(**{**data['objective'], 'target': tuple(data['objective']['target']) if data['objective']['target'] is not None else None,
                                                'exits': tuple(tuple(pos) for pos in data['objective']['exits'])}),
                   outcome_reason=data['outcome_reason'], sight_rules=data['sight_rules'],
                   smoke_clouds=[SmokeCloud(tuple(cloud['pos']), cloud['expires_before_team']) for cloud in data['smoke_clouds']])
