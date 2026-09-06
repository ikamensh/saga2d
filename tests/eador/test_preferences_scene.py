"""Player-facing preference editing through public input, audio and real files."""

import pytest

from saga2d import Button, Scene, Settings

from eador.app import create_game
from eador.preferences import DEFAULTS, load_preferences
from eador.settings_scene import SettingsScene


def press(game, key):
    game.backend.inject_key(key)
    game.tick(1 / 60)


def click_button(game, label):
    control = game.scene.ui.find(lambda child: isinstance(child, Button) and child.text == label)
    assert control is not None, label
    x, y, w, h = control.bounds
    game.backend.inject_click(round(x + w / 2), round(y + h / 2))
    game.tick(1 / 60)


def test_keyboard_preview_cancel_and_apply_survive_restart(tmp_path):
    """Preview affects runtime only; Cancel restores it and Apply persists before closing."""
    game = create_game("Shardbound settings test", backend="mock", save_dir=tmp_path / "saves")
    try:
        preferences = load_preferences(game)
        underlying = Scene()
        game.push(underlying)
        game.push(SettingsScene())
        press(game, "left")
        assert game.audio.get_volume("master") == pytest.approx(DEFAULTS["master"] - .1)
        assert not preferences.path.exists()
        press(game, "escape")
        assert game.scene is underlying
        assert game.audio.get_volume("master") == DEFAULTS["master"]
        game.push(SettingsScene())
        press(game, "left")
        press(game, "return")
        assert game.scene is underlying
        assert preferences["master"] == pytest.approx(DEFAULTS["master"] - .1)
    finally:
        game._teardown()
    restarted = create_game("Shardbound settings test", backend="mock", save_dir=tmp_path / "saves")
    try:
        load_preferences(restarted)
        assert restarted.audio.get_volume("master") == pytest.approx(DEFAULTS["master"] - .1)
    finally:
        restarted._teardown()


def test_mouse_and_keyboard_edit_the_same_rows_and_mute(tmp_path):
    """Row keys and visible controls produce the same draft and previewed gains."""
    game = create_game("Shardbound settings test", backend="mock", save_dir=tmp_path / "saves")
    try:
        load_preferences(game)
        game.push(Scene())
        game.push(SettingsScene())
        game.tick(1 / 60)
        click_button(game, "−")
        press(game, "right")
        assert game.audio.get_volume("master") == DEFAULTS["master"]
        press(game, "down")
        press(game, "left")
        assert game.audio.get_volume("music") == pytest.approx(DEFAULTS["music"] - .1)
        press(game, "down")
        press(game, "right")
        assert game.audio.get_volume("sfx") == pytest.approx(DEFAULTS["sfx"] + .1)
        click_button(game, "Mute")
        assert game.audio.muted
        press(game, "left")
        assert not game.audio.muted
        click_button(game, "Apply")
        saved = Settings(game.data_dir / "settings.json", DEFAULTS)
        assert saved["music"] == pytest.approx(DEFAULTS["music"] - .1)
        assert saved["sfx"] == pytest.approx(DEFAULTS["sfx"] + .1)
        assert not saved["muted"]
    finally:
        game._teardown()


def test_cancel_and_external_close_restore_exact_entry_audio_without_writing(tmp_path):
    """Runtime overrides are restored exactly, even when another scene closes Settings."""
    game = create_game("Shardbound settings test", backend="mock", save_dir=tmp_path / "saves")
    try:
        prefs = load_preferences(game)
        prefs.save()
        before = prefs.path.read_bytes()
        for close in (lambda: click_button(game, "Cancel"), game.pop):
            game.audio.set_volume("master", .17)
            game.audio.set_volume("music", .29)
            game.audio.set_volume("sfx", .43)
            game.audio.muted = True
            game.push(SettingsScene())
            press(game, "left")
            close()
            assert [game.audio.get_volume(channel) for channel in ("master", "music", "sfx")] == [.17, .29, .43]
            assert game.audio.muted
            assert prefs.path.read_bytes() == before
            assert not list(tmp_path.glob("settings.*.json"))
    finally:
        game._teardown()


