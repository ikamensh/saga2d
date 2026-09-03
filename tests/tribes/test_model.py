"""Rules of the Tribes game, exercised through the World API."""

import random

import pytest

from tribes import ai, mapgen
from tribes.model import RuleError, Tile, World
from tribes.rules import HARVEST, UNITS, Resource, Tech, Terrain, UnitType, tech_cost


def flat_world(size: int = 10, tribes: int = 2) -> World:
    """All-field world with a capital per tribe in opposite corners."""
    tiles = [[Tile(x, y, Terrain.FIELD) for x in range(size)] for y in range(size)]
    world = World(size, tiles, tribes)
    world.found_city(0, (1, 1), "Home", capital=True)
    if tribes > 1:
        world.found_city(1, (size - 2, size - 2), "Away", capital=True)
    world._start_turn(0)
    return world


# -- Movement -----------------------------------------------------------------------


def test_warrior_reaches_its_eight_neighbours_and_nothing_further() -> None:
    world = flat_world()
    unit = world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    assert set(world.reachable(unit)) == set(world.neighbors((4, 4)))


def test_rider_moves_two_tiles_but_forest_and_mountains_stop_it() -> None:
    world = flat_world()
    world.tile((4, 3)).terrain = Terrain.FOREST
    world.tile((4, 6)).terrain = Terrain.MOUNTAIN
    unit = world.spawn_unit(0, UnitType.RIDER, (4, 4))
    reach = world.reachable(unit)
    assert (4, 2) in reach and (2, 4) in reach  # two steps across fields
    assert (4, 3) in reach and (4, 1) not in reach  # forest is enterable but ends the move
    assert (4, 6) not in reach  # mountains need Climbing
    world.tribes[0].techs.add(Tech.CLIMBING)
    assert (4, 6) in world.reachable(unit)


def test_water_and_occupied_tiles_are_impassable() -> None:
    world = flat_world()
    world.tile((5, 4)).terrain = Terrain.WATER
    world.spawn_unit(0, UnitType.WARRIOR, (3, 4))
    unit = world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    reach = world.reachable(unit)
    assert (5, 4) not in reach and (3, 4) not in reach


def test_enemy_zone_of_control_ends_movement() -> None:
    world = flat_world()
    world.tribes[0].explored.update(world.neighbors((4, 4), 3))
    world.spawn_unit(1, UnitType.WARRIOR, (4, 1))
    unit = world.spawn_unit(0, UnitType.RIDER, (4, 4))
    reach = world.reachable(unit)
    assert (4, 2) in reach  # adjacent to the enemy: allowed, but movement stops there
    assert (3, 1) not in reach and (5, 1) not in reach


def test_move_spends_the_move_and_explores_the_path() -> None:
    world = flat_world()
    unit = world.spawn_unit(0, UnitType.RIDER, (4, 4))
    path = world.move(unit, (6, 4))
    assert path == [(4, 4), (5, 4), (6, 4)]
    assert unit.pos == (6, 4) and not unit.can_move and unit.can_attack
    assert world.explored(0, (7, 5))
    with pytest.raises(RuleError):
        world.move(unit, (6, 5))


# -- Combat -------------------------------------------------------------------------


def _duel(attacker_type: UnitType, defender_type: UnitType, *, defender_hp: int | None = None) -> tuple[World, object, object]:
    world = flat_world()
    world.tribes[0].explored.update(world.neighbors((4, 4), 3))
    a = world.spawn_unit(0, attacker_type, (4, 4))
    d = world.spawn_unit(1, defender_type, (5, 4))
    if defender_hp is not None:
        d.hp = defender_hp
    return world, a, d


def test_combat_uses_the_polytopia_formula_for_equal_warriors() -> None:
    world, a, d = _duel(UnitType.WARRIOR, UnitType.WARRIOR)
    assert world.combat_preview(a, d) == (5, 5)
    result = world.attack(a, d)
    assert (result.damage_dealt, result.damage_taken) == (5, 5)
    assert (a.hp, d.hp) == (5, 5)
    assert not a.can_attack and not a.can_move


def test_wounded_units_hit_softer_and_defenders_in_cities_hold_better() -> None:
    world, a, d = _duel(UnitType.WARRIOR, UnitType.WARRIOR)
    full, _ = world.combat_preview(a, d)
    a.hp = 4
    weak, _ = world.combat_preview(a, d)
    assert weak < full
    a.hp = 10
    world.found_city(1, (5, 4), "Fort")
    fortified, _ = world.combat_preview(a, d)
    assert fortified < full


