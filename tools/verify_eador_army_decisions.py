"""Inspect earned casualty forecasts and replay paid decisions through native controls."""
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

from saga2d import Label
from eador.__main__ import create_session
from eador.model import State
from eador.persistence import CampaignSaves
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def aim(player, actor, target):
    player.click(*player.game.scene.grid.center(player.state.battle.unit(actor).pos))
    destination = player.state.battle.unit(target).pos
    for _ in player.state.battle.units:
        player.press('f')
        if player.game.scene.cursor == destination:
            return
    raise AssertionError('The expected target is not selectable')


def inspect(player, warning):
    """Read both sizes in every supported window without changing the earned save."""
    game, rows = player.game, []
    before = player.state.to_json()
    for window in ((1280, 720), (1280, 800), (1920, 1080)):
        game.set_window_size(window)
        for percent, direction in ((100, 'left'), (125, 'right')):
            for key in ('f2', direction, 'return'):
                player.press(key)
            labels = [item.text for item in game.scene.ui.walk() if isinstance(item, Label)]
            assert any(warning in text for text in labels)
            assert player.state.to_json() == before
            check_reading_layout(game.scene)
            rows.append(dict(window=window, reading_percent=percent, labels=labels))
            if window == (1280, 720):
                player.capture(f'warning-{percent}', settle=False)
    return rows


def verify(input_report, output, *, backend='pyglet'):
    """Replay one current audit report; historical journals remain provenance only."""
    paths = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'),
             ROOT / 'tools/verify_eador_army_decisions.py', ROOT / 'tools/eador_ui.py',
             ROOT / 'tools/verify_eador_guidance.py']
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    input_bytes = input_report.read_bytes()
    source = json.loads(gzip.decompress(input_bytes))
    required = {'plan', 'source', 'initial_state', 'manual', 'auto', 'source_commit', 'source_sha256'}
    if not isinstance(source, dict) or not required <= source.keys():
        raise ValueError('Input report must contain the current army audit, source manifest and both branches')
    plan = source['plan']
    if plan not in ('control', 'mobile'):
        raise ValueError(f'Unsupported army decision plan: {plan!r}')
    model_hashes = {path: digest for path, digest in hashes.items() if path.startswith(('eador/', 'saga2d/'))}
    if not isinstance(source['source_sha256'], dict):
        raise ValueError('Input report must contain its model source manifest')
    recorded_models = {path: digest for path, digest in source['source_sha256'].items()
                       if path.startswith(('eador/', 'saga2d/'))}
    # Compare only known repository paths; never read a path supplied by the report.
    if recorded_models.keys() != model_hashes.keys():
        raise ValueError('Input report model source manifest is incomplete or incompatible; regenerate the audit')
    for path, digest in model_hashes.items():
        if recorded_models[path] != digest:
            raise ValueError(f'Input report differs from current {path}; regenerate the audit')
    provenance = source['source']
    required_provenance = {'path', 'journal_sha256', 'journal_source_commit', 'command_index', 'state_sha256'}
    if not isinstance(provenance, dict) or not required_provenance <= provenance.keys():
        raise ValueError('Input report must identify the historical earned save')
    initial = source['initial_state']
    if not isinstance(initial, str) or hashlib.sha256(initial.encode()).hexdigest() != provenance['state_sha256']:
        raise ValueError('Input report earned save differs from its recorded hash')
    for branch in ('manual', 'auto'):
        data = source[branch]
        if (not isinstance(data, dict) or not {'commands', 'replenished'} <= data.keys()
                or not isinstance(data['commands'], list) or not data['commands']
                or not isinstance(data['replenished'], str)):
            raise ValueError(f'Input report must contain the {branch} command journal and paid aftermath')
        before = initial
        for entry in data['commands']:
            if not isinstance(entry, dict) or not {'command', 'args', 'kwargs', 'before', 'after'} <= entry.keys():
                raise ValueError(f'Input report has an incomplete {branch} command')
            if (not isinstance(entry['command'], str) or not isinstance(entry['args'], list)
                    or not isinstance(entry['kwargs'], dict) or not isinstance(entry['after'], str)):
                raise ValueError(f'Input report has a malformed {branch} command')
            if entry['before'] != before:
                raise ValueError(f'Input report {branch} commands do not form an exact saved chain')
            before = entry['after']
        if before != data['replenished']:
            raise ValueError(f'Input report {branch} paid aftermath differs from its last command')
    rows = []
    for branch in ('manual', 'auto'):
        with TemporaryDirectory(prefix='shardbound-army-input-') as directory:
            game, title = create_session(['--data-dir', directory], backend=backend, visible=False)
            player = PlayerInput(game, native=backend == 'pyglet', output=output / f'{plan}-{branch}')
            try:
                CampaignSaves(game.save_manager).save(State.from_json(initial))
                game.push(title); player.press('f9')
                # Inspect a genuine casualty before either branch chooses its orders.
                aim(player, 6 if plan == 'control' else 4, 1011 if plan == 'control' else 1007)
                warning = 'Rune Adept falls.' if plan == 'control' else 'Warden falls.'
                layouts = inspect(player, warning)
                player.press('f1')
                check_reading_layout(game.scene)
                player.capture('guide-125', settle=False)
                player.press('escape')
                for entry in source[branch]['commands']:
                    assert player.state.to_json() == entry['before']
                    player.order(entry['command'], *entry['args'], **entry['kwargs'])
                    assert player.state.to_json() == entry['after'], entry['command']
                    player.reload(entry['after'])
                assert player.state.to_json() == source[branch]['replenished']
                player.capture('paid-aftermath', settle=False)
                rows.append(dict(plan=plan, branch=branch, layouts=layouts, inputs=player.events,
                                 reloads=player.reloads, exact_commands=len(source[branch]['commands']),
                                 final=player.state.to_json()))
            finally:
                game.close()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, source_unchanged=True,
                  input_report=str(input_report.resolve()), input_sha256=hashlib.sha256(input_bytes).hexdigest(),
                  input_source_commit=source['source_commit'], input_source=provenance, backend=backend,
                  scope='Native/model input from earned saves, explicit orders then autoplay as journaled, '
                        'real rewards and paid replenishment. No native preparation or independent playtest.', rows=rows)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{backend}: {len(rows)} paid branches, {sum(len(r["layouts"]) for r in rows)} forecast layouts, '
          f'{sum(len(r["inputs"]) for r in rows)} inputs; final saved states match', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-report', type=Path, required=True,
                        help='One current .json.gz report from audit_eador_army_decisions.py')
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    args = parser.parse_args()
    verify(args.input_report, args.output, backend=args.backend)
