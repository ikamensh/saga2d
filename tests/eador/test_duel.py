"""Human armies use ordinary combat rules while retaining separate identities and magic."""
from dataclasses import asdict
import json

import pytest

from eador.battle import Battle
from eador.model import RuleError, State
from tools.cpu_budget import CpuBudget


def duel(attacker='Wizard', defender='Wizard'):
    """Start with two real fresh realms, whose troop IDs deliberately overlap."""
    realms = State.new(7, attacker), State.new(12, defender)
    battle = Battle.create_duel(realms[0].hero, realms[1].hero, 'plains',
                               realms[0].spells, realms[1].spells)
    return realms, battle


def side_unit(battle, team, source_id):
    return next(unit for unit in battle.units
                if unit.team == team and unit.source_id == source_id)


def test_two_humans_move_and_cast_on_alternating_turns_with_their_own_mana():
    """A defender acts manually after handoff; neither army spends its opponent's pool."""
    realms, battle = duel()
    armies = [asdict(realm.hero) for realm in realms]
    attacker, defender = (side_unit(battle, team, 0) for team in ('player', 'enemy'))
    with pytest.raises(RuleError, match='your units'):
        battle.guard(defender.id)
    battle.move(side_unit(battle, 'player', 1).id, (-1, 0))
    battle.move(attacker.id, (-1, -1))
    battle.cast('bolt', side_unit(battle, 'enemy', 1).id)
    assert battle.mana == realms[0].hero.mana - 4
    battle.end_turn()
    assert battle.active_team == 'enemy' and battle.round == 1
    assert defender.hp == realms[1].hero.hp  # No AI ran during the handoff.
    with pytest.raises(RuleError, match='your units'):
        battle.guard(attacker.id)
    battle.move(side_unit(battle, 'enemy', 1).id, (1, 0))
    battle.move(defender.id, (1, 1))
    battle.cast('bolt', attacker.id)
    assert battle.enemy_magic.mana == realms[1].hero.mana - 4
    assert battle.mana == realms[0].hero.mana - 4
    assert attacker.hp == realms[0].hero.hp - 14
    battle.end_turn()
    assert battle.active_team == 'player' and battle.round == 2
    assert [asdict(realm.hero) for realm in realms] == armies


def test_handoff_and_defender_magic_are_observed_and_restore_without_enabling_autoplay():
    """A pure turn change remains visible, and a saved defender turn resumes its own magic."""
    realms, battle = duel()
    solo = Battle.create(realms[0].hero, [], 'plains', realms[0].spells)
    assert set(battle.to_dict()) == set(solo.to_dict()) | {'active_team', 'enemy_magic'}
    handoff = battle.trace(battle.end_turn)
    assert len(handoff.events) == 1
    assert handoff.before.active_team == 'player' and handoff.after.active_team == 'enemy'
    saved = battle.to_dict()
    with pytest.raises(RuleError, match='human'):
        battle.auto_turn()
    assert battle.to_dict() == saved
    restored = Battle.from_dict(json.loads(json.dumps(saved)))
    assert restored.to_dict() == saved
    for actual in (battle, restored):
        actual.move(side_unit(actual, 'enemy', 1).id, (1, 0))
        actual.move(side_unit(actual, 'enemy', 0).id, (1, 1))
        trace = actual.trace(lambda: actual.cast('bolt', side_unit(actual, 'player', 3).id))
        assert trace.before.mana == trace.after.mana
        assert trace.before.enemy_mana - trace.after.enemy_mana == 4
        assert any(event.kind == 'bolt' for event in trace.events)
    assert battle.to_dict() == restored.to_dict()


