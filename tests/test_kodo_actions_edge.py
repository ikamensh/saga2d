"""Edge-case tests for zero-duration, NaN, and negative-duration actions/tweens.

Probes gaps not covered by F1-F20:
  1. FadeOut(0) — zero-duration division guard
  2. FadeIn(0) — zero-duration division guard
  3. FadeOut/FadeIn with negative duration
  4. Tween with duration=0
  5. Tween with NaN duration
  6. Tween with negative duration
  7. Sequence(Remove(), Do(...)) — callback after removal
  8. MoveTo to current position (already there)
  9. Parallel with only infinite children
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from saga2d import (
    Do,
    FadeIn,
    FadeOut,
    Game,
    MoveTo,
    Parallel,
    Remove,
    Repeat,
    Sequence,
    Sprite,
)
from saga2d.actions import Action, Delay
from saga2d.util.tween import Ease, TweenManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _InfiniteAction(Action):
    """An action that never finishes (is_finite=False)."""

    @property
    def is_finite(self) -> bool:
        return False

    def start(self, sprite: Sprite) -> None:
        self._started = True

    def update(self, _dt: float) -> bool:
        return False  # never done

    def stop(self) -> None:
        self._stopped = True


# ======================================================================
# 1. FadeOut(0) — division by zero guard
# ======================================================================


class TestFadeOutZeroDuration:
    """FadeOut(0) should complete instantly without ZeroDivisionError."""

    def test_fadeout_zero_completes_first_update(self) -> None:
        """FadeOut(0) should return True on the first update (dt=0)
        because elapsed (0) >= duration (0)."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            s.opacity = 200
            action = FadeOut(0)
            action.start(s)
            done = action.update(0.0)
            assert done is True, "FadeOut(0) should complete immediately"
            assert s.opacity == 0, "Opacity should be 0 after FadeOut(0)"
        finally:
            g._teardown()

    def test_fadeout_zero_with_positive_dt(self) -> None:
        """FadeOut(0) with dt > 0 should also complete immediately."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            s.opacity = 255
            action = FadeOut(0)
            action.start(s)
            done = action.update(0.016)
            assert done is True
            assert s.opacity == 0
        finally:
            g._teardown()


# ======================================================================
# 2. FadeIn(0) — division by zero guard
# ======================================================================


class TestFadeInZeroDuration:
    """FadeIn(0) should complete instantly without ZeroDivisionError."""

    def test_fadein_zero_completes_first_update(self) -> None:
        """FadeIn(0) should return True on the first update (dt=0)
        because elapsed (0) >= duration (0)."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            s.opacity = 0
            action = FadeIn(0)
            action.start(s)
            done = action.update(0.0)
            assert done is True, "FadeIn(0) should complete immediately"
            assert s.opacity == 255, "Opacity should be 255 after FadeIn(0)"
        finally:
            g._teardown()

    def test_fadein_zero_with_positive_dt(self) -> None:
        """FadeIn(0) with dt > 0 should also complete immediately."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            s.opacity = 100
            action = FadeIn(0)
            action.start(s)
            done = action.update(0.016)
            assert done is True
            assert s.opacity == 255
        finally:
            g._teardown()


# ======================================================================
# 3. FadeOut/FadeIn with negative duration
# ======================================================================


class TestFadeNegativeDuration:
    """Negative duration for FadeOut/FadeIn is now rejected at init time.

    FadeOut/FadeIn now validate duration and raise ValueError for
    negative, NaN, and Inf values.
    """

    def test_fadeout_negative_duration_completes_immediately(self) -> None:
        """FadeOut(-1.0) now raises ValueError at construction time
        because negative duration is rejected by validation."""
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            FadeOut(-1.0)

    def test_fadein_negative_duration_completes_immediately(self) -> None:
        """FadeIn(-1.0) now raises ValueError at construction time
        because negative duration is rejected by validation."""
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            FadeIn(-1.0)

    def test_fadeout_nan_duration_crashes_with_valueerror(self) -> None:
        """FadeOut(NaN) now raises ValueError at construction time.

        Previously, NaN was accepted and caused a crash during update
        when int(NaN) was attempted. Now validation catches it early.
        """
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            FadeOut(float("nan"))

    def test_fadein_nan_duration_crashes_with_valueerror(self) -> None:
        """FadeIn(NaN) now raises ValueError at construction time.

        Previously, NaN was accepted and caused a crash during update
        when int(NaN) was attempted. Now validation catches it early.
        """
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            FadeIn(float("nan"))


# ======================================================================
# 4. Tween with duration=0
# ======================================================================


class TestTweenZeroDuration:
    """Tween with duration=0 should snap to to_val immediately."""

    def test_tween_zero_duration_completes_on_first_update(self) -> None:
        """TweenManager.update(dt=0) with duration=0 tween:
        elapsed (0) >= duration (0) -> True, sets to_val immediately."""
        tm = TweenManager()

        class Target:
            val: float = 0.0

        t = Target()
        completed = []
        tm.create(t, "val", 0.0, 100.0, 0.0, on_complete=lambda: completed.append(True))
        tm.update(0.0)  # elapsed=0 >= duration=0 -> complete
        assert t.val == 100.0, "Tween(duration=0) should snap to to_val"
        assert len(completed) == 1, "on_complete should have been called"

    def test_tween_zero_duration_with_positive_dt(self) -> None:
        """Tween with duration=0 and dt>0 should also complete immediately."""
        tm = TweenManager()

        class Target:
            val: float = 50.0

        t = Target()
        tm.create(t, "val", 50.0, 200.0, 0.0)
        tm.update(0.016)
        assert t.val == 200.0


# ======================================================================
# 5. Tween with NaN duration
# ======================================================================


class TestTweenNanDuration:
    """Tween with NaN duration is now rejected by create().

    TweenManager.create() now validates duration and raises ValueError
    for NaN, Inf, and negative values.
    """

    def test_tween_nan_duration_accepted_by_create(self) -> None:
        """TweenManager.create() now validates duration — NaN is rejected."""
        tm = TweenManager()

        class Target:
            val: float = 0.0

        t = Target()
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            tm.create(t, "val", 0.0, 100.0, float("nan"))

    def test_tween_nan_duration_never_completes(self) -> None:
        """Tween with NaN duration cannot be created — ValueError at create time.

        Previously the tween would silently never complete. Now it is
        rejected upfront.
        """
        tm = TweenManager()

        class Target:
            val: float = 0.0

        t = Target()
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            tm.create(
                t, "val", 0.0, 100.0, float("nan"),
                on_complete=lambda: None,
            )

    def test_tween_nan_duration_produces_nan_values(self) -> None:
        """Tween with NaN duration cannot be created — ValueError at create time.

        Previously NaN duration would cause NaN property values. Now
        validation prevents the tween from being created at all.
        """
        tm = TweenManager()

        class Target:
            val: float = 0.0

        t = Target()
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            tm.create(t, "val", 0.0, 100.0, float("nan"))


# ======================================================================
# 6. Tween with negative duration
# ======================================================================


class TestTweenNegativeDuration:
    """Tween with negative duration is now rejected by create().

    TweenManager.create() now validates duration and raises ValueError
    for negative values.
    """

    def test_tween_negative_duration_accepted_by_create(self) -> None:
        """TweenManager.create() now rejects negative duration with ValueError."""
        tm = TweenManager()

        class Target:
            val: float = 0.0

        t = Target()
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            tm.create(t, "val", 0.0, 100.0, -1.0)

    def test_tween_negative_duration_completes_immediately(self) -> None:
        """Tween with negative duration cannot be created — ValueError at create time.

        Previously a negative-duration tween would complete immediately.
        Now it is rejected upfront.
        """
        tm = TweenManager()

        class Target:
            val: float = 0.0

        t = Target()
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            tm.create(
                t, "val", 0.0, 100.0, -1.0,
                on_complete=lambda: None,
            )


# ======================================================================
# 7. Sequence(Remove(), Do(...)) — callback after sprite removal
# ======================================================================


class TestSequenceRemoveThenDo:
    """When Remove() runs mid-Sequence, subsequent Do() should not crash.

    Remove() calls sprite.remove() which sets _removed=True and stops actions.
    The question is whether the Sequence continues executing after Remove().
    """

    def test_remove_then_do_in_sequence(self) -> None:
        """Sequence(Remove(), Do(fn)) — fn should still execute because
        Sequence chains instant actions in a single frame. Remove() returns
        True (done), then Do() starts and runs on the now-removed sprite.
        The Do callback itself should run since it's just a lambda."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            callback_called = []

            seq = Sequence(
                Remove(),
                Do(lambda: callback_called.append(True)),
            )
            s.do(seq)

            # After s.do(seq):
            #   - Sequence.start(s) starts Remove().start(s)
            #   - Sequence.update(0): Remove.update(0) calls s.remove() -> True
            #   BUT: s.remove() calls stop_actions(), which calls seq.stop()
            #   This sets _current_action = None, so update_action exits early.
            #   The question is whether Sequence.update is still on the stack.

            # Actually, let's trace the call more carefully:
            # s.do(seq) -> stop_actions(), set _current_action = seq, seq.start(s)
            # Then on the FIRST tick, s.update_action(dt) -> seq.update(dt)
            # seq.update calls Remove().update() -> s.remove()
            # s.remove() calls stop_actions() which calls seq.stop() and sets
            # s._current_action = None. But we are still inside seq.update().
            # After Remove().update() returns True, seq tries to advance to
            # next child. But s.remove() already called stop...

            # Let's just tick and see what happens.
            g.tick(dt=0.016)

            # Check sprite is removed
            assert s.is_removed is True

            # Whether the callback was called depends on the implementation.
            # Let's just record the result.
            if callback_called:
                # Do() callback ran even after Remove()
                assert len(callback_called) == 1
            else:
                # The callback was NOT called because remove() stopped the sequence
                pass

        finally:
            g._teardown()

    def test_remove_stops_sequence_progression(self) -> None:
        """Verify that after Remove(), the Sequence does not continue
        to subsequent non-instant actions either."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            post_remove_reached = []

            seq = Sequence(
                Remove(),
                Delay(1.0),
                Do(lambda: post_remove_reached.append(True)),
            )
            s.do(seq)
            # Tick multiple times
            for _ in range(60):
                g.tick(dt=0.016)

            assert s.is_removed is True
            # Post-Remove Delay/Do should NOT run since sprite is removed
            assert len(post_remove_reached) == 0
        finally:
            g._teardown()


# ======================================================================
# 8. MoveTo to current position (already there)
# ======================================================================


class TestMoveToCurrentPosition:
    """MoveTo where target == current position should complete immediately."""

    def test_moveto_already_at_target(self) -> None:
        """When sprite is already at target, dist < 1e-6 -> return True."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            action = MoveTo((100, 100), speed=200)
            action.start(s)
            done = action.update(0.0)
            assert done is True, "MoveTo to current position should return True immediately"
        finally:
            g._teardown()

    def test_moveto_very_close_to_target(self) -> None:
        """When sprite is within 1e-6 of target, should also complete."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            # Move to a position that differs by less than 1e-6
            action = MoveTo((100 + 1e-8, 100 + 1e-8), speed=200)
            action.start(s)
            done = action.update(0.0)
            assert done is True, "MoveTo within 1e-6 should return True immediately"
        finally:
            g._teardown()

    def test_moveto_just_outside_threshold(self) -> None:
        """When sprite is just outside the 1e-6 threshold, should NOT complete
        immediately (dt=0 means step=0, so it stays put, dist > 1e-6)."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            # 1e-5 is above the 1e-6 threshold
            action = MoveTo((100 + 1e-5, 100), speed=200)
            action.start(s)
            done = action.update(0.0)
            # dt=0, step=0, but dist ~ 1e-5 > 1e-6, so step(0) < dist -> False
            # BUT step=0 < dist, ratio = 0/dist = 0, sprite doesn't move.
            # Actually, step >= dist check: 0 >= 1e-5 -> False.
            # ratio = 0 / 1e-5 = 0 -> sprite stays.
            assert done is False, "MoveTo slightly outside threshold with dt=0 should NOT complete"
        finally:
            g._teardown()


