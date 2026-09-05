"""Finite rival forces use the same public battle and campaign rules as the player."""
from eador.battle import Battle
from eador.model import State, UNITS


def resolve(state):
    while not state.battle.outcome:
        state.battle.auto_turn()
    result = state.resolve_battle()
    while state.choice:
        state.choose(state.choice.options[0].id)
    return result


def test_armies_without_a_hero_use_tactical_rules_and_keep_their_survivors():
    """A rival-neutral clash has ordinary movement, damage and lasting health losses."""
    attacking = [('guard', UNITS['guard'].hp), ('archer', UNITS['archer'].hp)]
    defending = [('brigand', UNITS['brigand'].hp), ('goblin', UNITS['goblin'].hp)]
    battle = Battle.clash(attacking, defending, 'forest', seed=7)
    while not battle.outcome:
        battle.auto_turn()
    assert battle.outcome == 'player'
    assert any(unit.hp < unit.max_hp for unit in battle.units if unit.team == 'player')
    assert Battle.from_dict(battle.to_dict()).to_dict() == battle.to_dict()


def test_rival_conquest_uses_a_visible_finite_army_and_persists_its_losses():
    """The announced expedition moves to its target and pays the real cost of combat."""
    state = State.new(7)
    target = state.rival.target
    countdown = state.rival.turns_until_action
    starting_ids = {troop.id for troop in state.rival.army}
    starting_health = sum(troop.hp for troop in state.rival.army)
    for _ in range(countdown):
        state.end_turn()
    assert state.rival.pos == target
    assert state.provinces[target].owner == 'rival'
    assert {troop.id for troop in state.rival.army} <= starting_ids
    surviving_health = sum(troop.hp for troop in state.rival.army) + sum(state.provinces[target].guard_hp)
    assert surviving_health < starting_health
    assert State.from_json(state.to_json()).to_json() == state.to_json()


def test_previous_saves_keep_pending_choices_and_exact_defense_continuations():
    """Schema two upgrades add a finite rival without rerolling an earned choice or a running battle."""
    import json
    from pathlib import Path

    fixtures = Path(__file__).parent / 'fixtures'
    pending = State.from_json((fixtures / 'v2_choice.json').read_text())
    assert pending.choice.kind == 'relic'
    pending.choose('take')
    assert pending.inventory == ['moonstone']
    assert State.from_json(pending.to_json()).to_json() == pending.to_json()
    defense = State.from_json((fixtures / 'v2_defense.json').read_text())
    assert defense.battle_kind == 'defense'
    assert defense.rival.intent == 'attack'
    assert State.from_json(defense.to_json()).to_json() == defense.to_json()
    while not defense.battle.outcome:
        defense.battle.auto_turn()
    expected = json.loads((fixtures / 'v2_defense_result.json').read_text())
    assert defense.battle.outcome == expected['outcome']
    assert [[u.id, u.hp, list(u.pos)] for u in defense.battle.units] == expected['units']
    defense.resolve_battle()
    assert State.from_json(defense.to_json()).to_json() == defense.to_json()


def central_hero():
    """A three-turn expedition meets the rival after its first neutral conquest."""
    state = State.new(7)
    state.build('barracks')
    state.recruit('swordsman')
    state.explore()
    resolve(state)
    state.equip('moonstone')
    state.end_turn()
    for destination in ((-1, 0), (0, 0)):
        state.travel(destination)
        if state.battle:
            resolve(state)
        state.end_turn()
    return state


def test_interception_and_retreat_preserve_rival_casualties_and_saved_reengagement():
    """Retreat cannot restore dead or wounded enemies before a second engagement."""
    state = central_hero()
    target = state.rival.pos
    before = {troop.id: troop.hp for troop in state.rival.army}
    state.travel(target)
    assert state.battle_kind == 'intercept'
    for _ in range(2):
        state.battle.auto_turn()
    wounded = {unit.source_id: unit.hp for unit in state.battle.units if unit.team == 'enemy' and unit.alive}
    assert wounded.keys() < before.keys()
    assert any(hp < before[ident] for ident, hp in wounded.items())
    state.retreat()
    assert {troop.id: troop.hp for troop in state.rival.army} == wounded
    assert state.rival.pos == target
    assert state.rival.intent == 'return'
    restored = State.from_json(state.to_json())
    for campaign in (state, restored):
        campaign.travel(target)
        assert {unit.source_id: unit.hp for unit in campaign.battle.units if unit.team == 'enemy'} == wounded
    assert resolve(state) == resolve(restored)
    assert state.to_json() == restored.to_json()


def test_refitting_requires_a_return_to_stronghold_and_pays_for_actual_health_and_recruits():
    """Survivors march home wounded, then spend treasury gold on healing and fresh IDs."""
    from eador.rival import RECRUIT_COSTS, STRONGHOLD

    state = central_hero()
    original_ids = {troop.id for troop in state.rival.army}
    state.travel(state.rival.pos)
    for _ in range(2):
        state.battle.auto_turn()
    state.retreat()
    health = {troop.id: troop.hp for troop in state.rival.army}
    for _ in range(6):
        if state.rival.pos == STRONGHOLD:
            break
        gold = state.rival.gold + state.rival.income(state) - state.rival.upkeep
        state.end_turn()
        assert state.rival.gold == gold
        assert {troop.id: troop.hp for troop in state.rival.army} == health
    assert state.rival.pos == STRONGHOLD
    assert state.rival.intent == 'recover'
    gold = state.rival.gold + state.rival.income(state) - state.rival.upkeep
    missing = sum(troop.max_hp - troop.hp for troop in state.rival.army)
    state.end_turn()
    assert all(troop.hp == troop.max_hp for troop in state.rival.army)
    assert state.rival.gold == gold - missing
    assert state.rival.intent == 'recruit'
    gold = state.rival.gold + state.rival.income(state) - state.rival.upkeep
    previous_ids = {troop.id for troop in state.rival.army}
    state.end_turn()
    recruits = [troop for troop in state.rival.army if troop.id not in previous_ids]
    assert len(recruits) == 1
    assert recruits[0].id not in original_ids
    assert state.rival.gold == gold - RECRUIT_COSTS[recruits[0].kind]


