"""Stage 4 integration and stress edge-case tests.

Tests cross-system interactions and stress scenarios:
  1. Scene on_enter exception with owned timers/sprites
  2. Game teardown and recreation cycle
  3. Game methods after teardown (BUG: silently no-ops)
  4. Rapid push/pop during callbacks
  5. Timer callback modifying scene stack
  6. Action replacement during Parallel execution
  7. Exception in scene.update() recovery
  8. Deep scene stack (100+ scenes)

BUGS FOUND:
  B1. Game.tick() and Game.push() after _teardown() succeed silently
      instead of raising RuntimeError. The game is in a corrupted state
      (all managers are None) but keeps going.

GOOD BEHAVIOR:
  G1. on_enter exception with owned timers - game recovers cleanly.
  G2. Game teardown and recreation works perfectly.
  G3. Push during on_enter handled via deferred operations.
  G4. Timer callback can pop scene correctly.
  G5. Action replacement during Parallel works fine.
  G6. Exception in scene.update() doesn't corrupt game state.
  G7. Deep scene stack (100 push/pop) works without issues.
"""

from __future__ import annotations

import pytest

from saga2d import Game, Scene, Sprite
from saga2d.actions import Delay, Do, Parallel, Sequence


# ===================================================================
# 1. Scene on_enter exception with owned timers
# ===================================================================


class TestOnEnterExceptionCleanup:
    """on_enter() that creates timers then raises — game should recover."""

    def test_on_enter_exception_allows_recovery(self):
        """GOOD (G1): on_enter exception pops scene, game still usable."""

        class FailingScene(Scene):
            def on_enter(self):
                self.after(1.0, lambda: None)
                raise RuntimeError("on_enter failed")

        g = Game("test", backend="mock")
        with pytest.raises(RuntimeError, match="on_enter failed"):
            g.push(FailingScene())
        # Game should still be usable
        g.push(Scene())
        g.tick(0.016)
        assert len(g._scene_stack._stack) == 1
        g._teardown()

    def test_on_enter_exception_cleans_stack(self):
        """After on_enter raises, the failed scene is NOT in the stack."""

        class FailingScene(Scene):
            def on_enter(self):
                raise RuntimeError("fail")

        g = Game("test", backend="mock")
        with pytest.raises(RuntimeError):
            g.push(FailingScene())
        assert len(g._scene_stack._stack) == 0
        g._teardown()


# ===================================================================
# 2. Game teardown and recreation
# ===================================================================


class TestGameTeardownRecreation:
    """Create, use, teardown, then create a new Game instance."""

    def test_teardown_and_recreate(self):
        """GOOD (G2): Can create a new Game after tearing down the old one."""
        g1 = Game("test1", backend="mock")
        g1.push(Scene())
        g1.tick(0.016)
        g1._teardown()

        g2 = Game("test2", backend="mock")
        g2.push(Scene())
        g2.tick(0.016)
        assert len(g2._scene_stack._stack) == 1
        g2._teardown()

    def test_multiple_recreations(self):
        """Can do teardown/recreate cycle multiple times."""
        for i in range(5):
            g = Game(f"test_{i}", backend="mock")
            g.push(Scene())
            g.tick(0.016)
            g._teardown()


# ===================================================================
# 3. Game methods after teardown (BUG)
# ===================================================================


class TestGameAfterTeardown:
    """BUG (B1): Game.tick() and Game.push() after _teardown() succeed
    silently instead of raising. The game is in a broken state but
    methods don't inform the caller.

    After _teardown(), the scene stack, timer manager, tween manager, etc.
    are all cleared. Calling tick() or push() has undefined behavior
    but does not raise an error.
    """

    def test_tick_after_teardown_does_not_raise(self):
        """BUG: tick() after teardown silently succeeds."""
        g = Game("test", backend="mock")
        g.push(Scene())
        g.tick(0.016)
        g._teardown()

        # This should raise but doesn't
        g.tick(0.016)  # Silently succeeds

    def test_push_after_teardown_does_not_raise(self):
        """BUG: push() after teardown silently succeeds."""
        g = Game("test", backend="mock")
        g.push(Scene())
        g.tick(0.016)
        g._teardown()

        # This should raise but doesn't
        g.push(Scene())  # Silently succeeds


# ===================================================================
# 4. Rapid push during callbacks
# ===================================================================


