"""Run Tribes: ``python -m tribes [--seed N] [--size N] [--tribes N] [--fullscreen]``.

Without ``--seed`` the game opens on the title screen (``--size`` and
``--tribes`` pre-fill the new-game options).  With ``--seed`` it skips the
title and starts that map directly, so a seed reproduces a game in one step.
"""

from __future__ import annotations

import argparse

from saga2d import Game, TextStyle, Theme
from tribes import effects
from tribes.scene import DEFAULT_SETTINGS, new_game
from tribes.sound import SoundBank
from tribes.title import TitleScene


def build_theme() -> Theme:
    return Theme(
        font="Helvetica Neue",
        font_size=16,
        text_styles={
            "title": TextStyle(22, (255, 224, 120, 255)),
            "heading": TextStyle(18, (250, 250, 255, 255)),
            "hud": TextStyle(17, (240, 242, 250, 255)),
            "body": TextStyle(15, (225, 230, 240, 255)),
            "sub": TextStyle(13, (190, 196, 214, 255)),
            "caption": TextStyle(12, (150, 156, 176, 255)),
            "city": TextStyle(12, (255, 255, 255, 255)),
            "banner": TextStyle(38, (255, 255, 255, 255)),
            "banner_sub": TextStyle(17, (255, 255, 255, 255)),
            "hero": TextStyle(84, (255, 224, 120, 255)),
            "hero_sub": TextStyle(19, (210, 216, 235, 255)),
        },
        button_font_size=15,
        button_min_width=90,
        panel_border_width=1,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Tribes — a small Polytopia-style strategy game")
    parser.add_argument("--seed", type=int, default=None, help="start this map directly, skipping the title screen")
    parser.add_argument("--size", type=int, default=14)
    parser.add_argument("--tribes", type=int, default=3)
    parser.add_argument("--fullscreen", action="store_true")
    args = parser.parse_args()
    game = Game("Tribes", resolution=None, fullscreen=args.fullscreen, theme=build_theme())
    bank = SoundBank(game)
    effects.sound_hook = bank.play
    effects.volume_hook = bank.set_volume
    effects.apply_volumes(DEFAULT_SETTINGS)
    bank.start_music()
    if args.seed is not None:
        game.run(new_game(args.seed, size=args.size, tribes=args.tribes))
    else:
        game.run(TitleScene(size=args.size, tribes=args.tribes))


if __name__ == "__main__":
    main()
