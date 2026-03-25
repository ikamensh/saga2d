"""Stage 4 regression tests — integration/lifecycle edge cases.

F57: flush_pending_ops exception clears stale ops from queue
F58: direct scene ops auto-flush deferred ops from on_exit/on_reveal

Also validates correct behavior (no bug found) in:
- Scene stack transitions during active actions/timers
- Exceptions in scene hooks (on_enter, on_exit, on_reveal, update, draw)
- Repeated Game initialization/teardown
- Deferred operations safety/limits
"""
from __future__ import annotations

import pytest
from saga2d.actions import Delay, Do, Sequence
from saga2d.game import Game
from saga2d.rendering.sprite import Sprite
from saga2d.scene import Scene, SceneStack


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class TrackingScene(Scene):
    """Scene that logs lifecycle events."""

    def __init__(self, name: str = ""):
        super().__init__()
        self.name = name
        self.log: list[str] = []

    def on_enter(self) -> None:
        self.log.append(f"{self.name}.on_enter")

    def on_exit(self) -> None:
        self.log.append(f"{self.name}.on_exit")

    def on_reveal(self) -> None:
        self.log.append(f"{self.name}.on_reveal")


# ---------------------------------------------------------------------------
# F57 — flush_pending_ops exception clears queue
# ---------------------------------------------------------------------------


class TestF57FlushExceptionClearsQueue:
    """F57: When flush_pending_ops raises, remaining deferred ops are cleared."""

    def test_exception_in_flush_clears_pending_ops(self, mock_game: Game) -> None:
        """Deferred ops are discarded when flush raises, preventing stale op leaks."""

        class BadExitScene(Scene):
            def on_exit(self) -> None:
                raise RuntimeError("on_exit boom")

        class GoodScene(Scene):
            pass

        class Trigger(Scene):
            done = False

            def update(self, dt: float) -> None:
                if not self.done:
                    self.done = True
                    mock_game.push(GoodScene())  # deferred op 1
                    mock_game.push(GoodScene())  # deferred op 2

            def on_exit(self) -> None:
                raise RuntimeError("trigger on_exit boom")

        mock_game.push(Trigger())
        with pytest.raises(RuntimeError, match="trigger on_exit boom"):
            mock_game.tick(0.016)

        # F57: pending_ops should be cleared even after exception
        assert len(mock_game._scene_stack._pending_ops) == 0, \
            "pending_ops should be cleared after flush exception"

    def test_game_usable_after_flush_exception(self, mock_game: Game) -> None:
        """Game is usable after a flush exception (no stale state)."""

        class BadOnEnter(Scene):
            def on_enter(self) -> None:
                raise RuntimeError("on_enter boom")

        class Trigger(Scene):
            done = False

            def update(self, dt: float) -> None:
                if not self.done:
                    self.done = True
                    mock_game.push(BadOnEnter())  # deferred
                    mock_game.push(Scene())       # second deferred op

        mock_game.push(Trigger())
        with pytest.raises(RuntimeError, match="on_enter boom"):
            mock_game.tick(0.016)

        # F57: pending_ops should be cleared after the exception
        assert len(mock_game._scene_stack._pending_ops) == 0
        # Game should still be functional with Trigger as top
        assert isinstance(mock_game._scene_stack.top(), Trigger)
        mock_game.tick(0.016)  # Should not crash


# ---------------------------------------------------------------------------
# F58 — direct scene ops auto-flush deferred ops
# ---------------------------------------------------------------------------


