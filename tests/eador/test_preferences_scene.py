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
