"""Read the larger tactical canvas and execute its unchanged public controls.

One fresh Wizard battle plus fixed historical hold/escape snapshots. Two explicit
auto-round control checks are rewound through F9; no campaign preparation runs.
"""
from __future__ import annotations

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

from saga2d import Button, Label
from eador.app import create_game
from eador.battle_playback_scene import BattlePlaybackScene
from eador.diagnostics import DiagnosticScene
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import BattleScene, ShardScene, TitleScene
from eador.ui import icon_path
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout

EFFECTS = 'docs/evidence/presentation-pass/effects/verification.json.gz'
SCOUT = 'docs/evidence/scout-paths-78cb545/pathfinder.json.gz'
RELIEF = 'docs/evidence/relief-c6093de/model-orders.json.gz'
FIXED = {
    EFFECTS: 'a4af40389cbf27f4dfa0e7138bfef0575bfcf4879bdcc5b1ff666d3a076ab4b3',
    SCOUT: '543ed0a413c2f0ff27d2894066079ba5f098a53133b87d75fc81b56dccef7b18',
    RELIEF: 'a1b288a7fbe5a66944adf072090f4c86653b915316a4188afb08bda7c20989aa',
}
FOOTER = (('Auto-play one round', 'auto_play', 'a'), ('Retreat', 'retreat', 't'), ('Battle log', 'log', 'l'))


def _fixed_states():
    journals = {}
    for path, digest in FIXED.items():
        data = (ROOT / path).read_bytes()
        assert hashlib.sha256(data).hexdigest() == digest, f'Changed earned source: {path}'
        journals[path] = json.loads(gzip.decompress(data))
    effects, scout = journals[EFFECTS], journals[SCOUT]
    hold = next(case for case in effects['cases'] if case['name'] == 'melee')['orders'][0]['before']
    snapshots = {'hold': hold, 'entry': scout['commands'][93]['before'], 'ready': scout['commands'][108]['before']}
    relief = journals[RELIEF]
    earned = relief['plans']['standard/7/Commander/passive']['snapshots']
    snapshots.update(seal_gain=earned[13], seal_loss=earned[14])
    states = {name: State.from_json(value if isinstance(value, str) else json.dumps(value))
              for name, value in snapshots.items()}
    assert states['hold'].battle.objective.kind == 'hold'
    assert sum(unit.alive for unit in states['hold'].battle.units) == 11
    assert states['entry'].battle.evacuation_blocked_reason
    assert states['ready'].battle.evacuation_blocked_reason is None
    return states, {'files': FIXED, 'hold': {'source': effects['source_revision'],
        'location': 'cases[name=melee].orders[0].before', 'preparation': 'Historical paid model commands including autoplay.'},
        'scout': {'source': scout['execution_source'], 'entry': 'commands[93].before',
                  'ready': 'commands[108].before', 'anchor': scout['source'],
                  'preparation': 'Historical directed continuation; its earlier Scout opening used autoplay.'},
        'relief': {'source': relief['source_revision'], 'plan': 'standard/7/Commander/passive',
                   'gain': 'snapshots[13]', 'loss': 'snapshots[14]',
                   'preparation': 'Historical paid preparation including autoplay; loaded unchanged.'}}


def _fingerprints():
    paths = {Path(__file__), ROOT / 'tools/eador_ui.py', ROOT / 'tools/cpu_budget.py',
             ROOT / 'tools/verify_eador_guidance.py', *(ROOT / 'eador').glob('*.py'),
             *(ROOT / 'saga2d').rglob('*.py'), *(ROOT / path for path in FIXED)}
    paths.update(path for path in (ROOT / 'eador/assets').rglob('*') if path.is_file())
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def _centers(scene):
    return {pos: scene.grid.center(pos) for pos in scene.battle.terrain}


