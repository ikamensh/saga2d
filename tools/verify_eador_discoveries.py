"""Read saved adventure locations through real controls without conquering or preparing.

Three fresh Commander/Standard title starts and two authenticated historical saves.
Only selection, reference, reading-size and F5/F9 inputs are issued. Historical
preparation is retained evidence, never replayed here; this is directed UI QA.
"""
from __future__ import annotations

import argparse
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

from eador.app import create_game
from eador.codex import CodexScene
from eador.content import RELICS, SITES
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import ShardScene, TitleScene
from saga2d import Button
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout
from tools.verify_eador_reading import check_page, visible_labels

OLD_WORLD = 'tests/eador/fixtures/v12_ruins_seed7_before_site_variation.json'
CLEARED = 'tests/eador/fixtures/v12_frontier_caravan_result.json'
FIXED = {
    OLD_WORLD: '58ad400afc630200504a58c2058de5e6286e4030b8a3289becfe22ec1207d093',
    CLEARED: '49ee4c2786520a3be241bf02a810f142d23519873bd0f34477b6f5e015024fa1',
}
# Comparison evidence only. Destinations always come from the loaded world's provinces.
BASELINE = {
    'frontier': {'stranded_explorer': (0, -1), 'muster_yard': (-1, 1), 'courier_crossing': (0, 2)},
    'ruins': {'broken_observatory': (-1, 0), 'sealed_vault': (-1, 1), 'aerie_raid': (0, 0)},
}


def _fingerprints():
    paths = {Path(__file__), ROOT / 'tools/eador_ui.py', ROOT / 'tools/cpu_budget.py',
             ROOT / 'tools/verify_eador_guidance.py', ROOT / 'tools/verify_eador_reading.py',
             *(ROOT / 'eador').glob('*.py'), *(ROOT / 'saga2d').rglob('*.py'),
             *(ROOT / path for path in FIXED)}
    paths.update(path for path in (ROOT / 'eador/assets').rglob('*') if path.is_file())
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def _fixed_state(path):
    data = (ROOT / path).read_bytes()
    assert hashlib.sha256(data).hexdigest() == FIXED[path], f'Changed historical source: {path}'
    state = State.from_json(data.decode())
    assert json.loads(state.to_json()) == json.loads(data), 'Historical world changed while loading'
    return state


