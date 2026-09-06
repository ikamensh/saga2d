"""World state and every rule that changes it.

Pure Python — no rendering, no randomness except what the caller passes
in.  Both the UI and the AI drive the game exclusively through
:class:`World` methods, so a rule lives in exactly one place.

Positions are ``(x, y)`` grid coordinates; adjacency is 8-directional
(Chebyshev distance), as in Polytopia.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterator

from tribes.rules import (
    CITY_BORDER_GROWTH_LEVEL, CITY_DEFENSE_BONUS, EXPLORER_RADIUS, HARVEST, HEAL_IN_TERRITORY, HEAL_OUTSIDE,
    LEVEL_REWARDS, MAX_ROUNDS, MEDITATION_HEAL, MOUNTAIN_DEFENSE_BONUS, REWARD_PARK_SCORE, REWARD_POPULATION, REWARD_STARS, REWARDS,
    RUIN_POPULATION, RUIN_TREASURE, RUIN_VISION_RADIUS, STARTING_STARS, TECHS, TRIBES, UNITS, WALL_DEFENSE_BONUS,
    Discovery, Resource, Reward, Tech, Terrain, UnitType, tech_cost,
)

Pos = tuple[int, int]


def _round_half_up(value: float) -> int:
    return int(value + 0.5)


class RuleError(Exception):
    """An action that the rules forbid.  The message says why."""


@dataclass
class Tile:
    x: int
    y: int
    terrain: Terrain
    resource: Resource | None = None
    harvested: bool = False
    village: bool = False
    city_id: int | None = None
    owner_city: int | None = None
    ruin: bool = False  # ancient ruins: the first unit to walk here finds something

    @property
    def pos(self) -> Pos:
        return (self.x, self.y)


@dataclass
class City:
    id: int
    name: str
    tribe: int
    x: int
    y: int
    level: int = 1
    population: int = 0
    capital: bool = False
    workshop: bool = False
    walls: bool = False
    border_bonus: int = 0
    parks: int = 0
    pending_reward: bool = False  # reached a new level; its owner must pick a reward before ending the turn

    @property
    def pos(self) -> Pos:
        return (self.x, self.y)

    @property
    def radius(self) -> int:
        return (2 if self.level >= CITY_BORDER_GROWTH_LEVEL else 1) + self.border_bonus

    @property
    def next_level_population(self) -> int:
        return self.level + 1

    @property
    def income(self) -> int:
        return self.level + (1 if self.capital else 0) + (1 if self.workshop else 0)

    @property
    def has_wall(self) -> bool:
        return self.walls


@dataclass
class Unit:
    id: int
    type: UnitType
    tribe: int
    x: int
    y: int
    hp: int
    moved: bool = False
    attacked: bool = False
    done: bool = False
    kills: int = 0

    @property
    def pos(self) -> Pos:
        return (self.x, self.y)

    @property
    def info(self):
        return UNITS[self.type]

    @property
    def max_hp(self) -> int:
        return self.info.hp

    @property
    def can_move(self) -> bool:
        if self.done or self.moved:
            return False
        return not self.attacked or self.info.escape

    @property
    def can_attack(self) -> bool:
        return not self.done and not self.attacked

    @property
    def can_act(self) -> bool:
        return self.can_move or self.can_attack

    @property
    def idle(self) -> bool:
        """Did nothing this turn (heals at the start of the next)."""
        return not self.moved and not self.attacked


@dataclass
class Tribe:
    id: int
    name: str
    color: tuple[int, int, int]
    human: bool = False
    stars: int = STARTING_STARS
    techs: set[Tech] = field(default_factory=set)
    explored: set[Pos] = field(default_factory=set)
    alive: bool = True
    surrendered: bool = False


@dataclass
class CombatResult:
    attacker: Unit
    defender: Unit
    damage_dealt: int
    damage_taken: int
    defender_killed: bool
    attacker_killed: bool


@dataclass(frozen=True)
class Finding:
    """What a unit found in ruins; collected by the UI with :meth:`World.take_findings`."""

    pos: Pos
    kind: Discovery
    text: str


class World:
    """Parameters:
        tribe_count: How many tribes play; tribe ``i`` takes its name, colour
                     and starting tech from ``TRIBES`` rotated by *first_tribe*,
                     so the player (always tribe 0) can play any of them.
        human:       Index of the human tribe, or ``None`` for AI-only games.
    """

    def __init__(self, size: int, tiles: list[list[Tile]], tribe_count: int, human: int | None = 0, *, first_tribe: int = 0) -> None:
        self.size = size
        self.tiles = tiles
        infos = [TRIBES[(first_tribe + i) % len(TRIBES)] for i in range(tribe_count)]
        self.tribes = [Tribe(i, info.name, info.color, human=(i == human), techs={info.tech}) for i, info in enumerate(infos)]
        self.cities: dict[int, City] = {}
        self.units: dict[int, Unit] = {}
        self.current = 0
        self.round = 1
        self.winner: int | None = None
        self.log: list[str] = []
        self.findings: list[Finding] = []
        self._next_id = 1

    # -- Queries -----------------------------------------------------------------

    def in_bounds(self, pos: Pos) -> bool:
        return 0 <= pos[0] < self.size and 0 <= pos[1] < self.size

    def tile(self, pos: Pos) -> Tile:
        return self.tiles[pos[1]][pos[0]]

    def all_tiles(self) -> Iterator[Tile]:
        for row in self.tiles:
            yield from row

    def neighbors(self, pos: Pos, radius: int = 1) -> list[Pos]:
        """Tiles within Chebyshev *radius*, orthogonal ones first (straighter paths)."""
        x, y = pos
        cells = [
            (nx, ny)
            for ny in range(y - radius, y + radius + 1)
            for nx in range(x - radius, x + radius + 1)
            if (nx, ny) != pos and self.in_bounds((nx, ny))
        ]
        cells.sort(key=lambda p: abs(p[0] - x) + abs(p[1] - y))
        return cells

    @staticmethod
    def distance(a: Pos, b: Pos) -> int:
        return max(abs(a[0] - b[0]), abs(a[1] - b[1]))

    def unit_at(self, pos: Pos) -> Unit | None:
        return next((u for u in self.units.values() if u.pos == pos), None)

    def city_at(self, pos: Pos) -> City | None:
        city_id = self.tile(pos).city_id
        return self.cities[city_id] if city_id is not None else None

    def owner_of(self, pos: Pos) -> int | None:
        """Tribe id owning the territory at *pos*, or ``None``."""
        city_id = self.tile(pos).owner_city
        return self.cities[city_id].tribe if city_id is not None else None

    @property
    def current_tribe(self) -> Tribe:
        return self.tribes[self.current]

    def tribe_units(self, tribe: int) -> list[Unit]:
        return [u for u in self.units.values() if u.tribe == tribe]

    def tribe_cities(self, tribe: int) -> list[City]:
        return [c for c in self.cities.values() if c.tribe == tribe]

    def capital_of(self, tribe: int) -> City | None:
        return next((c for c in self.cities.values() if c.tribe == tribe and c.capital), None)

    def income(self, tribe: int) -> int:
        return sum(self.city_income(c) for c in self.tribe_cities(tribe))

    def city_income(self, city: City) -> int:
        """The city's own income plus what its tribe's techs add (Navigation on the coast, Trade everywhere)."""
        bonus = int(self.has_tech(city.tribe, Tech.TRADE))
        if self.has_tech(city.tribe, Tech.NAVIGATION) and self.is_coastal(city.pos):
            bonus += 1
        return city.income + bonus

    def is_coastal(self, pos: Pos) -> bool:
        return any(self.tile(n).terrain is Terrain.WATER for n in self.neighbors(pos))

    def unit_cap(self, tribe: int) -> int:
        return sum(c.level + 1 for c in self.tribe_cities(tribe))

    def has_tech(self, tribe: int, tech: Tech | None) -> bool:
        return tech is None or tech in self.tribes[tribe].techs

    def explored(self, tribe: int, pos: Pos) -> bool:
        return pos in self.tribes[tribe].explored

    def score(self, tribe: int) -> int:
        return sum(self.score_breakdown(tribe).values())

    def score_breakdown(self, tribe: int, *, final: bool = False) -> dict[str, int]:
        """Empire points, with victory and pace bonuses only for a finished game.

        The live empire score still decides round-limit wins. Banking stars or
        farming kills earns no extra points; end bonuses reward winning promptly.
        Compare final scores on the same map size and with the same tribe count.
        """
        if final and self.winner is None:
            raise RuleError("The game is not over")
        t = self.tribes[tribe]
        cities = self.tribe_cities(tribe)
        territory = sum(1 for tile in self.all_tiles() if self.owner_of(tile.pos) == tribe)
        parts = {
            "Cities": sum(100 * c.level for c in cities),
            "Parks": sum(REWARD_PARK_SCORE * c.parks for c in cities),
            "Technology": 20 * len(t.techs),
            "Army": sum(5 * u.info.cost for u in self.tribe_units(tribe)),
            "Territory": 5 * territory,
        }
        if final:
            won = self.winner == tribe
            parts["Victory"] = 1000 if won else 0
            parts["Early finish"] = 50 * max(0, MAX_ROUNDS - self.round) if won else 0
        return parts

    # -- Setup -------------------------------------------------------------------

    def found_city(self, tribe: int, pos: Pos, name: str, *, capital: bool = False) -> City:
        tile = self.tile(pos)
        city = City(self._new_id(), name, tribe, pos[0], pos[1], capital=capital)
        self.cities[city.id] = city
        tile.city_id = city.id
        tile.village = False
        self._claim_territory(city)
        self.explore(tribe, pos, 2)
        return city

    def spawn_unit(self, tribe: int, unit_type: UnitType, pos: Pos, *, fresh: bool = True) -> Unit:
        if self.unit_at(pos) is not None:
            raise RuleError("That tile is occupied")
        unit = Unit(self._new_id(), unit_type, tribe, pos[0], pos[1], UNITS[unit_type].hp)
        if not fresh:
            unit.moved = unit.attacked = unit.done = True
        self.units[unit.id] = unit
        self.explore(tribe, pos, self._vision(unit))
        return unit

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def _claim_territory(self, city: City) -> None:
        """A city always owns its own tile; around it, it claims only unowned land."""
        self.tile(city.pos).owner_city = city.id
        for pos in self.neighbors(city.pos, city.radius):
            tile = self.tile(pos)
            if tile.owner_city is None:
                tile.owner_city = city.id

    def explore(self, tribe: int, pos: Pos, radius: int) -> None:
        explored = self.tribes[tribe].explored
        explored.add(pos)
        explored.update(self.neighbors(pos, radius))

    def _vision(self, unit: Unit) -> int:
        return 2 if self.tile(unit.pos).terrain is Terrain.MOUNTAIN else 1

    # -- Movement ----------------------------------------------------------------

    def can_enter(self, unit: Unit, pos: Pos) -> bool:
        tile = self.tile(pos)
        if tile.terrain is Terrain.WATER:
            return False
        if tile.terrain is Terrain.MOUNTAIN and not self.has_tech(unit.tribe, Tech.CLIMBING):
            return False
        return self.unit_at(pos) is None

    def _stops_movement(self, unit: Unit, pos: Pos) -> bool:
        terrain = self.tile(pos).terrain
        if terrain is Terrain.MOUNTAIN or (terrain is Terrain.FOREST and not self.has_tech(unit.tribe, Tech.FORESTRY)):
            return True
        return any((n := self.unit_at(p)) is not None and n.tribe != unit.tribe for p in self.neighbors(pos))

    def movement(self, unit: Unit) -> int:
        """Tiles the unit may cross this turn: its own speed, plus one on roads (own territory)."""
        roads = self.has_tech(unit.tribe, Tech.ROADS) and self.owner_of(unit.pos) == unit.tribe
        return unit.info.movement + int(roads)

    def reachable(self, unit: Unit) -> dict[Pos, Pos]:
        """Every tile *unit* can move to this turn, mapped to the tile before it on the path."""
        if not unit.can_move:
            return {}
        parents: dict[Pos, Pos] = {}
        budget_left: dict[Pos, int] = {unit.pos: self.movement(unit)}
        queue: deque[Pos] = deque([unit.pos])
        while queue:
            pos = queue.popleft()
            budget = budget_left[pos]
            if budget <= 0:
                continue
            for nxt in self.neighbors(pos):
                if not self.can_enter(unit, nxt):
                    continue
                left = 0 if self._stops_movement(unit, nxt) else budget - 1
                if nxt in budget_left and budget_left[nxt] >= left:
                    continue
                budget_left[nxt] = left
                parents[nxt] = pos
                queue.append(nxt)
        return parents

    def path_to(self, unit: Unit, dest: Pos) -> list[Pos]:
        parents = self.reachable(unit)
        if dest not in parents:
            raise RuleError("Cannot reach that tile")
        path = [dest]
        while path[-1] != unit.pos:
            path.append(parents[path[-1]])
        return path[::-1]

    def move(self, unit: Unit, dest: Pos) -> list[Pos]:
        """Move *unit* to *dest*; returns the path taken (starting tile first)."""
        self._check_turn(unit.tribe)
        path = self.path_to(unit, dest)
        unit.x, unit.y = dest
        unit.moved = True
        if unit.attacked:
            unit.done = True
        for pos in path:
            self.explore(unit.tribe, pos, self._vision(unit) if pos == dest else 1)
        self._arrive(unit)
        return path

    def _arrive(self, unit: Unit) -> None:
        if self.tile(unit.pos).ruin:
            self._explore_ruin(unit)

    def _explore_ruin(self, unit: Unit) -> None:
        """The ruins vanish and the tribe gains something; which thing depends on
        the spot and the round, so it is unknowable in advance but reproducible."""
        tile = self.tile(unit.pos)
        tile.ruin = False
        tribe = self.tribes[unit.tribe]
        kind = list(Discovery)[(unit.x * 31 + unit.y * 17 + self.round * 7) % len(Discovery)]
        learnable = sorted(
            (t for t in TECHS if t not in tribe.techs and (TECHS[t].requires is None or TECHS[t].requires in tribe.techs)),
            key=lambda t: (TECHS[t].tier, t.value),
        )
        if kind is Discovery.KNOWLEDGE and not learnable:
            kind = Discovery.TREASURE
        if kind is Discovery.KNOWLEDGE:
            tribe.techs.add(learnable[0])
            text = f"Ancient knowledge: {learnable[0].value.title()}"
        elif kind is Discovery.GROWTH:
            city = min(self.tribe_cities(unit.tribe), key=lambda c: self.distance(c.pos, unit.pos))
            self._grow(city, RUIN_POPULATION)
            text = f"Settlers join {city.name}: +{RUIN_POPULATION} pop"
        elif kind is Discovery.VISION:
            self.explore(unit.tribe, unit.pos, RUIN_VISION_RADIUS)
            text = "A map of the surrounding land"
        else:
            tribe.stars += RUIN_TREASURE
            text = f"Treasure: +{RUIN_TREASURE}★"
        self.findings.append(Finding(unit.pos, kind, text))
        self.log.append(f"{tribe.name} explored ruins: {text}")

    def take_findings(self) -> list[Finding]:
        """Findings since the last call (the UI shows them once)."""
        found, self.findings = self.findings, []
        return found

    # -- Combat ------------------------------------------------------------------

    def attack_targets(self, unit: Unit) -> list[Unit]:
        if not unit.can_attack:
            return []
        return [
            other for other in self.units.values()
            if other.tribe != unit.tribe and self.distance(unit.pos, other.pos) <= unit.info.range
            and self.explored(unit.tribe, other.pos)
        ]

    def defense_bonus(self, unit: Unit) -> float:
        city = self.city_at(unit.pos)
        if city is not None and city.tribe == unit.tribe:
            return WALL_DEFENSE_BONUS if city.has_wall else CITY_DEFENSE_BONUS
        if self.tile(unit.pos).terrain is Terrain.MOUNTAIN:
            return MOUNTAIN_DEFENSE_BONUS
        return 1.0

    def combat_preview(self, attacker: Unit, defender: Unit) -> tuple[int, int]:
        """``(damage to defender, damage to attacker)`` for an attack, before retaliation checks."""
        attack_force = attacker.info.attack * attacker.hp / attacker.max_hp
        defense_force = defender.info.defense * defender.hp / defender.max_hp * self.defense_bonus(defender)
        total = attack_force + defense_force
        dealt = _round_half_up(attack_force / total * attacker.info.attack * 4.5)
        taken = _round_half_up(defense_force / total * defender.info.defense * 4.5)
        return max(1, dealt), taken

    def attack(self, attacker: Unit, defender: Unit) -> CombatResult:
        self._check_turn(attacker.tribe)
        if not attacker.can_attack:
            raise RuleError("Already attacked this turn")
        if defender not in self.attack_targets(attacker):
            raise RuleError("Target out of range")
        dealt, taken = self.combat_preview(attacker, defender)
        defender.hp -= dealt
        defender_killed = defender.hp <= 0
        attacker_killed = False
        if defender_killed:
            self._kill(defender)
            attacker.kills += 1
            if attacker.info.range == 1 and self.can_enter(attacker, defender.pos):
                self.move_free(attacker, defender.pos)
            taken = 0
        elif self.distance(attacker.pos, defender.pos) <= defender.info.range:
            attacker.hp -= taken
            attacker_killed = attacker.hp <= 0
            if attacker_killed:
                self._kill(attacker)
        else:
            taken = 0
        attacker.attacked = True
        if defender_killed and attacker.info.persist:
            attacker.attacked = False  # persist: may strike again, but the kill used up its move
            attacker.moved = True
        elif not (attacker.info.escape and not attacker.moved):
            attacker.done = True  # escape units may still move away
        self.log.append(f"{self.tribes[attacker.tribe].name} {attacker.type.value} hit {defender.type.value} for {dealt}")
        self._check_elimination()
        return CombatResult(attacker, defender, dealt, taken, defender_killed, attacker_killed)

    def move_free(self, unit: Unit, pos: Pos) -> None:
        """Relocate without spending movement (used when a melee kill advances)."""
        unit.x, unit.y = pos
        self.explore(unit.tribe, pos, self._vision(unit))
        self._arrive(unit)

    def _kill(self, unit: Unit) -> None:
        del self.units[unit.id]
        unit.hp = 0

    # -- Cities ------------------------------------------------------------------

    def can_capture(self, unit: Unit) -> bool:
        tile = self.tile(unit.pos)
        if unit.moved or unit.attacked or unit.done:
            return False
        if tile.village:
            return True
        city = self.city_at(unit.pos)
        return city is not None and city.tribe != unit.tribe

    def capture(self, unit: Unit) -> City:
        self._check_turn(unit.tribe)
        if not self.can_capture(unit):
            raise RuleError("Nothing to capture here")
        tile = self.tile(unit.pos)
        if tile.village:
            city = self.found_city(unit.tribe, unit.pos, self._city_name())
            self.log.append(f"{self.tribes[unit.tribe].name} founded {city.name}")
        else:
            city = self.city_at(unit.pos)
            assert city is not None
            self.log.append(f"{self.tribes[unit.tribe].name} captured {city.name} from {self.tribes[city.tribe].name}")
            city.tribe = unit.tribe
            city.capital = False
            self._claim_territory(city)
            self.explore(unit.tribe, city.pos, city.radius)
        unit.done = unit.moved = unit.attacked = True
        self._check_elimination()
        return city

    def _city_name(self) -> str:
        from tribes.rules import CITY_NAMES

        used = {c.name for c in self.cities.values()}
        return next((n for n in CITY_NAMES if n not in used), f"City {len(self.cities) + 1}")

    def can_train(self, city: City, unit_type: UnitType) -> str | None:
        """``None`` if allowed, else the reason it is not."""
        info = UNITS[unit_type]
        tribe = self.tribes[city.tribe]
        if not self.has_tech(city.tribe, info.tech):
            return f"Requires {info.tech.value.title()}"
        if tribe.stars < info.cost:
            return f"Costs {info.cost}★"
        if len(self.tribe_units(city.tribe)) >= self.unit_cap(city.tribe):
            return "Unit limit reached"
        if self.unit_at(city.pos) is not None:
            return "City tile occupied"
        return None

    def train(self, city: City, unit_type: UnitType) -> Unit:
        self._check_turn(city.tribe)
        reason = self.can_train(city, unit_type)
        if reason is not None:
            raise RuleError(reason)
        self.tribes[city.tribe].stars -= UNITS[unit_type].cost
        return self.spawn_unit(city.tribe, unit_type, city.pos, fresh=False)

    def harvest_cost(self, tribe: int, resource: Resource) -> int:
        return max(1, HARVEST[resource].cost - int(self.has_tech(tribe, Tech.CONSTRUCTION)))

    def harvest_yield(self, tribe: int, resource: Resource) -> int:
        return HARVEST[resource].population + int(resource is Resource.FISH and self.has_tech(tribe, Tech.AQUACULTURE))

    def can_harvest(self, tribe: int, pos: Pos) -> str | None:
        tile = self.tile(pos)
        if tile.resource is None or tile.harvested:
            return "Nothing to harvest"
        if self.owner_of(pos) != tribe:
            return "Not your territory"
        info = HARVEST[tile.resource]
        if not self.has_tech(tribe, info.tech):
            return f"Requires {info.tech.value.title()}"
        cost = self.harvest_cost(tribe, tile.resource)
        if self.tribes[tribe].stars < cost:
            return f"Costs {cost}★"
        return None

    def harvest(self, tribe: int, pos: Pos) -> City:
        self._check_turn(tribe)
        reason = self.can_harvest(tribe, pos)
        if reason is not None:
            raise RuleError(reason)
        tile = self.tile(pos)
        assert tile.resource is not None
        self.tribes[tribe].stars -= self.harvest_cost(tribe, tile.resource)
        tile.harvested = True
        city = self.cities[tile.owner_city]  # type: ignore[index]
        self._grow(city, self.harvest_yield(tribe, tile.resource))
        return city

    def _grow(self, city: City, population: int) -> None:
        city.population += population
        while city.population >= city.next_level_population:
            city.population -= city.next_level_population
            city.level += 1
            city.pending_reward = True
            self._claim_territory(city)
            self.explore(city.tribe, city.pos, city.radius)
            self.log.append(f"{self.tribes[city.tribe].name}'s {city.name} grew to level {city.level}")

    # -- Level rewards -------------------------------------------------------------

    def reward_options(self, city: City) -> tuple[Reward, Reward]:
        """The two rewards a city of this level picks between."""
        return LEVEL_REWARDS[min(city.level, max(LEVEL_REWARDS))]

    def pending_rewards(self, tribe: int) -> list[City]:
        return [c for c in self.tribe_cities(tribe) if c.pending_reward]

    def choose_reward(self, city: City, reward: Reward) -> None:
        self._check_turn(city.tribe)
        if not city.pending_reward:
            raise RuleError(f"{city.name} has no reward to choose")
        if reward not in self.reward_options(city):
            raise RuleError(f"{REWARDS[reward].name} is not on offer at level {city.level}")
        city.pending_reward = False
        tribe = self.tribes[city.tribe]
        if reward is Reward.WORKSHOP:
            city.workshop = True
        elif reward is Reward.EXPLORER:
            self.explore(city.tribe, city.pos, EXPLORER_RADIUS)
        elif reward is Reward.WALLS:
            city.walls = True
        elif reward is Reward.RESOURCES:
            tribe.stars += REWARD_STARS
        elif reward is Reward.BORDER:
            city.border_bonus += 1
            self._claim_territory(city)
            self.explore(city.tribe, city.pos, city.radius)
        elif reward is Reward.POPULATION:
            self._grow(city, REWARD_POPULATION)  # may reach the next level, and offer again
        elif reward is Reward.PARK:
            city.parks += 1
        self.log.append(f"{tribe.name}'s {city.name} chose {REWARDS[reward].name}")

    # -- Research ----------------------------------------------------------------

    def tech_cost(self, tribe: int, tech: Tech) -> int:
        return tech_cost(tech, len(self.tribe_cities(tribe)))

    def can_research(self, tribe: int, tech: Tech) -> str | None:
        t = self.tribes[tribe]
        if tech in t.techs:
            return "Already known"
        requires = TECHS[tech].requires
        if requires is not None and requires not in t.techs:
            return f"Requires {requires.value.title()}"
        cost = self.tech_cost(tribe, tech)
        if t.stars < cost:
            return f"Costs {cost}★"
        return None

    def research(self, tribe: int, tech: Tech) -> None:
        self._check_turn(tribe)
        reason = self.can_research(tribe, tech)
        if reason is not None:
            raise RuleError(reason)
        self.tribes[tribe].stars -= self.tech_cost(tribe, tech)
        self.tribes[tribe].techs.add(tech)
        self.log.append(f"{self.tribes[tribe].name} learned {tech.value.title()}")
        if tech is Tech.CARTOGRAPHY:
            for tile in self.all_tiles():
                if tile.terrain is Terrain.WATER:
                    self.explore(tribe, tile.pos, 1)

    # -- Turns -------------------------------------------------------------------

    def _check_turn(self, tribe: int) -> None:
        if tribe != self.current:
            raise RuleError("Not your turn")
        if self.winner is not None:
            raise RuleError("The game is over")

    def end_turn(self) -> None:
        """Finish the current tribe's turn and start the next living tribe's."""
        if self.winner is not None:
            return
        pending = self.pending_rewards(self.current)
        if pending:
            raise RuleError(f"{pending[0].name} reached a new level: choose its reward first")
        for unit in self.tribe_units(self.current):
            self._heal_if_idle(unit)
        start = self.current
        while True:
            self.current = (self.current + 1) % len(self.tribes)
            if self.tribes[self.current].alive:
                break
        if self.current <= start:
            self.round += 1
        if self.round > MAX_ROUNDS:
            self.winner = max((t.id for t in self.tribes if t.alive), key=self.score)
            self.log.append(f"Round limit reached: {self.tribes[self.winner].name} wins on score")
            return
        self._start_turn(self.current)

    def _heal_if_idle(self, unit: Unit) -> None:
        if unit.idle and unit.hp < unit.max_hp:
            heal = HEAL_IN_TERRITORY if self.owner_of(unit.pos) == unit.tribe else HEAL_OUTSIDE
            heal += MEDITATION_HEAL * int(self.has_tech(unit.tribe, Tech.MEDITATION))
            unit.hp = min(unit.max_hp, unit.hp + heal)

    def _start_turn(self, tribe: int) -> None:
        t = self.tribes[tribe]
        t.stars += self.income(tribe)
        for unit in self.tribe_units(tribe):
            unit.moved = unit.attacked = unit.done = False
            self.explore(tribe, unit.pos, self._vision(unit))

    def surrender_reason(self, tribe: int) -> str | None:
        """Check after harvesting / rewards: no army and no funded recruitment path."""
        t = self.tribes[tribe]
        if t.human or not t.alive or self.winner is not None or self.tribe_units(tribe):
            return None
        if self.pending_rewards(tribe):
            return None  # resolve rewards before judging the economy
        cities = self.tribe_cities(tribe)
        if cities and all(self.unit_at(city.pos) is not None for city in cities):
            return "no army and every city occupied"
        cheapest = min(info.cost for info in UNITS.values() if self.has_tech(tribe, info.tech))
        remaining_income = max(0, MAX_ROUNDS - self.round) * self.income(tribe)
        if not cities or t.stars + remaining_income < cheapest:
            return "no army and cannot fund a unit before the round limit"
        return None

    def surrender(self, tribe: int) -> None:
        """Concede an unrecoverable AI position, giving occupied cities to their occupiers."""
        self._check_turn(tribe)
        reason = self.surrender_reason(tribe)
        if reason is None:
            raise RuleError("This tribe can still fight or rebuild")
        for city in self.tribe_cities(tribe):
            occupant = self.unit_at(city.pos)
            if occupant is not None:
                city.tribe = occupant.tribe
                city.capital = False
                self.explore(occupant.tribe, city.pos, city.radius)
            else:
                # Nobody receives free unoccupied cities: they can be settled again.
                for tile in self.all_tiles():
                    if tile.owner_city == city.id:
                        tile.owner_city = None
                tile = self.tile(city.pos)
                tile.city_id = None
                tile.village = True
                del self.cities[city.id]
        self.tribes[tribe].surrendered = True
        self.log.append(f"{self.tribes[tribe].name} surrendered: {reason}")
        self._check_elimination()

    def _check_elimination(self) -> None:
        for t in self.tribes:
            if t.alive and not self.tribe_cities(t.id):
                t.alive = False
                for unit in self.tribe_units(t.id):
                    self._kill(unit)
                if not t.surrendered:
                    self.log.append(f"{t.name} has fallen")
        alive = [t for t in self.tribes if t.alive]
        if self.winner is not None:
            return
        if len(alive) == 1:
            self.winner = alive[0].id
            self.log.append(f"{alive[0].name} rules the land")
        elif any(t.human for t in self.tribes) and not any(t.human for t in alive):
            self.winner = max((t.id for t in alive), key=self.score)  # the player is out: the game ends now
            self.log.append(f"{self.tribes[self.winner].name} wins on score")

    # -- Serialisation -----------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "current": self.current,
            "round": self.round,
            "winner": self.winner,
            "next_id": self._next_id,
            "tiles": [
                [t.terrain.value, t.resource.value if t.resource else None, t.harvested, t.village, t.city_id, t.owner_city, t.ruin]
                for t in self.all_tiles()
            ],
            "tribes": [
                {"id": t.id, "name": t.name, "color": list(t.color), "human": t.human, "stars": t.stars,
                 "techs": sorted(x.value for x in t.techs), "explored": sorted(t.explored), "alive": t.alive,
                 "surrendered": t.surrendered}
                for t in self.tribes
            ],
            "cities": [vars(c) for c in self.cities.values()],
            "units": [{**vars(u), "type": u.type.value} for u in self.units.values()],
            "log": self.log[-20:],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> World:
        size = data["size"]
        flat = data["tiles"]
        tiles = [
            [
                Tile(x, y, Terrain(flat[y * size + x][0]),
                     Resource(flat[y * size + x][1]) if flat[y * size + x][1] else None,
                     *flat[y * size + x][2:])
                for x in range(size)
            ]
            for y in range(size)
        ]
        human = next((t["id"] for t in data["tribes"] if t["human"]), None)
        world = cls(size, tiles, len(data["tribes"]), human=human)
        world.current = data["current"]
        world.round = data["round"]
        world.winner = data["winner"]
        world._next_id = data["next_id"]
        world.log = list(data["log"])
        for t, saved in zip(world.tribes, data["tribes"]):
            t.name = saved["name"]
            t.color = tuple(saved["color"])
            t.stars = saved["stars"]
            t.techs = {Tech(v) for v in saved["techs"]}
            t.explored = {tuple(p) for p in saved["explored"]}
            t.alive = saved["alive"]
            t.surrendered = saved.get("surrendered", False)
        for c in data["cities"]:
            world.cities[c["id"]] = City(**c)
        for u in data["units"]:
            world.units[u["id"]] = Unit(**{**u, "type": UnitType(u["type"])})
        return world
