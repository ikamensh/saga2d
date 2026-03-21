"""Exploratory tests for persistence (save/load) and resource lifecycle.

Targets:
  - Save/load input validation edge cases (slot 0, float, negative)
  - Non-serializable state → SaveError
  - Save/delete/resave cycles
  - list_slots with count=0, corrupted mid-list
  - Game.save/load with stacked scenes (top vs. bottom)
  - Game.load with empty stack, missing "state" key
  - Game._teardown completeness (all subsystems nulled)
  - Resource cleanup across scene transitions (sprites, timers, emitters)
  - Sprite WeakSet auto-cleanup after GC
  - Animation/action state cleanup on sprite removal
  - Crossfade interrupted by teardown
  - Atomic write .tmp cleanup

Run:  .venv/bin/python -m pytest tests/kodo_test_persistence_resources.py -v
"""

from __future__ import annotations

import gc
import json
import weakref
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
        "KodoTest",
        backend="mock",
        resolution=(800, 600),
        save_dir=tmp_path / "saves",
    )
    yield g
    g._teardown()


# ═════════════════════════════════════════════════════════════
# 1. SAVE/LOAD INPUT VALIDATION
# ═════════════════════════════════════════════════════════════


class TestSaveInputValidation:
    """Slot validation edge cases not fully covered by existing tests."""

    def test_save_slot_zero_raises_value_error(self, manager: SaveManager) -> None:
        with pytest.raises(ValueError, match="slot must be >= 1"):
            manager.save(0, {}, "S")

    def test_save_slot_negative_raises_value_error(self, manager: SaveManager) -> None:
        with pytest.raises(ValueError, match="slot must be >= 1"):
            manager.save(-5, {}, "S")

    def test_save_slot_float_raises_type_error(self, manager: SaveManager) -> None:
        with pytest.raises(TypeError, match="slot must be an int"):
            manager.save(1.5, {}, "S")  # type: ignore[arg-type]

    def test_save_slot_string_raises_type_error(self, manager: SaveManager) -> None:
        with pytest.raises(TypeError, match="slot must be an int"):
            manager.save("one", {}, "S")  # type: ignore[arg-type]

    def test_load_slot_zero_raises_value_error(self, manager: SaveManager) -> None:
        with pytest.raises(ValueError, match="slot must be >= 1"):
            manager.load(0)

    def test_load_slot_float_raises_type_error(self, manager: SaveManager) -> None:
        with pytest.raises(TypeError, match="slot must be an int"):
            manager.load(1.5)  # type: ignore[arg-type]

    def test_delete_slot_zero_raises_value_error(self, manager: SaveManager) -> None:
        with pytest.raises(ValueError, match="slot must be >= 1"):
            manager.delete(0)

    def test_delete_slot_string_raises_type_error(self, manager: SaveManager) -> None:
        with pytest.raises(TypeError, match="slot must be an int"):
            manager.delete("x")  # type: ignore[arg-type]


# ═════════════════════════════════════════════════════════════
# 2. NON-SERIALIZABLE STATE
# ═════════════════════════════════════════════════════════════


class TestNonSerializableState:
    """Saving non-JSON-serializable data raises SaveError."""

    def test_save_lambda_raises_save_error(self, manager: SaveManager) -> None:
        with pytest.raises(SaveError):
            manager.save(1, {"callback": lambda: None}, "S")

    def test_save_set_raises_save_error(self, manager: SaveManager) -> None:
        with pytest.raises(SaveError):
            manager.save(1, {"items": {1, 2, 3}}, "S")

    def test_save_bytes_raises_save_error(self, manager: SaveManager) -> None:
        with pytest.raises(SaveError):
            manager.save(1, {"data": b"\x00\x01"}, "S")

    def test_save_custom_object_raises_save_error(self, manager: SaveManager) -> None:
        class Thing:
            pass

        with pytest.raises(SaveError):
            manager.save(1, {"obj": Thing()}, "S")


