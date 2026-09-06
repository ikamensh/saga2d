"""Review paid replacements, preserve saves, and use a purchased Warden in a real assault."""
from __future__ import annotations

import argparse
from dataclasses import asdict
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
from eador.model import RECRUITABLE, State
from eador.persistence import AUTO_SLOTS
from eador.preferences import reading_scale
from eador.replacement_scene import ReplacementScene
from eador.scene import CatalogScene, ShardScene
from tools.eador_campaign import finish_battle
from tools.eador_ui import PlayerInput
from tools.verify_eador_extraction import PlayerOrders
from tools.verify_eador_guidance import check_reading_layout


def earned_army():
    record = json.loads((ROOT / 'docs/evidence/crystal-service-comparison.examples.json').read_text())
    return State.from_json(json.dumps(record['late_full_roster']['state']))


def open_review(player, outgoing_id, kind, *, mouse=False):
    """Open the visible quote without executing the model command."""
    player.press('r')
    player.button('Replace troop') if mouse else player.press('m')
    assert isinstance(player.game.scene, ReplacementScene) and player.game.scene.kind is None
    check_reading_layout(player.game.scene)
    while outgoing_id not in player.game.scene.visible_troops:
        assert player.game.scene.page + 1 < player.game.scene.pages
        player.press('right')
    index = player.game.scene.visible_troops.index(outgoing_id)
    if mouse:
        controls = player.game.scene.ui.find_all(lambda item: isinstance(item, Button) and item.text == 'Choose')
        x, y, w, h = controls[index].bounds
        player.click(x + w / 2, y + h / 2)
    else:
        player.press(str(index + 1))
    assert isinstance(player.game.scene, CatalogScene)
    while kind not in player.game.scene.visible_items:
        player.press('right')
    if mouse:
        controls = player.game.scene.ui.find_all(lambda item: isinstance(item, Button) and item.text == 'Review')
        x, y, w, h = controls[player.game.scene.visible_items.index(kind)].bounds
        player.click(x + w / 2, y + h / 2)
    else:
        player.press(str(player.game.scene.visible_items.index(kind) + 1))
    assert isinstance(player.game.scene, ReplacementScene) and player.game.scene.kind == kind


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    sources = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'), *ROOT.glob('tools/*.py'),
               ROOT / 'docs/evidence/crystal-service-comparison.examples.json']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    native, metrics, purchases = backend == 'pyglet', [], []
    with TemporaryDirectory(prefix='shardbound-replacement-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=native, output=output)
        try:
            game.set_window_size((1280, 720))
            # Begin at a retained earned checkpoint, then pay for all further work through UI.
            for mouse in (False, True):
                game.clear_and_push(ShardScene(earned_army()))
                player.state.build('archery')
                player.state.build('mage_tower')
                before = player.state.to_json()
                quote = player.root.state.replacement_preview(1, 'warden')
                expected = State.from_json(before)
                expected.replace_troop(1, 'warden')
                open_review(player, 1, 'warden', mouse=mouse)
                for key in ('t', 'left', 'escape'):
                    player.press(key)
                entry_scale = reading_scale(game)
                for key in ('t', 'right', 'return', 'c', 'escape'):
                    player.press(key)
                assert reading_scale(game) == 125 and player.state.to_json() == before
                check_reading_layout(game.scene)
                player.capture(f'review-warden-{mouse}-125')
                player.press('escape')
                assert isinstance(game.scene, CatalogScene) and player.state.to_json() == before
                player.press(str(game.scene.visible_items.index('warden') + 1))
                player.button('Replace veteran') if mouse else player.press('return')
                assert game.scene.applied and player.state.to_json() == expected.to_json()
                after = player.state.to_json()
                player.press('1')
                assert player.state.to_json() == after
                check_reading_layout(game.scene)
                player.capture(f'applied-warden-{mouse}-125')
                purchases.append(dict(mouse=mouse, quote=asdict(quote), cancel_restored_scale=entry_scale))
                player.button('Return to shard')
                player.reload(after)

            # The saved fresh Warden brings an injured flank troop into the hero's Heal range.
            player.state.travel((2, 0))
            for _ in range(3):
                player.press('a')
            battle = player.state.battle
            assert battle.round == 4 and battle.unit(5).hp == 7
            assert battle.unit(5) not in battle.spell_targets('heal')
            play = PlayerOrders(player.state)
            player.capture('wounded-flank-before-swap')
            play.do('swap', 7, 5)
            battle = player.state.battle
            assert battle.unit(5) in battle.spell_targets('heal')
            hp = battle.unit(5).hp
            gain = battle.spell_preview('heal', 5)
            play.do('cast', 'heal', 5)
            assert player.state.battle.unit(5).hp == hp + gain and gain == 22
            player.capture('rescued-flank-after-heal')
            expected = State.from_json(player.state.to_json())
            finish_battle(expected)
            finish_battle(player.state)
            assert player.state.to_json() == expected.to_json() and player.state.status == 'victory'
            assert any(t.id == 5 for t in player.state.hero.army)
            player.capture('replacement-assault-victory')
            assault = dict(turn=player.state.turn, healed_troop=5, hp_gained=gain, orders=play.orders,
                           final_state_sha256=hashlib.sha256(player.state.to_json().encode()).hexdigest())

            funded = earned_army()
            funded.build('archery'); funded.build('mage_tower')
            for name, source in (('funded', funded), ('opening', State.new(7))):
                snapshot = source.to_json()
                for size in ((1280, 720), (1280, 800), (1920, 1080)):
                    game.set_window_size(size)
                    for percent in (100, 125):
                        for kind in RECRUITABLE:
                            game.clear_and_push(ShardScene(State.from_json(snapshot)))
                            open_review(player, source.hero.army[0].id, kind)
                            for key in ('t', 'left' if percent == 100 else 'right', 'return'):
                                player.press(key)
                            record = dict(case=name, kind=kind, percent=percent, window=game.window_size,
                                          quote=asdict(game.scene.quote), labels=check_reading_layout(game.scene))
                            metrics.append(record)
                            if record['quote']['blocked_reason']:
                                player.press('return')
                                control = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == 'Replace veteran')
                                assert not control.enabled
                                x, y, w, h = control.bounds
                                player.click(x + w / 2, y + h / 2)
                            assert player.state.to_json() == snapshot
                            if size == (1280, 720) and percent == 125 and kind in ('adept', 'skyrider'):
                                player.capture(f'{name}-{kind}-125')

            # A real filesystem error must fit alongside a complete paged roster or the longest role.
            game.set_window_size((1280, 720))
            manual = saves / 'save_1.json'
            saved_bytes = manual.read_bytes()
            manual.unlink()
            manual.mkdir()
            game.clear_and_push(ShardScene(earned_army()))
            player.press('r'); player.press('m'); player.press('f5')
            seen = []
            for page in range(game.scene.pages):
                check_reading_layout(game.scene)
                seen.extend(game.scene.visible_troops)
                player.capture(f'roster-file-error-125-page-{page + 1}')
                if page + 1 < game.scene.pages:
                    player.press('right')
            assert seen == [troop.id for troop in player.state.hero.army]
            player.press('escape')
            open_review(player, 1, 'skyrider')
            before = player.state.to_json()
            player.press('f5')
            check_reading_layout(game.scene)
            player.capture('skyrider-file-error-125')
            assert player.state.to_json() == before and manual.is_dir()
            manual.rmdir()
            manual.write_bytes(saved_bytes)

            # Real damaged autosaves preserve the already-applied consequence and manual recovery.
            game.clear_and_push(ShardScene(earned_army()))
            for slot in AUTO_SLOTS:
                (saves / f'save_{slot}.json').write_bytes(b'damaged autosave')
            open_review(player, 1, 'warden')
            player.press('return')
            after = player.state.to_json()
            assert game.scene.applied
            assert any('All autosave slots are damaged' in item.text
                       for item in game.scene.ui.find_all(lambda item: isinstance(item, Label)))
            check_reading_layout(game.scene)
            player.capture('replacement-save-error-125')
            player.press('f6'); player.press('1'); player.press('escape'); player.press('f9')
            assert isinstance(game.scene, ShardScene) and player.state.to_json() == after
            assert all((saves / f'save_{slot}.json').read_bytes() == b'damaged autosave' for slot in AUTO_SLOTS)
        finally:
            game._teardown()
        restarted = create_game(backend=backend, visible=False, save_dir=saves)
        try:
            assert reading_scale(restarted) == 125
            replay = PlayerInput(restarted, native=native, output=output)
            restarted.push(ShardScene(State.from_json(after)))
            replay.press('r'); replay.press('m')
            check_reading_layout(restarted.scene)
            replay.capture('restarted-roster-125')
            assert replay.state.to_json() == after
            events = player.events + replay.events
        finally:
            restarted._teardown()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  backend=backend, source_sha256=hashes, source_unchanged=True, input_activations=len(events),
                  exact_reloads=player.reloads, purchases=purchases, assault=assault, matrix=metrics, inputs=events)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Replacement passed ({backend}): {len(metrics)} reviews, {len(events)} inputs; {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-replacement'))
    parser.add_argument('--backend', choices=('pyglet', 'mock'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
