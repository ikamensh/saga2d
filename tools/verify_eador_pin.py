"""Render Pin targeting/status/cooldown and an earned hero's Watch Bell with native input."""

import argparse
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d.testing.native_frames import tick
from saga2d import Button

from eador.app import create_game
from eador.model import State
from eador.scene import BattleScene, ShardScene, TitleScene
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_campaign import finish_battle, march_to, provision_army, rest
from tools.eador_ui import PlayerInput


def prepare_watch_bell(*, budget=None):
    """Earn the Bell through paid campaign orders, then enter a battle where the hero can Brace."""
    budget = CpuBudget(25) if budget is None else budget
    state = State.new(7)
    state.build('barracks')
    state.recruit('swordsman')
    state.explore()
    finish_battle(state, budget=budget)
    rest(state, budget=budget)
    provision_army(state)
    watch = next(p.pos for p in state.provinces.values() if p.site_kind == 'border_watch')
    march_to(state, watch, budget=budget)
    rest(state, budget=budget)
    provision_army(state)
    march_to(state, watch, budget=budget)
    if not state.actions_left:
        rest(state, budget=budget)
        march_to(state, watch, budget=budget)
    state.explore()
    finish_battle(state, budget=budget)
    assert 'watch_bell' in state.inventory
    state.equip('watch_bell')
    if not state.actions_left:
        rest(state, budget=budget)
    destination = next(pos for pos in state.grid.neighbors(state.hero.pos)
                       if state.provinces[pos].owner == 'neutral')
    state.travel(destination)
    assert state.battle and state.battle.unit(0).can_brace
    return state


def verify(output, *, budget=None):
    from pyglet.window import key, mouse

    budget = CpuBudget(25) if budget is None else budget
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='shardbound-pin-') as directory:
        game = create_game('Shardbound Pin', resolution=(1280, 800), visible=False,
                    save_dir=Path(directory) / 'saves')
        window = game.backend.window
        player = PlayerInput(game, native=True)

        def press(symbol):
            window.dispatch_event('on_key_press', symbol, 0)
            window.dispatch_event('on_key_release', symbol, 0)
            tick(game)
            player.finish_playback()

        def click(x, y):
            scale = min(window.width / game.width, window.height / game.height)
            px = (window.width - game.width * scale) / 2 + x * scale
            py = (window.height - game.height * scale) / 2 + (game.height - y) * scale
            window.dispatch_event('on_mouse_press', round(px), round(py), mouse.LEFT, 0)
            window.dispatch_event('on_mouse_release', round(px), round(py), mouse.LEFT, 0)
            tick(game)
            player.finish_playback()

        def capture(name):
            for _ in range(110):
                tick(game)
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
            state = prepare_watch_bell(budget=budget)
            game.clear_and_push(ShardScene(State.from_json(state.to_json())))
            tick(game)
            button = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Brace')
            assert button.enabled
            x, y, w, h = button.bounds
            click(x + w / 2, y + h / 2)
            assert game.scene.battle.unit(0).stance == 'brace'
            capture('watch-bell-hero')
        finally:
            game._teardown()
            game.backend.quit()
    print(f'Native Pin forecast/status/cooldown/reload and earned Watch Bell hero passed '
          f'(model CPU allowance {budget.percent}%): {output}')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('/tmp/shardbound-pin'))
    parser.add_argument('--cpu-percent', type=float, default=25,
                        help='Model preparation CPU allowance as a percent of one core (default 25; 100 for explicit stress)')
    args = parser.parse_args(argv)
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    verify(args.out, budget=budget)


if __name__ == '__main__':
    main()
