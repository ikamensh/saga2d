"""Real Pyglet input journeys for rival inspection, interception and defense."""

import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["SAGA2D_SILENT"] = "1"

from tools.native_frames import tick
from eador.app import create_game
from eador.model import State
from eador.rival_scene import RivalScene
from eador.scene import BattleScene, ChoiceScene, SaveScene, ShardScene, TitleScene


def verify(output):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="shardbound-rival-") as saves:
        game = create_game("Shardbound rival verification", resolution=(1280, 800), visible=False, save_dir=Path(saves) / "saves")
        from pyglet.window import key, mouse

        window = game.backend.window

        def press(symbol):
            window.dispatch_event("on_key_press", symbol, 0)
            window.dispatch_event("on_key_release", symbol, 0)
            tick(game)

        def capture(name):
            tick(game)
            game.backend.capture_frame().save(output / f"{name}.png")

        def travel(pos):
            x, y = root.grid.center(pos)
            scale = min(window.width / game.width, window.height / game.height)
            px = (window.width - game.width * scale) / 2 + x * scale
            py = (window.height - game.height * scale) / 2 + (game.height - y) * scale
            window.dispatch_event("on_mouse_press", round(px), round(py), mouse.LEFT, 0)
            window.dispatch_event("on_mouse_release", round(px), round(py), mouse.LEFT, 0)
            tick(game)
            assert root.selected == pos, (root.selected, pos, type(game.scene).__name__)
            press(key.ENTER)

        def resolve():
            assert isinstance(game.scene, BattleScene)
            for _ in range(80):
                if root.state.battle.outcome:
                    break
                press(key.A)
            assert root.state.battle.outcome == "player"
            press(key.E)
            while isinstance(game.scene, ChoiceScene):
                press(key._1)
            assert game.scene is root

        try:
            game.push(TitleScene(seed=7))
            press(key.ENTER)
            root = game.scene
            assert isinstance(root, ShardScene)
            press(key.V)
            assert isinstance(game.scene, RivalScene)
            capture("rival-initial")
            press(key.L)
            assert root.selected == root.state.rival.pos
            capture("rival-located")
            press(key.B)
            press(key._1)
            press(key.ESCAPE)
            press(key.R)
            press(key._2)
            press(key.ESCAPE)
            press(key.X)
            resolve()
            press(key.H)
            press(key._1)
            press(key.ESCAPE)
            assert root.state.hero.relic == "moonstone"
            press(key.E)
            for pos in ((-1, 0), (0, 0)):
                travel(pos)
                if isinstance(game.scene, BattleScene):
                    resolve()
                press(key.E)
            assert root.state.rival.target == root.state.hero.pos
            assert root.state.rival.intent == "attack"
            central = root.state.to_json()
            press(key.F5)
            capture("rival-warning")
            press(key.V)
            capture("rival-after-conquest")
            press(key.ESCAPE)
            travel(root.state.rival.pos)
            assert root.state.battle_kind == "intercept"
            press(key.A)
            press(key.A)
            capture("rival-interception")
            wounded = {u.source_id: u.hp for u in root.state.battle.units if u.team == "enemy" and u.alive}
            press(key.T)
            assert {t.id: t.hp for t in root.state.rival.army} == wounded
            assert root.state.rival.intent == "return"
            press(key.V)
            capture("rival-retreat-survivors")
            press(key.ESCAPE)
            press(key.F6)
            assert isinstance(game.scene, SaveScene)
            press(key.TAB)
            press(key._2)
            press(key.ESCAPE)
            after_retreat = root.state.to_json()
            press(key.F6)
            press(key._2)
            root = game.scene
            assert root.state.to_json() == after_retreat
            travel(root.state.rival.pos)
            assert {u.source_id: u.hp for u in root.state.battle.units if u.team == "enemy"} == wounded
            resolve()
            assert not root.state.rival.army
            press(key.F9)
            root = game.scene
            assert root.state.to_json() == central
            for _ in range(root.state.rival.turns_until_action):
                press(key.E)
            assert root.state.battle_kind == "defense"
            capture("rival-defense")
            resolve()
            assert not root.state.rival.army
            countdown = root.state.rival.turns_until_action
            press(key.V)
            capture("rival-counterattack-window")
            press(key.ESCAPE)
            press(key.F5)
            press(key.F9)
            root = game.scene
            assert not root.state.rival.army
            for remaining in range(countdown - 1, 0, -1):
                press(key.E)
                assert not root.state.rival.army
                assert root.state.rival.turns_until_action == remaining
            press(key.E)
            assert len(root.state.rival.army) == 1
            press(key.V)
            capture("rival-paid-recruit")
            press(key.ESCAPE)

            # Resume an earned pre-pressure save, advanced with public commands
            # to the next unpaid bill. The loaded UI journey then warns, loses
            # troops, reloads and breaks out through actual input.
            supply = State.from_json((Path(__file__).resolve().parents[1] /
                                     "tests/eador/fixtures/v3_fortified_capital.json").read_text())
            for _ in range(100):
                if supply.upkeep_shortfall:
                    break
                supply.end_turn()
            assert supply.encircled and supply.upkeep_shortfall
            root.saves.save(supply, 3)
            press(key.F6)
            press(key._3)
            root = game.scene
            assert root.state.upkeep_shortfall == supply.upkeep_shortfall
            capture("supply-shortfall")
            press(key.V)
            capture("supply-breakout-routes")
            press(key.ESCAPE)
            count = len(root.state.hero.army)
            press(key.E)
            assert len(root.state.hero.army) < count
            assert "deserted" in root.message
            capture("supply-desertion")
            press(key.F6)
            press(key._3)
            root = game.scene
            assert root.state.to_json() == supply.to_json()
            destination = min((pos for pos in root.grid.neighbors(root.state.hero.pos)
                               if pos != root.state.rival.pos),
                              key=lambda pos: (len(root.state.provinces[pos].guards), pos))
            travel(destination)
            if isinstance(game.scene, BattleScene):
                resolve()
            assert not root.state.encircled and root.state.income > 0
            capture("supply-restored")
            print(f"Real rival inspection, interception, wound/save continuity, defense, paid rebuilding and supply breakout passed. Screenshots: {output}")
        finally:
            game._teardown()
            game.backend.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/shardbound-rival"))
    verify(parser.parse_args().output)