class TestF58DirectOpsAutoFlush:
    """F58: Direct scene ops (outside tick) auto-flush deferred ops from on_exit/on_reveal."""

    def test_pop_flushes_on_exit_push(self, mock_game: Game) -> None:
        """Direct pop: push from on_exit is flushed immediately."""
        log = []

        class Replacement(Scene):
            def on_enter(self) -> None:
                log.append("replacement_enter")

        class ExitPusher(Scene):
            def on_exit(self) -> None:
                self.game.push(Replacement())

        mock_game.push(Scene())  # base
        mock_game.push(ExitPusher())
        mock_game.pop()

        assert "replacement_enter" in log
        assert len(mock_game._scene_stack._pending_ops) == 0
        assert mock_game._scene_stack.top().__class__.__name__ == "Replacement"

    def test_push_flushes_on_exit_push(self, mock_game: Game) -> None:
        """Direct push: old scene's on_exit deferred push is flushed."""
        log = []

        class Extra(Scene):
            def on_enter(self) -> None:
                log.append("extra_enter")

        class ExitPusher(Scene):
            def on_exit(self) -> None:
                self.game.push(Extra())

        class NewTop(Scene):
            pass

        mock_game.push(ExitPusher())
        mock_game.push(NewTop())

        assert "extra_enter" in log
        assert len(mock_game._scene_stack._pending_ops) == 0

    def test_replace_flushes_on_exit_push(self, mock_game: Game) -> None:
        """Direct replace: old scene's on_exit deferred push is flushed."""
        log = []

        class Extra(Scene):
            def on_enter(self) -> None:
                log.append("extra_enter")

        class ExitPusher(Scene):
            def on_exit(self) -> None:
                self.game.push(Extra())

        class Replacement(Scene):
            pass

        mock_game.push(ExitPusher())
        mock_game.replace(Replacement())

        assert "extra_enter" in log
        assert len(mock_game._scene_stack._pending_ops) == 0

    def test_clear_and_push_flushes_on_exit_push(self, mock_game: Game) -> None:
        """Direct clear_and_push: on_exit deferred push is flushed."""
        log = []

        class Extra(Scene):
            def on_enter(self) -> None:
                log.append("extra_enter")

        class ExitPusher(Scene):
            def on_exit(self) -> None:
                self.game.push(Extra())

        class Fresh(Scene):
            pass

        mock_game.push(ExitPusher())
        mock_game.clear_and_push(Fresh())

        assert "extra_enter" in log
        assert len(mock_game._scene_stack._pending_ops) == 0

    def test_pop_flushes_on_reveal_push(self, mock_game: Game) -> None:
        """Direct pop: push from on_reveal is flushed immediately."""
        log = []

        class Extra(Scene):
            def on_enter(self) -> None:
                log.append("extra_enter")

        class RevealPusher(Scene):
            def on_reveal(self) -> None:
                self.game.push(Extra())

        class Top(Scene):
            pass

        mock_game.push(RevealPusher())
        mock_game.push(Top())
        mock_game.pop()

        assert "extra_enter" in log
        assert len(mock_game._scene_stack._pending_ops) == 0

    def test_on_exit_pop_during_direct_push(self, mock_game: Game) -> None:
        """Direct push: on_exit pops the CURRENT scene (deferred, then flushed)."""
        log = []

        class ExitPopper(Scene):
            def on_exit(self) -> None:
                log.append("exit_pop")
                self.game.pop()  # deferred — pops ExitPopper permanently

        class NewTop(Scene):
            pass

        mock_game.push(ExitPopper())
        mock_game.push(NewTop())

        assert "exit_pop" in log
        # The pop from on_exit is processed; stack should be [NewTop] only
        # (ExitPopper was pushed-over, then the deferred pop removed it)
        assert len(mock_game._scene_stack._pending_ops) == 0


# ---------------------------------------------------------------------------
# Deferred operations safety/limits
# ---------------------------------------------------------------------------


