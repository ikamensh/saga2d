"""Read modal icon/value pairs through the same bounded mock/native inputs.

Two fresh Wizard/Standard/Frontier7 starts and one paid Barracks purchase.
The Observatory briefing is a separate public-model preparation using autoplay;
it is neither part of those fresh UI routes nor independent player evidence.
"""
import argparse
from collections import Counter
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
from eador.encounter_scene import EncounterScene
from eador.model import BUILDINGS, State, UNITS
from eador.preferences import reading_scale
from eador.rival_scene import RivalScene
from eador.scene import CatalogScene, HeroScene, ShardScene, TitleScene
from eador.ui import icon_path
from saga2d import Button, Image, Label, Row
from tools.cpu_budget import CpuBudget
from tools.eador_observatory_campaign import prepare_observatory
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout

NAMES = dict(gold='Gold', crystals='Crystals', income='Income', upkeep='Upkeep',
             level='Level', health='Health', mana='Mana', actions='Campaign actions',
             attack='Attack', range='Attack range')


def expected_metrics(scene):
    """Read the actual quoted prices, stats and rewards, independently of UI rows."""
    state, result = scene.root.state, []
    hero = state.hero
    if isinstance(scene, CatalogScene):
        result = [('gold', state.gold), ('crystals', state.crystals)]
        for name in scene.visible_items:
            spec = BUILDINGS[name] if scene.kind == 'build' else UNITS[name]
            if scene.kind == 'recruit':
                result += [('health', spec.hp), ('attack', spec.attack),
                           ('range', spec.attack_range), ('upkeep', spec.upkeep)]
            result += [('gold', spec.cost if scene.kind == 'build' else state.recruit_cost(name)),
                       ('crystals', spec.crystals if scene.kind == 'build' else state.recruit_crystal_cost(name))]
    elif isinstance(scene, HeroScene):
        quote = state.infusion_preview()
        result = [('level', hero.level), ('health', f'{hero.hp}/{hero.max_hp}'),
                  ('mana', f'{hero.mana}/{hero.max_mana}'), ('mana', f'+{quote.mana}'),
                  ('crystals', quote.crystals), ('actions', quote.actions),
                  ('crystals', state.crystals), ('actions', state.actions_left)]
    elif isinstance(scene, RivalScene):
        rival = state.rival
        result = [('gold', rival.gold), ('income', f'+{rival.income(state)}'), ('upkeep', f'−{rival.upkeep}')]
        result += [('health', f'{troop.hp}/{troop.max_hp}') for troop in rival.army if troop.id in scene.visible_troops]
    else:
        assert isinstance(scene, EncounterScene) and scene.kind == 'site'
        province = scene.province
        result = [('actions', 1), ('actions', state.actions_left), ('gold', state.gold), ('crystals', state.crystals),
                  ('gold', province.site_gold + (scene.approach.bonus_gold if scene.approach else 0)),
                  ('crystals', province.site_crystals),
                  ('health', f'{sum(province.site_guard_hp)}/{sum(UNITS[kind].hp for kind in scene.guards)}')]
    return Counter((name, str(value)) for name, value in result)


class PacedInput(PlayerInput):
    def __init__(self, game, budget, **options):
        super().__init__(game, finish_actions=False, **options)
        self.budget = budget

    def _tick(self):
        super()._tick()  # PlayerInput already caps every native frame at 30 FPS.
        self.budget.checkpoint()


