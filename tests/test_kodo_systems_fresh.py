"""Fresh edge-case tests for Saga2D systems: Save, Audio, Input, Assets, FSM.

Each section targets boundary conditions, error handling, and unusual inputs
that the existing test suite does not cover.
"""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import Any

import pytest

from saga2d.assets import AssetManager, AssetNotFoundError
from saga2d.audio import AudioManager
from saga2d.backends.base import KeyEvent, MouseEvent
from saga2d.backends.mock_backend import MockBackend
from saga2d.input import InputEvent, InputManager
from saga2d.save import SaveError, SaveManager
from saga2d.util.fsm import StateMachine


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def save_dir(tmp_path: Path) -> Path:
    """Return a temporary directory for save files (not yet created)."""
    return tmp_path / "saves"


@pytest.fixture
def manager(save_dir: Path) -> SaveManager:
    """Return a SaveManager using a temp directory."""
    return SaveManager(save_dir)


@pytest.fixture
def asset_dir(tmp_path: Path) -> Path:
    """Temp asset dir with test sounds, music, and images."""
    sounds = tmp_path / "sounds"
    sounds.mkdir()
    (sounds / "sword_hit.wav").write_bytes(b"wav")
    (sounds / "click.wav").write_bytes(b"wav")
    (sounds / "hit_01.wav").write_bytes(b"wav")
    (sounds / "hit_02.wav").write_bytes(b"wav")
    (sounds / "hit_03.wav").write_bytes(b"wav")
    (sounds / "lone.wav").write_bytes(b"wav")

    music = tmp_path / "music"
    music.mkdir()
    (music / "exploration.ogg").write_bytes(b"ogg")
    (music / "battle.ogg").write_bytes(b"ogg")
    (music / "victory.ogg").write_bytes(b"ogg")

    images = tmp_path / "images" / "sprites"
    images.mkdir(parents=True)
    (images / "knight.png").write_bytes(b"png")
    return tmp_path


@pytest.fixture
def backend() -> MockBackend:
    return MockBackend()


@pytest.fixture
def assets(backend: MockBackend, asset_dir: Path) -> AssetManager:
    return AssetManager(backend, base_path=asset_dir)


@pytest.fixture
def audio(backend: MockBackend, assets: AssetManager) -> AudioManager:
    return AudioManager(backend, assets)


# ======================================================================
# 1. SAVE/LOAD EDGE CASES
# ======================================================================


class TestSaveDeeplyNested:
    """Save with deeply nested dict (3+ levels)."""

    def test_three_level_nested_dict_round_trips(
        self, manager: SaveManager
    ) -> None:
        state = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {"value": 42, "items": [1, 2, 3]}
                    }
                }
            }
        }
        manager.save(1, state, "DeepScene")
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"] == state

    def test_deeply_nested_list_of_dicts(self, manager: SaveManager) -> None:
        state = {
            "armies": [
                {
                    "units": [
                        {
                            "skills": [
                                {"name": "fireball", "level": 3, "damage": {"min": 5, "max": 15}}
                            ]
                        }
                    ]
                }
            ]
        }
        manager.save(1, state, "ArmyScene")
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"]["armies"][0]["units"][0]["skills"][0]["damage"]["max"] == 15


class TestSaveUnicode:
    """Save with unicode characters in keys and values."""

    def test_unicode_keys(self, manager: SaveManager) -> None:
        state = {"\u540d\u524d": "\u52c7\u8005", "\u30ec\u30d9\u30eb": 10}
        manager.save(1, state, "UnicodeScene")
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"]["\u540d\u524d"] == "\u52c7\u8005"
        assert loaded["state"]["\u30ec\u30d9\u30eb"] == 10

    def test_emoji_values(self, manager: SaveManager) -> None:
        state = {"mood": "\U0001f600\U0001f525\u2694\ufe0f", "flag": "\U0001f1ef\U0001f1f5"}
        manager.save(1, state, "EmojiScene")
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"]["mood"] == "\U0001f600\U0001f525\u2694\ufe0f"

    def test_mixed_unicode_and_ascii(self, manager: SaveManager) -> None:
        state = {"player": "Albrecht D\u00fcrer", "gold": 100}
        manager.save(1, state, "MixScene")
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"]["player"] == "Albrecht D\u00fcrer"


