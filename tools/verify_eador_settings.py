"""Render Shardbound settings and exercise native keyboard input, silently.

    uv run python tools/verify_eador_settings.py --out /tmp/shardbound-settings

Settings is reached through the title and in-game guide using native keys.
"""

import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

os.environ.setdefault("SAGA2D_SILENT", "1")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from eador.app import create_game  # noqa: E402
from eador.preferences import DEFAULTS, load_preferences, reduced_motion  # noqa: E402
from eador.scene import HelpScene, TitleScene  # noqa: E402
from eador.settings_scene import SettingsScene  # noqa: E402
from saga2d.testing.native_frames import tick
from saga2d import Button  # noqa: E402
from pyglet.window import key, mouse  # noqa: E402


def press(game, symbol):
    game.backend.window.dispatch_event("on_key_press", symbol, 0)
    tick(game)
    game.backend.window.dispatch_event("on_key_release", symbol, 0)
    tick(game)


def click(game, label):
    control = game.scene.ui.find(lambda child: isinstance(child, Button) and child.text == label)
    assert control is not None, label
    x, y, w, h = control.bounds
    window = game.backend.window
    scale = min(window.width / game.width, window.height / game.height)
    px = (window.width - game.width * scale) / 2 + (x + w / 2) * scale
    py = (window.height - game.height * scale) / 2 + (game.height - y - h / 2) * scale
    window.dispatch_event("on_mouse_press", round(px), round(py), mouse.LEFT, 0)
    window.dispatch_event("on_mouse_release", round(px), round(py), mouse.LEFT, 0)
    tick(game)


def verify_display(out):
    observations = []

    def capture(game, name):
        for _ in range(3):
            tick(game)
        game.backend.capture_frame().save(out / f"{name}.png")
        observations.append(dict(name=name, fullscreen=game.fullscreen, window_size=game.window_size,
                                 windowed_size=game.windowed_size, canvas=game.resolution,
                                 reduced_motion=reduced_motion(game)))
        assert game.resolution == (1280, 800)

    with TemporaryDirectory(prefix="shardbound-display-preferences-") as directory:
        data = Path(directory)
        game = create_game("Shardbound display verification", visible=False, save_dir=data / "saves")
        try:
            title = TitleScene()
            game.push(title)
            tick(game)
            game.backend.window.set_size(940, 720)  # Simulates an OS resize outside the Game API.
            tick(game)
            assert game.window_size == game.windowed_size == (940, 720)
            press(game, key.O)
            click(game, "Display")
            capture(game, "display-os-resized")
            click(game, "Go fullscreen")
            capture(game, "display-fullscreen-preview")
            click(game, "Cancel")  # Native mouse coordinates cross letterboxing.
            assert game.scene is title and not game.fullscreen and game.window_size == (940, 720)
            game.set_fullscreen(True)
            press(game, key.O)
            for symbol in (key.D, key.RIGHT, key.DOWN, key.RIGHT, key.DOWN, key.RIGHT):
                press(game, symbol)
            assert game.fullscreen and game.windowed_size == (960, 600) and reduced_motion(game)
            capture(game, "display-reduced-motion-preview")
            press(game, key.ESCAPE)
            assert game.fullscreen and game.windowed_size == (940, 720) and not reduced_motion(game)
            game.set_fullscreen(False)
            assert game.window_size == (940, 720)
            # Apply both tabs, then exercise the actual startup restoration path.
            press(game, key.O)
            click(game, "Display")
            click(game, "+")
            click(game, "Go fullscreen")
            click(game, "Reduce motion")
            click(game, "Sound")
            press(game, key.LEFT)
            click(game, "Apply")
            assert game.fullscreen and game.windowed_size == (960, 600)
        finally:
            game._teardown()
            game.backend.quit()
        game = create_game("Shardbound display restart", save_dir=data / "saves")
        try:
            game.backend.window.set_visible(False)
            assert game.fullscreen and game.windowed_size == (960, 600)
            assert reduced_motion(game) and game.audio.get_volume("master") == .7
            game.push(TitleScene())
            press(game, key.O)
            press(game, key.D)
            capture(game, "display-restarted-fullscreen")
            press(game, key.ESCAPE)
            game.set_fullscreen(False)
            assert game.window_size == (960, 600)
            press(game, key.O)
            press(game, key.D)
            capture(game, "display-restored-windowed")
        finally:
            game._teardown()
            game.backend.quit()
        game = create_game("Shardbound hidden smoke display", visible=False, save_dir=data / "saves")
        try:
            assert not game.fullscreen and game.window_size == (1280, 800)
            game.push(TitleScene())
            capture(game, "display-hidden-launch-override")
        finally:
            game._teardown()
            game.backend.quit()
    (out / "display-report.json").write_text(json.dumps(observations, indent=2) + "\n")


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
            game = create_game("Shardbound settings verification", resolution=(1280, 800),
                        visible=False, save_dir=data / "saves")
            try:
                game.set_window_size(resolution)
                prefs = load_preferences(game)
                if scenario == "write-error":
                    prefs.save()
                    prefs.path.with_suffix(".backup.json").mkdir()
                title = TitleScene()
                game.push(title)
                tick(game)
                game.backend.capture_frame().save(args.out / f"title-{scenario}.png")
                press(game, key.O)
                assert isinstance(game.scene, SettingsScene)
                tick(game)
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
    verify_display(args.out)
    print(f"Native display preview/restart, title/guide settings, recovery, preview/cancel and campaign-load independence passed: {args.out}")


if __name__ == "__main__":
    main()
