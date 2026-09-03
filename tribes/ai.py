"""A straightforward computer opponent: grow, arm, expand, fight."""

from __future__ import annotations

import random

from tribes.model import Pos, RuleError, Unit, World
from tribes.rules import HARVEST, TECHS, Resource, Tech, UnitType


def take_turn(world: World, tribe: int, rng: random.Random) -> None:
    """Play the whole turn for *tribe* (which must be current), then end it."""
    assert world.current == tribe
    _research(world, tribe)
    _harvest(world, tribe)
    _train(world, tribe, rng)
    for unit in list(world.tribe_units(tribe)):
        if unit.id in world.units:
            _act(world, unit, rng)
    world.end_turn()


def _research(world: World, tribe: int) -> None:
    wanted = _wanted_techs(world, tribe)
    for tech in wanted:
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


def _train(world: World, tribe: int, rng: random.Random) -> None:
    for city in world.tribe_cities(tribe):
        choices = [u for u in UnitType if world.can_train(city, u) is None]
        if choices:
            world.train(city, rng.choice(choices))


def _act(world: World, unit: Unit, rng: random.Random) -> None:
    if world.can_capture(unit):
        world.capture(unit)
        return
    if _attack_best(world, unit):
        if not unit.can_move:
            return
    if unit.can_move:
        target = _target_for(world, unit)
        if target is not None:
            _move_toward(world, unit, target, rng)
    _attack_best(world, unit)


def _attack_best(world: World, unit: Unit) -> bool:
    targets = world.attack_targets(unit)
    if not targets:
        return False
    target = min(targets, key=lambda t: (t.hp, -t.info.cost))
    try:
        world.attack(unit, target)
    except RuleError:
        return False
    return True


def _target_for(world: World, unit: Unit) -> Pos | None:
    explored = world.tribes[unit.tribe].explored
    goals: list[tuple[int, Pos]] = []
    for tile in world.all_tiles():
        if tile.pos not in explored:
            continue
        city = world.city_at(tile.pos)
        if tile.village or (city is not None and city.tribe != unit.tribe):
            goals.append((0, tile.pos))
    for other in world.units.values():
        if other.tribe != unit.tribe and other.pos in explored:
            goals.append((1, other.pos))
    if not goals:
        frontier = [p for p in explored if any(n not in explored for n in world.neighbors(p))]
        goals = [(2, p) for p in frontier]
    if not goals:
        return None
    return min(goals, key=lambda g: (g[0], world.distance(unit.pos, g[1])))[1]


def _move_toward(world: World, unit: Unit, target: Pos, rng: random.Random) -> None:
    reachable = world.reachable(unit)
    if not reachable:
        return
    best = min(reachable, key=lambda p: (world.distance(p, target), rng.random()))
    if world.distance(best, target) < world.distance(unit.pos, target) or rng.random() < 0.3:
        world.move(unit, best)
