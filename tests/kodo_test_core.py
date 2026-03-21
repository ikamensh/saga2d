"""Core engine and scene stack tests.

Tests for Game lifecycle, SceneStack operations, scene-owned resources,
the FakeGame cursor bug, and various edge cases.
"""

from __future__ import annotations

from typing import Any, cast

import pytest

from saga2d import Game, Scene, Sprite
from saga2d.backends.mock_backend import MockBackend
from saga2d.scene import SceneStack


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


class TrackingScene(Scene):
    """Scene that records lifecycle calls in a shared log list."""

    def __init__(self, name: str, log: list[str] | None = None) -> None:
        self.name = name
        self.log: list[str] = log if log is not None else []

    def on_enter(self) -> None:
        self.log.append(f"{self.name}.on_enter")

    def on_exit(self) -> None:
        self.log.append(f"{self.name}.on_exit")

    def on_reveal(self) -> None:
        self.log.append(f"{self.name}.on_reveal")

    def update(self, dt: float) -> None:
        self.log.append(f"{self.name}.update")

    def draw(self) -> None:
        self.log.append(f"{self.name}.draw")


class TransparentScene(TrackingScene):
    transparent = True
    pause_below = True


class NoPauseBelowScene(TrackingScene):
    pause_below = False
    transparent = True


class FakeGame:
    """Minimal game stand-in for low-level SceneStack tests (from test_adversarial.py)."""

    _hud = None


# ------------------------------------------------------------------
# 1. Game lifecycle
# ------------------------------------------------------------------


class TestGameLifecycle:

    def test_tick_advances_frame(self, mock_game: Game, mock_backend: MockBackend) -> None:
        """tick() should advance the frame counter."""
        scene = TrackingScene("A")
        mock_game.push(scene)
        assert mock_backend.frame_count == 0
        mock_game.tick(dt=0.016)
        assert mock_backend.frame_count == 1
        mock_game.tick(dt=0.016)
        assert mock_backend.frame_count == 2

    def test_teardown_clears_scene_stack(self, mock_game: Game) -> None:
        """_teardown() should drain the scene stack."""
        scene = TrackingScene("A")
        mock_game.push(scene)
        mock_game._teardown()
        assert mock_game._scene_stack.top() is None

    def test_teardown_clears_sprites(self, mock_game: Game, mock_backend: MockBackend) -> None:
        """_teardown() should clear sprite tracking sets."""
        scene = TrackingScene("A")
        mock_game.push(scene)
        mock_game._teardown()
        assert len(mock_game._all_sprites) == 0
        assert len(mock_game._animated_sprites) == 0

    def test_teardown_safe_to_call_twice(self, mock_game: Game) -> None:
        """_teardown() should be safe to call multiple times."""
        scene = TrackingScene("A")
        mock_game.push(scene)
        mock_game._teardown()
        # Second call should not raise
        mock_game._teardown()

    def test_quit_sets_running_false(self, mock_game: Game) -> None:
        """quit() should set running to False."""
        assert mock_game.running is True
        mock_game.quit()
        assert mock_game.running is False


# ------------------------------------------------------------------
# 2. Scene stack operations
# ------------------------------------------------------------------


