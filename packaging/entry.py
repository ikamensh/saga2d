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
    from eador.model import State
    from eador.scene import ShardScene, TitleScene
    from eador.style import build_theme

    image_path = image_path.resolve()
    image_path.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="shardbound-smoke-saves-") as saves:
        game = Game("Shardbound package verification", resolution=(1280, 800),
                    visible=False, save_dir=saves, theme=build_theme())
        try:
            game.push(TitleScene(seed=7))
            game.tick(1 / 60)
            game.backend.capture_frame().save(image_path)
            root = ShardScene(State.new(7))
            game.clear_and_push(root)
            game.tick(1 / 60)
            root.save_game()
            saved = root.state.to_json()
            root.load_game()
            game.tick(1 / 60)
            assert game.scene.state.to_json() == saved
            game.backend.capture_frame().save(image_path.with_stem(image_path.stem + "-shard"))
            report = {
                "frozen": bool(getattr(sys, "frozen", False)),
                "executable": sys.executable,
                "cwd": str(Path.cwd()),
                "platform": platform.platform(),
                "python": platform.python_version(),
                "title_and_shard_rendered": True,
                "save_load_roundtrip": True,
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
