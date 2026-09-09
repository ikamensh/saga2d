"""Bounded character-art input check: one fresh route and two fixed earned saves.

Native frames are visual evidence; the mock additionally compares rendered
miniatures with the public art renderer at each actual saved unit's position.
The specialty army's historical preparation used autoplay. No preparation,
autoplay, campaign matrix or rule injection runs in this verifier.
"""
import argparse
from collections import Counter
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

from eador import art
from eador.app import create_game
from eador.model import HERO_CLASSES, UNITS, State
from eador.preferences import reading_scale
from eador.scene import BattleScene, HeroScene, Screen, ShardScene, TitleScene
from eador.style import GOLD, MUTED
from eador.ui import hero_portrait_path, icon_path
from saga2d import Button, Image, Label, Row
from saga2d.testing.cpu_budget import CpuBudget
from tools.eador_sources import framework_sources, source_name
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout

EFFECTS = 'docs/evidence/presentation-pass/effects/verification.json.gz'
EQUIPMENT = 'tests/eador/fixtures/v11_relic_collection.json'
FIXED_SAVES = {
    EFFECTS: 'a4af40389cbf27f4dfa0e7138bfef0575bfcf4879bdcc5b1ff666d3a076ab4b3',
    EQUIPMENT: '1bcfd8d05fdfbcc0377a38aa2b203fcfcde24a5009ea518428a7dbb313780585',
}


def _fixed_states():
    blobs = {}
    for name, digest in FIXED_SAVES.items():
        blobs[name] = (ROOT / name).read_bytes()
        assert hashlib.sha256(blobs[name]).hexdigest() == digest, f'Changed earned source: {name}'
    report = json.loads(gzip.decompress(blobs[EFFECTS]))
    case = next(case for case in report['cases'] if case['name'] == 'melee')
    specialty = State.from_json(json.dumps(case['orders'][0]['before']))
    equipment = State.from_json(blobs[EQUIPMENT].decode())
    provenance = {'files': FIXED_SAVES, 'specialty_source': report['source_revision'],
                  'specialty_location': 'cases[name=melee].orders[0].before',
                  'preparation': 'Historically earned through public model commands including autoplay; loaded unchanged.'}
    return specialty, equipment, provenance


