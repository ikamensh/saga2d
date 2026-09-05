"""Rules of the Tribes game, exercised through the World API."""

import random

import pytest

from tribes import ai, mapgen
from tribes.model import RuleError, Tile, World
from tribes.rules import (
    HARVEST, REWARD_PARK_SCORE, REWARD_STARS, RUIN_POPULATION, RUIN_TREASURE, RUIN_VISION_RADIUS, Discovery, Resource, Reward,
    Tech, Terrain, UnitType, tech_cost,
)


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
    with pytest.raises(RuleError, match="out of range"):
        world.attack(a, far)
    with pytest.raises(RuleError, match="Not your turn"):
        world.move(far, (6, 4))
    near = world.spawn_unit(1, UnitType.WARRIOR, (5, 4))
    world.attack(a, near)
    with pytest.raises(RuleError, match="Already attacked"):
        world.attack(a, near)


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


# -- Regressions ---------------------------------------------------------------------


def _three_tribe_world() -> World:
    """Three computer tribes; tests that need a human set ``human`` themselves."""
    world = flat_world(tribes=3)
    world.tribes[0].human = False
    world.found_city(2, (8, 1), "Third", capital=True)
    return world


def _eliminate(world: World, tribe: int, heir: int) -> None:
    for city in world.tribe_cities(tribe):
        city.tribe = heir
    world._check_elimination()


@pytest.mark.parametrize("dead", [0, 1, 2])
def test_round_advances_exactly_once_per_lap_whatever_tribe_is_dead(dead: int) -> None:
    world = _three_tribe_world()
    _eliminate(world, dead, (dead + 1) % 3)
    world.current = next(t.id for t in world.tribes if t.alive)
    first = world.current
    world.end_turn()
    assert world.round == 1 and world.tribes[world.current].alive and world.current != dead
    world.end_turn()
    assert world.current == first and world.round == 2


def test_knight_that_killed_may_strike_again_but_neither_moves_nor_heals() -> None:
    world, knight, weak = _duel(UnitType.KNIGHT, UnitType.WARRIOR, defender_hp=1)
    knight.hp = 6
    world.attack(knight, weak)
    assert knight.pos == weak.pos and knight.can_attack and not knight.can_move
    world.end_turn()
    assert knight.hp == 6


def test_eliminating_the_human_ends_the_game_with_the_strongest_ai_as_winner() -> None:
    world = _three_tribe_world()
    world.tribes[0].human = True
    world.tribes[2].techs.update({Tech.RIDING, Tech.CLIMBING})
    world.end_turn()
    raider = world.spawn_unit(1, UnitType.WARRIOR, (1, 1))
    world.capture(raider)
    assert not world.tribes[0].alive and world.tribe_units(0) == []
    assert world.winner == max((1, 2), key=world.score)
    with pytest.raises(RuleError):
        world.move(raider, (2, 2))


def test_round_limit_winner_is_chosen_among_living_tribes() -> None:
    from tribes.rules import MAX_ROUNDS

    world = _three_tribe_world()
    world.tribes[2].techs.update(Tech)  # a dead tribe's techs must not win it the game
    _eliminate(world, 2, 1)
    world.round = MAX_ROUNDS
    world.end_turn()
    world.end_turn()
    assert world.winner in (0, 1)


def test_a_city_founded_inside_foreign_borders_owns_its_own_tile() -> None:
    world = flat_world()
    world._grow(world.capital_of(0), 5)  # level 3: radius-2 border reaches (3, 3)
    world.capital_of(0).pending_reward = False  # rewards are not the subject here
    world.tile((3, 3)).village = True
    settler = world.spawn_unit(1, UnitType.WARRIOR, (3, 3))
    world.end_turn()
    city = world.capture(settler)
    assert world.owner_of((3, 3)) == 1 and world.tile((3, 3)).owner_city == city.id
    assert world.owner_of((2, 2)) == 0  # but it steals nothing else


