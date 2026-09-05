"""Frozen application entry; smoke mode renders without using player saves."""

import argparse
import json
import os
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory


def smoke(image_path: Path) -> None:
    os.environ["SAGA2D_SILENT"] = "1"
    from saga2d import Game
    from eador.codex import CodexScene
    from eador.rival_scene import RivalScene
    from eador.scene import BattleScene, ShardScene, TitleScene
    from eador.style import build_theme

    image_path = image_path.resolve()
    image_path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="shardbound-smoke-saves-") as saves:
        game = Game("Shardbound package verification", resolution=(1280, 800),
                    visible=False, save_dir=saves, theme=build_theme())
        from pyglet.window import key

        def press(symbol):
            game.backend.window.dispatch_event("on_key_press", symbol, 0)
            game.backend.window.dispatch_event("on_key_release", symbol, 0)
            game.tick(1 / 60)

        def capture(suffix):
            game.tick(1 / 60)
            game.backend.capture_frame().save(image_path.with_stem(image_path.stem + suffix))

        try:
            game.push(TitleScene(seed=7))
            capture("")
            press(key.ENTER)
            assert isinstance(game.scene, ShardScene)
            root = game.scene
            press(key.F5)
            saved = root.state.to_json()
            press(key.F9)
            assert game.scene.state.to_json() == saved
            root = game.scene
            capture("-shard")
            press(key.C)
            assert isinstance(game.scene, CodexScene)
            press(key._4)
            capture("-codex")
            press(key.ESCAPE)
            press(key.V)
            assert isinstance(game.scene, RivalScene)
            capture("-rival")
            press(key.L)
            assert game.scene is root and root.selected == root.state.rival.pos
            assert root.state.to_json() == saved
            for _ in range(6):
                if root.selected == (-1, 0):
                    break
                press(key.TAB)
            assert root.selected == (-1, 0)
            press(key.ENTER)
            assert isinstance(game.scene, BattleScene)
            press(key.F5)
            battle_saved = root.state.to_json()
            press(key.A)
            press(key.F9)
            assert isinstance(game.scene, BattleScene)
            assert game.scene.root.state.to_json() == battle_saved
            capture("-battle")
            press(key.T)
            assert isinstance(game.scene, ShardScene)
            report = {
                "frozen": bool(getattr(sys, "frozen", False)),
                "executable": sys.executable,
                "cwd": str(Path.cwd()),
                "platform": platform.platform(),
                "python": platform.python_version(),
                "title_and_shard_rendered": True,
                "save_load_roundtrip": True,
                "codex_and_rival_rendered": True,
                "battle_save_load_roundtrip": True,
                "native_input_journey": True,
                "image": str(image_path),
            }
            image_path.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")
        finally:
            game._teardown()
            game.backend.quit()


if __name__ == "__main__":
    if "--smoke-image" in sys.argv:
        parser = argparse.ArgumentParser(description="Verify the packaged Shardbound runtime")
        parser.add_argument("--smoke-image", required=True, type=Path)
        smoke(parser.parse_args().smoke_image)
    else:
        from eador.__main__ import main
        main()
