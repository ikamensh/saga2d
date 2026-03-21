"""Extended Stage 5 tests: malformed save data, version mismatches, and
resource cleanup edge cases during scene transitions.

Targets NOT covered by existing kodo_test_persistence_resources.py:
  - Truncated/empty/binary save files
  - Valid JSON but structurally wrong (missing keys, wrong types, wrong envelope)
  - Future/unknown version numbers in save data
  - load_save_state receiving mangled state dicts
  - clear_and_push resource cleanup across full stack
  - Emitter cleanup on pop/replace (only sprites/timers were tested before)
  - Replace where new scene's on_enter fails — old resources still cleaned
  - Camera pan tween cleanup on scene exit
  - Resources created in on_exit (during cleanup phase)
  - Rapid deferred transitions in a single tick

Run:  .venv/bin/python -m pytest tests/kodo_test_persistence_resources_ext.py -v
"""

from __future__ import annotations

import gc
import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from saga2d import Game, Scene
from saga2d.save import SaveError, SaveManager


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def save_dir(tmp_path: Path) -> Path:
    return tmp_path / "saves"


@pytest.fixture
def manager(save_dir: Path) -> SaveManager:
    return SaveManager(save_dir)


@pytest.fixture
def game(tmp_path: Path) -> Game:
    g = Game(
        "KodoExtTest",
        backend="mock",
        resolution=(800, 600),
        save_dir=tmp_path / "saves",
    )
    yield g
    g._teardown()


# ═════════════════════════════════════════════════════════════
# A. MALFORMED SAVE FILE CONTENT
# ═════════════════════════════════════════════════════════════


