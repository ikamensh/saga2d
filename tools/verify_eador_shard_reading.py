"""Read actual campaign HUD states and issue their unchanged public map commands."""
from __future__ import annotations

import argparse
from collections import Counter
from functools import cache
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

from saga2d import Button, Label
from eador.app import create_game
from eador.model import State, UNITS
from eador.preferences import reading_scale
from eador.rival_scene import rival_order
from eador.scene import BattleScene, ShardScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout
from tools.verify_eador_rival_reading import prepared_rivals


@cache
def prepared_shards():
    """Earn supply pressure and a complete control army; load untouched historical records."""
    from tools.eador_control_campaign import prepare_control_watch
    from tools.verify_eador_replacement import earned_army
    cases = list(prepared_rivals())
    control = prepare_control_watch()
    control.retreat()
    assert len(control.hero.army) == control.hero.max_army
    cases.append(('paid-full-army', control.to_json()))
    cases.append(('paid-late-army', earned_army().to_json()))
    cases.append(('linked-opening', State.new_campaign(7).to_json()))
    poor = State.new(7)
    poor.build('barracks'); poor.build('archery')
    assert poor.gold == 0
    cases.append(('paid-zero-gold', poor.to_json()))
    dry = State.new(7, 'Wizard', difficulty='challenge')
    dry.build('mage_tower')
    assert dry.crystals == 0
    cases.append(('paid-zero-crystals', dry.to_json()))
    exhausted = State.new(7, 'Wizard')
    for _ in range(exhausted.actions_left):
        exhausted.explore(); exhausted.retreat()
    assert exhausted.actions_left == 0
    cases.append(('paid-no-actions', exhausted.to_json()))
    for name, snapshot in cases:
        state = State.from_json(snapshot)
        assert state.status == 'playing' and state.battle is None and state.choice is None, name
    return tuple(cases)