@pytest.mark.parametrize("raw", ['{"master": 2}', '{"music": NaN}', '{"sfx": true}', '{"muted": 1}'])
def test_load_applies_safe_defaults_and_reports_invalid_game_values(tmp_path, raw):
    """Only actual booleans and finite 0–1 volumes can reach live game audio."""
    path = tmp_path / "settings.json"
    path.write_text(raw)
    game = create_game("Shardbound settings test", backend="mock", save_dir=tmp_path / "saves")
    try:
        prefs = load_preferences(game)
        assert prefs.error is not None
        assert dict(prefs) == DEFAULTS
        assert game.audio.get_volume("master") == DEFAULTS["master"]
        assert path.read_text() == raw
    finally:
        game._teardown()


def test_damaged_preferences_require_explicit_recovery_and_cancel_does_not_authorize_it(tmp_path):
    """Only the recovery action allows replacing damaged bytes, which remain retained."""
    path = tmp_path / "settings.json"
    damaged = b"\xffdamaged audio settings"
    path.write_bytes(damaged)
    game = create_game("Shardbound settings test", backend="mock", save_dir=tmp_path / "saves")
    try:
        prefs = load_preferences(game)
        underlying = Scene()
        game.push(underlying)
        game.push(SettingsScene())
        press(game, "return")
        assert isinstance(game.scene, SettingsScene)
        assert path.read_bytes() == damaged
        assert "Could not apply" in game.scene.message
        click_button(game, "Preserve damaged file & use defaults")
        click_button(game, "Cancel")
        assert path.read_bytes() == damaged
        assert not list(tmp_path.glob("settings.recovery-*.json"))
        game.push(SettingsScene())
        press(game, "return")
        assert isinstance(game.scene, SettingsScene)
        assert path.read_bytes() == damaged
        press(game, "r")
        press(game, "return")
        assert game.scene is underlying
        assert prefs.error is None
        assert dict(prefs) == DEFAULTS
        assert [item.read_bytes() for item in tmp_path.glob("settings.recovery-*.json")] == [damaged]
    finally:
        game._teardown()


def test_failed_apply_stays_open_and_cancel_preserves_disk_and_shared_preferences(tmp_path):
    """A real filesystem conflict cannot announce success or leak draft values into memory."""
    game = create_game("Shardbound settings test", backend="mock", save_dir=tmp_path / "saves")
    try:
        prefs = load_preferences(game)
        prefs.save()
        before = prefs.path.read_bytes()
        prefs.path.with_suffix(".backup.json").mkdir()
        underlying = Scene()
        game.push(underlying)
        game.push(SettingsScene())
        press(game, "left")
        click_button(game, "Apply")
        assert isinstance(game.scene, SettingsScene)
        assert "Could not apply" in game.scene.message
        assert prefs.path.read_bytes() == before
        assert dict(prefs) == DEFAULTS
        assert game.audio.get_volume("master") == pytest.approx(DEFAULTS["master"] - .1)
        click_button(game, "Cancel")
        assert game.scene is underlying
        assert game.audio.get_volume("master") == DEFAULTS["master"]
        assert prefs.path.read_bytes() == before
    finally:
        game._teardown()


def test_campaign_load_does_not_change_preferences_or_store_them_in_progress(tmp_path):
    """Campaign checkpoints and preferences have separate persistence lifetimes."""
    from eador.model import State
    from eador.persistence import CampaignSaves

    game = create_game("Shardbound settings test", backend="mock", save_dir=tmp_path / "saves")
    try:
        prefs = load_preferences(game)
        state = State.new(7)
        progress = state.to_json()
        saves = CampaignSaves(game.save_manager)
        saves.save(state)
        game.push(Scene())
        game.push(SettingsScene())
        press(game, "left")
        press(game, "return")
        assert saves.load().to_json() == progress
        assert game.audio.get_volume("master") == prefs["master"] == pytest.approx(DEFAULTS["master"] - .1)
        assert set(game.save_manager.load(1)["state"]) == {"campaign"}
    finally:
        game._teardown()


