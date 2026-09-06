"""Replay the earned lethal Pin as a bounded native input and reading check."""
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ['SAGA2D_SILENT'] = '1'
from saga2d import Label
from eador.__main__ import create_session
from eador.model import State
from eador.persistence import CampaignSaves
from tools.eador_ui import PlayerInput
from tools.verify_eador_army_decisions import inspect

path = ROOT / 'docs/evidence/shardbound-army-plans-cd351a9/mobile.json.gz'
initial = json.loads(gzip.decompress(path.read_bytes()))['commands'][26]['before']
output = Path('/tmp/shardbound-pin-kill-native')
paths = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'), Path(__file__).resolve(),
         *(ROOT / 'tools' / p for p in ('eador_ui.py', 'verify_eador_army_decisions.py', 'verify_eador_guidance.py'))]
hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
with TemporaryDirectory(prefix='shardbound-pin-kill-') as directory:
    game, title = create_session(['--data-dir', directory], backend='pyglet', visible=False)
    player = PlayerInput(game, native=True, output=output)
    try:
        CampaignSaves(game.save_manager).save(State.from_json(initial))
        game.push(title); player.press('f9')
        player.click(*game.scene.grid.center(player.state.battle.unit(3).pos))
        player.press('p')
        for _ in player.state.battle.units:
            player.press('f')
            if game.scene.cursor == player.state.battle.unit(1007).pos:
                break
        layouts = inspect(player, 'Goblin defeated.')
        assert not any('Next turn: Move' in item.text for item in game.scene.ui.walk() if isinstance(item, Label))
        player.press('return')
        assert player.state.battle.unit(1007).hp == 0
        player.reload(player.state.to_json())
        assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest for p, digest in hashes.items())
        output.mkdir(parents=True, exist_ok=True)
        report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                      source_sha256=hashes, source_unchanged=True,
                      input_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), command_index=26,
                      initial_sha256=hashlib.sha256(initial.encode()).hexdigest(), layouts=layouts,
                      inputs=player.events, reloads=player.reloads, final=player.state.to_json())
        (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
        print(f'Native lethal Pin: {len(layouts)} layouts, {len(player.events)} inputs, exact saved continuation.')
    finally:
        game._teardown(); game.backend.quit()