def test_json_save_round_trip_mid_turn_keeps_unit_flags_and_the_winner() -> None:
    import json

    world = mapgen.generate(seed=5, size=12, tribe_count=3)
    rng = random.Random(0)
    for _ in range(3):
        ai.take_turn(world, world.current, rng)
    home = world.capital_of(0)
    field = next(t for t in world.all_tiles() if t.resource and not t.harvested and world.owner_of(t.pos) == 0)
    world.tribes[0].techs.update({Tech.CLIMBING, HARVEST[field.resource].tech})
    world.tribes[0].stars = 10
    world.harvest(0, field.pos)
    camp = next(p for p in world.neighbors(home.pos) if world.unit_at(p) is None and world.tile(p).terrain is not Terrain.WATER)
    scout = world.spawn_unit(0, UnitType.WARRIOR, camp, fresh=False)
    world.winner = 2
    copy = World.from_dict(json.loads(json.dumps(world.to_dict())))
    assert copy.to_dict() == world.to_dict()
    twin = copy.units[scout.id]
    assert (twin.moved, twin.attacked, twin.done, twin.pos) == (True, True, True, scout.pos)
    assert copy.tile(field.pos).harvested and copy.capital_of(0).capital and copy.winner == 2
    assert copy.tribes[0].techs == world.tribes[0].techs and copy.tribes[0].explored == world.tribes[0].explored


@pytest.mark.parametrize("seed", range(1, 21))
def test_generated_capitals_have_room_to_move_and_resources_to_harvest(seed: int) -> None:
    world = mapgen.generate(seed=seed, size=14, tribe_count=3)
    for tribe in range(3):
        capital = world.capital_of(tribe)
        walkable = [p for p in world.neighbors(capital.pos) if world.tile(p).terrain in (Terrain.FIELD, Terrain.FOREST)]
        assert len(walkable) >= 4, f"tribe {tribe} is boxed in"
        assert sum(1 for p in world.neighbors(capital.pos, 1) if world.tile(p).resource) >= 2
        assert sum(1 for p in world.neighbors(capital.pos, 2) if world.tile(p).resource) >= 4
        assert not world.tile(capital.pos).village and world.tile(capital.pos).resource is None
    villages = [t.pos for t in world.all_tiles() if t.village]
    assert len(villages) >= 2
    for a in villages:
        for b in villages:
            assert a == b or World.distance(a, b) >= 3


@pytest.mark.parametrize("seed", [21, 22, 23])
def test_every_path_on_a_generated_map_is_a_legal_walk(seed: int) -> None:
    world = mapgen.generate(seed=seed, size=14, tribe_count=3, human=None)
    rng = random.Random(seed)
    for _ in range(9):
        ai.take_turn(world, world.current, rng)
    world.tribes[world.current].techs.add(Tech.RIDING)
    world.tribes[world.current].stars = 30
    for city in world.tribe_cities(world.current):
        if world.can_train(city, UnitType.RIDER) is None:
            world.train(city, UnitType.RIDER)
    world.end_turn()
    for _ in range(len(world.tribes) - 1):
        world.end_turn()
    checked = 0
    for unit in world.tribe_units(world.current):
        for dest in world.reachable(unit):
            path = world.path_to(unit, dest)
            assert path[0] == unit.pos and path[-1] == dest and len(path) - 1 <= unit.info.movement
            for a, b in zip(path, path[1:]):
                assert World.distance(a, b) == 1 and world.can_enter(unit, b)
            for step in path[1:-1]:
                assert world.tile(step).terrain is Terrain.FIELD, "forest and mountains end a move"
                assert not any((n := world.unit_at(p)) and n.tribe != unit.tribe for p in world.neighbors(step)), "zone of control"
            checked += 1
    assert checked > 0


def test_fog_hides_targets_until_the_tile_is_explored() -> None:
    world = flat_world()
    archer = world.spawn_unit(0, UnitType.ARCHER, (4, 4))
    lurker = world.spawn_unit(1, UnitType.WARRIOR, (6, 4))
    assert not world.explored(0, (6, 4)) and lurker not in world.attack_targets(archer)
    world.explore(0, (6, 4), 0)
    assert lurker in world.attack_targets(archer)


def test_retaliation_only_within_the_defenders_range() -> None:
    world = flat_world()
    world.tribes[0].explored.update(world.neighbors((4, 4), 3))
    archer = world.spawn_unit(0, UnitType.ARCHER, (4, 4))
    enemy_archer = world.spawn_unit(1, UnitType.ARCHER, (6, 4))
    result = world.attack(archer, enemy_archer)
    assert result.damage_taken > 0, "an archer two tiles away shoots back"
    warrior = world.spawn_unit(0, UnitType.WARRIOR, (5, 5))
    enemy_archer.hp = 10
    result = world.attack(warrior, enemy_archer)
    assert result.damage_taken > 0, "an adjacent archer shoots back too"
    world.end_turn()
    world.end_turn()
    far = world.spawn_unit(1, UnitType.WARRIOR, (2, 4))
    result = world.attack(archer, far)
    assert result.damage_taken == 0, "a warrior cannot reach an archer two tiles away"


