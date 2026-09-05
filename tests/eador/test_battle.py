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
