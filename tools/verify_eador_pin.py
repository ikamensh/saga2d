"""Render Pin targeting/status/cooldown and an earned hero's Watch Bell with native input."""

import argparse
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Button

from eador.app import create_game
from eador.model import State
from eador.scene import BattleScene, ShardScene, TitleScene
from tools.eador_campaign import finish_battle, march_to, provision_army, rest


def verify(output):
    from pyglet.window import key, mouse

    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='shardbound-pin-') as directory:
        game = create_game('Shardbound Pin', resolution=(1280, 800), visible=False,
                    save_dir=Path(directory) / 'saves')
        window = game.backend.window

        def press(symbol):
            window.dispatch_event('on_key_press', symbol, 0)
            window.dispatch_event('on_key_release', symbol, 0)
            game.tick(1 / 60)

        def click(x, y):
            scale = min(window.width / game.width, window.height / game.height)
            px = (window.width - game.width * scale) / 2 + x * scale
            py = (window.height - game.height * scale) / 2 + (game.height - y) * scale
            window.dispatch_event('on_mouse_press', round(px), round(py), mouse.LEFT, 0)
            window.dispatch_event('on_mouse_release', round(px), round(py), mouse.LEFT, 0)
            game.tick(1 / 60)

        def capture(name):
            for _ in range(110):
                game.tick(1 / 60)
            game.backend.capture_frame().save(output / f'{name}.png')

        try:
            game.push(TitleScene())
            press(key.ENTER)
            press(key.X)
            assert isinstance(game.scene, BattleScene)
            battle = game.scene.battle
            archer = next(unit for unit in battle.units if unit.team == 'player' and unit.can_pin)
            click(*game.scene.grid.center(archer.pos))
            click(*game.scene.grid.center((-1, 0)))
            before = game.scene.root.state.to_json()
            press(key.P)
            press(key.ESCAPE)
            assert game.scene.root.state.to_json() == before
            press(key.P)
            target = battle.pin_targets(archer.id)[0]
            for _ in range(len(battle.units)):
                if game.scene.cursor == target.pos:
                    break
                press(key.F)
            assert game.scene.cursor == target.pos
            capture('pin-forecast')
            expected, hp = battle.pin_preview(archer.id, target.id), (target.hp, archer.hp)
            press(key.ENTER)
            assert (hp[0] - target.hp, hp[1] - archer.hp) == expected
            assert target.pinned and archer.pin_cooldown == 2
            capture('pinned-target')
            press(key.F5)
            saved = game.scene.root.state.to_json()
            press(key.E)
            press(key.F9)
            assert game.scene.root.state.to_json() == saved
            press(key.E)
            archer = game.scene.battle.unit(archer.id)
            click(*game.scene.grid.center(archer.pos))
            button = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text.startswith('Pin'))
            assert not button.enabled
            capture('pin-cooldown')
            press(key.G)
            assert archer.stance == 'guard'
            press(key.T)
            assert isinstance(game.scene, ShardScene)

            # Earn the Bell through public campaign commands, then show its real hero order.
            state = State.new(7)
            state.build('barracks')
            state.recruit('swordsman')
            state.explore()
            finish_battle(state)
            rest(state)
            provision_army(state)
            watch = next(p.pos for p in state.provinces.values() if p.site_kind == 'border_watch')
            march_to(state, watch)
            rest(state)
            provision_army(state)
            march_to(state, watch)
            if not state.actions_left:
                rest(state)
                march_to(state, watch)
            state.explore()
            finish_battle(state)
            assert 'watch_bell' in state.inventory
            state.equip('watch_bell')
            if not state.actions_left:
                rest(state)
            destination = next(pos for pos in state.grid.neighbors(state.hero.pos)
                               if state.provinces[pos].owner == 'neutral')
            state.travel(destination)
            assert state.battle and state.battle.unit(0).can_brace
            game.clear_and_push(ShardScene(State.from_json(state.to_json())))
            game.tick(1 / 60)
            button = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Brace')
            assert button.enabled
            x, y, w, h = button.bounds
            click(x + w / 2, y + h / 2)
            assert game.scene.battle.unit(0).stance == 'brace'
            capture('watch-bell-hero')
        finally:
            game._teardown()
            game.backend.quit()
    print(f'Native Pin forecast/status/cooldown/reload and earned Watch Bell hero passed: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('/tmp/shardbound-pin'))
    verify(parser.parse_args().out)