def test_melee_kill_advances_into_a_village_that_can_be_captured_next_turn() -> None:
    world = flat_world()
    world.tribes[0].explored.update(world.neighbors((4, 4), 3))
    world.tile((5, 4)).village = True
    attacker = world.spawn_unit(0, UnitType.WARRIOR, (4, 4))
    squatter = world.spawn_unit(1, UnitType.WARRIOR, (5, 4))
    squatter.hp = 1
    world.attack(attacker, squatter)
    assert attacker.pos == (5, 4) and not world.can_capture(attacker)
    world.end_turn()
    world.end_turn()
    assert world.can_capture(attacker)
    assert world.capture(attacker).tribe == 0


def test_capturing_an_enemy_city_transfers_its_territory_and_income() -> None:
    world = flat_world(tribes=3)
    world.tribes[0].human = False
    world.found_city(2, (8, 1), "Third", capital=True)
    away = world.capital_of(1)
    world._grow(away, 5)  # level 3, radius 2
    income_before = world.income(0)
    raider = world.spawn_unit(0, UnitType.WARRIOR, away.pos)
    world.capture(raider)
    assert world.owner_of((6, 6)) == 0 and world.owner_of((8, 8)) == 0
    assert world.income(0) == income_before + 3 and world.income(1) == 0
    assert not world.tribes[1].alive and world.winner is None
    assert world.unit_cap(0) == 2 + 4


def test_growth_can_climb_several_levels_at_once() -> None:
    world = flat_world()
    home = world.capital_of(0)
    world._grow(home, 2 + 3 + 4)
    assert (home.level, home.population, home.radius, home.has_wall) == (4, 0, 2, False)
    assert home.pending_reward  # walls are a reward now, not a level
    assert world.owner_of((3, 3)) == 0 and world.explored(0, (3, 3))


def test_capital_placement_does_not_favour_the_first_tribe() -> None:
    """Farthest-point picking used to leave tribe 0 central and push the others to the map edge."""
    edge_sum = [0, 0, 0]
    for seed in range(1, 41):
        world = mapgen.generate(seed=seed, size=14, tribe_count=3)
        for tribe in range(3):
            c = world.capital_of(tribe)
            edge_sum[tribe] += min(c.x, c.y, world.size - 1 - c.x, world.size - 1 - c.y)
    assert max(edge_sum) - min(edge_sum) <= 25, edge_sum


# -- Tribes, ruins and rewards ---------------------------------------------------------


def test_tribes_start_with_their_own_tech_and_the_player_can_be_any_tribe() -> None:
    world = flat_world(tribes=2)
    assert world.tribes[0].techs == {Tech.FISHING} and world.tribes[1].techs == {Tech.HUNTING}
    tiles = [[Tile(x, y, Terrain.FIELD) for x in range(6)] for y in range(6)]
    rotated = World(6, tiles, 3, first_tribe=2)
    assert [t.name for t in rotated.tribes] == ["Moss", "Amber", "Azure"]
    assert rotated.tribes[0].human and rotated.tribes[0].techs == {Tech.ORGANIZATION}
    copy = World.from_dict(rotated.to_dict())
    assert [(t.name, t.color) for t in copy.tribes] == [(t.name, t.color) for t in rotated.tribes]


def test_maps_scatter_a_few_ruins_on_empty_land_clear_of_villages_and_capitals() -> None:
    for seed in range(1, 6):
        world = mapgen.generate(seed=seed, size=14, tribe_count=3)
        ruins = [t for t in world.all_tiles() if t.ruin]
        assert 2 <= len(ruins) <= 14 * 14 // 45
        for tile in ruins:
            assert tile.terrain is not Terrain.WATER and tile.resource is None and not tile.village and tile.city_id is None
            assert all(World.distance(tile.pos, c.pos) >= 3 for c in world.cities.values())
            assert all(World.distance(tile.pos, o.pos) >= 3 for o in ruins if o is not tile)
        assert World.from_dict(world.to_dict()).tile(ruins[0].pos).ruin


def _ruin_kind(pos: tuple[int, int], round_: int) -> Discovery:
    return list(Discovery)[(pos[0] * 31 + pos[1] * 17 + round_ * 7) % len(Discovery)]


def _walk_onto_ruin(world: World, kind: Discovery):
    """Spawn a warrior next to a fresh ruin whose finding will be *kind*, and step on it."""
    for pos in world.neighbors((5, 5), 3):
        step = (pos[0] + 1, pos[1])
        if _ruin_kind(pos, world.round) is kind and world.unit_at(pos) is None and world.unit_at(step) is None and world.city_at(pos) is None:
            world.tile(pos).ruin = True
            unit = world.spawn_unit(0, UnitType.WARRIOR, step)
            world.move(unit, pos)
            return pos
    raise AssertionError(f"no spot for {kind}")


