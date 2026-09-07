"""Two native reading checks from exact earned seed5 saves; no preparation or autoplay."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d import Button, Label
from eador.app import create_game
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import ResultScene, ShardScene
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout

JOURNAL = ROOT / 'docs/evidence/adventure-variety/route-seed5.json.gz'
DIGEST = 'cdccd3ef5ae9750098d371b6c31de7c97196aaa4091c2b7f56bebe564ccda846'


def fingerprints():
    paths = {Path(__file__), JOURNAL, ROOT / 'tools/eador_ui.py', ROOT / 'tools/cpu_budget.py',
             ROOT / 'tools/verify_eador_guidance.py', *(ROOT / 'eador').glob('*.py'),
             *(ROOT / 'saga2d').rglob('*.py')}
    paths.update(path for path in (ROOT / 'eador/assets').rglob('*') if path.is_file())
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def verify(output):
    output.mkdir(parents=True, exist_ok=True)
    started, cpu_started = time.monotonic(), time.process_time()
    budget = CpuBudget(25)
    data = JOURNAL.read_bytes()
    assert hashlib.sha256(data).hexdigest() == DIGEST
    journal = json.loads(gzip.decompress(data))
    commands = journal['commands']
    report = {'scope': __doc__, 'backend': 'pyglet', 'cpu_percent': 25, 'native_fps': 30,
              'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'source_sha256': fingerprints(), 'journal': str(JOURNAL.relative_to(ROOT)),
              'journal_sha256': DIGEST, 'original_execution_source': journal['execution_source'],
              'checkpoints': ['commands[102].before', 'commands[12].after'],
              'captures': [], 'cases': []}
    wake = subprocess.Popen(['caffeinate', '-du', '-t', '90'])
    try:
        with TemporaryDirectory(prefix='shardbound-escape-hint-') as directory:
            for name, saved in (('ready-after-swap-125', commands[102]['before']),
                                ('one-foe-125', commands[12]['after'])):
                game = create_game(backend='pyglet', visible=False, save_dir=Path(directory) / name)
                player = PlayerInput(game, native=True, output=output)
                try:
                    game.push(ShardScene(State.from_json(saved)))
                    for key in ('f2', 'right', 'return'):
                        player.press(key)
                        budget.checkpoint()
                    assert reading_scale(game) == 125 and player.state.to_json() == saved
                    if name.startswith('ready'):
                        step = commands[102]
                        player.order(step['command'], *step['args'], **step['kwargs'])
                        assert player.state.to_json() == step['after']
                        saved = step['after']
                        scene = game.scene
                        assert scene.selected == 4 and scene.battle.unit(4).acted
                        assert not scene.battle.unit(0).acted and scene.battle.evacuation_blocked_reason is None
                        control = scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Swap ally')
                        assert not control.enabled and 'unspent unit action' in control.tooltip
                        control = scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Evacuate')
                        assert control.enabled
                        assert scene.order_guidance == 'Ready: V evacuates your hero and surviving army.'
                    else:
                        assert '5 allies · 1 foe · Tab selects' in [item.text for item in game.scene.ui.walk()
                                                                  if isinstance(item, Label)]
                    # Settle the actual Swap effect using the same paced native frame driver.
                    for _ in range(70):
                        player._tick()
                        budget.checkpoint()
                    check_reading_layout(game.scene)
                    player.capture(name, settle=False)
                    assert player.state.to_json() == saved
                    report['captures'].append({'file': name + '.png', 'reading_size': reading_scale(game),
                                                'window_size': game.window_size, 'state': json.loads(saved)})
                    player.reload(saved)
                    if name.startswith('ready'):
                        player.press('v')
                        assert isinstance(game.scene, ResultScene)
                        assert player.state.to_json() == commands[103]['after']
                    budget.checkpoint()
                    report['cases'].append({'name': name, 'inputs': player.events, 'exact_reloads': player.reloads,
                                            'final_state': json.loads(player.state.to_json())})
                finally:
                    game.close()
                budget.checkpoint()
    finally:
        wake.terminate()
        wake.wait()
    assert fingerprints() == report['source_sha256'], 'Source or assets changed during capture'
    report.update(source_unchanged=True, wall_seconds=time.monotonic() - started,
                  cpu_seconds=time.process_time() - cpu_started)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    result = verify(Path(sys.argv[1]))
    print(f'{len(result["captures"])} native captures; '
          f'{sum(len(case["inputs"]) for case in result["cases"])} inputs; '
          f'{sum(case["exact_reloads"] for case in result["cases"])} exact reloads; '
          f'{result["wall_seconds"]:.3f}s wall / {result["cpu_seconds"]:.3f}s CPU', flush=True)
