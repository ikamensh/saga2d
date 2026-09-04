"""The computer opponent, driven through the public World API."""

import random
from collections import Counter

import pytest

from tribes import ai, mapgen
from tribes.model import Tile, World
from tribes.rules import MAX_ROUNDS, Terrain, UnitType


def flat_world(size: int = 10, tribes: int = 2) -> World:
    """All-field world, both tribes computer-controlled, everything explored."""
    tiles = [[Tile(x, y, Terrain.FIELD) for x in range(size)] for y in range(size)]
    world = World(size, tiles, tribes, human=None)
    world.found_city(0, (1, 1), "Home", capital=True)
    world.found_city(1, (size - 2, size - 2), "Away", capital=True)
    for tribe in world.tribes:
        tribe.explored.update(t.pos for t in world.all_tiles())
    world._start_turn(0)
    return world


def check_invariants(world: World) -> None:
    occupied: dict = {}
    for unit in world.units.values():
        assert 0 < unit.hp <= unit.max_hp
        assert unit.pos not in occupied, f"two units on {unit.pos}"
        occupied[unit.pos] = unit
        assert world.tile(unit.pos).terrain is not Terrain.WATER
        assert world.tribes[unit.tribe].alive
    for tribe in world.tribes:
        assert tribe.stars >= 0
        assert bool(world.tribe_cities(tribe.id)) == tribe.alive
        assert tribe.alive or not world.tribe_units(tribe.id)
    assert all(n <= 1 for n in Counter(c.tribe for c in world.cities.values() if c.capital).values())
    for tile in world.all_tiles():
        if tile.city_id is not None:
            assert tile.owner_city == tile.city_id and not tile.village


def test_ai_stops_acting_once_it_has_won() -> None:
    world = flat_world()
    world.tribes[0].explored.discard((0, 9))  # a frontier keeps the second unit wanting to move
    world.spawn_unit(0, UnitType.WARRIOR, (8, 8))  # standing on the enemy capital
    world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    ai.take_turn(world, 0, random.Random(1))
    assert world.winner == 0


def test_ai_captures_the_village_it_stands_on() -> None:
    world = flat_world()
    world.tile((4, 4)).village = True
    world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    ai.take_turn(world, 0, random.Random(1))
    city = world.city_at((4, 4))
    assert city is not None and city.tribe == 0


def test_ai_walks_around_water_to_reach_a_village() -> None:
    world = flat_world(size=12)
    for y in range(2, 12):
        world.tile((6, y)).terrain = Terrain.WATER  # a wall with a gap only at the top edge
    world.tile((9, 4)).village = True
    world.tribes[0].stars = 0
    scout = world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    rng = random.Random(1)
    for _ in range(10):
        ai.take_turn(world, 0, rng)
        world.end_turn()
    assert world.city_at((9, 4)) is not None, scout.pos


def test_ai_does_not_throw_a_warrior_at_a_walled_city() -> None:
    world = flat_world()
    fort = world.capital_of(1)
    world._grow(fort, 9)  # level 4: walls
    guard = world.spawn_unit(1, UnitType.DEFENDER, fort.pos)
    attacker = world.spawn_unit(0, UnitType.WARRIOR, (7, 7))
    world.tribes[0].stars = 0
    ai.take_turn(world, 0, random.Random(1))
    assert attacker.id in world.units and guard.hp == guard.max_hp


def test_ai_finishes_off_a_weak_unit_and_advances() -> None:
    world = flat_world()
    victim = world.spawn_unit(1, UnitType.WARRIOR, (5, 5))
    victim.hp = 1
    hunter = world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    world.tribes[0].stars = 0
    ai.take_turn(world, 0, random.Random(1))
    assert victim.id not in world.units and hunter.pos == (5, 5)


def test_ai_spends_its_stars_on_research_harvest_and_units() -> None:
    world = mapgen.generate(seed=3, size=12, tribe_count=2, human=None)
    rng = random.Random(3)
    for _ in range(8):
        ai.take_turn(world, world.current, rng)
    for tribe in world.tribes:
        assert tribe.techs, f"{tribe.name} researched nothing"
        assert len(world.tribe_units(tribe.id)) >= 2, f"{tribe.name} trained nothing"
        assert tribe.stars < 12, f"{tribe.name} hoards {tribe.stars} stars"
    assert any(t.harvested for t in world.all_tiles())


@pytest.mark.parametrize("seed", range(1, 13))
def test_ai_games_keep_every_invariant_and_end(seed: int) -> None:
    world = mapgen.generate(seed=seed, size=14, tribe_count=3, human=None)
    rng = random.Random(seed)
    turns = 0
    while world.winner is None:
        round_before = world.round
        ai.take_turn(world, world.current, rng)
        assert world.round in (round_before, round_before + 1)
        check_invariants(world)
        turns += 1
        assert turns < 3 * (MAX_ROUNDS + 1)
    assert world.tribes[world.winner].alive
