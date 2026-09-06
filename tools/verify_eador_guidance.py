"""Check shared reading size through native Guide/Settings input and restart."""

import argparse
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ['SAGA2D_SILENT'] = '1'

from saga2d import Button, Label
from eador.app import create_game
from eador.preferences import reading_scale
from eador.scene import HelpScene, ShardScene, TitleScene
from tools.eador_ui import PlayerInput


def check_reading_layout(scene):
    """Every reading Label stays on canvas and clear of other text and controls."""
    labels = scene.ui.find_all(lambda item: isinstance(item, Label) and item.visible)
    controls = scene.ui.find_all(lambda item: isinstance(item, Button) and item.visible)
    assert labels
    for index, label in enumerate(labels):
        x, y, width, height = label.bounds
        assert 0 <= x < x + width <= scene.game.width
        assert 0 <= y < y + height <= scene.game.height
        for other in labels[index + 1:] + controls:
            ox, oy, ow, oh = other.bounds
            assert x + width <= ox or ox + ow <= x or y + height <= oy or oy + oh <= y, (label.text, other.text)
    return len(labels)


def verify(output):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix='eador-guidance-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(visible=False, save_dir=saves)
        player = PlayerInput(game, native=True, output=output)
        metrics = []
        try:
            game.set_window_size((1280, 720))
            game.push(TitleScene(7))
            player.press('return')
            saved = player.state.to_json()
            player.press('f1')
            assert isinstance(game.scene, HelpScene)
            check_reading_layout(game.scene)
            player.capture('guide-100')
            for key in ('o', 'd', 'down', 'down', 'down', 'right'):
                player.press(key)
            player.capture('settings-reading-125')
            player.button('Cancel')
            assert reading_scale(game) == 100
            assert not (Path(directory) / 'settings.json').exists()
            for key in ('o', 'd', 'down', 'down', 'down', 'right', 'return'):
                player.press(key)
            assert reading_scale(game) == 125
            for size in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(size)
                game.tick(1 / 60)
                metrics.append(dict(screen='guide', window=game.window_size,
                                    framebuffer=game.backend.capture_frame().size,
                                    percent=reading_scale(game), labels=check_reading_layout(game.scene)))
                player.capture(f'guide-125-{size[0]}x{size[1]}')
            player.press('c')
            assert any(entry.title == 'Militia' for entry in game.scene.visible_entries)
            player.press('escape')
            assert isinstance(game.scene, HelpScene) and player.state.to_json() == saved
        finally:
            game._teardown()
            game.backend.quit()
        game = create_game(visible=False, save_dir=saves)
        try:
            from eador.model import State
            game.push(ShardScene(State.from_json(saved)))
            player = PlayerInput(game, native=True, output=output)
            player.press('f1')
            assert reading_scale(game) == 125
            check_reading_layout(game.scene)
            player.capture('guide-restarted-125')
        finally:
            game._teardown()
            game.backend.quit()
    (output / 'matrix.json').write_text(json.dumps(metrics, indent=2) + '\n')
    print(f'Native guidance preview, Cancel, Apply, resize and restart passed: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-guidance'))
    args = parser.parse_args()
    verify(args.output)
