"""Run Tribes: ``python -m tribes [--seed N] [--size N] [--tribes N] [--fullscreen]``.

Without ``--seed`` the game opens on the title screen (``--size`` and
``--tribes`` pre-fill the new-game options).  With ``--seed`` it skips the
title and starts that map directly, so a seed reproduces a game in one step.
"""

from __future__ import annotations

import argparse

from saga2d import add_match_arguments, match_from_arguments
from saga2d import Game, fonts
from tribes import effects
from tribes.scene import DEFAULT_SETTINGS, new_game
from tribes.sound import SoundBank
from tribes.style import build_theme
from tribes.title import TitleScene


def main() -> None:
    parser = argparse.ArgumentParser(description="Tribes — a small Polytopia-style strategy game")
    parser.add_argument("--seed", type=int, default=None, help="start this map directly, skipping the title screen")
    parser.add_argument("--size", type=int, default=14)
    parser.add_argument("--tribes", type=int, default=3)
    parser.add_argument("--fullscreen", action="store_true")
    add_match_arguments(parser)
    args = parser.parse_args()
    game = Game("Tribes", resolution=None, fullscreen=args.fullscreen, theme=build_theme())
    fonts.load(game)
    bank = SoundBank(game)
    effects.sound_hook = bank.play
    effects.volume_hook = bank.set_volume
    effects.apply_volumes(DEFAULT_SETTINGS)
    bank.start_music()
    from tribes.multiplayer import NetworkMapScene, TribesMatch
    lobby = match_from_arguments(args, parser, title="Tribes", game_id="tribes-v1",
                                 create_match=lambda: TribesMatch(args.seed if args.seed is not None else 7, size=args.size), create_scene=NetworkMapScene)
    if lobby is not None:
        game.run(lobby)
        return
    if args.seed is not None:
        game.run(new_game(args.seed, size=args.size, tribes=args.tribes))
    else:
        game.run(TitleScene(size=args.size, tribes=args.tribes))


if __name__ == "__main__":
    main()