class TestDeferredOpsSafety:
    """Validate deferred operations safety including the 1000-iteration cap."""

    def test_deferred_ops_cap_logs_warning(self, mock_game: Game) -> None:
        """1000-iteration cap prevents infinite loops; excess ops are discarded."""
        count = [0]

        class Inf(Scene):
            def on_enter(self) -> None:
                count[0] += 1
                if count[0] < 2000:
                    mock_game.push(Inf())

        class Trigger(Scene):
            done = False

            def update(self, dt: float) -> None:
                if not self.done:
                    self.done = True
                    mock_game.push(Inf())

        mock_game.push(Trigger())
        mock_game.tick(0.016)

        assert count[0] == 1000, f"should hit cap at 1000, got {count[0]}"
        # After cap, excess ops are discarded
        assert len(mock_game._scene_stack._pending_ops) == 0

    def test_deferred_push_from_update(self, mock_game: Game) -> None:
        """Push from update is deferred and processed after update phase."""

        class S2(Scene):
            pass

        class S1(Scene):
            pushed = False

            def update(self, dt: float) -> None:
                if not self.pushed:
                    self.pushed = True
                    mock_game.push(S2())

        mock_game.push(S1())
        mock_game.tick(0.016)
        assert isinstance(mock_game._scene_stack.top(), S2)

    def test_deferred_pop_from_update(self, mock_game: Game) -> None:
        """Pop from update is deferred and processed after update phase."""

        class S2(Scene):
            def update(self, dt: float) -> None:
                mock_game.pop()

        class S1(Scene):
            pass

        mock_game.push(S1())
        mock_game.push(S2())
        mock_game.tick(0.016)
        assert isinstance(mock_game._scene_stack.top(), S1)

    def test_deferred_ops_fifo_order(self, mock_game: Game) -> None:
        """Multiple deferred ops execute in FIFO order."""
        log = []

        class S3(Scene):
            def on_enter(self) -> None:
                log.append("s3")

        class S2(Scene):
            def on_enter(self) -> None:
                log.append("s2")

        class S1(Scene):
            def update(self, dt: float) -> None:
                mock_game.push(S2())
                mock_game.push(S3())

        mock_game.push(S1())
        mock_game.tick(0.016)
        assert log == ["s2", "s3"]

    def test_nested_deferred_ops(self, mock_game: Game) -> None:
        """Deferred ops triggered from on_enter of deferred-pushed scene."""
        log = []

        class S3(Scene):
            def on_enter(self) -> None:
                log.append("s3")

        class S2(Scene):
            def on_enter(self) -> None:
                log.append("s2")
                mock_game.push(S3())

        class S1(Scene):
            def update(self, dt: float) -> None:
                mock_game.push(S2())

        mock_game.push(S1())
        mock_game.tick(0.016)
        assert "s2" in log and "s3" in log
        assert isinstance(mock_game._scene_stack.top(), S3)


# ---------------------------------------------------------------------------
# Scene stack transitions during active actions/timers
# ---------------------------------------------------------------------------


