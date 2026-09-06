"""Run Shardbound with ``uv run python -m eador [--seed 7]``."""

import argparse
from eador.app import create_game
from eador.difficulty import DIFFICULTIES

from eador.model import HERO_CLASSES, State
from eador.scene import ShardScene, TitleScene
from eador.worldgen import THEMES


def main():
    parser = argparse.ArgumentParser(description="Shardbound — an Eador-inspired Saga2D game")
    parser.add_argument("--seed", type=int, help="open a seeded shard or linked campaign directly")
    parser.add_argument("--hero", choices=HERO_CLASSES, default="Commander")
    parser.add_argument("--difficulty", choices=DIFFICULTIES, default="standard")
    parser.add_argument("--theme", choices=THEMES, help="standalone world; linked campaigns begin in Frontier")
    parser.add_argument("--campaign", action="store_true", help="start a linked campaign; default seed 7")
    args = parser.parse_args()
    if args.campaign and args.theme not in (None, "frontier"):
        parser.error("Linked campaigns begin in Frontier. Use --theme without --campaign for a standalone world.")
    game = create_game()
    if args.campaign:
        scene = ShardScene(State.new_campaign(args.seed if args.seed is not None else 7, args.hero,
                                             difficulty=args.difficulty))
    elif args.seed is not None:
        scene = ShardScene(State.new(args.seed, args.hero, theme=args.theme or "frontier", difficulty=args.difficulty))
    else:
        scene = TitleScene(theme=args.theme or "frontier", hero_class=args.hero, difficulty=args.difficulty)
    game.run(scene)


if __name__ == "__main__":
    main()
