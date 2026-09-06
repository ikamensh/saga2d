"""Difficulty changes announced realm decisions while preserving saved Standard rules."""
import json
from pathlib import Path

from eador.model import State
from tools.eador_campaign import finish_battle
from tools.eador_linked_campaign import travel_selection


def without_difficulty_metadata(state):
    data = json.loads(state.to_json())
    assert data.pop('rules_id') == 'standard-1'
    assert data.pop('schema_version') == 12
    return data


def test_real_v11_progress_migrates_and_continues_with_exact_standard_rules():
    """Real old battle/reward/order/departure/recovery states keep every gameplay field."""
    cases = json.loads((Path(__file__).parent / 'fixtures/v11_difficulty_cases.json').read_text())
    for case in cases:
        state = State.from_json(json.dumps(case['before']))
        expected = {key: value for key, value in case['before'].items() if key != 'schema_version'}
        assert state.difficulty == 'standard' and state.rules.title == 'Standard'
        assert without_difficulty_metadata(state) == expected
        if case['name'] == 'new_game':
            assert without_difficulty_metadata(State.new()) == expected
        if case['name'] == 'departure':
            state.advance('rootward', **travel_selection(state))
        elif case['name'] == 'recovery':
            state.recover(**travel_selection(state))
        elif case['name'] == 'active_battle':
            finish_battle(state)
        while state.choice:
            state.choose(state.choice.options[0].id)
        state.end_turn()
        assert without_difficulty_metadata(state) == {
            key: value for key, value in case['after'].items() if key != 'schema_version'}


def test_accessible_recovery_forecast_is_live_nonmutating_and_matches_end_turn():
    """A real purchased army spends mana and takes wounds before its advertised rest."""
    state = State.new(7, 'Wizard', difficulty='accessible')
    assert (state.gold, state.crystals) == (130, 6)
    state.build('temple'); state.recruit('healer'); state.explore()
    finish_battle(state)
    saved = state.to_json()
    forecast = state.recovery_preview()
    assert state.to_json() == saved
    assert forecast.army_hp == 13 and forecast.mana > 0 and forecast.blocked_reason is None
    before = (state.hero.hp, state.hero.mana, {t.id: t.hp for t in state.hero.army})
    state.end_turn()
    assert state.hero.hp == before[0] + forecast.hero_hp
    assert state.hero.mana == before[1] + forecast.mana
    for troop in state.hero.army:
        assert troop.hp == min(troop.max_hp, before[2][troop.id] + forecast.army_hp)
    assert State.from_json(state.to_json()).to_json() == state.to_json()
