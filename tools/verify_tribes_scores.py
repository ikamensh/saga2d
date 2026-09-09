"""Native surrender → results → leaderboard → restart journey, with screenshots.

Run: uv run python tools/verify_tribes_scores.py --output /tmp/tribes-scores
All records use a temporary directory; the player's high scores are untouched.
"""

import argparse
import os
from pathlib import Path
import sys
import tempfile

os.environ["SAGA2D_SILENT"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pyglet.window import key, mouse
from saga2d import Game, fonts
from saga2d.testing.native_frames import tick
from tribes import mapgen
from tribes.scene import GameOverScene, MapScene, load_game
from tribes.score_scene import HighScoresScene
from tribes.scores import HighScores
from tribes.style import build_theme
from tribes.title import TitleScene


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        board = HighScores(root)
        for i in range(10):
            past = mapgen.generate(seed=i, size=11, tribe_count=2, first_tribe=i % 5)
            past.winner = 0 if i % 3 else 1
            past.round = 20 + i
            board.record(past, tribe=0, seed=i, run_id=f"past-{i}")

        game = Game("Tribes verification", resolution=(1280, 800), visible=False,
                    save_dir=root / "saves", theme=build_theme())
        try:
            fonts.load(game)

            def press(symbol):
                game.backend.window.dispatch_event("on_key_press", symbol, 0)
                game.backend.window.dispatch_event("on_key_release", symbol, 0)
                for _ in range(3):
                    tick(game)
                assert game.running, "Native input unexpectedly closed the game"

            def capture(name):
                for _ in range(3):
                    tick(game)
                def check_bounds(component):
                    x, y, width, height = component.bounds
                    assert 0 <= x <= x + width <= game.width, (name, type(component).__name__, component.bounds)
                    assert 0 <= y <= y + height <= game.height, (name, type(component).__name__, component.bounds)
                    for child in component.children:
                        if child.visible:
                            check_bounds(child)
                check_bounds(game.scene.ui)
                game.backend.capture_frame().save(output / f"{name}.png")
                print(name, flush=True)

            world = mapgen.generate(seed=7, size=11, tribe_count=2)
            world.round = 12
            world.tribes[0].explored = {tile.pos for tile in world.all_tiles()}
            world.units = {u.id: u for u in world.tribe_units(0)}
            world.move_free(world.tribe_units(0)[0], world.capital_of(1).pos)
            scene = MapScene(world, 7, settings={"confirm_end_turn": False})
            game.push(scene)
            tick(game)
            press(key.E)
            assert world.winner == 0 and world.tribes[1].surrendered
            assert isinstance(game.scene, GameOverScene)
            capture("victory")
            finished = scene.get_save_state()
            press(key.L)
            assert isinstance(game.scene, HighScoresScene)
            capture("leaderboard")
            press(key.M)
            capture("empty-board")
            press(key.ESCAPE)
            assert isinstance(game.scene, GameOverScene)
            press(key.T)
            assert isinstance(game.scene, TitleScene)
            capture("title")

            # Native mouse activation, using the button's measured logical bounds.
            def descendants(component):
                yield component
                for child in component.children:
                    yield from descendants(child)

            button = next(c for c in descendants(game.scene.ui) if getattr(c, "text", None) == "High scores")
            x, y, width, height = button.bounds
            window = game.backend.window
            scale = min(window.width / game.width, window.height / game.height)
            px = (window.width - game.width * scale) / 2 + (x + width / 2) * scale
            py = (window.height - game.height * scale) / 2 + (game.height - y - height / 2) * scale
            game.backend.window.dispatch_event("on_mouse_press", round(px), round(py), mouse.LEFT, 0)
            game.backend.window.dispatch_event("on_mouse_release", round(px), round(py), mouse.LEFT, 0)
            tick(game)
            assert isinstance(game.scene, HighScoresScene)
        finally:
            game.close()

        count = len(board.load())
        game = Game("Tribes verification", resolution=(960, 600), visible=False,
                    save_dir=root / "saves", theme=build_theme())
        try:
            fonts.load(game)
            game.push(load_game(finished))
            tick(game)
            assert isinstance(game.scene, GameOverScene)
            assert len(board.load()) == count
            capture("victory-960")
            press(key.L)
            capture("leaderboard-960")
            press(key.ESCAPE)
            loss = mapgen.generate(seed=8, size=14, tribe_count=4)
            loss.capital_of(1).level = 3
            loss.round, loss.current = 30, 3
            loss.end_turn()
            assert loss.winner == 1
            game.clear_and_push(MapScene(loss, 8))
            tick(game)
            capture("defeat")
            broken = root / "high_scores" / "save_1.json"
            broken.write_text("{broken")
            game.clear_and_push(MapScene(loss, 8))
            tick(game)
            capture("unsaved-result")
            press(key.L)
            capture("storage-error")
            assert broken.read_text() == "{broken"
        finally:
            game.close()
    print("PASS: native keyboard, mouse, AI surrender, persistence, restart and error reporting", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/tribes-scores"))
    run(parser.parse_args().output)
