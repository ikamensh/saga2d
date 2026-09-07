"""Replay directed orders from an authenticated earned save or a fresh campaign."""
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

from eador.__main__ import create_session
from eador.model import State
from eador.persistence import CampaignSaves
from eador.preferences import reading_scale
from eador.scene import TitleScene
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PLAYER_COMMANDS, PlayerInput
from tools.verify_eador_guidance import check_reading_layout

EARNED_OPENINGS = {
    'docs/evidence/shardbound-army-plans-cd351a9/control.json.gz':
        ('6609eb4f334a956f6d6873e378b0b87bdd6901f3ad2f4688226265b8ede0b72a', 38),
    'docs/evidence/shardbound-army-plans-cd351a9/mobile.json.gz':
        ('1962ca77a5cbad06de2d81a5591e18d35e5502429dbe0d55b8b07a36bde00d5c', 14),
}


def _opening(supplied):
    if not isinstance(supplied, dict):
        raise ValueError('Directed journal must identify its opening')
    if supplied.get('kind') == 'new_campaign':
        if (set(supplied) != {'kind', 'seed', 'hero_class', 'difficulty', 'initial_sha256'}
                or type(supplied['seed']) is not int
                or not isinstance(supplied['hero_class'], str)
                or not isinstance(supplied['difficulty'], str)):
            raise ValueError('Fresh campaign provenance requires seed, hero and difficulty')
        initial = State.new_campaign(supplied['seed'], supplied['hero_class'],
                                     difficulty=supplied['difficulty']).to_json()
        return initial, dict(kind='new_campaign', seed=supplied['seed'],
                             hero_class=supplied['hero_class'], difficulty=supplied['difficulty'],
                             initial_sha256=hashlib.sha256(initial.encode()).hexdigest())
    if not isinstance(supplied.get('path'), str) or supplied['path'] not in EARNED_OPENINGS:
        raise ValueError('Directed journal must name an authenticated earned opening')
    path = supplied['path']
    checksum, index = EARNED_OPENINGS[path]
    history_blob = (ROOT / path).read_bytes()
    if hashlib.sha256(history_blob).hexdigest() != checksum:
        raise ValueError(f'The retained earned opening has changed: {path}')
    history = json.loads(gzip.decompress(history_blob))
    initial = history['commands'][index]['before']
    provenance = dict(path=path, journal_sha256=checksum, journal_source=history['source_commit'],
                      command_index=index, initial_sha256=hashlib.sha256(initial.encode()).hexdigest())
    return initial, provenance


def load_journal(blob, hashes, budget):
    """Verify a reproducible opening and exact command chain before opening a session."""
    source = json.loads(gzip.decompress(blob))
    required = {'source', 'execution_source', 'source_sha256', 'initial_state', 'final_state', 'commands'}
    if not isinstance(source, dict) or not required <= source.keys():
        raise ValueError('Directed journal must contain provenance, model hashes and saved commands')
    supplied = source['source']
    initial, provenance = _opening(supplied)
    if supplied != provenance or source['initial_state'] != initial:
        raise ValueError('Directed journal must start from its authenticated opening')
    manifest = source['source_sha256']
    if not isinstance(manifest, dict):
        raise ValueError('Directed journal must include its model source manifest')
    models = {path: digest for path, digest in hashes.items() if path.startswith(('eador/', 'saga2d/'))}
    recorded = {path: digest for path, digest in manifest.items() if path.startswith(('eador/', 'saga2d/'))}
    if recorded != models:
        raise ValueError('Directed journal model source differs from the current game')
    if not isinstance(source['commands'], list) or not source['commands']:
        raise ValueError('Directed journal must contain at least one command')
    before = initial
    for entry in source['commands']:
        budget.checkpoint()
        if (not isinstance(entry, dict) or not {'command', 'args', 'kwargs', 'reason', 'before', 'after'} <= entry.keys()
                or not isinstance(entry['command'], str) or not isinstance(entry['args'], list)
                or not isinstance(entry['kwargs'], dict) or not isinstance(entry['after'], str)
                or not isinstance(entry['reason'], str) or not entry['reason'].strip()):
            raise ValueError('Directed journal contains an incomplete command or rationale')
        if entry['command'] == 'battle.auto_turn':
            raise ValueError('Directed continuation cannot contain autoplay')
        if entry['command'] not in PLAYER_COMMANDS:
            raise ValueError('Directed journal contains an unsupported player command')
        if entry['before'] != before:
            raise ValueError('Directed commands do not form an exact saved chain')
        before = entry['after']
    if before != source['final_state']:
        raise ValueError('Directed final state differs from its last command')
    return source