def test_reopening_settings_reloads_a_file_repaired_outside_the_game(tmp_path):
    """A previous loading error does not trap a repaired preferences file behind recovery."""
    path = tmp_path / "settings.json"
    path.write_text('{broken')
    game = create_game("Shardbound settings test", backend="mock", save_dir=tmp_path / "saves")
    try:
        load_preferences(game)
        game.push(Scene())
        game.push(SettingsScene())
        press(game, "escape")
        path.write_text('{"master": 0.6}')
        game.push(SettingsScene())
        game.tick(1 / 60)
        recovery = game.scene.ui.find(lambda child: isinstance(child, Button) and child.text == "Preserve damaged file & use defaults")
        assert recovery is None
        press(game, "return")
        assert game.audio.get_volume("master") == .6
    finally:
        game._teardown()


def test_title_and_guide_settings_preserve_campaign_and_survive_quickload(tmp_path):
    """Both visible entry points edit the same preferences without changing saved progress."""
    from eador.scene import HelpScene, ShardScene, TitleScene

    game = create_game("Shardbound", backend="mock", save_dir=tmp_path / "saves")
    try:
        title = TitleScene(seed=7)
        game.push(title)
        press(game, "o")
        assert isinstance(game.scene, SettingsScene)
        press(game, "left")
        press(game, "return")
        assert game.scene is title
        assert game.audio.get_volume("master") == pytest.approx(.7)
        press(game, "return")
        assert isinstance(game.scene, ShardScene)
        press(game, "f5")
        saved = game.scene.state.to_json()
        press(game, "f1")
        guide = game.scene
        assert isinstance(guide, HelpScene)
        click_button(game, "Settings")
        assert isinstance(game.scene, SettingsScene)
        click_button(game, "Mute")
        click_button(game, "Apply")
        assert game.scene is guide
        press(game, "escape")
        press(game, "f9")
        assert game.scene.state.to_json() == saved
        assert game.audio.muted and game.audio.get_volume("master") == pytest.approx(.7)
        assert Settings(tmp_path / "settings.json", DEFAULTS)["muted"]
    finally:
        game._teardown()


def test_saved_display_applies_once_at_startup_and_scene_load_keeps_os_resize(tmp_path):
    """Restart restores display preferences without later scene entry undoing an OS resize."""
    from eador.preferences import reduced_motion, validate_preferences

    prefs = Settings(tmp_path / "settings.json", DEFAULTS, validator=validate_preferences)
    prefs.update(window_size=[1280, 720], fullscreen=True, reduced_motion=True)
    prefs.save()
    game = create_game("Display restart", backend="mock", save_dir=tmp_path / "saves")
    try:
        assert game.fullscreen and game.windowed_size == (1280, 720)
        assert game.resolution == (1280, 800) and reduced_motion(game)
        game.set_fullscreen(False)
        game.backend.inject_resize(940, 720)
        game.tick(1 / 60)
        load_preferences(game)
        assert not game.fullscreen and game.window_size == (940, 720)
        assert reduced_motion(game)
    finally:
        game._teardown()


@pytest.mark.parametrize("options", [{"visible": False}, {"resolution": (1280, 720)}, {"fullscreen": False}])
def test_explicit_launch_display_does_not_inherit_saved_fullscreen(tmp_path, options):
    """Hidden verification windows and explicit launch displays retain their requested mode."""
    prefs = Settings(tmp_path / "settings.json", DEFAULTS)
    prefs.update(window_size=[960, 600], fullscreen=True, reduced_motion=True)
    prefs.save()
    game = create_game("Controlled display", backend="mock", save_dir=tmp_path / "saves", **options)
    try:
        assert not game.fullscreen
        assert game.window_size == options.get("resolution", (1280, 800))
        load_preferences(game)
        assert not game.fullscreen
        assert prefs["fullscreen"] is True
    finally:
        game._teardown()


