"""World selection remains the same playable, saved world through visible input."""

import pytest

from saga2d import Button

from eador.app import create_game
from eador.scene import ShardScene, TitleScene
from eador.worldgen import THEMES


def press(game, name):
    game.backend.inject_key(name)
    game.backend.inject_key(name, type='key_release')
    game.tick(1 / 60)


@pytest.mark.parametrize('theme', THEMES)
def test_selected_world_and_hero_survive_title_save_and_reload(tmp_path, theme):
    """Each advertised theme starts its actual generator and returns intact from Saves."""
    game = create_game('Theme journey', backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(TitleScene(seed=17))
        for _ in range(list(THEMES).index(theme)):
            press(game, 'right')
        press(game, 'tab')
        press(game, 'return')
        assert isinstance(game.scene, ShardScene)
        state = game.scene.state
        assert state.theme == theme and state.hero.hero_class == 'Warrior'
        press(game, 'f5')
        saved = state.to_json()
        press(game, 'f1')
        press(game, 's')
        press(game, '1')
        assert isinstance(game.scene, TitleScene)
        assert game.scene.world_theme == theme
        # A different visible theme button must not alter the campaign saved earlier.
        control = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Ruins')
        x, y, w, h = control.bounds
        game.backend.inject_click(round(x + w / 2), round(y + h / 2))
        game.backend.inject_release(round(x + w / 2), round(y + h / 2))
        game.tick(1 / 60)
        press(game, 'f9')
        assert isinstance(game.scene, ShardScene) and game.scene.state.to_json() == saved
    finally:
        game._teardown()
