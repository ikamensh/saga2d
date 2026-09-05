"""Tactical commands use the same real rules as manual input and the AI."""
import pytest

from eador.battle import Battle
from eador.model import RuleError, State


def test_tactical_battle_can_be_played_saved_and_won():
    """The automatic player uses public actions and a saved battle keeps its state."""
    state = State.new()
    battle = Battle.create(state.hero, ['brigand', 'goblin'], 'forest', set(), seed=3)
    hero = battle.unit(0)
    reachable = battle.reachable(hero.id)
    assert reachable
    destination = min(reachable)
    battle.move(hero.id, destination)
    with pytest.raises(RuleError):
        battle.move(hero.id, hero.pos)
    assert Battle.from_dict(battle.to_dict()).to_dict() == battle.to_dict()
    for _ in range(40):
        if battle.outcome:
            break
        battle.auto_turn()
    assert battle.outcome == 'player'
    assert any(u.hp < u.max_hp for u in battle.units if u.team == 'player')


def test_wizard_spells_consume_mana_and_an_action_and_reject_invalid_targets():
    """Magic respects allegiance, action economy and health limits."""
    state = State.new(hero_class='Wizard')
    battle = Battle.create(state.hero, ['guard'], 'plains', state.spells)
    before = battle.to_dict()
    with pytest.raises(RuleError):
        battle.cast('bolt', 0)
    assert battle.to_dict() == before
    hero = battle.unit(0)
    enemy = next(u for u in battle.units if u.team == 'enemy')
    battle.move(0, min(battle.reachable(0), key=lambda pos: battle.grid.distance(pos, enemy.pos)))
    battle.cast('bolt', enemy.id)
    assert battle.mana == state.hero.mana - 4
    assert enemy.hp < enemy.max_hp
    with pytest.raises(RuleError, match='already acted'):
        battle.cast('bolt', enemy.id)
    battle.end_turn()
    wounded = [u for u in battle.units if u.team == 'player' and u.alive and u.hp < u.max_hp
               and battle.grid.distance(hero.pos, u.pos) <= 4]
    assert wounded
    target = wounded[0]
    hp_before = target.hp
    battle.cast('heal', target.id)
    assert hp_before < target.hp <= target.max_hp


@pytest.mark.parametrize('seed', range(12))
def test_tactical_ai_keeps_living_units_on_distinct_legal_hexes(seed):
    """Terrain, occupancy and per-unit actions hold during complete battles."""
    state = State.new(seed=seed)
    battle = Battle.create(state.hero, ['guard', 'goblin', 'wolf'], 'forest', set(), seed)
    for _ in range(80):
        live = [u for u in battle.units if u.alive]
        assert len({u.pos for u in live}) == len(live)
        assert all(u.pos in battle.grid.cells and 0 < u.hp <= u.max_hp for u in live)
        if battle.outcome:
            break
        battle.auto_turn()
    assert battle.outcome in ('player', 'enemy')


def test_attack_previews_match_real_damage_without_changing_battle():
    """Manual attacks match their forecast, including retaliation and lethal hits."""
    state = State.new()
    battle = Battle.create(state.hero, ['guard', 'brigand'], 'forest', set(), seed=5)
    saw_retaliation = saw_lethal = False
    for _ in range(40):
        for unit in battle.units:
            if battle.outcome or unit.team != 'player' or not unit.alive:
                continue
            targets = battle.targets(unit.id)
            if not targets:
                enemies = [enemy for enemy in battle.units if enemy.team == 'enemy' and enemy.alive]
                reachable = battle.reachable(unit.id)
                if reachable and enemies:
                    destination = min(reachable, key=lambda pos: min(battle.grid.distance(pos, enemy.pos) for enemy in enemies))
                    battle.move(unit.id, destination)
                targets = battle.targets(unit.id)
            if targets:
                target = min(targets, key=lambda enemy: enemy.hp)
                before = battle.to_dict()
                damage, retaliation = battle.preview(unit.id, target.id)
                assert battle.to_dict() == before
                target_hp, attacker_hp = target.hp, unit.hp
                battle.attack(unit.id, target.id)
                assert (target_hp - target.hp, attacker_hp - unit.hp) == (damage, retaliation)
                saw_retaliation |= retaliation > 0
                if target.hp == 0:
                    saw_lethal = True
                    assert retaliation == 0
        if battle.outcome:
            break
        # Enemy previews use the same forecast, without requiring player ownership.
        for unit in battle.units:
            if unit.team == 'enemy' and battle.targets(unit.id):
                battle.preview(unit.id, battle.targets(unit.id)[0].id)
        battle.end_turn()
    assert saw_retaliation and saw_lethal
