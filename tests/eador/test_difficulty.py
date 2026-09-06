"""Difficulty changes announced realm decisions while preserving saved Standard rules."""
import json
from pathlib import Path

import pytest

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


def test_challenge_changes_affordable_orders_and_income_without_altering_the_world():
    """A Tower consumes the same price, but the smaller grant cannot also buy Militia."""
    from eador.model import RuleError
    normal = State.new(7)
    state = State.new(7, difficulty='challenge')
    assert state.provinces == normal.provinces and state.hero == normal.hero
    assert state.rival.gold == normal.rival.gold and state.rival.army == normal.rival.army
    normal.build('mage_tower'); state.build('mage_tower')
    normal.recruit('militia')
    before = state.to_json()
    with pytest.raises(RuleError):
        state.recruit('militia')
    assert state.to_json() == before
    assert state.income == sum(p.income for p in state.provinces.values() if p.owner == 'player') * 80 // 100
    assert state.crystal_income == normal.crystal_income
    before_gold, before_crystals, bill = state.gold, state.crystals, state.upkeep
    forecast = state.recovery_preview()
    state.end_turn()
    assert state.gold == before_gold + state.income - bill
    assert state.crystals == before_crystals + state.crystal_income
    assert forecast.army_hp == normal.recovery_preview().army_hp


def test_unselected_mana_candidate_keeps_existing_challenge_saves_and_new_games_exact():
    """A separately saved candidate can be measured without changing the shipped selector."""
    from eador.difficulty import DIFFICULTIES
    original = State.new(7, 'Wizard', difficulty='challenge')
    original.explore(); finish_battle(original)
    saved = original.to_json()
    data = json.loads(saved)
    data['rules_id'] = 'challenge-2'
    candidate = State.from_json(json.dumps(data))
    assert DIFFICULTIES['challenge'].id == original.rules_id == 'challenge-1'
    assert candidate.recovery_preview().mana == 4
    assert original.recovery_preview().mana == 3
    before_mana = original.hero.mana
    original.end_turn(); candidate.end_turn()
    assert original.hero.mana == before_mana + 3
    assert candidate.hero.mana == before_mana + 4
    assert State.from_json(candidate.to_json()).to_json() == candidate.to_json()
    resumed = State.from_json(saved)
    resumed.end_turn()
    assert resumed.to_json() == original.to_json()
    assert candidate.replay().rules_id == 'challenge-2'


@pytest.mark.parametrize('mode', ['accessible', 'standard', 'challenge'])
def test_linked_arrival_and_recovery_keep_the_saved_policy_and_separate_grants(mode):
    """A completed shard carries bounded funds; defeat restores its recorded finite world."""
    from tools.eador_linked_campaign import lose_shard, play_stage
    state = play_stage(State.new_campaign(7, difficulty=mode))
    assert state.campaign.phase == 'departure'
    state = State.from_json(state.to_json())
    rules, old_gold, old_crystals = state.rules, state.gold, state.crystals
    funding = state.expedition_funding()
    state.advance('rootward', **travel_selection(state))
    assert state.rules is rules and state.difficulty == mode
    assert (state.gold, state.crystals) == (rules.starting_gold + min(40, old_gold),
                                           rules.starting_crystals + min(2, old_crystals))
    assert (state.gold, state.crystals) == funding
    assert state.rival.gold == 80 and state.rival.turns_until_action == rules.arrival_delay
    original = json.loads(json.dumps(state.campaign.entry))
    state = lose_shard(state)
    saved = State.from_json(state.to_json())
    for current in (state, saved):
        funding = current.expedition_funding(recovery=True)
        current.recover(**travel_selection(current))
        assert current.rules is rules and current.campaign.recovery_used
        assert json.loads(json.dumps(current.campaign.entry)) == original
        assert (current.gold, current.crystals) == (rules.recovery_gold, rules.recovery_crystals)
        assert (current.gold, current.crystals) == funding
        assert current.rival.gold == original['rival']['gold']
        assert current.rival.turns_until_action == rules.arrival_delay
    assert state.to_json() == saved.to_json()


