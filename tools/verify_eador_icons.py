"""Exercise icon controls with the same bounded input journey in mock and native UI.

One fresh linked Wizard opening, ordinary toolbar visits, an End turn, one
legal Archer attack and Guard, plus exact save/reloads. The Explore icon and
key are compared from the same real quicksave. No independent first-run claim.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import subprocess
from tempfile import TemporaryDirectory
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ['SAGA2D_SILENT'] = '1'

from eador.app import create_game
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import BattleScene, ShardScene, TitleScene
from eador.ui import icon_path
from saga2d import Button, Image, Label, Row
from tools.cpu_budget import CpuBudget
from tools.eador_ui import PlayerInput


def _fingerprints():
    paths = {Path(__file__), ROOT / 'tools/eador_ui.py', ROOT / 'tools/cpu_budget.py',
             *(ROOT / 'eador').glob('*.py'), *(ROOT / 'saga2d').rglob('*.py'),
             *(ROOT / 'eador/assets').rglob('*.json')}
    paths.update((ROOT / 'eador/assets/images/icons').glob('*.png'))
    return {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(paths)}


def verify(output, *, backend='pyglet', budget=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    budget = budget or CpuBudget()
    started, cpu_started = time.monotonic(), time.process_time()
    report = {'scope': 'Directed icon presentation and input; silent audio; fresh linked seed 7 Wizard opening.',
              'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'dirty_at_start': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
              'source_sha256': _fingerprints(), 'captures': [], 'tooltips': [],
              'toolbar_visits': [], 'metrics': [], 'army_metrics': [], 'spell_costs': [],
              'travel_controls': [], 'command_checks': [], 'aiming_checks': [],
              'disabled_checks': [], 'state_checks': 0, 'comparison_loads': 0,
              'cpu_percent_requested': budget.percent}
    with TemporaryDirectory(prefix='shardbound-icons-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output, finish_actions=False)

        def state():
            roots = [scene for scene in game.scenes if isinstance(scene, ShardScene)]
            return roots[0].state.to_json() if roots else None

        def unchanged(before):
            assert state() == before, 'A presentation-only input changed the campaign'
            report['state_checks'] += 1
            budget.checkpoint()

        def press(key):
            player.press(key)
            budget.checkpoint()

        def move_pointer(x, y):
            before = state()
            player.events.append((type(game.scene).__name__, 'hover', (round(x), round(y))))
            if player.native:
                window = game.backend.window
                scale = min(window.width / game.width, window.height / game.height)
                px = (window.width - game.width * scale) / 2 + x * scale
                py = (window.height - game.height * scale) / 2 + (game.height - y) * scale
                window.dispatch_event('on_mouse_motion', round(px), round(py), 0, 0)
            else:
                game.backend.inject_mouse_move(round(x), round(y))
            player._tick()
            unchanged(before)

        def control(label):
            item = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == label)
            assert item is not None, f'{type(game.scene).__name__}: missing {label}'
            x, y, width, height = item.bounds
            assert 0 <= x < x + width <= game.width and 0 <= y < y + height <= game.height
            return item

        def hover(item, *, owner=None):
            owner = owner or item
            expected = owner.tooltip() if callable(owner.tooltip) else owner.tooltip
            if expected is None and isinstance(owner, Button) and not owner.show_text:
                expected = owner.text
            assert expected, 'Every icon and unavailable action must explain itself'
            x, y, width, height = item.bounds
            move_pointer(x + width / 2, y + height / 2)
            font_size = 18 if reading_scale(game) == 125 else 14
            actual_font = game.theme.get_text_style('body').font_size
            assert actual_font == font_size, f'{type(game.scene).__name__} tooltip font {actual_font}; expected {font_size}'
            if backend == 'mock':
                order = max(text['order'] for text in game.backend.texts)
                rendered = ' '.join(text['text'] for text in game.backend.texts if text['order'] == order)
                assert ' '.join(expected.split()) == ' '.join(rendered.split()), (expected, rendered)
                assert order > max(image['order'] for image in game.backend.images)
                assert all(text['font_size'] == font_size for text in game.backend.texts if text['order'] == order)
            report['tooltips'].append({'scene': type(game.scene).__name__, 'text': expected,
                                       'enabled': item.enabled, 'reading_size': reading_scale(game),
                                       'font_size': font_size,
                                       'rendered_order': order if backend == 'mock' else None})
            return expected

        def hide_tip():
            move_pointer(2, 2)
            if backend == 'mock' and report['tooltips']:
                assert all(text['order'] != report['tooltips'][-1]['rendered_order'] for text in game.backend.texts), \
                    'The tooltip remained after the pointer left'

        def icon(label):
            item = control(label)
            assert item.icon and not item.show_text, f'{label} still renders as a text-only toolbar button'
            if backend == 'mock':
                x, y, width, height = item.bounds
                assert any(x <= image['x'] < x + width and y <= image['y'] < y + height
                           for image in game.backend.images), f'{label} has no rendered icon'
                assert not any(text['text'] == label and x <= text['x'] < x + width and y <= text['y'] < y + height
                               for text in game.backend.texts), f'{label} still draws its repeated label'
            return item

        def visit(label, shortcut=None):
            before, scene = state(), game.scene
            hover(icon(label))
            player.button(label)
            assert game.scene is not scene, f'{label} click did not open its screen'
            if backend == 'mock':
                assert all(text['order'] != report['tooltips'][-1]['rendered_order'] for text in game.backend.texts), \
                    'A covered toolbar tooltip leaked through its modal'
            opened = type(game.scene).__name__
            unchanged(before)
            if label in ('Hero', 'Save'):
                capture(label.lower() + '-modal')
            press('escape')
            assert game.scene is scene
            unchanged(before)
            hide_tip()
            if shortcut:
                press(shortcut)
                assert type(game.scene).__name__ == opened, f'{label} shortcut differs from its icon'
                press('escape')
                assert game.scene is scene
                unchanged(before)
            report['toolbar_visits'].append({'label': label, 'opened': opened, 'shortcut': shortcut,
                                             'reading_size': reading_scale(game)})

        def metric(name, expected_value, *, index=0, detail=None, collection='metrics'):
            rows = [item for item in game.scene.ui.walk() if isinstance(item, Row) and
                    any(isinstance(child, Image) and child.image == icon_path(name)
                        for child in item.children) and (detail is None or detail in (item.tooltip or ''))]
            assert len(rows) > index, f'No icon/value metric for {name} #{index}'
            row = rows[index]
            image = next(child for child in row.children if isinstance(child, Image))
            value = next(child for child in row.children if isinstance(child, Label))
            assert value.text == str(expected_value), f'{name} no longer shows its authoritative value'
            for item in (row, image, value):
                x, y, width, height = item.bounds
                assert 0 <= x < x + width <= game.width and 0 <= y < y + height <= game.height
            tip = hover(image, owner=row)
            assert hover(value, owner=row) == tip, f'{name} tooltip depends on hitting the tiny icon'
            report[collection].append({'scene': type(game.scene).__name__, 'name': name,
                                       'value': value.text, 'tooltip': tip,
                                       'reading_size': reading_scale(game)})

        def army_metrics():
            for index, troop in enumerate(player.state.hero.army, 1):
                metric('level', troop.level, index=index, collection='army_metrics')
                metric('health', f'{troop.hp}/{troop.max_hp}', index=index, collection='army_metrics')

        def travel_label(label):
            item = control(label)
            assert item.icon == icon_path('travel') and item.show_text
            if backend == 'mock':
                x, y, width, height = item.bounds
                assert any(text['text'] == label and x <= text['x'] < x + width and y <= text['y'] < y + height
                           for text in game.backend.texts), 'The contextual travel verb disappeared'
            report['travel_controls'].append({'label': label, 'reading_size': reading_scale(game)})

        def command_check(command, expected, via):
            assert state() == expected.to_json(), f'{command} {via} differs from the public command'
            report['command_checks'].append({'command': command, 'via': via,
                                             'after_sha256': hashlib.sha256(state().encode()).hexdigest()})
            budget.checkpoint()

        def capture(name):
            before = state()
            for _ in range(3):
                player._tick()
                budget.checkpoint()
            player.capture(name, settle=False)
            unchanged(before)
            report['captures'].append({'name': name, 'scene': type(game.scene).__name__,
                                       'reading_size': reading_scale(game)})

        def disabled(label, shortcut, capture_name):
            item = control(label)
            assert not item.enabled
            tip = hover(item)
            assert tip != item.text and len(tip) > len(item.text), 'Unavailable action has no explanation'
            before, scene = state(), game.scene
            aiming = scene.targeting
            capture(capture_name)
            x, y, width, height = item.bounds
            player.click(x + width / 2, y + height / 2)
            assert scene.targeting == aiming, 'An unavailable button entered aiming'
            press(shortcut)
            assert game.scene is scene
            assert scene.targeting == aiming, 'An unavailable shortcut entered aiming'
            unchanged(before)
            report['disabled_checks'].append({'label': label, 'shortcut': shortcut, 'tooltip': tip})
            hide_tip()

        try:
            game.push(TitleScene(seed=7, hero_class='Wizard'))
            player._tick()
            visit('Settings', 'o')
            visit('Text size', 't')
            capture('title-icons')
            player.button('Linked campaign')
            assert type(game.scene) is ShardScene
            s = player.state
            for name, value in {'gold': s.gold, 'crystals': s.crystals, 'income': f'+{s.income}',
                                'upkeep': f'−{s.upkeep}', 'level': s.hero.level, 'xp': s.hero.xp,
                                'actions': s.actions_left, 'health': f'{s.hero.hp} / {s.hero.max_hp}',
                                'mana': f'{s.hero.mana} / {s.hero.max_mana}'}.items():
                metric(name, value)
            army_metrics()
            hide_tip()
            capture('campaign-icons')
            metric('gold', s.gold)
            capture('campaign-gold-tooltip')
            hide_tip()
            for label, shortcut in (('Guide', 'f1'), ('Hero', 'h'), ('Codex', 'c'),
                                    ('Save', None), ('Load', 'f6'), ('Build stronghold', 'b'),
                                    ('Recruit troops', 'r'), ('Rival plan', 'v'), ('Campaign', 'j')):
                visit(label, shortcut)
            travel_label('Hero is here')
            before = state()
            destination = next(pos for pos in s.grid.neighbors(s.hero.pos)
                               if s.provinces[pos].owner == 'neutral')
            player.click(*player.root.grid.center(destination))
            travel_label('Invade province')
            unchanged(before)
            press('home')
            before = state()
            hover(icon('Text size'))
            player.button('Text size')
            press('right'); press('return')
            assert reading_scale(game) == 125
            unchanged(before)
            hide_tip()
            for label in ('Guide', 'Hero', 'Codex', 'Text size', 'Save', 'Load'):
                icon(label)
            for label, shortcut in (('Build stronghold', 'b'), ('Recruit troops', 'r'),
                                    ('Rival plan', 'v'), ('Campaign', 'j')):
                visit(label, shortcut)
            army_metrics()
            travel_label('Hero is here')
            hide_tip()
            capture('campaign-reading-125')
            hover(icon('End turn'))
            expected = State.from_json(state()); expected.end_turn()
            player.button('End turn')
            command_check('end_turn', expected, 'icon')
            before = state()
            player.reload(before)
            budget.checkpoint()
            expected = State.from_json(state()); expected.explore()
            hover(icon('Explore current province'))
            player.button('Explore current province')
            assert type(game.scene) is BattleScene
            command_check('explore', expected, 'icon')
            press('f9')
            assert type(game.scene) is ShardScene and state() == before
            report['comparison_loads'] += 1
            player.order('explore')
            assert type(game.scene) is BattleScene
            command_check('explore', expected, 'key X after baseline reload')
            selected = player.state.battle.unit(game.scene.selected)
            for name, value in {'health': f'{selected.hp} / {selected.max_hp}', 'attack': selected.attack,
                                'defense': selected.effective_defense, 'move': selected.effective_move_range,
                                'range': selected.attack_range, 'mana': player.state.battle.mana}.items():
                metric(name, value)
            hide_tip()
            for label in ('Guide', 'Codex', 'Save', 'Text size'):
                hover(icon(label))
            for spell, title in (('bolt', 'Arcane Bolt'), ('heal', 'Hero Heal')):
                cost = player.state.battle.spell_cost(spell)
                hover(icon(f'{title} · {cost} mana'))
                metric('mana', cost, detail=f'Cost per {title} cast.')
                report['spell_costs'].append({'spell': spell, 'cost': cost, 'reading_size': reading_scale(game)})
            hide_tip()
            capture('battle-icons')
            heal = next(item for item in game.scene.ui.walk() if isinstance(item, Button) and 'Heal ·' in item.text)
            disabled(heal.text, '2', 'disabled-heal-tooltip')
            archer = next(unit for unit in player.state.battle.units if unit.team == 'player' and unit.can_pin)
            archer_start = archer.pos
            expected = State.from_json(state()); expected.battle.move(archer.id, (-1, 0))
            player.order('battle.move', archer.id, (-1, 0))
            command_check('battle.move', expected, 'board click')
            target = player.state.battle.targets(archer.id)[0]
            expected.battle.attack(archer.id, target.id)
            player.order('battle.attack', archer.id, target.id)
            command_check('battle.attack', expected, 'board click')
            disabled('Pin', 'p', 'disabled-pin-tooltip')
            # The opening Bolt is out of range. The Archer has now cleared this
            # adjacent hex, so the hero can legally step forward before aiming.
            assert archer_start in player.state.battle.reachable(0)
            expected.battle.move(0, archer_start)
            player.order('battle.move', 0, archer_start)
            command_check('battle.move', expected, 'hero follows the Archer')
            bolt = f'Arcane Bolt · {player.state.battle.spell_cost("bolt")} mana'
            before = state()
            player.button(bolt)
            assert game.scene.targeting == 'bolt'
            click_targets = tuple(unit.id for unit in game.scene.action_targets())
            assert click_targets
            press('escape')
            assert game.scene.targeting is None
            press('1')
            assert game.scene.targeting == 'bolt'
            assert tuple(unit.id for unit in game.scene.action_targets()) == click_targets
            press('escape')
            assert game.scene.targeting is None
            unchanged(before)
            report['aiming_checks'].append({'label': 'Arcane Bolt', 'targets': click_targets, 'shortcut': '1'})
            militia = next(unit for unit in player.state.battle.units
                           if unit.team == 'player' and unit.kind == 'militia' and not unit.acted)
            player.click(*game.scene.grid.center(militia.pos))
            assert game.scene.selected == militia.id
            hover(icon('Guard'))
            expected.battle.guard(militia.id)
            player.button('Guard')
            command_check('battle.guard', expected, 'icon')
            player.reload(expected.to_json())
            hide_tip()
            capture('battle-reloaded')
            report.update(inputs=player.events, input_activations=len(player.events),
                          exact_save_reloads=player.reloads + report['comparison_loads'], final_state=state(),
                          final_reading_size=reading_scale(game))
        finally:
            game.close()
    assert _fingerprints() == report['source_sha256'], 'Sources or icon assets changed during capture'
    report.update(wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-icons'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    receipt = verify(args.output, backend=args.backend, budget=CpuBudget(args.cpu_percent))
    print(f'{len(receipt["captures"])} captures; {receipt["input_activations"]} inputs; '
          f'{receipt["exact_save_reloads"]} exact reloads ({args.backend}): {args.output}')
