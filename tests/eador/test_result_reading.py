"""Battle conclusions keep their saved consequences readable before acceptance."""
from saga2d import Label

from eador.app import create_game
from eador.model import State
from eador.scene import BattleScene, ResultScene, ShardScene, TitleScene
from eador.settings_scene import SettingsScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_battle_result_reflows_without_resolving_or_losing_its_saved_outcome(tmp_path):
    """Win through input, inspect the larger result and its saves, then resolve that exact victory once."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        game.push(TitleScene(7, hero_class='Wizard'))
        player.press('return')
        player.press('x')
        while isinstance(game.scene, BattleScene):
            player.press('a')
        assert isinstance(game.scene, ResultScene)
        before = player.state.to_json()
        for key in ('t', 'right'):
            player.press(key)
        assert isinstance(game.scene, SettingsScene)
        player.press('escape')
        assert not (tmp_path / 'settings.json').exists()
        for key in ('t', 'right', 'return', 'c', 'escape'):
            player.press(key)
        assert isinstance(game.scene, ResultScene)
        assert player.state.to_json() == before
        check_reading_layout(game.scene)
        player.press('f5')
        assert any('Saved to Manual 1' in label.text
                   for label in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
        check_reading_layout(game.scene)
        player.press('f9')
        assert isinstance(game.scene, ResultScene) and player.state.to_json() == before
        expected = State.from_json(before)
        expected.resolve_battle()
        player.button('Return to shard')
        assert player.state.to_json() == expected.to_json()
        assert not any(isinstance(scene, ResultScene) for scene in game.scenes)
    finally:
        game._teardown()


def test_result_save_errors_keep_the_battle_and_damaged_file_intact(tmp_path):
    """Refused save/load writes remain readable immediately, including after a settings round trip."""
    from tools.verify_eador_results import prepared_results

    before = dict(prepared_results())['rout']
    saves = tmp_path / 'saves'
    saves.mkdir()
    manual = saves / 'save_1.json'
    manual.write_bytes(b'damaged manual save')
    game = create_game(backend='mock', save_dir=saves)
    player = PlayerInput(game)
    try:
        game.push(ShardScene(State.from_json(before)))
        for key in ('t', 'right', 'return'):
            player.press(key)
        for shortcut in ('f5', 'f9'):
            player.press(shortcut)
            assert isinstance(game.scene, ResultScene)
            assert game.scene.message and any(label.text == game.scene.message
                   for label in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
            check_reading_layout(game.scene)
            assert player.state.to_json() == before and manual.read_bytes() == b'damaged manual save'
        message = game.scene.message
        for key in ('t', 'left', 'escape'):
            player.press(key)
        assert game.scene.message == message
        check_reading_layout(game.scene)
    finally:
        game._teardown()


def test_earned_result_types_preserve_their_entire_outcome_at_each_reading_size(tmp_path):
    """Rout, extraction, hold, deadlines, hero death and world conclusions remain read-only and in bounds."""
    from tools.verify_eador_results import prepared_results

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        for _, before in prepared_results():
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                game.clear_and_push(ShardScene(State.from_json(before)))
                assert isinstance(game.scene, ResultScene)
                for percent in (100, 125):
                    for key in ('t', 'left' if percent == 100 else 'right', 'return'):
                        player.press(key)
                    check_reading_layout(game.scene)
                    assert player.state.to_json() == before
    finally:
        game._teardown()
