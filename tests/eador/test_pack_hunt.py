"""An authored rout preserves paid approach decisions and finite pack losses."""
import json
from pathlib import Path

import pytest

from eador.model import State
from tools.eador_hunt_campaign import prepare_pack_hunt as prepared_hunt


def test_luring_the_same_pack_changes_deployment_without_turning_the_fight_into_a_hold():
    """Both selected approaches remain rout battles after an exact campaign reload."""
    before = prepared_hunt().to_json()
    free, paid = State.from_json(before), State.from_json(before)
    assert free.provinces[free.hero.pos].site_kind == 'pack_hunt'
    free.explore(); paid.explore(approach='lure')
    assert free.gold == paid.gold + 20 and free.crystals == paid.crystals
    assert free.battle.objective.kind == paid.battle.objective.kind == 'rout'
    assert free.battle.objective.deadline is None and free.battle.objective.target is None
    assert free.battle.unit(0).pos != paid.battle.unit(0).pos
    assert [u for u in free.battle.units if u.team == 'enemy'] == [u for u in paid.battle.units if u.team == 'enemy']
    assert free.battle.terrain == paid.battle.terrain
    assert free.battle_adventure.gold == paid.battle_adventure.gold
    assert State.from_json(paid.to_json()).to_json() == paid.to_json()


@pytest.mark.parametrize('fixture', ['v10_ruins_battle', 'v11_wolf_den_battle'])
def test_real_prior_battles_keep_their_recorded_world_and_exact_continuation(fixture):
    """New authored content cannot replace a saved site or reroll an active old fight."""
    from tools.eador_campaign import finish_battle

    fixtures = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixtures / f'{fixture}.json').read_text())
    assert all(p.site_kind != 'pack_hunt' for p in state.provinces.values())
    finish_battle(state)
    actual = json.loads(state.to_json())
    expected = json.loads((fixtures / f'{fixture}_result.json').read_text())
    actual.pop('schema_version'); expected.pop('schema_version')
    assert actual == expected


def test_manual_lure_concentrates_fire_while_free_play_must_reposition_around_the_forest():
    """The paid army wins a round earlier, preserving mana and every purchased soldier."""
    from tools.eador_hunt_campaign import prepare_pack_hunt, hunt_route
    from tests.eador.test_extraction_journeys import Journey

    before = prepare_pack_hunt().to_json()
    free = hunt_route(State.from_json(before), 'compact', orders_type=Journey)
    paid = hunt_route(State.from_json(before), 'lure', orders_type=Journey)
    assert (free.battle.round, paid.battle.round) == (3, 2)
    assert free.battle.mana == paid.battle.mana
    assert free.state.gold == paid.state.gold + 20
    assert sum(u.hp for u in free.battle.units if u.team == 'player') < sum(
        u.hp for u in paid.battle.units if u.team == 'player')
    for play in (free, paid):
        assert_one_rout_reward(play)


def assert_one_rout_reward(play):
    from eador.model import RuleError
    state, battle = play.state, play.battle
    assert battle.outcome == 'player' and battle.outcome_reason == 'rout'
    assert all(u.alive for u in battle.units if u.team == 'player')
    reward, gold, crystals, pos = state.battle_adventure, state.gold, state.crystals, state.hero.pos
    state.resolve_battle()
    assert state.gold == gold + reward.gold and state.crystals == crystals + reward.crystals
    assert state.provinces[pos].explored and state.battle_adventure is None
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


def test_a_cheaper_warrior_spear_army_can_clear_the_free_approach_with_different_orders():
    """Two ordinary Pikemen replace the Ranger/Warden investment without changing the pack."""
    from tools.eador_hunt_campaign import prepare_hunt_spears, spear_hunt_route
    from tests.eador.test_extraction_journeys import Journey

    state = prepare_hunt_spears()
    assert state.hero.hero_class == 'Warrior' and state.buildings == {'barracks'}
    assert [t.kind for t in state.hero.army][-2:] == ['pikeman', 'pikeman']
    play = spear_hunt_route(state, orders_type=Journey)
    assert play.battle.round == 3 and play.battle.mana == state.hero.mana
    assert any('Pikeman braces' in line for line in play.battle.log)
    assert_one_rout_reward(play)


