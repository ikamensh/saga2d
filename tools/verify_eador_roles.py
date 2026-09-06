"""Recruit, command and save a Ranger/Warden/Acolyte hold through real player controls."""
import argparse
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game
from eador.scene import BattleScene, ChoiceScene, ResultScene, TitleScene
from tools.eador_roles_campaign import prepare_support_watch
from tools.eador_ui import PlayerInput


def verify(output, *, backend='pyglet'):
    with TemporaryDirectory(prefix='shardbound-roles-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)

        def select(ident):
            player.click(*game.scene.grid.center(player.state.battle.unit(ident).pos))
            assert game.scene.selected == ident

        def move(ident, destination):
            select(ident)
            player.click(*game.scene.grid.center(destination))
            assert player.state.battle.unit(ident).pos == destination

        def attack(ident, target):
            select(ident)
            battle = player.state.battle
            before = battle.unit(target).hp, battle.unit(ident).hp
            expected = battle.preview(ident, target)
            player.click(*game.scene.grid.center(battle.unit(target).pos))
            assert (before[0] - battle.unit(target).hp, before[1] - battle.unit(ident).hp) == expected

        def guard_army():
            for unit in player.state.battle.units:
                if unit.team == 'player' and unit.alive and not unit.acted:
                    select(unit.id)
                    player.press('g')

        def aim_at(ident):
            for _ in player.state.battle.units:
                player.press('f')
                if game.scene.cursor == player.state.battle.unit(ident).pos:
                    return
            raise AssertionError('The legal target could not be reached by keyboard targeting')

        try:
            game.push(TitleScene(7))
            for key in ('o', 'd', 'down', 'down', 'right', 'return'):
                player.press(key)
            player.press('return')
            player.press('r')
            player.press('right')
            player.capture('recruitment-second-page')
            player.press('escape')
            prepare_support_watch(player.state)
            assert player.state.turn == 8 and isinstance(game.scene, BattleScene)
            for uid, destination in ((1, (1, 0)), (3, (0, -1)), (2, (0, 0)), (6, (0, 1)),
                                     (4, (-1, 1)), (5, (-1, 0)), (0, (-1, -1))):
                move(uid, destination)
            pike = next(u.id for u in player.state.battle.units if u.team == 'enemy' and u.kind == 'pikeman')
            for ident in (1, 3, 6):
                attack(ident, pike)
            guard_army()
            player.press('e')
            player.reload(player.state.to_json())
            attack(6, pike)
            assert player.state.battle.unit(6).acted and not player.state.battle.unit(6).moved
            player.capture('ranger-shot-can-move')
            player.reload(player.state.to_json())
            for uid, destination in ((1, (1, -1)), (6, (1, 0)), (4, (0, 1)), (5, (-1, 1)), (0, (-1, 0))):
                move(uid, destination)
            guard_army()
            player.press('e')
            assert player.state.battle.objective.progress == 1
            player.reload(player.state.to_json())
            select(4)
            player.press('s')
            aim_at(2)
            player.capture('warden-swap-target')
            player.click(*game.scene.grid.center(player.state.battle.unit(2).pos))
            assert player.state.battle.unit(4).pos == player.state.battle.objective.target
            assert player.state.battle.unit(2).moved and not player.state.battle.unit(2).acted
            player.reload(player.state.to_json())
            select(5)
            battle = player.state.battle
            restored = battle.spell_preview('heal', 2, caster_id=5)
            before, mana = battle.unit(2).hp, battle.mana
            player.press('2')
            aim_at(2)
            player.capture('acolyte-heal-forecast')
            player.click(*game.scene.grid.center(battle.unit(2).pos))
            assert battle.unit(2).hp - before == restored and battle.mana == mana - battle.spell_cost('heal')
            assert battle.unit(5).acted and not battle.unit(0).acted
            player.capture('heal-static-feedback', settle=False)
            player.reload(player.state.to_json())
            guard_army()
            player.press('e')
            assert isinstance(game.scene, ResultScene) and player.state.battle.outcome_reason == 'hold'
            assert all(u.alive for u in player.state.battle.units if u.team == 'player')
            assert any(u.alive for u in player.state.battle.units if u.team == 'enemy')
            player.capture('support-hold-victory')
            player.reload(player.state.to_json())
            player.press('e')
            while isinstance(game.scene, ChoiceScene):
                player.press('1')
            assert player.state.provinces[(0, -2)].explored
            print(f'Paid support opening and manual hold passed: {len(player.events)} inputs, {player.reloads} exact reloads ({backend})')
        finally:
            game._teardown()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-roles'))
    verify(parser.parse_args().output)