def verify(input_report, output, *, backend='pyglet', cpu_percent=25):
    """Replay exact input and F5/F9 continuation, with isolated saves and cooperative pacing."""
    budget = CpuBudget(cpu_percent)
    started, cpu_started = time.monotonic(), time.process_time()
    paths = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'),
             Path(__file__), ROOT / 'tools/eador_ui.py', ROOT / 'tools/cpu_budget.py',
             ROOT / 'tools/verify_eador_guidance.py']
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    blob = input_report.read_bytes()
    source = load_journal(blob, hashes, budget)
    captures = []
    with TemporaryDirectory(prefix='shardbound-directed-input-') as directory:
        game, title = create_session(['--data-dir', directory], backend=backend, visible=False)
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            origin = source['source']
            if origin.get('kind') == 'new_campaign':
                game.push(TitleScene(origin['seed'], hero_class=origin['hero_class'],
                                     difficulty=origin['difficulty']))
                player.press('l')
            else:
                CampaignSaves(game.save_manager).save(State.from_json(source['initial_state']))
                game.push(title)
                player.press('f9')
            player.button('Text size')
            for key in ('right', 'return'):
                player.press(key)
            assert reading_scale(game) == 125
            assert player.state.to_json() == source['initial_state']
            seen = set()
            for index, entry in enumerate(source['commands'], 1):
                budget.checkpoint()
                assert player.state.to_json() == entry['before'], f'Before command {index}'
                command = entry['command']
                if command == 'battle.evacuate':
                    name = f'{index:03d}-before-battle-evacuate'
                    check_reading_layout(game.scene)
                    player.capture(name, settle=False)
                    captures.append(name)
                player.order(command, *entry['args'], **entry['kwargs'])
                assert player.state.to_json() == entry['after'], f'After command {index}: {entry["command"]}'
                if command == 'explore' and player.state.battle_encounter:
                    name = f'{index:03d}-entry-{player.state.battle_encounter}'
                    check_reading_layout(game.scene)
                    player.capture(name, settle=False)
                    captures.append(name)
                if command == 'battle.evacuate' or (command not in seen and command in (
                        'battle.cast', 'battle.end_turn', 'battle.repulse', 'battle.smoke', 'battle.swap',
                        'resolve_battle', 'advance')):
                    name = f'{index:03d}-{command.replace(".", "-")}'
                    check_reading_layout(game.scene)
                    player.capture(name, settle=False)
                    captures.append(name)
                seen.add(command)
                player.reload(entry['after'])
                if index % 25 == 0:
                    print(f'{backend}: {index}/{len(source["commands"])} exact commands and reloads', flush=True)
            player.capture('final-state', settle=False)
            check_reading_layout(game.scene)
            final = player.state.to_json()
            assert final == source['final_state']
        finally:
            game.close()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, source_unchanged=True, backend=backend, cpu_percent=cpu_percent,
                  elapsed_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started,
                  input_report=str(input_report.resolve()), input_sha256=hashlib.sha256(blob).hexdigest(),
                  input_source=source['source'], input_execution_source=source['execution_source'],
                  exact_commands=len(source['commands']), reloads=player.reloads, inputs=player.events,
                  final_state=final, captures=captures + ['final-state'],
                  scope=('Agent-directed fresh campaign reproduced through New Campaign input. '
                         if source['source'].get('kind') == 'new_campaign' else
                         'Agent-directed continuation from a historical autoplay opening; no native opening preparation. ')
                        + 'Exact game controls and saves; no independent playtest or full-campaign claim.')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{backend}: {report["exact_commands"]} exact commands, {len(player.events)} inputs; saved states match', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    verify(args.input_report, args.output, backend=args.backend, cpu_percent=args.cpu_percent)
