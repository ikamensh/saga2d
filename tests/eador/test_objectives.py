"""Authored objectives use public tactical orders and preserve campaign consequences."""
import json
from pathlib import Path
import pytest

from eador.battle import Battle, BattleUnit
from eador.model import SaveFormatError, State
from eador.content import SITES
from eador.encounters import ENCOUNTERS


def distant_watch():
    """A distant slow archer makes two uncontested holding turns possible."""
    from eador.battle import BattleObjective

    units = [BattleUnit(0, 'player', 'hero', (-2, 0), 36, 36, 10, 3, 3, 1),
             BattleUnit(1000, 'enemy', 'archer', (3, 0), 20, 20, 8, 1, 1, 3)]
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    return Battle(units, terrain, 0, set(), objective=BattleObjective('hold', (-2, 0), 0, 2, 8))


def test_two_uncontested_enemy_turns_win_the_seal_with_defenders_still_alive():
    """Holding an objective can end an encounter without pretending its defenders died."""
    battle = distant_watch()
    battle.end_turn()
    assert battle.outcome is None and battle.objective.progress == 1
    battle = Battle.from_dict(battle.to_dict())
    battle.end_turn()
    assert battle.outcome == 'player' and battle.outcome_reason == 'hold'
    assert battle.objective.progress == battle.objective.required == 2
    assert battle.unit(1000).alive


def test_a_v4_battle_with_brace_migrates_as_rout_and_keeps_its_exact_continuation():
    """A new objective does not alter an older saved stance, terrain or automatic outcome."""
    fixtures = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixtures / 'v4_brace_battle.json').read_text())
    assert json.loads(state.to_json())['schema_version'] == 5
    assert state.battle.objective.kind == 'rout'
    assert state.battle.objective.target is None and state.battle.outcome_reason is None
    state = State.from_json(state.to_json())
    while state.battle.outcome is None:
        state.battle.auto_turn()
    expected = json.loads((fixtures / 'v4_brace_battle_result.json').read_text())
    assert (state.battle.outcome, state.battle.round, state.battle.mana) == (expected['outcome'], expected['round'], expected['mana'])
    assert [[u.id, u.hp, list(u.pos), u.stance] for u in state.battle.units] == expected['units']
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_border_watch_creates_its_authored_layout_and_visible_hold_contract():
    """The adventure's public definition supplies stable terrain, deployment and objective data."""
    state = State.new(7)
    site = SITES['border_watch']
    battle = Battle.create(state.hero, list(site.guards), 'marsh', state.spells, 43, encounter=site.encounter)
    spec = ENCOUNTERS['border_watch']
    assert battle.terrain == dict(spec.terrain)
    assert [unit.pos for unit in battle.units if unit.team == 'enemy'] == list(spec.enemy_positions[:len(site.guards)])
    assert battle.objective.kind == 'hold' and battle.objective.target == (0, 0)
    assert battle.objective.progress == 0 and battle.objective.required == 2 and battle.objective.deadline == 8


@pytest.mark.parametrize('change', [dict(kind='unknown'), dict(progress='one'), dict(required=1), dict(target=[99, 0]), dict(deadline=0)])
def test_inconsistent_saved_objectives_fail_at_load(change):
    """Damaged objective data is rejected before it can break a later enemy turn."""
    state = State.new(7)
    state.explore()
    data = json.loads(state.to_json())
    data['battle']['objective'].update(change)
    with pytest.raises(SaveFormatError, match='[Oo]bjective'):
        State.from_json(json.dumps(data))


def test_defenders_contest_the_seal_instead_of_taking_irrelevant_ranged_bait():
    """A ranged defender denies the imminent hold even with a one-HP target in range."""
    battle = distant_watch()
    battle.unit(1000).pos = (0, 0)
    battle.units.append(BattleUnit(1, 'player', 'militia', (1, -1), 1, 20, 7, 1, 2, 1))
    battle.objective.progress = 1
    battle.end_turn()
    assert battle.outcome is None and battle.objective.progress == 0
    assert battle.grid.distance(battle.unit(1000).pos, battle.objective.target) == 1
    assert battle.unit(1).alive
    assert battle.unit(0).hp < 36


@pytest.mark.parametrize('round_number,initial_progress,expected', [(8, 1, 'hold'), (8, 0, 'deadline')])
def test_last_enemy_turn_counts_toward_the_hold_before_the_deadline(round_number, initial_progress, expected):
    """The eighth enemy phase is playable; completing the second hold then still wins."""
    battle = distant_watch()
    battle.round = round_number
    battle.objective.progress = initial_progress
    battle.end_turn()
    assert battle.outcome_reason == expected and battle.round == 8
    assert battle.outcome == ('player' if expected == 'hold' else 'enemy')
    assert battle.unit(0).alive and battle.unit(1000).alive


def test_leaving_the_seal_breaks_consecutive_control():
    """A saved first hold does not become a win after its holder moves away."""
    battle = distant_watch()
    battle.end_turn()
    battle.move(0, (-3, 0))
    battle.end_turn()
    assert battle.outcome is None and battle.objective.progress == 0


def test_rout_and_hero_death_end_an_objective_immediately():
    """Objective progress cannot delay a rout or rescue an army whose hero has fallen."""
    battle = distant_watch()
    battle.unit(1000).pos = (-1, 0)
    battle.unit(1000).hp = 1
    battle.attack(0, 1000)
    assert battle.outcome == 'player' and battle.outcome_reason == 'rout'
    battle = distant_watch()
    battle.unit(1000).pos = (-1, 0)
    battle.unit(0).hp = 1
    battle.objective.progress = 1
    battle.end_turn()
    assert battle.outcome == 'enemy' and battle.outcome_reason == 'hero_death'