def _board(scene, *, minimum, native=False):
    """Every real terrain corner and HP label fits; no assumed radius or injected board."""
    check_reading_layout(scene)
    assert scene.grid.size >= minimum, (scene.battle.objective.kind, scene.grid.size, minimum)
    corners = [point for pos in scene.battle.terrain for point in scene.grid.corners(pos)]
    for x, y in corners:
        assert 0 <= x <= scene.edge and scene.objective_bottom < y < scene.footer_top
    for control in scene.ui.find_all(lambda item: isinstance(item, Button) and item.visible):
        x, y, width, height = control.bounds
        assert 0 <= x < x + width <= scene.game.width and 0 <= y < y + height <= scene.game.height
    if not native:
        health = []
        for unit in scene.battle.units:
            if not unit.alive:
                continue
            cx, cy = scene.grid.center(unit.pos)
            label = next(text for text in scene.game.backend.texts if text['text'] == str(unit.hp)
                         and abs(text['x'] - cx) < .01 and abs(text['y'] - (cy + scene.grid.size * .23)) < .01)
            width, height = scene.game.backend.measure_text(label['text'], label['font_size'], label['font'])
            for x in (cx - width / 2, cx + width / 2):
                for y in (label['y'], label['y'] + height):
                    assert scene.grid.cell_at(x, y) == unit.pos, (unit.name, label)
            health.append(label['order'])
        transient = [text for text in scene.game.backend.texts
                     if text['text'].startswith(('+', '-')) and text['text'][1:].isdigit()]
        assert all(text['order'] < min(health) for text in transient)
    return {'reading_size': reading_scale(scene.game), 'radius': scene.grid.size,
            'terrain_cells': len(scene.battle.terrain), 'alive_units': sum(unit.alive for unit in scene.battle.units),
            'objective': scene.battle.objective.kind, 'objective_bottom': scene.objective_bottom,
            'footer_top': scene.footer_top, 'bounds': [min(x for x, y in corners), min(y for x, y in corners),
                                                     max(x for x, y in corners), max(y for x, y in corners)]}


