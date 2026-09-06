"""Finite control orders change legal plans without granting replacement actions."""
from dataclasses import asdict

from eador.battle import Battle


def test_militia_rally_releases_a_real_enemy_pin_without_refreshing_orders():
    """A cheap adjacent reserve restores the Ranger's route, not a second move or shot."""
    battle = Battle.clash([('ranger', 22), ('militia', 24)], [('archer', 20)], 'plains')
    battle.move(0, (0, 0)); battle.move(1, (-1, 0))
    battle.guard(0); battle.guard(1); battle.end_turn()
    assert battle.unit(0).pinned
    before, limited = battle.to_dict(), battle.reachable(0)
    forecast = battle.rally_preview(1, 0)
    assert battle.to_dict() == before and limited < forecast.reachable
    target_before = asdict(battle.unit(0))
    battle.rally(1, 0)
    assert battle.reachable(0) == forecast.reachable
    assert battle.unit(0).effective_move_range == forecast.move_range
    assert asdict(battle.unit(0)) == {**target_before, 'pinned': False}
    assert battle.unit(1).acted and battle.unit(1).moved
    restored = Battle.from_dict(battle.to_dict())
    destination = min(forecast.reachable - limited)
    restored.move(0, destination)
    assert restored.unit(0).pos == destination


def test_new_militia_ability_saves_while_a_real_v10_extraction_continues_exactly():
    """Updating the registry must not teach an ability to a battle already in progress."""
    import json
    from pathlib import Path
    from eador.model import State
    from tools.eador_campaign import finish_battle
    fresh = State.new(7); fresh.explore()
    assert any(u.can_rally for u in fresh.battle.units)
    assert State.from_json(fresh.to_json()).to_json() == fresh.to_json()
    fixtures = Path(__file__).parent / 'fixtures'
    legacy = State.from_json((fixtures / 'v10_pinned_crossing.json').read_text())
    assert legacy.battle.unit(0).pinned and not any(u.can_rally for u in legacy.battle.units)
    finish_battle(legacy)
    actual = json.loads(legacy.to_json())
    expected = json.loads((fixtures / 'v10_pinned_crossing_result.json').read_text())
    actual.pop('schema_version'); expected.pop('schema_version')
    assert actual == expected


def test_rally_of_a_spent_ally_clears_only_pin_and_invalid_orders_are_atomic():
    """Rally cannot create an extra turn, clear enemy Pin, or be used twice."""
    import pytest
    from eador.model import RuleError
    battle = Battle.clash([('ranger', 22), ('militia', 24)], [('archer', 20)], 'plains')
    battle.move(0, (0, 0)); battle.move(1, (-1, 0))
    battle.guard(0); battle.guard(1); battle.end_turn(); battle.guard(0)
    assert battle.unit(0).pinned and not battle.rally_preview(1, 0).reachable
    target_before = asdict(battle.unit(0))
    battle.rally(1, 0)
    assert asdict(battle.unit(0)) == {**target_before, 'pinned': False}
    before = battle.to_dict()
    for command, arguments in ((battle.rally, (1, 0)), (battle.rally, (1000, 0)),
                                (battle.move, (0, (0, 1))), (battle.attack, (0, 1000))):
        with pytest.raises(RuleError):
            command(*arguments)
        assert battle.to_dict() == before


def test_smoke_blocks_both_sides_and_shared_magic_then_expires_before_its_team():
    """A finite screen protects an approach at the cost of allied fire and healing."""
    from eador.battle import BattleUnit
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    battle = Battle([
        BattleUnit(0, 'player', 'hero', (-2, 0), 20, 30, 10, 3, 3, 2),
        BattleUnit(1, 'player', 'sapper', (-2, 1), 26, 26, 7, 2, 3, 1, abilities=('smoke',)),
        BattleUnit(2, 'player', 'archer', (-1, 0), 20, 20, 8, 1, 3, 3, abilities=('pin',)),
        BattleUnit(1000, 'enemy', 'archer', (1, 0), 20, 20, 8, 1, 3, 3, abilities=('pin',)),
    ], terrain, 12, {'bolt', 'heal'})
    assert battle.unit(1000) in battle.targets(2) and battle.unit(0) in battle.spell_targets('heal')
    before = battle.to_dict(); forecast = battle.smoke_preview(1, (-1, 0))
    assert battle.to_dict() == before
    battle.smoke(1, (-1, 0))
    assert battle.smoke_clouds == [forecast] and battle.unit(1).spent_abilities == ('smoke',)
    assert battle.targets(2) == [] and battle.unit(2) not in battle.targets(1000)
    assert battle.pin_targets(2) == [] and battle.spell_targets('bolt') == []
    assert battle.unit(0) in battle.spell_targets('heal')  # Seeing oneself always works.
    assert not battle.smoke_targets(1)
    battle = Battle.from_dict(battle.to_dict())
    battle.end_turn()
    assert battle.smoke_clouds == [] and battle.unit(1).spent_abilities == ('smoke',)


