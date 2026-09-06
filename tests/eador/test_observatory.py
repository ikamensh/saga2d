"""A paid observatory approach is a saved, finite hold adventure."""
from eador.model import State


def test_purchased_observatory_army_holds_the_cleared_lane_and_survives_every_saved_order():
    """A real earned army secures the hill before the deadline while enemies remain alive."""
    from tools.eador_observatory_campaign import prepare_observatory, observatory_route
    from tests.eador.test_extraction_journeys import Journey

    state = prepare_observatory()
    crystals = state.crystals
    assert {'barracks', 'market', 'temple'} <= state.buildings
    assert [troop.kind for troop in state.hero.army][-3:] == ['warden', 'sapper', 'healer']
    play = observatory_route(state, 'clear', orders_type=Journey)
    assert state.crystals == crystals - 2
    assert play.battle.outcome_reason == 'hold' and play.battle.outcome == 'player'
    assert play.battle.objective.progress == 2 and play.battle.round <= 8
    assert all(u.alive for u in play.battle.units if u.team == 'player')
    assert any(u.alive for u in play.battle.units if u.team == 'enemy')
    assert State.from_json(play.state.to_json()).to_json() == play.state.to_json()
    assert_one_hold_reward(play)


def test_actual_prior_barrow_save_keeps_its_site_and_complete_continuation():
    """Authored placement affects new worlds only; an old active Barrow stays exact."""
    import json
    from pathlib import Path
    from tools.eador_campaign import finish_battle

    fixtures = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixtures / 'v11_ruins_barrow_battle.json').read_text())
    assert state.provinces[(-1, 0)].site_kind == 'barrow'
    assert not any(p.site_kind == 'broken_observatory' for p in state.provinces.values())
    finish_battle(state)
    actual = json.loads(state.to_json())
    expected = json.loads((fixtures / 'v11_ruins_barrow_battle_result.json').read_text())
    assert actual.pop('rules_id') == 'standard-1'
    actual.pop('schema_version'); expected.pop('schema_version')
    assert actual == expected


def test_a_purchased_rune_army_can_keep_the_forest_and_push_the_final_contester_off_the_hill():
    """The same Rune orders hold in either approach; the paid terrain saves wounds, not a phase."""
    from tools.eador_observatory_campaign import prepare_observatory, observatory_rune_route
    from tests.eador.test_extraction_journeys import Journey

    before = prepare_observatory(support='adept').to_json()
    free = observatory_rune_route(State.from_json(before), orders_type=Journey)
    paid = observatory_rune_route(State.from_json(before), 'clear', orders_type=Journey)
    assert free.state.crystals == paid.state.crystals + 2
    assert free.battle.round == paid.battle.round == 5
    assert free.battle.mana == paid.battle.mana
    assert free.orders == paid.orders
    assert sum(u.hp for u in free.battle.units if u.team == 'player') < sum(u.hp for u in paid.battle.units if u.team == 'player')
    for play in (free, paid):
        assert play.battle.outcome_reason == 'hold'
        assert all(u.alive for u in play.battle.units if u.team == 'player')
        assert any(u.alive for u in play.battle.units if u.team == 'enemy')
        assert any(command == 'repulse' for command, *_ in play.orders)
        assert_one_hold_reward(play)


def assert_one_hold_reward(play):
    import pytest
    from eador.model import RuleError

    state, battle = play.state, play.battle
    assert battle.outcome_reason == 'hold' and any(u.alive for u in battle.units if u.team == 'enemy')
    gold, crystals, reward, pos = state.gold, state.crystals, state.battle_adventure, state.hero.pos
    state.resolve_battle()
    assert state.gold == gold + reward.gold and state.crystals == crystals + reward.crystals
    assert state.provinces[pos].explored
    state = State.from_json(state.to_json())
    while state.choice:
        state.choose(state.choice.options[0].id)
        state = State.from_json(state.to_json())
    before = state.to_json()
    with pytest.raises(RuleError):
        state.explore()
    with pytest.raises(RuleError):
        state.resolve_battle()
    assert state.to_json() == before


