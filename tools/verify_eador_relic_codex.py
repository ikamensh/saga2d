"""Inspect relic order guidance in a real earned battle and an older active save."""
import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game
from eador.codex import CodexScene
from eador.model import State
from eador.scene import ShardScene
from tools.eador_relic_campaign import prepare_censer_watch
from tools.eador_ui import PlayerInput


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='relic-codex-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            state = prepare_censer_watch()
            root = ShardScene(state)
            game.push(root)
            game.tick(1 / 60)
            player.click(*game.scene.grid.center(state.battle.unit(0).pos))
            player.button('Smoke · 1')
            player.click(*game.scene.grid.center(state.battle.unit(0).pos))
            assert state.battle.unit(0).spent_abilities == ('smoke',)
            player.reload(state.to_json())
            old = Path(__file__).resolve().parents[1] / 'tests/eador/fixtures/v10_pinned_crossing.json'
            for label, state in (('earned-censer', player.root.state), ('v10', State.from_json(old.read_text()))):
                root = ShardScene(state)
                game.clear_and_push(root)
                before = state.to_json()
                files = {p.name: p.read_bytes() for p in saves.iterdir()}
                game.push(CodexScene(root))
                player.press('2')
                for page in range(game.scene.pages):
                    player.capture(f'{label}-abilities-{page + 1}')
                    if page + 1 < game.scene.pages:
                        player.button('Next')
                player.button('Relics')
                for page in range(game.scene.pages):
                    player.capture(f'{label}-relics-{page + 1}')
                    if page + 1 < game.scene.pages:
                        player.press('right')
                player.button('Close codex')
                assert state.to_json() == before
                assert files == {p.name: p.read_bytes() for p in saves.iterdir()}
            print(f'Earned/reloaded hero Smoke and legacy relic Codex input passed ({backend}): {output}')
        finally:
            game._teardown()
            if backend == 'pyglet':
                game.backend.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-relic-codex'))
    verify(parser.parse_args().output)