def _fingerprints():
    paths = {Path(__file__), ROOT / 'tools/eador_ui.py',
             ROOT / 'tools/verify_eador_guidance.py',
             *(ROOT / 'eador').glob('*.py'), *framework_sources(),
             *(ROOT / 'eador/assets').rglob('*.json'), *(ROOT / 'eador/assets/images').rglob('*.png'),
             *(ROOT / name for name in FIXED_SAVES)}
    return {source_name(path): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def _overlap(a, b):
    x, y, width, height = a
    ox, oy, ow, oh = b
    return x < ox + ow and ox < x + width and y < oy + oh and oy < y + height


def _portrait(game, hero_class, *, native=False):
    path = hero_portrait_path(hero_class)
    assert Path(path).is_absolute() and Path(path).name == hero_class.lower() + '.png'
    portraits = [item for item in game.scene.ui.walk() if isinstance(item, Image)
                 and Path(item.image).parent.name == 'heroes']
    assert len(portraits) == 1 and portraits[0].image == path, 'Portrait disagrees with selected class'
    portrait = portraits[0]
    x, y, width, height = portrait.bounds
    assert width > 0 and height > 0 and 0 <= x < x + width <= game.width and 0 <= y < y + height <= game.height
    for item in game.scene.ui.walk():
        if isinstance(item, (Button, Label)) and item.visible:
            assert not _overlap(portrait.bounds, item.bounds), f'Portrait covers {item.text}'
    check_reading_layout(game.scene)
    if isinstance(game.scene, TitleScene):
        assert game.scene.hero_class == hero_class
        assert any(item.text == HERO_CLASSES[hero_class].description for item in game.scene.ui.walk()
                   if isinstance(item, Label))
    elif isinstance(game.scene, HeroScene):
        hero = game.scene.root.state.hero
        assert hero.hero_class == hero_class
        for name, value in {'level': str(hero.level), 'health': f'{hero.hp}/{hero.max_hp}',
                            'mana': f'{hero.mana}/{hero.max_mana}'}.items():
            row = game.scene.ui.find(lambda item: isinstance(item, Row) and any(
                isinstance(child, Image) and child.image == icon_path(name) for child in item.children))
            assert row is not None, f'Hero has no {name} metric'
            label = next(child for child in row.children if isinstance(child, Label))
            assert label.text.replace(' ', '') == value, f'Hero {name} disagrees with the saved model'
    if not native:
        handle = game.assets.image(path)
        assert any(item['image'] == handle for item in game.backend.images), 'Portrait widget did not draw its image'
    return {'hero_class': hero_class, 'scene': type(game.scene).__name__, 'path': path,
            'bounds': portrait.bounds, 'reading_size': reading_scale(game)}


class Miniatures(Screen):
    """A diagnostic view of the public art API, without a fabricated game state."""
    def __init__(self, pieces=None):
        super().__init__()
        self.pieces = pieces

    def draw(self):
        if self.pieces is not None:
            for kind, team, x, y, scale, selected, spent in self.pieces:
                art.piece(self, x, y, kind, team, scale=scale, selected=selected, spent=spent)
            return
        self.text('CHARACTER SILHOUETTES', 32, 20, size=26, serif=True, color=GOLD)
        self.text('Diagnostic art sheet · battle / retinue / enemy selected & spent · no campaign state',
                  32, 58, size=12, color=MUTED)
        for index, kind in enumerate((*HERO_CLASSES, *UNITS)):
            x, y = 32 + index % 6 * 205, 100 + index // 6 * 222
            self.text(HERO_CLASSES[kind].name if kind in HERO_CLASSES else UNITS[kind].name, x, y, size=15)
            art.piece(self, x + 42, y + 102, kind, 'player', scale=1.15)
            art.piece(self, x + 124, y + 102, kind, 'player', scale=.53)
            art.piece(self, x + 84, y + 181, kind, 'enemy', scale=.85, selected=True, spent=True)


def _primitives(backend):
    return [(name, item) for name in ('polygons', 'lines', 'circles', 'rects')
            for item in getattr(backend, name)]


def _shape_key(name, item):
    return name, json.dumps({key: value for key, value in item.items() if key != 'order'}, sort_keys=True)


def _battle_identity(player):
    """Compare the actual board with public miniature rendering; preserve its model."""
    game, scene = player.game, player.game.scene
    assert type(scene) is BattleScene
    before = player.state.to_json()
    pieces, identities = [], []
    for unit in player.state.battle.units:
        if not unit.alive:
            continue
        kind = player.state.hero.hero_class if unit.id == 0 else unit.kind
        x, y = scene.grid.center(unit.pos)
        pieces.append((kind, unit.team, x, y + scene.grid.size * .22, min(1, scene.grid.size / 56),
                       unit.id == scene.selected, unit.acted))
        identities.append({'id': unit.id, 'kind': kind, 'team': unit.team, 'hp': unit.hp})
    check_reading_layout(scene)
    if not player.native:
        drawn = _primitives(game.backend)
        actual = Counter(_shape_key(name, item) for name, item in drawn)
        health = []
        for unit in player.state.battle.units:
            if unit.alive:
                x, y = scene.grid.center(unit.pos)
                health.append(next(text for text in game.backend.texts if text['text'] == str(unit.hp)
                                   and abs(text['x'] - x) < .01
                                   and y <= text['y'] <= y + scene.grid.size))
        game.push(Miniatures(pieces)); player._tick()
        expected = Counter(_shape_key(name, item) for name, item in _primitives(game.backend))
        assert not expected - actual, 'The board draws a different miniature than the saved unit kind/class'
        body_orders = [item['order'] for name, item in drawn if _shape_key(name, item) in expected]
        assert body_orders and all(text['order'] > max(body_orders) for text in health), 'Miniatures cover persistent HP'
        game.pop(); player._tick()
    assert player.state.to_json() == before
    return identities


def verify_class_carryover(output, hero_class):
    """Tiny mock tracer: actual class input, modal portrait, battle art and exact saves."""
    game = create_game(backend='mock', visible=False, save_dir=Path(output) / 'saves')
    player = PlayerInput(game, finish_actions=False)
    try:
        game.push(TitleScene(seed=7)); player._tick()
        player.button(hero_class)
        _portrait(game, hero_class)
        player.press('return')
        expected = State.new(7, hero_class).to_json()
        assert player.state.to_json() == expected
        player.press('h'); _portrait(game, hero_class)
        assert type(game.scene) is HeroScene and player.state.to_json() == expected
        player.press('escape'); player.press('x')
        _battle_identity(player)
        before = player.state.to_json()
        player.reload(before)
        assert player.state.hero.hero_class == hero_class
        return {'hero_class': hero_class, 'exact_reloads': player.reloads}
    finally:
        game.close()


def verify(output, *, backend='pyglet', budget=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    budget = budget or CpuBudget(25)
    started, cpu_started = time.monotonic(), time.process_time()
    specialty, equipment, provenance = _fixed_states()
    report = {'scope': 'Directed character presentation; silent audio; one fresh Wizard route plus fixed earned saves.',
              'source_revision': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
              'dirty_at_start': subprocess.check_output(['git', 'status', '--short'], cwd=ROOT, text=True).splitlines(),
              'source_sha256': _fingerprints(), 'provenance': provenance, 'captures': [],
              'portraits': [], 'title_classes': [], 'boards': [], 'cpu_percent_requested': budget.percent}
    with TemporaryDirectory(prefix='shardbound-characters-') as directory:
        game = create_game(backend=backend, visible=False, save_dir=Path(directory) / 'saves')
        player = PlayerInput(game, native=backend == 'pyglet', output=output, finish_actions=False)

        def state():
            return player.state.to_json() if any(isinstance(scene, ShardScene) for scene in game.scenes) else None

        def portrait(hero_class):
            report['portraits'].append(_portrait(game, hero_class, native=player.native))

        def capture(name):
            before = state()
            for _ in range(2):
                player._tick(); budget.checkpoint()
            player.capture(name, settle=False)
            assert state() == before
            report['captures'].append({'name': name, 'scene': type(game.scene).__name__, 'reading_size': reading_scale(game)})
            budget.checkpoint()

        def reading(percent, *, cancel=False):
            before, scene, old = state(), game.scene, reading_scale(game)
            player.button('Text size')
            player.press('right' if percent > old else 'left')
            player.press('escape' if cancel else 'return')
            assert game.scene is scene and state() == before
            assert reading_scale(game) == (old if cancel else percent)
            budget.checkpoint()

        try:
            game.push(TitleScene(seed=7)); player._tick()
            for hero_class in HERO_CLASSES:
                player.button(hero_class); portrait(hero_class)
                report['title_classes'].append(hero_class)
                capture('title-' + hero_class.lower())
                player.press('tab')
                next_class = tuple(HERO_CLASSES)[(tuple(HERO_CLASSES).index(hero_class) + 1) % len(HERO_CLASSES)]
                portrait(next_class)
            player.button('Wizard')
            reading(125, cancel=True); portrait('Wizard')
            reading(125); portrait('Wizard'); capture('title-wizard-125')
            reading(100)
            player.press('return')
            expected = State.new(7, 'Wizard').to_json()
            assert state() == expected
            player.press('h'); portrait('Wizard'); capture('hero-wizard-100')
            reading(125); portrait('Wizard'); capture('hero-wizard-125')
            player.press('escape')
            assert state() == expected
            reading(100)
            player.press('x')
            report['boards'].append(_battle_identity(player)); capture('battle-fresh-100')
            before = state()
            for ident in (1, 3, 0):
                player.click(*game.scene.grid.center(player.state.battle.unit(ident).pos))
                assert game.scene.selected == ident and state() == before
            player.press('tab')
            assert game.scene.selected != 0 and state() == before
            reading(125)
            report['boards'].append(_battle_identity(player)); capture('battle-fresh-125')
            archer = next(unit for unit in player.state.battle.units if unit.team == 'player' and unit.can_pin)
            expected = State.from_json(state()); expected.battle.move(archer.id, (-1, 0))
            player.order('battle.move', archer.id, (-1, 0))
            target = player.state.battle.targets(archer.id)[0]
            expected.battle.attack(archer.id, target.id)
            player.order('battle.attack', archer.id, target.id)
            assert state() == expected.to_json()
            for _ in range(20):
                player._tick(); budget.checkpoint()
            capture('battle-contact-125')
            # One ordinary enemy phase brings a legal two-hex basic magic shot
            # into reach on this same fresh shard; no separate preparation.
            expected.battle.end_turn()
            player.order('battle.end_turn'); player.finish_playback()
            assert state() == expected.to_json()
            battle = player.state.battle
            wizard = battle.unit(0)
            firing = [(pos, enemy) for pos in sorted(battle.reachable(wizard.id) | {wizard.pos})
                      for enemy in battle.units if enemy.team == 'enemy' and enemy.alive
                      and battle.grid.distance(pos, enemy.pos) == 2 and battle.has_sight(pos, enemy.pos)]
            assert firing, 'The fresh Wizard has no legal two-hex firing position'
            pos, target = firing[0]
            if pos != wizard.pos:
                expected.battle.move(wizard.id, pos)
                player.order('battle.move', wizard.id, pos)
                assert state() == expected.to_json()
            shot_before = state()
            expected.battle.attack(wizard.id, target.id)
            player.order('battle.attack', wizard.id, target.id)
            assert state() == expected.to_json()
            for _ in range(6):
                player._tick(); budget.checkpoint()
            capture('wizard-basic-projectile-125')
            report['wizard_basic_shot'] = {'actor': wizard.id, 'target': target.id, 'position': pos,
                                           'before': json.loads(shot_before), 'after': json.loads(state())}
            player.reload(expected.to_json())
            report['boards'].append(_battle_identity(player)); capture('battle-reloaded-125')

            game.clear_and_push(ShardScene(specialty)); player._tick()
            before = state()
            report['boards'].append(_battle_identity(player))
            report['specialist_kinds'] = sorted({unit.kind for unit in player.state.battle.units if unit.alive})
            for unit in player.state.battle.units:
                if unit.alive and unit.team == 'player':
                    player.click(*game.scene.grid.center(unit.pos))
                    assert game.scene.selected == unit.id and state() == before
                    check_reading_layout(game.scene)
                    budget.checkpoint()
            capture('earned-specialists-125')
            player.reload(before)
            assert state() == before

            game.clear_and_push(ShardScene(equipment)); player._tick()
            # A historical victorious campaign opens its result overlay first.
            game.push(HeroScene(player.root)); player._tick()
            before = state()
            report['equipment_inventory'] = list(equipment.inventory)
            seen = []
            while True:
                portrait(equipment.hero.hero_class)
                seen.extend(game.scene.visible_relics)
                capture(f'earned-equipment-125-page-{game.scene.page + 1}')
                if game.scene.page + 1 == game.scene.pages:
                    break
                player.button('Next')
            assert seen == list(equipment.inventory) and state() == before
            report['equipment_seen'] = seen
            game.clear_and_push(Miniatures()); player._tick(); capture('miniature-contact-sheet')
            report.update(inputs=player.events, input_activations=len(player.events), exact_reloads=player.reloads,
                          reading_sizes=[100, 125])
        finally:
            game.close()
    assert _fingerprints() == report['source_sha256'], 'Runtime or character assets changed during capture'
    report.update(source_unchanged=True, wall_seconds=time.monotonic() - started,
                  cpu_seconds=time.process_time() - cpu_started)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-characters'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    parser.add_argument('--cpu-percent', type=float, default=25)
    args = parser.parse_args()
    receipt = verify(args.output, backend=args.backend, budget=CpuBudget(args.cpu_percent))
    print(f'{len(receipt["captures"])} captures; {receipt["input_activations"]} inputs; '
          f'{receipt["exact_reloads"]} exact reloads ({args.backend}): {args.output}')
