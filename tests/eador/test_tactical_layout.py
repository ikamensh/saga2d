"""The tactical canvas gives pieces room without moving the player's aimed hex."""

from saga2d import Button, Label

from eador.app import create_game
from eador.diagnostics import DiagnosticScene
from eador.model import State
from eador.scene import BattleScene, TitleScene
from eador.ui import icon_path
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def test_compact_footer_enlarges_the_board_and_keeps_the_complete_log(tmp_path):
    """A fresh 125% battle keeps 75%-scale pieces, stable picking and readable log history."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        game.push(TitleScene(7, hero_class='Wizard'))
        for key in ('return', 'x', 'f2', 'right', 'return'):
            player.press(key)
        scene = game.scene
        assert type(scene) is BattleScene
        # Radius 42 retains at least 75% of the 56px reference miniature;
        # the old native board was about 36.7px (mock tracer: 37.8px).
        assert scene.grid.size >= 42, scene.grid.size
        for label, name in (('Auto-play one round', 'auto_play'), ('Retreat', 'retreat'), ('Battle log', 'log')):
            control = scene.ui.find(lambda item: isinstance(item, Button) and item.text == label)
            assert control is not None and control.icon == icon_path(name) and not control.show_text
            assert control.bounds[2] <= 90
        check_reading_layout(scene)
        centers = {pos: scene.grid.center(pos) for pos in scene.battle.terrain}
        before = player.state.to_json()
        player.press('tab'); player.press('f')
        assert player.state.to_json() == before
        expected = State.from_json(before)
        expected.battle.guard(scene.selected)
        player.button('Guard')
        assert player.state.to_json() == expected.to_json()
        assert scene.battle.log[-1] in [item.text for item in scene.ui.walk() if isinstance(item, Label)]
        assert {pos: scene.grid.center(pos) for pos in scene.battle.terrain} == centers
        aim = scene.selected, scene.cursor, scene.hover, scene.targeting
        for through_key in (False, True):
            player.press('l') if through_key else player.button('Battle log')
            assert isinstance(game.scene, DiagnosticScene)
            assert game.scene.message == '\n'.join(scene.battle.log)
            check_reading_layout(game.scene)
            player.press('e')
            assert isinstance(game.scene, DiagnosticScene) and player.state.to_json() == expected.to_json()
            player.press('escape')
            assert game.scene is scene and (scene.selected, scene.cursor, scene.hover, scene.targeting) == aim
            assert {pos: scene.grid.center(pos) for pos in scene.battle.terrain} == centers
        player.reload(expected.to_json())
    finally:
        game.close()


def test_tactical_journey_preserves_earned_objectives_controls_and_saves(tmp_path):
    """The native route also runs through mock input, including earned pulses and a real save error."""
    from tools.verify_eador_tactical_layout import verify

    receipt = verify(tmp_path, backend='mock')
    assert len(receipt['captures']) == 8
    assert {tuple(item['window_size']) for item in receipt['captures']} == {(1280, 720), (1280, 800), (1920, 1080)}
    assert {item['reading_size'] for item in receipt['captures']} == {100, 125}
    assert {item['objective'] for item in receipt['boards']} == {'rout', 'hold', 'extract'}
    assert max(item['alive_units'] for item in receipt['boards']) == 11
    assert [(item['before'], item['after']) for item in receipt['objective_pulses']] == [(0, 1), (1, 0)]
    assert receipt['exact_reloads'] == 3 and receipt['error_pages'] >= 1
    assert receipt['control_autoplay_rounds'] == 2 and not receipt['historical_preparation_executed']
    assert receipt['source_unchanged']


def test_disabled_footer_icons_keep_their_names_and_keys_during_playback(tmp_path):
    """Hovering unavailable actions explains both their identity and why they cannot run."""
    from eador.battle_playback_scene import BattlePlaybackScene

    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game, finish_actions=False)
    try:
        game.push(TitleScene(7, hero_class='Wizard'))
        for key in ('return', 'x', 'e'):
            player.press(key)
        assert isinstance(game.scene, BattlePlaybackScene)
        before = player.state.to_json()
        for label, shortcut in (('Auto-play one round', 'A'), ('Retreat', 'T')):
            item = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == label)
            assert item is not None and not item.enabled
            x, y, width, height = item.bounds
            game.backend.inject_mouse_move(x + width / 2, y + height / 2)
            game.tick(1 / 60)
            order = max(text['order'] for text in game.backend.texts)
            shown = ' '.join(text['text'] for text in game.backend.texts if text['order'] == order)
            assert f'{label} ({shortcut})' in shown, shown
            assert 'Finish playback before giving orders.' in shown
            assert player.state.to_json() == before
    finally:
        game.close()
