"""Army results retain earned wounds and progression independently of realm ownership."""
from dataclasses import asdict
import json

import pytest

from eador.model import RuleError, State, UNITS
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_campaign import finish_battle


def completed_paid_conquest():
    """Earn a second victory with a purchased Swordsman; stop before accepting its result."""
    state = State.new(7, 'Warrior')
    budget = CpuBudget(25)
    state.build('barracks')
    state.recruit('swordsman')
    state.explore()
    finish_battle(state, budget=budget)
    state.travel((-1, 0))
    for _ in range(80):
        budget.checkpoint()
        if state.battle.outcome:
            break
        state.battle.auto_turn()
    assert state.battle.outcome == 'player'
    assert any(troop.kind == 'swordsman' for troop in state.hero.army)
    return state


def test_paid_second_victory_advances_survivors_before_claim_and_skill_choice():
    """Ordinary result acceptance keeps battle wounds, earned levels and the existing log order."""
    state = completed_paid_conquest()
    saved = state.to_json()
    before = asdict(state.hero)
    battle = state.battle
    gold = state.gold
    destination = state.battle_province
    name = state.provinces[destination].name
    log_length = len(state.log)
    assert before['level'] == 1 and before['xp'] == 8
    assert all(unit.alive for unit in battle.units if unit.team == 'player')
    state.resolve_battle()
    assert (state.hero.level, state.hero.xp) == (2, 4)
    assert (state.hero.hp, state.hero.max_hp, state.hero.mana, state.hero.max_mana) == (
        battle.unit(0).hp + 4, before['max_hp'] + 4, battle.mana + 2, before['max_mana'] + 2)
    assert [(troop.id, troop.hp, troop.max_hp, troop.level, troop.xp) for troop in state.hero.army] == [
        (troop['id'], battle.unit(troop['id']).hp + 4, troop['max_hp'] + 4, 2, 0)
        for troop in before['army']]
    assert state.gold == gold + 25
    assert state.hero.pos == destination and state.provinces[destination].owner == 'player'
    assert state.log[log_length:] == ['Alden reached level 2.', f'Claimed {name}: +25 gold.']
    assert state.choice.kind == 'skill' and state.choice.context == 'Warrior'
    resumed = State.from_json(saved)
    resumed.resolve_battle()
    assert resumed.to_json() == state.to_json()


def test_standalone_army_result_changes_only_the_supplied_hero():
    """An earned result updates the army without claiming a province or changing its battle."""
    from eador.battle_results import apply_army_result

    state = completed_paid_conquest()
    saved = state.to_json()
    before = json.loads(saved)
    battle_before = state.battle.to_dict()
    result = apply_army_result(state.hero, state.battle,
                               hero_level_cap=state.hero_level_cap,
                               troop_level_cap=state.troop_level_cap)
    after = json.loads(state.to_json())
    original_hero = before.pop('hero')
    assert after.pop('hero') != original_hero
    assert after == before
    assert state.battle.to_dict() == battle_before
    assert result.hero_levels == (2,) and result.casualties == ()
    expected = State.from_json(saved)
    expected.resolve_battle()
    actual_hero, expected_hero = asdict(state.hero), asdict(expected.hero)
    assert actual_hero.pop('pos') == tuple(original_hero['pos'])
    assert expected_hero.pop('pos') == state.battle_province
    assert actual_hero == expected_hero


def test_real_paid_defeat_removes_casualties_without_advancement_and_restores_the_hero_floor():
    """The earned Observatory formation loses a Militia to retaliation, then falls to defenders."""
    from eador.battle_results import apply_army_result
    from tools.eador_observatory_campaign import prepare_observatory

    budget = CpuBudget(25)
    state = prepare_observatory(budget=budget)
    state.explore(approach='clear')
    battle = state.battle
    for unit, destination in ((1, (1, -1)), (0, (0, 0)), (3, (0, -1))):
        battle.move(unit, destination)
    guard = next(unit.id for unit in battle.units if unit.team == 'enemy' and unit.pos == (1, 0))
    for _ in range(2):
        battle.attack(1, guard)
        battle.end_turn()
        budget.checkpoint()
    battle.attack(1, guard)
    assert not battle.unit(1).alive and battle.outcome is None
    for _ in range(8):
        if battle.outcome:
            break
        battle.end_turn()
        budget.checkpoint()
    assert battle.outcome == 'enemy' and battle.unit(0).hp == 0
    saved = state.to_json()
    original_hero, original_battle = asdict(state.hero), battle.to_dict()
    lost = tuple(UNITS[troop.kind].name for troop in state.hero.army if not battle.unit(troop.id).alive)
    result = apply_army_result(state.hero, battle, hero_level_cap=state.hero_level_cap,
                               troop_level_cap=state.troop_level_cap)
    assert result.casualties == lost and 'Militia' in lost
    assert result.hero_levels == ()
    assert state.hero.hp == state.hero.max_hp // 3
    assert (state.hero.level, state.hero.xp) == (original_hero['level'], original_hero['xp'])
    assert [(troop.id, troop.level, troop.xp) for troop in state.hero.army] == [
        (troop['id'], troop['level'], troop['xp']) for troop in original_hero['army']
        if battle.unit(troop['id']).alive]
    assert battle.to_dict() == original_battle
    expected = State.from_json(saved)
    log_length = len(expected.log)
    expected.resolve_battle()
    assert asdict(state.hero) == asdict(expected.hero)
    assert expected.log[log_length:] == ['Fallen: ' + ', '.join(lost) + '.',
                                        f'Retreated. Lost {min(20, state.gold)} gold; the survivors keep their wounds.']


def test_unfinished_battle_is_rejected_before_any_army_mutation():
    """Starting a paid army's encounter is not permission to apply its unfinished result."""
    from eador.battle_results import apply_army_result

    state = State.new(7)
    state.build('barracks')
    state.recruit('swordsman')
    state.explore()
    saved = state.to_json()
    with pytest.raises(RuleError, match='not finished'):
        apply_army_result(state.hero, state.battle)
    assert state.to_json() == saved
