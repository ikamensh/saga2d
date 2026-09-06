"""Verify one retained directed journey after the explicit Game.close() change.

This creates a derived replay receipt, never a new playthrough. The original
compressed journal remains unchanged. Every command, forecast, currency delta
and serialized state must match before the new source identity is recorded.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())
sys.path.insert(0, str(ROOT))

from eador.model import State
from tools.audit_eador_army_plans import SavedCommands
from tools.cpu_budget import CpuBudget
from tools.verify_eador_directed_journey import load_journal


def replay(input_path, output_path):
    if input_path.resolve() == output_path.resolve():
        raise ValueError('Preserve the original journal; choose a separate derived output')
    budget = CpuBudget(25)
    started, cpu_started = time.monotonic(), time.process_time()
    implementations = [Path(__file__).resolve(), ROOT / 'tools/verify_eador_directed_journey.py']
    implementation_hashes = {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                             for path in implementations}
    blob = input_path.read_bytes()
    original = json.loads(gzip.decompress(blob))
    original = load_journal(blob, original['source_sha256'], budget)
    paths = set(original['source_sha256'])
    paths.update(str(path.relative_to(ROOT)) for area in ('eador', 'saga2d')
                 for path in ROOT.glob(f'{area}/**/*.py'))
    current = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
               for path in sorted(paths)}
    changed = {path for path in current
               if current[path] != original['source_sha256'].get(path)}
    assert changed == {'saga2d/game.py', 'saga2d/testing.py'}, changed

    played = SavedCommands(State.from_json(original['initial_state']), budget)
    for index, entry in enumerate(original['commands'], 1):
        assert played.state.to_json() == entry['before'], f'Before command {index}'
        command, args = entry['command'], entry['args']
        if command == 'travel':
            args = [tuple(args[0])]
        elif command in ('battle.move', 'battle.smoke'):
            args = [args[0], tuple(args[1])]
        if 'forecast' in entry:
            preview = played.battle.pin_preview if command == 'battle.pin' else played.battle.preview
            assert list(preview(*args)) == entry['forecast'], f'Forecast {index}'
        played.order(command, *args, **entry['kwargs'])
        actual = json.loads(json.dumps(played.commands[-1]))
        assert actual == {key: entry[key] for key in actual}, f'Command {index}: {command}'
        if index % 100 == 0:
            print(f'{index}/{len(original["commands"])} exact commands and saved states', flush=True)
    assert played.state.to_json() == original['final_state']
    budget.checkpoint()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
               for path, digest in current.items())
    assert all(hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest
               for path, digest in implementation_hashes.items())
    derived = dict(original)
    derived['execution_source'] = subprocess.check_output(
        ['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
    derived['source_sha256'] = current
    derived['replayed_from'] = dict(
        input_path=str(input_path.resolve()), input_sha256=hashlib.sha256(blob).hexdigest(),
        execution_source=original['execution_source'], source_sha256=original['source_sha256'],
        verification_source_sha256=implementation_hashes,
        changed_files=sorted(changed), exact_commands=len(original['commands']),
        cpu_percent=25, elapsed_seconds=time.monotonic() - started,
        cpu_seconds=time.process_time() - cpu_started,
        scope='Deterministic verification of the original decisions after Game.close(). '
              'Every before/after save, command argument, recorded forecast and currency delta matches. '
              'No new decisions, retries, state edits, outcome normalization or new manual-play credit.')
    load_journal(gzip.compress(json.dumps(derived).encode(), mtime=0), current, budget)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(gzip.compress(json.dumps(derived, separators=(',', ':')).encode(), mtime=0))
    print(json.dumps(derived['replayed_from'], indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    replay(args.input, args.output)
