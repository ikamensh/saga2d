"""Run Shardbound with ``uv run python -m eador [--seed 7]``."""

import argparse
from pathlib import Path
from saga2d import add_match_arguments, match_from_arguments
from eador.app import create_game
from eador.difficulty import DIFFICULTIES

from eador.model import HERO_CLASSES, State
from eador.scene import ShardScene, TitleScene
from eador.worldgen import THEMES


def create_session(argv=None, **game_options):
    """Configure a launch; the caller runs it or supplies a backend for input checks."""
    parser = argparse.ArgumentParser(description="Shardbound — an Eador-inspired Saga2D game")
    parser.add_argument("--seed", type=int, help="open a seeded shard or linked campaign directly")
    parser.add_argument("--hero", choices=HERO_CLASSES, default="Commander")
    parser.add_argument("--difficulty", choices=DIFFICULTIES, default="standard")
    parser.add_argument("--theme", choices=THEMES, help="standalone world; linked campaigns begin in Frontier")
    parser.add_argument("--campaign", action="store_true", help="start a linked campaign; default seed 7")
    parser.add_argument("--data-dir", type=Path, help="keep saves and settings in this separate directory")
    add_match_arguments(parser)
    args = parser.parse_args(argv)
    if args.campaign and args.theme not in (None, "frontier"):
        parser.error("Linked campaigns begin in Frontier. Use --theme without --campaign for a standalone world.")
    if args.join and not args.room:
        parser.error("--join requires --room CODE")
    if (args.host or args.join) and not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    if args.data_dir is not None:
        game_options['save_dir'] = args.data_dir.expanduser().resolve() / 'saves'
    game = create_game(**game_options)
    from eador.multiplayer import ShardboundMatch, NetworkShardScene
    lobby = match_from_arguments(args, parser, title="Shardbound co-op", game_id="shardbound-v1",
                                 create_match=lambda: ShardboundMatch(args.seed if args.seed is not None else 7, args.hero,
                                     theme=args.theme or "frontier", difficulty=args.difficulty, campaign=args.campaign),
                                 create_scene=NetworkShardScene)
    if lobby is not None:
        return game, lobby
    if args.campaign:
        scene = ShardScene(State.new_campaign(args.seed if args.seed is not None else 7, args.hero,
                                             difficulty=args.difficulty))
    elif args.seed is not None:
        scene = ShardScene(State.new(args.seed, args.hero, theme=args.theme or "frontier", difficulty=args.difficulty))
    else:
        scene = TitleScene(theme=args.theme or "frontier", hero_class=args.hero, difficulty=args.difficulty)
    return game, scene


def main():
    game, scene = create_session()
    game.run(scene)


if __name__ == "__main__":
    main()
