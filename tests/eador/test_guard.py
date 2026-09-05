"""Defensive orders exercised through ordinary battle and campaign commands."""
import json
from pathlib import Path

import pytest

from eador.battle import Battle, BattleUnit
from eador.model import RuleError, SaveFormatError, State, UNITS


def encounter(player='swordsman', enemy='brigand', *, player_hp=None, enemy_pos=(1, 0)):
    """A small authored arena makes exact counterplay observable without AI setup."""
    units = []
    for ident, team, kind, pos, health in (
        (0, 'player', player, (0, 0), player_hp),
        (1000, 'enemy', enemy, enemy_pos, None),
    ):
        spec = UNITS[kind]
        units.append(BattleUnit(ident, team, kind, pos, health or spec.hp, spec.hp,
                               spec.attack, spec.defense, spec.move_range, spec.attack_range))
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    return Battle(units, terrain, 0, set(), hero_id=None)


def test_guard_spends_the_order_reduces_incoming_damage_and_expires_next_turn():
    """Guard protects this enemy phase, with no action refund or permanent armor."""
    battle = encounter()
    soldier, enemy = battle.units
    unguarded_damage = battle.preview(enemy.id, soldier.id)[0]
    battle.guard(soldier.id)
    assert battle.preview(enemy.id, soldier.id)[0] == unguarded_damage - 2
    assert not battle.reachable(soldier.id) and not battle.targets(soldier.id)
    before = battle.to_dict()
    for order in (lambda: battle.guard(soldier.id), lambda: battle.attack(soldier.id, enemy.id),
                  lambda: battle.move(soldier.id, (-1, 0))):
        with pytest.raises(RuleError):
            order()
        assert battle.to_dict() == before
    health = soldier.hp
    battle.end_turn()
    assert health - soldier.hp == unguarded_damage - 2
    assert battle.preview(enemy.id, soldier.id)[0] == unguarded_damage
    assert battle.targets(soldier.id)


@pytest.mark.parametrize('fixture', ['v2_defense', 'v3_battle'])
def test_older_active_battles_migrate_without_changing_their_exact_continuation(fixture):
    """Adding defensive orders does not reroll older combat or its automatic outcome."""
    fixtures = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixtures / f'{fixture}.json').read_text())
    assert json.loads(state.to_json())['schema_version'] == 4
    state = State.from_json(state.to_json())
    while state.battle.outcome is None:
        state.battle.auto_turn()
    expected = json.loads((fixtures / f'{fixture}_result.json').read_text())
    assert state.battle.outcome == expected['outcome']
    assert [[u.id, u.hp, list(u.pos)] for u in state.battle.units] == expected['units']
    if 'round' in expected:
        assert (state.battle.round, state.battle.mana) == (expected['round'], expected['mana'])


def test_saved_guard_orders_keep_their_effect_and_reject_unknown_stances():
    """A saved defensive order resumes exactly; corrupt stance IDs fail at load."""
    state = State.new()
    state.explore()
    for unit in state.battle.units:
        if unit.team == 'player':
            state.battle.guard(unit.id)
    restored = State.from_json(state.to_json())
    assert restored.to_json() == state.to_json()
    for campaign in (state, restored):
        campaign.battle.end_turn()
    assert restored.to_json() == state.to_json()
    data = json.loads(state.to_json())
    data['battle']['units'][0]['stance'] = 'invincible'
    with pytest.raises(SaveFormatError, match='stance'):
        State.from_json(json.dumps(data))
