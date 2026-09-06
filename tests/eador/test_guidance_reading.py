"""Reading size extends to complete guidance without changing campaign commands."""

from eador.app import create_game
from eador.model import State
from eador.scene import HelpScene, ShardScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def guide_body_size(game):
    return next(record['font_size'] for record in game.backend.texts if record['text'].startswith('Build a barracks'))


def test_guide_shares_reading_preview_cancel_apply_and_restart(tmp_path):
    """The Guide visibly reflows at125; Cancel restores100 and no reading action changes a save."""
    state = State.new(7)
    saved = state.to_json()
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(state))
        player = PlayerInput(game)
        player.press('f1')
        assert isinstance(game.scene, HelpScene) and guide_body_size(game) == 12
        for key in ('o', 'd', 'down', 'down', 'down', 'right', 'escape'):
            player.press(key)
        assert isinstance(game.scene, HelpScene) and guide_body_size(game) == 12
        assert not (tmp_path / 'settings.json').exists()
        for key in ('o', 'd', 'down', 'down', 'down', 'right', 'return'):
            player.press(key)
        assert isinstance(game.scene, HelpScene) and guide_body_size(game) == 15
        check_reading_layout(game.scene)
        assert state.to_json() == saved
        player.press('c')
        assert any(record['font_size'] == 16 and 'Recruit for' in record['text'] for record in game.backend.texts)
        player.press('escape')
        assert isinstance(game.scene, HelpScene)
    finally:
        game._teardown()
    restarted = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        restarted.push(ShardScene(State.from_json(saved)))
        PlayerInput(restarted).press('f1')
        assert guide_body_size(restarted) == 15
        check_reading_layout(restarted.scene)
    finally:
        restarted._teardown()
