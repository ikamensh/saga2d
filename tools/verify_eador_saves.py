"""Read complete save slots, recover a backup and protect live play through real file errors."""
from __future__ import annotations

import argparse
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
from eador.model import State
from eador.preferences import reading_scale
from eador.scene import BattleScene, SaveScene, ShardScene, TitleScene
from tools.eador_linked_campaign import lose_shard, play_linked, play_stage, travel_selection
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


@cache
def prepared_saves():
    """Earn saved phases with public commands, and keep actual old fixture payloads."""
    state = State.new_campaign(7)
    states = [('opening', state.to_json())]
    state.explore()
    states.append(('battle', state.to_json()))
    while state.battle.outcome is None:
        state.battle.auto_turn()
    states.append(('result', state.to_json()))
    state.resolve_battle()
    assert state.choice is not None
    states.append(('choice', state.to_json()))
    departure = play_stage(State.new_campaign(7))
    states.append(('departure', departure.to_json()))
    departure.advance('rootward', **travel_selection(departure))
    lose_shard(departure)
    states.append(('recovery', departure.to_json()))
    lost = State.from_json(departure.to_json())
    lost.abandon_campaign()
    states.append(('lost', lost.to_json()))
    departure.recover(**travel_selection(departure))
    states.append(('recovered', departure.to_json()))
    states.append(('completed', play_linked().to_json()))
    states.append(('challenge', State.new_campaign(7, difficulty='challenge').to_json()))
    for filename in ('v1_campaign.json', 'v10_pinned_crossing.json'):
        states.append((filename, (ROOT / 'tests/eador/fixtures' / filename).read_text()))
    return tuple(states)


def show_slot(player, slot):
    for _ in range(player.game.scene.pages):
        if any(entry.slot == slot for entry in player.game.scene.visible_entries):
            return
        player.press('left' if slot < player.game.scene.visible_entries[0].slot else 'right')
    raise AssertionError(f'No reachable visible save slot {slot}')


