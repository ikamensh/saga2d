"""Evacuation is a carrier action, with finite attempts and saved consequences."""
import pytest

from eador.battle import Battle, BattleObjective, BattleUnit
from eador.model import RuleError, SaveFormatError


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
    battle.unit(1000).defense = 100
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


def test_frontier_crossing_advertises_two_real_approaches_and_extraction_exits():
    """The map exposes a free and paid authored route without modifying its Shrine opening."""
    from eador.model import State
    state = State.new(7)
    assert state.provinces[(-2, 0)].site_kind == 'shrine'
    province = state.provinces[(0, 2)]
    assert province.site_kind == 'courier_crossing'
    approaches = state.adventure_approaches(province.pos)
    assert [approach.id for approach in approaches] == ['direct', 'guided']
    assert [approach.gold_cost for approach in approaches] == [0, 20]
    battles = [Battle.create(state.hero, province.site_guards, province.terrain, state.spells,
                            encounter=approach.encounter) for approach in approaches]
    assert all(b.objective.kind == 'extract' and len(b.objective.exits) == 2 for b in battles)
    assert battles[0].unit(0).pos != battles[1].unit(0).pos
    assert [(u.kind, u.hp) for u in battles[0].units if u.team == 'enemy'] == [
        (u.kind, u.hp) for u in battles[1].units if u.team == 'enemy']


def prepared_crossing():
    """The same bought support army clears its Watch, then travels to the southern crossing."""
    from tests.eador.test_roles import prepare_support_watch
    from tools.eador_campaign import finish_battle, march_to, rest
    state = prepare_support_watch()
    finish_battle(state)
    march_to(state, (0, 2))
    if not state.actions_left:
        rest(state, defend=False)
    return state


def test_paid_entry_is_atomic_saved_once_and_retry_preserves_defender_wounds():
    """A failed guided attempt loses its fee and cannot replenish its damaged guard roster."""
    from eador.model import State
    state = prepared_crossing()
    before = state.to_json()
    with pytest.raises(RuleError):
        state.explore(approach='missing')
    assert state.to_json() == before
    gold, actions = state.gold, state.actions_left
    state.explore(approach='guided')
    assert state.gold == gold - 20 and state.actions_left == actions - 1
    assert state.battle_encounter == 'courier_guided'
    state = State.from_json(state.to_json())
    assert state.gold == gold - 20
    battle = state.battle
    target = next(u for u in battle.units if u.team == 'enemy' and u.kind == 'brigand')
    battle.pin(3, target.id)
    guards = [(u.kind, u.hp) for u in battle.units if u.team == 'enemy' and u.alive]
    state = State.from_json(state.to_json())
    state.retreat()
    assert state.battle_adventure is None and not state.provinces[(0, 2)].explored
    assert state.gold == gold - 40  # entry fee plus the already-existing 20-gold retreat loss.
    assert list(zip(state.provinces[(0, 2)].site_guards, state.provinces[(0, 2)].site_guard_hp)) == guards
    if not state.actions_left:
        state.end_turn()
    before_gold = state.gold
    state.explore(approach='direct')
    assert state.gold == before_gold and state.battle_encounter == 'courier_direct'
    assert [(u.kind, u.hp) for u in state.battle.units if u.team == 'enemy'] == guards
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_cache_cargo_is_a_saved_battle_burden_not_a_persistent_hero_upgrade():
    """The risky reward buys no extra power: it costs exactly one carrier move point."""
    from eador.model import State
    from tools.eador_campaign import finish_battle, march_to
    state = State.new(7, theme='elderwild')
    state.explore(); finish_battle(state)
    march_to(state, (-1, -1))
    if not state.actions_left:
        state.end_turn()
    assert state.provinces[state.hero.pos].site_kind == 'supply_cache'
    baseline = state.to_json()
    state.explore(approach='full')
    full = State.from_json(state.to_json())
    light = State.from_json(baseline)
    light.explore(approach='light')
    assert full.hero == light.hero
    assert full.battle_adventure.gold == light.battle_adventure.gold + 40
    assert full.battle.unit(0).effective_move_range == max(1, light.battle.unit(0).effective_move_range - 1)
    assert full.battle.unit(0).move_range == light.battle.unit(0).move_range
    assert full.battle.objective.exits == light.battle.objective.exits
    assert full.battle.unit(0).pos == light.battle.unit(0).pos
    assert full.battle.unit(0).cargo_penalty == 1


def test_auto_play_takes_a_ready_exit_before_healing_or_attacking():
    battle = escape_fixture()
    battle.swap(1, 0)
    battle.unit(1).hp = 1
    battle.auto_turn()
    assert battle.outcome_reason == 'escape' and battle.mana == 10


def test_enemy_blocks_the_carrier_route_instead_of_chasing_wounded_ranger_bait():
    battle = escape_fixture()
    battle.unit(0).pos = (1, -1)
    battle.unit(1).pos = (-1, 0)
    battle.unit(1000).pos = (0, 1)
    battle.objective.exits = ((3, -3), (3, 0))
    battle.units.append(BattleUnit(2, 'player', 'ranger', (-1, 3), 1, 22, 7, 1, 3, 3, skirmisher=True))
    before = battle.unit(2).hp
    battle.end_turn()
    defender = battle.unit(1000)
    assert any(battle.grid.distance(defender.pos, exit) <= 1 for exit in battle.objective.exits)
    assert battle.unit(2).hp == before


@pytest.mark.parametrize('damage', ['reward', 'cargo', 'deadline', 'already_explored', 'wrong_origin', 'missing_guards', 'objective'])
def test_malformed_extraction_attempts_cannot_change_or_repeat_the_contract(damage):
    import json
    from eador.model import State
    state = prepared_crossing(); state.explore(approach='guided')
    data = json.loads(state.to_json())
    province = next(p for p in data['provinces'] if p['pos'] == [0, 2])
    if damage == 'reward':
        data['battle_adventure']['gold'] += 1
    elif damage == 'cargo':
        data['battle_adventure']['cargo_penalty'] = data['battle']['units'][0]['cargo_penalty'] = 1
    elif damage == 'deadline':
        data['battle']['objective']['deadline'] += 1
    elif damage == 'already_explored':
        province['explored'] = True
    elif damage == 'wrong_origin':
        data['hero']['pos'] = [-2, 0]
    elif damage == 'missing_guards':
        province['site_guards'] = province['site_guard_hp'] = []
    elif damage == 'objective':
        data['battle_adventure'] = None
        data['battle']['objective'] = {'kind': 'rout', 'target': None, 'progress': 0, 'required': 0, 'deadline': None, 'exits': []}
    with pytest.raises(SaveFormatError):
        State.from_json(json.dumps(data))