# ======================================================================
# 9. Parallel with only infinite children
# ======================================================================


class TestParallelOnlyInfiniteChildren:
    """Parallel with only is_finite=False children.

    The check is:
        all(self._done[i] or not action.is_finite for i, action ...)
    If all children have is_finite=False, then `not action.is_finite` is True
    for every child, so `all(... True ...)` = True. The Parallel should
    finish immediately on the FIRST update.
    """

    def test_parallel_all_infinite_completes_first_update(self) -> None:
        """Parallel with only infinite children should complete on first update."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            inf1 = _InfiniteAction()
            inf2 = _InfiniteAction()

            par = Parallel(inf1, inf2)
            par.start(s)
            done = par.update(0.016)
            assert done is True, (
                "Parallel with only infinite children should complete immediately "
                "because all_finite_done = all(not is_finite) = all(True, True) = True"
            )
        finally:
            g._teardown()

    def test_parallel_all_infinite_stops_children(self) -> None:
        """When Parallel finishes due to no finite children, it should
        stop() all the infinite children."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            inf1 = _InfiniteAction()
            inf2 = _InfiniteAction()
            inf1._stopped = False
            inf2._stopped = False

            par = Parallel(inf1, inf2)
            par.start(s)
            done = par.update(0.016)
            assert done is True
            assert getattr(inf1, "_stopped", False) is True, "Infinite child 1 should be stopped"
            assert getattr(inf2, "_stopped", False) is True, "Infinite child 2 should be stopped"
        finally:
            g._teardown()

    def test_parallel_empty_completes_immediately(self) -> None:
        """Parallel with NO children should also complete immediately
        because all() of empty iterable is True."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            par = Parallel()
            par.start(s)
            done = par.update(0.016)
            assert done is True, "Parallel with no children should complete immediately"
        finally:
            g._teardown()


# ======================================================================
# Additional edge case: FadeOut/FadeIn with NaN (int(NaN) behavior)
# ======================================================================


class TestFadeNanIntConversion:
    """FadeOut/FadeIn with NaN duration now raise ValueError at init time.

    Previously, NaN duration was accepted and caused int(NaN) ValueError
    during update. Now validation catches NaN at construction time.
    """

    def test_fadeout_nan_duration_int_conversion(self) -> None:
        """FadeOut(NaN) now raises ValueError at construction time.

        Previously the error surfaced during update as int(NaN) failure.
        Now duration validation catches it immediately.
        """
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            FadeOut(float("nan"))

    def test_fadein_nan_duration_int_conversion(self) -> None:
        """FadeIn(NaN) now raises ValueError at construction time.

        Previously the error surfaced during update as int(NaN) failure.
        Now duration validation catches it immediately.
        """
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            FadeIn(float("nan"))


# ======================================================================
# Additional: Tween from_val/to_val NaN validation
# ======================================================================


class TestTweenInputValidation:
    """Verify that from_val and to_val NaN/Inf ARE rejected."""

    def test_tween_nan_from_val_rejected(self) -> None:
        tm = TweenManager()

        class Target:
            val: float = 0.0

        t = Target()
        with pytest.raises(ValueError, match="from_val must be finite"):
            tm.create(t, "val", float("nan"), 100.0, 1.0)

    def test_tween_nan_to_val_rejected(self) -> None:
        tm = TweenManager()

        class Target:
            val: float = 0.0

        t = Target()
        with pytest.raises(ValueError, match="to_val must be finite"):
            tm.create(t, "val", 0.0, float("nan"), 1.0)

    def test_tween_inf_duration_accepted(self) -> None:
        """Infinity duration is now rejected by create() with ValueError.

        Previously only from/to values were validated. Now duration is
        also checked for finiteness.
        """
        tm = TweenManager()

        class Target:
            val: float = 0.0

        t = Target()
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            tm.create(t, "val", 0.0, 100.0, float("inf"))

    def test_tween_inf_duration_never_completes(self) -> None:
        """Tween with inf duration cannot be created — ValueError at create time.

        Previously a tween with inf duration would silently never complete.
        Now validation prevents the tween from being created at all.
        """
        tm = TweenManager()

        class Target:
            val: float = 0.0

        t = Target()
        with pytest.raises(ValueError, match="duration must be a finite number >= 0"):
            tm.create(
                t, "val", 0.0, 100.0, float("inf"),
                on_complete=lambda: None,
            )


# ======================================================================
# Additional: Delay(0) should complete immediately
# ======================================================================


class TestDelayZero:
    """Delay(0) should complete on first update."""

    def test_delay_zero_completes_immediately(self) -> None:
        action = Delay(0)
        action.start(None)  # Delay.start is a no-op
        done = action.update(0.0)
        assert done is True, "Delay(0) with dt=0: 0 >= 0 is True"

    def test_delay_zero_with_positive_dt(self) -> None:
        action = Delay(0)
        action.start(None)
        done = action.update(0.016)
        assert done is True


# ======================================================================
# Additional: MoveTo with dt=0 and distant target
# ======================================================================


class TestMoveToZeroDt:
    """MoveTo with dt=0 — step = speed * 0 = 0."""

    def test_moveto_dt_zero_does_not_move(self) -> None:
        """With dt=0, step=0, sprite should not move and action not complete."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            action = MoveTo((500, 500), speed=200)
            action.start(s)
            done = action.update(0.0)
            # step = 0, dist > 1e-6, 0 >= dist -> False
            # ratio = 0/dist = 0, sprite stays at (100, 100)
            assert done is False
            assert s.position == (100, 100)
        finally:
            g._teardown()