def verify(output, *, backend='pyglet', budget=None):
    output = Path(output).resolve()
    if output.exists() and any(output.iterdir()):
        raise FileExistsError('Choose an empty output directory to preserve earlier receipts')
    output.mkdir(parents=True, exist_ok=True)
    budget = CpuBudget(25) if budget is None else budget
    started, cpu_started = time.monotonic(), time.process_time()
    paths = {Path(__file__).resolve(), *(ROOT / 'eador').glob('*.py'), *(ROOT / 'saga2d').rglob('*.py'),
             *(ROOT / 'tools').glob('eador_*.py'), ROOT / 'tools/cpu_budget.py', ROOT / 'tools/verify_eador_guidance.py'}
    paths.update(path for path in (ROOT / 'eador/assets').rglob('*') if path.is_file())
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}
    report = dict(source_revision=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  dirty_at_start=subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
                  source_sha256=hashes, backend=backend, cpu_percent_requested=budget.percent, native_fps=30,
                  scope=__doc__, cases=[], purchases=[])
    prepared = prepare_observatory(budget=budget).to_json()
    report['briefing_preparation'] = dict(helper='prepare_observatory', public_model=True, autoplay=True, state=prepared)
    with TemporaryDirectory(prefix='shardbound-modal-icons-') as temporary:
        for percent in (100, 125):
            game = create_game(backend=backend, visible=False, save_dir=Path(temporary) / str(percent) / 'saves')
            player = PacedInput(game, budget, native=backend == 'pyglet', output=output)
            case = dict(reading_size=percent, panels=[], tooltips=[], utilities=[], captures=[])

            def unchanged(before):
                assert player.state.to_json() == before, 'Reading or navigation changed the campaign'

            def move(x, y):
                before = player.state.to_json()
                player.events.append((type(game.scene).__name__, 'hover', (round(x), round(y))))
                if player.native:
                    window = game.backend.window
                    scale = min(window.width / game.width, window.height / game.height)
                    px = (window.width - game.width * scale) / 2 + x * scale
                    py = (window.height - game.height * scale) / 2 + (game.height - y) * scale
                    window.dispatch_event('on_mouse_motion', round(px), round(py), 0, 0)
                else:
                    game.backend.inject_mouse_move(round(x), round(y))
                player._tick(); unchanged(before)

            def hover(item, owner):
                tip = owner.tooltip() if callable(owner.tooltip) else owner.tooltip
                tip = tip or (owner.text if isinstance(owner, Button) else None)
                assert tip and tip.strip()
                x, y, width, height = item.bounds
                assert 0 <= x < x + width <= game.width and 0 <= y < y + height <= game.height
                move(x + width / 2, y + height / 2)
                assert game.theme.get_text_style('body').font_size == round(14 * percent / 100)
                if backend == 'mock':
                    order = max(text['order'] for text in game.backend.texts)
                    texts = [text for text in game.backend.texts if text['order'] == order]
                    assert ' '.join(' '.join(text['text'] for text in texts).split()) == ' '.join(tip.split()), 'Missing or duplicated tooltip'
                    assert all(text['font_size'] == round(14 * percent / 100) for text in texts)
                case['tooltips'].append(dict(scene=type(game.scene).__name__, target=type(item).__name__, text=tip))

            def panel():
                scene, actual = game.scene, Counter()
                labels = check_reading_layout(scene)
                if isinstance(scene, EncounterScene):
                    categories = [scene.ui.find(lambda item: isinstance(item, Label) and item.text == text)
                                  for text in ('Entry', 'Available')]
                    assert categories[0].bounds[3] == categories[1].bounds[3], 'A short resource heading broke across lines'
                for row in scene.ui.walk():
                    if not isinstance(row, Row) or not row.visible:
                        continue
                    icons = [child for child in row.children if isinstance(child, Image) and child.image in {icon_path(name) for name in NAMES}]
                    if not icons:
                        continue
                    values = [child for child in row.children if isinstance(child, Label)]
                    assert len(icons) == len(values) == 1, 'A metric must have one icon and one value'
                    icon, value = icons[0], values[0]
                    name = Path(icon.image).stem
                    semantic = f'{NAMES[name]}: {value.text}'
                    assert row.tooltip == semantic or (row.tooltip or '').startswith(semantic + '. ')
                    actual[name, value.text] += 1
                    hover(icon, row); hover(value, row)
                assert actual == expected_metrics(scene), (type(scene).__name__, actual, expected_metrics(scene))
                case['panels'].append(dict(scene=type(scene).__name__, page=getattr(scene, 'page', 0), labels=labels,
                                           metrics=[dict(name=name, value=value, count=count) for (name, value), count in actual.items()]))

            def capture(name, *, clean=True):
                if clean:
                    move(2, 2)
                player.capture(f'{name}-{percent}', settle=False)
                case['captures'].append(dict(file=f'{name}-{percent}.png', scene=type(game.scene).__name__))

            def utility(label, key):
                scene, before, selected = game.scene, player.state.to_json(), player.root.selected
                item = scene.ui.find(lambda item: isinstance(item, Button) and item.text == label)
                assert item is not None and item.icon and not item.show_text
                hover(item, item)
                player.button(label); opened = type(game.scene).__name__
                assert opened == {'Text size': 'SettingsScene', 'Codex': 'CodexScene'}[label]
                unchanged(before); player.press('escape')
                assert game.scene is scene
                player.press(key); assert type(game.scene).__name__ == opened
                unchanged(before); player.press('escape')
                assert game.scene is scene and player.root.selected == selected
                unchanged(before)
                case['utilities'].append(dict(label=label, shortcut=key, opened=opened))

            try:
                game.push(TitleScene(seed=7)); player._tick()
                player.button('Wizard'); player.press('return')
                fresh = player.state.to_json()
                assert fresh == State.new(7, 'Wizard').to_json()
                player.button('Text size'); player.press('right' if percent == 125 else 'left'); player.button('Apply')
                assert reading_scale(game) == percent
                for label, name in (('Build stronghold', 'build'), ('Recruit troops', 'recruit'), ('Hero', 'hero'), ('Rival plan', 'rival')):
                    player.button(label)
                    scene, seen = game.scene, []
                    for page in range(scene.pages):
                        panel()
                        if page == 0:
                            capture(name)
                        if isinstance(scene, CatalogScene):
                            seen.extend(scene.visible_items)
                        if page + 1 < scene.pages:
                            player.press('right')
                    if isinstance(scene, CatalogScene):
                        assert seen == scene.items
                    utility('Text size', 't')
                    if isinstance(scene, HeroScene):
                        utility('Codex', 'c')
                    player.press('escape'); unchanged(fresh)
                if percent == 125:
                    expected = State.from_json(fresh); expected.build('barracks')
                    player.order('build', 'barracks')
                    unchanged(expected.to_json()); player.reload(expected.to_json())
                    report['purchases'].append(dict(command='build', args=['barracks'], before=fresh, after=expected.to_json()))
                game.clear_and_push(ShardScene(State.from_json(prepared))); player._tick(); player.press('x')
                assert isinstance(game.scene, EncounterScene)
                panel(); capture('observatory')
                row = game.scene.ui.find(lambda item: isinstance(item, Row) and (item.tooltip or '').startswith('Health:'))
                hover(next(child for child in row.children if isinstance(child, Label)), row)
                capture('defender-health-explanation', clean=False)
                utility('Text size', 't'); utility('Codex', 'c')
                player.press('escape'); unchanged(prepared)
                case.update(inputs=player.events, input_count=len(player.events), exact_reloads=player.reloads)
                report['cases'].append(case)
            finally:
                game.close()
    assert hashes == {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in hashes}, 'Sources changed during verification'
    report.update(source_unchanged=True, wall_seconds=time.monotonic() - started, cpu_seconds=time.process_time() - cpu_started)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    receipt = verify(args.output, backend=args.backend, budget=CpuBudget(args.cpu_percent))
    print(json.dumps(dict(cases=len(receipt['cases']), inputs=sum(case['input_count'] for case in receipt['cases']),
                          captures=sum(len(case['captures']) for case in receipt['cases']), source_unchanged=True)))
