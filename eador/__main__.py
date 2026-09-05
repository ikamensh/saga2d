"""Run Shardbound with ``uv run python -m eador [--seed 7]``."""

import argparse
from eador.app import create_game

from eador.model import HERO_CLASSES, State
from eador.scene import ShardScene, TitleScene
from eador.worldgen import THEMES


def main():
    parser = argparse.ArgumentParser(description="Shardbound — an Eador-inspired Saga2D game")
    parser.add_argument("--seed", type=int, help="open a seeded shard directly")
    parser.add_argument("--hero", choices=HERO_CLASSES, default="Commander")
    parser.add_argument("--theme", choices=THEMES, default="frontier")
    args = parser.parse_args()
    game = create_game()
    game.run(ShardScene(State.new(args.seed, args.hero, theme=args.theme)) if args.seed is not None
             else TitleScene(theme=args.theme, hero_class=args.hero))


if __name__ == "__main__":
    main()
