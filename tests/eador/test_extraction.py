"""Evacuation is a carrier action, with finite attempts and saved consequences."""
import pytest

from eador.battle import Battle, BattleObjective, BattleUnit
from eador.model import RuleError


def escape_fixture():
    """An isolated edge exit makes the order cost and allied delivery unambiguous."""
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q + r) <= 3}
    units = [BattleUnit(0, 'player', 'hero', (-2, 0), 36, 36, 10, 3, 3, 1),
             BattleUnit(1, 'player', 'warden', (-3, 0), 38, 38, 8, 4, 2, 1, abilities=('swap',)),
             BattleUnit(1000, 'enemy', 'archer', (3, 0), 20, 20, 8, 1, 3, 3)]
    return Battle(units, terrain, 10, {'heal'}, objective=BattleObjective(
        'extract', deadline=8, exits=((-3, 0), (-3, 1))))


def test_evacuating_spends_an_action_and_a_warden_can_deliver_an_unspent_hero():
    """Arrival alone never wins; a spent hero must wait, while allied delivery keeps its action."""
    battle = escape_fixture()
    battle.move(0, (-3, 1))
    assert battle.outcome is None and battle.evacuation_blocked_reason is None
    ready = Battle.from_dict(battle.to_dict())
    battle.guard(0)
    before = battle.to_dict()
    with pytest.raises(RuleError, match='acted'):
        battle.evacuate()
    assert battle.to_dict() == before
    ready.evacuate()
    assert ready.outcome == 'player' and ready.outcome_reason == 'escape'
    assert ready.unit(0).acted and ready.unit(1000).alive
    delivered = escape_fixture()
    delivered.swap(1, 0)
    assert delivered.outcome is None and delivered.unit(0).moved and not delivered.unit(0).acted
    delivered = Battle.from_dict(delivered.to_dict())
    delivered.evacuate()
    assert delivered.outcome_reason == 'escape'


def test_adjacent_defenders_block_evacuation_and_rout_remains_an_alternative():
    """An exit is contested by any living foe, including ranged defenders."""
    battle = escape_fixture()
    battle.unit(1000).pos = (-2, 1)
    battle.unit(1000).hp = 1
    battle.move(0, (-3, 1))
    before = battle.to_dict()
    with pytest.raises(RuleError, match='adjacent'):
        battle.evacuate()
    assert battle.to_dict() == before
    battle.attack(0, 1000)
    assert battle.outcome_reason == 'rout' and battle.outcome == 'player'


def test_the_eighth_enemy_phase_ends_an_unfinished_escape():
    """Waiting on deployment cannot avoid the extraction deadline."""
    battle = escape_fixture()
    battle.unit(1000).attack = battle.unit(1000).move_range = 1
    for _ in range(8):
        for unit in battle.units:
            if unit.team == 'player' and unit.alive:
                battle.guard(unit.id)
        battle.end_turn()
        battle = Battle.from_dict(battle.to_dict())
    assert battle.outcome == 'enemy' and battle.outcome_reason == 'deadline' and battle.round == 8
    assert all(unit.alive for unit in battle.units)


def test_a_real_v9_support_battle_retains_its_exact_continuation():
    """New objective metadata never changes an already-started Watch or its earned rewards."""
    import json
    from pathlib import Path
    from eador.model import State
    from tools.eador_campaign import finish_battle
    fixture = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixture / 'v9_support_watch.json').read_text())
    assert state.battle.objective.exits == ()
    finish_battle(state)
    actual = json.loads(state.to_json())
    expected = json.loads((fixture / 'v9_support_watch_result.json').read_text())
    actual.pop('schema_version'); expected.pop('schema_version')
    expected['battle_adventure'] = None
    assert actual == expected
