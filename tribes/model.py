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
    CITY_BORDER_GROWTH_LEVEL, CITY_DEFENSE_BONUS, CITY_WALL_LEVEL, HARVEST, HEAL_IN_TERRITORY, HEAL_OUTSIDE,
    MAX_ROUNDS, MOUNTAIN_DEFENSE_BONUS, STARTING_STARS, TECHS, TRIBES, UNITS, WALL_DEFENSE_BONUS, Resource, Tech,
    Terrain, UnitType, tech_cost,
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

    @property
    def pos(self) -> Pos:
        return (self.x, self.y)

    @property
    def radius(self) -> int:
        return 2 if self.level >= CITY_BORDER_GROWTH_LEVEL else 1

    @property
    def next_level_population(self) -> int:
        return self.level + 1

    @property
    def income(self) -> int:
        return self.level + (1 if self.capital else 0)

    @property
    def has_wall(self) -> bool:
        return self.level >= CITY_WALL_LEVEL


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


@dataclass
class CombatResult:
    attacker: Unit
    defender: Unit
    damage_dealt: int
    damage_taken: int
    defender_killed: bool
    attacker_killed: bool


class World:
    def __init__(self, size: int, tiles: list[list[Tile]], tribe_count: int, human: int | None = 0) -> None:
        self.size = size
        self.tiles = tiles
        self.tribes = [Tribe(i, TRIBES[i].name, TRIBES[i].color, human=(i == human)) for i in range(tribe_count)]
        self.cities: dict[int, City] = {}
        self.units: dict[int, Unit] = {}
        self.current = 0
        self.round = 1
        self.winner: int | None = None
        self.log: list[str] = []
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
        return sum(c.income for c in self.tribe_cities(tribe))

    def unit_cap(self, tribe: int) -> int:
        return sum(c.level + 1 for c in self.tribe_cities(tribe))

    def has_tech(self, tribe: int, tech: Tech | None) -> bool:
        return tech is None or tech in self.tribes[tribe].techs

    def explored(self, tribe: int, pos: Pos) -> bool:
        return pos in self.tribes[tribe].explored

    def score(self, tribe: int) -> int:
        t = self.tribes[tribe]
        territory = sum(1 for tile in self.all_tiles() if self.owner_of(tile.pos) == tribe)
        return (
            sum(100 * c.level for c in self.tribe_cities(tribe))
            + 20 * len(t.techs)
            + sum(5 * u.info.cost for u in self.tribe_units(tribe))
            + 5 * territory
        )

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
        for pos in [city.pos, *self.neighbors(city.pos, city.radius)]:
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
        if self.tile(pos).terrain in (Terrain.FOREST, Terrain.MOUNTAIN):
            return True
        return any((n := self.unit_at(p)) is not None and n.tribe != unit.tribe for p in self.neighbors(pos))

    def reachable(self, unit: Unit) -> dict[Pos, Pos]:
        """Every tile *unit* can move to this turn, mapped to the tile before it on the path."""
        if not unit.can_move:
            return {}
        parents: dict[Pos, Pos] = {}
        budget_left: dict[Pos, int] = {unit.pos: unit.info.movement}
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
        return path

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
            attacker.attacked = False  # persist: may strike again
        elif not (attacker.info.escape and not attacker.moved):
            attacker.done = True  # escape units may still move away
        self.log.append(f"{self.tribes[attacker.tribe].name} {attacker.type.value} hit {defender.type.value} for {dealt}")
        self._check_elimination()
        return CombatResult(attacker, defender, dealt, taken, defender_killed, attacker_killed)

    def move_free(self, unit: Unit, pos: Pos) -> None:
        """Relocate without spending movement (used when a melee kill advances)."""
        unit.x, unit.y = pos
        self.explore(unit.tribe, pos, self._vision(unit))

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

    def can_harvest(self, tribe: int, pos: Pos) -> str | None:
        tile = self.tile(pos)
        if tile.resource is None or tile.harvested:
            return "Nothing to harvest"
        if self.owner_of(pos) != tribe:
            return "Not your territory"
        info = HARVEST[tile.resource]
        if not self.has_tech(tribe, info.tech):
            return f"Requires {info.tech.value.title()}"
        if self.tribes[tribe].stars < info.cost:
            return f"Costs {info.cost}★"
        return None

    def harvest(self, tribe: int, pos: Pos) -> City:
        self._check_turn(tribe)
        reason = self.can_harvest(tribe, pos)
        if reason is not None:
            raise RuleError(reason)
        tile = self.tile(pos)
        info = HARVEST[tile.resource]  # type: ignore[index]
        self.tribes[tribe].stars -= info.cost
        tile.harvested = True
        city = self.cities[tile.owner_city]  # type: ignore[index]
        self._grow(city, info.population)
        return city

    def _grow(self, city: City, population: int) -> None:
        city.population += population
        while city.population >= city.next_level_population:
            city.population -= city.next_level_population
            city.level += 1
            self._claim_territory(city)
            self.explore(city.tribe, city.pos, city.radius)
            self.log.append(f"{self.tribes[city.tribe].name}'s {city.name} grew to level {city.level}")

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
        for unit in self.tribe_units(self.current):
            self._heal_if_idle(unit)
        start = self.current
        while True:
            self.current = (self.current + 1) % len(self.tribes)
            if self.current <= start:
                self.round += 1
            if self.tribes[self.current].alive:
                break
        if self.round > MAX_ROUNDS:
            self.winner = max(range(len(self.tribes)), key=self.score)
            self.log.append(f"Round limit reached: {self.tribes[self.winner].name} wins on score")
            return
        self._start_turn(self.current)

    def _heal_if_idle(self, unit: Unit) -> None:
        if unit.idle and unit.hp < unit.max_hp:
            heal = HEAL_IN_TERRITORY if self.owner_of(unit.pos) == unit.tribe else HEAL_OUTSIDE
            unit.hp = min(unit.max_hp, unit.hp + heal)

    def _start_turn(self, tribe: int) -> None:
        t = self.tribes[tribe]
        t.stars += self.income(tribe)
        for unit in self.tribe_units(tribe):
            unit.moved = unit.attacked = unit.done = False
            self.explore(tribe, unit.pos, self._vision(unit))

    def _check_elimination(self) -> None:
        for t in self.tribes:
            if t.alive and not self.tribe_cities(t.id):
                t.alive = False
                for unit in self.tribe_units(t.id):
                    self._kill(unit)
                self.log.append(f"{t.name} has fallen")
        alive = [t for t in self.tribes if t.alive]
        if len(alive) == 1 and self.winner is None:
            self.winner = alive[0].id
            self.log.append(f"{alive[0].name} rules the land")

    # -- Serialisation -----------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        return {
            "size": self.size,
            "current": self.current,
            "round": self.round,
            "winner": self.winner,
            "next_id": self._next_id,
            "tiles": [
                [t.terrain.value, t.resource.value if t.resource else None, t.harvested, t.village, t.city_id, t.owner_city]
                for t in self.all_tiles()
            ],
            "tribes": [
                {"id": t.id, "human": t.human, "stars": t.stars, "techs": sorted(x.value for x in t.techs),
                 "explored": sorted(t.explored), "alive": t.alive}
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
            t.stars = saved["stars"]
            t.techs = {Tech(v) for v in saved["techs"]}
            t.explored = {tuple(p) for p in saved["explored"]}
            t.alive = saved["alive"]
        for c in data["cities"]:
            world.cities[c["id"]] = City(**c)
        for u in data["units"]:
            world.units[u["id"]] = Unit(**{**u, "type": UnitType(u["type"])})
        return world
