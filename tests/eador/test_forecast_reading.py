"""Reading an immediate tactical consequence must preserve the queued command."""
from saga2d import Label
from eador.app import create_game
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import BattleScene, ShardScene
from eador.settings_scene import SettingsScene
from tools.eador_ui import PlayerInput


def test_larger_tactical_forecast_preserves_aim_and_matches_the_real_spell(tmp_path):
    """Read/cancel/apply, then spend the same aimed order with its exact shown result."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(State.new(7, 'Wizard')))
        player = PlayerInput(game)
        player.click(*game.scene.grid.center((-1, 0))); player.press('return')
        scene = game.scene
        assert isinstance(scene, BattleScene)
        assert any('Arrows aim' in c.text for c in scene.ui.walk() if isinstance(c, Label))
        player.click(*scene.grid.center((-2, -1))); player.press('e')
        player.press('1'); player.press('f')
        target = next(u for u in scene.action_targets() if u.pos == scene.cursor)
        amount = scene.battle.spell_preview('bolt', target.id)
        before = player.state.to_json()
        aim = (scene.selected, scene.cursor, scene.hover, scene.targeting)
        player.press('f2')
        assert isinstance(game.scene, SettingsScene)
        player.press('right'); player.press('escape')
        assert game.scene is scene and reading_scale(game) == 100
        assert (scene.selected, scene.cursor, scene.hover, scene.targeting) == aim
        player.press('f2'); player.press('right'); player.press('return')
        assert reading_scale(game) == 125 and player.state.to_json() == before
        assert (scene.selected, scene.cursor, scene.hover, scene.targeting) == aim
        forecast = scene.ui.find(lambda c: isinstance(c, Label) and c.text == f'Deal {amount} HP damage')
        assert forecast is not None
        hp, mana = target.hp, scene.battle.mana
        cost = scene.battle.spell_cost('bolt')
        player.press('return')
        assert target.hp == hp - amount and scene.battle.mana == mana - cost
        assert scene.battle.unit(0).acted
    finally:
        game._teardown()


def test_pointer_forecast_changes_without_spending_an_order(tmp_path):
    """Moving the pointer must refresh the visible forecast before a command is clicked."""
    game = create_game(backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(ShardScene(State.new(7)))
        player = PlayerInput(game)
        player.click(*game.scene.grid.center((-1, 0))); player.press('return')
        scene, before = game.scene, player.state.to_json()
        targets = [u for u in scene.battle.units if u.team == 'enemy']
        for target in targets:
            x, y = scene.grid.center(target.pos)
            game.backend.inject_mouse_move(round(x), round(y)); game.tick(1 / 60)
            expected = f'{target.name}  ·  {target.hp}/{target.max_hp} HP'
            assert any(c.text == expected for c in scene.ui.walk() if isinstance(c, Label))
            assert player.state.to_json() == before
    finally:
        game._teardown()
