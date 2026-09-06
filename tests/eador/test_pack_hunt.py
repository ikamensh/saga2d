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
