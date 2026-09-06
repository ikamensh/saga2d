"""Capture shipped presentation through paced native input, including larger reading size.

    python tools/verify_eador_presentation.py --output /tmp/shardbound-presentation

No simulation policy, campaign completion or audio listening is claimed. This
short visual journey opens three worlds, saves/loads, and enters a real battle.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game
from eador.preferences import reading_scale
from eador.scene import BattleScene, ShardScene, TitleScene
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    budget = CpuBudget()
    report = {'scope': 'Native visual input and exact saves; silent audio, no listening approval.',
              'frames': [], 'source_sha256': {}}
    for path in sorted((ROOT / 'eador').glob('*.py')):
        report['source_sha256'][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    with TemporaryDirectory(prefix='shardbound-presentation-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)

        def capture(name):
            before = player.root.state.to_json() if any(isinstance(s, ShardScene) for s in game.scenes) else None
            cpu = time.process_time()
            for _ in range(6):
                player._tick()
                budget.checkpoint()
            render_cpu = time.process_time() - cpu
            player.capture(name, settle=False)
            if before is not None:
                assert player.root.state.to_json() == before, 'Static presentation changed campaign rules.'
            report['frames'].append({'name': name, 'scene': type(game.scene).__name__,
                                     'reading_size': reading_scale(game),
                                     'six_frames_cpu_seconds': round(render_cpu, 6)})

        try:
            for index, theme in enumerate(('frontier', 'elderwild', 'ruins')):
                game.clear_and_push(TitleScene(seed=7, hero_class='Wizard'))
                for _ in range(index):
                    player.press('right')
                capture('title-' + theme)
                player.press('return')
                assert player.root.state.theme == theme
                capture('campaign-' + theme)
                player.reload(player.root.state.to_json())
            game.clear_and_push(TitleScene(seed=7, hero_class='Wizard'))
            player.press('t')
            player.press('right')
            player.press('return')
            assert reading_scale(game) == 125
            capture('title-reading-125')
            player.press('return')
            capture('campaign-reading-125')
            player.order('explore')
            assert isinstance(game.scene, BattleScene)
            capture('battle-reading-125')
            player.reload(player.root.state.to_json())
            report['native_inputs'] = len(player.events)
            report['exact_reloads'] = player.reloads
            report['final_sha256'] = hashlib.sha256(player.root.state.to_json().encode()).hexdigest()
        finally:
            game.close()
    (output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-presentation'))
    args = parser.parse_args()
    report = verify(args.output)
    print(f'{len(report["frames"])} frames; {report["native_inputs"]} native inputs; '
          f'{report["exact_reloads"]} exact save/reloads: {args.output}')