def test_melee_kill_advances_into_the_tile_and_ranged_attacks_avoid_retaliation() -> None:
    world, a, d = _duel(UnitType.WARRIOR, UnitType.WARRIOR, defender_hp=3)
    result = world.attack(a, d)
    assert result.defender_killed and a.pos == (5, 4) and a.hp == 10 and d.id not in world.units
    world2 = flat_world()
    world2.tribes[0].explored.update(world2.neighbors((4, 4), 3))
    archer = world2.spawn_unit(0, UnitType.ARCHER, (4, 4))
    target = world2.spawn_unit(1, UnitType.WARRIOR, (6, 4))
    result = world2.attack(archer, target)
    assert result.damage_taken == 0 and archer.hp == 10 and target.hp < 10


def test_rider_can_escape_after_attacking_and_knight_persists_after_a_kill() -> None:
    world, rider, d = _duel(UnitType.RIDER, UnitType.WARRIOR)
    world.attack(rider, d)
    assert rider.can_move and not rider.can_attack
    world.move(rider, (3, 3))
    assert not rider.can_act
    world2, knight, weak = _duel(UnitType.KNIGHT, UnitType.WARRIOR, defender_hp=1)
    world2.attack(knight, weak)
    assert knight.can_attack


def test_attacking_out_of_range_or_out_of_turn_is_refused() -> None:
    world = flat_world()
    world.tribes[0].explored.update(world.neighbors((4, 4), 3))
    a = world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    far = world.spawn_unit(1, UnitType.WARRIOR, (7, 4))
    with pytest.raises(RuleError):
        world.attack(a, far)
    with pytest.raises(RuleError):
        world.move(far, (6, 4))


# -- Cities -------------------------------------------------------------------------


def test_capturing_a_village_founds_a_city_with_territory_and_takes_the_turn() -> None:
    world = flat_world()
    world.tile((4, 4)).village = True
    unit = world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    assert world.can_capture(unit)
    city = world.capture(unit)
    assert city.tribe == 0 and world.city_at((4, 4)) is city and not world.tile((4, 4)).village
    assert world.owner_of((5, 5)) == 0 and world.owner_of((6, 6)) is None
    assert not unit.can_act
    assert len(world.tribe_cities(0)) == 2 and world.income(0) == 3


def test_capture_needs_a_full_turn_on_the_tile() -> None:
    world = flat_world()
    world.tile((5, 4)).village = True
    unit = world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    world.move(unit, (5, 4))
    assert not world.can_capture(unit)
    world.end_turn()
    world.end_turn()
    assert world.can_capture(unit)


def test_taking_an_enemy_capital_eliminates_a_tribe_with_no_cities_left() -> None:
    world = flat_world()
    away = world.capital_of(1)
    world.spawn_unit(1, UnitType.WARRIOR, (3, 3))
    unit = world.spawn_unit(0, UnitType.WARRIOR, away.pos)
    world.capture(unit)
    assert away.tribe == 0 and not away.capital
    assert not world.tribes[1].alive and world.tribe_units(1) == []
    assert world.winner == 0


def test_training_costs_stars_respects_tech_and_the_unit_cap() -> None:
    world = flat_world()
    home = world.capital_of(0)
    assert world.can_train(home, UnitType.ARCHER) == "Requires Archery"
    world.tribes[0].stars = 1
    assert world.can_train(home, UnitType.WARRIOR) == "Costs 2★"
    world.tribes[0].stars = 10
    first = world.train(home, UnitType.WARRIOR)
    assert world.tribes[0].stars == 8 and not first.can_act
    assert world.can_train(home, UnitType.WARRIOR) == "City tile occupied"
    world.move_free(first, (2, 2))
    world.train(home, UnitType.WARRIOR)
    world.move_free(world.unit_at(home.pos), (3, 3))
    assert world.can_train(home, UnitType.WARRIOR) == "Unit limit reached"


def test_harvesting_grows_population_and_levels_the_city_up() -> None:
    world = flat_world()
    home = world.capital_of(0)
    world.tile((2, 1)).resource = Resource.FRUIT
    world.tile((2, 2)).resource = Resource.FRUIT
    assert world.can_harvest(0, (2, 1)) == "Requires Organization"
    world.tribes[0].techs.add(Tech.ORGANIZATION)
    world.tribes[0].stars = 10
    world.harvest(0, (2, 1))
    assert (home.level, home.population, world.tribes[0].stars) == (1, 1, 8)
    world.harvest(0, (2, 2))
    assert (home.level, home.population) == (2, 0)
    assert world.can_harvest(0, (2, 2)) == "Nothing to harvest"
    assert world.income(0) == 3