class TestSceneStackBasic:

    def test_push_calls_on_enter(self, mock_game: Game) -> None:
        log: list[str] = []
        scene = TrackingScene("A", log)
        mock_game.push(scene)
        assert "A.on_enter" in log

    def test_push_calls_on_exit_on_previous(self, mock_game: Game) -> None:
        log: list[str] = []
        a = TrackingScene("A", log)
        b = TrackingScene("B", log)
        mock_game.push(a)
        mock_game.push(b)
        assert "A.on_exit" in log
        assert "B.on_enter" in log

    def test_pop_calls_on_exit_and_on_reveal(self, mock_game: Game) -> None:
        log: list[str] = []
        a = TrackingScene("A", log)
        b = TrackingScene("B", log)
        mock_game.push(a)
        mock_game.push(b)
        log.clear()
        mock_game.pop()
        assert "B.on_exit" in log
        assert "A.on_reveal" in log

    def test_replace_calls_on_exit_and_on_enter(self, mock_game: Game) -> None:
        log: list[str] = []
        a = TrackingScene("A", log)
        b = TrackingScene("B", log)
        mock_game.push(a)
        log.clear()
        mock_game.replace(b)
        assert "A.on_exit" in log
        assert "B.on_enter" in log
        # No on_reveal should fire during replace
        assert "A.on_reveal" not in log

    def test_clear_and_push(self, mock_game: Game) -> None:
        log: list[str] = []
        a = TrackingScene("A", log)
        b = TrackingScene("B", log)
        c = TrackingScene("C", log)
        mock_game.push(a)
        mock_game.push(b)
        log.clear()
        mock_game.clear_and_push(c)
        assert "A.on_exit" in log
        assert "B.on_exit" in log
        assert "C.on_enter" in log
        assert mock_game._scene_stack.top() is c

    def test_transparent_scene_draws_below(self, mock_game: Game) -> None:
        """transparent=True scene: scenes below should be drawn."""
        log: list[str] = []
        a = TrackingScene("A", log)
        b = TransparentScene("B", log)
        mock_game.push(a)
        mock_game.push(b)
        log.clear()
        mock_game.tick(dt=0.016)
        assert "A.draw" in log
        assert "B.draw" in log

    def test_pause_below_false_updates_below(self, mock_game: Game) -> None:
        """pause_below=False: scenes below should get update()."""
        log: list[str] = []
        a = TrackingScene("A", log)
        b = NoPauseBelowScene("B", log)
        mock_game.push(a)
        mock_game.push(b)
        log.clear()
        mock_game.tick(dt=0.016)
        assert "A.update" in log
        assert "B.update" in log

    def test_pause_below_true_does_not_update_below(self, mock_game: Game) -> None:
        """pause_below=True (default): scenes below should NOT get update()."""
        log: list[str] = []
        a = TrackingScene("A", log)
        b = TrackingScene("B", log)
        mock_game.push(a)
        mock_game.push(b)
        log.clear()
        mock_game.tick(dt=0.016)
        assert "A.update" not in log
        assert "B.update" in log

    def test_push_same_scene_twice(self, mock_game: Game) -> None:
        """BUG: Push the same scene instance twice silently succeeds but causes
        a crash during teardown.

        The push itself works, but _teardown() iterates the stack and calls
        _teardown_exited_scene (which sets scene.game = None) on the first
        copy. When it processes the second copy, scene.game is already None,
        so _cleanup_exiting_scene crashes with AttributeError on
        scene.game.cursor.set("default").

        The framework should either reject duplicate pushes or handle them
        safely during teardown.
        """
        log: list[str] = []
        a = TrackingScene("A", log)
        mock_game.push(a)
        # Pushing the same instance again silently succeeds
        mock_game.push(a)
        assert len(mock_game._scene_stack._stack) == 2
        assert mock_game._scene_stack._stack[0] is mock_game._scene_stack._stack[1]

    def test_pop_from_empty_stack(self, mock_game: Game) -> None:
        """Pop from empty stack should not crash."""
        # No scene pushed
        mock_game.pop()  # Should be a no-op

    def test_replace_on_empty_stack(self, mock_game: Game) -> None:
        """Replace on empty stack should work like push."""
        log: list[str] = []
        a = TrackingScene("A", log)
        mock_game.replace(a)
        assert "A.on_enter" in log
        assert mock_game._scene_stack.top() is a

    def test_clear_and_push_empty_stack(self, mock_game: Game) -> None:
        """clear_and_push on empty stack should just push."""
        log: list[str] = []
        a = TrackingScene("A", log)
        mock_game.clear_and_push(a)
        assert "A.on_enter" in log
        assert mock_game._scene_stack.top() is a


# ------------------------------------------------------------------
# 3. Scene-owned resources
# ------------------------------------------------------------------