def verify(output, *, backend='pyglet', budget=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    budget = budget or CpuBudget(25)
    started, cpu_started = time.monotonic(), time.process_time()
    report = {
        'scope': __doc__, 'backend': backend, 'cpu_percent_requested': budget.percent,
        'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'dirty_at_start': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
        'source_sha256': _fingerprints(), 'cases': [], 'readings': [], 'captures': [],
        'state_checks': 0, 'preparation_commands': 0,
        'provenance': {
            'baseline_revision': 'a7a6c5020232d539a7f4d616597942a47174b396',
            'baseline_worldgen_sha256': '0c89b6d52208f9cc929e67caae09790f4b1407903806fe87f0f01d0320ac79a3',
            'baseline_positions': BASELINE, 'fixed_sha256': FIXED,
            'old_world': 'Exact initial Ruins7/Standard world generated at1524c48 before site variation.',
            'cleared_world': 'Retained v12 Caravan result, introduced at e041337; historical preparation includes autoplay.',
        },
    }
    with TemporaryDirectory(prefix='shardbound-discovery-reader-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output)

        def exact(expected):
            assert player.state.to_json() == expected, 'Reading or saving changed the world'
            report['state_checks'] += 1
            budget.checkpoint()

        def press(key):
            player.press(key)
            exact(before)

        def capture(name):
            player.capture(name, settle=False)
            exact(before)
            report['captures'].append({'name': name, 'case': case['name'],
                'scene': type(game.scene).__name__, 'reading_size': reading_scale(game),
                'window_size': list(game.window_size), 'selected': list(player.root.selected)})

        def select_source():
            player.click(*player.root.grid.center(province.pos))
            assert player.root.selected == province.pos
            expected_label = province.site + (' · cleared' if province.explored else '')
            assert expected_label in [label.text for label in visible_labels(game.scene.ui)]
            check_reading_layout(game.scene)
            exact(before)

        def read_entry(key, title, location, capture_name=None):
            press(key)
            assert isinstance(game.scene, CodexScene)
            for _ in range(game.scene.pages):
                check_page(game.scene)
                match = next((entry for entry in game.scene.visible_entries if entry.title == title), None)
                if match:
                    text = match.facts + ' ' + match.description
                    assert 'Recorded sources: ' in text and location in text, (title, location, text)
                    shown = '\n'.join(label.text for label in visible_labels(game.scene.ui))
                    assert match.title in shown and match.description in shown
                    if capture_name:
                        capture(capture_name)
                    return {'title': title, 'text': text, 'location': location, 'page': game.scene.page + 1}
                press('right')
            raise AssertionError(f'No readable page contains {title}')

        cases = [('frontier-5', 'frontier', 5, None), ('frontier-12', 'frontier', 12, None),
                 ('ruins-7', 'ruins', 7, None), ('historical-ruins', 'ruins', 7, OLD_WORLD),
                 ('cleared-caravan', 'frontier', 7, CLEARED)]
        try:
            for name, theme, seed, fixture in cases:
                if fixture:
                    game.clear_and_push(ShardScene(_fixed_state(fixture)))
                    player._tick()
                else:
                    game.clear_and_push(TitleScene(seed, theme=theme))
                    player.press('return')
                    assert player.state.to_json() == State.new(seed, theme=theme).to_json()
                before = player.state.to_json()
                state = player.root.state
                if fixture:
                    kind = 'sealed_vault' if fixture == OLD_WORLD else 'caravan'
                    province, = [p for p in state.provinces.values() if p.site_kind == kind
                                 and (fixture != CLEARED or p.explored)]
                    assert province.explored == (fixture == CLEARED)
                else:
                    moved = [p for kind, old in BASELINE[theme].items() for p in state.provinces.values()
                             if p.site_kind == kind and p.pos != old]
                    assert moved, f'{name} has no moved named source'
                    province = moved[0]
                    assert province.owner == 'neutral' and not province.explored
                assert province.site_relic
                case = {'name': name, 'theme': theme, 'seed': seed, 'fixture': fixture,
                        'origin': 'fixed_save' if fixture else 'fresh_title', 'initial': json.loads(before),
                        'source': {'kind': province.site_kind, 'name': province.site, 'province': province.name,
                                   'position': list(province.pos), 'owner': province.owner,
                                   'cleared': province.explored, 'relic': province.site_relic,
                                   'baseline_position': list(BASELINE[theme][province.site_kind]) if not fixture else None},
                        'readings': [125] if fixture else [100, 125]}
                for percent in case['readings']:
                    select_source()
                    selected = player.root.selected
                    press('f2'); press('left' if percent == 100 else 'right'); press('return')
                    assert reading_scale(game) == percent and player.root.selected == selected
                    select_source()
                    if (name == 'frontier-5' and percent == 100 or name != 'frontier-5' and percent == 125):
                        capture(f'{name}-selected-{percent}')
                    codex = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Codex')
                    assert codex is not None and codex.icon and not codex.show_text
                    if percent == 100:
                        player.button('Codex')
                        exact(before)
                    else:
                        press('c')
                    location = province.name + (' (cleared)' if province.explored else '')
                    sites = read_entry('5', SITES[province.site_kind].name, location,
                                       'frontier-5-sites-125' if name == 'frontier-5' and percent == 125 else None)
                    relics = read_entry('6', RELICS[province.site_relic].name, province.site + ' at ' + location,
                                        f'{name}-relics-125' if name in ('frontier-5', 'cleared-caravan') and percent == 125 else None)
                    report['readings'].append({'case': name, 'percent': percent,
                                              'site_location': sites, 'relic_location': relics})
                    press('escape')
                    assert game.scene is player.root and player.root.selected == selected
                # Reload restores the saved world. UI selection is re-established by the
                # ordinary map click, rather than misrepresented as serialized model data.
                player.reload(before)
                exact(before)
                case['selection_after_reload'] = list(player.root.selected)
                select_source()
                case['final'] = json.loads(player.state.to_json())
                report['cases'].append(case)
            report['inputs'] = player.events
            report['input_activations'] = len(player.events)
            report['exact_reloads'] = player.reloads
        finally:
            game.close()
    report['source_unchanged'] = report['source_sha256'] == _fingerprints()
    assert report['source_unchanged'], 'Source or assets changed during verification'
    budget.checkpoint()
    report['wall_seconds'], report['cpu_seconds'] = time.monotonic() - started, time.process_time() - cpu_started
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"Discovery reader: {len(report['cases'])} worlds, {report['input_activations']} inputs, "
          f"{report['exact_reloads']} exact reloads, {len(report['captures'])} captures ({backend})", flush=True)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-discoveries'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    verify(args.output, backend=args.backend, budget=CpuBudget(args.cpu_percent))
