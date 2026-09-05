"""Render Shardbound settings and exercise native keyboard input, silently.

    uv run python tools/verify_eador_settings.py --out /tmp/shardbound-settings

Settings is reached through the title and in-game guide using native keys.
"""

import argparse
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

os.environ.setdefault("SAGA2D_SILENT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eador.app import create_game# noqa: E402
from eador.preferences import DEFAULTS, load_preferences  # noqa: E402
from eador.scene import HelpScene, TitleScene  # noqa: E402
from eador.settings_scene import SettingsScene  # noqa: E402
from pyglet.window import key  # noqa: E402


def press(game, symbol):
    game.backend.window.dispatch_event("on_key_press", symbol, 0)
    game.tick(1 / 60)
    game.backend.window.dispatch_event("on_key_release", symbol, 0)
    game.tick(1 / 60)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("/tmp/shardbound-settings"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for scenario, resolution in (("normal", (1280, 800)), ("compact", (1280, 720)),
                                 ("damaged", (1280, 800)), ("write-error", (1280, 800))):
        with TemporaryDirectory(prefix="shardbound-preferences-") as directory:
            data = Path(directory)
            if scenario == "damaged":
                (data / "settings.json").write_bytes(b"\xffdamaged")
            game = create_game("Shardbound settings verification", resolution=resolution,
                        visible=False, save_dir=data / "saves")
            try:
                prefs = load_preferences(game)
                if scenario == "write-error":
                    prefs.save()
                    prefs.path.with_suffix(".backup.json").mkdir()
                title = TitleScene()
                game.push(title)
                game.tick(1 / 60)
                game.backend.capture_frame().save(args.out / f"title-{scenario}.png")
                press(game, key.O)
                assert isinstance(game.scene, SettingsScene)
                game.tick(1 / 60)
                if scenario in ("normal", "compact"):
                    press(game, key.LEFT)
                    press(game, key.DOWN)
                    press(game, key.LEFT)
                    assert game.audio.get_volume("master") == .7
                    assert game.audio.get_volume("music") == .4
                elif scenario == "write-error":
                    press(game, key.LEFT)
                    press(game, key.ENTER)
                    assert isinstance(game.scene, SettingsScene)
                    assert "Could not apply" in game.scene.message
                game.backend.capture_frame().save(args.out / f"settings-{scenario}.png")
                if scenario == "damaged":
                    press(game, key.R)
                    press(game, key.ENTER)
                    assert game.scene is title
                    assert [p.read_bytes() for p in data.glob("settings.recovery-*.json")] == [b"\xffdamaged"]
                else:
                    press(game, key.ESCAPE)
                    assert game.scene is title
                    assert game.audio.get_volume("master") == DEFAULTS["master"]
                if scenario == "normal":
                    press(game, key.ENTER)
                    root = game.scene
                    press(game, key.F5)
                    saved = root.state.to_json()
                    press(game, key.F1)
                    assert isinstance(game.scene, HelpScene)
                    game.backend.capture_frame().save(args.out / "guide-entry.png")
                    press(game, key.O)
                    assert isinstance(game.scene, SettingsScene)
                    for _ in range(3):
                        press(game, key.DOWN)
                    press(game, key.RIGHT)
                    assert game.audio.muted
                    press(game, key.ENTER)
                    assert isinstance(game.scene, HelpScene)
                    press(game, key.ESCAPE)
                    press(game, key.F9)
                    assert game.scene.state.to_json() == saved and game.audio.muted
                assert game.backend.window is not None
            finally:
                game._teardown()
                game.backend.quit()
    print(f"Native title/guide settings, recovery, preview/cancel and campaign-load independence passed: {args.out}")


if __name__ == "__main__":
    main()
