"""Earned decisions reflow without changing their saved consequences."""

from saga2d import Label

from eador.app import create_game
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import ChoiceScene, ShardScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def first_reward():
    """Win the starting shrine through public tactics, leaving its reward undecided."""
    state = State.new(7, 'Wizard')
    state.explore()
    for _ in range(80):
        if state.battle.outcome:
            break
        state.battle.auto_turn()
    assert state.battle.outcome == 'player'
    state.resolve_battle()
    assert state.choice.context == 'moonstone'
    return state


def test_choice_reading_preview_restart_and_numbered_reward(tmp_path):
    """Reading overlays do not choose; a restarted 125% reward keeps complete text and its real effects."""
    state = first_reward()
    before = state.to_json()
    saves = tmp_path / 'saves'
    game = create_game(backend='mock', save_dir=saves)
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        assert isinstance(game.scene, ChoiceScene)
        for key in ('t', 'right', 'escape'):
            player.press(key)
        assert reading_scale(game) == 100
        assert not (tmp_path / 'settings.json').exists()
        for key in ('t', 'right', 'return', 'c', 'escape'):
            player.press(key)
        assert isinstance(game.scene, ChoiceScene)
        assert reading_scale(game) == 125
        assert state.to_json() == before
        check_reading_layout(game.scene)
        labels = [item.text for item in game.scene.ui.find_all(lambda item: isinstance(item, Label))]
        for option in state.choice.options:
            assert option.name in labels and option.description in labels
        assert any(row['text'] == 'Keep Moonstone' and row['font_size'] == 21 for row in game.backend.texts)
        player.reload(before)
        assert isinstance(game.scene, ChoiceScene)
    finally:
        game._teardown()

    restarted = create_game(backend='mock', save_dir=saves)
    try:
        restarted.push(ShardScene(State.from_json(before)))
        player = PlayerInput(restarted)
        restarted.tick(1 / 60)
        assert reading_scale(restarted) == 125
        check_reading_layout(restarted.scene)
        expected = State.from_json(before)
        expected.choose(expected.choice.options[1].id)
        player.press('2')
        assert player.state.to_json() == expected.to_json()
        assert 'moonstone' not in player.state.inventory
        player.press('2')
        assert player.state.to_json() == expected.to_json()
    finally:
        restarted._teardown()
