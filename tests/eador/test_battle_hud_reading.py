"""Battle reading preserves orders while exposing complete unit facts and recent events."""
from saga2d import Label
from eador.app import create_game
from eador.model import State
from eador.scene import ShardScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_unit_facts_guidance_and_log_follow_a_saved_order_at_larger_size(tmp_path):
    """Read a selected hero, guard through its control, and retain its exact logged result."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(State.new(7)))
        player = PlayerInput(game)
        player.click(*game.scene.grid.center((-1, 0))); player.press('return')
        scene = game.scene
        player.press('f2'); player.press('right'); player.press('return')
        before = player.state.to_json()
        selected = scene.battle.unit(scene.selected)
        for window in ((1280, 720), (1280, 800), (1920, 1080)):
            game.set_window_size(window); game.tick(1 / 60)
            labels = [c.text for c in scene.ui.walk() if isinstance(c, Label)]
            assert f'{selected.hp} / {selected.max_hp} HP' in labels
            assert f'Attack {selected.attack}   Defense {selected.effective_defense}' in labels
            assert scene.order_hint() in labels
            assert all(line in labels for line in scene.battle.log[-3:])
            check_reading_layout(scene)
            assert player.state.to_json() == before
        centers = {pos: scene.grid.center(pos) for pos in scene.battle.terrain}
        player.button('Guard')
        assert selected.acted and selected.stance == 'guard'
        assert scene.battle.log[-1] in [c.text for c in scene.ui.walk() if isinstance(c, Label)]
        assert {pos: scene.grid.center(pos) for pos in scene.battle.terrain} == centers
        player.reload(player.state.to_json())
    finally:
        game._teardown()


def test_random_input_can_leave_the_battle_log_and_complete_its_campaign():
    """The seed that clicked the new log must preserve state and reach the replay control."""
    from collections import Counter
    from tools.fuzz_eador import scene_run
    metrics = Counter()
    scene_run(4, 120, metrics)
    assert metrics['message_reader_inputs'] > 0 and metrics['replays'] == 1


def test_complete_log_is_read_only_and_returns_to_the_same_aim(tmp_path):
    """Battle hotkeys stay isolated while the player reads events and changes text size."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(State.new(7)))
        player = PlayerInput(game)
        player.click(*game.scene.grid.center((-1, 0))); player.press('return')
        player.press('g'); player.press('tab'); player.press('f')
        scene = game.scene
        before = player.state.to_json()
        aim = scene.selected, scene.cursor, scene.hover, scene.targeting
        player.button('Battle log')
        viewer = game.scene
        assert viewer is not scene
        assert '\n'.join(scene.battle.log) in [c.text for c in viewer.ui.walk() if isinstance(c, Label)]
        for key in ('a', 'g', 'e', '1', 'f5', 'f9'):
            player.press(key)
            assert game.scene is viewer and player.state.to_json() == before
        player.press('t'); player.press('right'); player.press('return')
        check_reading_layout(viewer)
        player.press('escape')
        assert game.scene is scene and player.state.to_json() == before
        assert (scene.selected, scene.cursor, scene.hover, scene.targeting) == aim
    finally:
        game._teardown()