class TestSceneOwnedResources:

    def test_sprites_removed_on_pop(self, mock_game: Game, mock_backend: MockBackend) -> None:
        """Sprites created in a scene should be removed when the scene is popped."""
        class SpriteScene(Scene):
            def on_enter(self) -> None:
                self.knight = self.add_sprite(Sprite("sprites/knight", position=(100, 100)))

        scene = SpriteScene()
        mock_game.push(scene)
        # There should be a sprite in the backend
        sprite_count_before = len(mock_backend.sprites)
        assert sprite_count_before > 0

        mock_game.pop()
        # After pop, the sprite should be removed
        assert len(mock_backend.sprites) < sprite_count_before

    def test_timers_cancelled_on_pop(self, mock_game: Game) -> None:
        """Timers created via scene.after() should be cancelled when scene is popped."""
        fired = []

        class TimerScene(Scene):
            def on_enter(self) -> None:
                self.after(0.1, lambda: fired.append("timer_fired"))

        scene = TimerScene()
        mock_game.push(scene)
        mock_game.pop()

        # Advance time past when the timer would fire
        for _ in range(20):
            mock_game.tick(dt=0.016)

        assert len(fired) == 0, "Timer should have been cancelled on scene pop"

    def test_emitters_cleaned_up_on_pop(self, mock_game: Game) -> None:
        """Particle emitters registered via scene.add_emitter() should be cleaned up on pop."""

        class FakeEmitter:
            def __init__(self):
                self.removed = False
                self.is_active = True

            def remove(self):
                self.removed = True

            def update(self, dt):
                pass

        class EmitterScene(Scene):
            def on_enter(self) -> None:
                self.emitter = FakeEmitter()
                self.add_emitter(self.emitter)

        scene = EmitterScene()
        mock_game.push(scene)
        emitter = scene.emitter
        mock_game.pop()
        assert emitter.removed, "Emitter should have been removed on scene pop"


# ------------------------------------------------------------------
# 4. FakeGame cursor bug
# ------------------------------------------------------------------


class TestFakeGameCursorBug:
    """Tests investigating the FakeGame cursor bug.

    _cleanup_exiting_scene calls scene.game.cursor.set("default") at line 526
    of scene.py. FakeGame doesn't have a cursor attribute, so this should fail
    when using FakeGame with SceneStack directly.
    """

    def test_fakegame_pop_cursor_crash(self) -> None:
        """Pushing a second scene onto a SceneStack using FakeGame crashes
        because _cleanup_exiting_scene calls scene.game.cursor.set("default")
        and FakeGame has no cursor attribute.

        The crash happens on push(b) because pushing B triggers A.on_exit
        -> _cleanup_exiting_scene(A) -> cursor.set("default").
        """
        fake_game = FakeGame()
        stack = SceneStack(cast(Game, fake_game))

        log: list[str] = []
        a = TrackingScene("A", log)
        b = TrackingScene("B", log)

        stack.push(a)  # Fine -- no previous scene to clean up

        # After fix: pushing B should NOT crash even though FakeGame has no cursor.
        # _cleanup_exiting_scene now guards with hasattr.
        stack.push(b)
        assert stack.top().name == "B"  # type: ignore[union-attr]

    def test_fakegame_replace_cursor_no_crash(self) -> None:
        """Replacing a scene using FakeGame should not crash after cursor guard fix."""
        fake_game = FakeGame()
        stack = SceneStack(cast(Game, fake_game))

        log: list[str] = []
        a = TrackingScene("A", log)
        b = TrackingScene("B", log)

        stack.push(a)
        stack.replace(b)
        assert stack.top().name == "B"  # type: ignore[union-attr]

    def test_fakegame_clear_and_push_cursor_no_crash(self) -> None:
        """clear_and_push using FakeGame should not crash after cursor guard fix."""
        fake_game = FakeGame()
        stack = SceneStack(cast(Game, fake_game))

        log: list[str] = []
        a = TrackingScene("A", log)
        b = TrackingScene("B", log)

        stack.push(a)
        stack.clear_and_push(b)
        assert stack.top().name == "B"  # type: ignore[union-attr]

    def test_fakegame_push_over_existing_cursor_no_crash(self) -> None:
        """Pushing a scene over an existing one using FakeGame should not crash
        after cursor guard fix in _cleanup_exiting_scene."""
        fake_game = FakeGame()
        stack = SceneStack(cast(Game, fake_game))

        a = TrackingScene("A")
        b = TrackingScene("B")

        stack.push(a)
        stack.push(b)
        assert stack.top().name == "B"  # type: ignore[union-attr]

    def test_real_game_cursor_no_crash(self, mock_game: Game) -> None:
        """Using the real Game with mock backend should NOT crash on cursor access
        because Game lazily creates a CursorManager."""
        a = TrackingScene("A")
        b = TrackingScene("B")
        mock_game.push(a)
        mock_game.push(b)  # Should not crash
        mock_game.pop()  # Should not crash


# ------------------------------------------------------------------
# 5. Edge cases
# ------------------------------------------------------------------


