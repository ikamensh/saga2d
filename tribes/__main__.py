"""Run Tribes: ``python -m tribes [--seed N] [--size N] [--tribes N] [--fullscreen]``."""

from __future__ import annotations

import argparse
import random

from saga2d import Game, TextStyle, Theme
from tribes.scene import new_game


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
            "banner": TextStyle(30, (255, 255, 255, 255)),
        },
        button_font_size=15,
        button_min_width=90,
        panel_border_width=1,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Tribes — a small Polytopia-style strategy game")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--size", type=int, default=14)
    parser.add_argument("--tribes", type=int, default=3)
    parser.add_argument("--fullscreen", action="store_true")
    args = parser.parse_args()
    seed = args.seed if args.seed is not None else random.randrange(1, 10_000)
    game = Game("Tribes", resolution=None, fullscreen=args.fullscreen, theme=build_theme())
    game.run(new_game(seed, size=args.size, tribes=args.tribes))


if __name__ == "__main__":
    main()
