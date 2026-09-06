"""Exercise defensive orders with native Pyglet input and capture their UI."""

import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["SAGA2D_SILENT"] = "1"

from saga2d import Button

from eador.app import create_game
from eador.scene import BattleScene, TitleScene


def verify(output):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="shardbound-guard-") as saves:
        game = create_game("Shardbound defensive orders", resolution=(1280, 800), visible=False, save_dir=Path(saves) / "saves")
        from pyglet.window import key, mouse

        window = game.backend.window

        def press(symbol):
            window.dispatch_event("on_key_press", symbol, 0)
            window.dispatch_event("on_key_release", symbol, 0)
            game.tick(1 / 60)

        def capture(name):
            game.tick(1 / 60)
            game.backend.capture_frame().save(output / f"{name}.png")

        def button(label):
            control = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == label)
            assert control is not None and control.enabled, label
            x, y, width, height = control.bounds
            scale = min(window.width / game.width, window.height / game.height)
            px = (window.width - game.width * scale) / 2 + (x + width / 2) * scale
            py = (window.height - game.height * scale) / 2 + (game.height - y - height / 2) * scale
            window.dispatch_event("on_mouse_press", round(px), round(py), mouse.LEFT, 0)
            window.dispatch_event("on_mouse_release", round(px), round(py), mouse.LEFT, 0)
            game.tick(1 / 60)

        try:
            game.push(TitleScene(seed=7))
            for symbol in (key.ENTER, key.B, key._1, key.ESCAPE, key.R):
                press(symbol)
            capture("pikeman-recruitment")
            press(key._5)
            press(key.ESCAPE)
            root = game.scene
            assert root.state.hero.army[-1].kind == "pikeman"
            press(key.F1)
            capture("guide")
            press(key.ESCAPE)
            press(key.C)
            while not any(entry.title == "Pikeman" for entry in game.scene.visible_entries):
                assert game.scene.page + 1 < game.scene.pages
                press(key.RIGHT)
            capture("pikeman-codex")
            press(key.ESCAPE)
            press(key.TAB)
            press(key.ENTER)
            assert isinstance(game.scene, BattleScene)
            press(key.G)
            hero = root.state.battle.unit(0)
            assert hero.stance == "guard" and hero.effective_defense == hero.defense + 2
            capture("hero-guard")
            press(key.F5)
            saved = root.state.to_json()
            press(key.E)
            assert root.state.battle.unit(0).stance is None
            press(key.F9)
            root = game.scene.root
            assert root.state.to_json() == saved
            for _ in range(len(root.state.battle.units)):
                if root.state.battle.unit(game.scene.selected).kind == "pikeman":
                    break
                press(key.TAB)
            assert root.state.battle.unit(game.scene.selected).kind == "pikeman"
            button("Brace")
            assert root.state.battle.unit(game.scene.selected).stance == "brace"
            capture("pikeman-brace")
            saved = root.state.to_json()
            press(key.G)
            assert root.state.to_json() == saved
            press(key.F5)
            press(key.E)
            assert all(unit.stance is None for unit in root.state.battle.units if unit.team == "player")
            capture("stances-expired")
            press(key.F9)
            assert game.scene.root.state.to_json() == saved
            capture("stances-restored")
            print(f"Native recruitment, Guard/Brace, disabled shortcut, expiry and exact save restoration passed: {output}")
        finally:
            game._teardown()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/shardbound-guard"))
    verify(parser.parse_args().output)