def check_shard(scene):
    """All facts remain exact; every province center stays clickable outside the HUD."""
    assert isinstance(scene, ShardScene)
    labels = check_reading_layout(scene)
    text = '\n'.join(item.text for item in scene.ui.walk() if isinstance(item, Label))
    state, province = scene.state, scene.state.provinces[scene.selected]
    required = [province.name, f'{state.gold} gold', f'{state.crystals} crystals',
                f'Income +{state.income}', f'Upkeep −{state.upkeep}',
                f'{state.rules.gold_percent}% of base production',
                f'Level {state.hero.level}', f'{state.hero.xp} XP', f'{state.actions_left} actions left',
                f'Health {state.hero.hp}/{state.hero.max_hp}', f'Mana {state.hero.mana}/{state.hero.max_mana}',
                f'At {state.provinces[state.hero.pos].name}', f'Turn {state.turn}',
                state.rules.title.upper(), rival_order(state)]
    for phrase in required:
        assert phrase in text, (phrase, text)
    if state.encircled:
        assert 'WESTWATCH ENCIRCLED' in text
    if state.upkeep_shortfall:
        assert f'{state.upkeep_shortfall} gold short: unpaid troops will leave.' in text
    if state.rival.army and scene.selected == state.rival.pos:
        assert f'Expedition: {len(state.rival.army)} troops' in text
    elif province.owner != 'player':
        assert all(f'{count} {UNITS[kind].name}' in text for kind, count in Counter(province.guards).items())
    for troop in state.hero.army:
        assert UNITS[troop.kind].name in text and f'{troop.hp}/{troop.max_hp}' in text
    controls = scene.ui.find_all(lambda item: isinstance(item, Button))
    for pos in state.provinces:
        x, y = scene.grid.center(pos)
        assert scene.grid.cell_at(x, y) == pos
        assert all(not (bx <= x <= bx + bw and by <= y <= by + bh)
                   for bx, by, bw, bh in [c.bounds for c in controls])
    return labels


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    sources = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'), *ROOT.glob('tools/*.py')]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    matrix, retained = [], {'standard-opening', 'paid-full-army', 'saved-encircled',
                           'linked-opening', 'saved-challenge-1', 'standard-announced-attack'}
    with TemporaryDirectory(prefix='shardbound-map-reading-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            game.push(ShardScene(State.new(7, 'Wizard')))
            player.click(*player.root.grid.center((-1, 0)))
            before = player.state.to_json()
            player.press('f2'); player.press('right'); player.press('return')
            assert player.root.selected == (-1, 0) and player.state.to_json() == before
            expected = State.from_json(before); expected.travel((-1, 0))
            player.button('Invade province')
            assert isinstance(game.scene, BattleScene) and player.state.to_json() == expected.to_json()
            player.capture('unchanged-battle-art')
            player.reload(expected.to_json())
            expected.retreat(); player.press('t')
            assert player.state.to_json() == expected.to_json()
            expected.end_turn(); player.button('End turn')
            assert player.state.to_json() == expected.to_json()
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                for percent in (100, 125):
                    for name, snapshot in prepared_shards():
                        game.clear_and_push(ShardScene(State.from_json(snapshot)))
                        for key in ('f2', 'left' if percent == 100 else 'right', 'return'):
                            player.press(key)
                        assert reading_scale(game) == percent
                        root = player.root
                        # All selected descriptions, including the actual distant final garrison.
                        for pos in root.state.provinces:
                            player.click(*root.grid.center(pos))
                            assert root.selected == pos and root.state.to_json() == snapshot
                            matrix.append(dict(case=name, rules_id=root.state.rules_id, selected=pos,
                                               window=game.window_size, percent=percent,
                                               labels=check_shard(root)))
                        player.press('home')
                        if size == (1280, 720) and name in retained and (percent == 125 or name == 'standard-opening'):
                            player.capture(f'{name}-{percent}')
                        # Settings and other read-only overlays preserve live selection.
                        player.press('tab'); selected = root.selected
                        player.press('f2'); player.press('left'); player.press('escape')
                        assert reading_scale(game) == percent and root.selected == selected
                        for key in ('h', 'c', 'v', 'f1'):
                            player.press(key); player.press('escape')
                            assert game.scene is root and root.selected == selected and root.state.to_json() == snapshot
                        player.reload(snapshot)
                        assert isinstance(game.scene, ShardScene)
            last_snapshot = player.state.to_json()
            events, reloads = len(player.events), player.reloads
        finally:
            game._teardown(); game.backend.quit()
        game = create_game(backend=backend, visible=False, save_dir=saves)
        try:
            game.push(ShardScene(State.from_json(last_snapshot)))
            game.tick(1 / 60)
            assert reading_scale(game) == 125
            check_shard(game.scene)
        finally:
            game._teardown(); game.backend.quit()
    with TemporaryDirectory(prefix='shardbound-map-error-') as directory:
        saves = Path(directory)
        for index in range(9):
            saves /= f'ordinary-directory-{index}-' + 'a' * 70
        saves.mkdir(parents=True)
        occupied = saves / 'save_1.json'; occupied.mkdir()
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=backend == 'pyglet', output=output)
        try:
            from eador.diagnostics import DiagnosticScene
            game.push(ShardScene(State.new(7)))
            player.click(*player.root.grid.center((-1, 0)))
            before = player.state.to_json()
            player.press('f5'); player.capture('complete-message-link')
            player.press('d')
            assert isinstance(game.scene, DiagnosticScene)
            player.press('t'); player.press('right'); player.press('return')
            assert str(occupied) in game.scene.message
            message = game.scene.message
            error_pages = game.scene.pages
            parts = []
            for page in range(error_pages):
                check_reading_layout(game.scene)
                parts.append(game.scene.ui.find(lambda c: isinstance(c, Label) and c.text in message).text)
                player.capture(f'complete-message-{page + 1}')
                if page + 1 < error_pages:
                    player.press('pagedown')
            assert ''.join(parts) == message
            for key in ('1', 'space', 'f5', 'f9'):
                player.press(key)
            player.button('Return to map')
            assert player.root.selected == (-1, 0) and player.state.to_json() == before and occupied.is_dir()
            player.button('Read message')
            assert game.scene.message == message
            player.press('escape')
            events += len(player.events)
        finally:
            game._teardown(); game.backend.quit()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, backend=backend, layouts=matrix,
                  input_activations=events, exact_save_reloads=reloads, complete_message_pages=error_pages)
    (output / 'matrix.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Shard reading passed ({backend}): {len(matrix)} layouts / {events} inputs / {reloads} exact reloads')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-hud-reading'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
