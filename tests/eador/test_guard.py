"""Defensive orders exercised through ordinary battle and campaign commands."""
import json
from dataclasses import replace
from pathlib import Path
import random

import pytest

from eador.battle import Battle, BattleUnit
from eador.model import RuleError, SaveFormatError, State, UNITS


def encounter(player='swordsman', enemy='brigand', *, player_hp=None, enemy_hp=None, enemy_pos=(1, 0)):
    """A small authored arena makes exact counterplay observable without AI setup."""
    units = []
    for ident, team, kind, pos, health in (
        (0, 'player', player, (0, 0), player_hp),
        (1000, 'enemy', enemy, enemy_pos, enemy_hp),
    ):
        spec = UNITS[kind]
        units.append(BattleUnit(ident, team, kind, pos, spec.hp if health is None else health, spec.hp,
                               spec.attack, spec.defense, spec.move_range, spec.attack_range))
    terrain = {(q, r): 'plains' for q in range(-3, 4) for r in range(-3, 4) if abs(q+r) <= 3}
    return Battle(units, terrain, 0, set(), hero_id=None)


def test_guard_spends_the_order_reduces_incoming_damage_and_expires_next_turn():
    """Guard protects this enemy phase, with no action refund or permanent armor."""
    battle = encounter()
    soldier, enemy = battle.units
    unguarded_damage = battle.preview(enemy.id, soldier.id)[0]
    battle.guard(soldier.id)
    assert soldier.effective_defense == soldier.defense + 2
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
    assert soldier.effective_defense == soldier.defense


@pytest.mark.parametrize('fixture', ['v2_defense', 'v3_battle'])
def test_older_active_battles_migrate_without_changing_their_exact_continuation(fixture):
    """Adding defensive orders does not reroll older combat or its automatic outcome."""
    fixtures = Path(__file__).parent / 'fixtures'
    state = State.from_json((fixtures / f'{fixture}.json').read_text())
    assert json.loads(state.to_json())['schema_version'] == 9
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


@pytest.mark.parametrize('pikeman_hp,enemy_hp', [(28, 5), (2, 20), (28, 20)])
def test_brace_hits_before_melee_damage_and_exact_preview_includes_either_death(pikeman_hp, enemy_hp):
    """A spear reaction happens before the blow, once, including either participant dying."""
    battle = encounter('pikeman', player_hp=pikeman_hp, enemy_hp=enemy_hp)
    pikeman, enemy = battle.units
    battle.guard(pikeman.id)
    before = battle.to_dict()
    prediction = battle.preview(enemy.id, pikeman.id)
    spear_damage = min(enemy_hp, pikeman.attack - enemy.defense)
    incoming = 0 if spear_damage == enemy_hp else min(pikeman_hp, enemy.attack - pikeman.defense)
    assert prediction == (incoming, spear_damage)
    assert battle.to_dict() == before
    battle.end_turn()
    assert (pikeman_hp - pikeman.hp, enemy_hp - enemy.hp) == prediction
    assert pikeman.stance is None
    assert battle.outcome == ('player' if spear_damage == enemy_hp else 'enemy' if incoming == pikeman_hp else None)


def test_one_brace_cannot_hit_a_second_attacker_in_the_same_enemy_turn():
    """The first spear hit spends the defensive reaction even when it kills its attacker."""
    battle = encounter('pikeman', enemy_hp=5)
    pikeman, first = battle.units
    second = replace(first, id=1001, hp=first.max_hp, pos=(0, 1))
    battle.units.append(second)
    battle.guard(pikeman.id)
    battle = Battle.from_dict(battle.to_dict())
    battle.end_turn()
    assert battle.unit(first.id).hp == 0
    assert battle.unit(second.id).hp == second.hp
    assert battle.unit(pikeman.id).hp == pikeman.hp - (second.attack - pikeman.defense)


@pytest.mark.parametrize('distance', [1, 2])
def test_ranged_attackers_bypass_brace_even_at_point_blank_range(distance):
    """A bow can finish a wounded bracing Pikeman without triggering the pre-attack spear."""
    battle = encounter('pikeman', 'archer', player_hp=2, enemy_pos=(distance, 0))
    pikeman, archer = battle.units
    battle.guard(pikeman.id)
    assert battle.preview(archer.id, pikeman.id) == (2, 0)
    battle.end_turn()
    assert not pikeman.alive and archer.hp == archer.max_hp
    assert battle.outcome == 'enemy'


def test_barracks_recruitment_provides_a_pikeman_with_a_saved_brace_order():
    """The fifth recruit is affordable through ordinary play and carries its stance into saves."""
    state = State.new()
    before = state.to_json()
    with pytest.raises(RuleError):
        state.recruit('pikeman')
    assert state.to_json() == before
    state.build('barracks')
    gold = state.gold
    state.recruit('pikeman')
    assert state.gold == gold - state.recruit_cost('pikeman')
    troop = state.hero.army[-1]
    assert troop.kind == 'pikeman'
    state.explore()
    state.battle.guard(troop.id)
    assert state.battle.unit(troop.id).stance == 'brace'
    assert not state.battle.reachable(troop.id) and not state.battle.targets(troop.id)
    restored = State.from_json(state.to_json())
    assert restored.to_json() == state.to_json()
    for campaign in (state, restored):
        campaign.battle.end_turn()
    assert restored.to_json() == state.to_json()