def test_saved_failed_lure_keeps_its_cost_and_remaining_wolves_when_retrying_for_free():
    """A killed wolf and another wolf's wounds remain after retreat, reload and reselection."""
    from tools.eador_campaign import finish_battle, rest
    state = prepared_hunt()
    gold, xp = state.gold, state.hero.xp
    state.explore(approach='lure')
    battle = state.battle
    east, north = [next(u.id for u in battle.units if u.team == 'enemy' and u.pos == pos)
                   for pos in ((1, -1), (2, -1))]
    battle.attack(5, east); battle.move(2, (3, -2)); battle.move(0, (2, -2)); battle.attack(0, east)
    battle.move(3, (1, -3)); battle.attack(3, north)
    survivors = [(u.kind, u.hp) for u in battle.units if u.team == 'enemy' and u.alive]
    assert len(survivors) == 5 and min(hp for _, hp in survivors) < 17
    state = State.from_json(state.to_json())
    assert state.gold == gold - 20
    state.retreat()
    assert state.gold == gold - 40 and state.hero.xp == xp  # Fee plus ordinary retreat loss.
    state = State.from_json(state.to_json())
    province = state.provinces[state.hero.pos]
    assert list(zip(province.site_guards, province.site_guard_hp)) == survivors
    if not state.actions_left:
        rest(state)
    before_gold = state.gold
    state.explore(approach='compact')
    assert state.gold == before_gold
    assert [(u.kind, u.hp) for u in state.battle.units if u.team == 'enemy'] == survivors
    state = State.from_json(state.to_json())
    reward = state.battle_adventure
    finish_battle(state)
    assert state.provinces[(-1, 1)].explored and state.gold == before_gold + reward.gold


@pytest.mark.parametrize('corruption', ['missing_attempt', 'hold', 'explored', 'displaced_hero', 'missing_guard'])
def test_a_damaged_rout_attempt_is_refused_before_it_can_lose_state_or_repeat_rewards(corruption):
    """Generalizing an approach's objective preserves the existing origin/roster boundary."""
    from eador.model import SaveFormatError
    state = prepared_hunt(); state.explore(approach='lure')
    data = json.loads(state.to_json())
    province = next(p for p in data['provinces'] if p['pos'] == [-1, 1])
    if corruption == 'missing_attempt':
        data['battle_adventure'] = None
    elif corruption == 'hold':
        data['battle']['objective'].update(kind='hold', target=[0, 0], required=2, deadline=8)
    elif corruption == 'explored':
        province['explored'] = True
    elif corruption == 'displaced_hero':
        data['hero']['pos'] = [-2, 0]
    else:
        province['site_guards'].pop(); province['site_guard_hp'].pop()
    with pytest.raises(SaveFormatError):
        State.from_json(json.dumps(data))


def test_pack_hunt_is_placed_once_in_elderwild_without_replacing_required_sources():
    """Authored placement is a new-world choice; old Den and guaranteed equipment remain."""
    for seed in range(100):
        state = State.new(seed, theme='elderwild')
        assert sum(p.site_kind == 'pack_hunt' for p in state.provinces.values()) == 1
        assert state.provinces[(-1, 1)].site_kind == 'pack_hunt'
        assert state.provinces[(-2, 0)].site_kind == 'shrine'
        assert state.provinces[(-2, 2)].site_kind == 'den'
        assert state.provinces[(-2, 2)].site_relic == 'storm_quiver'
        assert state.provinces[(-1, 2)].site_kind == 'explorer_camp'
        assert sum(p.site_kind == 'border_watch' for p in state.provinces.values()) == 1
