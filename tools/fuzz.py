"""Random play against the rules and the scene; any exception or broken invariant is a bug.

    uv run python tools/fuzz.py            # 60 AI-vs-AI games and 20 random-input scene runs
    uv run python tools/fuzz.py --games 300 --monkey 0

The AI games check the world after every turn (one unit per tile, hp in
range, cities own their tiles, dead tribes keep nothing, a winner by round
30).  The monkey runs feed the map scene random keys, clicks, drags and
scrolls on the mock backend, including through every overlay.  Run this
after changing rules, the AI or scene input handling; it found the pause
menu's save/load bug within thirty runs.
"""

from __future__ import annotations

import argparse
import random
import sys
import tempfile
import traceback
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.cpu_budget import CpuBudget  # noqa: E402
from saga2d import Game  # noqa: E402
from tribes import ai, mapgen  # noqa: E402
from tribes.model import World  # noqa: E402
from tribes.scene import MapScene  # noqa: E402
from tribes.style import build_theme  # noqa: E402
from tribes.title import TitleScene  # noqa: E402


def check_world(world: World) -> None:
    occupied: set[tuple[int, int]] = set()
    for unit in world.units.values():
        assert world.in_bounds(unit.pos), ("unit out of bounds", unit)
        assert unit.pos not in occupied, ("two units on one tile", unit.pos)
        occupied.add(unit.pos)
        assert 0 < unit.hp <= unit.max_hp, ("hp out of range", unit)
        assert world.tribes[unit.tribe].alive, ("unit of a dead tribe", unit)
        assert world.tile(unit.pos).terrain.value != "water", ("unit on water", unit)
    for city in world.cities.values():
        tile = world.tile(city.pos)
        assert tile.city_id == city.id and not tile.village and tile.owner_city == city.id, ("city tile mismatch", city)
        assert city.population < city.next_level_population, ("unspent population", city)
    for tile in world.all_tiles():
        assert tile.owner_city is None or tile.owner_city in world.cities, ("territory of a missing city", tile)
        assert tile.city_id is None or world.cities[tile.city_id].pos == tile.pos, ("dangling city id", tile)
    for tribe in world.tribes:
        assert tribe.stars >= 0, ("negative stars", tribe.id)
        assert bool(world.tribe_cities(tribe.id)) == tribe.alive, ("alive without cities, or dead with them", tribe.id)
        assert tribe.alive or not world.tribe_units(tribe.id), ("dead tribe keeps units", tribe.id)
    assert 1 <= world.round <= 31, ("round", world.round)


def ai_games(seeds: range, *, budget: CpuBudget | None = None) -> int:
    failures = 0
    outcomes: Counter[str] = Counter()
    for seed in seeds:
        if budget:
            budget.checkpoint()
        rng = random.Random(seed)
        size, tribes = rng.choice((11, 14, 18)), rng.choice((2, 3, 4))
        try:
            world = mapgen.generate(seed=seed, size=size, tribe_count=tribes, human=None)
            check_world(world)
            for _turn in range(400):
                if budget:
                    budget.checkpoint()
                if world.winner is not None:
                    break
                ai.take_turn(world, world.current, rng)
                check_world(world)
            assert world.winner is not None, "no winner after 400 turns"
            outcomes["domination" if world.round <= 30 and any(not t.alive for t in world.tribes) else "score"] += 1
        except Exception:
            failures += 1
            print(f"AI game seed {seed} (size {size}, {tribes} tribes):")
            traceback.print_exc(limit=4)
    print(f"AI games: {len(seeds)} played, {failures} failed, outcomes {dict(outcomes)}")
    return failures


MONKEY_KEYS = [k for keys in MapScene.controls for k in ((keys,) if isinstance(keys, str) else keys)] + list("12345snlmp")


def monkey_runs(seeds: range, steps: int = 600, *, budget: CpuBudget | None = None) -> int:
    """Each seed reproduces title/world choices as well as the input stream."""
    failures = 0
    for seed in seeds:
        if budget:
            budget.checkpoint()
        rng = random.Random(seed)
        random.seed(seed)  # Title/NewGameScene use the global RNG; only this development tool seeds it.
        with tempfile.TemporaryDirectory() as save_dir:
            game = Game("Monkey", backend="mock", resolution=(1280, 800), theme=build_theme(), save_dir=Path(save_dir) / "saves")
            try:
                game.push(TitleScene(size=rng.choice((11, 14)), tribes=rng.choice((2, 3, 4))))
                game.tick(1 / 60)
                for key in ("n", "return"):
                    game.backend.inject_key(key)
                    game.tick(1 / 60)
                for _step in range(steps):
                    if budget:
                        budget.checkpoint()
                    roll = rng.random()
                    if roll < 0.45:
                        game.backend.inject_key(rng.choice(MONKEY_KEYS), shift=rng.random() < 0.1)
                    elif roll < 0.8:
                        game.backend.inject_click(rng.randrange(1280), rng.randrange(800), rng.choice(("left", "left", "right")))
                    elif roll < 0.9:
                        game.backend.inject_mouse_move(rng.randrange(1280), rng.randrange(800))
                    elif roll < 0.95:
                        game.backend.inject_scroll(rng.randrange(1280), rng.randrange(800), 0, rng.uniform(-5, 5))
                    else:
                        game.backend.inject_drag(rng.randrange(1280), rng.randrange(800), rng.uniform(-40, 40), rng.uniform(-40, 40), button="right")
                    for _ in range(rng.choice((1, 1, 2, 6))):
                        if budget:
                            budget.checkpoint()
                        game.tick(1 / 60)
                    if game.scene is None:
                        break
                assert len(game.scenes) <= 3, ("scene stack grew", [type(s).__name__ for s in game.scenes])
            except Exception:
                failures += 1
                print(f"monkey seed {seed}, stack {[type(s).__name__ for s in game.scenes]}:")
                traceback.print_exc()
            finally:
                game._teardown()
    print(f"monkey runs: {len(seeds)} played, {failures} failed")
    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--games", type=int, default=60)
    parser.add_argument("--monkey", type=int, default=20)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--cpu-percent", type=float, default=25,
                        help="CPU allowance as a percent of one core (default 25; 100 for explicit stress)")
    args = parser.parse_args()
    try:
        budget = CpuBudget(args.cpu_percent)
    except ValueError as error:
        parser.error(str(error))
    failures = (ai_games(range(args.seed, args.seed + args.games), budget=budget)
                + monkey_runs(range(args.seed, args.seed + args.monkey), budget=budget))
    budget.checkpoint()
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
