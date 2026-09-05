"""Play the Watch briefing, manual hold, exact saves and deadline through visible input."""

import argparse
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["SAGA2D_SILENT"] = "1"

from eador.app import create_game
from eador.encounter_scene import EncounterScene
from eador.scene import BattleScene, ChoiceScene, ResultScene, ShardScene, TitleScene


def verify(output, *, backend="pyglet"):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="shardbound-watch-") as directory:
        game = create_game("Shardbound Watch verification", resolution=(1280, 800), backend=backend,
                    visible=False, save_dir=Path(directory) / "saves")
        if backend == "pyglet":
            from pyglet.window import key, mouse
            window = game.backend.window

        def press(name):
            if backend == "mock":
                game.backend.inject_key(name)
                game.backend.inject_key(name, type="key_release")
            else:
                symbol = getattr(key, {"return": "ENTER"}.get(name, "_" + name if name.isdigit() else name.upper()))
                window.dispatch_event("on_key_press", symbol, 0)
                window.dispatch_event("on_key_release", symbol, 0)
            game.tick(1 / 60)

        def click(x, y):
            if backend == "mock":
                game.backend.inject_click(round(x), round(y))
                game.backend.inject_release(round(x), round(y))
            else:
                scale = min(window.width / game.width, window.height / game.height)
                px = (window.width - game.width * scale) / 2 + x * scale
                py = (window.height - game.height * scale) / 2 + (game.height - y) * scale
                window.dispatch_event("on_mouse_press", round(px), round(py), mouse.LEFT, 0)
                window.dispatch_event("on_mouse_release", round(px), round(py), mouse.LEFT, 0)
            game.tick(1 / 60)

        def capture(name):
            for _ in range(110 if isinstance(game.scene, BattleScene) else 1):
                game.tick(1 / 60)  # Let transient damage labels settle; model turns do not advance.
            if backend == "pyglet":
                game.backend.capture_frame().save(output / f"{name}.png")

        def root():
            return next(scene for scene in game.scenes if isinstance(scene, ShardScene))

        def finish_rout():
            for _ in range(60):
                if root().state.battle.outcome:
                    break
                press("a")
            assert root().state.battle.outcome == "player"
            press("e")
            while isinstance(game.scene, ChoiceScene):
                press("1")

        def select(ident):
            click(*game.scene.grid.center(root().state.battle.unit(ident).pos))
            assert game.scene.selected == ident

        def move(ident, destination):
            select(ident)
            if destination == root().state.battle.objective.target:
                press("o")
                assert game.scene.cursor == destination
                press("return")
            else:
                click(*game.scene.grid.center(destination))
            assert root().state.battle.unit(ident).pos == destination

        def attack(ident, target):
            select(ident)
            battle = root().state.battle
            before = battle.unit(target).hp, battle.unit(ident).hp
            preview = battle.preview(ident, target)
            click(*game.scene.grid.center(battle.unit(target).pos))
            assert preview == (before[0] - battle.unit(target).hp, before[1] - battle.unit(ident).hp)

        def guard_army():
            for unit in root().state.battle.units:
                if unit.team == "player" and unit.alive and not unit.acted:
                    select(unit.id)
                    press("g")

        try:
            game.push(TitleScene(seed=7))
            for name in ("return", "b", "1", "escape", "r", "2", "escape"):
                press(name)
            for destination in (None, (-1, -1), (0, -2)):
                if destination is None:
                    press("x")
                else:
                    click(*root().grid.center(destination))
                    press("return")
                finish_rout()
                if root().state.inventory and not root().state.hero.relic:
                    press("h")
                    press("1")
                    press("escape")
                press("e")
                if "temple" not in root().state.buildings:
                    for name in ("b", "3", "escape"):
                        press(name)
                press("r")
                while (root().state.gold >= root().state.recruit_cost("swordsman")
                       and len(root().state.hero.army) < root().state.hero.max_army):
                    press("2")
                press("escape")
            before = root().state.to_json()
            press("x")
            assert isinstance(game.scene, EncounterScene)
            assert root().state.to_json() == before
            capture("briefing")
            press("escape")
            assert root().state.to_json() == before
            press("x")
            press("return")
            assert isinstance(game.scene, BattleScene)
            assert root().state.actions_left == 1
            assert root().state.battle.objective.kind == "hold"
            capture("objective-start")
            for name in ("f6", "tab", "2", "escape"):
                press(name)
            pike = next(unit.id for unit in root().state.battle.units if unit.team == "enemy" and unit.kind == "pikeman")
            for ident, destination in ((1, (1, 0)), (4, (0, 1)), (5, (0, 0)), (3, (0, -1)), (2, (-1, 0)), (6, (-1, 1))):
                move(ident, destination)
            attack(1, pike)
            attack(3, pike)
            guard_army()
            press("e")
            attack(3, pike)
            for ident, destination in ((1, (1, -1)), (4, (1, 0)), (6, (0, 1)), (0, (-1, 1))):
                move(ident, destination)
            guard_army()
            press("e")
            assert root().state.battle.objective.progress == 1
            capture("objective-progress")
            press("f5")
            saved = root().state.to_json()
            guard_army()
            press("e")
            assert isinstance(game.scene, ResultScene)
            assert root().state.battle.outcome_reason == "hold"
            terminal = root().state.to_json()
            capture("hold-victory")
            press("f9")
            assert root().state.to_json() == saved
            guard_army()
            press("e")
            assert root().state.to_json() == terminal
            press("f5")
            press("f9")
            assert isinstance(game.scene, ResultScene) and root().state.to_json() == terminal
            press("e")
            while isinstance(game.scene, ChoiceScene):
                press("1")
            assert root().state.provinces[(0, -2)].explored
            after_reward = root().state.to_json()
            press("x")
            assert isinstance(game.scene, ShardScene) and root().state.to_json() == after_reward
            press("f6")
            press("2")
            assert isinstance(game.scene, BattleScene)
            while root().state.battle.outcome is None:
                guard_army()
                press("e")
            assert root().state.battle.outcome_reason == "deadline"
            assert root().state.battle.round == 8 and root().state.battle.unit(0).alive
            capture("deadline-loss")
            print(f"Watch briefing, manual hold, exact saved continuation, one-time reward and deadline passed ({backend}): {output}")
        finally:
            game._teardown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/shardbound-watch"))
    verify(parser.parse_args().output)
