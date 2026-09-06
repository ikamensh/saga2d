"""Players can read build facts without changing their realm or launch choices."""

from saga2d import Label
from eador.app import create_game
from eador.diagnostics import DiagnosticScene
from eador.scene import TitleScene
from tools.eador_ui import PlayerInput


def read_all_pages(player):
    """Read the actual visible pages through their ordinary controls."""
    scene = player.game.scene
    assert isinstance(scene, DiagnosticScene)
    text = []
    for index in range(scene.pages):
        assert scene.page == index
        text += [c.text for c in scene.ui.walk() if isinstance(c, Label)]
        player.press('pagedown')
    return '\n'.join(text)


def test_build_scope_and_feedback_are_readable_from_title_and_live_guide(tmp_path):
    """About returns to the same choices/state; reading settings do not create a save."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        title = TitleScene(17, theme='ruins', hero_class='Scout', difficulty='challenge')
        game.push(title)
        player = PlayerInput(game)
        player.press('a')
        assert isinstance(game.scene, DiagnosticScene)
        player.press('t'); player.press('right'); player.press('return')
        text = read_all_pages(player)
        for fact in ('Development build', 'source checkout', 'three linked shards',
                     'balance', 'Windows', 'Ilya Kamenshchikov', 'save file', str(tmp_path)):
            assert fact in text
        player.press('escape')
        assert game.scene is title
        assert (title.seed, title.world_theme, title.hero_class, title.difficulty) == (17, 'ruins', 'Scout', 'challenge')
        assert not (tmp_path / 'saves').exists()
        player.press('return')
        saved = player.state.to_json()
        player.press('f1')
        guide = game.scene
        player.button('About this build')
        assert isinstance(game.scene, DiagnosticScene)
        read_all_pages(player)
        player.press('return')
        assert game.scene is guide and player.state.to_json() == saved
    finally:
        game._teardown()
