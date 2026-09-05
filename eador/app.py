"""The shipped game configuration, shared by the launcher and playable checks."""

from pathlib import Path

from saga2d import Game
from eador.style import build_theme

ASSETS = Path(__file__).resolve().parent / 'assets'


def create_game(title='Shardbound', **options):
    """Create an ordinary Saga2D Game with Shardbound's files and presentation.

    Tests and packaging may override normal Game options such as backend,
    visibility and save_dir. Asset paths never depend on the launch directory.
    """
    defaults = dict(resolution=(1280, 800), theme=build_theme(), asset_path=ASSETS,
                    save_dir=Path.home() / '.shardbound' / 'saves')
    return Game(title, **(defaults | options))
