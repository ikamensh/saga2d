"""Campaign behavior exercised through the same commands as the game scenes."""
import pytest

from eador.model import RuleError, State


def test_a_seeded_shard_can_build_recruit_and_survive_a_save():
    """A first turn and its progress survive a portable JSON save."""
    state = State.new(seed=7)
    assert len(state.provinces) == 19
    assert state.to_json() == State.new(seed=7).to_json()
    starting_army = len(state.hero.army)
    state.build('barracks')
    state.recruit('swordsman')
    assert len(state.hero.army) == starting_army + 1
    assert state.gold >= 0
    assert State.from_json(state.to_json()).to_json() == state.to_json()
    with pytest.raises(RuleError, match='already'):
        state.build('barracks')