def select_slot(player, slot, *, backup=False):
    show_slot(player, slot)
    number = str(next(index for index, entry in enumerate(player.game.scene.entries, 1) if entry.slot == slot))
    if not backup:
        player.press(number)
    elif player.native:
        from pyglet.window import key
        player.events.append(('SaveScene', 'key', 'shift+' + number))
        window = player.game.backend.window
        window.dispatch_event('on_key_press', getattr(key, '_' + number), key.MOD_SHIFT)
        window.dispatch_event('on_key_release', getattr(key, '_' + number), key.MOD_SHIFT)
        player.game.tick(1 / 60)
    else:
        player.events.append(('SaveScene', 'key', 'shift+' + number))
        player.game.backend.inject_key(number, shift=True)
        player.game.backend.inject_key(number, type='key_release', shift=True)
        player.game.tick(1 / 60)


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    sources = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'), *ROOT.glob('tools/*.py'),
               *ROOT.glob('tests/eador/fixtures/*.json')]
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    native, metrics = backend == 'pyglet', []
    with TemporaryDirectory(prefix='shardbound-save-reading-') as directory:
        saves_path = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves_path)
        player = PlayerInput(game, native=native, output=output)
        try:
            game.set_window_size((1280, 720))
            game.push(TitleScene(7))
            player.press('l'); player.press('f5')
            opening = player.state.to_json()
            player.press('x'); player.press('f5')
            live = player.state.to_json()
            player.press('f6')
            for key in ('t', 'right', 'escape'):
                player.press(key)
            assert reading_scale(game) == 100
            for key in ('t', 'right', 'return'):
                player.press(key)
                if key == 'right':
                    player.capture('save-settings-125')
            assert reading_scale(game) == 125 and player.state.to_json() == live
            check_reading_layout(game.scene)
            player.capture('live-battle-slots-125')
            player.button('Save slots'); select_slot(player, 2)
            assert game.scene.saves.load(2).to_json() == live
            player.button('Load slots')
            damaged = saves_path / 'save_1.json'
            damaged.write_text(json.dumps({'version': 'X' * 5000}))
            before_files = {path.name: path.read_bytes() for path in saves_path.iterdir()}
            select_slot(player, 1)
            assert isinstance(game.scene, SaveScene) and player.state.to_json() == live
            check_reading_layout(game.scene)
            player.capture('invalid-version-125')
            select_slot(player, 1, backup=True)
            assert isinstance(game.scene, ShardScene) and player.state.to_json() == opening
            assert {path.name: path.read_bytes() for path in saves_path.iterdir()} == before_files

            # The same real bad directory must not overflow load/save error footers.
            manual = saves_path / 'save_3.json'
            manual.mkdir()
            player.press('f6'); select_slot(player, 3)
            check_reading_layout(game.scene)
            player.capture('directory-load-error-125')
            player.button('Save slots'); select_slot(player, 3)
            check_reading_layout(game.scene)
            player.capture('directory-save-error-125')
            assert player.state.to_json() == opening and manual.is_dir()
            manual.rmdir()
            player.press('escape'); player.press('f1'); player.button('Save & title')
            select_slot(player, 1)
            assert isinstance(game.scene, SaveScene) and player.state.to_json() == opening
            check_reading_layout(game.scene)
            player.capture('failed-save-before-title-125')
            select_slot(player, 3)
            assert isinstance(game.scene, TitleScene)
            player.press('f6'); select_slot(player, 3)
            assert isinstance(game.scene, ShardScene) and player.state.to_json() == opening

            # This is a read-only layout matrix over actual saved phases, separate from the tracer.
            cases = prepared_saves()
            for batch in range(2):
                game.clear_and_push(ShardScene(State.new(7)))
                saves = player.root.saves
                for path in saves_path.iterdir():
                    path.unlink()  # Isolated verification files, replaced with this batch's earned phases.
                for index, (_, snapshot) in enumerate(cases[batch * 6:batch * 6 + 6]):
                    state = State.from_json(snapshot)
                    saves.save(state, index + 1) if index < 3 else saves.autosave(state)
                stored = {path.name: path.read_bytes() for path in saves_path.iterdir()}
                for window in ((1280, 720), (1280, 800), (1920, 1080)):
                    game.set_window_size(window)
                    for percent in (100, 125):
                        for mode in ('load', 'save', 'title'):
                            root = ShardScene(State.new(7))
                            game.clear_and_push(root)
                            game.push(SaveScene(root, mode='save' if mode == 'title' else mode, return_to_title=mode == 'title'))
                            for key in ('t', 'left' if percent == 100 else 'right', 'return'):
                                player.press(key)
                            seen = []
                            for page in range(game.scene.pages):
                                scene = game.scene
                                labels = [item.text for item in scene.ui.find_all(lambda item: isinstance(item, Label))]
                                for entry in scene.visible_entries:
                                    assert entry.detail in labels
                                hidden = next((entry for entry in scene.entries if entry not in scene.visible_entries), None)
                                if hidden:
                                    before = player.state.to_json()
                                    player.press(str(scene.entries.index(hidden) + 1))
                                    assert game.scene is scene and player.state.to_json() == before
                                seen.extend(entry.slot for entry in scene.visible_entries)
                                record = dict(batch=batch, mode=mode, percent=percent, window=game.window_size,
                                              page=page + 1, slots=[entry.slot for entry in scene.visible_entries],
                                              labels=check_reading_layout(scene))
                                metrics.append(record)
                                if window == (1280, 720) and mode == 'load':
                                    player.capture(f'batch-{batch}-{percent}-page-{page + 1}')
                                if page + 1 < scene.pages:
                                    player.press('right')
                            assert seen == [entry.slot for entry in game.scene.entries]
                            anchor = game.scene.visible_entries[0].slot
                            for key in ('t', 'left' if percent == 125 else 'right', 'return'):
                                player.press(key)
                            assert game.scene.visible_entries[0].slot == anchor
                            assert {path.name: path.read_bytes() for path in saves_path.iterdir()} == stored
            for key in ('t', 'right', 'return'):
                player.press(key)
            assert reading_scale(game) == 125
        finally:
            game._teardown()
        restarted = create_game(backend=backend, visible=False, save_dir=saves_path)
        try:
            assert reading_scale(restarted) == 125
            replay = PlayerInput(restarted, native=native, output=output)
            restarted.push(TitleScene(7)); replay.press('f6')
            check_reading_layout(restarted.scene)
            replay.capture('settings-restarted-slots')
            events = player.events + replay.events
        finally:
            restarted._teardown()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  backend=backend, source_sha256=hashes, source_unchanged=True, input_activations=len(events),
                  matrix=metrics, inputs=events, phases=[name for name, _ in cases])
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Save reading passed ({backend}): {len(metrics)} pages, {len(events)} inputs; {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-save-reading'))
    parser.add_argument('--backend', choices=('pyglet', 'mock'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
