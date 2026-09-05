"""Different troop orders enable sustain, mobile fire and extraction plans."""
import pytest

from eador.battle import Battle
from eador.model import Hero, RuleError, Troop, UNITS


def test_acolyte_spends_shared_mana_to_heal_without_spending_the_heros_order():
    """A healer's action buys time while the same turn's hero can still use magic."""
    hero = Hero('Alden', 'Wizard', (-2, 0), 24, 36, 16, 16,
                [Troop(1, 'healer', 22, 22)])
    battle = Battle.create(hero, ['guard'], 'plains', {'bolt', 'heal'})
    assert battle.unit(1).can_heal
    assert battle.spell_targets('heal', caster_id=1) == [battle.unit(0)]
    before = battle.to_dict()
    assert battle.spell_preview('heal', 0, caster_id=1) == 12
    assert battle.to_dict() == before
    battle.cast('heal', 0, caster_id=1)
    assert battle.unit(0).hp == 36 and battle.mana == 12
    assert battle.unit(1).acted and battle.unit(1).moved
    assert not battle.unit(0).acted
    battle = Battle.from_dict(battle.to_dict())
    battle.move(0, (-1, 0))
    target = next(u for u in battle.units if u.team == 'enemy')
    amount = battle.spell_preview('bolt', target.id)
    hp = target.hp
    battle.cast('bolt', target.id)
    assert hp - target.hp == amount and battle.mana == 8
    before = battle.to_dict()
    with pytest.raises(RuleError):
        battle.cast('heal', 0, caster_id=1)
    assert battle.to_dict() == before


def test_a_recruited_acolyte_saves_its_new_order():
    """Building and paying for support creates a usable order that survives campaign saves."""
    from eador.model import State
    state = State.new_campaign(7, 'Wizard')
    with pytest.raises(RuleError, match='Temple'):
        state.recruit('healer')
    state.build('temple')
    state.end_turn(); state.end_turn()
    gold = state.gold
    state.recruit('healer')
    assert gold - state.gold == state.recruit_cost('healer')
    state.explore()
    state = State.from_json(state.to_json())
    healer = next(u for u in state.battle.units if u.can_heal)
    assert healer.kind == 'healer'
    state.battle.auto_turn()
    restored = State.from_json(state.to_json())
    assert restored.to_json() == state.to_json()


def test_a_v8_active_acolyte_keeps_its_exact_prior_continuation():
    """Loading gives no new spell order to an already-started older battle."""
    import json
    from pathlib import Path
    from eador.model import State
    from tools.eador_campaign import finish_battle
    fixture = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixture / 'v8_acolyte_battle.json').read_text())
    assert not any(unit.can_heal for unit in state.battle.units)
    finish_battle(state)
    actual = json.loads(state.to_json())
    expected = json.loads((fixture / 'v8_acolyte_battle_result.json').read_text())
    actual.pop('schema_version'); expected.pop('schema_version')
    assert actual == expected


def test_acolyte_heal_uses_current_bonuses_and_cannot_borrow_mana_from_an_opponent():
    """Support follows spell modifiers, but an army without a hero has no free spell budget."""
    hero = Hero('Alden', 'Wizard', (-2, 0), 10, 40, 18, 18,
                [Troop(1, 'healer', 22, 22)], level=2,
                skill_ranks={'restoration': 1}, relic='moonstone')
    battle = Battle.create(hero, ['guard'], 'plains', {'heal'})
    assert battle.spell_preview('heal', 0, caster_id=1) == 26
    battle.guard(0)
    battle.auto_turn()
    assert battle.mana == 15 and battle.unit(0).hp == 36
    clash = Battle.clash([('healer', 10)], [('healer', 10)], 'plains')
    assert clash.spell_targets('heal', caster_id=0) == []
    before = clash.to_dict()
    with pytest.raises(RuleError, match='shared mana'):
        clash.cast('heal', 0, caster_id=0)
    assert clash.to_dict() == before
    clash.auto_turn()
    assert clash.mana == 0 and not any('Heal restores' in line for line in clash.log)
