"""Read every new-run configuration and preserve saved progress through title errors."""
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

from saga2d import Label
from eador.app import create_game
from eador.difficulty import DIFFICULTIES
from eador.model import HERO_CLASSES
from eador.preferences import reading_scale
from eador.scene import ShardScene, TitleScene
from eador.worldgen import THEMES
from tools.eador_ui import PlayerInput
from tools.verify_eador_guidance import check_reading_layout
from tools.verify_eador_saves import select_slot


def title_choices(scene):
    return scene.seed, scene.hero_class, scene.world_theme, scene.difficulty


def files(path):
    return {p.name: p.read_bytes() for p in path.glob('*') if p.is_file()}


def verify(output, *, backend='pyglet'):
    output.mkdir(parents=True, exist_ok=True)
    sources = [*ROOT.glob('eador/**/*.py'), *ROOT.glob('saga2d/**/*.py'), *ROOT.glob('tools/*.py')]
    hashes = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    native, matrix = backend == 'pyglet', []
    about_views = []
    with TemporaryDirectory(prefix='shardbound-title-reading-') as directory:
        saves = Path(directory) / 'saves'
        game = create_game(backend=backend, visible=False, save_dir=saves)
        player = PlayerInput(game, native=native, output=output)
        try:
            game.set_window_size((1280, 720))
            game.push(TitleScene(17, hero_class='Wizard', theme='ruins', difficulty='challenge'))
            choice = title_choices(game.scene)
            player.press('t'); player.press('right'); player.press('escape')
            assert title_choices(game.scene) == choice and reading_scale(game) == 100
            player.button('Text size'); player.press('right'); player.button('Apply')
            assert title_choices(game.scene) == choice and reading_scale(game) == 125
            player.press('n')
            assert title_choices(game.scene) == (18, 'Wizard', 'ruins', 'challenge')
            assert any('Seed 18' in c.text for c in game.scene.ui.walk() if isinstance(c, Label))
            player.press('return')
            assert isinstance(game.scene, ShardScene)
            state = player.state
            assert (state.seed, state.hero.hero_class, state.theme, state.difficulty) == (18, 'Wizard', 'ruins', 'challenge')
            assert state.campaign is None
            player.press('f5'); player.press('f5')
            saved = state.to_json()
            player.press('f1'); player.press('s'); select_slot(player, 2)
            assert isinstance(game.scene, TitleScene)
            player.button('Commander'); player.button('Accessible'); player.button('Elderwild')
            chosen = title_choices(game.scene)
            invalid = json.loads((saves / 'save_1.json').read_text())
            invalid['version'] = 'X' * 5000
            (saves / 'save_1.json').write_text(json.dumps(invalid))
            retained = files(saves)
            player.press('f9')
            assert isinstance(game.scene, TitleScene) and title_choices(game.scene) == chosen
            assert files(saves) == retained
            assert 'Save format version' in game.scene.message and 'X' * 100 not in game.scene.message
            check_reading_layout(game.scene); player.capture('invalid-save-125')
            player.press('f6'); select_slot(player, 1, backup=True)
            assert player.state.to_json() == saved and files(saves) == retained
            player.press('f1'); player.press('s'); select_slot(player, 3)
            assert isinstance(game.scene, TitleScene)
            # A real file-system error has a longer path than a malformed version.
            (saves / 'save_1.json').unlink(); (saves / 'save_1.json').mkdir()
            chosen = title_choices(game.scene)
            player.press('f9')
            assert isinstance(game.scene, TitleScene) and title_choices(game.scene) == chosen
            assert 'directory' in game.scene.message
            check_reading_layout(game.scene); player.capture('directory-save-125')
            (saves / 'save_1.json').rmdir()
            player.press('f6'); select_slot(player, 2)
            assert player.state.to_json() == saved
            player.press('f1'); player.press('s'); select_slot(player, 3)
            player.button('Wizard'); player.button('Challenge'); player.button('Linked campaign')
            assert player.state.campaign is not None and player.state.hero.hero_class == 'Wizard'
            assert player.state.difficulty == 'challenge' and player.state.theme == 'frontier'

            # Reading and new-run choices must not touch any existing campaign file.
            retained = files(saves)
            for window in ((1280, 720), (1280, 800), (1920, 1080)):
                game.set_window_size(window)
                game.clear_and_push(TitleScene(17))
                game.tick(1 / 60)
                for percent in (100, 125):
                    player.press('t'); player.press('left' if percent == 100 else 'right'); player.press('return')
                    title = game.scene
                    player.button('About this build')
                    about = game.scene
                    assert about.title == 'About Shardbound'
                    for page in range(about.pages):
                        assert about.page == page
                        check_reading_layout(about)
                        about_views.append(dict(window=window, percent=percent, page=page + 1))
                        if window == (1280, 720):
                            player.capture(f'about-{percent}-page-{page + 1}')
                        player.press('pagedown')
                    player.press('escape')
                    assert game.scene is title and files(saves) == retained
                    for mode_index, (mode, rules) in enumerate(DIFFICULTIES.items(), 1):
                        player.press(str(mode_index)) if percent == 100 else player.button(rules.title)
                        for theme, world in THEMES.items():
                            while game.scene.world_theme != theme: player.press('right')
                            for hero in HERO_CLASSES:
                                if percent == 125:
                                    player.button(hero)
                                else:
                                    while game.scene.hero_class != hero: player.press('tab')
                                assert title_choices(game.scene) == (17, hero, theme, mode)
                                labels = [c.text for c in game.scene.ui.walk() if isinstance(c, Label)]
                                for description in (HERO_CLASSES[hero].description, world.description, rules.description):
                                    assert description in labels
                                check_reading_layout(game.scene)
                                assert files(saves) == retained
                                matrix.append(dict(window=window, percent=percent, hero=hero, theme=theme, difficulty=mode))
                                if window == (1280, 720) and (hero, theme, mode) in (
                                        ('Wizard', 'ruins', 'challenge'), ('Commander', 'frontier', 'accessible')):
                                    player.capture(f'{hero.lower()}-{theme}-{mode}-{percent}')
            events = player.events
        finally:
            game._teardown(); game.backend.quit()
        game = create_game(backend=backend, visible=False, save_dir=saves)
        try:
            game.push(TitleScene(17))
            replay = PlayerInput(game, native=native, output=output)
            replay.press('t')
            assert reading_scale(game) == 125
            replay.capture('restarted-settings-125'); replay.press('escape')
            assert isinstance(game.scene, TitleScene) and files(saves) == retained
            check_reading_layout(game.scene)
            events += replay.events
        finally:
            game._teardown(); game.backend.quit()
        # A valid nested path can make the OS diagnostic longer than a whole panel.
        long_path = Path(directory)
        while len(str(long_path)) < 700:
            long_path /= 'a-realm-with-a-long-storage-directory'
        long_path.mkdir(parents=True)
        (long_path / 'save_1.json').mkdir()
        game = create_game(backend=backend, visible=False, save_dir=long_path)
        try:
            game.set_window_size((1280, 720))
            game.push(TitleScene(17, hero_class='Wizard', theme='ruins', difficulty='challenge'))
            replay = PlayerInput(game, native=native, output=output)
            replay.press('t'); replay.press('right'); replay.press('return'); replay.press('f9')
            title = game.scene
            pages = title.notice_pages
            assert len(pages) > 1 and ''.join(pages) == title.message
            for index, text in enumerate(pages):
                assert title.notice_page == index
                assert any(c.text == text for c in title.ui.walk() if isinstance(c, Label))
                check_reading_layout(title); replay.capture(f'long-path-125-page-{index + 1}')
                replay.press('pagedown')
            replay.press('t'); replay.press('left'); replay.press('escape')
            assert title.notice_page == len(pages) - 1
            for size in ((1280, 800), (1920, 1080), (1280, 720)):
                game.set_window_size(size); game.tick(1 / 60)
                check_reading_layout(title)
                assert ''.join(title.notice_pages) == title.message
            assert title_choices(title) == (17, 'Wizard', 'ruins', 'challenge')
            replay.press('pageup')
            assert title.notice_page < len(title.notice_pages) - 1
            assert (long_path / 'save_1.json').is_dir()
            events += replay.events
        finally:
            game._teardown(); game.backend.quit()
    assert all(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == sha for name, sha in hashes.items())
    report = dict(about_views=about_views,
                  source_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  source_sha256=hashes, backend=backend, layouts=matrix, input_activations=len(events), inputs=events)
    (output / 'verification.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f'Title reading passed ({backend}): {len(matrix)} layouts / {len(events)} inputs')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('/tmp/shardbound-title-reading'))
    parser.add_argument('--backend', choices=('mock', 'pyglet'), default='pyglet')
    args = parser.parse_args()
    verify(args.output, backend=args.backend)