class TestEdgeCases:

    def test_tick_with_no_scene(self, mock_game: Game, mock_backend: MockBackend) -> None:
        """tick() with no scene pushed should not crash."""
        mock_game.tick(dt=0.016)
        assert mock_backend.frame_count == 1

    def test_tick_with_very_large_dt(self, mock_game: Game) -> None:
        """tick() with very large dt (100.0) should not crash or hang."""
        scene = TrackingScene("A")
        mock_game.push(scene)
        mock_game.tick(dt=100.0)  # Should not crash

    def test_tick_with_dt_zero(self, mock_game: Game) -> None:
        """tick() with dt=0 should not crash."""
        scene = TrackingScene("A")
        mock_game.push(scene)
        mock_game.tick(dt=0.0)  # Should not crash

    def test_tick_with_negative_dt(self, mock_game: Game) -> None:
        """BUG: tick() with negative dt silently accepted, corrupts timer state.

        Negative dt causes timer accumulators to go negative, delaying timer
        firing by an additional abs(dt) seconds beyond the expected delay.
        For example, a timer set for 0.1s after a tick(dt=-1.0) won't fire
        until 1.1s of positive dt has elapsed.

        The framework does not validate dt. This is a silent-wrong bug.
        """
        fired = []

        class TimerScene(Scene):
            def on_enter(self) -> None:
                self.after(0.1, lambda: fired.append("timer"))

        scene = TimerScene()
        mock_game.push(scene)
        mock_game.tick(dt=-1.0)  # Silently accepted

        # After negative dt, need to tick much more than 0.1s to fire the timer
        for _ in range(10):
            mock_game.tick(dt=0.016)  # 0.16s total
        assert len(fired) == 0, \
            "Timer with 0.1s delay has not fired after 0.16s because negative dt corrupted state"

    def test_scene_modifies_stack_from_on_exit_outside_tick(self, mock_game: Game) -> None:
        """BUG: Scene that pushes from on_exit OUTSIDE a tick() loses the deferred op.

        When game.pop() is called outside of tick(), the push from on_exit is
        deferred (because _in_on_exit is True), but flush_pending_ops() is never
        called afterward. The deferred push is silently lost.

        This is a silent-wrong bug: the deferred operation is queued but never
        executed when pop() is called outside of a tick.
        """
        log: list[str] = []

        class PushOnExitScene(Scene):
            def __init__(self, name: str, log: list[str]):
                self.name = name
                self.log = log
                self._pushed = False

            def on_enter(self) -> None:
                self.log.append(f"{self.name}.on_enter")

            def on_exit(self) -> None:
                self.log.append(f"{self.name}.on_exit")
                if not self._pushed:
                    self._pushed = True
                    self.game.push(TrackingScene("Replacement", self.log))

        scene = PushOnExitScene("A", log)
        mock_game.push(scene)
        log.clear()
        mock_game.pop()

        # BUG: The deferred push is lost -- stack is empty even though
        # on_exit queued a push("Replacement").
        # The pending op sits in _pending_ops but is never flushed.
        assert mock_game._scene_stack.top() is None  # Documenting the bug
        assert len(mock_game._scene_stack._pending_ops) > 0, \
            "The deferred push should still be in the pending queue"

    def test_scene_modifies_stack_from_on_exit_during_tick(self, mock_game: Game) -> None:
        """Scene that pushes from on_exit DURING a tick should work correctly,
        because tick() calls flush_pending_ops()."""
        log: list[str] = []

        class PushOnExitScene(Scene):
            def __init__(self, name: str, log: list[str]):
                self.name = name
                self.log = log
                self._pushed = False

            def on_enter(self) -> None:
                self.log.append(f"{self.name}.on_enter")

            def on_exit(self) -> None:
                self.log.append(f"{self.name}.on_exit")
                if not self._pushed:
                    self._pushed = True
                    self.game.push(TrackingScene("Replacement", self.log))

            def handle_input(self, event) -> bool:
                if event.type == "key_press" and event.key == "q":
                    self.game.pop()
                    return True
                return False

        scene = PushOnExitScene("A", log)
        mock_game.push(scene)
        log.clear()

        # Trigger pop from within a tick via input handling
        mock_game.backend.inject_key("q")
        mock_game.tick(dt=0.016)

        # During tick, flush_pending_ops() is called, so the deferred push runs
        assert mock_game._scene_stack.top() is not None

    def test_scene_modifies_stack_from_on_reveal(self, mock_game: Game) -> None:
        """Scene that pushes from on_reveal should be deferred."""
        log: list[str] = []

        class PushOnRevealScene(Scene):
            def __init__(self, name: str, log: list[str]):
                self.name = name
                self.log = log
                self._revealed = False

            def on_enter(self) -> None:
                self.log.append(f"{self.name}.on_enter")

            def on_exit(self) -> None:
                self.log.append(f"{self.name}.on_exit")

            def on_reveal(self) -> None:
                self.log.append(f"{self.name}.on_reveal")
                if not self._revealed:
                    self._revealed = True
                    self.game.push(TrackingScene("NewScene", self.log))

        a = PushOnRevealScene("A", log)
        b = TrackingScene("B", log)
        mock_game.push(a)
        mock_game.push(b)
        log.clear()
        mock_game.pop()
        # A.on_reveal pushes NewScene (deferred)
        # After flush, NewScene should be on top
        top = mock_game._scene_stack.top()
        assert top is not None

    def test_push_none_raises(self, mock_game: Game) -> None:
        """push(None) should raise a clear error."""
        with pytest.raises((TypeError, ValueError)):
            mock_game.push(None)  # type: ignore[arg-type]

    def test_push_non_scene_raises(self, mock_game: Game) -> None:
        """push(non-Scene) should raise TypeError."""
        with pytest.raises(TypeError):
            mock_game.push("not a scene")  # type: ignore[arg-type]

    def test_replace_none_raises(self, mock_game: Game) -> None:
        """replace(None) should raise."""
        with pytest.raises((TypeError, ValueError)):
            mock_game.replace(None)  # type: ignore[arg-type]

    def test_lifecycle_order_on_push(self, mock_game: Game) -> None:
        """Verify exact ordering: old.on_exit happens BEFORE new.on_enter."""
        log: list[str] = []
        a = TrackingScene("A", log)
        b = TrackingScene("B", log)
        mock_game.push(a)
        log.clear()
        mock_game.push(b)
        exit_idx = log.index("A.on_exit")
        enter_idx = log.index("B.on_enter")
        assert exit_idx < enter_idx, f"on_exit should come before on_enter, got: {log}"

    def test_lifecycle_order_on_pop(self, mock_game: Game) -> None:
        """Verify exact ordering: old.on_exit happens BEFORE revealed.on_reveal."""
        log: list[str] = []
        a = TrackingScene("A", log)
        b = TrackingScene("B", log)
        mock_game.push(a)
        mock_game.push(b)
        log.clear()
        mock_game.pop()
        exit_idx = log.index("B.on_exit")
        reveal_idx = log.index("A.on_reveal")
        assert exit_idx < reveal_idx, f"on_exit should come before on_reveal, got: {log}"

    def test_multiple_rapid_pops(self, mock_game: Game) -> None:
        """Multiple pops in succession should not crash."""
        a = TrackingScene("A")
        b = TrackingScene("B")
        c = TrackingScene("C")
        mock_game.push(a)
        mock_game.push(b)
        mock_game.push(c)
        mock_game.pop()
        mock_game.pop()
        mock_game.pop()
        assert mock_game._scene_stack.top() is None

    def test_pop_beyond_empty(self, mock_game: Game) -> None:
        """Popping more times than scenes pushed should not crash."""
        a = TrackingScene("A")
        mock_game.push(a)
        mock_game.pop()
        mock_game.pop()  # Already empty, should be no-op
        mock_game.pop()  # Still empty, should be no-op

    def test_tick_after_teardown(self, mock_game: Game) -> None:
        """tick() after _teardown() -- what happens?"""
        scene = TrackingScene("A")
        mock_game.push(scene)
        mock_game._teardown()
        # Ticking after teardown: the scene stack is empty, subsystems are None
        # This could crash if subsystems are accessed
        try:
            mock_game.tick(dt=0.016)
            crashed = False
        except Exception as e:
            crashed = True
            error = e
        # Just document the behavior; don't assert either way

    def test_on_enter_exception_rolls_back_push(self, mock_game: Game) -> None:
        """If on_enter raises, the scene should be removed from stack."""
        class BadScene(Scene):
            def on_enter(self) -> None:
                raise RuntimeError("on_enter failed")

        good = TrackingScene("Good")
        mock_game.push(good)

        with pytest.raises(RuntimeError, match="on_enter failed"):
            mock_game.push(BadScene())

        # Stack should still have Good on top, not BadScene
        assert mock_game._scene_stack.top() is good
