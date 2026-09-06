"""Active relics are earned, occupy one slot, and reuse existing tactical orders."""
from pathlib import Path

from eador.model import State
from tools.eador_campaign import finish_battle
from tools.eador_relic_campaign import prepare_censer_watch


def test_an_earned_censer_grants_one_saved_smoke_charge_in_a_later_watch():
    state = prepare_censer_watch()
    assert state.hero.relic == 'veil_censer' and 'veil_censer' in state.inventory
    hero = state.battle.unit(0)
    assert hero.abilities == ('smoke',)
    before = state.to_json()
    cloud = state.battle.smoke_preview(0, hero.pos)
    assert state.to_json() == before
    state.battle.smoke(0, hero.pos)
    assert hero.acted and hero.moved and hero.spent_abilities == ('smoke',)
    loaded = State.from_json(state.to_json())
    assert loaded.to_json() == state.to_json()
    assert loaded.battle.smoke_clouds == [cloud] and loaded.battle.smoke_targets(0) == set()
    loaded.battle.end_turn()
    assert loaded.battle.smoke_clouds == [] and loaded.battle.unit(0).spent_abilities == ('smoke',)


def test_existing_active_crossing_keeps_its_reward_and_exact_continuation():
    fixtures = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixtures / 'v11_crossing_relic_battle.json').read_text())
    assert state.battle_adventure.relic == 'merchant_seal'
    assert state.provinces[(0, 2)].site_relic == 'merchant_seal'
    assert not state.battle.unit(0).abilities
    finish_battle(state)
    assert state.to_json() == (fixtures / 'v11_crossing_relic_result.json').read_text().strip()


def test_censer_uses_one_equipped_slot_and_cannot_change_power_during_combat():
    import json
    import pytest
    from eador.model import RuleError, SaveFormatError
    state = prepare_censer_watch()
    before = state.to_json()
    with pytest.raises(RuleError):
        state.equip('moonstone')
    assert state.to_json() == before
    for relic, abilities, spent in (('moonstone', ['smoke'], []),
                                    ('veil_censer', ['smoke', 'swap'], []),
                                    ('veil_censer', [], ['smoke'])):
        data = json.loads(before)
        data['hero']['relic'] = relic
        hero = next(u for u in data['battle']['units'] if u['id'] == 0)
        hero['abilities'], hero['spent_abilities'] = abilities, spent
        with pytest.raises(SaveFormatError):
            State.from_json(json.dumps(data))
    assert state.to_json() == before
