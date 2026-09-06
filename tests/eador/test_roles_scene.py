"""The new tactical roles are discoverable, executable and saveable through player controls."""
from tools.verify_eador_roles import verify
import pytest


def test_paid_support_opening_and_manual_hold_with_visible_orders(tmp_path):
    """The native verifier recruits each role and uses its distinct order on a real Watch battle."""
    verify(tmp_path, backend='mock')


@pytest.mark.parametrize('reduce', [False, True])
def test_reduced_motion_keeps_damage_feedback_still_without_changing_combat(tmp_path, reduce):
    """The saved display preference changes floating feedback, while idle frames never change tactics."""
    from eador.app import create_game
    from eador.scene import TitleScene
    from tools.eador_ui import PlayerInput
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    player = PlayerInput(game)
    try:
        game.push(TitleScene(7, hero_class='Wizard'))
        if reduce:
            for key in ('o', 'd', 'down', 'down', 'right', 'return'):
                player.press(key)
        for key in ('return', 'x'):
            player.press(key)
        battle = player.state.battle
        destination = min(battle.reachable(0), key=lambda pos: min(
            battle.grid.distance(pos, unit.pos) for unit in battle.units if unit.team == 'enemy'))
        player.click(*game.scene.grid.center(destination))
        for key in ('1', 'f', 'return'):
            player.press(key)
        before = player.state.to_json()
        numbers = [(text['text'], text['x'], text['y']) for text in game.backend.texts
                   if text['text'].startswith(('+', '-')) and text['text'][1:].isdigit()]
        assert numbers
        game.tick(.25)
        after = [(text['text'], text['x'], text['y']) for text in game.backend.texts
                 if text['text'].startswith(('+', '-')) and text['text'][1:].isdigit()]
        assert (numbers == after) == reduce
        assert player.state.to_json() == before
    finally:
        game._teardown()
