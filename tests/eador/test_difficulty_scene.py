"""Difficulty selection controls new runs while saved realm rules stay authoritative."""
import pytest

from eador.app import create_game
from eador.scene import ShardScene, TitleScene
from tools.eador_ui import PlayerInput


@pytest.mark.parametrize('mode,key', [('accessible', '1'), ('standard', '2'), ('challenge', '3')])
def test_title_keyboard_and_mouse_select_the_actual_standalone_and_linked_rules(tmp_path, mode, key):
    """Visible choices supply grants and warnings to both starting paths without touching saved runs."""
    from eador.difficulty import DIFFICULTIES
    rules = DIFFICULTIES[mode]
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        player = PlayerInput(game)
        game.push(TitleScene(17, theme='ruins', hero_class='Wizard'))
        player.press(key)
        assert rules.description in ' '.join(t['text'] for t in game.backend.texts)
        player.press('return')
        assert isinstance(game.scene, ShardScene)
        state = game.scene.state
        assert state.rules is rules and state.theme == 'ruins' and state.hero.hero_class == 'Wizard'
        assert (state.gold, state.crystals) == (rules.starting_gold, rules.starting_crystals)
        assert state.rival.turns_until_action == rules.opening_delay
        player.press('f5')
        saved = state.to_json()
        player.press('f1'); player.press('s'); player.press('1')
        assert isinstance(game.scene, TitleScene)
        player.button('Standard' if mode != 'standard' else 'Challenge')
        player.press('f9')
        assert game.scene.state.to_json() == saved
        game.clear_and_push(TitleScene(17, hero_class='Wizard'))
        game.tick(1 / 60)
        player.button(rules.title)
        player.press('l')
        assert game.scene.state.rules is rules and game.scene.state.campaign is not None
    finally:
        game._teardown()