@pytest.mark.parametrize('winner', ['player', 'enemy'])
def test_either_hero_can_fall_with_troops_alive_and_both_armies_receive_their_own_result(winner):
    """Three manual Bolts end the duel by hero death, with no injected damage or outcome."""
    realms, battle = duel()
    loser = 'enemy' if winner == 'player' else 'player'
    attacker = side_unit(battle, 'player', 0)
    defender = side_unit(battle, 'enemy', 0)
    battle.move(side_unit(battle, 'player', 1).id, (-1, 0))
    battle.move(attacker.id, (-1, -1))
    if winner == 'enemy':
        battle.end_turn()
        battle.move(side_unit(battle, 'enemy', 1).id, (1, 0))
        battle.move(defender.id, (1, 1))
    victim = side_unit(battle, loser, 0)
    for shot in range(3):
        battle.cast('bolt', victim.id)
        if shot < 2:
            battle.end_turn()
            battle.end_turn()
    assert battle.outcome == winner and battle.outcome_reason == 'hero_death'
    assert victim.hp == 0
    assert all(unit.alive for unit in battle.units if unit.kind != 'hero')
    saved = battle.to_dict()
    for realm, team in zip(realms, ('player', 'enemy')):
        result = realm.apply_battle_progression(battle, team=team)
        assert result.casualties == () and result.hero_levels == ()
        assert realm.hero.hp == (realm.hero.max_hp if team == winner else realm.hero.max_hp // 3)
        assert realm.hero.mana == (4 if team == winner else 16)
        assert realm.hero.xp == (8 if team == winner else 0)
        assert all(troop.xp == (3 if team == winner else 0) for troop in realm.hero.army)
    assert battle.to_dict() == saved


def test_pin_brace_and_reactions_keep_their_phase_lifetimes_between_humans():
    """Pin survives its victim's turn, while Brace reacts once and clears on its owner's turn."""
    realms = [State.new(7, 'Wizard'), State.new(12, 'Wizard')]
    for realm in realms:
        realm.build('barracks')
        realm.recruit('pikeman')
    battle = Battle.create_duel(realms[0].hero, realms[1].hero, 'plains',
                               realms[0].spells, realms[1].spells)
    pike = side_unit(battle, 'player', 4)
    archer = side_unit(battle, 'player', 3)
    enemy = side_unit(battle, 'enemy', 1)
    shooter = side_unit(battle, 'enemy', 3)
    battle.move(pike.id, (0, 0))
    battle.guard(pike.id)
    battle.move(archer.id, (0, 1))
    battle.pin(archer.id, enemy.id)
    battle.end_turn()
    assert enemy.pinned and enemy.effective_move_range == 1
    assert pike.stance == 'brace' and not pike.retaliated
    battle.move(enemy.id, (1, 0))
    predicted = battle.preview(enemy.id, pike.id)
    hp = pike.hp, enemy.hp
    trace = battle.trace(lambda: battle.attack(enemy.id, pike.id))
    assert (hp[0] - pike.hp, hp[1] - enemy.hp) == predicted
    assert [event.kind for event in trace.events] == ['brace', 'attack']
    assert pike.retaliated
    battle.pin(shooter.id, pike.id)
    assert pike.pinned
    battle.end_turn()
    assert not enemy.pinned and pike.pinned
    assert pike.stance is None and not pike.retaliated
    assert (archer.pin_cooldown, shooter.pin_cooldown) == (1, 2)
    battle.guard(pike.id)
    battle.end_turn()
    assert not pike.pinned and pike.stance == 'brace'
    assert shooter.pin_cooldown == 1


def test_both_paid_sappers_keep_smoke_until_their_next_turn_without_refunding_charges():
    """Public construction and income buy each Sapper; each smoke cloud expires independently."""
    realms = [State.new(7), State.new(12)]
    for realm in realms:
        realm.build('market')
        realm.end_turn()
        realm.end_turn()
        realm.recruit('sapper')
    battle = Battle.create_duel(realms[0].hero, realms[1].hero, 'plains',
                               realms[0].spells, realms[1].spells)
    own = side_unit(battle, 'player', 4)
    opposing = side_unit(battle, 'enemy', 4)
    battle.smoke(own.id, (-1, 2))
    battle.end_turn()
    assert [cloud.expires_before_team for cloud in battle.smoke_clouds] == ['player']
    battle.smoke(opposing.id, (1, -2))
    battle.end_turn()
    assert [cloud.expires_before_team for cloud in battle.smoke_clouds] == ['enemy']
    with pytest.raises(RuleError, match='unused charge'):
        battle.smoke(own.id, (-1, 2))
    battle.end_turn()
    assert battle.smoke_clouds == []
    with pytest.raises(RuleError, match='unused charge'):
        battle.smoke(opposing.id, (1, -2))


def test_paid_veterans_keep_class_skills_relics_and_source_ids_on_both_sides():
    """Two real conquests earn the ranks being deployed; remapping cannot flatten a defender."""
    from tools.eador_campaign import finish_battle

    budget = CpuBudget(25)
    realms = [State.new(7, kind) for kind in ('Warrior', 'Commander')]
    for realm in realms:
        realm.build('barracks')
        realm.recruit('pikeman')
        realm.explore()
        finish_battle(realm, budget=budget)
        realm.travel((-1, 0))
        finish_battle(realm, budget=budget)
        assert realm.hero.level == 2 and realm.hero.skills and realm.hero.relic
        assert all(troop.level == 2 for troop in realm.hero.army)
    saved = [realm.to_json() for realm in realms]
    battle = Battle.create_duel(realms[0].hero, realms[1].hero, 'plains',
                               realms[0].spells, realms[1].spells)
    assert len({unit.id for unit in battle.units}) == len(battle.units)
    for realm, team in zip(realms, ('player', 'enemy')):
        reference = Battle.create(realm.hero, [], 'plains', realm.spells)
        for original in reference.units:
            actual = side_unit(battle, team, original.id)
            actual_fields, original_fields = asdict(actual), asdict(original)
            for field in ('id', 'team', 'source_id', 'pos'):
                actual_fields.pop(field)
                original_fields.pop(field)
            assert actual_fields == original_fields
            assert actual.pos == (original.pos if team == 'player' else tuple(-n for n in original.pos))
    assert [realm.to_json() for realm in realms] == saved


def test_idle_human_rounds_never_award_the_solo_exhaustion_victory_to_the_defender():
    """An unresolved human stand-off remains unresolved; campaign retreat belongs to the room."""
    _, battle = duel()
    budget = CpuBudget(25)
    for _ in range(160):
        battle.end_turn()
        budget.checkpoint()
    assert battle.round == 81 and battle.outcome is None


def test_real_casualties_return_to_the_correct_overlapping_realm_ids():
    """Each human kills a different Militia source ID before a real hero-death result."""
    realms, battle = duel()
    player = lambda ident: side_unit(battle, 'player', ident).id
    enemy = lambda ident: side_unit(battle, 'enemy', ident).id
    battle.move(player(1), (-1, 0))
    battle.move(player(0), (-1, -1))
    battle.move(player(3), (0, 1))
    battle.attack(player(3), enemy(1))
    battle.cast('bolt', enemy(1))
    battle.end_turn()
    battle.move(enemy(3), (0, -1))
    battle.move(enemy(0), (1, -1))
    battle.attack(enemy(3), player(2))
    battle.cast('bolt', player(2))
    battle.end_turn()
    battle.attack(player(3), enemy(1))
    battle.cast('bolt', enemy(0))
    battle.end_turn()
    battle.attack(enemy(3), player(2))
    battle.end_turn()
    battle.cast('bolt', enemy(0))
    battle.end_turn()
    battle.end_turn()
    battle.cast('bolt', enemy(0))
    assert battle.outcome == 'player'
    before = battle.to_dict()
    for realm, team, lost_id in zip(realms, ('player', 'enemy'), (2, 1)):
        result = realm.apply_battle_progression(battle, team=team)
        assert result.casualties == ('Militia',)
        assert [troop.id for troop in realm.hero.army] == [ident for ident in (1, 2, 3) if ident != lost_id]
        assert all(troop.hp == side_unit(battle, team, troop.id).hp for troop in realm.hero.army)
    assert battle.to_dict() == before
