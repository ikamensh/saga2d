"""An authored rout preserves paid approach decisions and finite pack losses."""
import json
from pathlib import Path

import pytest

from eador.model import State
from tools.eador_campaign import march_to, rest
from tools.eador_extraction_campaign import prepare_adventure


def prepared_hunt(hero='Commander', support='ranger'):
    state = prepare_adventure(hero, 'elderwild', support=support)
    march_to(state, (-1, 1))
    if not state.actions_left:
        rest(state)
    return state


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
