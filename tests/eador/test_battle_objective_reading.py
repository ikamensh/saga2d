"""Objective reading retains the board command and exposes the complete scoring rule."""
from saga2d import Label
from eador.app import create_game
from eador.scene import BattleScene, ShardScene
from tools.eador_control_campaign import prepare_control_watch
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_larger_hold_instructions_preserve_the_located_seal(tmp_path):
    """Locate, resize and read the actual hold rule without spending the aimed order."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(prepare_control_watch()))
        player = PlayerInput(game)
        scene = game.scene
        assert isinstance(scene, BattleScene)
        player.press('o')
        before = player.state.to_json()
        aim = scene.selected, scene.cursor, scene.hover, scene.targeting
        player.press('f2'); player.press('right'); player.press('return')
        for window in ((1280, 720), (1280, 800), (1920, 1080)):
            game.set_window_size(window); game.tick(1 / 60)
            objective = scene.battle.objective
            expected = f'HOLD THE SEAL · {objective.progress}/{objective.required} turns · By round {objective.deadline}'
            labels = [c.text for c in scene.ui.walk() if isinstance(c, Label)]
            assert expected in labels
            assert 'Keep an ally on the seal after consecutive enemy turns, with no adjacent foe. Losing control resets progress; rout also wins.' in labels
            check_reading_layout(scene)
            assert player.state.to_json() == before
            assert (scene.selected, scene.cursor, scene.hover, scene.targeting) == aim
            assert scene.cursor == objective.target
    finally:
        game._teardown()
