"""Directed shard UI checks: unchanged reading, bounded public orders and native captures.

Historical preparation may include autoplay; this is not independent human play.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Label
from eador.app import create_game
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import BattleScene, ShardScene
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput
from tools.verify_eador_shard_reading import check_shard, prepared_shards


class PacedInput(PlayerInput):
    def __init__(self, game, budget, **options):
        super().__init__(game, finish_actions=False, **options)
        self.budget = budget

    def _tick(self):
        super()._tick()  # PlayerInput also caps native rendering at 30 FPS.
        self.budget.checkpoint()

    def pointer(self, x, y):
        self.events.append((type(self.game.scene).__name__, 'hover', (round(x), round(y))))
        if self.native:
            window = self.game.backend.window
            scale = min(window.width / self.game.width, window.height / self.game.height)
            px = (window.width - self.game.width * scale) / 2 + x * scale
            py = (window.height - self.game.height * scale) / 2 + (self.game.height - y) * scale
            window.dispatch_event('on_mouse_motion', round(px), round(py), 0, 0)
        else:
            self.game.backend.inject_mouse_move(round(x), round(y))
        self._tick()


def longest_contract(budget):
    """Use the reading test's paid departures and public offers, without replaying battles."""
    path = ROOT / 'docs/evidence/shardbound-army-plans-cd351a9/control.json.gz'
    with gzip.open(path, 'rt') as source:
        history = json.load(source)
    arrivals = []
    for index, entry in enumerate(history['commands']):
        if entry['command'] == 'advance':
            for offer in State.from_json(entry['before']).campaign.offers:
                state = State.from_json(entry['before'])
                state.advance(offer.id, **entry['kwargs'])
                arrivals.append((state, index, offer.id))
                budget.checkpoint()
    state, index, offer = max(arrivals, key=lambda item: len(item[0].campaign.objective))
    return state.to_json(), dict(history=str(path.relative_to(ROOT)), command_index=index, offer=offer,
                                 sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                 historical_preparation_includes_autoplay=True)


