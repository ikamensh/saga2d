"""Inspect extraction Codex pages through native input on paid, saved adventures."""
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
from tools.eador_extraction_campaign import AdventureOrders, crossing_route, prepare_adventure, prepared_crossing
from tools.eador_ui import PlayerInput


def verify(output):
    output.mkdir(parents=True, exist_ok=True)
    guided = prepared_crossing()
    guided.explore(approach='guided')
    cache = prepare_adventure(theme='elderwild')
    cache.explore(approach='full')
    cache.battle.guard(0)
    checkpoints = {}

    class RecordOrders(AdventureOrders):
        def do(self, command, *args, **kwargs):
            if command == 'evacuate':
                checkpoints['ready'] = self.state.to_json()
            super().do(command, *args, **kwargs)
            if self.battle.unit(0).pinned and self.battle.outcome is None:
                checkpoints.setdefault('pinned', self.state.to_json())

    crossing_route(prepared_crossing(), 'direct', orders_type=RecordOrders)
    cases = [('guided', guided.to_json()), ('full-cache', cache.to_json()), *checkpoints.items(),
             ('ordinary', State.new(7).to_json())]
    with TemporaryDirectory(prefix='extraction-codex-') as directory:
        game = create_game(visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=True, output=output)
        try:
            for label, saved in cases:
                state = State.from_json(saved)
                root = ShardScene(state)
                game.clear_and_push(root)
                game.push(CodexScene(root))
                game.tick(1 / 60)
                player.press('2')
                player.press('end')
                assert game.scene.category == 1 and game.scene.page == 2
                player.capture(label + '-escape-orders')
                if label in ('guided', 'full-cache'):
                    player.button('Sites')
                    player.press('end')
                    if label == 'guided':
                        player.button('Previous')
                    assert game.scene.category == 4
                    player.capture(label + '-approaches')
                if label == 'ready':
                    assert state.battle.evacuation_blocked_reason is None
                player.press('escape')
                assert state.to_json() == saved
            assert not list((Path(directory) / 'saves').glob('*'))
            print(f'Native paid/reloaded extraction Codex journeys passed: {output}')
        finally:
            game._teardown()
            game.backend.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-extraction-codex'))
    verify(parser.parse_args().output)
