"""Launch configuration uses the same native/mock game and real save files."""

from eador.__main__ import create_session
from eador.preferences import load_preferences
from eador.scene import ShardScene, TitleScene
from tools.eador_ui import PlayerInput


def test_separate_data_directory_keeps_preferences_and_campaigns_together(tmp_path):
    """An isolated playtest starts, saves, exits and reloads without the normal profile."""
    directory = tmp_path / 'independent playtest'
    arguments = ['--data-dir', str(directory), '--hero', 'Wizard', '--difficulty', 'challenge']
    game, title = create_session(arguments, backend='mock')
    try:
        assert isinstance(title, TitleScene)
        game.push(title)
        player = PlayerInput(game)
        player.press('t'); player.press('right'); player.press('return')
        player.press('l')
        assert isinstance(game.scene, ShardScene)
        assert player.state.hero.hero_class == 'Wizard'
        assert player.state.difficulty == 'challenge' and player.state.campaign
        player.press('f5')
        saved = player.state.to_json()
        assert (directory / 'saves' / 'save_1.json').is_file()
        assert (directory / 'settings.json').is_file()
        assert game.data_dir == directory
    finally:
        game._teardown()
    game, title = create_session(arguments, backend='mock')
    try:
        game.push(title)
        assert load_preferences(game)['codex_text_scale'] == 125
        player = PlayerInput(game)
        player.press('f9')
        assert player.state.to_json() == saved
    finally:
        game._teardown()