def test_ruins_yield_treasure_knowledge_settlers_or_a_map_and_then_vanish() -> None:
    world = flat_world()
    tribe = world.tribes[0]
    home = world.capital_of(0)
    stars = tribe.stars
    pos = _walk_onto_ruin(world, Discovery.TREASURE)
    assert tribe.stars == stars + RUIN_TREASURE and not world.tile(pos).ruin
    _walk_onto_ruin(world, Discovery.KNOWLEDGE)
    assert tribe.techs == {Tech.FISHING, Tech.CLIMBING}  # the cheapest tech we could research
    _walk_onto_ruin(world, Discovery.GROWTH)
    assert home.level == 2 and home.pending_reward  # +2 pop levels a fresh capital
    pos = _walk_onto_ruin(world, Discovery.VISION)
    assert all(world.explored(0, p) for p in world.neighbors(pos, RUIN_VISION_RADIUS))
    kinds = [f.kind for f in world.take_findings()]
    assert kinds == [Discovery.TREASURE, Discovery.KNOWLEDGE, Discovery.GROWTH, Discovery.VISION]
    assert world.take_findings() == []
    assert any("explored ruins" in line for line in world.log)


def test_knowledge_falls_back_to_treasure_when_nothing_is_left_to_learn() -> None:
    world = flat_world()
    world.tribes[0].techs.update(Tech)
    stars = world.tribes[0].stars
    _walk_onto_ruin(world, Discovery.KNOWLEDGE)
    assert world.tribes[0].stars == stars + RUIN_TREASURE


def test_a_new_level_offers_two_rewards_and_blocks_the_turn_until_one_is_picked() -> None:
    world = flat_world()
    home = world.capital_of(0)
    world._grow(home, 2)
    assert home.pending_reward and world.reward_options(home) == (Reward.WORKSHOP, Reward.EXPLORER)
    with pytest.raises(RuleError, match="choose its reward"):
        world.end_turn()
    with pytest.raises(RuleError, match="not on offer"):
        world.choose_reward(home, Reward.WALLS)
    income = world.income(0)
    world.choose_reward(home, Reward.WORKSHOP)
    assert not home.pending_reward and world.income(0) == income + 1
    with pytest.raises(RuleError, match="no reward"):
        world.choose_reward(home, Reward.WORKSHOP)
    world.end_turn()
    assert world.current == 1


def test_every_reward_does_what_it_says() -> None:
    world = flat_world()
    home = world.capital_of(0)
    tribe = world.tribes[0]
    world._grow(home, 2)
    world.choose_reward(home, Reward.EXPLORER)
    assert world.explored(0, (5, 5))
    world._grow(home, 3)
    world.choose_reward(home, Reward.WALLS)
    guard = world.spawn_unit(0, UnitType.WARRIOR, home.pos)
    assert home.has_wall and world.defense_bonus(guard) == 4.0
    world._grow(home, 4)
    assert world.reward_options(home) == (Reward.BORDER, Reward.POPULATION)
    world.choose_reward(home, Reward.BORDER)
    assert home.radius == 3 and world.owner_of((4, 4)) == 0
    world._grow(home, 5)
    score = world.score(0)
    world.choose_reward(home, Reward.PARK)
    assert world.score(0) == score + REWARD_PARK_SCORE
    world._grow(home, 6)
    assert world.reward_options(home) == (Reward.PARK, Reward.RESOURCES)
    stars = tribe.stars
    world.choose_reward(home, Reward.RESOURCES)
    assert tribe.stars == stars + REWARD_STARS


def test_the_population_reward_can_reach_the_next_level_and_offer_again() -> None:
    world = flat_world()
    home = world.capital_of(0)
    world._grow(home, 2 + 3 + 4)
    home.population = 2
    world.choose_reward(home, Reward.POPULATION)
    assert home.level == 5 and home.population == 0 and home.pending_reward
    assert world.reward_options(home) == (Reward.PARK, Reward.RESOURCES)


def test_ai_picks_rewards_and_marches_on_ruins() -> None:
    world = flat_world()
    world.tribes[0].human = False
    home = world.capital_of(0)
    world._grow(home, 2)
    world.tile((6, 1)).ruin = True
    world.explore(0, (6, 1), 0)  # the ruins are in sight
    scout = world.spawn_unit(0, UnitType.WARRIOR, (3, 1))
    world.tribes[0].stars = 0
    rng = random.Random(4)
    ai.take_turn(world, 0, rng)
    assert not home.pending_reward and home.workshop
    assert World.distance(scout.pos, (6, 1)) < 3
    world.end_turn()
    ai.take_turn(world, 0, rng)
    world.end_turn()
    ai.take_turn(world, 0, rng)
    assert not world.tile((6, 1)).ruin and any("explored ruins" in line for line in world.log)