@pytest.mark.parametrize('mode', ['accessible', 'standard', 'challenge'])
def test_a_won_interception_stays_empty_until_a_delayed_paid_replacement(mode):
    """Difficulty changes the announced window, never conjures another expedition."""
    from eador.rival import RECRUIT_COSTS
    state = State.new(7, difficulty=mode)
    state.build('barracks'); state.recruit('swordsman'); state.explore()
    finish_battle(state); state.end_turn()
    for destination in ((-1, 0), (0, 0)):
        state.travel(destination)
        if state.battle:
            finish_battle(state)
        state.end_turn()
        if state.battle:
            finish_battle(state)
    for _ in range(24):
        if not state.rival.army:
            break
        if state.grid.distance(state.hero.pos, state.rival.pos) == 1 and state.actions_left:
            state.travel(state.rival.pos)
        else:
            state.end_turn()
        if state.battle:
            finish_battle(state)
    assert state.status == 'playing' and state.rival.defeats == 1 and not state.rival.army
    assert state.rival.turns_until_action == state.rules.replacement_delay
    next_id = state.rival.next_troop_id
    for _ in range(state.rules.replacement_delay - 1):
        state = State.from_json(state.to_json())
        state.end_turn()
        assert not state.rival.army
    expected_gold = state.rival.gold + state.rival.income(state)
    state.end_turn()
    assert len(state.rival.army) == 1 and state.rival.army[0].id == next_id
    assert state.rival.gold == expected_gold - RECRUIT_COSTS[state.rival.army[0].kind]


@pytest.mark.parametrize('bad', [None, [], {}, True, 'future', 'standard-2'])
def test_unknown_rule_profiles_are_refused_before_loading_a_live_campaign(bad):
    from eador.model import RuleError, SaveFormatError
    state = State.new()
    saved = state.to_json()
    with pytest.raises(RuleError):
        State.new(difficulty=bad)
    data = json.loads(saved)
    data['rules_id'] = bad
    with pytest.raises(SaveFormatError, match='difficulty'):
        State.from_json(json.dumps(data))
    assert state.to_json() == saved


@pytest.mark.parametrize('linked', [False, True])
def test_replay_starts_the_same_policy_without_mutating_the_finished_or_live_run(linked):
    state = State.new_campaign(17, 'Scout', difficulty='accessible') if linked else State.new(17, 'Scout', theme='ruins', difficulty='challenge')
    initial = state.to_json()
    state.explore(); finish_battle(state); state.end_turn()
    saved = state.to_json()
    replay = state.replay()
    assert replay.to_json() == initial and state.to_json() == saved
    replay.end_turn()
    assert state.to_json() == saved


@pytest.mark.parametrize('mode,gold,loses_acolyte', [('standard', 0, True), ('challenge', 5, False)])
def test_recovery_forecasts_this_turns_paid_survivors_before_the_treasury_changes(mode, gold, loses_acolyte):
    """A valid wounded-army fixture isolates unpaid support and the exact payment phase."""
    from eador.model import Troop, UNITS
    state = State.new(7, difficulty=mode)
    # Controlled roster/resource fixture, not an additional earned campaign claim.
    state.hero.army = [Troop(i, 'skyrider', 10, UNITS['skyrider'].hp, xp=1) for i in range(1, 6)]
    state.hero.army.append(Troop(6, 'healer', 10, UNITS['healer'].hp))
    state.next_troop_id, state.gold, state.hero.hp = 7, gold, 12
    state = State.from_json(state.to_json())
    before = state.to_json()
    forecast = state.recovery_preview()
    assert state.to_json() == before
    state.end_turn()
    assert any(t.kind == 'healer' for t in state.hero.army) is not loses_acolyte
    assert state.hero.hp == 12 + forecast.hero_hp
    assert all(t.hp == 10 + forecast.army_hp for t in state.hero.army)
