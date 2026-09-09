"""Realm settlement preserves paid recovery while the campaign owns the world clock."""
from dataclasses import asdict
import json

from eador.model import State
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_campaign import finish_battle


def paid_wounded_realm():
    state = State.new(7)
    state.build('barracks')
    state.recruit('swordsman')
    state.explore()
    finish_battle(state, budget=CpuBudget(25))
    assert any(troop.kind == 'swordsman' for troop in state.hero.army)
    assert any(troop.hp < troop.max_hp for troop in state.hero.army)
    return state


def test_paid_wounded_army_rests_and_pays_upkeep_before_the_rival_advances():
    """A paid adventure reaches the ordinary public turn command and survives an exact reload."""
    state = paid_wounded_realm()
    saved = state.to_json()
    before = {'gold': state.gold, 'crystals': state.crystals, 'hero': asdict(state.hero),
              'rival': asdict(state.rival), 'turn': state.turn, 'actions': state.actions_left}
    income, upkeep, crystals = state.income, state.upkeep, state.crystal_income
    recovery = state.recovery_preview()
    rival_earnings = state.rival.income(state) - state.rival.upkeep
    log_length = len(state.log)
    state.end_turn()
    assert (state.gold, state.crystals, state.turn, state.actions_left) == (
        before['gold'] + income - upkeep, before['crystals'] + crystals, before['turn'] + 1, 2)
    assert state.hero.hp == before['hero']['hp'] + recovery.hero_hp
    assert state.hero.mana == before['hero']['mana'] + recovery.mana
    assert [(troop.id, troop.hp) for troop in state.hero.army] == [
        (troop['id'], min(troop['max_hp'], troop['hp'] + recovery.army_hp))
        for troop in before['hero']['army']]
    assert state.rival.gold == before['rival']['gold'] + rival_earnings
    assert state.rival.turns_until_action == before['rival']['turns_until_action'] - 1
    assert state.log[log_length:] == [f'Turn 2: {income - upkeep:+d} gold after upkeep; army rests.']
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    resumed = State.from_json(saved)
    resumed.end_turn()
    assert resumed.to_json() == state.to_json()


def test_standalone_realm_settlement_cannot_advance_the_world():
    """Ordinary hero data can settle without a State-shaped adapter or a world clock."""
    from eador.economy import settle_realm

    state = paid_wounded_realm()
    saved = state.to_json()
    before = json.loads(saved)
    recovery = state.recovery_preview()
    result = settle_realm(state.hero, gold=state.gold, crystals=state.crystals,
                          income=state.income, crystal_income=state.crystal_income,
                          recovery=recovery, turn=state.turn + 1)
    after = json.loads(state.to_json())
    assert after.pop('hero') != before.pop('hero'), 'The provided wounded army actually rests'
    assert after == before, 'Settlement has no reference to treasury, date, provinces, rival or choices'
    assert (result.gold, result.crystals, result.actions_left) == (65, 7, 2)
    assert result.log == ('Turn 2: +10 gold after upkeep; army rests.',)

    expected = State.from_json(saved)
    log_length = len(expected.log)
    expected.end_turn()
    assert asdict(state.hero) == asdict(expected.hero)
    assert (result.gold, result.crystals, result.actions_left) == (
        expected.gold, expected.crystals, expected.actions_left)
    assert list(result.log) == expected.log[log_length:]
