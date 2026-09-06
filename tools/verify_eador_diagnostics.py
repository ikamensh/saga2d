"""Read real long-path file errors without losing slots, quotes or applied decisions."""
from __future__ import annotations

import argparse
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

from saga2d import Label, SaveManager
from eador.app import create_game
from eador.diagnostics import DiagnosticScene
from eador.model import State
from eador.persistence import CampaignSaves
from eador.preferences import reading_scale
from eador.replacement_scene import ReplacementScene
from eador.scene import SaveScene, ShardScene
from eador.style import RED
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout
from tools.verify_eador_replacement import earned_army, open_review
from tools.verify_eador_saves import select_slot


def queued_keys(player, names):
    """Dispatch one actual input batch to prove the popped overlay protects the scene below."""
    for name in names:
        player.events.append((type(player.game.scene).__name__, 'queued key', name))
        if player.native:
            from pyglet.window import key
            symbol = getattr(key, 'ENTER' if name == 'return' else '_' + name if name.isdigit() else name.upper())
            for event in ('on_key_press', 'on_key_release'):
                player.game.backend.window.dispatch_event(event, symbol, 0)
        else:
            player.game.backend.inject_key(name)
            player.game.backend.inject_key(name, type='key_release')
    player.game.tick(1 / 60)


def read_all(player, metrics, name, *, capture=False):
    scene = player.game.scene
    assert isinstance(scene, DiagnosticScene)
    while scene.page:
        player.press('pageup')
    parts = []
    for index in range(scene.pages):
        check_reading_layout(scene)
        text = next(item.text for item in scene.ui.find_all(lambda item: isinstance(item, Label))
                    if item.style.text_color == RED)
        parts.append(text)
        metrics.append(dict(case=name, window=player.game.window_size, scale=reading_scale(player.game),
                            page=index + 1, pages=scene.pages, characters=len(text)))
        if capture:
            player.capture(f'{name}-page-{index + 1}')
        if index + 1 < scene.pages:
            player.press('pagedown')
    assert ''.join(parts) == scene.message
    return scene.message


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    sources = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'), *ROOT.glob('tools/*.py'),
               ROOT / 'docs/evidence/crystal-service-comparison.examples.json']
    hashes = {str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest() for path in sources}
    native, metrics = backend == 'pyglet', []
    with TemporaryDirectory(prefix='shardbound-long-diagnostic-') as temporary:
        directory = Path(temporary)
        for index in range(9):
            directory /= f'ordinary-directory-name-{index}-' + 'a' * 70
        directory.mkdir(parents=True)
        assert len(str(directory)) > 700
        saves = CampaignSaves(SaveManager(directory))
        state = State.new_campaign(7)
        backup = state.to_json()
        saves.save(state, 3)
        state.end_turn(); saves.save(state, 3)
        before = state.to_json()
        occupied = directory / 'save_3.json'; occupied.unlink(); occupied.mkdir()
        manual = directory / 'save_1.json'; manual.mkdir()
        files = {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()}
        game = create_game(backend=backend, visible=False, save_dir=directory)
        player = PlayerInput(game, native=native, output=output)
        try:
            game.set_window_size((1280, 720))
            game.push(ShardScene(state))
            for key in ('f6', 't', 'right', 'return'):
                player.press(key)
            browser = game.scene
            select_slot(player, 3)
            # Native Verdana reproduces the original SaveScene overflow; mock metrics may fit it inline.
            if native or isinstance(game.scene, DiagnosticScene):
                error = read_all(player, metrics, 'save-load-125', capture=True)
                assert str(occupied) in error
                player.press('1'); player.press('space')
                assert game.scene.message == error and player.state.to_json() == before
                queued_keys(player, ('return', 'return', '3', 'space'))
                assert game.scene is browser
                player.capture('save-selected-slot-after-error')
                player.button('Read error')
                assert read_all(player, metrics, 'save-reopened') == error
                # Reflow the same immutable diagnostic through every supported physical size.
                for window in ((1280, 720), (1280, 800), (1920, 1080)):
                    game.set_window_size(window); game.tick(1 / 60)
                    for size in (100, 125):
                        for key in ('t', 'left' if size == 100 else 'right', 'return'):
                            player.press(key)
                        assert read_all(player, metrics, 'save-reflow') == error
                player.press('escape')
            assert game.scene is browser and player.state.to_json() == before
            assert any(entry.slot == 3 for entry in browser.visible_entries)
            check_reading_layout(browser)
            select_slot(player, 3, backup=True)
            assert player.state.to_json() == backup and occupied.is_dir()
            assert {path.name: path.read_bytes() for path in directory.iterdir() if path.is_file()} == files

            # The real earned six-troop picker still exposes every veteran after returning from diagnostics.
            game.clear_and_push(ShardScene(earned_army()))
            game.set_window_size((1280, 720))
            before = player.state.to_json()
            for key in ('r', 'm', 'f5'):
                player.press(key)
            if isinstance(game.scene, DiagnosticScene):
                read_all(player, metrics, 'retirement-picker', capture=True)
                player.press('escape')
            picker = game.scene
            assert isinstance(picker, ReplacementScene) and picker.kind is None
            ids = set()
            while picker.page:
                player.press('left')
            for index in range(picker.pages):
                ids.update(picker.visible_troops); check_reading_layout(picker)
                if index + 1 < picker.pages:
                    player.press('right')
            assert ids == {troop.id for troop in player.state.hero.army}
            assert player.state.to_json() == before

            for kind in ('skyrider', 'warden'):
                game.clear_and_push(ShardScene(earned_army()))
                before = player.state.to_json()
                open_review(player, 1, kind)
                review = game.scene
                quote = review.quote
                player.press('f5')
                error = read_all(player, metrics, f'review-{kind}-125', capture=kind == 'skyrider')
                assert str(manual) in error and player.state.to_json() == before
                for key in ('t', 'left', 'escape'):
                    player.press(key)
                assert reading_scale(game) == 125
                queued_keys(player, ('return', 'return', '1', 'space'))
                assert game.scene is review and review.quote == quote and player.state.to_json() == before
                check_reading_layout(review)
                player.capture(f'review-{kind}-after-error')
                player.button('Read error')
                assert read_all(player, metrics, f'review-{kind}-reopened') == error
                player.press('escape')
                if kind == 'warden':
                    player.button('Replace veteran')
                    assert game.scene is review and review.applied
                    after = player.state.to_json()
                    player.press('f5')
                    assert read_all(player, metrics, 'applied-warden') == error
                    queued_keys(player, ('return', 'return', '1', 'space'))
                    assert game.scene is review and review.applied and review.quote == quote
                    assert player.state.to_json() == after
                    check_reading_layout(review); player.capture('applied-warden-after-error')
                    player.press('f6'); select_slot(player, 2)
                    assert game.scene.saves.load(2).to_json() == after
                    player.press('escape'); player.button('Return to shard')
                    player.press('f6'); select_slot(player, 2)
                    assert isinstance(game.scene, ShardScene) and player.state.to_json() == after
            assert occupied.is_dir() and manual.is_dir()
        finally:
            game._teardown()
    assert all(hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest for path, digest in hashes.items())
    report = dict(source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  backend=backend, source_sha256=hashes, source_unchanged=True, input_activations=len(player.events),
                  directory_characters=len(str(directory)), matrix=metrics, inputs=player.events,
                  exact_backup_reload=True, exact_applied_reload=True)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Diagnostics passed ({backend}): {len(metrics)} pages, {len(player.events)} inputs; {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-diagnostics'))
    parser.add_argument('--backend', choices=('pyglet', 'mock'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