def verify(output, *, backend='pyglet', budget=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    budget = budget or CpuBudget(25)
    started, cpu_started = time.monotonic(), time.process_time()
    fixtures, provenance = _fixed_states()
    report = {'scope': __doc__, 'backend': backend, 'provenance': provenance,
              'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'dirty_at_start': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
              'source_sha256': _fingerprints(), 'cpu_percent_requested': budget.percent,
              'captures': [], 'boards': [], 'tooltips': [], 'orders': [], 'objective_pulses': [], 'state_checks': 0}
    with TemporaryDirectory(prefix='shardbound-tactical-layout-') as directory:
        saves = Path(directory)
        # A real long-path backup failure later exercises the complete-message
        # reader. Each component is legal; no game message is injected.
        for index in range(9):
            saves /= f'ordinary-save-directory-{index}-' + 'a' * 70
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=backend == 'pyglet', output=output, finish_actions=False)

        def snapshot():
            return player.state.to_json()

        def exact(expected):
            assert snapshot() == expected
            report['state_checks'] += 1
            budget.checkpoint()

        def press(key):
            player.press(key)
            budget.checkpoint()

        def reading(percent):
            before, scene = snapshot(), game.scene
            press('f2'); press('left' if percent == 100 else 'right'); press('return')
            assert game.scene is scene and reading_scale(game) == percent
            exact(before)

        def window(size):
            before = snapshot()
            game.set_window_size(size)
            player._tick()
            assert game.window_size == size and game.resolution == (1280, 800)
            exact(before)

        def pointer(x, y):
            before = snapshot()
            player.events.append((type(game.scene).__name__, 'hover', (round(x), round(y))))
            if player.native:
                window = game.backend.window
                scale = min(window.width / game.width, window.height / game.height)
                px = (window.width - game.width * scale) / 2 + x * scale
                py = (window.height - game.height * scale) / 2 + (game.height - y) * scale
                window.dispatch_event('on_mouse_motion', round(px), round(py), 0, 0)
            else:
                game.backend.inject_mouse_move(round(x), round(y))
            player._tick(); exact(before)

        def control(label):
            item = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == label)
            assert item is not None, label
            return item

        def hover(item):
            expected = item.tooltip() if callable(item.tooltip) else item.tooltip
            expected = expected or item.text
            x, y, width, height = item.bounds
            pointer(x + width / 2, y + height / 2)
            font = 18 if reading_scale(game) == 125 else 14
            assert game.theme.get_text_style('body').font_size == font
            if not player.native:
                order = max(text['order'] for text in game.backend.texts)
                text = ' '.join(text['text'] for text in game.backend.texts if text['order'] == order)
                assert ' '.join(text.split()) == ' '.join(expected.split()), (expected, text)
                assert all(text['font_size'] == font for text in game.backend.texts if text['order'] == order)
            report['tooltips'].append({'text': expected, 'enabled': item.enabled, 'font_size': font})
            return expected

        def footer():
            scene, before = game.scene, snapshot()
            centers = _centers(scene)
            for label, name, key in FOOTER:
                item = control(label)
                assert item.icon == icon_path(name) and not item.show_text and item.bounds[2] <= 90
                hover(item)
            pointer(2, 2)
            assert _centers(scene) == centers
            exact(before)

        def capture(name, minimum=0):
            before = snapshot()
            player.capture(name, settle=False)
            exact(before)
            if type(game.scene) is BattleScene:
                report['boards'].append(_board(game.scene, minimum=minimum, native=player.native))
            else:
                check_reading_layout(game.scene)
            report['captures'].append({'name': name, 'scene': type(game.scene).__name__,
                                       'reading_size': reading_scale(game), 'window_size': game.window_size,
                                       'logical_canvas': game.resolution})

        def apply(command, *args, key=None, button=None, finish=True):
            before = snapshot()
            expected = State.from_json(before)
            owner = expected.battle if command.startswith('battle.') else expected
            getattr(owner, command.removeprefix('battle.'))(*args)
            if button:
                player.button(button)
            elif key:
                press(key)
            else:
                player.order(command, *args)
            if finish:
                player.finish_playback()
            exact(expected.to_json())
            report['orders'].append({'command': command, 'args': args, 'button': button, 'key': key,
                                     'before': json.loads(before), 'after': json.loads(snapshot())})

        def log_visits():
            scene, before = game.scene, snapshot()
            centers = _centers(scene)
            aim = scene.selected, scene.cursor, scene.hover, scene.targeting
            for key in (False, True):
                press('l') if key else player.button('Battle log')
                assert isinstance(game.scene, DiagnosticScene)
                assert game.scene.message == '\n'.join(scene.battle.log)
                check_reading_layout(game.scene)
                for ignored in ('e', 'g', 'a', '1', 'f5', 'f9'):
                    press(ignored)
                    assert isinstance(game.scene, DiagnosticScene)
                    exact(before)
                press('escape')
                assert game.scene is scene and (scene.selected, scene.cursor, scene.hover, scene.targeting) == aim
                assert _centers(scene) == centers

        try:
            game.push(TitleScene(7, hero_class='Wizard')); press('return')
            exact(State.new(7, 'Wizard').to_json())
            apply('explore', key='x')
            window((1280, 720))
            footer(); capture('fresh-100', minimum=42)
            reading(125); window((1280, 800)); footer()
            scene = game.scene
            centers, before = _centers(scene), snapshot()
            for ident in (1, 3, 0):
                player.click(*scene.grid.center(scene.battle.unit(ident).pos))
                assert scene.selected == ident and _centers(scene) == centers
                exact(before)
            heal = next(item for item in scene.ui.walk() if isinstance(item, Button) and 'Heal ·' in item.text)
            assert not heal.enabled
            hover(heal)
            aim = scene.targeting
            x, y, width, height = heal.bounds
            player.click(x + width / 2, y + height / 2); press('2')
            assert scene.targeting == aim
            exact(before); pointer(2, 2)
            archer = next(unit for unit in scene.battle.units if unit.team == 'player' and unit.can_pin)
            apply('battle.move', archer.id, (-1, 0))
            target = scene.battle.targets(archer.id)[0]
            apply('battle.attack', archer.id, target.id)
            for _ in range(20):
                player._tick(); budget.checkpoint()
            assert _centers(scene) == centers
            capture('fresh-contact-125', minimum=42)
            log_visits()
            apply('battle.end_turn', key='e')
            assert _centers(game.scene) == centers
            saved = snapshot(); player.reload(saved); exact(saved)
            # Each disposable A/T check starts at this exact saved battle.
            for command, label, key in (('battle.auto_turn', 'Auto-play one round', 'a'), ('retreat', 'Retreat', 't')):
                for use_key in (False, True):
                    apply(command, key=key if use_key else None, button=None if use_key else label)
                    press('f9'); exact(saved)

            game.clear_and_push(ShardScene(fixtures['hold'])); player._tick()
            before = snapshot(); reading(125); window((1920, 1080))
            scene, centers = game.scene, _centers(game.scene)
            for unit in scene.battle.units:
                if unit.alive and unit.team == 'player':
                    player.click(*scene.grid.center(unit.pos))
                    assert scene.selected == unit.id and _centers(scene) == centers
                    _board(scene, minimum=38, native=player.native); exact(before)
            press('o'); assert scene.cursor == scene.battle.objective.target
            exact(before); footer(); capture('earned-hold-125', minimum=38)
            player.reload(before); exact(before)

            game.clear_and_push(ShardScene(fixtures['entry'])); player._tick()
            window((1280, 800))
            before = snapshot(); scene = game.scene
            blocked = scene.battle.evacuation_blocked_reason
            assert blocked and blocked in [item.text for item in scene.ui.walk() if isinstance(item, Label)]
            item = control('Evacuate'); assert not item.enabled
            x, y, width, height = item.bounds
            player.click(x + width / 2, y + height / 2); press('v')
            exact(before)
            press('o'); assert scene.cursor in scene.battle.objective.exits
            capture('earned-extraction-entry-125', minimum=35)
            game.clear_and_push(ShardScene(fixtures['ready'])); player._tick()
            assert control('Evacuate').enabled
            saved = snapshot(); player.reload(saved); exact(saved)
            capture('earned-extraction-ready-125', minimum=35)
            apply('battle.evacuate', key='v')
            press('f9'); exact(saved)

            for kind, before_progress, after_progress in (('gain', 0, 1), ('loss', 1, 0)):
                game.clear_and_push(ShardScene(fixtures['seal_' + kind])); player._tick()
                assert game.scene.battle.objective.progress == before_progress
                if kind == 'loss':
                    apply('battle.move', 5, (-2, -1))
                    apply('battle.move', 2, (-1, -1))
                apply('battle.end_turn', key='e', finish=False)
                assert isinstance(game.scene, BattlePlaybackScene)
                resolved = snapshot()
                assert player.state.battle.objective.progress == after_progress and player.state.battle.outcome is None
                for frame in range(500):
                    playback = game.scene.playback
                    if playback.event.kind == 'objective' and .55 <= playback.fraction <= .8:
                        break
                    player._tick(); exact(resolved)
                    assert isinstance(game.scene, BattlePlaybackScene), 'The objective pulse was never seen'
                else:
                    raise AssertionError('The objective pulse exceeded its bounded presentation time')
                label, key = ('Auto-play one round', 'A') if kind == 'gain' else ('Retreat', 'T')
                item = control(label)
                assert not item.enabled
                tip = hover(item)
                assert f'{label} ({key})' in tip and 'Finish playback before giving orders.' in tip
                capture('seal-' + kind + '-125')
                assert game.scene.battle.objective.progress == after_progress
                report['objective_pulses'].append({'kind': kind, 'before': before_progress, 'after': after_progress,
                                                   'frames': frame + 1, 'resolved_state': json.loads(resolved)})
                pointer(2, 2); player.finish_playback(); exact(resolved)

            # Restore the already checked ready save before the real file error.
            press('f9'); exact(saved)

            scene, centers = game.scene, _centers(game.scene)
            primary = saves / 'save_1.json'
            previous = primary.read_bytes()
            backup = saves / 'save_1.backup.json'
            backup.unlink(); backup.mkdir()
            press('f5')
            assert primary.read_bytes() == previous and backup.is_dir()
            exact(saved)
            assert _centers(scene) == centers and str(backup) in scene.message
            assert control('Read message').enabled
            complete = scene.message
            press('m'); assert isinstance(game.scene, DiagnosticScene) and game.scene.message == complete
            capture('complete-message-125')
            parts = []
            for index in range(game.scene.pages):
                view = game.scene
                check_reading_layout(view)
                parts.append(next(item.text for item in view.ui.walk()
                                  if isinstance(item, Label) and item.style.text_color == view.body_color))
                if index + 1 < view.pages:
                    press('pagedown')
            assert ''.join(parts) == complete
            for key in ('a', 'g', 'e', '1', 'f5', 'f9'):
                press(key); exact(saved)
                assert isinstance(game.scene, DiagnosticScene)
            press('escape')
            assert game.scene is scene and _centers(scene) == centers
            player.button('Read message')
            assert isinstance(game.scene, DiagnosticScene) and game.scene.message == complete
            press('escape'); exact(saved)
            report.update(inputs=player.events, input_activations=len(player.events), exact_reloads=player.reloads,
                          final_state=json.loads(snapshot()), error_pages=len(parts),
                          control_autoplay_rounds=2, historical_preparation_executed=False)
        finally:
            game.close()
    assert _fingerprints() == report['source_sha256'], 'Runtime or assets changed during verification'
    report.update(source_unchanged=True, wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-tactical-layout'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    result = verify(args.output, backend=args.backend, budget=CpuBudget(args.cpu_percent))
    print(f'{len(result["captures"])} captures; {result["input_activations"]} inputs; '
          f'{result["exact_reloads"]} exact reload pairs ({args.backend}): {args.output}', flush=True)
