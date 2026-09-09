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


def verify_forecast_save(save_path: Path, image_path: Path, *, backend='pyglet') -> dict:
    """Read the earned Control party's lethal attack through ordinary loaded-game controls."""
    from saga2d import Label
    from eador.__main__ import create_session
    from eador.model import State
    from eador.persistence import CampaignSaves
    from eador.preferences import reading_scale
    from eador.scene import BattleScene
    from tools.eador_ui import PlayerInput

    payload = save_path.read_bytes()
    initial = State.from_json(payload.decode('utf-8')).to_json()
    image_path = image_path.resolve()
    name = image_path.stem + '-forecast-125'
    with TemporaryDirectory(prefix='shardbound-forecast-saves-') as saves:
        game, title = create_session(['--data-dir', saves], backend=backend, visible=False)
        player = PlayerInput(game, native=backend == 'pyglet', output=image_path.parent)

        def labels():
            return [item.text for item in game.scene.ui.walk() if isinstance(item, Label)]

        def aim(ident):
            player.click(*game.scene.grid.center(player.state.battle.unit(ident).pos))
            assert game.scene.selected == ident
            player.press('f')
            assert game.scene.cursor == player.state.battle.unit(1011).pos

        try:
            CampaignSaves(game.save_manager).save(State.from_json(initial))
            game.push(title)
            player.press('f9')
            assert isinstance(game.scene, BattleScene) and player.state.to_json() == initial
            aim(6)
            forecast_100 = labels()
            assert any('Rune Adept falls.' in text for text in forecast_100)
            assert any('Tab selects another unit.' in text for text in forecast_100)
            assert reading_scale(game) == 100 and player.state.to_json() == initial
            for key in ('f2', 'right', 'return'):
                player.press(key)
            forecast_125 = labels()
            assert any('Rune Adept falls.' in text for text in forecast_125)
            assert any('Tab selects another unit.' in text for text in forecast_125)
            assert reading_scale(game) == 125 and player.state.to_json() == initial
            player.capture(name, settle=False)
            aim(8)
            safe_forecast = labels()
            assert any(text.startswith('Deal ') for text in safe_forecast)
            assert not any('Rune Adept falls.' in text for text in safe_forecast)
            assert player.state.to_json() == initial
            player.reload(initial)
            report = dict(backend=backend, input_sha256=hashlib.sha256(payload).hexdigest(),
                          state_sha256=hashlib.sha256(player.state.to_json().encode('utf-8')).hexdigest(),
                          state_unchanged=True, exact_save_reloads=player.reloads,
                          input_activations=len(player.events), inputs=player.events,
                          reading_percent=reading_scale(game), forecast_100=forecast_100,
                          forecast_125=forecast_125, safe_forecast=safe_forecast,
                          isolated_data_directory=str(game.data_dir),
                          image=str(image_path.parent / (name + '.png')) if backend == 'pyglet' else None,
                          scope='Public controls from an externally supplied Control save; '
                                'no campaign preparation or human-playtest claim.')
        finally:
            try:
                game._teardown()
            finally:
                game.backend.quit()
    return report


def verify_shard_controls(game, image_path: Path, *, backend='pyglet', budget=None) -> dict:
    """Read the installed map and click its primary orders, then restore the smoke save."""
    from saga2d import Button, Label
    from eador.model import State
    from eador.preferences import load_preferences, reading_scale
    from eador.scene import BattleScene, ShardScene
    from saga2d.testing.cpu_budget import CpuBudget
    from tools.eador_ui import PlayerInput

    budget = CpuBudget(25) if budget is None else budget

    class PacedInput(PlayerInput):
        def _tick(self):
            super()._tick()  # Native inputs already cap explicit frames at 30 FPS.
            budget.checkpoint()

    image_path = image_path.resolve()
    player = PacedInput(game, native=backend == 'pyglet', output=image_path.parent, finish_actions=False)
    assert isinstance(game.scene, ShardScene) and reading_scale(game) == 100
    saved = player.state.to_json()
    preferences = load_preferences(game)
    saved_preferences = preferences.path.read_bytes()

    def pointer(x, y):
        player.events.append((type(game.scene).__name__, 'hover', (round(x), round(y))))
        if player.native:
            window = game.backend.window
            scale = min(window.width / game.width, window.height / game.height)
            px = (window.width - game.width * scale) / 2 + x * scale
            py = (window.height - game.height * scale) / 2 + (game.height - y) * scale
            window.dispatch_event('on_mouse_motion', round(px), round(py), 0, 0)
        else:
            game.backend.inject_mouse_move(round(x), round(y))
        player._tick()
        assert player.state.to_json() == saved

    for key in ('f2', 'right', 'return', 'home'):
        player.press(key)
    assert reading_scale(game) == 125 and player.state.to_json() == saved
    pointer(10, 100)
    assert player.root.hover is None
    clean_image = image_path.stem + '-shard-125'
    hover_image = image_path.stem + '-shard-hover-125'
    player.capture(clean_image, settle=False)
    root = player.root
    position = max((pos for pos, province in root.state.provinces.items() if not province.capital),
                   key=lambda pos: len(root.state.provinces[pos].name))
    pointer(*root.grid.center(position))
    assert root.hover == position and root.selected == root.state.hero.pos
    label, = root._hover_name.find_all(lambda item: isinstance(item, Label) and item.visible)
    assert label.text == root.state.provinces[position].name
    x, y, width, height = root._hover_name.bounds
    assert 26 <= x < x + width <= root.edge - 26
    assert root._summary_bottom <= y < y + height <= game.height - 158
    lx, ly, lw, lh = label.bounds
    assert x <= lx < lx + lw <= x + width and y <= ly < ly + lh <= y + height
    player.capture(hover_image, settle=False)
    pointer(10, 100)
    explore = root.ui.find(lambda item: isinstance(item, Button) and item.text == 'Explore current province')
    assert explore is not None and explore.show_text and explore.enabled
    expected = State.from_json(saved)
    orders = []
    for action, control in (('explore', 'Explore current province'), ('retreat', 't'), ('end_turn', 'End turn')):
        getattr(expected, action)()
        if action == 'retreat':
            player.press(control)
        else:
            player.button(control)
        assert player.state.to_json() == expected.to_json(), action
        assert isinstance(game.scene, BattleScene if action == 'explore' else ShardScene)
        orders.append(action)
    player.press('f9')
    assert isinstance(game.scene, ShardScene) and game.scene is not root
    assert player.state.to_json() == saved
    for key in ('f2', 'left', 'return'):
        player.press(key)
    assert reading_scale(game) == 100 and player.state.to_json() == saved
    assert preferences.path.read_bytes() == saved_preferences
    return dict(verified=True, backend=backend, exact_orders=orders, hover_name=label.text,
                state_sha256=hashlib.sha256(saved.encode()).hexdigest(),
                input_activations=len(player.events), cpu_percent_requested=budget.percent,
                images=[str(image_path.parent / (name + '.png')) for name in (clean_image, hover_image)]
                       if player.native else [])