def test_border_growth_claims_the_outer_ring_but_not_neighbours_land() -> None:
    world = flat_world()
    home = world.capital_of(0)
    world.found_city(1, (4, 1), "Rival")
    world._grow(home, 5)
    assert home.level == 3 and world.owner_of((3, 3)) == 0
    assert world.owner_of((3, 1)) == 1  # already Rival's


# -- Research -----------------------------------------------------------------------


def test_tech_costs_rise_with_city_count_and_prerequisites_are_enforced() -> None:
    assert tech_cost(Tech.ORGANIZATION, 1) < tech_cost(Tech.ORGANIZATION, 3)
    assert tech_cost(Tech.FARMING, 1) > tech_cost(Tech.ORGANIZATION, 1)
    world = flat_world()
    world.tribes[0].stars = 100
    assert world.can_research(0, Tech.FARMING) == "Requires Organization"
    world.research(0, Tech.ORGANIZATION)
    world.research(0, Tech.FARMING)
    assert world.can_research(0, Tech.FARMING) == "Already known"
    assert world.tribes[0].stars == 100 - tech_cost(Tech.ORGANIZATION, 1) - tech_cost(Tech.FARMING, 1)


# -- Turns --------------------------------------------------------------------------


def test_end_turn_cycles_tribes_pays_income_and_heals_idle_units() -> None:
    world = flat_world()
    hurt = world.spawn_unit(0, UnitType.WARRIOR, (1, 1))
    hurt.hp = 2
    mover = world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    mover.hp = 2
    world.move(mover, (5, 5))
    stars = world.tribes[0].stars
    world.end_turn()
    assert world.current == 1 and world.round == 1
    world.end_turn()
    assert world.current == 0 and world.round == 2
    assert world.tribes[0].stars == stars + world.income(0)
    assert hurt.hp == 2 + 4 and mover.hp == 2  # idle unit in territory heals 4; the mover does not
    assert mover.can_act


def test_game_ends_on_score_after_the_round_limit() -> None:
    from tribes.rules import MAX_ROUNDS

    world = flat_world()
    world.round = MAX_ROUNDS
    world.end_turn()
    world.end_turn()
    assert world.winner is not None


def test_save_round_trip_preserves_the_world() -> None:
    world = mapgen.generate(seed=7, size=12, tribe_count=3)
    rng = random.Random(0)
    world.tribes[0].human = False
    for _ in range(6):
        ai.take_turn(world, world.current, rng)
    copy = World.from_dict(world.to_dict())
    assert copy.to_dict() == world.to_dict()
    assert [u.pos for u in copy.units.values()] == [u.pos for u in world.units.values()]


# -- Map generation and AI ------------------------------------------------------------


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_generated_maps_are_connected_and_capitals_start_apart(seed: int) -> None:
    world = mapgen.generate(seed=seed, size=14, tribe_count=3)
    capitals = [world.capital_of(i) for i in range(3)]
    assert all(c is not None for c in capitals)
    for a in capitals:
        for b in capitals:
            if a is not b:
                assert World.distance(a.pos, b.pos) >= 5
    # Every capital can reach every other capital over land.
    from collections import deque

    start = capitals[0].pos
    seen = {start}
    queue = deque([start])
    while queue:
        pos = queue.popleft()
        for n in world.neighbors(pos):
            if n not in seen and world.tile(n).terrain is not Terrain.WATER:
                seen.add(n)
                queue.append(n)
    assert all(c.pos in seen for c in capitals)
    assert any(t.village for t in world.all_tiles())
    assert all(world.unit_at(c.pos) is not None for c in capitals)


@pytest.mark.parametrize("seed", [11, 12])
def test_ai_plays_a_full_game_to_a_winner(seed: int) -> None:
    world = mapgen.generate(seed=seed, size=14, tribe_count=3)
    world.tribes[0].human = False
    rng = random.Random(seed)
    turns = 0
    while world.winner is None:
        ai.take_turn(world, world.current, rng)
        turns += 1
        assert turns < 500
    assert world.tribes[world.winner].alive
