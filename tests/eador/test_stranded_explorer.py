"""A separated carrier can regroup without requiring a Ranger or a full party."""
from eador.model import State
import pytest

from tools.eador_explorer_campaign import prepare_explorer, explorer_route, explorer_healer_route, explorer_scout_route
from tests.eador.test_extraction_journeys import Journey, assert_one_reward


def test_frontier_explorer_offers_two_free_assemblies_without_replacing_other_sources():
    state = State.new(7)
    assert state.provinces[(0, -1)].site_kind == 'stranded_explorer'
    assert state.provinces[(-2, 0)].site_kind == 'shrine'
    assert state.provinces[(0, -2)].site_kind == 'border_watch'
    assert state.provinces[(-2, 2)].site_kind == 'den'
    assert state.provinces[(-1, 2)].site_kind == 'explorer_camp'
    assert state.provinces[(-1, 1)].site_kind == 'muster_yard'
    assert state.provinces[(0, 2)].site_kind == 'courier_crossing'
    from eador.content import SITES
    approaches = SITES['stranded_explorer'].approaches
    assert [a.id for a in approaches] == ['north', 'south']
    assert all(a.gold_cost == a.crystals_cost == 0 for a in approaches)


@pytest.mark.parametrize('hero_class,support,approach,route,rounds', [
    ('Commander', 'ranger', 'north', explorer_route, 3),
    ('Commander', 'ranger', 'south', explorer_route, 3),
    ('Warrior', 'healer', 'north', explorer_healer_route, 3),
    ('Scout', None, 'north', explorer_scout_route, 2),
])
def test_purchased_parties_escape_both_assemblies_with_no_hidden_ranger_requirement(hero_class, support, approach, route, rounds):
    state = prepare_explorer(hero_class, support=support)
    before = state.to_json()
    initial = State.from_json(before)
    initial.explore(approach=approach)
    isolated = [u for u in initial.battle.units if u.team == 'player' and u.pos[0] > 0]
    assert [u.kind for u in isolated] == (['hero'] if support is None else ['hero', support])
    assert initial.battle.objective.deadline == 6
    assert initial.battle.objective.exits == ((-3, 1),)
    play = (route(state, approach, orders_type=Journey) if support == 'ranger'
            else route(state, orders_type=Journey))
    assert play.battle.round == rounds and play.battle.outcome_reason == 'escape'
    assert len([u for u in play.battle.units if u.team == 'player']) == (5 if support is None else 6)
    assert play.state.gold == initial.gold and play.state.crystals == initial.crystals
    if approach == 'south':
        # This plan first extracts the exposed Archer, then the arriving hero.
        assert [args[1] for command, args, _ in play.orders if command == 'swap'] == [3, 0]
    if support == 'healer':
        assert any(command == 'cast' and kwargs.get('caster_id') == 5 for command, _, kwargs in play.orders)
    assert_one_reward(play)


def test_saved_failed_northern_assembly_keeps_wounded_patrol_on_free_southern_retry():
    from tools.eador_campaign import finish_battle, march_to, rest

    before = prepare_explorer().to_json()
    complete = explorer_route(State.from_json(before))
    state = State.from_json(before)
    state.explore(approach='north')
    gold, crystals, xp = state.gold, state.crystals, state.hero.xp
    for command, args, kwargs in complete.orders:
        getattr(state.battle, command)(*args, **kwargs)
        if command == 'end_turn':
            break
    survivors = [(u.kind, u.hp) for u in state.battle.units if u.team == 'enemy' and u.alive]
    assert len(survivors) == 3 and survivors[0][1] < 28
    state = State.from_json(state.to_json()); state.retreat()
    # The assembly is free; the game's ordinary retreat loss still applies.
    assert (state.gold, state.crystals, state.hero.xp) == (gold - 20, crystals, xp)
    state = State.from_json(state.to_json())
    province = state.provinces[(0, -1)]
    assert list(zip(province.site_guards, province.site_guard_hp)) == survivors
    if not state.actions_left:
        rest(state)
    march_to(state, (0, -1))
    state.explore(approach='south')
    assert [(u.kind, u.hp) for u in state.battle.units if u.team == 'enemy'] == survivors
    assert state.battle_adventure.encounter == 'explorer_south'
    state = State.from_json(state.to_json())
    gold, crystals, reward = state.gold, state.crystals, state.battle_adventure
    finish_battle(state)
    assert state.provinces[(0, -1)].explored
    assert (state.gold, state.crystals) == (gold + reward.gold, crystals + reward.crystals)