@pytest.mark.parametrize("raw", ['{"window_size": [true, 720]}', '{"window_size": [1280.0, 720]}',
                                 '{"window_size": [0, 720]}', '{"window_size": [999999999, 720]}',
                                 '{"window_size": [1280]}', '{"fullscreen": 1}', '{"reduced_motion": 1}'])
def test_invalid_display_file_stays_intact_and_uses_windowed_defaults(tmp_path, raw):
    """Malformed display data cannot send invalid native requests or silently overwrite evidence."""
    path = tmp_path / "settings.json"
    path.write_text(raw)
    game = create_game("Invalid display", backend="mock", save_dir=tmp_path / "saves")
    try:
        assert load_preferences(game).error
        assert game.window_size == (1280, 800) and not game.fullscreen
        assert path.read_text() == raw
    finally:
        game._teardown()


def test_display_keyboard_preview_cancel_from_fullscreen_restores_os_size(tmp_path):
    """Tabs share one draft; cancelling fullscreen previews restores the real entry display."""
    from eador.preferences import reduced_motion

    game = create_game("Display preview", backend="mock", save_dir=tmp_path / "saves")
    try:
        game.backend.inject_resize(940, 720)
        game.tick(1 / 60)
        game.set_fullscreen(True)
        underlying = Scene()
        game.push(underlying)
        game.push(SettingsScene())
        press(game, "d")
        press(game, "right")
        assert not game.fullscreen and game.windowed_size != (940, 720)
        press(game, "down")
        press(game, "right")
        assert game.fullscreen
        press(game, "down")
        press(game, "right")
        assert reduced_motion(game)
        press(game, "s")
        press(game, "left")
        assert game.audio.get_volume("master") == .7
        press(game, "escape")
        assert game.scene is underlying
        assert game.fullscreen and game.windowed_size == (940, 720)
        assert not reduced_motion(game) and game.audio.get_volume("master") == .8
        game.set_fullscreen(False)
        assert game.window_size == (940, 720) and game.resolution == (1280, 800)
        assert not (tmp_path / "settings.json").exists()
    finally:
        game._teardown()


@pytest.mark.parametrize("input_mode", ["keyboard", "mouse"])
def test_display_apply_and_restart_match_for_mouse_and_keyboard(tmp_path, input_mode):
    """Both input paths persist the same presentation without changing the logical canvas."""
    from eador.preferences import reduced_motion

    game = create_game("Display apply", backend="mock", save_dir=tmp_path / "saves")
    try:
        underlying = Scene()
        game.push(underlying)
        game.push(SettingsScene())
        game.tick(1 / 60)
        if input_mode == "keyboard":
            for key in ("tab", "left", "down", "right", "down", "right", "tab", "left", "return"):
                press(game, key)
        else:
            for label in ("Display", "−", "Go fullscreen", "Reduce motion", "Sound", "−", "Apply"):
                click_button(game, label)
        assert game.scene is underlying
        assert game.fullscreen and game.windowed_size == (1280, 720)
        assert reduced_motion(game) and game.audio.get_volume("master") == .7
    finally:
        game._teardown()
    restarted = create_game("Display apply", backend="mock", save_dir=tmp_path / "saves")
    try:
        assert restarted.fullscreen and restarted.windowed_size == (1280, 720)
        assert restarted.resolution == (1280, 800)
        assert reduced_motion(restarted) and restarted.audio.get_volume("master") == .7
    finally:
        restarted._teardown()