def test_paid_sapper_consumes_both_resources_and_saved_smoke_keeps_its_charge():
    """The special recruit must compete for crystals and a slot, with no charge refill on load."""
    from eador.model import State
    state = State.new(7); state.build('market')
    while state.gold < state.recruit_cost('sapper'):
        state.end_turn()
    gold, crystals = state.gold, state.crystals
    state.recruit('sapper')
    assert state.gold == gold - state.recruit_cost('sapper')
    assert state.crystals == crystals - state.recruit_crystal_cost('sapper')
    state.explore(); battle = state.battle
    sapper = next(u for u in battle.units if u.kind == 'sapper')
    battle.smoke(sapper.id, sapper.pos)
    loaded = State.from_json(state.to_json())
    assert loaded.to_json() == state.to_json()
    assert not loaded.battle.smoke_targets(sapper.id)
    assert loaded.battle.smoke_clouds == battle.smoke_clouds


def test_forest_blocks_ranged_orders_and_auto_play_moves_to_legal_sight():
    """The shooter must change position; rejecting its old ranged action is not an AI policy."""
    from eador.battle import BattleUnit
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    terrain[(-1, 0)] = 'forest'
    battle = Battle([BattleUnit(0, 'player', 'hero', (-2, 0), 30, 30, 10, 3, 3, 2),
                     BattleUnit(1000, 'enemy', 'guard', (1, 0), 42, 42, 12, 4, 3, 1)],
                    terrain, 12, {'bolt'})
    assert battle.spell_targets('bolt') == []
    before = battle.to_dict()
    assert not battle.has_sight((-2, 0), (1, 0)) and battle.to_dict() == before
    battle.auto_turn()
    assert battle.unit(0).pos != (-2, 0) and battle.unit(1000).hp < 42


def test_repulse_displaces_a_contester_once_without_damage_or_order_changes():
    """Forced position opens a seal; it never silently awards progress or refreshes the target."""
    from eador.battle import BattleUnit, BattleObjective
    from eador.model import RuleError
    import pytest
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    battle = Battle([BattleUnit(0, 'player', 'adept', (0, 0), 28, 28, 6, 2, 3, 2, abilities=('repulse',)),
                     BattleUnit(1000, 'enemy', 'guard', (1, 0), 42, 42, 12, 4, 3, 1, pinned=True)],
                    terrain, 0, set(), hero_id=None,
                    objective=BattleObjective('hold', (0, 0), required=2, deadline=8))
    before = battle.to_dict(); target = asdict(battle.unit(1000))
    destination = battle.repulse_preview(0, 1000)
    assert battle.to_dict() == before and destination == (2, 0)
    battle.repulse(0, 1000)
    assert asdict(battle.unit(1000)) == {**target, 'pos': destination}
    assert battle.unit(0).acted and battle.unit(0).moved and battle.objective.progress == 0
    assert battle.unit(0).spent_abilities == ('repulse',)
    before = battle.to_dict()
    with pytest.raises(RuleError): battle.repulse(0, 1000)
    assert battle.to_dict() == before
    assert Battle.from_dict(before).to_dict() == before


