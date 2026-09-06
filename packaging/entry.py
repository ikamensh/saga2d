"""Frozen application entry; smoke mode renders without using player saves."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import sys
from tempfile import TemporaryDirectory
import time
import wave


def decode_audio_catalogue(assets: Path) -> dict:
    """Decode every shipping WAV and verify its installed bytes against provenance."""
    manifest = json.loads((assets / "audio-manifest.json").read_text(encoding="utf-8"))
    files = {}
    actual = {path.relative_to(assets).as_posix() for path in assets.rglob("*.wav")}
    if actual != set(manifest["files"]):
        raise RuntimeError("Installed audio catalogue differs from manifest")
    for name, expected in manifest["files"].items():
        path = assets / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected["sha256"] or path.stat().st_size != expected["bytes"]:
            raise RuntimeError(f"Audio asset differs from manifest: {name}")
        with wave.open(str(path), "rb") as stream:
            channels, frames, rate = stream.getnchannels(), stream.getnframes(), stream.getframerate()
            if (stream.getsampwidth() != 2 or stream.getcomptype() != "NONE"
                    or channels != expected["channels"] or frames != expected["frames"]
                    or rate != manifest["sample_rate"]
                    or len(stream.readframes(frames)) != frames * channels * 2):
                raise RuntimeError(f"Audio format differs from manifest: {name}")
        files[name] = {"sha256": digest, "bytes": expected["bytes"], "channels": channels,
                       "frames": frames, "sample_rate": rate, "seconds": frames / rate}
    return files


def verify_audio_playback(game, files: dict) -> None:
    """Start the installed catalogue on the native silent driver, checking mix and lifetime.

    Native player inspection is diagnostic evidence; playback uses game.audio.
    Full musical loops and listening quality are separate audio verification.
    """
    def pump(seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            game.tick()
            time.sleep(1 / 30)

    game.audio.stop_music()
    longest_cue = max(record["seconds"] for name, record in files.items() if name.startswith("sounds/"))
    pump(longest_cue + .3)  # Let any scene-action cues finish before catalogue inspection.
    assert not game.backend._players
    game.audio.muted = False
    game.audio.set_volume("master", .5)
    game.audio.set_volume("sfx", .4)
    players = []
    for name in files:
        if name.startswith("sounds/"):
            game.audio.play_sound(Path(name).stem, volume=.5)
            players.append(list(game.backend._players.values())[-1])
    assert len(game.backend._sound_players) == len(players)
    assert all(player.playing and abs(player.volume - .1) < 1e-8 for player in players)
    game.audio.muted = True
    game.audio.set_volume("master", .25)
    assert all(player.volume == 0 for player in players)
    game.audio.muted = False
    assert all(abs(player.volume - .05) < 1e-8 for player in players)
    pump(longest_cue + .5)
    assert not game.backend._sound_players
    assert all(not player.playing and player.source is None for player in players)
    for name in files:
        if name.startswith("music/"):
            game.audio.play_music(Path(name).stem)
            player = list(game.backend._players.values())[-1]
            pump(.25)
            assert player.playing and player.time > 0
            game.audio.muted = True
            game.audio.set_volume("music", .2)
            assert player.volume == 0
            game.audio.muted = False
            assert abs(player.volume - .05) < 1e-8
            game.audio.stop_music()
            assert not player.playing and player._audio_player is None
    assert not game.backend._players


def smoke(image_path: Path) -> None:
    os.environ["SAGA2D_SILENT"] = "1"
    import eador
    from saga2d import Game
    from eador.codex import CodexScene
    from eador.rival_scene import RivalScene
    from eador.scene import BattleScene, ShardScene, TitleScene
    from eador.preferences import load_preferences
    from eador.settings_scene import SettingsScene
    from eador.__main__ import create_session
    from eador.diagnostics import DiagnosticScene
    from eador.release import build_label

    image_path = image_path.resolve()
    image_path.parent.mkdir(parents=True, exist_ok=True)
    assets = Path(eador.__file__).resolve().parent / "assets"
    audio_files = decode_audio_catalogue(assets)
    with TemporaryDirectory(prefix="shardbound-smoke-saves-") as saves:
        game, title = create_session(['--data-dir', saves], title='Shardbound package verification', visible=False)
        assert game.data_dir == Path(saves).resolve()
        from pyglet.window import key

        def press(symbol):
            game.backend.window.dispatch_event("on_key_press", symbol, 0)
            game.backend.window.dispatch_event("on_key_release", symbol, 0)
            game.tick(1 / 60)
            time.sleep(1 / 30)

        def capture(suffix):
            game.tick(1 / 60)
            game.backend.capture_frame().save(image_path.with_stem(image_path.stem + suffix))
            time.sleep(1 / 30)

        try:
            preferences = load_preferences(game)
            assert preferences.error is None
            game.push(title)
            capture("")
            press(key.A)
            assert isinstance(game.scene, DiagnosticScene)
            label = build_label()
            assert label in game.scene.message and str(game.data_dir) in game.scene.message
            if getattr(sys, 'frozen', False):
                info = json.loads((Path(sys._MEIPASS) / 'release' / 'build-info.json').read_text(encoding='utf-8'))
                assert info['source_commit'][:12] in label and info['version'] in label
            about = game.scene
            for index in range(about.pages):
                assert about.page == index
                capture(f'-about-{index + 1}')
                press(key.PAGEDOWN)
            press(key.ESCAPE)
            assert game.scene is title
            press(key.O)
            assert isinstance(game.scene, SettingsScene)
            press(key.LEFT)
            press(key.DOWN)
            press(key.LEFT)
            capture("-settings")
            press(key.ENTER)
            assert isinstance(game.scene, TitleScene)
            preferences.load()
            assert preferences["master"] == .7 and preferences["music"] == .4
            press(key.O)
            press(key.LEFT)
            press(key.ESCAPE)
            assert game.audio.get_volume("master") == .7
            saved_preferences = preferences.path.read_bytes()
            press(key.ENTER)
            assert isinstance(game.scene, ShardScene)
            root = game.scene
            press(key.F5)
            saved = root.state.to_json()
            press(key.F9)
            assert game.scene.state.to_json() == saved
            root = game.scene
            capture("-shard")
            press(key.F1)
            guide = game.scene
            capture('-guide')
            press(key.A)
            assert isinstance(game.scene, DiagnosticScene) and build_label() in game.scene.message
            press(key.ESCAPE)
            assert game.scene is guide and root.state.to_json() == saved
            press(key.ESCAPE)
            assert game.scene is root
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
            press(key.G)
            assert game.scene.root.state.battle.unit(0).stance == "guard"
            press(key.F5)
            battle_saved = root.state.to_json()
            press(key.A)
            press(key.F9)
            assert isinstance(game.scene, BattleScene)
            assert game.scene.root.state.to_json() == battle_saved
            assert game.scene.root.state.battle.unit(0).stance == "guard"
            capture("-battle")
            press(key.T)
            assert isinstance(game.scene, ShardScene)
            assert preferences.path.read_bytes() == saved_preferences
            verify_audio_playback(game, audio_files)
            report = {
                "frozen": bool(getattr(sys, "frozen", False)),
                "executable": sys.executable,
                "cwd": str(Path.cwd()),
                "platform": platform.platform(),
                "python": platform.python_version(),
                "title_and_shard_rendered": True,
                "about_build_label": label,
                "about_pages_rendered": about.pages,
                "guide_about_return_preserves_campaign": True,
                "isolated_launch_data_directory": str(game.data_dir),
                "save_load_roundtrip": True,
                "codex_and_rival_rendered": True,
                "battle_save_load_roundtrip": True,
                "guard_save_load_roundtrip": True,
                "native_input_journey": True,
                "audio_catalogue_decoded_and_played": True,
                "audio_live_mix_and_cleanup": True,
                "asset_path": str(assets),
                "audio_files": audio_files,
                "image": str(image_path),
            }
        finally:
            game._teardown()
            game.backend.quit()
        restarted = Game("Shardbound settings restart verification", visible=False,
                         resolution=(64, 64), save_dir=Path(saves) / "saves", asset_path=assets)
        try:
            preferences = load_preferences(restarted)
            assert preferences.error is None and preferences.path.read_bytes() == saved_preferences
            assert restarted.audio.get_volume("master") == .7
            assert restarted.audio.get_volume("music") == .4
            assert not restarted.audio.muted
            report["settings_apply_cancel_restart"] = True
        finally:
            restarted._teardown()
            restarted.backend.quit()
        image_path.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    if "--campaign-check" in sys.argv:
        from campaign_check import run
        parser = argparse.ArgumentParser(description="Verify one isolated packaged campaign phase")
        parser.add_argument("--campaign-check", required=True, type=Path)
        parser.add_argument("--phase", required=True, type=int, choices=range(1, 6))
        parser.add_argument("--recovery", action="store_true")
        args = parser.parse_args()
        run(args.campaign_check, phase=args.phase, recovery=args.recovery)
    elif "--smoke-image" in sys.argv:
        parser = argparse.ArgumentParser(description="Verify the packaged Shardbound runtime")
        parser.add_argument("--smoke-image", required=True, type=Path)
        smoke(parser.parse_args().smoke_image)
    else:
        from eador.__main__ import main
        main()