# -- The wider tech tree -----------------------------------------------------------


def test_forestry_lets_units_keep_moving_through_forests() -> None:
    world = flat_world()
    for x in range(10):
        world.tile((x, 3)).terrain = Terrain.FOREST
    rider = world.spawn_unit(0, UnitType.RIDER, (4, 4))
    assert (4, 2) not in world.reachable(rider)  # the forest belt ends the move
    world.tribes[0].techs.add(Tech.FORESTRY)
    assert (4, 2) in world.reachable(rider)


def test_roads_add_a_move_when_starting_on_home_soil() -> None:
    world = flat_world()
    home_guard = world.spawn_unit(0, UnitType.WARRIOR, (1, 2))
    abroad = world.spawn_unit(0, UnitType.WARRIOR, (6, 6))
    assert (1, 4) not in world.reachable(home_guard)
    world.tribes[0].techs.add(Tech.ROADS)
    assert (1, 4) in world.reachable(home_guard)
    assert (6, 8) not in world.reachable(abroad)


def test_meditation_heals_idle_units_more() -> None:
    world = flat_world()
    hurt = world.spawn_unit(0, UnitType.WARRIOR, (1, 2))
    hurt.hp = 1
    world.end_turn()
    assert hurt.hp == 5
    hurt.hp = 1
    world.tribes[0].techs.add(Tech.MEDITATION)
    world.end_turn()
    world.end_turn()
    assert hurt.hp == 7


def test_navigation_pays_coastal_cities_and_trade_pays_every_city() -> None:
    world = flat_world()
    home = world.capital_of(0)
    assert world.city_income(home) == 2
    world.tribes[0].techs.add(Tech.NAVIGATION)
    assert world.city_income(home) == 2  # no water nearby
    world.tile((0, 0)).terrain = Terrain.WATER
    assert world.city_income(home) == 3
    world.tribes[0].techs.add(Tech.TRADE)
    assert world.city_income(home) == 4 and world.income(0) == 4


def test_construction_cheapens_harvests_and_aquaculture_fattens_fish() -> None:
    world = flat_world()
    world.tile((2, 1)).resource = Resource.FISH
    world.tile((1, 2)).resource = Resource.FISH
    world.tribes[0].stars = 10
    home = world.capital_of(0)
    world.harvest(0, (2, 1))
    assert world.tribes[0].stars == 8 and home.population == 1
    world.tribes[0].techs.update({Tech.CONSTRUCTION, Tech.AQUACULTURE})
    assert world.harvest_cost(0, Resource.FISH) == 1 and world.harvest_yield(0, Resource.FISH) == 2
    world.harvest(0, (1, 2))
    assert world.tribes[0].stars == 7 and home.level == 2  # 1 + 2 pop reaches level 2


def test_cartography_reveals_every_coastline() -> None:
    world = flat_world()
    world.tile((8, 2)).terrain = Terrain.WATER
    world.tribes[0].techs.update({Tech.NAVIGATION})
    world.tribes[0].stars = 100
    assert not world.explored(0, (8, 2))
    world.research(0, Tech.CARTOGRAPHY)
    assert world.explored(0, (8, 2)) and world.explored(0, (7, 3)) and not world.explored(0, (5, 5))


def test_catapults_strike_from_three_tiles_and_never_hit_back() -> None:
    world = flat_world()
    world.tribes[0].techs.update({Tech.MATHEMATICS, Tech.SMITHERY})
    catapult = world.spawn_unit(0, UnitType.CATAPULT, (4, 4))
    swordsman = world.spawn_unit(0, UnitType.SWORDSMAN, (5, 5))
    target = world.spawn_unit(1, UnitType.WARRIOR, (7, 4))
    world.explore(0, (7, 4), 0)  # in sight
    result = world.attack(catapult, target)
    assert result.damage_dealt >= 8 and result.damage_taken == 0
    world.end_turn()
    raider = world.spawn_unit(1, UnitType.WARRIOR, (3, 4))
    hit = world.attack(raider, catapult)
    assert hit.damage_taken == 0 and hit.damage_dealt == 9  # no defence at all
    assert swordsman.max_hp == 15 and world.can_train(world.capital_of(0), UnitType.SWORDSMAN) != "Requires Smithery"