def test_flight_crosses_an_occupied_screen_but_pin_and_brace_still_counter_it():
    """Flying permits crossing bodies, never occupied landings or free melee attacks."""
    from eador.battle import BattleUnit
    terrain = {(q, r): 'marsh' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    directions = ((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1))
    enemies = [BattleUnit(1000+i, 'enemy', 'pikeman', pos, 28, 28, 9, 3, 2, 1, stance='brace')
               for i, pos in enumerate(directions)]
    flyer = BattleUnit(0, 'player', 'skyrider', (0, 0), 28, 28, 10, 2, 4, 1, abilities=('fly',))
    battle = Battle([flyer, *enemies], terrain, 0, set(), hero_id=None)
    unpinned = battle.reachable(0)
    assert (3, 0) in unpinned and not set(directions) & unpinned
    pinned = Battle.from_dict(battle.to_dict())
    pinned.unit(0).pinned = True  # The fixture isolates the existing status counter.
    assert pinned.reachable(0) < unpinned and (3, 0) not in pinned.reachable(0)
    battle.move(0, (2, 0))
    target_before, attacker_before = battle.unit(1000).hp, battle.unit(0).hp
    forecast = battle.preview(0, 1000)
    battle.attack(0, 1000)
    assert (target_before-battle.unit(1000).hp, attacker_before-battle.unit(0).hp) == forecast
    assert forecast[1] > 0 and not battle.reachable(0)


def test_auto_control_clears_the_carriers_exit_before_the_hero_spends_its_action():
    """Support acts before ID-ordered hero magic when it can immediately enable evacuation."""
    from eador.battle import BattleUnit, BattleObjective
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    battle = Battle([BattleUnit(0, 'player', 'hero', (0, 0), 30, 30, 10, 3, 3, 1),
                     BattleUnit(1, 'player', 'adept', (1, -1), 28, 28, 6, 2, 3, 2, abilities=('repulse',)),
                     BattleUnit(1000, 'enemy', 'guard', (1, 0), 42, 42, 12, 4, 3, 1)],
                    terrain, 12, {'bolt'}, objective=BattleObjective('extract', deadline=8, exits=((0, 0),)))
    battle.auto_turn()
    assert battle.outcome_reason == 'escape' and battle.unit(1000).hp == 42
    assert battle.unit(1).spent_abilities == ('repulse',) and battle.mana == 12


def test_auto_rally_restores_an_unspent_escape_route_but_never_refills_cargo():
    """A reserve clears Pin before the carrier moves; full cargo still costs one movement."""
    from eador.battle import BattleUnit, BattleObjective
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    battle = Battle([BattleUnit(0, 'player', 'hero', (0, 0), 30, 30, 10, 3, 3, 1, pinned=True, cargo_penalty=1),
                     BattleUnit(1, 'player', 'militia', (-1, 0), 24, 24, 8, 2, 3, 1, abilities=('rally',)),
                     BattleUnit(1000, 'enemy', 'archer', (-3, 3), 20, 20, 8, 1, 3, 3)],
                    terrain, 12, {'bolt'}, objective=BattleObjective('extract', deadline=8, exits=((2, 0),)))
    assert battle.rally_preview(1, 0).move_range == 2
    battle.auto_turn()
    assert battle.outcome_reason == 'escape' and battle.unit(1).acted
    assert battle.unit(0).cargo_penalty == 1 and not battle.unit(0).pinned


def test_automatic_smoke_uses_one_real_screen_and_enemy_cloud_lasts_into_player_turn():
    """Both policies spend a finite charge; enemy smoke survives until that enemy team next begins."""
    from eador.battle import BattleUnit
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    battle = Battle([BattleUnit(1, 'enemy', 'sapper', (-1, 1), 26, 26, 7, 2, 3, 1, abilities=('smoke',)),
                     BattleUnit(2, 'enemy', 'militia', (-1, 0), 24, 24, 8, 2, 3, 1),
                     BattleUnit(1000, 'player', 'archer', (1, 0), 20, 20, 8, 1, 3, 3),
                     BattleUnit(1001, 'player', 'goblin', (1, 1), 16, 16, 6, 1, 3, 2)],
                    terrain, 0, set(), hero_id=None)
    battle.guard(1000); battle.guard(1001); battle.end_turn()
    assert battle.unit(1).spent_abilities == ('smoke',)
    assert len(battle.smoke_clouds) == 1 and battle.smoke_clouds[0].expires_before_team == 'enemy'
    clone = Battle.from_dict(battle.to_dict())
    battle.end_turn(); clone.end_turn()
    assert battle.to_dict() == clone.to_dict() and battle.smoke_clouds == []
    assert battle.unit(1).spent_abilities == ('smoke',)



def test_flying_policy_chooses_the_less_exposed_ranged_flank():
    """Equal attack access should not send a fragile flyer into the nearest spear point."""
    from eador.battle import BattleUnit
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    battle = Battle([BattleUnit(0, 'player', 'skyrider', (-3, 1), 28, 28, 10, 2, 4, 1, abilities=('fly',)),
                     BattleUnit(1000, 'enemy', 'pikeman', (0, 0), 28, 28, 9, 3, 2, 1, stance='brace'),
                     BattleUnit(1001, 'enemy', 'archer', (0, 2), 20, 20, 8, 1, 3, 3)],
                    terrain, 0, set(), hero_id=None)
    battle.auto_turn()
    assert battle.unit(1001).hp < 20
    assert battle.grid.distance(battle.unit(0).pos, (0, 0)) > 1


def test_repulse_respects_anchored_units_occupied_landings_and_board_edges():
    """Every denied displacement preserves the charge, positions and orders."""
    from eador.battle import BattleUnit
    from eador.model import RuleError
    import pytest
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    for stance, actor_pos, target_pos, blocker in (
        ('guard', (0, 0), (1, 0), None), ('brace', (0, 0), (1, 0), None),
        (None, (0, 0), (1, 0), (2, 0)), (None, (2, 0), (3, 0), None),
    ):
        battle = Battle([
            BattleUnit(0, 'player', 'adept', actor_pos, 28, 28, 6, 2, 3, 2, abilities=('repulse',)),
            BattleUnit(1000, 'enemy', 'pikeman', target_pos, 28, 28, 9, 3, 2, 1, stance=stance),
        ], terrain, 0, set(), hero_id=None)
        if blocker:
            battle.units.append(BattleUnit(1001, 'enemy', 'guard', blocker, 42, 42, 12, 4, 3, 1))
        before = battle.to_dict()
        assert battle.repulse_targets(0) == []
        for command in (battle.repulse_preview, battle.repulse):
            with pytest.raises(RuleError):
                command(0, 1000)
            assert battle.to_dict() == before


def test_damaged_save_cannot_keep_player_smoke_while_refunding_its_order():
    """A live player cloud belongs to a Smoke order spent in this player phase."""
    import json
    import pytest
    from eador.model import State, SaveFormatError
    state = State.new(7); state.build('market')
    while state.gold < state.recruit_cost('sapper'):
        state.end_turn()
    state.recruit('sapper'); state.explore()
    sapper = next(u for u in state.battle.units if u.can_smoke)
    state.battle.smoke(sapper.id, sapper.pos)
    original = state.to_json()
    for corruption in ('charge', 'action', 'movement', 'team', 'duplicate', 'outside'):
        data = json.loads(original)
        source = next(u for u in data['battle']['units'] if u['id'] == sapper.id)
        cloud = data['battle']['smoke_clouds'][0]
        if corruption == 'charge': source['spent_abilities'] = []
        elif corruption == 'action': source['acted'] = False
        elif corruption == 'movement': source['moved'] = False
        elif corruption == 'team': cloud['expires_before_team'] = 'enemy'
        elif corruption == 'duplicate': data['battle']['smoke_clouds'].append(dict(cloud))
        else: cloud['pos'] = [4, 0]
        with pytest.raises(SaveFormatError):
            State.from_json(json.dumps(data))
    assert state.to_json() == original


def test_recruitment_with_insufficient_crystals_is_atomic():
    """Gold alone cannot purchase the new crystal-funded roles."""
    from eador.model import State, RuleError
    import pytest
    state = State.new(7); state.build('temple')
    while state.gold < state.recruit_cost('skyrider'):
        state.end_turn()
    state.crystals = state.recruit_crystal_cost('skyrider') - 1
    before = state.to_json()
    with pytest.raises(RuleError):
        state.recruit('skyrider')
    assert state.to_json() == before


def test_killing_the_sapper_keeps_its_existing_cloud_until_the_recorded_phase():
    """Smoke's lifetime belongs to the spent order, not its source's remaining HP."""
    from eador.battle import BattleUnit
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    battle = Battle([
        BattleUnit(1, 'enemy', 'sapper', (-1, 1), 1, 26, 7, 2, 3, 1, abilities=('smoke',)),
        BattleUnit(2, 'enemy', 'militia', (-1, 0), 24, 24, 8, 2, 3, 1),
        BattleUnit(1000, 'player', 'archer', (1, 0), 20, 20, 8, 1, 3, 3),
        BattleUnit(1001, 'player', 'goblin', (1, 1), 16, 16, 6, 1, 3, 2),
        BattleUnit(1002, 'player', 'militia', (0, 1), 24, 24, 12, 2, 3, 1),
    ], terrain, 0, set(), hero_id=None)
    for unit in battle.units:
        if unit.team == 'player':
            battle.guard(unit.id)
    battle.end_turn()
    clouds = list(battle.smoke_clouds)
    assert clouds and battle.unit(1).spent_abilities == ('smoke',)
    battle.attack(1002, 1)
    assert not battle.unit(1).alive and battle.smoke_clouds == clouds
    restored = Battle.from_dict(battle.to_dict())
    battle.end_turn(); restored.end_turn()
    assert battle.to_dict() == restored.to_dict() and battle.smoke_clouds == []