class TestSceneTransitionsWithActionsTimers:
    """Verify correct behavior during scene transitions with active actions/timers."""

    def test_action_stopped_on_scene_pop(self, mock_game: Game) -> None:
        """Owned sprite's action is stopped when scene is popped."""
        log = []

        class S1(Scene):
            def on_enter(self) -> None:
                self.sp = self.add_sprite(
                    Sprite("sprites/knight", position=(100, 100))
                )
                self.sp.do(Sequence(
                    Delay(1.0),
                    Do(lambda: log.append("done")),
                ))

        s1 = S1()
        mock_game.push(s1)
        mock_game.tick(0.1)
        assert s1.sp._current_action is not None

        mock_game.pop()
        for _ in range(20):
            mock_game.tick(0.1)

        assert s1.sp.is_removed
        assert "done" not in log

    def test_timer_cancelled_on_scene_pop(self, mock_game: Game) -> None:
        """Scene-owned timer is cancelled when scene is popped."""
        log = []

        class S1(Scene):
            def on_enter(self) -> None:
                self.after(0.5, lambda: log.append("fired"))

        mock_game.push(S1())
        mock_game.tick(0.1)
        mock_game.pop()
        for _ in range(20):
            mock_game.tick(0.1)

        assert log == []

    def test_timer_survives_push_over(self, mock_game: Game) -> None:
        """Scene-owned timer survives when another scene is pushed on top."""
        log = []

        class S1(Scene):
            def on_enter(self) -> None:
                self.after(0.3, lambda: log.append("fired"))

        class S2(Scene):
            pass

        mock_game.push(S1())
        mock_game.tick(0.01)
        mock_game.push(S2())
        for _ in range(10):
            mock_game.tick(0.05)

        assert "fired" in log

    def test_timer_chain_cancelled_on_pop(self, mock_game: Game) -> None:
        """Timer with .then() chain is fully cancelled on scene pop."""
        log = []

        class S1(Scene):
            def on_enter(self) -> None:
                self.after(0.1, lambda: log.append("s1")) \
                    .then(lambda: log.append("s2"), 0.1) \
                    .then(lambda: log.append("s3"), 0.1)

        mock_game.push(S1())
        mock_game.tick(0.05)
        mock_game.pop()
        for _ in range(30):
            mock_game.tick(0.1)

        assert log == []

    def test_every_timer_cancelled_on_pop(self, mock_game: Game) -> None:
        """Repeating timer cancelled on scene pop."""
        log = []

        class S1(Scene):
            def on_enter(self) -> None:
                self.every(0.1, lambda: log.append("t"))

        mock_game.push(S1())
        mock_game.tick(0.15)
        count = len(log)
        mock_game.pop()
        for _ in range(20):
            mock_game.tick(0.1)

        assert len(log) == count

    def test_clear_and_push_kills_all(self, mock_game: Game) -> None:
        """clear_and_push kills all timers/actions from cleared scenes."""
        log = []

        class S1(Scene):
            def on_enter(self) -> None:
                self.sp = self.add_sprite(
                    Sprite("sprites/knight", position=(100, 100))
                )
                self.sp.do(Sequence(
                    Delay(1.0), Do(lambda: log.append("s1_act"))
                ))
                self.after(1.0, lambda: log.append("s1_tmr"))
                self.every(0.1, lambda: log.append("s1_ev"))

        class S2(Scene):
            pass

        mock_game.push(S1())
        mock_game.tick(0.05)
        log.clear()
        mock_game.clear_and_push(S2())
        for _ in range(30):
            mock_game.tick(0.1)

        assert log == []

    def test_scene_push_from_action_callback(self, mock_game: Game) -> None:
        """Push new scene from within a Do() action callback."""

        class S2(Scene):
            pass

        class S1(Scene):
            def on_enter(self) -> None:
                self.sp = self.add_sprite(
                    Sprite("sprites/knight", position=(100, 100))
                )
                self.sp.do(Sequence(Do(lambda: mock_game.push(S2()))))

        mock_game.push(S1())
        mock_game.tick(0.016)
        assert isinstance(mock_game._scene_stack.top(), S2)


# ---------------------------------------------------------------------------
# Exceptions in scene hooks
# ---------------------------------------------------------------------------


