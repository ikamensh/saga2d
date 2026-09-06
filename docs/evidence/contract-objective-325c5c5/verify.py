"""Inspect two earned contract maps and the actual retained ending; no new campaign credit."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import time

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from eador.app import create_game
from eador.campaign_scene import CampaignScene
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import ShardScene, TitleScene
from saga2d import Label
from tests.eador.test_shard_reading import earned_contract_arrivals
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput
from tools.verify_eador_campaign_reading import check_transition
from tools.verify_eador_shard_reading import check_shard


output = Path('/tmp/shardbound-contract-objective-native')
original_path = Path('/tmp/shardbound-manual-control-6648690.json.gz')
original_blob = original_path.read_bytes()
original = json.loads(gzip.decompress(original_blob))
foundries = next(row['after'] for row in original['commands'] if row['command'] == 'advance'
                 and json.loads(row['after'])['campaign']['contract'] == 'foundries')
gate = next(snapshot for snapshot in earned_contract_arrivals()
            if json.loads(snapshot)['campaign']['contract'] == 'gate')
paths = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'),
         ROOT / 'tests/eador/test_shard_reading.py', ROOT / 'tools/eador_ui.py',
         ROOT / 'tools/cpu_budget.py', ROOT / 'tools/verify_eador_campaign_reading.py',
         ROOT / 'tools/verify_eador_shard_reading.py', ROOT / 'tools/verify_eador_guidance.py']
hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
started, cpu_started = time.monotonic(), time.process_time()
budget = CpuBudget(25)
rows = []
with TemporaryDirectory(prefix='shardbound-contract-objective-') as directory:
    game = create_game(backend='pyglet', visible=False, save_dir=Path(directory) / 'saves')
    player = PlayerInput(game, native=True, output=output)
    try:
        game.set_window_size((1280, 720))
        for name, snapshot in (('foundries', foundries), ('gate', gate)):
            budget.checkpoint()
            game.clear_and_push(ShardScene(State.from_json(snapshot)))
            for key in ('f2', 'right', 'return'):
                player.press(key)
            assert reading_scale(game) == 125
            player.capture(name + '-arrival-125', settle=False)
            for pos in (player.state.hero.pos, (0, -1), (2, 0)):
                player.click(*player.root.grid.center(pos))
                labels = check_shard(player.root)
                assert player.root.selected == pos
                assert player.state.campaign.objective in [item.text for item in game.scene.ui.walk()
                                                           if isinstance(item, Label) and item.visible]
                assert player.state.to_json() == snapshot
            player.press('j'); player.press('escape')
            assert player.root.selected == (2, 0) and player.state.to_json() == snapshot
            player.capture(name + '-selected-125', settle=False)
            player.reload(snapshot)
            assert player.state.campaign.objective in [item.text for item in game.scene.ui.walk()
                                                       if isinstance(item, Label) and item.visible]
            check_shard(player.root)
            rows.append(dict(case=name, labels=labels, state_sha256=hashlib.sha256(snapshot.encode()).hexdigest(),
                             exact_state=True, selected_provinces=3, campaign_plan_return=True, f5_f9=True))
        budget.checkpoint()
        snapshot = original['final_state']
        game.clear_and_push(ShardScene(State.from_json(snapshot)))
        player.press('t'); player.press('right'); player.press('return')
        assert isinstance(game.scene, CampaignScene) and game.scene.phase == 'completed'
        assert reading_scale(game) == 125 and game.scene.prose_pages == 1
        check_transition(game.scene)
        player.reload(snapshot)
        check_transition(game.scene)
        player.capture('earned-ending-125', settle=False)
        rows.append(dict(case='earned-ending', exact_state=player.state.to_json() == snapshot,
                         state_sha256=hashlib.sha256(snapshot.encode()).hexdigest(),
                         casualties=[record.casualties for record in player.state.campaign.completed], f5_f9=True))
        assert rows[-1]['exact_state']
        player.press('return')
        assert isinstance(game.scene, TitleScene)
    finally:
        game.close()
assert game.backend.window is None
budget.checkpoint()
assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
              source_sha256=hashes, script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              original_path=str(original_path), original_sha256=hashlib.sha256(original_blob).hexdigest(),
              historical_gate_source='docs/evidence/shardbound-army-plans-cd351a9/control.json.gz',
              historical_gate_sha256=hashlib.sha256((ROOT / 'docs/evidence/shardbound-army-plans-cd351a9/control.json.gz').read_bytes()).hexdigest(),
              backend='pyglet', window=[1280, 720], text_percent=125, cpu_percent=25, native_fps=30,
              elapsed_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started,
              rows=rows, inputs=player.events, reloads=player.reloads, window_closed=True,
              scope='Three saved presentation cases. Foundries and ending are untouched checkpoints from the '
                    'completed directed journal; Gate uses a public offer from a historical paid departure. '
                    'Exact-state native input checks and screenshots, not another campaign playthrough.')
output.mkdir(parents=True, exist_ok=True)
(output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({key: value for key, value in report.items() if key not in ('source_sha256', 'inputs')}, indent=2))
