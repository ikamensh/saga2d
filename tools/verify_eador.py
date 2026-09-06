"""Render Shardbound and verify real pyglet keyboard/mouse scene transitions.

Run: ``uv run python tools/verify_eador.py --output /tmp/shardbound``.
Open the resulting PNGs before shipping visual changes. Requires an awake
display on macOS; windows stay hidden and save files live in a temp folder.
"""

import argparse
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["SAGA2D_SILENT"] = "1"

from tools.native_frames import tick
from saga2d import Button

from eador.app import create_game
from eador.codex import CodexScene
from eador.scene import BattleScene, CatalogScene, ChoiceScene, HelpScene, HeroScene, SaveScene, ShardScene, TitleScene


def verify(output: Path):
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="shardbound-verify-") as saves:
        game = create_game("Shardbound verification", resolution=(1280, 800), visible=False, save_dir=Path(saves) / "saves")
        from pyglet.window import key, mouse

        window = game.backend.window

        def press(symbol, modifiers=0):
            window.dispatch_event("on_key_press", symbol, modifiers)
            window.dispatch_event("on_key_release", symbol, modifiers)
            tick(game)

        def click(x, y):
            scale = min(window.width / game.width, window.height / game.height)
            px = (window.width - game.width * scale) / 2 + x * scale
            py = (window.height - game.height * scale) / 2 + (game.height - y) * scale
            window.dispatch_event("on_mouse_press", round(px), round(py), mouse.LEFT, 0)
            window.dispatch_event("on_mouse_release", round(px), round(py), mouse.LEFT, 0)
            tick(game)

        def capture(name):
            tick(game)
            game.backend.capture_frame().save(output / f"{name}.png")

        def button(label):
            control = game.scene.ui.find(lambda item: isinstance(item, Button) and item.text == label)
            assert control is not None, label
            x, y, w, h = control.bounds
            click(x + w / 2, y + h / 2)

        try:
            game.push(TitleScene(seed=7))
            capture("title")
            press(key.ENTER)
            assert isinstance(game.scene, ShardScene)
            root = game.scene
            capture("shard")
            press(key.C)
            assert isinstance(game.scene, CodexScene)
            for symbol, name in ((key._1, "troops"), (key._2, "spells"), (key._3, "buildings"),
                                 (key._4, "skills"), (key._5, "sites"), (key._6, "relics")):
                press(symbol)
                capture("codex-" + name)
            press(key.ESCAPE)
            assert game.scene is root
            press(key.B)
            assert isinstance(game.scene, CatalogScene)
            capture("buildings")
            press(key._1)
            assert "barracks" in root.state.buildings
            press(key.ESCAPE)
            assert game.scene is root and game.running
            press(key.R)
            capture("recruitment")
            press(key._2)
            assert root.state.hero.army[-1].kind == "swordsman"
            press(key.ESCAPE)
            press(key.F1)
            assert isinstance(game.scene, HelpScene)
            capture("guide")
            press(key.ESCAPE)
            click(*root.grid.center((-1, 0)))
            assert root.selected == (-1, 0)
            press(key.ENTER)
            assert isinstance(game.scene, BattleScene)
            capture("battle")
            press(key.F5)
            saved = root.state.to_json()
            press(key.A)
            press(key.F9)
            assert isinstance(game.scene, BattleScene)
            root = game.scene.root
            assert root.state.to_json() == saved
            for _ in range(40):
                if root.state.battle.outcome:
                    break
                press(key.A)
            assert root.state.battle.outcome == "player"
            capture("battle-victory")
            press(key.E)
            assert game.scene is root and root.state.hero.pos == (-1, 0)
            capture("conquest")
            press(key.E)
            press(key.X)
            assert isinstance(game.scene, BattleScene)
            for _ in range(40):
                if root.state.battle.outcome:
                    break
                press(key.A)
            assert root.state.battle.outcome == "player"
            press(key.E)
            assert isinstance(game.scene, ChoiceScene)
            capture("hero-choice")
            press(key.F5)
            pending = root.state.to_json()
            press(key._1)
            press(key.F9)
            assert isinstance(game.scene, ChoiceScene)
            root = game.scene.root
            assert root.state.to_json() == pending
            press(key._1)
            if isinstance(game.scene, ChoiceScene):
                capture("relic-choice")
                press(key._1)
            assert game.scene is root
            press(key.H)
            assert isinstance(game.scene, HeroScene)
            button("Equip")
            assert root.state.hero.relic == root.state.inventory[0]
            capture("hero-relics")
            press(key.ESCAPE)
            button("Save")
            assert isinstance(game.scene, SaveScene)
            press(key._2)
            capture("save-browser")
            button("Load slots")
            press(key._2)
            assert isinstance(game.scene, ShardScene)
            assert game.scene.state.to_json() == root.state.to_json()
            root = game.scene
            # A damaged current file is visible and does not replace live play.
            (Path(saves) / "saves" / "save_1.json").write_text("interrupted write")
            press(key.F9)
            assert game.scene is root and root.message
            press(key.F6)
            capture("damaged-save")
            press(key._1, key.MOD_SHIFT)
            assert isinstance(game.scene, BattleScene)
            press(key.F1)
            button("Save & title")
            assert isinstance(game.scene, SaveScene)
            capture("save-before-title")
            press(key._1)
            assert isinstance(game.scene, SaveScene) and game.scene.message
            capture("save-error")
            press(key._3)
            assert isinstance(game.scene, TitleScene)
            press(key.F6)
            press(key._3)
            assert isinstance(game.scene, BattleScene)
            # A new launch fixture, then a complete aimed keyboard sequence.
            game.clear_and_push(TitleScene(seed=7))
            tick(game)
            for _ in range(3):
                press(key.TAB)
            press(key.ENTER)
            root = game.scene
            assert root.state.hero.hero_class == "Wizard"
            for _ in range(6):
                press(key.TAB)
                if root.selected == (-1, 0):
                    break
            press(key.ENTER)
            assert isinstance(game.scene, BattleScene)
            b = root.state.battle
            before = root.state.to_json()
            press(key._1)
            press(key.UP)
            press(key.ENTER)
            assert root.state.to_json() == before  # Empty spell target.
            press(key.ESCAPE)
            press(key.ENTER)
            assert b.unit(0).pos == (-3, 0) and b.unit(0).moved
            press(key.E)
            mana = b.mana
            press(key._1)
            press(key.F)
            capture("keyboard-spell-target")
            press(key.ENTER)
            assert b.mana < mana
            archer = next(u for u in b.units if u.team == "player" and u.kind == "archer")
            for _ in range(6):
                press(key.TAB)
                if game.scene.selected == archer.id:
                    break
            press(key.F6)
            press(key.TAB)
            press(key._2)
            press(key.ESCAPE)
            saved = root.state.to_json()
            press(key.F)
            for width, height in ((1280, 720), (1280, 800), (1920, 1080)):
                window.set_size(width, height)
                capture(f"keyboard-target-{width}x{height}")
            press(key.ENTER)
            assert archer.acted
            press(key.F6)
            press(key._2)
            assert isinstance(game.scene, BattleScene)
            assert game.scene.root.state.to_json() == saved
            press(key.T)
            assert isinstance(game.scene, ShardScene)
            print(f"Real mouse/keyboard tactics, choices, equipment, slots, autosaves, recovery and window-size matrix passed. Screenshots: {output}")
        finally:
            game._teardown()
            game.backend.quit()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("/tmp/shardbound"))
    verify(parser.parse_args().output)
