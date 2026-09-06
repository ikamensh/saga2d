"""Replay two real paid battle continuations through the shipped save and order controls."""
import argparse
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('SAGA2D_SILENT', '1')

from eador.__main__ import create_session
from eador.model import State
from eador.persistence import CampaignSaves
from eador.scene import BattleScene, ResultScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_control import ControlOrders


def verify(input_report, output, *, backend='pyglet'):
    """Load an unedited earned save; compare explicit Smoke/Guard and exact model continuations.

    Paid preparation was executed by the input report's model policy. This UI
    check starts at its saved round-three decision, not at a new campaign.
    """
    original = json.loads(gzip.decompress(input_report.read_bytes()))
    files = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'),
             *(ROOT / 'tools' / name for name in ('verify_eador_investment_choice.py',
               'eador_ui.py', 'verify_eador_control.py', 'verify_eador_extraction.py',
               'eador_extraction_campaign.py'))]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    rows = []
    for branch in original['branches']:
        command = branch['command']
        with TemporaryDirectory(prefix='shardbound-paid-choice-') as directory:
            game, title = create_session(['--data-dir', directory], backend=backend, visible=False)
            player = PlayerInput(game, native=backend == 'pyglet', output=output / command)
            try:
                # Only restore the earned input. All changing orders below use game input.
                CampaignSaves(game.save_manager).save(State.from_json(json.dumps(original['before'])))
                game.push(title)
                player.press('f9')
                assert isinstance(game.scene, BattleScene)
                assert json.loads(player.state.to_json()) == original['before']
                orders = ControlOrders(player.state)
                args = branch['args']
                if command == 'smoke':
                    args = [args[0], tuple(args[1])]
                orders.do(command, *args)
                assert json.loads(player.state.to_json()) == branch['first_order_state']
                player.reload(player.state.to_json())
                player.capture('chosen-order')
                for action, args in branch['fight']['orders']:
                    assert action == 'auto_turn' and not args
                    player.press('a')
                assert isinstance(game.scene, ResultScene)
                actual = json.loads(json.dumps(player.state.battle.to_dict()))
                assert actual == branch['fight']['result']
                living = [u for u in actual['units'] if u['team'] == 'player' and u['hp'] > 0]
                wounds = sum(u['max_hp'] - u['hp'] for u in living)
                player.capture('tactical-result')
                player.state.resolve_battle()
                while player.state.choice:
                    player.state.choose(player.state.choice.options[0].id)
                assert json.loads(player.state.to_json()) == branch['final']
                player.reload(player.state.to_json())
                rows.append(dict(command=command, wounds=wounds, round=actual['round'],
                                 exact_reloads=player.reloads, inputs=player.events,
                                 final=json.loads(player.state.to_json())))
            finally:
                game._teardown()
                game.backend.quit()
    assert all(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() == digest for p, digest in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, backend=backend, input_sha256=hashlib.sha256(input_report.read_bytes()).hexdigest(),
                  scope='Public game input from an earned round-three save; model preparation, explicit first order, '
                        'then automatic rounds and visible Finish playback. No native preparation or optimal-play claim.',
                  branches=rows)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Paid choice ({backend}): ' + ', '.join(f"{r["command"]}: {r["wounds"]} wounds" for r in rows))
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    args = parser.parse_args()
    verify(args.input_report, args.output, backend=args.backend)