class TestSaveLargeState:
    """Save with very large state (1000+ keys)."""

    def test_1000_keys_round_trip(self, manager: SaveManager) -> None:
        state = {f"key_{i}": i * 3.14 for i in range(1000)}
        manager.save(1, state, "LargeScene")
        loaded = manager.load(1)
        assert loaded is not None
        assert len(loaded["state"]) == 1000
        assert loaded["state"]["key_999"] == pytest.approx(999 * 3.14)

    def test_2000_keys_round_trip(self, manager: SaveManager) -> None:
        state = {f"item_{i}": {"name": f"Item {i}", "qty": i} for i in range(2000)}
        manager.save(1, state, "HugeScene")
        loaded = manager.load(1)
        assert loaded is not None
        assert len(loaded["state"]) == 2000
        assert loaded["state"]["item_1999"]["qty"] == 1999


class TestSaveEmptyDict:
    """Save with empty dict."""

    def test_empty_dict_saves_and_loads(self, manager: SaveManager) -> None:
        manager.save(1, {}, "EmptyScene")
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"] == {}
        assert loaded["version"] == 1


class TestLoadCorruptedFile:
    """Load from corrupted file (write garbage bytes)."""

    def test_garbage_bytes_raises_save_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_bytes(b"\x80\x81\x82\x83\xff\xfe")
        with pytest.raises(SaveError):
            manager.load(1)

    def test_truncated_json_raises_save_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text('{"version": 1, "state":', encoding="utf-8")
        with pytest.raises(SaveError):
            manager.load(1)


class TestLoadJsonList:
    """Load from valid JSON that's a list (not a dict)."""

    def test_json_list_raises_save_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text('[1, 2, 3]', encoding="utf-8")
        with pytest.raises(SaveError, match="expected JSON object"):
            manager.load(1)


class TestLoadJsonString:
    """Load from valid JSON that's a string."""

    def test_json_string_raises_save_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text('"hello world"', encoding="utf-8")
        with pytest.raises(SaveError, match="expected JSON object"):
            manager.load(1)


class TestLoadEmptyFile:
    """Load from empty file (0 bytes)."""

    def test_empty_file_raises_save_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("", encoding="utf-8")
        with pytest.raises(SaveError):
            manager.load(1)


class TestLoadInvalidUtf8:
    """Load from file with invalid UTF-8 bytes."""

    def test_invalid_utf8_raises_save_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        save_dir.mkdir(parents=True, exist_ok=True)
        # Write bytes that are not valid UTF-8
        (save_dir / "save_1.json").write_bytes(b'\xc3\x28\xff\xfe')
        with pytest.raises(SaveError):
            manager.load(1)


