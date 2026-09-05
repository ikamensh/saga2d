"""A straightforward computer opponent: grow, arm, expand, fight.

Deterministic for a given ``rng``.  Every action is checked with the
corresponding ``can_*`` query first, so the model never raises here.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Iterator

from tribes.model import City, Pos, Unit, World
from tribes.rules import HARVEST, MAX_ROUNDS, TECHS, Reward, Tech, Terrain, UnitType

_UNREACHABLE = 10**6


def take_turn(world: World, tribe: int, rng: random.Random) -> None:
    """Play the whole turn for *tribe* (which must be current), then end it."""
    assert world.current == tribe and world.winner is None
    _research(world, tribe)
    _harvest(world, tribe)
    _choose_rewards(world, tribe)
    _train(world, tribe, rng)
    for unit in _units_in_play(world, tribe):
        _act(world, unit, rng)
    for unit in _units_in_play(world, tribe):
        _attack(world, unit)  # second pass: units that moved into place this turn can now gang up
    _choose_rewards(world, tribe)  # ruins found on the march can level a city too
    if world.winner is None:
        world.end_turn()


def _units_in_play(world: World, tribe: int) -> Iterator[Unit]:
    """The tribe's units still alive when their turn comes, while the game is on."""
    for unit in list(world.tribe_units(tribe)):
        if world.winner is None and unit.id in world.units:
            yield unit


def _research(world: World, tribe: int) -> None:
    for tech in _wanted_techs(world, tribe):
        if world.can_research(tribe, tech) is None and world.tribes[tribe].stars - world.tech_cost(tribe, tech) >= 2:
            world.research(tribe, tech)
            return


def _wanted_techs(world: World, tribe: int) -> list[Tech]:
    """Techs that unlock something in our territory first, then the rest by tier."""
    resources = {t.resource for t in world.all_tiles() if world.owner_of(t.pos) == tribe and t.resource and not t.harvested}
    useful = [HARVEST[r].tech for r in resources]
    ordered = sorted(TECHS, key=lambda t: (t not in useful, TECHS[t].tier))
    return [t for t in ordered if t not in world.tribes[tribe].techs]


def _harvest(world: World, tribe: int) -> None:
    options = [t for t in world.all_tiles() if world.owner_of(t.pos) == tribe and t.resource and not t.harvested]
    options.sort(key=lambda t: HARVEST[t.resource].cost / HARVEST[t.resource].population)  # type: ignore[index]
    for tile in options:
        if world.can_harvest(tribe, tile.pos) is None:
            world.harvest(tribe, tile.pos)


def _choose_rewards(world: World, tribe: int) -> None:
    while (pending := world.pending_rewards(tribe)) and world.winner is None:
        world.choose_reward(pending[0], _pick_reward(world, pending[0]))


def _pick_reward(world: World, city: City) -> Reward:
    """Walls when enemies are near, borders when they reach new resources, parks late; else the first offer."""
    first, second = world.reward_options(city)
    if first is Reward.WALLS:
        threatened = any(u.tribe != city.tribe and world.distance(u.pos, city.pos) <= 4 for u in world.units.values())
        return first if threatened else second
    if first is Reward.BORDER:
        ring = [p for p in world.neighbors(city.pos, city.radius + 1) if world.distance(p, city.pos) == city.radius + 1]
        return first if any(world.tile(p).resource is not None and world.owner_of(p) is None for p in ring) else second
    if first is Reward.PARK:
        return first if world.round > MAX_ROUNDS * 2 // 3 else second
    return first


def _train(world: World, tribe: int, rng: random.Random) -> None:
    for city in world.tribe_cities(tribe):
        choices = [u for u in UnitType if world.can_train(city, u) is None]
        if choices:
            world.train(city, rng.choice(choices))


def _act(world: World, unit: Unit, rng: random.Random) -> None:
    if world.can_capture(unit):
        world.capture(unit)
        return
    _attack(world, unit)
    if unit.id in world.units and unit.can_move:
        target = _target_for(world, unit, rng)
        if target is not None:
            _move_toward(world, unit, target, rng)


