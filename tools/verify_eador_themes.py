"""Choose each world with native input, then save, return to title and reload it."""

import argparse
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault('SAGA2D_SILENT', '1')

from saga2d.testing.native_frames import tick
from eador.app import create_game
from eador.scene import ShardScene, TitleScene
from eador.worldgen import THEMES


def verify(output):
    from pyglet.window import key

    output.mkdir(parents=True, exist_ok=True)
    for height in (720, 800):
        with TemporaryDirectory(prefix='shardbound-themes-') as directory:
            game = create_game('Shardbound worlds', resolution=(1280, 800), visible=False,
                        save_dir=Path(directory) / 'saves')
            game.backend.window.set_size(1280, height)

            def press(symbol):
                window = game.backend.window
                window.dispatch_event('on_key_press', symbol, 0)
                window.dispatch_event('on_key_release', symbol, 0)
                tick(game)

            def capture(name):
                tick(game)
                game.backend.capture_frame().save(output / f'{name}-{height}.png')

            try:
                for index, theme in enumerate(THEMES):
                    game.clear_and_push(TitleScene(seed=17))
                    for _ in range(index):
                        press(key.RIGHT)
                    press(key.TAB)
                    capture(f'title-{theme}')
                    press(key.ENTER)
                    assert isinstance(game.scene, ShardScene)
                    assert game.scene.state.theme == theme
                    assert game.scene.state.hero.hero_class == 'Warrior'
                    press(key.F5)
                    saved = game.scene.state.to_json()
                    capture(f'shard-{theme}')
                    for symbol in (key.F1, key.S, key._1):
                        press(symbol)
                    assert isinstance(game.scene, TitleScene) and game.scene.world_theme == theme
                    press(key.RIGHT)
                    press(key.F9)
                    assert game.scene.state.to_json() == saved
            finally:
                game._teardown()
                game.backend.quit()
    print(f'Three native world selections, saved campaigns and return-to-title paths passed: {output}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=Path('/tmp/shardbound-themes'))
    verify(parser.parse_args().out)