def test_enemy_pikemen_brace_after_advancing_and_expire_at_their_next_team_turn():
    """Hero-free auto-play can set a stance that protects the intervening player turn."""
    battle = encounter('archer', 'pikeman', enemy_pos=(3, 0))
    battle.move(0, (-2, 0))
    battle.end_turn()
    pikeman = battle.unit(1000)
    assert pikeman.stance == 'brace'
    snapshot = Battle.from_dict(battle.to_dict())
    for combat in (battle, snapshot):
        # Approach without striking, so Brace must expire rather than be consumed.
        destination = min(combat.reachable(0), key=lambda pos: combat.grid.distance(pos, combat.unit(1000).pos))
        combat.move(0, destination)
        combat.end_turn()
        assert combat.unit(1000).stance is None
    assert snapshot.to_dict() == battle.to_dict()


@pytest.mark.parametrize('health', [5, 17])
def test_player_attack_matches_the_braced_enemy_preview_including_a_lethal_spear(health):
    """A visible enemy stance gives the same exact forecast through the player's attack command."""
    battle = encounter('wolf', 'pikeman', player_hp=health, enemy_pos=(3, 0))
    battle.move(0, (-2, 0))
    battle.end_turn()
    battle.move(0, (0, 0))
    before = battle.to_dict()
    target_hp = battle.unit(1000).hp
    prediction = battle.preview(0, 1000)
    assert battle.to_dict() == before
    battle.attack(0, 1000)
    assert (target_hp - battle.unit(1000).hp, health - battle.unit(0).hp) == prediction
    assert battle.unit(1000).stance is None
    assert battle.unit(1000).retaliated
    if health == 5:
        assert prediction == (0, 5) and battle.outcome == 'enemy'


def test_a_ranged_player_attack_leaves_the_enemy_brace_unspent():
    """Ranged counterplay deals normal damage without consuming a stance reserved for melee."""
    battle = encounter('archer', 'pikeman', enemy_pos=(3, 0))
    battle.move(0, (-2, 0))
    battle.end_turn()
    assert battle.unit(1000).stance == 'brace'
    prediction = battle.preview(0, 1000)
    assert prediction[1] == 0
    battle.attack(0, 1000)
    assert battle.unit(1000).stance == 'brace'
    assert battle.unit(1000).hp == UNITS['pikeman'].hp - prediction[0]
    battle.end_turn()
    assert battle.unit(1000).stance is None


def test_brace_reserves_one_reaction_when_adjacent_ranged_fire_precedes_melee():
    """An Archer cannot draw ordinary retaliation and leave a second spear reaction available."""
    battle = encounter('archer', 'pikeman')
    spec = UNITS['swordsman']
    swordsman = BattleUnit(1, 'player', 'swordsman', (1, -1), spec.hp, spec.hp,
                           spec.attack, spec.defense, spec.move_range, spec.attack_range)
    battle.units.append(swordsman)
    data = battle.to_dict()
    data['units'][1]['stance'] = 'brace'
    battle = Battle.from_dict(data)
    pikeman = battle.unit(1000)
    assert battle.preview(0, pikeman.id)[1] == 0
    battle.attack(0, pikeman.id)
    assert battle.unit(0).hp == UNITS['archer'].hp
    assert pikeman.stance == 'brace' and not pikeman.retaliated
    prediction = battle.preview(swordsman.id, pikeman.id)
    health = pikeman.hp
    battle.attack(swordsman.id, pikeman.id)
    assert (health - pikeman.hp, spec.hp - battle.unit(swordsman.id).hp) == prediction
    assert pikeman.stance is None and pikeman.retaliated


def test_an_enemy_guard_protects_the_player_phase_and_expires_before_its_own_order():
    """A restored enemy Guard has the same armor and own-turn lifetime as a player's Guard."""
    battle = encounter(enemy='guard')
    data = battle.to_dict()
    data['units'][1]['stance'] = 'guard'
    battle = Battle.from_dict(data)
    defender = battle.unit(1000)
    assert defender.effective_defense == defender.defense + 2
    prediction = battle.preview(0, 1000)
    old_hp = defender.hp
    battle.attack(0, 1000)
    assert defender.hp == old_hp - prediction[0]
    assert defender.stance == 'guard'
    battle.end_turn()
    assert defender.stance is None and defender.effective_defense == defender.defense


@pytest.mark.parametrize('seed', range(12))
def test_mixed_defensive_orders_preserve_hero_free_clash_rules_and_saved_continuation(seed):
    """Both armies use new recruits and saved stances without invalid health or occupied hexes."""
    rng = random.Random(seed)
    kinds = ('pikeman', 'swordsman', 'archer')
    army = [(kind, UNITS[kind].hp) for kind in kinds]
    battle = Battle.clash(army, list(reversed(army)), ('plains', 'forest', 'marsh')[seed % 3], seed)
    for _ in range(80):
        if battle.outcome:
            break
        for unit in battle.units:
            if unit.team == 'player' and unit.alive and not unit.acted and rng.random() < 0.3:
                battle.guard(unit.id)
        restored = Battle.from_dict(battle.to_dict())
        for combat in (battle, restored):
            combat.auto_turn()
            alive = [unit for unit in combat.units if unit.alive]
            assert len({unit.pos for unit in alive}) == len(alive)
            assert all(0 <= unit.hp <= unit.max_hp for unit in combat.units)
        assert restored.to_dict() == battle.to_dict()
    assert battle.outcome in ('player', 'enemy')