def test_winning_an_announced_defense_opens_a_persistent_counterattack_window():
    """The defeated army stays gone until a delayed, paid stronghold recruitment."""
    from eador.rival import RECRUIT_COSTS, STRONGHOLD

    state = central_hero()
    assert state.rival.intent == 'attack'
    assert state.rival.target == state.hero.pos
    starting_ids = {troop.id for troop in state.rival.army}
    for _ in range(state.rival.turns_until_action):
        state.end_turn()
    assert state.battle_kind == 'defense'
    assert resolve(state).startswith('Defended')
    assert state.provinces[state.hero.pos].owner == 'player'
    assert not state.rival.army
    assert state.rival.defeats == 1
    window = state.rival.turns_until_action
    assert window >= 3
    for remaining in range(window - 1, 0, -1):
        state = State.from_json(state.to_json())
        state.end_turn()
        assert not state.rival.army
        assert state.rival.turns_until_action == remaining
    gold = state.rival.gold + state.rival.income(state)
    state.end_turn()
    assert state.rival.pos == STRONGHOLD
    assert len(state.rival.army) == 1
    recruit = state.rival.army[0]
    assert recruit.id not in starting_ids
    assert state.rival.gold == gold - RECRUIT_COSTS[recruit.kind]


def test_camping_does_not_farm_repeat_victories_or_make_the_rival_oscillate():
    """A funded defender makes the rival pursue other land while the treasury lasts."""
    from pathlib import Path

    # Produced through public commands at 915dd40, before encirclement pressure.
    # Keeping this earned treasury isolates routing from the starvation regression.
    state = State.from_json((Path(__file__).parent / 'fixtures' / 'v3_fortified_capital.json').read_text())
    assert state.hero.level == 1 and state.hero.xp == 8
    for _ in range(state.gold // state.upkeep - 1):
        state.end_turn()
        assert state.battle is None
    assert state.status == 'playing'
    assert state.hero.level == 1 and state.hero.xp == 8
    assert all(province.owner == 'rival' for pos, province in state.provinces.items() if pos != state.hero.pos)
    assert state.rival.intent == 'watch'


def test_save_rejects_rival_operations_that_cannot_execute():
    """Damaged saves are rejected before their future end-turn operation can crash play."""
    import json
    import pytest
    from eador.model import SaveFormatError

    for changes in ({'intent': 'attack', 'target': None},
                    {'intent': 'march', 'target': [-2, 0]},
                    {'intent': 'recruit'}, {'intent': 'recover'}, {'army': []}):
        data = json.loads(State.new(7).to_json())
        data['rival'].update(changes)
        with pytest.raises(SaveFormatError, match='Rival'):
            State.from_json(json.dumps(data))


def test_save_rejects_duplicate_or_missing_expedition_soldiers():
    """Every persistent rival soldier must have exactly one combat identity, even when dead."""
    import json
    import pytest
    from eador.model import SaveFormatError

    state = central_hero()
    state.travel(state.rival.pos)
    data = json.loads(state.to_json())
    guards = [unit for unit in data['battle']['units'] if unit['team'] == 'enemy' and unit['kind'] == 'guard']
    guards[1]['source_id'] = guards[0]['source_id']
    with pytest.raises(SaveFormatError, match='Expedition'):
        State.from_json(json.dumps(data))
    data = json.loads(state.to_json())
    data['rival']['army'].append({'id': data['rival']['next_troop_id'], 'kind': 'guard', 'hp': 42, 'max_hp': 42})
    data['rival']['next_troop_id'] += 1
    with pytest.raises(SaveFormatError, match='Expedition'):
        State.from_json(json.dumps(data))


def test_capturing_an_announced_route_updates_it_without_postponing_the_operation():
    """Taking a marching destination refreshes the warning while preserving elapsed preparation."""
    state = State.new(7)
    state.build('barracks')
    state.recruit('swordsman')
    for _ in range(100):
        if 'temple' not in state.buildings and state.gold >= 65:
            state.build('temple')
        while state.gold >= state.recruit_cost('swordsman') and len(state.hero.army) < state.hero.max_army:
            state.recruit('swordsman')
        if (state.rival.defeats and state.rival.intent == 'march'
                and state.rival.target in state.grid.neighbors(state.hero.pos)):
            break
        state.end_turn()
        if state.battle:
            resolve(state)
    else:
        raise AssertionError('No interceptable march was announced.')
    target, countdown = state.rival.target, state.rival.turns_until_action
    state.travel(target)
    if state.battle:
        resolve(state)
    assert state.hero.pos == target
    assert state.rival.target != target or state.rival.intent == 'attack'
    assert state.rival.turns_until_action <= countdown
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    state.end_turn()