def online_smoke(endpoint: str) -> dict:
    """Two real WebSocket clients share one server-owned campaign and reclaim a seat."""
    if not endpoint:
        raise ValueError("The online smoke check requires an explicit --endpoint")
    from saga2d.online import OnlineClient
    from eador.model import State

    clients = []

    def wait(condition):
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            for client in clients:
                client.poll()
            if condition():
                return
            time.sleep(.02)
        raise AssertionError([(client.ready, client.closed, client.error) for client in clients])

    def campaign(client):
        return State.from_json(client.state["campaign"])

    try:
        creator = OnlineClient("shardbound-v1", endpoint=endpoint, options={"seed": 7, "campaign": True})
        clients.append(creator)
        wait(lambda: bool(creator.room) and creator.state is not None)
        assert creator.resume_token and not creator.ready and creator.retention >= 3600
        guest = OnlineClient("shardbound-v1", endpoint=endpoint, room=creator.room)
        clients.append(guest)
        wait(lambda: creator.ready and guest.ready)
        assert (creator.player, guest.player) == (0, 1)
        gold = campaign(creator).gold
        creator.submit({"action": "build", "target": "state", "args": ["barracks"]})
        wait(lambda: campaign(creator).gold < gold and campaign(guest).gold < gold)
        guest.submit({"action": "explore", "target": "state", "args": []})
        wait(lambda: campaign(creator).to_json() == campaign(guest).to_json() and creator.revision >= 4)
        room, token = creator.room, creator.resume_token
        creator.close()
        wait(lambda: not guest.ready)
        resumed = OnlineClient("shardbound-v1", endpoint=endpoint, room=room, resume_token=token)
        clients.append(resumed)
        wait(lambda: resumed.ready and guest.ready)
        assert resumed.player == 0 and campaign(resumed).to_json() == campaign(guest).to_json()
        return {"create_join": True, "shared_realm_orders": True, "private_seat_rejoin": True,
                "campaign_retention_seconds": creator.retention}
    finally:
        for client in clients:
            client.close()


def online_report(report_path: Path, endpoint: str) -> None:
    from eador.release import build_info
    info = build_info()
    result = {"passed": True, "frozen": True, "version": info["version"], "source_commit": info["source_commit"],
              "executable": str(Path(sys.executable).resolve()),
              "executable_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
              "endpoint": endpoint, "online": online_smoke(endpoint)}
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, indent=2) + "\n")


def smoke(image_path: Path, *, forecast_save: Path | None = None) -> None:
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
            shard_controls = verify_shard_controls(game, image_path)
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
                "shard_controls_verified": shard_controls['verified'],
                "shard_controls": shard_controls,
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
        if forecast_save is not None:
            report['casualty_forecast'] = verify_forecast_save(forecast_save, image_path)
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
    elif "--online-smoke" in sys.argv or "--smoke-image" in sys.argv:
        # A windowed PyInstaller build turns an unhandled exception into a blocking
        # dialog, so diagnostics record their failure and exit instead.
        import traceback
        parser = argparse.ArgumentParser(description="Verify the packaged Shardbound runtime")
        parser.add_argument("--online-smoke", type=Path)
        parser.add_argument("--endpoint")
        parser.add_argument("--smoke-image", type=Path)
        parser.add_argument('--forecast-save', type=Path,
                            help='also inspect the earned Control casualty forecast from this plain State JSON')
        args = parser.parse_args()
        report = args.online_smoke if args.online_smoke is not None else args.smoke_image.with_suffix(".json")
        try:
            if args.online_smoke is not None:
                online_report(args.online_smoke, args.endpoint)
            else:
                smoke(args.smoke_image, forecast_save=args.forecast_save)
        except Exception as exc:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps({"passed": False, "error_type": type(exc).__name__, "error": str(exc),
                                          "traceback": traceback.format_exc()}, indent=2) + "\n")
            print(traceback.format_exc(), file=sys.stderr)
            raise SystemExit(1) from exc
    else:
        from eador.__main__ import main
        main()
