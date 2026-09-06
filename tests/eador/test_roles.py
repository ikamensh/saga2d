"""Different troop orders enable sustain, mobile fire and extraction plans."""
import pytest

from eador.battle import Battle
from eador.model import Hero, RuleError, Troop, UNITS
from tools.eador_roles_campaign import prepare_support_watch


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
    assert actual.pop('battle_adventure') is None
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


def test_ranger_can_shoot_then_escape_but_never_refreshes_a_used_move():
    """Mobile fire is a choice of order; moving before the shot does not grant a second move."""
    battle = Battle.clash([('ranger', 22)], [('swordsman', 34)], 'plains')
    battle.move(0, (0, 0)); battle.guard(0); battle.end_turn()
    # The swordsman advances into range; the Ranger starts its next turn ready.
    target = battle.unit(1000)
    before_hp = (target.hp, battle.unit(0).hp)
    forecast = battle.preview(0, target.id)
    battle.attack(0, target.id)
    assert (before_hp[0] - target.hp, before_hp[1] - battle.unit(0).hp) == forecast
    assert battle.reachable(0) and not battle.unit(0).moved
    battle = Battle.from_dict(battle.to_dict())
    escape = max(battle.reachable(0), key=lambda pos: battle.grid.distance(pos, target.pos))
    battle.move(0, escape)
    assert battle.reachable(0) == set() and battle.targets(0) == []
    moved_first = Battle.clash([('ranger', 22)], [('swordsman', 34)], 'plains')
    moved_first.move(0, (0, 0))
    moved_first.attack(0, 1000)
    assert moved_first.reachable(0) == set()


def test_ranger_ai_withdraws_after_firing_and_an_archer_pins_its_escape():
    """AI uses the new order and an existing control ability counters its mobility."""
    battle = Battle.clash([('ranger', 22)], [('swordsman', 34)], 'plains')
    battle.move(0, (0, 0)); battle.guard(0); battle.end_turn()
    old_pos = battle.unit(0).pos
    battle.auto_turn()
    assert battle.unit(0).pos != old_pos
    pinned = Battle.clash([('ranger', 22)], [('archer', 20)], 'plains')
    pinned.move(0, (0, 0)); pinned.guard(0); pinned.end_turn()
    assert pinned.unit(0).pinned and pinned.unit(0).effective_move_range == 1
    assert all(pinned.grid.distance(pinned.unit(0).pos, pos) == 1 for pos in pinned.reachable(0))
    pinned.attack(0, 1000)
    assert pinned.reachable(0)  # Pin restricts the move; it does not disable the shot or escape.


def test_warden_extracts_an_adjacent_wounded_ally_without_refreshing_orders_or_status():
    """Swap replaces the holder, preserves Pin/Guard, and cannot create another move."""
    battle = Battle.clash([('warden', 38), ('ranger', 8)], [('archer', 20)], 'plains')
    battle.move(1, (0, 0)); battle.move(0, (-1, 0))
    battle.guard(1); battle.end_turn()
    warden, ranger = battle.unit(0), battle.unit(1)
    assert ranger.pinned
    battle.guard(1)
    old = (warden.pos, ranger.pos)
    assert battle.swap_targets(0) == [ranger]
    battle.swap(0, 1)
    assert (warden.pos, ranger.pos) == (old[1], old[0])
    assert warden.acted and warden.moved and ranger.acted and ranger.moved
    assert ranger.stance == 'guard' and ranger.pinned
    assert battle.swap_targets(0) == [] and battle.reachable(1) == set()
    saved = Battle.from_dict(battle.to_dict())
    assert saved.to_dict() == battle.to_dict()
    with pytest.raises(RuleError):
        saved.swap(0, 1)
    assert saved.to_dict() == battle.to_dict()


def test_swap_leaves_an_unspent_allied_attack_available_and_rejects_enemies():
    """Extraction consumes movement, not the ally's unspent action; it never relocates foes."""
    battle = Battle.clash([('warden', 38), ('ranger', 22)], [('archer', 20)], 'plains')
    before = battle.to_dict()
    with pytest.raises(RuleError):
        battle.swap(0, 1000)
    assert battle.to_dict() == before
    battle.swap(0, 1)
    assert battle.unit(1).moved and not battle.unit(1).acted
    assert battle.reachable(1) == set()
    battle.guard(1)


def test_an_enemy_warden_extracts_a_wounded_ranger_in_a_hero_free_clash():
    """Opposing support follows the same movement costs instead of receiving free actions."""
    battle = Battle.clash([('archer', 20)], [('warden', 38), ('ranger', 8)], 'plains')
    battle.move(0, (0, 0)); battle.guard(0)
    old_positions = (battle.unit(1000).pos, battle.unit(1001).pos)
    battle.end_turn()
    assert (battle.unit(1000).pos, battle.unit(1001).pos) == old_positions[::-1]
    assert any('Warden swaps places with Ranger' in line for line in battle.log)


