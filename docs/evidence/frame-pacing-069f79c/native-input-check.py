from pathlib import Path
import hashlib
import json
import os
import subprocess
import sys
import time

root = Path.cwd()
sys.path.insert(0, str(root))
os.environ['SAGA2D_SILENT'] = '1'
from eador.app import create_game
from eador.scene import TitleScene, BattleScene
from tools.eador_ui import PlayerInput

output = Path('/tmp/shardbound-input-paced-069f79c-awake')
output.mkdir(exist_ok=False)
game = create_game('Native input pacing', visible=False, save_dir=output / 'saves')
try:
    game.push(TitleScene())
    game.tick(1 / 60)
    player = PlayerInput(game, native=True, output=output)
    player.button('Enter single shard')
    player.press('x')
    assert isinstance(game.scene, BattleScene)
    player.press('g')
    before = player.state.to_json()
    player.reload(before)
    cpu, start = time.process_time(), time.monotonic()
    player.capture('battle')
    elapsed = time.monotonic() - start
    cpu_percent = (time.process_time() - cpu) / elapsed * 100
    assert elapsed >= 109 / 30 - .03, elapsed
    assert player.state.to_json() == before
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                  source_sha256={str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
                                 for package in ('saga2d','eador','tools') for path in (root / package).rglob('*.py')},
                  native_events=player.events, exact_reloads=player.reloads,
                  settling_ticks=110, explicit_dt=1/60, settling_seconds=elapsed,
                  cpu_percent=cpu_percent, state_unchanged=True)
finally:
    game._teardown()
    game.backend.quit()
report['window_closed'] = game.backend.window is None
(output / 'report.json').write_text(json.dumps(report, indent=2) + '\n')
print({key:value for key,value in report.items() if key != 'source_sha256'})