def verify(output, *, backend='pyglet', budget=None):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Choose an empty output directory to preserve earlier receipts')
    output.mkdir(parents=True, exist_ok=True)
    budget = CpuBudget(25) if budget is None else budget
    started, cpu_started = time.monotonic(), time.process_time()
    paths = (ROOT / 'eador/scene.py', ROOT / 'eador/art.py', ROOT / 'eador/ui.py',
             Path(__file__).resolve(), ROOT / 'tools/verify_eador_shard_reading.py')
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
    report = dict(backend=backend, cpu_percent_requested=budget.percent,
                  source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, cases=[], captures=[], command_checks=[])
    # Existing cached preparation is atomic and has no budget argument. Finish
    # it and yield before opening a window; do not replay it for each UI case.
    prepared = dict(prepared_shards())
    budget.checkpoint()
    longest, origin = longest_contract(budget)
    report['historical_contract'] = origin
    cases = [('solo-opening', State.new(7).to_json(), 100),
             ('linked-opening', State.new_campaign(7, 'Wizard').to_json(), 125),
             ('ruins-opening', State.new(7, theme='ruins').to_json(), 125),
             ('no-actions', prepared['paid-no-actions'], 125),
             ('paid-full-army', prepared['paid-full-army'], 125),
             ('saved-encircled', prepared['saved-encircled'], 125),
             ('longest-contract', longest, 125)]
    with TemporaryDirectory(prefix='shardbound-shard-look-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PacedInput(game, budget, native=backend == 'pyglet', output=output)

        def clear_pointer():
            player.pointer(10, 100)
            assert player.root.hover is None and player.root._hover_name is None

        def capture(name):
            player.capture(name, settle=False)
            assert player.state.to_json() == snapshot
            report['captures'].append(dict(name=name, case=case['name'], percent=reading_scale(game),
                                           selected=list(player.root.selected), png=player.native))

        def hover(pos):
            selected = player.root.selected
            player.pointer(*player.root.grid.center(pos))
            root = player.root
            assert root.hover == pos and root.selected == selected
            box = root._hover_name
            assert box is not None
            labels = box.find_all(lambda item: isinstance(item, Label) and item.visible)
            assert len(labels) == 1 and labels[0].text == root.state.provinces[pos].name
            x, y, width, height = box.bounds
            assert 26 <= x < x + width <= root.edge - 26
            assert root._summary_bottom <= y < y + height <= game.height - 158
            lx, ly, lw, lh = labels[0].bounds
            assert x <= lx < lx + lw <= x + width and y <= ly < ly + lh <= y + height
            assert player.state.to_json() == snapshot

        try:
            game.set_window_size((1280, 720))
            for name, snapshot, percent in cases:
                game.clear_and_push(ShardScene(State.from_json(snapshot)))
                player._tick()
                for key in ('f2', 'left' if percent == 100 else 'right', 'return'):
                    player.press(key)
                assert reading_scale(game) == percent and game.window_size == (1280, 720)
                case = dict(name=name, percent=percent, window=list(game.window_size),
                            selected_count=0, hover_count=0)
                clear_pointer()
                check_shard(player.root)
                capture(f'{name}-{percent}-home')
                for pos in player.state.provinces:
                    player.click(*player.root.grid.center(pos))
                    assert player.root.selected == pos
                    clear_pointer()  # Exclude transient hover overlays from static HUD overlap checks.
                    check_shard(player.root)
                    assert player.state.to_json() == snapshot
                    case['selected_count'] += 1
                    hover(pos)
                    case['hover_count'] += 1
                clear_pointer()
                player.press('home')
                if name == 'linked-opening':
                    destination = max((pos for pos in player.state.provinces
                                       if not player.state.provinces[pos].capital),
                                      key=lambda pos: len(player.state.provinces[pos].name))
                    hover(destination)
                    capture('linked-opening-125-hover')
                    clear_pointer()
                    player.click(*player.root.grid.center((-1, 0)))
                    clear_pointer()
                    check_shard(player.root)
                    capture('linked-opening-125-neighbor')
                    for direction, destination in (('north', (-1, -1)), ('south', (-2, 1))):
                        player.click(*player.root.grid.center(destination))
                        clear_pointer()
                        check_shard(player.root)
                        capture(f'linked-opening-125-{direction}')
                assert player.state.to_json() == snapshot
                case.update(state_unchanged=True, state_sha256=hashlib.sha256(snapshot.encode()).hexdigest())
                report['cases'].append(case)
                if name == 'solo-opening':
                    expected = State.from_json(snapshot)
                    for action, args, control in (
                            ('explore', (), 'Explore current province'), ('retreat', (), 't'),
                            ('end_turn', (), 'End turn'), ('travel', ((-1, 0),), 'Invade province')):
                        getattr(expected, action)(*args)
                        if action == 'travel':
                            player.click(*player.root.grid.center(args[0]))
                        player.press(control) if action == 'retreat' else player.button(control)
                        assert player.state.to_json() == expected.to_json(), action
                        assert isinstance(game.scene, BattleScene if action in ('explore', 'travel') else ShardScene)
                        report['command_checks'].append(dict(action=action, exact=True))
            report['input_activations'] = len(player.events)
        finally:
            game.close()
            assert not game.scenes and not game.running
            assert (game.backend.window is None) if backend == 'pyglet' else (not game.backend.is_running)
            report['game_closed'] = True
    report['source_unchanged'] = all(hashlib.sha256(path.read_bytes()).hexdigest() ==
                                    hashes[str(path.relative_to(ROOT))] for path in paths)
    assert report['source_unchanged'], 'Verified UI source changed during the run'
    budget.checkpoint()
    report.update(wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"Shard look passed ({backend}): {len(report['cases'])} cases, "
          f"{sum(case['selected_count'] for case in report['cases'])} selections, "
          f"{len(report['command_checks'])} exact orders, {len(report['captures'])} captures", flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-shard-look'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    verify(args.output, backend=args.backend, budget=CpuBudget(args.cpu_percent))
