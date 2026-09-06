"""Render new role art and browse paid/current/legacy control references natively."""
import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from tools.verify_eador_role_art import TroopSheet
from eador.app import create_game
from eador.codex import CodexScene
from eador.model import State
from eador.scene import ShardScene
from tools.eador_ui import PlayerInput


class ControlSheet(TroopSheet):
    kinds = [('militia', 'Militia'), ('sapper', 'Sapper'), ('Wizard', 'Wizard'),
             ('adept', 'Rune Adept'), ('ranger', 'Ranger'), ('skyrider', 'Skyrider')]


def verify(output):
    from tools.eador_control_campaign import prepare_control_watch

    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='roster-art-') as directory:
        game = create_game(visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=True, output=output)
        try:
            game.push(ControlSheet())
            player.capture('control-troop-sheet')
            state = prepare_control_watch()
            root = ShardScene(state)
            game.clear_and_push(root)
            player.capture('paid-control-watch')
            before = state.to_json()
            game.push(CodexScene(root))
            game.tick(1 / 60)
            player.capture('current-militia-rally')
            player.press('end')
            player.capture('adept-skyrider-recruits')
            player.button('Previous')
            player.capture('sapper-recruit')
            player.button('Abilities')
            player.press('right'); player.press('right')
            player.capture('current-rally-smoke')
            player.button('Next')
            player.capture('current-repulse-flight')
            player.button('Next')
            player.capture('current-sight-and-extraction')
            player.press('escape')
            assert state.to_json() == before
            sapper = next(unit for unit in state.battle.units if unit.can_smoke)
            state.battle.smoke(sapper.id, sapper.pos)
            state = State.from_json(state.to_json())
            root = ShardScene(state)
            game.clear_and_push(root)
            before = state.to_json()
            game.push(CodexScene(root))
            player.press('2'); player.press('right'); player.press('right')
            player.capture('saved-used-smoke-charge')
            player.press('end')
            player.capture('saved-smoke-sight')
            player.press('escape')
            assert state.to_json() == before
            fixture = Path(__file__).resolve().parents[1] / 'tests/eador/fixtures/v10_pinned_crossing.json'
            state = State.from_json(fixture.read_text())
            root = ShardScene(state)
            game.clear_and_push(root)
            before = state.to_json()
            game.push(CodexScene(root))
            player.capture('v10-militia-no-rally')
            player.press('2'); player.press('right'); player.press('right')
            player.capture('v10-unavailable-new-orders')
            player.press('end')
            player.capture('v10-open-sight')
            player.press('escape')
            assert state.to_json() == before
            assert not list((Path(directory) / 'saves').glob('*'))
            print(f'Native role art and paid/current/legacy Codex journeys passed: {output}')
        finally:
            game._teardown()
            game.backend.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-roster-art'))
    verify(parser.parse_args().output)
