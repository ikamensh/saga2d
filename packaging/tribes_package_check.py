"""Diagnostics executed inside the frozen Tribes application, without a source checkout."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time


def online_smoke(endpoint: str) -> dict:
    """Two real WebSocket clients take server-owned turns and reclaim a seat."""
    if not endpoint:
        raise ValueError("The package smoke check requires an explicit --endpoint")
    from saga2d.online import OnlineClient

    clients = []

    def wait(condition):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            for client in clients:
                client.poll()
            if condition():
                return
            time.sleep(.02)
        raise AssertionError([(client.ready, client.closed, client.error) for client in clients])

    try:
        creator = OnlineClient("tribes-v1", endpoint=endpoint, options={"seed": 7, "size": 11})
        clients.append(creator)
        wait(lambda: bool(creator.room) and creator.state is not None)
        assert creator.resume_token and not creator.ready and creator.retention
        guest = OnlineClient("tribes-v1", endpoint=endpoint, room=creator.room)
        clients.append(guest)
        wait(lambda: creator.ready and guest.ready)
        assert (creator.player, guest.player) == (0, 1)
        assert creator.state["world"]["current"] == 0
        guest.submit({"action": "end_turn"})
        wait(lambda: bool(guest.error))
        assert "turn" in guest.error.lower(), guest.error
        guest.error = ""
        creator.submit({"action": "end_turn"})
        wait(lambda: creator.state["world"]["current"] == 1 and guest.state["world"]["current"] == 1)
        room, token = creator.room, creator.resume_token
        creator.close()
        wait(lambda: not guest.ready)
        resumed = OnlineClient("tribes-v1", endpoint=endpoint, room=room, resume_token=token)
        clients.append(resumed)
        wait(lambda: resumed.ready and guest.ready)
        assert resumed.player == 0 and resumed.state["world"]["current"] == 1
        guest.submit({"action": "end_turn"})
        wait(lambda: resumed.state["world"]["current"] == 0 and resumed.state["world"]["round"] == 2)
        return {"create_join": True, "foreign_turn_rejected": True, "authoritative_turns": True,
                "private_seat_rejoin": True}
    finally:
        for client in clients:
            client.close()


def build_info() -> dict:
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Package acceptance must run the frozen executable")
    info = json.loads((Path(sys._MEIPASS) / "release" / "build-info.json").read_text(encoding="utf-8"))
    with Path(sys.executable).open("rb") as stream:
        info["executable_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    info["executable"] = str(Path(sys.executable).resolve())
    return info


def smoke(endpoint: str) -> dict:
    from saga2d import fonts
    info = build_info()
    for filename in (*fonts.FILES.values(), "OFL.txt"):
        assert (fonts.FONT_DIR / filename).is_file(), filename
    return {"passed": True, "source_commit": info["source_commit"], "version": info["version"], "frozen": True,
            "executable": info["executable"], "executable_sha256": info["executable_sha256"],
            "bundled_fonts": True, "online": online_smoke(endpoint)}


def native_smoke(output: Path, endpoint: str) -> dict:
    """Use native clipboard/buttons to create and join a real online match in the package."""
    if not endpoint:
        raise ValueError("Native multiplayer acceptance requires an explicit --endpoint")
    os.environ["SAGA2D_SILENT"] = "1"
    os.environ["SAGA2D_HEADLESS"] = "1"
    os.environ["SAGA2D_SERVER_URL"] = endpoint
    from PIL import ImageStat
    from pyglet import gl
    from pyglet.window import key
    from saga2d import Game, MatchMenu, fonts
    from saga2d.multiplayer_ui import MatchLobby
    from saga2d.online import OnlineClient
    from tribes import effects
    from tribes.multiplayer import NetworkMapScene
    from tribes.scene import DEFAULT_SETTINGS, PauseScene, new_game
    from tribes.sound import SoundBank
    from tribes.style import build_theme
    from tribes.title import TitleScene

    info = build_info()
    images = []
    with tempfile.TemporaryDirectory(prefix="tribes-native-") as profile:
        game = Game("Tribes", resolution=(1280, 800), visible=False, save_dir=Path(profile) / "saves", theme=build_theme())
        creator = None
        clipboard = game.backend.get_clipboard_text()
        try:
            fonts.load(game)
            bank = SoundBank(game, Path(profile) / "audio")
            effects.sound_hook = bank.play
            effects.volume_hook = bank.set_volume
            effects.apply_volumes(DEFAULT_SETTINGS)

            def frames(count=3):
                for _ in range(count):
                    started = time.monotonic()
                    game.tick(1 / 30)
                    if creator is not None:
                        creator.poll()
                    time.sleep(max(0, 1 / 30 - (time.monotonic() - started)))

            def wait(condition):
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    frames(1)
                    if condition():
                        return
                raise AssertionError(f"Native online flow stopped at {type(game.scene).__name__}")

            def press(symbol, modifiers=0):
                game.backend.window.dispatch_event("on_key_press", symbol, modifiers)
                game.backend.window.dispatch_event("on_key_release", symbol, modifiers)
                frames()

            def click(text):
                from pyglet.window import mouse
                button = next(b for b in game.scene.ui.walk() if getattr(b, "text", "") == text)
                x, y, w, h = button.bounds
                px = int((x + w / 2) * game.backend.scale_factor + game.backend.offset_x)
                py = int((game.height - y - h / 2) * game.backend.scale_factor + game.backend.offset_y)
                game.backend.window.dispatch_event("on_mouse_motion", px, py, 0, 0)
                game.backend.window.dispatch_event("on_mouse_press", px, py, mouse.LEFT, 0)
                game.backend.window.dispatch_event("on_mouse_release", px, py, mouse.LEFT, 0)
                frames()

            def capture(suffix):
                frames()
                image = game.backend.capture_frame()
                assert sum(ImageStat.Stat(image.convert("RGB")).stddev) > 10, "The native frame is blank"
                path = output.with_name(output.stem + suffix + output.suffix)
                image.save(path)
                images.append(path.name)

            game.push(TitleScene(settings=dict(DEFAULT_SETTINGS)))
            capture("-title")
            press(key.M)
            assert isinstance(game.scene, MatchMenu)
            capture("-multiplayer")
            click("Create room")
            wait(lambda: isinstance(game.scene, MatchLobby) and game.scene.session.state is not None)
            session = game.scene.session
            room, token = session.room, session.resume_token
            click("Copy room code")
            assert game.backend.get_clipboard_text() == room
            click("Copy invite link")
            assert game.backend.get_clipboard_text().endswith(f"/join/tribes-v1/{room}")
            assert token not in game.backend.get_clipboard_text()
            capture("-room-code")
            click("Cancel")
            creator = OnlineClient("tribes-v1", endpoint=endpoint, room=room, resume_token=token)
            wait(lambda: creator.state is not None)
            game.backend.set_clipboard_text(room)
            click("Paste code")
            assert game.scene.fields[2] == room.upper()
            press(key.V, key.MOD_COMMAND if sys.platform == "darwin" else key.MOD_CTRL)
            assert game.scene.fields[2] == room.upper()
            capture("-paste-code")
            press(key.ENTER)
            wait(lambda: isinstance(game.scene, NetworkMapScene) and game.scene.session.ready)
            live = game.scene
            assert live.human == 1 and live.world.current == 0
            creator.submit({"action": "end_turn"})
            wait(lambda: live.world.current == 1)
            capture("-online-match")
            press(key.E)  # Arm, then confirm, the native End turn control.
            press(key.E)
            wait(lambda: live.world.current == 0 and creator.state["world"]["current"] == 0)
            press(key.ESCAPE)
            assert isinstance(game.scene, PauseScene)
            capture("-pause-menu")
            click("Back to title")
            wait(lambda: isinstance(game.scene, TitleScene))
            game.clear_and_push(new_game(3, size=11, settings=dict(DEFAULT_SETTINGS)))
            capture("")
            assert game.scene.world.tribes and game.scene.world.units
            return {"passed": True, "source_commit": info["source_commit"], "version": info["version"],
                    "executable": info["executable"], "executable_sha256": info["executable_sha256"],
                    "renderer": gl.gl_info.get_renderer(), "opengl_version": gl.gl_info.get_version_string(), "vendor": gl.gl_info.get_vendor(),
                    "backend": "pyglet", "native_multiplayer_input": True, "native_clipboard_join": True,
                    "native_invite_link": True, "native_turn_exchange": True,
                    "sound_catalogue": len(bank.names), "images": images}
        finally:
            game.backend.set_clipboard_text(clipboard)
            game.close()
            if creator is not None:
                creator.close()
