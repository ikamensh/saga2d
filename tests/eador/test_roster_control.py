"""Finite control orders change legal plans without granting replacement actions."""
from dataclasses import asdict

from eador.battle import Battle


def test_militia_rally_releases_a_real_enemy_pin_without_refreshing_orders():
    """A cheap adjacent reserve restores the Ranger's route, not a second move or shot."""
    battle = Battle.clash([('ranger', 22), ('militia', 24)], [('archer', 20)], 'plains')
    battle.move(0, (0, 0)); battle.move(1, (-1, 0))
    battle.guard(0); battle.guard(1); battle.end_turn()
    assert battle.unit(0).pinned
    before, limited = battle.to_dict(), battle.reachable(0)
    forecast = battle.rally_preview(1, 0)
    assert battle.to_dict() == before and limited < forecast.reachable
    target_before = asdict(battle.unit(0))
    battle.rally(1, 0)
    assert battle.reachable(0) == forecast.reachable
    assert battle.unit(0).effective_move_range == forecast.move_range
    assert asdict(battle.unit(0)) == {**target_before, 'pinned': False}
    assert battle.unit(1).acted and battle.unit(1).moved
    restored = Battle.from_dict(battle.to_dict())
    destination = min(forecast.reachable - limited)
    restored.move(0, destination)
    assert restored.unit(0).pos == destination


def test_new_militia_ability_saves_while_a_real_v10_extraction_continues_exactly():
    """Updating the registry must not teach an ability to a battle already in progress."""
    import json
    from pathlib import Path
    from eador.model import State
    from tools.eador_campaign import finish_battle
    fresh = State.new(7); fresh.explore()
    assert any(u.can_rally for u in fresh.battle.units)
    assert State.from_json(fresh.to_json()).to_json() == fresh.to_json()
    fixtures = Path(__file__).parent / 'fixtures'
    legacy = State.from_json((fixtures / 'v10_pinned_crossing.json').read_text())
    assert legacy.battle.unit(0).pinned and not any(u.can_rally for u in legacy.battle.units)
    finish_battle(legacy)
    actual = json.loads(legacy.to_json())
    expected = json.loads((fixtures / 'v10_pinned_crossing_result.json').read_text())
    actual.pop('schema_version'); expected.pop('schema_version')
    assert actual == expected


def test_rally_of_a_spent_ally_clears_only_pin_and_invalid_orders_are_atomic():
    """Rally cannot create an extra turn, clear enemy Pin, or be used twice."""
    import pytest
    from eador.model import RuleError
    battle = Battle.clash([('ranger', 22), ('militia', 24)], [('archer', 20)], 'plains')
    battle.move(0, (0, 0)); battle.move(1, (-1, 0))
    battle.guard(0); battle.guard(1); battle.end_turn(); battle.guard(0)
    assert battle.unit(0).pinned and not battle.rally_preview(1, 0).reachable
    target_before = asdict(battle.unit(0))
    battle.rally(1, 0)
    assert asdict(battle.unit(0)) == {**target_before, 'pinned': False}
    before = battle.to_dict()
    for command, arguments in ((battle.rally, (1, 0)), (battle.rally, (1000, 0)),
                                (battle.move, (0, (0, 1))), (battle.attack, (0, 1000))):
        with pytest.raises(RuleError):
            command(*arguments)
        assert battle.to_dict() == before