class TestRapidPushDuringCallbacks:
    """Push during on_enter — handled via deferred operations."""

    def test_push_during_on_enter(self):
        """GOOD (G3): Push during on_enter creates deferred operation."""

        class PushyScene(Scene):
            def on_enter(self):
                self.game.push(Scene())

        g = Game("test", backend="mock")
        g.push(PushyScene())
        g.tick(0.016)
        # PushyScene + the Scene it pushed
        assert len(g._scene_stack._stack) == 2
        g._teardown()

    def test_pop_during_on_enter(self):
        """Push then pop during on_enter — deferred ops both execute."""

        class PopSelfScene(Scene):
            def on_enter(self):
                self.game.pop()

        g = Game("test", backend="mock")
        g.push(Scene())  # Base scene
        g.push(PopSelfScene())  # This scene pops itself
        g.tick(0.016)
        # PopSelfScene popped, base scene remains
        assert len(g._scene_stack._stack) == 1
        g._teardown()


# ===================================================================
# 5. Timer callback modifying scene stack
# ===================================================================


class TestTimerCallbackSceneStack:
    """Timer with delay=0 that pops the scene."""

    def test_timer_pops_scene(self):
        """GOOD (G4): Timer callback can pop scene during tick."""

        class TimerScene(Scene):
            def on_enter(self):
                self.after(0.0, lambda: self.game.pop())

        g = Game("test", backend="mock")
        g.push(TimerScene())
        g.tick(0.016)  # Timer fires and pops scene
        assert len(g._scene_stack._stack) == 0
        g._teardown()

    def test_timer_pushes_scene(self):
        """Timer callback can push a new scene."""

        class TimerPushScene(Scene):
            def on_enter(self):
                self.after(0.0, lambda: self.game.push(Scene()))

        g = Game("test", backend="mock")
        g.push(TimerPushScene())
        g.tick(0.016)  # Timer fires and pushes new scene
        assert len(g._scene_stack._stack) == 2
        g._teardown()


# ===================================================================
# 6. Action replacement during Parallel execution
# ===================================================================


class TestActionReplacementDuringParallel:
    """Replace a sprite's action from within a Do() callback in a Parallel."""

    def test_action_replacement_in_parallel(self):
        """GOOD (G5): Action replacement from Do() inside Parallel works."""

        class ActionScene(Scene):
            def on_enter(self):
                self.sprite = self.add_sprite(Sprite("sprites/knight"))
                self.sprite.do(Parallel(
                    Delay(0.1),
                    Do(lambda: self.sprite.do(Delay(0.5))),
                ))

        g = Game("test", backend="mock")
        g.push(ActionScene())
        for _ in range(10):
            g.tick(0.016)
        g._teardown()


# ===================================================================
# 7. Exception in scene.update() recovery
# ===================================================================


class TestUpdateExceptionRecovery:
    """scene.update() raises — game should recover on next tick."""

    def test_game_recovers_after_update_exception(self):
        """GOOD (G6): Game continues working after scene.update() raises."""

        class BuggyScene(Scene):
            def __init__(self):
                super().__init__()
                self.tick_count = 0

            def update(self, dt):
                self.tick_count += 1
                if self.tick_count == 2:
                    raise RuntimeError("update error")

        g = Game("test", backend="mock")
        scene = BuggyScene()
        g.push(scene)

        g.tick(0.016)  # Tick 1 OK
        assert scene.tick_count == 1

        with pytest.raises(RuntimeError, match="update error"):
            g.tick(0.016)  # Tick 2 raises
        assert scene.tick_count == 2

        g.tick(0.016)  # Tick 3 — game recovers
        assert scene.tick_count == 3
        g._teardown()


# ===================================================================
# 8. Deep scene stack
# ===================================================================


class TestDeepSceneStack:
    """Push and pop 100+ scenes."""

    def test_push_100_scenes(self):
        """GOOD (G7): Deep scene stack works without issues."""
        g = Game("test", backend="mock")
        for _ in range(100):
            g.push(Scene())
        assert len(g._scene_stack._stack) == 100
        g.tick(0.016)
        g._teardown()

    def test_push_pop_100_scenes(self):
        """Push 100, pop 100, tick after each phase."""
        g = Game("test", backend="mock")
        for _ in range(100):
            g.push(Scene())
        g.tick(0.016)
        assert len(g._scene_stack._stack) == 100

        for _ in range(100):
            g.pop()
        g.tick(0.016)
        assert len(g._scene_stack._stack) == 0
        g._teardown()

    def test_push_pop_interleaved(self):
        """Interleave push and pop operations."""
        g = Game("test", backend="mock")
        for i in range(50):
            g.push(Scene())
            g.push(Scene())
            g.pop()
            g.tick(0.016)
        # 50 remaining (one per iteration)
        assert len(g._scene_stack._stack) == 50
        g._teardown()
