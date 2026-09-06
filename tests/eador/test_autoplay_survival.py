"""Autoplay must not spend a veteran's life before safe allies can finish the fight."""
import gzip
import json
from pathlib import Path

from eador.battle import Battle, BattleUnit
from eador.model import State


def test_autoplay_uses_ready_allies_before_a_lethal_retaliation():
    """The earned Control army can win this round without sacrificing its wounded Adept."""
    journal = Path(__file__).resolve().parents[2] / 'docs/evidence/shardbound-army-plans-cd351a9/control.json.gz'
    saved = json.loads(gzip.decompress(journal.read_bytes()))['commands'][80]['before']
    state = State.from_json(saved)
    battle = state.battle
    adept, guard = battle.unit(6), battle.unit(1011)
    damage, reaction = battle.preview(adept.id, guard.id)
    assert reaction == adept.hp and damage < guard.hp
    veterans = {unit.id for unit in battle.units if unit.team == 'player' and unit.alive}

    battle.auto_turn()

    assert battle.outcome == 'player'
    assert all(battle.unit(ident).alive for ident in veterans)
    restored = State.from_json(saved)
    restored.battle.auto_turn()
    assert restored.to_json() == state.to_json()


def test_autoplay_rechecks_a_deferred_unit_after_its_ally_spends_the_reaction():
    """Deferring is not skipping: the wounded archer can finish once retaliation is spent."""
    battle = Battle([
        BattleUnit(0, 'player', 'archer', (-1, 0), 2, 20, 8, 1, 3, 3),
        BattleUnit(1, 'player', 'swordsman', (0, -1), 34, 34, 11, 3, 3, 1),
        BattleUnit(1000, 'enemy', 'guard', (0, 0), 11, 42, 12, 4, 3, 1),
    ], {(-1, 0): 'plains', (0, -1): 'plains', (0, 0): 'plains'},
        mana=0, spells=set(), hero_id=None)
    assert battle.preview(0, 1000)[1] == battle.unit(0).hp

    battle.auto_turn()

    assert battle.outcome == 'player'
    assert battle.unit(0).hp == 2 and battle.unit(0).acted
    assert battle.unit(1).alive and battle.unit(1).acted


def test_risky_orders_finish_when_no_ally_can_remove_the_reaction():
    """Each unsafe unit gets one reconsideration, not an endless queue or a free second order."""
    battle = Battle([
        BattleUnit(0, 'player', 'militia', (-1, 0), 2, 24, 8, 1, 3, 1),
        BattleUnit(1, 'player', 'militia', (0, -1), 2, 24, 8, 1, 3, 1),
        BattleUnit(1000, 'enemy', 'pikeman', (0, 0), 40, 40, 11, 3, 3, 1, stance='brace'),
    ], {(-1, 0): 'plains', (0, -1): 'plains', (0, 0): 'plains'},
        mana=0, spells=set(), hero_id=None)
    before = battle.to_dict()
    assert all(battle.preview(ident, 1000)[1] == 2 for ident in (0, 1))

    battle.auto_turn()

    assert battle.outcome == 'enemy'
    assert all(not unit.alive for unit in battle.units if unit.team == 'player')
    restored = Battle.from_dict(before)
    restored.auto_turn()
    assert restored.to_dict() == battle.to_dict()


def test_player_autoplay_safety_does_not_change_enemy_order_policy():
    """The convenience-command change does not silently strengthen opposing formations."""
    battle = Battle([
        BattleUnit(0, 'enemy', 'archer', (-1, 0), 2, 20, 8, 1, 3, 3),
        BattleUnit(1, 'enemy', 'swordsman', (0, -1), 34, 34, 11, 3, 3, 1),
        BattleUnit(1000, 'player', 'guard', (0, 0), 11, 42, 12, 4, 3, 1),
    ], {(-1, 0): 'plains', (0, -1): 'plains', (0, 0): 'plains'},
        mana=0, spells=set(), hero_id=None)

    battle.end_turn()

    assert battle.outcome == 'enemy'
    assert not battle.unit(0).alive and battle.unit(1).alive
