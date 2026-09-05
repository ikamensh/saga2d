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
    while not defense.battle.outcome:
        defense.battle.auto_turn()
    expected = json.loads((fixtures / 'v2_defense_result.json').read_text())
    assert defense.battle.outcome == expected['outcome']
    assert [[u.id, u.hp, list(u.pos)] for u in defense.battle.units] == expected['units']
    defense.resolve_battle()
    assert State.from_json(defense.to_json()).to_json() == defense.to_json()
