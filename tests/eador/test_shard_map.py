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
        for key in ('f2', 'right', 'return'):
            player.press(key)
        province = state.provinces[(-1, 0)]

        def visible_names():
            return {item.text for item in game.scene.ui.walk() if isinstance(item, Label) and item.visible}

        assert province.name not in visible_names()
        assert state.provinces[state.rival.target].name in visible_names(), 'The announced attack stays locatable'
        game.backend.inject_mouse_move(*game.scene.grid.center(province.pos))
        game.tick(1 / 60)
        assert province.name in visible_names()
        name = game.scene.ui.find(lambda item: isinstance(item, Label) and item.text == province.name)
        assert name.bounds[1] > 100, 'Hover name belongs beside the map, clear of the title toolbar'
        x, y, width, height = name.bounds
        cx, cy = game.scene.grid.center(province.pos)
        assert x <= cx <= x + width and y <= cy <= y + height, (
            'The revealed name must belong visually to the hovered province, not its neighbor')
        game.backend.inject_mouse_move(2, 2)
        game.tick(1 / 60)
        assert province.name not in visible_names()
        player.press('tab')
        assert game.scene.selected == province.pos and province.name in visible_names()
        other = state.provinces[(-2, 1)]
        game.backend.inject_mouse_move(*game.scene.grid.center(other.pos))
        game.tick(1 / 60)
        assert other.name in visible_names()
        player.click(*game.scene.grid.center(other.pos))
        assert game.scene.selected == other.pos, 'Hover names must not consume province clicks'
        assert state.to_json() == before
    finally:
        game.close()


def test_current_province_promotes_the_available_exploration_order(tmp_path):
    """The starting site has a named action, and clicking it enters that exact adventure."""
    from saga2d import Button
    from eador.scene import BattleScene

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        state = State.new(7)
        game.push(ShardScene(state))
        player = PlayerInput(game)
        game.tick(0)
        explore = game.scene.ui.find(lambda item: isinstance(item, Button)
                                     and item.text == 'Explore current province')
        assert explore.enabled and explore.show_text
        assert game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Hero is here') is None
        expected = State.from_json(state.to_json())
        expected.explore()
        player.button('Explore current province')
        assert isinstance(game.scene, BattleScene)
        assert state.to_json() == expected.to_json()
    finally:
        game.close()
