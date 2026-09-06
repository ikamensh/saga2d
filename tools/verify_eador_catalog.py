"""Native/public-input verification of complete Build/Recruit reading pages."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('SAGA2D_SILENT', '1')

from eador.app import create_game
from eador.model import BUILDINGS, RECRUITABLE, State
from eador.scene import CatalogScene, ShardScene, TitleScene
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout


def catalog_pages(player, kind):
    """Traverse each complete page once in item order, without buying or losing an item."""
    scene = player.game.scene
    assert isinstance(scene, CatalogScene) and scene.kind == kind
    seen, metrics = [], []
    while True:
        items = scene.visible_items
        seen.extend(items)
        metrics.append(dict(kind=kind, page=scene.page + 1, pages=scene.pages, items=items,
                            labels=check_reading_layout(scene)))
        if scene.page + 1 == scene.pages:
            break
        player.press('right')
    assert seen == (list(BUILDINGS) if kind == 'build' else list(RECRUITABLE))
    return metrics


def verify(output):
    output.mkdir(parents=True, exist_ok=True)
    metrics = []
    with TemporaryDirectory(prefix='eador-catalog-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(visible=False, save_dir=saves)
        player = PlayerInput(game, native=True, output=output)
        try:
            game.set_window_size((1280, 720))
            game.push(TitleScene(7))
            player.press('return')
            before = player.state.to_json()
            player.press('b')
            player.capture('build-100')
            for key in ('t', 'right', 'escape'):
                player.press(key)
            assert not (Path(directory) / 'settings.json').exists()
            for key in ('t', 'right', 'return'):
                player.press(key)
            player.capture('build-125')
            check_reading_layout(game.scene)
            assert player.state.to_json() == before
            player.button(f"{BUILDINGS['barracks'].cost} gold")
            assert 'barracks' in player.state.buildings
            purchased = player.state.to_json()
            player.press('1')
            assert player.state.to_json() == purchased
            player.press('escape')
            player.state.recruit('swordsman')
            purchased = player.state.to_json()
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                for kind, shortcut in (('build', 'b'), ('recruit', 'r')):
                    for percent in (100, 125):
                        game.clear_and_push(ShardScene(State.from_json(purchased)))
                        player.press(shortcut)
                        player.press('t')
                        player.press('left' if percent == 100 else 'right')
                        player.button('Apply')
                        scene = game.scene
                        seen = []
                        while True:
                            seen.extend(scene.visible_items)
                            metrics.append(dict(kind=kind, page=scene.page + 1, pages=scene.pages,
                                                items=scene.visible_items, percent=percent, window=game.window_size,
                                                framebuffer=game.backend.capture_frame().size,
                                                labels=check_reading_layout(scene)))
                            if size == (1280, 720):
                                player.capture(f'{kind}-{percent}-page-{scene.page + 1}')
                            if scene.page + 1 == scene.pages:
                                break
                            if percent == 100:
                                player.press('right')
                            else:
                                player.button('Next')
                        assert seen == (list(BUILDINGS) if kind == 'build' else list(RECRUITABLE))
                        anchor = scene.visible_items[0]
                        for key in ('t', 'left' if percent == 125 else 'right', 'return'):
                            player.press(key)
                        assert scene.visible_items[0] == anchor
                        check_reading_layout(scene)
                        for key in ('t', 'right' if percent == 125 else 'left', 'escape'):
                            player.press(key)
                        assert scene.visible_items[0] == anchor
                        for key in ('t', 'right' if percent == 125 else 'left', 'return'):
                            player.press(key)
                        assert scene.visible_items[0] == anchor
                        assert player.state.to_json() == purchased
                        player.press('escape')
        finally:
            game._teardown()
        restarted = create_game(visible=False, save_dir=saves)
        try:
            restarted.push(ShardScene(State.from_json(purchased)))
            player = PlayerInput(restarted, native=True, output=output)
            player.press('r')
            check_reading_layout(restarted.scene)
            player.capture('recruit-restarted-125')
        finally:
            restarted._teardown()
    (output / 'matrix.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(f'Native Catalog reading passed: {len(metrics)} complete pages; {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-catalog-reading'))
    verify(parser.parse_args().output)
