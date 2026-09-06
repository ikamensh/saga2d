"""The shipped game configuration, shared by the launcher and playable checks."""

import os
from pathlib import Path

from saga2d import Game
from eador.style import build_theme
from eador.preferences import apply_display_preferences, load_preferences

ASSETS = Path(__file__).resolve().parent / 'assets'


def create_game(title='Shardbound', **options):
    """Create an ordinary Saga2D Game with Shardbound's files and presentation.

    Tests and packaging may override normal Game options such as backend,
    visibility and save_dir. Explicit resolution/fullscreen, hidden windows, or
    SAGA2D_HEADLESS keep their launch display instead of restoring saved display.
    Sound, motion and Codex reading preferences still load. Asset paths never depend on cwd.
    """
    defaults = dict(resolution=(1280, 800), theme=build_theme(), asset_path=ASSETS,
                    save_dir=Path.home() / '.shardbound' / 'saves')
    game = Game(title, **(defaults | options))
    try:
        preferences = load_preferences(game)
        controlled_display = ("resolution" in options or "fullscreen" in options
                              or options.get("visible") is False
                              or os.environ.get("SAGA2D_HEADLESS", "").strip() not in ("", "0"))
        if not controlled_display:
            apply_display_preferences(game, preferences)
        return game
    except BaseException:
        try:
            game._teardown()
        finally:
            game.backend.quit()
        raise