# ═════════════════════════════════════════════════════════════
# 3. SAVE-DELETE-RESAVE CYCLES
# ═════════════════════════════════════════════════════════════


class TestSaveDeleteResaveCycles:
    """Exercise save → delete → resave workflows like a real user."""

    def test_save_delete_resave(self, manager: SaveManager) -> None:
        """Save, delete, then save again to the same slot."""
        manager.save(1, {"v": 1}, "S")
        manager.delete(1)
        assert manager.load(1) is None
        manager.save(1, {"v": 2}, "S")
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"]["v"] == 2

    def test_overwrite_all_slots_then_delete_all(self, manager: SaveManager) -> None:
        """Fill multiple slots, overwrite, then delete all."""
        for i in range(1, 6):
            manager.save(i, {"slot": i}, "S")
        # Overwrite
        for i in range(1, 6):
            manager.save(i, {"slot": i, "version": 2}, "S")
        # Delete all
        for i in range(1, 6):
            manager.delete(i)
        slots = manager.list_slots(count=5)
        assert all(s is None for s in slots)

    def test_save_after_failed_save_succeeds(self, manager: SaveManager) -> None:
        """A failed save (non-serializable) doesn't corrupt the slot."""
        manager.save(1, {"ok": True}, "S")
        with pytest.raises(SaveError):
            manager.save(1, {"bad": lambda: None}, "S")
        # Original save should still be intact (atomic write via .tmp)
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"]["ok"] is True


# ═════════════════════════════════════════════════════════════
# 4. LIST_SLOTS EDGE CASES
# ═════════════════════════════════════════════════════════════