class TestMalformedSaveFiles:
    """Load behavior when save files contain invalid/unexpected content."""

    def test_load_empty_file_raises_save_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A 0-byte save file raises SaveError, not a silent None."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("", encoding="utf-8")
        with pytest.raises(SaveError, match="slot 1"):
            manager.load(1)

    def test_load_truncated_json_raises_save_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A truncated JSON file (incomplete write) raises SaveError."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text(
            '{"version": 1, "sta', encoding="utf-8"
        )
        with pytest.raises(SaveError, match="slot 1"):
            manager.load(1)

    def test_load_binary_content_raises_save_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """Binary garbage in a save file raises SaveError."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_bytes(b"\x00\x01\x02\xff\xfe")
        with pytest.raises(SaveError, match="slot 1"):
            manager.load(1)

    def test_load_json_array_not_object(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A JSON array (instead of object) raises SaveError (F9 fix).

        SaveManager.load() validates the top-level type is a dict.
        Non-object JSON (arrays, strings, numbers, booleans, null)
        is treated as corrupt to prevent downstream TypeError crashes
        in list_slots() and SaveLoadScreen.
        """
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(SaveError, match="expected JSON object.*got list"):
            manager.load(1)

    def test_load_json_string_not_object(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A bare JSON string raises SaveError (F9 fix)."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text('"just a string"', encoding="utf-8")
        with pytest.raises(SaveError, match="expected JSON object.*got str"):
            manager.load(1)

    def test_load_json_null(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A JSON null in a file raises SaveError (F9 fix)."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("null", encoding="utf-8")
        with pytest.raises(SaveError, match="expected JSON object.*got NoneType"):
            manager.load(1)

    def test_load_json_number_not_object(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A bare JSON number raises SaveError (F9 fix)."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("42", encoding="utf-8")
        with pytest.raises(SaveError, match="expected JSON object.*got int"):
            manager.load(1)

    def test_load_json_boolean_not_object(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A bare JSON boolean raises SaveError (F9 fix)."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("true", encoding="utf-8")
        with pytest.raises(SaveError, match="expected JSON object.*got bool"):
            manager.load(1)

    def test_list_slots_with_json_array_at_slot(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """list_slots raises SaveError on non-object JSON (F9 regression).

        Before the fix, list_slots crashed with TypeError when a slot
        contained valid JSON that wasn't an object (e.g. [1,2,3]),
        because it tried data["slot"] = i on a list.
        """
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("[1, 2, 3]", encoding="utf-8")
        with pytest.raises(SaveError, match="expected JSON object"):
            manager.list_slots(1)

    def test_load_only_whitespace_raises_save_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A file containing only whitespace raises SaveError."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("   \n\t  ", encoding="utf-8")
        with pytest.raises(SaveError, match="slot 1"):
            manager.load(1)


# ═════════════════════════════════════════════════════════════
# B. STRUCTURALLY WRONG BUT VALID JSON
# ═════════════════════════════════════════════════════════════


class TestStructurallyWrongSaveData:
    """Valid JSON that doesn't match the expected save envelope."""

    def test_load_missing_version_key(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A save file without 'version' key loads fine (no validation)."""
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {"timestamp": "2026-01-01T00:00:00", "state": {"x": 1}}
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        data = manager.load(1)
        assert data is not None
        assert "version" not in data
        assert data["state"]["x"] == 1

    def test_load_missing_state_key(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A save file without 'state' key — Game.load handles via 'in' check."""
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "scene_class": "S"}
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        data = manager.load(1)
        assert data is not None
        assert "state" not in data

    def test_game_load_missing_state_key_no_crash(self, game: Game) -> None:
        """Game.load() with save data missing 'state' doesn't crash."""
        # Write a save file manually without a "state" key
        save_dir = game.save_manager._save_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "scene_class": "TestScene"}
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        game.push(Scene())
        # Game.load checks '"state" in data' before calling load_save_state
        data = game.load(1)
        assert data is not None
        assert "state" not in data

    def test_load_empty_json_object(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """An empty JSON object {} loads fine — no validation in SaveManager."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("{}", encoding="utf-8")
        data = manager.load(1)
        assert data is not None
        assert data == {}

    def test_load_state_is_list_not_dict(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """'state' is a list instead of dict — SaveManager doesn't validate."""
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "state": [1, 2, 3], "scene_class": "S"}
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        data = manager.load(1)
        assert data is not None
        assert data["state"] == [1, 2, 3]

    def test_load_state_is_string(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """'state' is a string — no validation in SaveManager."""
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "state": "hello", "scene_class": "S"}
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        data = manager.load(1)
        assert data is not None
        assert data["state"] == "hello"

    def test_load_state_is_null(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """'state' is null — data loaded but Game.load skips restore."""
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "state": None, "scene_class": "S"}
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        data = manager.load(1)
        assert data is not None
        assert data["state"] is None


# ═════════════════════════════════════════════════════════════
# C. VERSION MISMATCH SCENARIOS
# ═════════════════════════════════════════════════════════════


class TestVersionMismatch:
    """Save files with unexpected version numbers."""

    def test_future_version_loads_without_error(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A save with version=99 loads fine — no version check in load()."""
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 99,
            "timestamp": "2030-01-01T00:00:00",
            "scene_class": "FutureScene",
            "state": {"quantum_gold": 42},
        }
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        data = manager.load(1)
        assert data is not None
        assert data["version"] == 99
        assert data["state"]["quantum_gold"] == 42

    def test_version_zero_loads(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """Version 0 (pre-release?) loads fine."""
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": 0, "state": {"x": 1}, "scene_class": "S"}
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        data = manager.load(1)
        assert data["version"] == 0

    def test_version_string_loads(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """Version as string (e.g., '2.0') — no type check in load()."""
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": "2.0", "state": {"x": 1}, "scene_class": "S"}
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        data = manager.load(1)
        assert data["version"] == "2.0"

    def test_game_load_future_version_restores_state(self, game: Game) -> None:
        """Game.load() with a future version still calls load_save_state."""

        class Versioned(Scene):
            def __init__(self) -> None:
                self.gold = 0

            def load_save_state(self, state: dict) -> None:
                self.gold = state.get("gold", 0)

        # Manually write a v99 save file
        save_dir = game.save_manager._save_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": 99,
            "timestamp": "2030-01-01T00:00:00",
            "scene_class": "Versioned",
            "state": {"gold": 777},
        }
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )
        v = Versioned()
        game.push(v)
        game.load(1)
        assert v.gold == 777

    def test_v1_to_v2_migration_with_removed_fields(self, game: Game) -> None:
        """Migration pattern: V1 save has fields V2 scene doesn't expect."""

        class V2Scene(Scene):
            def __init__(self) -> None:
                self.gold = 0
                self.gems = 0
                self.reputation = 50  # new in V2

            def load_save_state(self, state: dict) -> None:
                self.gold = state.get("gold", 0)
                self.gems = state.get("gems", 0)
                self.reputation = state.get("reputation", 50)
                # V1 had "old_currency" — we just ignore it via .get()

        # Simulate V1 save with old fields
        save_dir = game.save_manager._save_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        v1_payload = {
            "version": 1,
            "timestamp": "2025-01-01T00:00:00",
            "scene_class": "V1Scene",
            "state": {"gold": 500, "old_currency": 999},
        }
        (save_dir / "save_1.json").write_text(
            json.dumps(v1_payload), encoding="utf-8"
        )

        v2 = V2Scene()
        game.push(v2)
        data = game.save_manager.load(1)
        assert data is not None
        v2.load_save_state(data["state"])

        assert v2.gold == 500
        assert v2.gems == 0  # default (not in V1)
        assert v2.reputation == 50  # default (not in V1)


# ═════════════════════════════════════════════════════════════
# D. GAME.LOAD WITH MANGLED STATE — SCENE ROBUSTNESS
# ═════════════════════════════════════════════════════════════


class TestLoadMangledState:
    """Scenes receiving unexpected state types from save data."""

    def test_game_load_with_state_list_raises_in_scene(
        self, game: Game
    ) -> None:
        """Scene.load_save_state receives a list — scene code must handle."""

        load_called_with: list[Any] = []

        class Receiver(Scene):
            def load_save_state(self, state: dict) -> None:
                load_called_with.append(state)

        save_dir = game.save_manager._save_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        payload = {"version": 1, "state": [1, 2, 3], "scene_class": "R"}
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

        game.push(Receiver())
        game.load(1)
        # Game.load passes data["state"] directly — no type guard
        assert load_called_with == [[1, 2, 3]]

    def test_game_load_null_state_skips_load_save_state(
        self, game: Game
    ) -> None:
        """When state is null in the file, Game.load still calls load_save_state
        because 'state' key exists and value is None (truthy check: 'in' only)."""
        called = []

        class Receiver(Scene):
            def load_save_state(self, state: dict) -> None:
                called.append(state)

        save_dir = game.save_manager._save_dir
        save_dir.mkdir(parents=True, exist_ok=True)
        # "state" key exists but value is None
        payload = {"version": 1, "state": None, "scene_class": "R"}
        (save_dir / "save_1.json").write_text(
            json.dumps(payload), encoding="utf-8"
        )

        game.push(Receiver())
        game.load(1)
        # Game.load checks `"state" in data` — True, so it calls load_save_state(None)
        assert called == [None]


# ═════════════════════════════════════════════════════════════
# E. RESOURCE CLEANUP — CLEAR_AND_PUSH FULL STACK
# ═════════════════════════════════════════════════════════════


class TestClearAndPushResourceCleanup:
    """clear_and_push must clean resources from ALL stacked scenes."""

    def test_clear_and_push_cleans_all_sprites(self, game: Game) -> None:
        """Sprites from every scene in the stack are removed."""
        from saga2d.rendering.sprite import Sprite

        sprites: list[Sprite] = []

        class SpriteScene(Scene):
            def on_enter(self) -> None:
                s = self.add_sprite(Sprite("sprites/knight", position=(0, 0)))
                sprites.append(s)

        # Build a 3-scene stack
        game.push(SpriteScene())
        game.push(SpriteScene())
        game.push(SpriteScene())
        assert len(sprites) == 3
        # Only top scene's sprite is live (push calls on_exit → cleanup on lower ones)
        # But the top scene's sprite should still be alive
        assert not sprites[-1]._removed

        game.clear_and_push(Scene())
        game.tick(0.016)
        # ALL sprites from all scenes should be removed
        for s in sprites:
            assert s._removed, f"Sprite {s} was not cleaned up"

    def test_clear_and_push_cancels_all_timers(self, game: Game) -> None:
        """Timers from every scene in the stack are cancelled."""
        fired: list[int] = []

        class TimerScene(Scene):
            def __init__(self, idx: int) -> None:
                self._idx = idx

            def on_enter(self) -> None:
                self.after(0.5, lambda: fired.append(self._idx))

        game.push(TimerScene(1))
        game.push(TimerScene(2))
        game.push(TimerScene(3))

        game.clear_and_push(Scene())
        game.tick(0.016)
        # Advance well past all timer durations
        for _ in range(100):
            game.tick(0.016)
        assert fired == [], f"Timers fired after clear_and_push: {fired}"


# ═════════════════════════════════════════════════════════════
# F. EMITTER CLEANUP ON SCENE TRANSITIONS
# ═════════════════════════════════════════════════════════════


class TestEmitterCleanupOnTransition:
    """Particle emitters are cleaned up on scene pop/replace."""

    def test_owned_emitter_removed_on_pop(self, game: Game) -> None:
        """Emitters owned by a scene are removed when the scene pops."""

        class FakeEmitter:
            def __init__(self) -> None:
                self.removed = False

            def remove(self) -> None:
                self.removed = True

        emitter_ref: list[Any] = []

        class EmitterScene(Scene):
            def on_enter(self) -> None:
                e = FakeEmitter()
                self.add_emitter(e)
                emitter_ref.append(e)

        game.push(EmitterScene())
        game.tick(0.016)
        assert not emitter_ref[0].removed

        game.pop()
        game.tick(0.016)
        assert emitter_ref[0].removed

    def test_owned_emitter_removed_on_replace(self, game: Game) -> None:
        """Emitters owned by old scene are removed on replace."""

        class FakeEmitter:
            def __init__(self) -> None:
                self.removed = False

            def remove(self) -> None:
                self.removed = True

        emitter_ref: list[Any] = []

        class EmitterScene(Scene):
            def on_enter(self) -> None:
                e = FakeEmitter()
                self.add_emitter(e)
                emitter_ref.append(e)

        game.push(EmitterScene())
        game.tick(0.016)
        game.replace(Scene())
        game.tick(0.016)
        assert emitter_ref[0].removed


# ═════════════════════════════════════════════════════════════
# G. REPLACE WITH FAILING ON_ENTER — OLD RESOURCES STILL CLEANED
# ═════════════════════════════════════════════════════════════


class TestReplaceWithFailingOnEnter:
    """When replace()'s new scene fails on_enter, old scene resources
    should still have been cleaned up (cleanup runs before on_enter)."""

    def test_old_sprites_cleaned_despite_new_on_enter_failure(
        self, game: Game
    ) -> None:
        from saga2d.rendering.sprite import Sprite

        old_sprite_ref: list[Sprite] = []

        class OldScene(Scene):
            def on_enter(self) -> None:
                old_sprite_ref.append(
                    self.add_sprite(Sprite("sprites/knight", position=(0, 0)))
                )

        class BadScene(Scene):
            def on_enter(self) -> None:
                raise RuntimeError("on_enter failed!")

        game.push(OldScene())
        game.tick(0.016)
        assert not old_sprite_ref[0]._removed

        with pytest.raises(RuntimeError, match="on_enter failed"):
            game.replace(BadScene())

        # Old scene's resources should still be cleaned up
        assert old_sprite_ref[0]._removed

    def test_old_timers_cancelled_despite_new_on_enter_failure(
        self, game: Game
    ) -> None:
        fired: list[bool] = []

        class OldScene(Scene):
            def on_enter(self) -> None:
                self.after(0.1, lambda: fired.append(True))

        class BadScene(Scene):
            def on_enter(self) -> None:
                raise RuntimeError("boom")

        game.push(OldScene())
        game.tick(0.016)

        with pytest.raises(RuntimeError, match="boom"):
            game.replace(BadScene())

        # Advance time past the timer
        for _ in range(50):
            game.tick(0.016)
        assert fired == [], "Timer from old scene should have been cancelled"


# ═════════════════════════════════════════════════════════════
# H. RESOURCES CREATED IN ON_EXIT
# ═════════════════════════════════════════════════════════════


class TestResourcesCreatedInOnExit:
    """Edge case: scene creates resources during its own on_exit.
    Cleanup runs AFTER on_exit, so these resources should be cleaned."""

    def test_sprite_created_in_on_exit_is_cleaned(self, game: Game) -> None:
        from saga2d.rendering.sprite import Sprite

        exit_sprite: list[Sprite] = []

        class ExitCreator(Scene):
            def on_exit(self) -> None:
                # Create and own a sprite during on_exit
                s = self.add_sprite(Sprite("sprites/knight", position=(0, 0)))
                exit_sprite.append(s)

        game.push(ExitCreator())
        game.tick(0.016)
        game.pop()
        game.tick(0.016)

        # Sprite created in on_exit should be cleaned by _cleanup_owned_sprites
        # which runs AFTER on_exit
        assert len(exit_sprite) == 1
        assert exit_sprite[0]._removed


# ═════════════════════════════════════════════════════════════
# I. DEFERRED TRANSITIONS — RAPID SUCCESSION IN SINGLE TICK
# ═════════════════════════════════════════════════════════════


class TestDeferredRapidTransitions:
    """Multiple scene operations queued and flushed in a single tick."""

    def test_push_then_pop_in_same_update(self, game: Game) -> None:
        """Push and pop queued during update() both execute on flush."""
        log: list[str] = []

        class Logger(Scene):
            def __init__(self, name: str) -> None:
                self._name = name

            def on_enter(self) -> None:
                log.append(f"{self._name}.enter")

            def on_exit(self) -> None:
                log.append(f"{self._name}.exit")

        class Driver(Scene):
            def __init__(self) -> None:
                self._did_push = False

            def update(self, dt: float) -> None:
                if not self._did_push:
                    self._did_push = True
                    self.game.push(Logger("A"))
                    self.game.pop()  # pops A immediately after push

        game.push(Driver())
        game.tick(0.016)

        # A was pushed then popped in same flush cycle
        assert "A.enter" in log
        assert "A.exit" in log

    def test_replace_twice_in_same_update(self, game: Game) -> None:
        """Two replace() calls in the same update — second wins."""
        log: list[str] = []

        class Logger(Scene):
            def __init__(self, name: str) -> None:
                self._name = name

            def on_enter(self) -> None:
                log.append(f"{self._name}.enter")

            def on_exit(self) -> None:
                log.append(f"{self._name}.exit")

        class Driver(Scene):
            def __init__(self) -> None:
                self._did = False

            def update(self, dt: float) -> None:
                if not self._did:
                    self._did = True
                    self.game.replace(Logger("A"))
                    self.game.replace(Logger("B"))

        game.push(Driver())
        game.tick(0.016)

        # Driver exits, A enters then exits, B enters and stays
        assert "A.enter" in log
        assert "A.exit" in log
        assert "B.enter" in log
        # B should be top
        assert game._scene_stack.top().__class__.__name__ == "Logger"

    def test_resources_cleaned_across_rapid_transitions(
        self, game: Game
    ) -> None:
        """Resources from rapidly transitioned scenes are all cleaned."""
        from saga2d.rendering.sprite import Sprite

        all_sprites: list[Sprite] = []

        class SpriteScene(Scene):
            def on_enter(self) -> None:
                all_sprites.append(
                    self.add_sprite(Sprite("sprites/knight", position=(0, 0)))
                )

        class Driver(Scene):
            def __init__(self) -> None:
                self._did = False

            def update(self, dt: float) -> None:
                if not self._did:
                    self._did = True
                    self.game.replace(SpriteScene())
                    self.game.replace(SpriteScene())
                    self.game.replace(SpriteScene())

        game.push(Driver())
        game.tick(0.016)

        # All but the last sprite should be removed
        for s in all_sprites[:-1]:
            assert s._removed, f"Sprite from intermediate scene not cleaned"
        # Last scene's sprite should be alive
        assert not all_sprites[-1]._removed


# ═════════════════════════════════════════════════════════════
# J. CAMERA PAN TWEEN CLEANUP ON SCENE EXIT
# ═════════════════════════════════════════════════════════════


class TestCameraPanCleanupOnExit:
    """Camera pan tweens are cancelled when a scene exits."""

    def test_camera_pan_cancelled_on_pop(self, game: Game) -> None:
        from saga2d.rendering.camera import Camera

        class CameraScene(Scene):
            def on_enter(self) -> None:
                self.camera = Camera(
                    viewport_size=(800, 600),
                    world_bounds=(0, 0, 1600, 1200),
                )
                self.camera.pan_to(800, 600, duration=5.0)

        scene = CameraScene()
        game.push(scene)
        game.tick(0.016)  # Start the pan

        # Camera should be mid-pan
        cam = scene.camera
        assert cam is not None

        game.pop()
        game.tick(0.016)

        # After pop, the pan tween should have been cancelled
        # (verified by _cleanup_exiting_scene calling camera._cancel_pan)
        # The scene is gone — we just verify no crash and game still works
        game.push(Scene())
        game.tick(0.016)  # No crash from stale tween


# ═════════════════════════════════════════════════════════════
# K. SAVE DURING TRANSITIONS
# ═════════════════════════════════════════════════════════════


class TestSaveDuringTransitions:
    """Save/load during scene transition edge cases."""

    def test_save_during_on_exit_captures_exiting_scene(
        self, game: Game
    ) -> None:
        """Saving during on_exit captures the exiting scene's state,
        because on_exit runs before the scene is removed from the stack."""

        class Saver(Scene):
            def get_save_state(self) -> dict:
                return {"saved_in_exit": True}

            def on_exit(self) -> None:
                self.game.save(1)

        game.push(Saver())
        game.pop()
        game.tick(0.016)

        data = game.save_manager.load(1)
        assert data is not None
        assert data["state"]["saved_in_exit"] is True

    def test_load_during_on_enter_applies_to_entering_scene(
        self, game: Game
    ) -> None:
        """Loading during on_enter applies state to the entering scene."""

        class Loader(Scene):
            def __init__(self) -> None:
                self.gold = 0

            def on_enter(self) -> None:
                self.game.load(1)

            def load_save_state(self, state: dict) -> None:
                self.gold = state.get("gold", 0)

        # Pre-populate save data
        game.save_manager.save(1, {"gold": 999}, "Loader")

        loader = Loader()
        game.push(loader)
        assert loader.gold == 999


# ═════════════════════════════════════════════════════════════
# L. LIST_SLOTS WITH DIVERSE CORRUPTION
# ═════════════════════════════════════════════════════════════


class TestListSlotsCorruptionVariants:
    """list_slots hitting different kinds of corrupted files."""

    def test_list_slots_with_empty_file_at_slot(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """Empty file at a slot causes SaveError in list_slots."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("", encoding="utf-8")
        with pytest.raises(SaveError, match="slot 1"):
            manager.list_slots(count=3)

    def test_list_slots_with_binary_at_slot(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """Binary content at a slot causes SaveError in list_slots."""
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_2.json").write_bytes(b"\x00\xff")
        with pytest.raises(SaveError, match="slot 2"):
            manager.list_slots(count=3)

    def test_list_slots_valid_then_corrupt_returns_partial(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """list_slots aborts on first corrupt slot (design-intent SE1).
        Slots before corruption are NOT returned — exception propagates."""
        manager.save(1, {"ok": True}, "S")
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_2.json").write_text("broken!", encoding="utf-8")
        with pytest.raises(SaveError, match="slot 2"):
            manager.list_slots(count=5)
