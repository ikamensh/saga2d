"""Public journey policies must not silently bypass the shipped input controls."""
import pytest

from eador.app import create_game
from eador.model import State
from eador.scene import ShardScene
from tools.eador_linked_campaign import lose_shard
from tools.eador_ui import PlayerInput


def test_an_unadapted_campaign_command_is_refused_before_mutating_a_ready_recovery(tmp_path):
    """Forwarded reads are useful; forwarding recovery would change the model behind its screen."""
    state = State.new_campaign(7)
    lose_shard(state)
    assert state.campaign.phase == 'recovery'
    game = create_game(backend='mock', save_dir=tmp_path)
    player = PlayerInput(game)
    try:
        game.push(ShardScene(state))
        before = state.to_json()
        assert player.state.to_json() == before
        with pytest.raises(AssertionError, match='No input adapter for.*recover'):
            player.state.recover(troop_ids=(), relic_ids=())
        assert state.to_json() == before and player.events == []
    finally:
        game._teardown()


def test_battle_queries_do_not_allow_a_policy_to_move_without_an_input_adapter(tmp_path):
    """A legal queried move must still pass through PlayerOrders to count as an input journey."""
    state = State.new(7)
    state.travel((-1, 0))
    game = create_game(backend='mock', save_dir=tmp_path)
    player = PlayerInput(game)
    try:
        game.push(ShardScene(state))
        destination = min(player.state.battle.reachable(0))
        before = state.to_json()
        with pytest.raises(AssertionError, match='No input adapter for.*move'):
            player.state.battle.move(0, destination)
        assert state.to_json() == before and player.events == []
    finally:
        game._teardown()
