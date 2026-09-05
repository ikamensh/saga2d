"""A player can aim Pin, inspect its result and resume the cooldown through real input."""

from saga2d import Button

from eador.app import create_game
from eador.scene import BattleScene, ShardScene, TitleScene


def press(game, key):
    game.backend.inject_key(key)
    game.backend.inject_key(key, type='key_release')
    game.tick(1 / 60)


def click_hex(game, pos):
    x, y = game.scene.grid.center(pos)
    game.backend.inject_click(round(x), round(y))
    game.backend.inject_release(round(x), round(y))
    game.tick(1 / 60)


def test_pin_targeting_save_and_cooldown_are_playable_without_private_commands(tmp_path):
    """Movement and a keyboard-aimed shot produce the forecast; saved cooldown gates the button."""
    game = create_game('Pin input', backend='mock', save_dir=tmp_path / 'saves')
    try:
        game.push(TitleScene())
        press(game, 'return')
        press(game, 'x')
        assert isinstance(game.scene, BattleScene)
        battle = game.scene.battle
        archer = next(unit for unit in battle.units if unit.team == 'player' and unit.can_pin)
        click_hex(game, archer.pos)
        click_hex(game, (-1, 0))
        before = game.scene.root.state.to_json()
        press(game, 'p')
        press(game, 'escape')
        assert isinstance(game.scene, BattleScene) and game.scene.root.state.to_json() == before
        press(game, 'p')
        target = battle.pin_targets(archer.id)[0]
        for _ in range(len(battle.units)):
            press(game, 'f')
            if game.scene.cursor == target.pos:
                break
        expected = battle.pin_preview(archer.id, target.id)
        hp = target.hp, archer.hp
        press(game, 'return')
        assert (hp[0] - target.hp, hp[1] - archer.hp) == expected
        assert target.pinned and archer.pin_cooldown == 2
        press(game, 'f5')
        saved = game.scene.root.state.to_json()
        press(game, 'e')
        press(game, 'f9')
        assert game.scene.root.state.to_json() == saved
        # One following turn cannot use Pin, but an ordinary defensive order remains usable.
        press(game, 'e')
        battle = game.scene.battle
        archer = battle.unit(archer.id)
        click_hex(game, archer.pos)
        control = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text.startswith('Pin'))
        assert control is not None and not control.enabled
        before = game.scene.root.state.to_json()
        press(game, 'p')
        assert game.scene.root.state.to_json() == before
        press(game, 'g')
        assert archer.stance == 'guard'
        press(game, 't')
        assert isinstance(game.scene, ShardScene)
    finally:
        game._teardown()
