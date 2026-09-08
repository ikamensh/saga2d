"""The shard stays readable while names remain available to mouse and keyboard."""
from saga2d import Label
from eador.app import create_game
from eador.model import State
from eador.scene import ShardScene
from tools.eador_ui import PlayerInput


def test_province_names_reveal_on_hover_and_keyboard_selection_without_orders(tmp_path):
    """Ordinary provinces do not cover the terrain; pointing or Tab reveals their full name."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        state = State.new(7)
        game.push(ShardScene(state))
        player = PlayerInput(game)
        before = state.to_json()
        province = state.provinces[(-1, 0)]

        def visible_names():
            return {item.text for item in game.scene.ui.walk() if isinstance(item, Label) and item.visible}

        assert province.name not in visible_names()
        game.backend.inject_mouse_move(*game.scene.grid.center(province.pos))
        game.tick(1 / 60)
        assert province.name in visible_names()
        name = game.scene.ui.find(lambda item: isinstance(item, Label) and item.text == province.name)
        assert name.bounds[1] > 100, 'Hover name belongs beside the map, clear of the title toolbar'
        game.backend.inject_mouse_move(2, 2)
        game.tick(1 / 60)
        assert province.name not in visible_names()
        player.press('tab')
        assert game.scene.selected == province.pos and province.name in visible_names()
        assert state.to_json() == before
    finally:
        game.close()