def test_failed_display_apply_keeps_preview_open_then_cancel_restores_entry(tmp_path):
    """Failed disk writes cannot close Settings or commit fullscreen/motion changes."""
    from eador.preferences import reduced_motion

    game = create_game("Display failure", backend="mock", save_dir=tmp_path / "saves")
    try:
        prefs = load_preferences(game)
        prefs.save()
        before = prefs.path.read_bytes()
        prefs.path.with_suffix(".backup.json").mkdir()
        game.backend.inject_resize(940, 720)
        game.tick(1 / 60)
        game.push(Scene())
        game.push(SettingsScene())
        for key in ("d", "right", "down", "right", "down", "right", "return"):
            press(game, key)
        assert isinstance(game.scene, SettingsScene) and game.fullscreen and reduced_motion(game)
        assert "Could not apply" in game.scene.message and prefs.path.read_bytes() == before
        press(game, "escape")
        assert not game.fullscreen and game.window_size == (940, 720) and not reduced_motion(game)
        assert prefs.path.read_bytes() == before
    finally:
        game._teardown()


def test_display_recovery_retains_corruption_and_cancels_fullscreen_preview(tmp_path):
    """Damaged display data needs explicit recovery; Cancel restores the entry mode and bytes."""
    damaged = b'{"fullscreen": "yes"}'
    path = tmp_path / "settings.json"
    path.write_bytes(damaged)
    game = create_game("Display recovery", backend="mock", save_dir=tmp_path / "saves")
    try:
        game.backend.inject_resize(940, 720)
        game.tick(1 / 60)
        game.set_fullscreen(True)
        game.push(Scene())
        for ending in ("escape", "return"):
            game.push(SettingsScene())
            press(game, "d")
            press(game, "r")
            assert not game.fullscreen and game.window_size == (1280, 800)
            press(game, ending)
            if ending == "escape":
                assert game.fullscreen and game.windowed_size == (940, 720)
                assert path.read_bytes() == damaged and not list(tmp_path.glob("settings.recovery-*.json"))
        assert not game.fullscreen and game.window_size == (1280, 800)
        assert [p.read_bytes() for p in tmp_path.glob("settings.recovery-*.json")] == [damaged]
        assert dict(Settings(path, DEFAULTS)) == DEFAULTS
    finally:
        game._teardown()


def test_headless_launch_and_settings_cannot_inherit_or_request_fullscreen(tmp_path, monkeypatch):
    """The process-wide hidden-window policy survives saved fullscreen and keyboard attempts."""
    prefs = Settings(tmp_path / "settings.json", DEFAULTS)
    prefs.update(window_size=[960, 600], fullscreen=True)
    prefs.save()
    before = prefs.path.read_bytes()
    monkeypatch.setenv("SAGA2D_HEADLESS", "1")
    game = create_game("Headless display", backend="mock", save_dir=tmp_path / "saves")
    try:
        assert not game.fullscreen and game.window_size == (1280, 800)
        game.push(Scene())
        game.push(SettingsScene())
        for key in ("d", "down", "right"):
            press(game, key)
        assert not game.fullscreen and "SAGA2D_HEADLESS" in game.scene.message
        press(game, "escape")
        assert prefs.path.read_bytes() == before
    finally:
        game._teardown()


def test_size_controls_follow_os_resize_while_settings_is_open(tmp_path):
    """A native resize updates the value and the next size choice, rather than stale draft data."""
    game = create_game("Live OS resize", backend="mock", save_dir=tmp_path / "saves")
    try:
        game.push(Scene())
        game.push(SettingsScene())
        press(game, "d")
        game.backend.inject_resize(1280, 720)
        game.tick(1 / 60)
        press(game, "right")
        assert game.window_size == (1280, 800)
        game.backend.inject_resize(940, 720)
        game.tick(1 / 60)
        press(game, "return")
        assert Settings(tmp_path / "settings.json", DEFAULTS)["window_size"] == [940, 720]
    finally:
        game._teardown()
