"""The policy adapter uses the same paged review and explicit confirmation as a player."""
import json
from pathlib import Path

from eador.app import create_game
from eador.model import State
from eador.scene import ShardScene
from tools.eador_ui import PlayerInput


def test_paid_replacement_adapter_preserves_exact_identity_and_leaves_reload_to_caller(tmp_path):
    """Two replacements follow visible pages and fresh IDs; the caller controls saved continuation."""
    path = Path(__file__).parents[2] / 'docs/evidence/crystal-service-comparison.examples.json'
    state = State.from_json(json.dumps(json.loads(path.read_text())['late_full_roster']['state']))
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        for key in ('h', 't', 'right', 'return', 'escape'):
            player.press(key)
        player.state.build('archery')
        player.state.build('mage_tower')
        outgoing_id = state.hero.army[-1].id
        for kind in ('skyrider', 'warden'):
            before = player.state.to_json()
            expected = State.from_json(before)
            quote = player.state.replacement_preview(outgoing_id, kind)
            assert player.state.to_json() == before
            expected.replace_troop(outgoing_id, kind)
            first_event = len(player.events)
            player.state.replace_troop(outgoing_id, kind)
            assert isinstance(game.scene, ShardScene) and len(game.scenes) == 1
            assert player.state.to_json() == expected.to_json()
            events = player.events[first_event:]
            assert any(scene == 'ReplacementScene' and key == 'return' for scene, _, key in events)
            assert not any(key in ('f5', 'f9') for _, _, key in events)
            assert player.reloads == (0 if kind == 'skyrider' else 1)
            player.reload(player.state.to_json())
            outgoing_id = quote.incoming.id
        assert player.reloads == 2
        assert outgoing_id == player.state.hero.army[-1].id
    finally:
        game._teardown()


def test_refused_policy_orders_do_not_fall_through_and_ordinary_recruit_keeps_zero_action_cost(tmp_path):
    """An unavailable role fails before input; exhausting replacement actions still permits ordinary recruitment."""
    import pytest
    from eador.model import RuleError

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(State.new()))
        player = PlayerInput(game)
        before, events = player.state.to_json(), list(player.events)
        with pytest.raises(AssertionError, match='Build Mage Tower first'):
            player.state.replace_troop(1, 'adept')
        assert player.state.to_json() == before and player.events == events
        outgoing_id = 1
        while player.state.actions_left:
            quote = player.state.replacement_preview(outgoing_id, 'militia')
            player.state.replace_troop(outgoing_id, 'militia')
            outgoing_id = quote.incoming.id
        before, events = player.state.to_json(), list(player.events)
        with pytest.raises(AssertionError, match='No campaign actions remain'):
            player.state.replace_troop(outgoing_id, 'militia')
        with pytest.raises(RuleError, match='living troop'):
            player.state.replace_troop(1, 'militia')
        assert player.state.to_json() == before and player.events == events
        expected = State.from_json(before)
        expected.recruit('militia')
        player.state.recruit('militia')
        assert player.state.to_json() == expected.to_json() and player.state.actions_left == 0
        player.reload(player.state.to_json())
    finally:
        game._teardown()


def test_saved_last_action_replacement_keeps_the_visible_missed_interception(tmp_path):
    """A real pursuit state loses its current intercept action and the warned territory after waiting."""
    path = Path(__file__).parents[2] / 'docs/evidence/crystal-service-comparison.examples.json'
    state = State.from_json(json.dumps(json.loads(path.read_text())['pursuit_last_action']['state']))
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        assert state.actions_left == 1 and state.rival.intent == 'attack'
        destination, target = state.rival.pos, state.rival.target
        expected = State.from_json(state.to_json())
        expected.replace_troop(1, 'warden')
        player.state.replace_troop(1, 'warden')
        assert player.state.actions_left == 0 and player.state.to_json() == expected.to_json()
        before = player.state.to_json()
        player.state.travel(destination)
        assert player.state.to_json() == before and isinstance(game.scene, ShardScene)
        player.reload(before)
        expected.end_turn()
        player.state.end_turn()
        assert player.state.to_json() == expected.to_json()
        assert player.state.provinces[target].owner == 'rival'
        player.reload(player.state.to_json())
    finally:
        game._teardown()