def test_one_hundred_frontier_sources_still_include_every_relic_and_prior_adventure():
    from eador.content import RELICS

    for seed in range(100):
        state = State.new(seed)
        assert [p.pos for p in state.provinces.values() if p.site_kind == 'stranded_explorer'] == [(0, -1)]
        themes = [state, State.new(seed, theme='elderwild'), State.new(seed, theme='ruins')]
        assert set(RELICS) <= {p.site_relic for world in themes for p in world.provinces.values()}
        assert {'moonstone', 'watch_bell', 'storm_quiver', 'wayfarer_boots', 'merchant_seal', 'vanguard_drum', 'veil_censer'} <= {p.site_relic for p in state.provinces.values()}
        expected = {(-2, 0): 'shrine', (0, -2): 'border_watch', (-2, 2): 'den',
                    (-1, 2): 'explorer_camp', (-1, 1): 'muster_yard', (0, 2): 'courier_crossing'}
        assert all(state.provinces[pos].site_kind == kind for pos, kind in expected.items())


def test_actual_prior_caravan_battle_keeps_its_site_and_complete_saved_continuation():
    import json
    from pathlib import Path
    from tools.eador_campaign import finish_battle

    fixtures = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixtures / 'v12_frontier_caravan_battle.json').read_text())
    assert state.provinces[(0, -1)].site_kind == 'caravan'
    assert not any(p.site_kind == 'stranded_explorer' for p in state.provinces.values())
    finish_battle(state)
    assert json.loads(state.to_json()) == json.loads((fixtures / 'v12_frontier_caravan_result.json').read_text())


def test_boots_earned_at_camp_make_the_later_explorer_reward_an_explicit_saved_duplicate_choice():
    from eador.model import RuleError

    state = prepare_explorer(collect_boots=True)
    assert state.provinces[(-1, 2)].explored and state.inventory.count('wayfarer_boots') == 1
    play = explorer_route(state, orders_type=Journey)
    state = play.state
    gold, crystals = state.gold, state.crystals
    state.resolve_battle()
    assert (state.gold, state.crystals) == (gold + 55, crystals + 1)
    while state.choice.kind != 'relic':
        state.choose(state.choice.options[0].id)
    assert state.choice.context == 'wayfarer_boots'
    assert [(option.id, option.name) for option in state.choice.options] == [
        ('distill', 'Distill the duplicate'), ('sell', 'Sell for 35 gold')]
    choice = state.to_json()
    for decision in ('distill', 'sell'):
        branch = State.from_json(choice)
        branch.choose(decision)
        assert branch.inventory.count('wayfarer_boots') == 1
        assert (branch.gold, branch.crystals) == (gold + 55 + (35 if decision == 'sell' else 0),
                                                 crystals + 1 + (4 if decision == 'distill' else 0))
        branch = State.from_json(branch.to_json())
        before = branch.to_json()
        with pytest.raises(RuleError):
            branch.choose(decision)
        with pytest.raises(RuleError):
            branch.explore()
        assert branch.to_json() == before


def test_missed_deadline_keeps_real_losses_and_allows_a_paid_replacement_expedition():
    from tools.eador_campaign import finish_battle, march_to, rest

    state = prepare_explorer()
    state.explore(approach='north')
    gold, xp = state.gold, state.hero.xp
    while state.battle.outcome is None:
        state.battle.end_turn()
        state = State.from_json(state.to_json())
    assert state.battle.outcome == 'enemy' and state.battle.outcome_reason == 'deadline'
    assert state.battle.round == 6
    fallen = {u.id for u in state.battle.units if u.team == 'player' and not u.alive}
    patrol = [(u.kind, u.hp) for u in state.battle.units if u.team == 'enemy' and u.alive]
    assert fallen and len(patrol) < 4
    state.resolve_battle()
    assert (state.gold, state.hero.xp) == (gold - 20, xp)
    assert fallen.isdisjoint(t.id for t in state.hero.army)
    assert not state.provinces[(0, -1)].explored
    state = State.from_json(state.to_json())
    before_recruits = state.gold
    while len(state.hero.army) < state.hero.max_army:
        state.recruit('swordsman')
    assert state.gold < before_recruits
    for _ in range(16):
        if state.hero.hp == state.hero.max_hp and all(t.hp == t.max_hp for t in state.hero.army):
            break
        rest(state)
    march_to(state, (0, -1))
    if not state.actions_left:
        rest(state); march_to(state, (0, -1))
    state.explore(approach='south')
    assert [(u.kind, u.hp) for u in state.battle.units if u.team == 'enemy'] == patrol
    state = State.from_json(state.to_json())
    gold, crystals, reward = state.gold, state.crystals, state.battle_adventure
    finish_battle(state)
    assert state.provinces[(0, -1)].explored
    assert (state.gold, state.crystals) == (gold + reward.gold, crystals + reward.crystals)
    assert fallen.isdisjoint(t.id for t in state.hero.army)