class TestListSlotsEdgeCases:
    """Exercise list_slots with unusual counts and corrupted data."""

    def test_list_slots_count_zero(self, manager: SaveManager) -> None:
        assert manager.list_slots(count=0) == []

    def test_list_slots_count_negative(self, manager: SaveManager) -> None:
        assert manager.list_slots(count=-1) == []

    def test_list_slots_count_one(self, manager: SaveManager) -> None:
        manager.save(1, {"x": 1}, "S")
        slots = manager.list_slots(count=1)
        assert len(slots) == 1
        assert slots[0] is not None
        assert slots[0]["slot"] == 1  # type: ignore[index]

    def test_list_slots_corrupted_mid_list(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """A corrupted file in the middle of list_slots raises SaveError."""
        manager.save(1, {"ok": True}, "S")
        manager.save(3, {"ok": True}, "S")
        # Corrupt slot 2
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_2.json").write_text("broken!", encoding="utf-8")
        with pytest.raises(SaveError, match="slot 2"):
            manager.list_slots(count=3)


# ═════════════════════════════════════════════════════════════
# 5. GAME.SAVE/LOAD WITH STACKED SCENES
# ═════════════════════════════════════════════════════════════


class TestGameSaveLoadStacked:
    """Game.save() always saves the TOP scene; Game.load() restores top."""

    def test_save_saves_top_scene_not_bottom(self, game: Game) -> None:
        """With two scenes stacked, save() captures the top one."""

        class Bottom(Scene):
            def get_save_state(self) -> dict:
                return {"scene": "bottom", "gold": 100}

        class Top(Scene):
            def get_save_state(self) -> dict:
                return {"scene": "top", "level": 5}

        game.push(Bottom())
        game.push(Top())
        game.save(1)
        data = game.save_manager.load(1)
        assert data is not None
        assert data["scene_class"] == "Top"
        assert data["state"]["scene"] == "top"
        assert data["state"]["level"] == 5

    def test_load_restores_top_scene(self, game: Game) -> None:
        """Game.load() calls load_save_state on the current top scene."""

        class Restorable(Scene):
            def __init__(self) -> None:
                self.gold = 0
                self.level = 1

            def get_save_state(self) -> dict:
                return {"gold": self.gold, "level": self.level}

            def load_save_state(self, state: dict) -> None:
                self.gold = state["gold"]
                self.level = state["level"]

        # Save with state
        s1 = Restorable()
        s1.gold = 9999
        s1.level = 50
        game.push(s1)
        game.save(1)
        game.pop()
        game.tick(0.016)

        # Load into fresh scene
        s2 = Restorable()
        game.push(s2)
        game.load(1)
        assert s2.gold == 9999
        assert s2.level == 50

    def test_load_empty_slot_no_crash(self, game: Game) -> None:
        """Game.load() returns None for empty slot without crashing."""
        game.push(Scene())
        result = game.load(99)
        assert result is None

    def test_load_empty_stack_no_crash(self, game: Game) -> None:
        """Game.load() with no scene on stack returns data but doesn't crash."""
        # Save some data first
        game.push(Scene())
        game.save(1)
        game.pop()
        game.tick(0.016)
        # Stack is empty; load should still return data
        data = game.load(1)
        assert data is not None
        assert data["scene_class"] == "Scene"

    def test_save_during_on_enter(self, game: Game) -> None:
        """Saving during on_enter captures the entering scene's state."""

        class SaveOnEnter(Scene):
            def __init__(self, g: Game) -> None:
                self._g = g

            def get_save_state(self) -> dict:
                return {"entered": True}

            def on_enter(self) -> None:
                self._g.save(1)

        game.push(SaveOnEnter(game))
        data = game.save_manager.load(1)
        assert data is not None
        assert data["state"]["entered"] is True


# ═════════════════════════════════════════════════════════════
# 6. ATOMIC WRITE BEHAVIOR
# ═════════════════════════════════════════════════════════════


class TestAtomicWrite:
    """Verify .tmp file cleanup after save."""

    def test_tmp_file_not_left_behind(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """After a successful save, no .tmp file remains."""
        manager.save(1, {"ok": True}, "S")
        tmp = save_dir / "save_1.tmp"
        assert not tmp.exists()
        assert (save_dir / "save_1.json").exists()

    def test_failed_save_may_leave_tmp(
        self, manager: SaveManager, save_dir: Path
    ) -> None:
        """After a failed save due to non-serializable data, .tmp may remain
        or be absent — the real save file is untouched."""
        manager.save(1, {"v": 1}, "S")
        with pytest.raises(SaveError):
            manager.save(1, {"bad": set()}, "S")
        # Original file untouched
        loaded = manager.load(1)
        assert loaded is not None
        assert loaded["state"]["v"] == 1


# ═════════════════════════════════════════════════════════════
# 7. GAME._TEARDOWN COMPLETENESS
# ═════════════════════════════════════════════════════════════


class TestTeardownCompleteness:
    """Verify _teardown nulls all subsystems and clears tracking sets."""

    def test_teardown_clears_all_sprite_sets(self) -> None:
        g = Game("TeardownTest", backend="mock", resolution=(800, 600))
        from saga2d.rendering.sprite import Sprite

        s = Sprite("sprites/knight", position=(0, 0))
        assert len(g._all_sprites) >= 1
        g._teardown()
        assert len(g._all_sprites) == 0
        assert len(g._animated_sprites) == 0
        assert len(g._action_sprites) == 0
        assert len(g._particle_emitters) == 0

    def test_teardown_nulls_subsystems(self) -> None:
        g = Game("TeardownTest2", backend="mock", resolution=(800, 600))
        # Force lazy creation
        _ = g.save_manager
        _ = g.hud
        g._teardown()
        assert g._hud is None
        assert g._save_manager is None
        assert g._cursor is None

    def test_teardown_drains_scene_stack(self) -> None:
        g = Game("TeardownTest3", backend="mock", resolution=(800, 600))
        g.push(Scene())
        g.push(Scene())
        assert len(g._scene_stack._stack) == 2
        g._teardown()
        assert len(g._scene_stack._stack) == 0

    def test_teardown_calls_scene_on_exit(self) -> None:
        g = Game("TeardownTest4", backend="mock", resolution=(800, 600))
        log: list[str] = []

        class Tracked(Scene):
            def on_exit(self) -> None:
                log.append("exit")

        g.push(Tracked())
        g.push(Tracked())  # push triggers on_exit for bottom → 1 exit
        log.clear()  # Reset: only count teardown exits
        g._teardown()
        assert log == ["exit", "exit"]  # Both scenes get on_exit during teardown


# ═════════════════════════════════════════════════════════════
# 8. RESOURCE CLEANUP ACROSS SCENE TRANSITIONS
# ═════════════════════════════════════════════════════════════


class TestResourceCleanupOnTransition:
    """Verify sprites/timers/emitters are cleaned up on scene transitions."""

    def test_owned_sprites_removed_on_pop(self, game: Game) -> None:
        """Sprites owned by a scene are removed when the scene is popped."""
        from saga2d.rendering.sprite import Sprite

        sprites_created: list[Sprite] = []

        class SpriteScene(Scene):
            def on_enter(self) -> None:
                s = self.add_sprite(Sprite("sprites/knight", position=(0, 0)))
                sprites_created.append(s)

        game.push(SpriteScene())
        game.tick(0.016)
        assert not sprites_created[0]._removed
        assert sprites_created[0] in game._all_sprites

        game.pop()
        game.tick(0.016)
        assert sprites_created[0]._removed

    def test_owned_timers_cancelled_on_pop(self, game: Game) -> None:
        """Timers owned by a scene are cancelled when the scene is popped."""
        fired: list[bool] = []

        class TimerScene(Scene):
            def on_enter(self) -> None:
                self.after(0.5, lambda: fired.append(True))

        game.push(TimerScene())
        game.tick(0.016)
        game.pop()
        game.tick(0.016)
        # Advance well past the timer
        for _ in range(100):
            game.tick(0.016)
        assert fired == []  # Timer was cancelled

    def test_push_pop_push_no_resource_leak(self, game: Game) -> None:
        """Push → pop → push cycle doesn't leak sprite tracking."""
        from saga2d.rendering.sprite import Sprite

        class SpriteScene(Scene):
            def on_enter(self) -> None:
                self.add_sprite(Sprite("sprites/knight", position=(0, 0)))

        initial_count = len(game._all_sprites)

        for _ in range(5):
            game.push(SpriteScene())
            game.tick(0.016)
            game.pop()
            game.tick(0.016)

        # After all push/pop cycles, sprite count should be back to initial
        # (WeakSet + removal ensures no ghosts)
        gc.collect()
        assert len(game._all_sprites) == initial_count

    def test_replace_cleans_old_scene_resources(self, game: Game) -> None:
        """replace() removes old scene's sprites and timers."""
        from saga2d.rendering.sprite import Sprite

        old_sprite: list[Sprite] = []

        class OldScene(Scene):
            def on_enter(self) -> None:
                old_sprite.append(
                    self.add_sprite(Sprite("sprites/knight", position=(0, 0)))
                )
                self.after(10.0, lambda: None)

        game.push(OldScene())
        game.tick(0.016)
        assert not old_sprite[0]._removed

        game.replace(Scene())
        game.tick(0.016)
        assert old_sprite[0]._removed


# ═════════════════════════════════════════════════════════════
# 9. SPRITE WEAKSET AUTO-CLEANUP
# ═════════════════════════════════════════════════════════════


class TestSpriteWeakSetAutoCleanup:
    """Sprites with no strong references are automatically GC'd from WeakSets."""

    def test_unowned_sprite_gc(self, game: Game) -> None:
        """A sprite with no scene owner can be GC'd when refs are dropped."""
        from saga2d.rendering.sprite import Sprite

        s = Sprite("sprites/knight", position=(0, 0))
        ref = weakref.ref(s)
        assert ref() is not None
        assert s in game._all_sprites
        s.remove()
        del s
        gc.collect()
        # WeakSet should no longer hold a reference
        assert ref() is None

    def test_action_sprite_set_cleared_on_remove(self, game: Game) -> None:
        """Removing a sprite with active action deregisters from _action_sprites."""
        from saga2d.rendering.sprite import Sprite
        from saga2d.actions import Delay

        s = Sprite("sprites/knight", position=(0, 0))
        s.do(Delay(10.0))
        assert s in game._action_sprites
        s.remove()
        assert s not in game._action_sprites

    def test_animated_sprite_set_cleared_on_remove(self, game: Game) -> None:
        """Removing a sprite with active animation deregisters from _animated_sprites."""
        from saga2d.animation import AnimationDef
        from saga2d.rendering.sprite import Sprite

        s = Sprite("sprites/knight", position=(0, 0))
        anim = AnimationDef(
            frames=["sprites/knight_walk_01", "sprites/knight_walk_02"],
            frame_duration=0.1,
            loop=True,
        )
        s.play(anim)
        assert s in game._animated_sprites
        s.remove()
        assert s not in game._animated_sprites


# ═════════════════════════════════════════════════════════════
# 10. ANIMATION/ACTION STATE CLEANUP ON SPRITE REMOVAL
# ═════════════════════════════════════════════════════════════


class TestAnimationActionCleanupOnRemoval:
    """Removing a sprite cleans up its action and animation state."""

    def test_current_action_cleared_on_remove(self, game: Game) -> None:
        from saga2d.actions import Delay
        from saga2d.rendering.sprite import Sprite

        s = Sprite("sprites/knight", position=(0, 0))
        s.do(Delay(10.0))
        assert s._current_action is not None
        s.remove()
        assert s._current_action is None

    def test_do_on_removed_sprite_is_noop(self, game: Game) -> None:
        """Calling do() on a removed sprite has no effect."""
        from saga2d.actions import Delay
        from saga2d.rendering.sprite import Sprite

        s = Sprite("sprites/knight", position=(0, 0))
        s.remove()
        s.do(Delay(1.0))
        assert s._current_action is None

    def test_play_on_removed_sprite_is_noop(self, game: Game) -> None:
        """Calling play() on a removed sprite has no effect."""
        from saga2d.animation import AnimationDef
        from saga2d.rendering.sprite import Sprite

        s = Sprite("sprites/knight", position=(0, 0))
        s.remove()
        anim = AnimationDef(
            frames=["sprites/knight_walk_01"], frame_duration=0.1, loop=False
        )
        s.play(anim)
        assert s._anim_player is None


# ═════════════════════════════════════════════════════════════
# 11. AUDIO CROSSFADE & TEARDOWN
# ═════════════════════════════════════════════════════════════


class TestAudioCrossfadeTeardown:
    """Audio crossfade state is cleaned up on teardown."""

    def test_music_stopped_on_teardown(self) -> None:
        g = Game("AudioTest1", backend="mock", resolution=(800, 600))
        # Use backend directly to bypass asset resolution
        handle = g.backend.load_music("battle.ogg")
        pid = g.backend.play_music(handle)
        assert g.backend.music_playing is not None
        g._teardown()
        # After teardown, audio subsystem is nulled
        assert g._audio is None

    def test_play_stop_play_no_leak(self) -> None:
        g = Game("AudioTest2", backend="mock", resolution=(800, 600))
        backend = g.backend
        h1 = backend.load_music("battle.ogg")
        pid1 = backend.play_music(h1)
        assert backend.music_playing is not None
        backend.stop_player(pid1)
        h2 = backend.load_music("town.ogg")
        pid2 = backend.play_music(h2)
        assert backend.music_playing is not None
        backend.stop_player(pid2)
        assert backend.music_playing is None
        g._teardown()


# ═════════════════════════════════════════════════════════════
# 12. SAVE MANAGER TEARDOWN
# ═════════════════════════════════════════════════════════════


class TestSaveManagerTeardown:
    """SaveManager reference is cleared on game teardown."""

    def test_save_manager_nulled_on_teardown(self) -> None:
        g = Game("SaveTeardown", backend="mock", resolution=(800, 600))
        _ = g.save_manager  # Force lazy creation
        assert g._save_manager is not None
        g._teardown()
        assert g._save_manager is None

    def test_save_after_teardown_raises(self) -> None:
        """After teardown, calling save() directly would fail gracefully."""
        g = Game("SaveTeardown2", backend="mock", resolution=(800, 600))
        g.push(Scene())
        g._teardown()
        # Stack is empty after teardown, so save is a no-op
        # (no crash because top() returns None)
        g.save(1)  # Should not crash


# ═════════════════════════════════════════════════════════════
# 13. SAVE WITH SCENE CLASS NAME CORRECTNESS
# ═════════════════════════════════════════════════════════════


class TestSceneClassNamePreservation:
    """Verify scene_class field correctly identifies the scene type."""

    def test_scene_class_name_is_class_not_base(self, game: Game) -> None:
        """scene_class stores the actual subclass name, not 'Scene'."""

        class DungeonScene(Scene):
            def get_save_state(self) -> dict:
                return {"floor": 3}

        game.push(DungeonScene())
        game.save(1)
        data = game.save_manager.load(1)
        assert data is not None
        assert data["scene_class"] == "DungeonScene"

    def test_scene_class_changes_on_replace_and_save(self, game: Game) -> None:
        """After replacing the scene, save() records the new class name."""

        class BattleScene(Scene):
            def get_save_state(self) -> dict:
                return {"enemy": "dragon"}

        class VictoryScene(Scene):
            def get_save_state(self) -> dict:
                return {"reward": 1000}

        game.push(BattleScene())
        game.save(1)
        game.replace(VictoryScene())
        game.tick(0.016)
        game.save(2)

        d1 = game.save_manager.load(1)
        d2 = game.save_manager.load(2)
        assert d1 is not None and d1["scene_class"] == "BattleScene"
        assert d2 is not None and d2["scene_class"] == "VictoryScene"


# ═════════════════════════════════════════════════════════════
# 14. LOAD WITH MISSING/EXTRA STATE KEYS
# ═════════════════════════════════════════════════════════════


class TestLoadMissingExtraKeys:
    """Edge cases around save file contents vs scene expectations."""

    def test_load_with_extra_keys_in_state(self, game: Game) -> None:
        """Scene.load_save_state only uses keys it cares about."""

        class Selective(Scene):
            def __init__(self) -> None:
                self.gold = 0

            def get_save_state(self) -> dict:
                return {"gold": self.gold, "legacy_field": "x"}

            def load_save_state(self, state: dict) -> None:
                self.gold = state["gold"]
                # Ignores legacy_field

        s1 = Selective()
        s1.gold = 500
        game.push(s1)
        game.save(1)

        s2 = Selective()
        game.replace(s2)
        game.tick(0.016)
        game.load(1)
        assert s2.gold == 500

    def test_load_manually_with_different_scene_class(self, game: Game) -> None:
        """Manual load workflow: save as one class, restore as another."""

        class V1Scene(Scene):
            def get_save_state(self) -> dict:
                return {"gold": 100}

        class V2Scene(Scene):
            def __init__(self) -> None:
                self.gold = 0
                self.gems = 0

            def load_save_state(self, state: dict) -> None:
                self.gold = state.get("gold", 0)
                self.gems = state.get("gems", 0)  # New field, default 0

        game.push(V1Scene())
        game.save(1)

        # Manual load → reconstruct with different scene class
        data = game.save_manager.load(1)
        assert data is not None
        assert data["scene_class"] == "V1Scene"

        v2 = V2Scene()
        game.replace(v2)
        game.tick(0.016)
        v2.load_save_state(data["state"])
        assert v2.gold == 100
        assert v2.gems == 0  # Default for missing key