@pytest.mark.parametrize('kind,building', [('ranger', 'archery'), ('warden', 'barracks')])
def test_new_recruits_require_their_building_and_preserve_paid_rosters_on_reload(kind, building):
    """New roles are reachable purchases with existing upkeep, not fixture-only capabilities."""
    from eador.model import State
    state = State.new(7)
    before = state.to_json()
    with pytest.raises(RuleError):
        state.recruit(kind)
    assert state.to_json() == before
    state.build(building)
    while state.gold < state.recruit_cost(kind):
        state.end_turn()
    gold = state.gold
    state.recruit(kind)
    assert gold - state.gold == state.recruit_cost(kind)
    assert state.hero.army[-1].kind == kind and UNITS[kind].upkeep == 2
    state.explore()
    restored = State.from_json(state.to_json())
    assert restored.to_json() == state.to_json()
    troop = next(u for u in restored.battle.units if u.kind == kind)
    assert troop.skirmisher if kind == 'ranger' else troop.can_swap


def test_a_paid_support_army_rotates_after_shooting_and_extracts_its_seal_holder():
    """Mobile fire, replacement and shared healing sustain a hold with a defender alive."""
    from eador.model import State
    from tests.eador.test_objectives import guard_army
    state = prepare_support_watch()
    assert state.turn == 7 and {t.kind for t in state.hero.army} >= {'ranger', 'warden', 'healer'}
    battle = state.battle
    for uid, destination in ((1, (1, 0)), (3, (0, -1)), (2, (0, 0)), (6, (0, 1)),
                             (4, (-1, 1)), (5, (-1, 0)), (0, (-1, -1))):
        battle.move(uid, destination)
    pike_id = next(u.id for u in battle.units if u.team == 'enemy' and u.kind == 'pikeman')
    for uid in (1, 3, 6):
        battle.attack(uid, pike_id)
    guard_army(battle); battle.end_turn()
    state = State.from_json(state.to_json())
    state.battle.attack(6, pike_id)
    assert state.battle.unit(6).acted and not state.battle.unit(6).moved
    state = State.from_json(state.to_json())
    battle = state.battle
    for uid, destination in ((1, (1, -1)), (6, (1, 0)), (4, (0, 1)), (5, (-1, 1)), (0, (-1, 0))):
        battle.move(uid, destination)
    guard_army(battle); battle.end_turn()
    assert battle.objective.progress == 1 and battle.unit(2).hp < battle.unit(2).max_hp
    state = State.from_json(state.to_json())
    battle = state.battle
    battle.swap(4, 2)
    assert battle.unit(4).pos == battle.objective.target and battle.objective.progress == 1
    assert battle.unit(2).moved and not battle.unit(2).acted
    state = State.from_json(state.to_json())
    battle = state.battle
    healed = battle.spell_preview('heal', 2, caster_id=5)
    hp, mana = battle.unit(2).hp, battle.mana
    battle.cast('heal', 2, caster_id=5)
    assert battle.unit(2).hp - hp == healed and battle.mana == mana - battle.spell_cost('heal')
    assert not battle.unit(0).acted
    guard_army(battle); battle.end_turn()
    assert battle.outcome_reason == 'hold' and battle.round == 3
    assert all(u.alive for u in battle.units if u.team == 'player')
    assert any(u.alive for u in battle.units if u.team == 'enemy')
    state = State.from_json(state.to_json())
    state.resolve_battle()
    while state.choice:
        state.choose(state.choice.options[0].id)
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    before = state.to_json()
    with pytest.raises(RuleError):
        state.resolve_battle()
    assert state.to_json() == before


def test_pin_delays_a_watch_archers_contesting_move_but_not_its_attack():
    """Control changes arrival at the authored seal; a slowed ranged defender can still shoot."""
    state = prepare_support_watch()
    battle = state.battle
    archer = next(u for u in battle.units if u.team == 'enemy' and u.kind == 'archer')
    battle.move(3, (0, 0))
    normal = Battle.from_dict(battle.to_dict())
    battle.pin(3, archer.id)
    battle.end_turn()
    normal.attack(3, archer.id)
    normal.end_turn()
    assert battle.grid.distance(battle.unit(archer.id).pos, battle.objective.target) > 1
    assert normal.grid.distance(normal.unit(archer.id).pos, normal.objective.target) == 1
    assert any('Archer hits' in line for line in battle.log)


@pytest.mark.parametrize('kind,capability', [('ranger', 'heal'), ('healer', 'swap'), ('warden', 'pin')])
def test_saved_capabilities_cannot_be_attached_to_the_wrong_recruit(kind, capability):
    """Damaged role metadata is rejected before a future order can misrepresent its actor."""
    import json
    from eador.model import SaveFormatError, State
    data = json.loads(prepare_support_watch().to_json())
    next(u for u in data['battle']['units'] if u['kind'] == kind)['abilities'] = [capability]
    with pytest.raises(SaveFormatError):
        State.from_json(json.dumps(data))
