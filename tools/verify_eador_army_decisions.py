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


def verify(output, *, backend='pyglet'):
    paths = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'),
             ROOT / 'tools/verify_eador_army_decisions.py', ROOT / 'tools/eador_ui.py',
             ROOT / 'tools/verify_eador_guidance.py']
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    rows, inputs = [], {}
    for plan in ('control', 'mobile'):
        path = ROOT / 'docs/evidence/army-decisions-474b41a' / f'{plan}.json.gz'
        inputs[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
        source = json.loads(gzip.decompress(path.read_bytes()))
        for branch in ('manual', 'auto'):
            with TemporaryDirectory(prefix='shardbound-army-input-') as directory:
                game, title = create_session(['--data-dir', directory], backend=backend, visible=False)
                player = PlayerInput(game, native=backend == 'pyglet', output=output / f'{plan}-{branch}')
                try:
                    CampaignSaves(game.save_manager).save(State.from_json(source['initial_state']))
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
                        command, args, kwargs = entry['command'], entry['args'], entry['kwargs']
                        if command == 'battle.auto_turn':
                            player.press('a')
                        elif command == 'battle.attack':
                            aim(player, *args); player.press('return')
                        elif command in ('battle.move', 'battle.guard'):
                            player.click(*game.scene.grid.center(player.state.battle.unit(args[0]).pos))
                            if command == 'battle.move':
                                player.click(*game.scene.grid.center(tuple(args[1])))
                            else:
                                player.press('g')
                        else:
                            getattr(player.state, command)(*args, **kwargs)
                        assert player.state.to_json() == entry['after'], command
                    assert player.state.to_json() == source[branch]['replenished']
                    player.reload(player.state.to_json())
                    player.capture('paid-aftermath', settle=False)
                    rows.append(dict(plan=plan, branch=branch, layouts=layouts, inputs=player.events,
                                     reloads=player.reloads, exact_commands=len(source[branch]['commands']),
                                     final=player.state.to_json()))
                finally:
                    game._teardown(); game.backend.quit()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, source_unchanged=True, input_sha256=inputs, backend=backend,
                  scope='Native/model input from earned saves, explicit orders then autoplay as journaled, '
                        'real rewards and paid replenishment. No native preparation or independent playtest.', rows=rows)
    output.mkdir(parents=True, exist_ok=True)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'{backend}: {len(rows)} paid branches, {sum(len(r["layouts"]) for r in rows)} forecast layouts, '
          f'{sum(len(r["inputs"]) for r in rows)} inputs; final saved states match', flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