class TestListSlotsWithCorruptSlot:
    """list_slots with corrupt slot in middle."""

    def test_corrupt_slot_in_middle_raises(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """list_slots iterates through slots; a corrupt file raises SaveError."""
        manager.save(1, {"ok": True}, "Scene1")
        # Corrupt slot 2
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_2.json").write_text("not json", encoding="utf-8")
        manager.save(3, {"ok": True}, "Scene3")

        # list_slots calls load() internally, which raises SaveError on corrupt
        with pytest.raises(SaveError):
            manager.list_slots(count=3)


class TestDeleteNonExistentSlot:
    """delete non-existent slot (should be no-op)."""

    def test_delete_nonexistent_no_error(self, manager: SaveManager) -> None:
        # Should not raise
        manager.delete(42)
        manager.delete(999)

    def test_delete_nonexistent_does_not_affect_existing(
        self, manager: SaveManager
    ) -> None:
        manager.save(1, {"data": "ok"}, "Scene")
        manager.delete(2)  # non-existent
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"]["data"] == "ok"


class TestSaveSlotZeroAndNegative:
    """save slot 0 and slot -1 (should raise ValueError)."""

    def test_save_slot_zero_raises_value_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(ValueError, match="slot must be >= 1"):
            manager.save(0, {}, "Scene")

    def test_save_slot_negative_raises_value_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(ValueError, match="slot must be >= 1"):
            manager.save(-1, {}, "Scene")

    def test_load_slot_zero_raises_value_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(ValueError, match="slot must be >= 1"):
            manager.load(0)

    def test_load_slot_negative_raises_value_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(ValueError, match="slot must be >= 1"):
            manager.load(-1)

    def test_delete_slot_zero_raises_value_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(ValueError, match="slot must be >= 1"):
            manager.delete(0)

    def test_delete_slot_negative_raises_value_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(ValueError, match="slot must be >= 1"):
            manager.delete(-1)


class TestSaveSlotFloat:
    """save slot=1.0 (float, should raise TypeError)."""

    def test_save_float_slot_raises_type_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(TypeError, match="slot must be an int"):
            manager.save(1.0, {}, "Scene")  # type: ignore[arg-type]

    def test_load_float_slot_raises_type_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(TypeError, match="slot must be an int"):
            manager.load(1.0)  # type: ignore[arg-type]

    def test_delete_float_slot_raises_type_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(TypeError, match="slot must be an int"):
            manager.delete(1.0)  # type: ignore[arg-type]


class TestSaveSlotString:
    """save slot="1" (string, should raise TypeError)."""

    def test_save_string_slot_raises_type_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(TypeError, match="slot must be an int"):
            manager.save("1", {}, "Scene")  # type: ignore[arg-type]

    def test_load_string_slot_raises_type_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(TypeError, match="slot must be an int"):
            manager.load("1")  # type: ignore[arg-type]

    def test_delete_string_slot_raises_type_error(
        self, manager: SaveManager
    ) -> None:
        with pytest.raises(TypeError, match="slot must be an int"):
            manager.delete("1")  # type: ignore[arg-type]


class TestConcurrentSaveLoad:
    """Concurrent save/load: save then immediately load same slot."""

    def test_save_then_load_same_slot(self, manager: SaveManager) -> None:
        state = {"counter": 42, "items": ["sword", "shield"]}
        manager.save(1, state, "BattleScene")
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"] == state

    def test_save_overwrite_then_load(self, manager: SaveManager) -> None:
        manager.save(1, {"v": 1}, "Scene")
        manager.save(1, {"v": 2}, "Scene")
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"]["v"] == 2

    def test_rapid_save_load_cycle(self, manager: SaveManager) -> None:
        """Rapidly save and load the same slot 50 times."""
        for i in range(50):
            manager.save(1, {"iteration": i}, "Scene")
            loaded = manager.load(1)
            assert loaded is not None
            assert loaded["state"]["iteration"] == i


# ======================================================================
# 2. AUDIO EDGE CASES
# ======================================================================


class TestSetVolumeOutOfRange:
    """set_volume with out-of-range values (should clamp)."""

    def test_volume_above_1_clamped(self, audio: AudioManager) -> None:
        audio.set_volume("master", 5.0)
        assert audio.get_volume("master") == 1.0

    def test_volume_below_0_clamped(self, audio: AudioManager) -> None:
        audio.set_volume("sfx", -10.0)
        assert audio.get_volume("sfx") == 0.0

    def test_volume_large_negative_clamped(self, audio: AudioManager) -> None:
        audio.set_volume("music", -999.99)
        assert audio.get_volume("music") == 0.0

    def test_volume_infinity_clamped(self, audio: AudioManager) -> None:
        audio.set_volume("ui", float("inf"))
        assert audio.get_volume("ui") == 1.0

    def test_volume_negative_infinity_clamped(self, audio: AudioManager) -> None:
        audio.set_volume("ui", float("-inf"))
        assert audio.get_volume("ui") == 0.0


class TestSetVolumeInvalidChannel:
    """set_volume on invalid channel (should raise KeyError)."""

    def test_unknown_channel_raises_key_error(self, audio: AudioManager) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            audio.set_volume("nonexistent", 0.5)

    def test_empty_string_channel_raises_key_error(
        self, audio: AudioManager
    ) -> None:
        with pytest.raises(KeyError):
            audio.set_volume("", 0.5)

    def test_get_unknown_channel_raises_key_error(
        self, audio: AudioManager
    ) -> None:
        with pytest.raises(KeyError, match="bogus"):
            audio.get_volume("bogus")


class TestPlaySoundOptionalMissing:
    """play_sound with optional=True on missing asset."""

    def test_optional_missing_returns_none(
        self, audio: AudioManager, backend: MockBackend
    ) -> None:
        result = audio.play_sound("does_not_exist", optional=True)
        assert result is None
        assert len(backend.sounds_played) == 0

    def test_optional_false_missing_raises(self, audio: AudioManager) -> None:
        with pytest.raises(AssetNotFoundError):
            audio.play_sound("does_not_exist", optional=False)


class TestPlayMusicStopPlay:
    """play_music then stop_music then play_music again."""

    def test_play_stop_play_cycle(
        self, audio: AudioManager, backend: MockBackend
    ) -> None:
        audio.play_music("exploration")
        assert backend.music_playing is not None
        first_player = audio._current_player_id

        audio.stop_music()
        assert backend.music_playing is None
        assert audio._current_player_id is None

        audio.play_music("battle")
        assert backend.music_playing is not None
        assert audio._current_player_id is not None
        assert audio._current_player_id != first_player
        assert audio._current_music_name == "battle"


class TestCrossfadeSameTrack:
    """crossfade_music to same track (should no-op)."""

    def test_crossfade_same_track_is_noop(
        self, audio: AudioManager, backend: MockBackend
    ) -> None:
        audio.play_music("exploration")
        player_before = audio._current_player_id
        players_count_before = len(backend._music_players)

        audio.crossfade_music("exploration", duration=1.0)

        # Same player, no new players created
        assert audio._current_player_id == player_before
        assert len(backend._music_players) == players_count_before
        assert audio._current_music_name == "exploration"


class TestCrossfadeDurationZero:
    """crossfade_music with duration=0."""

    def test_crossfade_duration_zero(
        self, audio: AudioManager, backend: MockBackend
    ) -> None:
        """Duration=0 should still create the crossfade (tweens with 0 duration)."""
        audio.play_music("exploration")
        old_player = audio._current_player_id

        # This will attempt to create tweens with duration=0.
        # The tween system needs a TweenManager to be set up, which
        # requires the module-level global. We test that it doesn't crash
        # when no tween manager is available, or that crossfade_music
        # at least initiates properly.
        # Since crossfade_music uses the tween module directly,
        # we need to ensure it's initialized. Without a Game.tick cycle,
        # the tween manager might not exist.
        from saga2d.util import tween as tween_mod

        # Set up a minimal tween manager if needed
        if tween_mod._tween_manager is None:
            from saga2d.util.tween import TweenManager
            tween_mod._tween_manager = TweenManager()

        audio.crossfade_music("battle", duration=0.0)

        # New player should be current
        assert audio._current_music_name == "battle"
        assert audio._current_player_id != old_player


class TestRegisterPoolEmpty:
    """register_pool with empty list."""

    def test_register_empty_pool(self, audio: AudioManager) -> None:
        audio.register_pool("empty", [])
        assert "empty" in audio._pools
        assert len(audio._pools["empty"]) == 0

    def test_play_empty_pool_is_noop(
        self, audio: AudioManager, backend: MockBackend
    ) -> None:
        audio.register_pool("empty", [])
        audio.play_pool("empty")
        assert len(backend.sounds_played) == 0


class TestPlayPoolUnregistered:
    """play_pool on unregistered pool name."""

    def test_unregistered_pool_raises_key_error(
        self, audio: AudioManager
    ) -> None:
        with pytest.raises(KeyError):
            audio.play_pool("nonexistent_pool")


class TestSoundPoolSingleElement:
    """sound pool with single element (always same sound)."""

    def test_single_element_pool_always_same(
        self, audio: AudioManager, backend: MockBackend
    ) -> None:
        audio.register_pool("one", ["lone"])
        for _ in range(10):
            audio.play_pool("one")
        assert len(backend.sounds_played) == 10
        handles = {entry["handle"] for entry in backend.sounds_played}
        assert len(handles) == 1  # always the same sound


# ======================================================================
# 3. INPUT EDGE CASES
# ======================================================================


class TestBindSameKeyTwoActions:
    """bind same key to two different actions (key stealing)."""

    def test_key_stealing(self) -> None:
        inp = InputManager()
        inp.bind("attack", "space")
        inp.bind("jump", "space")

        # "attack" should have been unbound (key was stolen by "jump")
        bindings = inp.get_bindings()
        assert bindings.get("jump") == "space"
        assert "attack" not in bindings

    def test_key_stealing_old_action_translated_is_none(self) -> None:
        inp = InputManager()
        inp.bind("attack", "space")
        inp.bind("jump", "space")

        events = inp.translate([KeyEvent(type="key_press", key="space")])
        assert len(events) == 1
        assert events[0].action == "jump"

    def test_rebind_same_action_to_new_key(self) -> None:
        inp = InputManager()
        inp.bind("attack", "a")
        inp.bind("attack", "b")

        bindings = inp.get_bindings()
        assert bindings["attack"] == "b"

        # Old key "a" should no longer map to anything
        events = inp.translate([KeyEvent(type="key_press", key="a")])
        assert events[0].action is None


class TestUnbindNonExistent:
    """unbind non-existent action."""

    def test_unbind_nonexistent_is_noop(self) -> None:
        inp = InputManager()
        # Should not raise
        inp.unbind("nonexistent_action")
        inp.unbind("")
        inp.unbind("definitely_not_bound")

    def test_unbind_preserves_existing_bindings(self) -> None:
        inp = InputManager()
        inp.bind("attack", "space")
        inp.unbind("nonexistent")
        bindings = inp.get_bindings()
        assert bindings["attack"] == "space"


class TestTranslateNoneEvents:
    """translate with None events."""

    def test_translate_none_returns_empty_list(self) -> None:
        inp = InputManager()
        result = inp.translate(None)
        assert result == []
        assert isinstance(result, list)


class TestTranslateEmptyList:
    """translate with empty list."""

    def test_translate_empty_list_returns_empty_list(self) -> None:
        inp = InputManager()
        result = inp.translate([])
        assert result == []
        assert isinstance(result, list)


class TestInputEventImmutability:
    """InputEvent frozen dataclass immutability."""

    def test_cannot_modify_type(self) -> None:
        event = InputEvent(type="key_press", key="space", action="jump")
        with pytest.raises(FrozenInstanceError):
            event.type = "key_release"  # type: ignore[misc]

    def test_cannot_modify_key(self) -> None:
        event = InputEvent(type="key_press", key="space")
        with pytest.raises(FrozenInstanceError):
            event.key = "a"  # type: ignore[misc]

    def test_cannot_modify_action(self) -> None:
        event = InputEvent(type="key_press", key="space", action="jump")
        with pytest.raises(FrozenInstanceError):
            event.action = "attack"  # type: ignore[misc]

    def test_cannot_modify_x(self) -> None:
        event = InputEvent(type="click", x=100, y=200)
        with pytest.raises(FrozenInstanceError):
            event.x = 999  # type: ignore[misc]

    def test_cannot_modify_world_coords(self) -> None:
        event = InputEvent(type="click", world_x=1.0, world_y=2.0)
        with pytest.raises(FrozenInstanceError):
            event.world_x = 99.0  # type: ignore[misc]

    def test_cannot_add_new_field(self) -> None:
        event = InputEvent(type="key_press")
        with pytest.raises(FrozenInstanceError):
            event.new_field = "test"  # type: ignore[attr-defined]

    def test_equality_by_value(self) -> None:
        e1 = InputEvent(type="key_press", key="space", action="jump")
        e2 = InputEvent(type="key_press", key="space", action="jump")
        assert e1 == e2

    def test_inequality_different_action(self) -> None:
        e1 = InputEvent(type="key_press", key="space", action="jump")
        e2 = InputEvent(type="key_press", key="space", action="attack")
        assert e1 != e2


class TestInputTranslationMouse:
    """Mouse events should not map to actions."""

    def test_mouse_event_action_is_none(self) -> None:
        inp = InputManager()
        events = inp.translate(
            [MouseEvent(type="click", x=100, y=200, button="left")]
        )
        assert len(events) == 1
        assert events[0].action is None
        assert events[0].x == 100
        assert events[0].y == 200
        assert events[0].button == "left"

    def test_mouse_move_translated(self) -> None:
        inp = InputManager()
        events = inp.translate(
            [MouseEvent(type="move", x=50, y=75, button=None)]
        )
        assert len(events) == 1
        assert events[0].type == "move"
        assert events[0].button is None


class TestInputDefaultBindings:
    """Verify default bindings exist and work."""

    def test_default_confirm_binding(self) -> None:
        inp = InputManager()
        events = inp.translate([KeyEvent(type="key_press", key="return")])
        assert events[0].action == "confirm"

    def test_default_cancel_binding(self) -> None:
        inp = InputManager()
        events = inp.translate([KeyEvent(type="key_press", key="escape")])
        assert events[0].action == "cancel"

    def test_default_directional_bindings(self) -> None:
        inp = InputManager()
        for key in ("up", "down", "left", "right"):
            events = inp.translate([KeyEvent(type="key_press", key=key)])
            assert events[0].action == key

    def test_unbound_key_action_is_none(self) -> None:
        inp = InputManager()
        events = inp.translate([KeyEvent(type="key_press", key="z")])
        assert events[0].action is None
        assert events[0].key == "z"


# ======================================================================
# 4. ASSET EDGE CASES
# ======================================================================


class TestLoadImageNoExtension:
    """Load image with no extension (should append .png)."""

    def test_image_no_extension_appends_png(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        handle = mgr.image("sprites/knight")
        assert handle is not None
        expected = str(asset_dir / "images" / "sprites" / "knight.png")
        assert expected in backend._loaded_images


class TestLoadImageNotExist:
    """Load image that doesn't exist."""

    def test_missing_image_raises(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        with pytest.raises(AssetNotFoundError, match="nonexistent"):
            mgr.image("sprites/nonexistent")

    def test_missing_image_error_includes_path(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        with pytest.raises(AssetNotFoundError) as exc_info:
            mgr.image("sprites/ghost")
        assert "ghost.png" in str(exc_info.value)


class TestLoadSoundNotExist:
    """Load sound that doesn't exist."""

    def test_missing_sound_raises(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        with pytest.raises(AssetNotFoundError, match="Sound"):
            mgr.sound("nonexistent_sound")

    def test_missing_sound_error_lists_extensions(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        with pytest.raises(AssetNotFoundError) as exc_info:
            mgr.sound("missing_fx")
        msg = str(exc_info.value)
        assert "missing_fx.wav" in msg
        assert "missing_fx.ogg" in msg
        assert "missing_fx.mp3" in msg


class TestAssetCaching:
    """Asset caching (load same image twice returns same handle)."""

    def test_same_image_returns_same_handle(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        h1 = mgr.image("sprites/knight")
        h2 = mgr.image("sprites/knight")
        assert h1 is h2

    def test_same_sound_returns_same_handle(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        h1 = mgr.sound("sword_hit")
        h2 = mgr.sound("sword_hit")
        assert h1 is h2

    def test_different_images_return_different_handles(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        # Create another image
        (asset_dir / "images" / "sprites" / "archer.png").write_bytes(b"png")
        mgr = AssetManager(backend, base_path=asset_dir)
        h1 = mgr.image("sprites/knight")
        h2 = mgr.image("sprites/archer")
        assert h1 is not h2


class TestFramesNoMatch:
    """frames() with no matching files."""

    def test_no_matching_frames_raises(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        with pytest.raises(AssetNotFoundError, match="No animation frames"):
            mgr.frames("sprites/nonexistent_anim")

    def test_frames_error_includes_pattern(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        with pytest.raises(AssetNotFoundError) as exc_info:
            mgr.frames("sprites/missing_walk")
        assert "missing_walk" in str(exc_info.value)


class TestAssetMusicNotCached:
    """Music assets return fresh handles (streaming limitation)."""

    def test_music_path_is_cached(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        mgr.music("exploration")
        assert "exploration" in mgr._music_path_cache

    def test_music_missing_raises(
        self, backend: MockBackend, asset_dir: Path
    ) -> None:
        mgr = AssetManager(backend, base_path=asset_dir)
        with pytest.raises(AssetNotFoundError, match="Music"):
            mgr.music("nonexistent_track")


# ======================================================================
# 5. FSM EDGE CASES
# ======================================================================


class TestFSMTriggerUnknownEvent:
    """trigger unknown event (should return False)."""

    def test_unknown_event_returns_false(self) -> None:
        fsm = StateMachine(
            states=["idle", "walking"],
            initial="idle",
            transitions={"idle": {"walk": "walking"}},
        )
        result = fsm.trigger("fly")
        assert result is False
        assert fsm.state == "idle"

    def test_unknown_event_from_state_with_no_transitions(self) -> None:
        fsm = StateMachine(
            states=["idle", "walking"],
            initial="walking",
            transitions={"idle": {"walk": "walking"}},
        )
        # "walking" has no transitions defined
        result = fsm.trigger("walk")
        assert result is False
        assert fsm.state == "walking"


class TestFSMInvalidInitialState:
    """invalid initial state (should raise ValueError)."""

    def test_invalid_initial_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="not in states"):
            StateMachine(
                states=["idle", "walking"],
                initial="flying",
            )

    def test_empty_states_list_invalid_initial(self) -> None:
        with pytest.raises(ValueError, match="not in states"):
            StateMachine(
                states=[],
                initial="idle",
            )


class TestFSMTransitionToSelf:
    """transition to self (same state)."""

    def test_self_transition_changes_nothing(self) -> None:
        enter_count = [0]
        exit_count = [0]

        def on_enter() -> None:
            enter_count[0] += 1

        def on_exit() -> None:
            exit_count[0] += 1

        fsm = StateMachine(
            states=["idle"],
            initial="idle",
            transitions={"idle": {"reset": "idle"}},
            on_enter={"idle": on_enter},
            on_exit={"idle": on_exit},
        )

        # on_enter was called once at construction
        initial_enter_count = enter_count[0]
        assert initial_enter_count == 1

        result = fsm.trigger("reset")
        assert result is True
        assert fsm.state == "idle"
        # on_exit and on_enter should both be called for self-transition
        assert exit_count[0] == 1
        assert enter_count[0] == initial_enter_count + 1

    def test_self_transition_returns_true(self) -> None:
        fsm = StateMachine(
            states=["active"],
            initial="active",
            transitions={"active": {"refresh": "active"}},
        )
        assert fsm.trigger("refresh") is True


class TestFSMOnExitRaises:
    """on_exit callback raises - what happens to on_enter?"""

    def test_on_exit_raises_exception_propagates(self) -> None:
        """When on_exit raises, the exception propagates but state is already in target."""
        enter_called = [False]

        def on_exit_boom() -> None:
            raise RuntimeError("exit crashed")

        def on_enter_walking() -> None:
            enter_called[0] = True

        fsm = StateMachine(
            states=["idle", "walking"],
            initial="idle",
            transitions={"idle": {"walk": "walking"}},
            on_exit={"idle": on_exit_boom},
            on_enter={"walking": on_enter_walking},
        )

        # Looking at the source code: on_exit is called before state change.
        # The on_exit exception is NOT caught by the FSM - it propagates.
        # Let's see what actually happens.
        with pytest.raises(RuntimeError, match="exit crashed"):
            fsm.trigger("walk")

        # After on_exit raises, the state change and on_enter don't happen
        # because the exception propagates from on_exit before the state
        # assignment line. Let's verify what state we're in.
        # Looking at code:
        #   old_state = self._state
        #   if old_state in self._on_exit:
        #       self._on_exit[old_state]()  # <-- raises here
        #   self._state = target            # <-- never reached
        # So state should remain "idle"
        assert fsm.state == "idle"
        assert enter_called[0] is False


class TestFSMOnEnterRaises:
    """on_enter callback raises - should state rollback?"""

    def test_on_enter_raises_rolls_back_state(self) -> None:
        """When on_enter raises, the FSM rolls back to the previous state."""
        exit_called = [False]

        def on_exit_idle() -> None:
            exit_called[0] = True

        def on_enter_boom() -> None:
            raise RuntimeError("enter crashed")

        fsm = StateMachine(
            states=["idle", "walking"],
            initial="idle",
            transitions={"idle": {"walk": "walking"}},
            on_exit={"idle": on_exit_idle},
            on_enter={"walking": on_enter_boom},
        )

        with pytest.raises(RuntimeError, match="enter crashed"):
            fsm.trigger("walk")

        # Source code shows: state is rolled back on on_enter exception
        # self._state = old_state  (inside except block)
        assert fsm.state == "idle"
        # on_exit was still called (it ran before on_enter)
        assert exit_called[0] is True

    def test_on_enter_raises_at_construction(self) -> None:
        """If on_enter for the initial state raises, construction fails."""

        def boom() -> None:
            raise RuntimeError("init enter crash")

        with pytest.raises(RuntimeError, match="init enter crash"):
            StateMachine(
                states=["idle"],
                initial="idle",
                on_enter={"idle": boom},
            )


class TestFSMTransitionValidation:
    """Validate transition source and target at construction time."""

    def test_invalid_transition_source_raises(self) -> None:
        with pytest.raises(ValueError, match="Transition source"):
            StateMachine(
                states=["idle", "walking"],
                initial="idle",
                transitions={"flying": {"land": "idle"}},
            )

    def test_invalid_transition_target_raises(self) -> None:
        with pytest.raises(ValueError, match="Transition target"):
            StateMachine(
                states=["idle", "walking"],
                initial="idle",
                transitions={"idle": {"teleport": "flying"}},
            )


class TestFSMValidEvents:
    """valid_events property returns events from current state."""

    def test_valid_events_from_state_with_transitions(self) -> None:
        fsm = StateMachine(
            states=["idle", "walking", "running"],
            initial="idle",
            transitions={
                "idle": {"walk": "walking", "run": "running"},
                "walking": {"stop": "idle"},
            },
        )
        events = fsm.valid_events
        assert sorted(events) == ["run", "walk"]

    def test_valid_events_from_state_with_no_transitions(self) -> None:
        fsm = StateMachine(
            states=["idle", "dead"],
            initial="dead",
            transitions={"idle": {"die": "dead"}},
        )
        assert fsm.valid_events == []

    def test_valid_events_updates_after_transition(self) -> None:
        fsm = StateMachine(
            states=["idle", "walking"],
            initial="idle",
            transitions={
                "idle": {"walk": "walking"},
                "walking": {"stop": "idle"},
            },
        )
        assert "walk" in fsm.valid_events
        fsm.trigger("walk")
        assert "stop" in fsm.valid_events
        assert "walk" not in fsm.valid_events


class TestFSMNoTransitions:
    """FSM with no transitions at all."""

    def test_no_transitions_trigger_returns_false(self) -> None:
        fsm = StateMachine(
            states=["idle"],
            initial="idle",
        )
        assert fsm.trigger("anything") is False
        assert fsm.state == "idle"

    def test_no_transitions_valid_events_empty(self) -> None:
        fsm = StateMachine(
            states=["start"],
            initial="start",
        )
        assert fsm.valid_events == []


class TestFSMMultipleStates:
    """FSM with a longer chain of transitions."""

    def test_chain_transitions(self) -> None:
        fsm = StateMachine(
            states=["a", "b", "c", "d"],
            initial="a",
            transitions={
                "a": {"next": "b"},
                "b": {"next": "c"},
                "c": {"next": "d"},
            },
        )
        assert fsm.state == "a"
        assert fsm.trigger("next") is True
        assert fsm.state == "b"
        assert fsm.trigger("next") is True
        assert fsm.state == "c"
        assert fsm.trigger("next") is True
        assert fsm.state == "d"
        # No transitions from "d"
        assert fsm.trigger("next") is False
        assert fsm.state == "d"