class TestSceneHookExceptions:
    """Verify correct exception handling in scene lifecycle hooks."""

    def test_on_enter_exception_rollback(self, mock_game: Game) -> None:
        """Exception in on_enter rolls back the push."""

        class Bad(Scene):
            def on_enter(self) -> None:
                raise RuntimeError("boom")

        mock_game.push(Scene())
        top_before = mock_game._scene_stack.top()
        with pytest.raises(RuntimeError, match="boom"):
            mock_game.push(Bad())
        assert mock_game._scene_stack.top() is top_before

    def test_on_exit_exception_cleanup_happens(self, mock_game: Game) -> None:
        """Exception in on_exit during pop: cleanup still runs."""

        class S2(Scene):
            def on_enter(self) -> None:
                self.sp = self.add_sprite(
                    Sprite("sprites/knight", position=(100, 100))
                )

            def on_exit(self) -> None:
                raise RuntimeError("boom")

        mock_game.push(Scene())
        s2 = S2()
        mock_game.push(s2)
        mock_game.tick(0.01)

        with pytest.raises(RuntimeError, match="boom"):
            mock_game.pop()

        assert mock_game._scene_stack.top().__class__.__name__ == "Scene"
        assert s2.sp.is_removed

    def test_on_reveal_exception(self, mock_game: Game) -> None:
        """Exception in on_reveal: S2 still popped."""

        class S1(Scene):
            def on_reveal(self) -> None:
                raise RuntimeError("boom")

        mock_game.push(S1())
        mock_game.push(Scene())

        with pytest.raises(RuntimeError, match="boom"):
            mock_game.pop()

        assert mock_game._scene_stack.top().__class__.__name__ == "S1"

    def test_on_exit_exception_in_clear_and_push(self, mock_game: Game) -> None:
        """Exception in one on_exit during clear_and_push: all cleaned up."""

        class S1(Scene):
            def on_enter(self) -> None:
                self.sp = self.add_sprite(
                    Sprite("sprites/knight", position=(100, 100))
                )

        class S2(Scene):
            def on_enter(self) -> None:
                self.sp = self.add_sprite(
                    Sprite("sprites/knight", position=(200, 200))
                )

            def on_exit(self) -> None:
                raise RuntimeError("boom")

        s1 = S1()
        mock_game.push(s1)
        mock_game.tick(0.01)
        s2 = S2()
        mock_game.push(s2)
        mock_game.tick(0.01)

        with pytest.raises(RuntimeError, match="boom"):
            mock_game.clear_and_push(Scene())

        assert s1.sp.is_removed
        assert s2.sp.is_removed

    def test_update_exception_propagates(self, mock_game: Game) -> None:
        """Exception in scene.update() propagates out of tick."""

        class Bad(Scene):
            def update(self, dt: float) -> None:
                raise RuntimeError("boom")

        mock_game.push(Bad())
        with pytest.raises(RuntimeError, match="boom"):
            mock_game.tick(0.016)

    def test_draw_exception_end_frame_called(self, mock_game: Game) -> None:
        """Exception in draw: end_frame still called."""
        calls = []
        orig = mock_game._backend.end_frame

        def tracking():
            calls.append("end_frame")
            return orig()

        mock_game._backend.end_frame = tracking

        class Bad(Scene):
            def draw(self) -> None:
                raise RuntimeError("boom")

        mock_game.push(Bad())
        with pytest.raises(RuntimeError, match="boom"):
            mock_game.tick(0.016)

        assert "end_frame" in calls

    def test_deferred_push_on_enter_exception_rollback(
        self, mock_game: Game
    ) -> None:
        """Deferred push with on_enter exception: S1 remains."""

        class Bad(Scene):
            def on_enter(self) -> None:
                raise RuntimeError("boom")

        class S1(Scene):
            done = False

            def update(self, dt: float) -> None:
                if not self.done:
                    self.done = True
                    mock_game.push(Bad())

        mock_game.push(S1())
        with pytest.raises(RuntimeError, match="boom"):
            mock_game.tick(0.016)

        assert isinstance(mock_game._scene_stack.top(), S1)


# ---------------------------------------------------------------------------
# Repeated Game initialization/teardown
# ---------------------------------------------------------------------------


