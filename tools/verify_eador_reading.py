"""Exercise Codex reading size through native Settings, save/restart and page bounds."""
import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from saga2d import Label
from eador.app import create_game
from eador.codex import CATEGORIES, CodexScene
from eador.model import State
from eador.preferences import codex_text_scale
from eador.scene import ShardScene
from tools.eador_ui import PlayerInput


def visible_labels(component):
    if component.visible:
        if isinstance(component, Label):
            yield component
        for child in component.children:
            yield from visible_labels(child)


def check_page(scene):
    for label in visible_labels(scene.ui):
        x, y, width, height = label.bounds
        assert x >= scene.x + 23 and x + width <= scene.x + 1017
        assert y >= scene.y + 162 and y + height <= scene.y + 615, (label.text, label.bounds)


def verify_matrix(game, output):
    from tools.eador_relic_campaign import prepare_censer_watch
    from tools.eador_observatory_campaign import prepare_observatory

    observatory = prepare_observatory()
    observatory.explore(approach='clear')
    old = Path(__file__).resolve().parents[1] / 'tests/eador/fixtures/v10_pinned_crossing.json'
    snapshots = [('earned-censer', prepare_censer_watch().to_json()),
                 ('paid-observatory', observatory.to_json()), ('v10', old.read_text())]
    metrics = []
    player = PlayerInput(game, native=True, output=output)
    for requested in ((1280, 720), (1280, 800), (1920, 1080)):
        game.set_window_size(requested)
        game.tick(1 / 60)
        assert game.window_size == requested, (requested, game.window_size)
        assert game.resolution == (1280, 800)
        for label, saved in snapshots:
            root = ShardScene(State.from_json(saved))
            game.clear_and_push(root)
            before = root.state.to_json()
            game.push(CodexScene(root))
            game.tick(1 / 60)
            for percent in (100, 125):
                player.button('Text size')
                player.press('right' if percent == 125 else 'left')
                player.button('Apply')
                assert codex_text_scale(game) == percent
                for index, category in enumerate(CATEGORIES):
                    player.press(str(index + 1))
                    seen = []
                    for page in range(game.scene.pages):
                        check_page(game.scene)
                        seen.extend(entry.title for entry in game.scene.visible_entries)
                        # Record all long-reference pages; the matrix checks every
                        # page even when only representative images are retained.
                        if page == 0 or category in ('Abilities', 'Sites', 'Relics'):
                            player.capture(f'{requested[0]}x{requested[1]}-{label}-{percent}-{category.lower()}-{page + 1}')
                        if page + 1 < game.scene.pages:
                            player.button('Next')
                    assert seen == [entry.title for entry in game.scene.entries]
                    metrics.append(dict(window=game.window_size, framebuffer=game.backend.capture_frame().size,
                                        state=label, percent=percent, category=category,
                                        pages=game.scene.pages, entries=len(seen)))
                assert root.state.to_json() == before
    return metrics


def verify(output, *, matrix=False):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='eador-reading-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(visible=False, save_dir=saves)
        player = PlayerInput(game, native=True, output=output)
        try:
            state = State.new(7)
            before = state.to_json()
            root = ShardScene(state)
            game.push(root)
            game.push(CodexScene(root))
            game.tick(1 / 60)
            player.capture('codex-100')
            player.button('Text size')
            player.press('right')
            player.capture('settings-reading-125')
            player.button('Cancel')
            player.capture('cancelled-100')
            player.button('Text size')
            player.press('right')
            player.button('Apply')
            for index, category in enumerate(CATEGORIES):
                player.press(str(index + 1))
                seen = []
                for page in range(game.scene.pages):
                    check_page(game.scene)
                    seen.extend(entry.title for entry in game.scene.visible_entries)
                    if page == 0:
                        player.capture(f'{category.lower()}-125')
                    if page + 1 < game.scene.pages:
                        player.button('Next')
                assert seen == [entry.title for entry in game.scene.entries]
            player.press('1')
            player.button('Next')
            anchor = game.scene.visible_entries[0].title
            player.button('Text size')
            player.press('left')
            player.button('Apply')
            assert game.scene.visible_entries[0].title == anchor
            player.capture('reading-anchor-100')
            player.button('Text size')
            player.press('right')
            player.button('Apply')
            assert root.state.to_json() == before
        finally:
            game._teardown()
            game.backend.quit()
        game = create_game(visible=False, save_dir=saves)
        try:
            root = ShardScene(State.new(7))
            game.push(root)
            game.push(CodexScene(root))
            game.tick(1 / 60)
            check_page(game.scene)
            assert codex_text_scale(game) == 125
            PlayerInput(game, native=True, output=output).capture('restarted-125')
            if matrix:
                results = verify_matrix(game, output / 'matrix')
                (output / 'matrix.json').write_text(json.dumps(results, indent=2))
        finally:
            game._teardown()
            game.backend.quit()
    print(f'Native reading preview, cancel, apply, page bounds and restart passed: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-reading'))
    parser.add_argument('--matrix', action='store_true', help='also inspect both sizes, current/v10 saves and three native window sizes')
    args = parser.parse_args()
    verify(args.output, matrix=args.matrix)