def test_paid_lane_changes_reach_and_opposing_sight_without_replacing_guards_or_rewards():
    """The fee changes a visible terrain choice, not hidden combat strength or free defenders."""
    from tools.eador_observatory_campaign import prepare_observatory
    before = prepare_observatory().to_json()
    free, paid = State.from_json(before), State.from_json(before)
    free.explore(approach='covered'); paid.explore(approach='clear')
    assert free.crystals == paid.crystals + 2
    assert free.battle.objective == paid.battle.objective
    assert [u for u in free.battle.units if u.team == 'enemy'] == [u for u in paid.battle.units if u.team == 'enemy']
    assert free.battle_adventure.gold == paid.battle_adventure.gold
    assert free.battle_adventure.crystals == paid.battle_adventure.crystals
    assert free.battle_adventure.relic == paid.battle_adventure.relic
    changed = {pos for pos in free.battle.terrain if free.battle.terrain[pos] != paid.battle.terrain[pos]}
    assert changed == {(-1, 0)}
    for state in (free, paid):
        state.battle.move(1, (0, -1))  # Vacate the hero's starting road.
    assert (0, 0) in paid.battle.reachable(0) and (0, 0) not in free.battle.reachable(0)
    for a, b in (((-2, 0), (1, 0)), ((1, 0), (-2, 0))):
        assert paid.battle.has_sight(a, b) and not free.battle.has_sight(a, b)
    assert State.from_json(free.to_json()).to_json() == free.to_json()
    assert State.from_json(paid.to_json()).to_json() == paid.to_json()


def test_failed_cleared_attempt_keeps_its_fee_and_finite_wounds_on_a_saved_free_retry():
    """One killed marksman and the guard's wounds cannot regenerate when changing approaches."""
    from tools.eador_observatory_campaign import prepare_observatory, observatory_route
    from tools.eador_campaign import finish_battle, march_to, rest

    before = prepare_observatory().to_json()
    successful = observatory_route(State.from_json(before), 'clear')
    state = State.from_json(before)
    crystals, xp = state.crystals, state.hero.xp
    state.explore(approach='clear')
    phases = 0
    for command, args, kwargs in successful.orders:
        getattr(state.battle, command)(*args, **kwargs)
        phases += command == 'end_turn'
        if phases == 2:
            break
    surviving = [(u.kind, u.hp) for u in state.battle.units if u.team == 'enemy' and u.alive]
    assert len(surviving) == 3 and surviving[0][1] < 42
    state = State.from_json(state.to_json()); state.retreat()
    assert state.crystals == crystals - 2 and state.hero.xp == xp
    state = State.from_json(state.to_json())
    province = state.provinces[(-1, 0)]
    assert list(zip(province.site_guards, province.site_guard_hp)) == surviving
    if not state.actions_left:
        rest(state)
    march_to(state, (-1, 0))
    before_gold, before_crystals = state.gold, state.crystals
    state.explore(approach='covered')
    assert state.crystals == before_crystals
    assert [(u.kind, u.hp) for u in state.battle.units if u.team == 'enemy'] == surviving
    state = State.from_json(state.to_json())
    reward = state.battle_adventure
    finish_battle(state)
    assert state.provinces[(-1, 0)].explored
    assert state.gold == before_gold + reward.gold and state.crystals == before_crystals + reward.crystals


def test_new_ruins_get_exactly_one_observatory_and_keep_crown_and_required_sources():
    """Fixed new-world placement never overwrites the home opening or unique equipment sources."""
    for seed in range(100):
        state = State.new(seed, theme='ruins')
        assert sum(p.site_kind == 'broken_observatory' for p in state.provinces.values()) == 1
        assert state.provinces[(-1, 0)].site_kind == 'broken_observatory'
        assert state.provinces[(-2, 0)].site_kind == 'shrine'
        assert state.provinces[(-2, 2)].site_kind == 'den'
        assert state.provinces[(-1, 2)].site_kind == 'explorer_camp'
        assert state.provinces[(-1, 1)].site_kind == 'sealed_vault'
        assert state.provinces[(-1, 1)].site_relic == 'mirror_badge'
        assert sum(p.site_kind == 'border_watch' for p in state.provinces.values()) == 1
        assert state.provinces[(0, 0)].site_relic == state.provinces[(1, 0)].site_relic == 'iron_crown'
    for theme in ('frontier', 'elderwild'):
        assert not any(p.site_kind == 'broken_observatory' for p in State.new(7, theme=theme).provinces.values())