class TestRepeatedGameLifecycle:
    """Validate Game init/teardown cycle safety."""

    def test_repeated_init_teardown(self) -> None:
        """Create and teardown Game multiple times."""
        for _ in range(5):
            g = Game("probe", backend="mock", resolution=(800, 600))
            g.push(Scene())
            Sprite("sprites/knight", position=(100, 100))
            g.tick(0.016)
            g._teardown()

    def test_teardown_calls_all_on_exit(self) -> None:
        """Teardown calls on_exit for all scenes on the stack."""
        g = Game("probe", backend="mock", resolution=(800, 600))
        try:
            log = []

            class S(Scene):
                def __init__(self, n: str):
                    super().__init__()
                    self.n = n

                def on_exit(self) -> None:
                    log.append(self.n)

            g.push(S("a"))
            g.push(S("b"))
            g.push(S("c"))
            g.tick(0.01)
            g._teardown()
            assert set(log) == {"a", "b", "c"}
        except Exception:
            g._teardown()
            raise

    def test_teardown_survives_on_exit_exception(self) -> None:
        """Teardown continues even when on_exit raises."""
        g = Game("probe", backend="mock", resolution=(800, 600))
        try:
            log = []

            class Good(Scene):
                def __init__(self, n: str):
                    super().__init__()
                    self.n = n

                def on_exit(self) -> None:
                    log.append(self.n)

            class Bad(Scene):
                def __init__(self):
                    super().__init__()
                    self._boom = False

                def on_exit(self) -> None:
                    log.append("bad")
                    if self._boom:
                        raise RuntimeError("boom")

            g.push(Good("a"))
            bad = Bad()
            g.push(bad)
            g.tick(0.01)
            bad._boom = True
            g._teardown()
            assert "a" in log and "bad" in log
        except Exception:
            g._teardown()
            raise

    def test_double_teardown_safe(self) -> None:
        """Double teardown is safe."""
        g = Game("probe", backend="mock", resolution=(800, 600))
        g.push(Scene())
        g.tick(0.01)
        g._teardown()
        g._teardown()

    def test_sprite_after_teardown_fails_cleanly(self) -> None:
        """Sprite creation after teardown raises RuntimeError."""
        g = Game("probe", backend="mock", resolution=(800, 600))
        g.push(Scene())
        g.tick(0.01)
        g._teardown()
        with pytest.raises(RuntimeError, match="No active Game"):
            Sprite("sprites/knight", position=(100, 100))

    def test_teardown_cancels_game_timers(self) -> None:
        """Teardown cancels all game-level timers."""
        g = Game("probe", backend="mock", resolution=(800, 600))
        try:
            g.push(Scene())
            g.after(0.5, lambda: None)
            g.every(0.1, lambda: None)
            g.tick(0.05)
            g._teardown()
            assert g._timer_manager._timers == {}
        except Exception:
            g._teardown()
            raise


# ---------------------------------------------------------------------------
# Additional edge cases
# ---------------------------------------------------------------------------


class TestAdditionalEdgeCases:
    """Validate additional edge cases."""

    def test_pause_below_false_updates_both(self, mock_game: Game) -> None:
        """pause_below=False: both scenes get updated."""
        log = []

        class S1(Scene):
            def update(self, dt: float) -> None:
                log.append("s1")

        class S2(Scene):
            pause_below = False

            def update(self, dt: float) -> None:
                log.append("s2")

        mock_game.push(S1())
        mock_game.push(S2())
        log.clear()
        mock_game.tick(0.016)
        assert "s1" in log and "s2" in log

    def test_game_timer_exception_does_not_kill_others(
        self, mock_game: Game
    ) -> None:
        """Timer callback exception doesn't prevent other timers from firing."""
        mock_game.push(Scene())
        mock_game.after(0.01, lambda: 1 / 0)
        log = []
        mock_game.after(0.01, lambda: log.append("ok"))
        mock_game.tick(0.02)
        assert "ok" in log

    def test_pop_on_cancel_deferred(self, mock_game: Game) -> None:
        """pop_on_cancel auto-pop is deferred during input phase."""

        class S2(Scene):
            pop_on_cancel = True

        mock_game.push(Scene())
        mock_game.push(S2())
        mock_game._backend.inject_key("escape")
        mock_game.tick(0.016)
        assert mock_game._scene_stack.top().__class__.__name__ == "Scene"

    def test_non_owned_sprite_survives_scene_pop(
        self, mock_game: Game
    ) -> None:
        """Sprite not owned by scene survives scene pop."""
        log = []

        class S1(Scene):
            def on_enter(self) -> None:
                self.free_sprite = Sprite(
                    "sprites/knight", position=(100, 100)
                )
                self.free_sprite.do(
                    Sequence(Delay(0.3), Do(lambda: log.append("done")))
                )

        s1 = S1()
        mock_game.push(s1)
        mock_game.tick(0.1)
        free_sp = s1.free_sprite
        mock_game.pop()

        assert not free_sp.is_removed
        for _ in range(10):
            mock_game.tick(0.1)
        assert "done" in log