def _attack(world: World, unit: Unit) -> None:
    """Strike every favourable target in reach (a knight keeps going after kills)."""
    while unit.id in world.units and unit.can_attack:
        target = _best_target(world, unit)
        if target is None:
            return
        world.attack(unit, target)


def _best_target(world: World, unit: Unit) -> Unit | None:
    """Prefer kills, then the target left weakest; refuse suicidal, losing and even trades.

    Even trades are refused because the side striking second wins them (both
    end on half health and the counter-strike kills).  A trade that does not
    win on its own is still taken when friends already in range can finish
    the target this turn — that is how cities fall.
    """
    options: list[tuple[tuple[bool, int, int], Unit]] = []
    for target in world.attack_targets(unit):
        dealt, taken = world.combat_preview(unit, target)
        support = sum(
            world.combat_preview(ally, target)[0]
            for ally in world.tribe_units(unit.tribe)
            if ally is not unit and ally.can_attack and target in world.attack_targets(ally)
        )
        solo_kill = dealt >= target.hp
        retaliation = 0 if solo_kill or world.distance(unit.pos, target.pos) > target.info.range else taken
        if retaliation >= unit.hp:
            continue
        kill = dealt + support >= target.hp
        if not kill and retaliation >= dealt:
            continue
        options.append(((not kill, target.hp - dealt, -target.info.cost), target))
    return min(options, key=lambda o: o[0])[1] if options else None


def _target_for(world: World, unit: Unit, rng: random.Random) -> Pos | None:
    """Nearest (by walking distance) village, ruin or enemy city, else enemy unit, else unexplored edge.

    Ties go to the tile nearest the map's centre, then to chance: breaking
    them on coordinates sent one corner's tribe exploring along the map edge.
    """
    explored = world.tribes[unit.tribe].explored
    dist = _distances(world, unit, unit.pos)
    goals: list[tuple[int, int, Pos]] = []
    for tile in world.all_tiles():
        if tile.pos not in explored or tile.pos not in dist:
            continue
        city = world.city_at(tile.pos)
        occupant = world.unit_at(tile.pos)
        claimable = tile.village or tile.ruin or (city is not None and city.tribe != unit.tribe)
        if claimable and (occupant is None or occupant.tribe != unit.tribe):
            goals.append((0, dist[tile.pos], tile.pos))
    for other in world.units.values():
        if other.tribe != unit.tribe and other.pos in explored and other.pos in dist:
            goals.append((1, dist[other.pos], other.pos))
    if not goals:
        goals = [(2, dist[p], p) for p in explored if p in dist and any(n not in explored for n in world.neighbors(p))]
    if not goals:
        return None
    centre = (world.size - 1) / 2
    return min(goals, key=lambda g: (g[0], g[1], abs(g[2][0] - centre) + abs(g[2][1] - centre), rng.random()))[2]


def _move_toward(world: World, unit: Unit, target: Pos, rng: random.Random) -> None:
    reachable = world.reachable(unit)
    if not reachable:
        return
    dist = _distances(world, unit, target)
    best = min(reachable, key=lambda p: (dist.get(p, _UNREACHABLE), rng.random()))
    if dist.get(best, _UNREACHABLE) < dist.get(unit.pos, _UNREACHABLE):
        world.move(unit, best)


def _distances(world: World, unit: Unit, origin: Pos) -> dict[Pos, int]:
    """Walking distance from *origin* to every tile *unit*'s tribe can traverse.

    Occupied tiles can be reached (they are targets) but not walked through,
    so friends queued behind a unit that is holding its ground fan out
    around it instead of waiting forever.
    """
    occupied = {u.pos for u in world.units.values()}
    dist = {origin: 0}
    queue = deque([origin])
    while queue:
        pos = queue.popleft()
        for nxt in world.neighbors(pos):
            if nxt in dist or not _passable(world, unit, nxt):
                continue
            dist[nxt] = dist[pos] + 1
            if nxt not in occupied:
                queue.append(nxt)
    return dist


def _passable(world: World, unit: Unit, pos: Pos) -> bool:
    terrain = world.tile(pos).terrain
    if terrain is Terrain.WATER:
        return False
    return terrain is not Terrain.MOUNTAIN or world.has_tech(unit.tribe, Tech.CLIMBING)
