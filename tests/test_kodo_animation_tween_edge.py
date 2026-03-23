"""Edge-case tests for AnimationPlayer and TweenManager.

Covers invalid frame_duration values (zero, negative, NaN, Inf) that cause
infinite loops or stuck playback, as well as tween duration edge cases
(zero, negative, very large dt, conflicting tweens).

Tests marked with ``# BUG: ...`` document current broken behavior and are
expected to FAIL until the underlying bugs are fixed.  Tests without that
marker exercise currently-working behavior and should PASS.

Key bugs demonstrated:
  - AnimationPlayer with frame_duration=0 and loop=True -> infinite loop
  - AnimationPlayer with frame_duration<0 and loop=True -> infinite loop
  - AnimationPlayer with frame_duration=NaN -> stuck (never advances)
  - AnimationPlayer with frame_duration=Inf -> stuck (never advances)
  - AnimationDef accepts all invalid frame_duration values without validation
"""

from __future__ import annotations

import math
import signal
import sys
from typing import Any

import pytest

from saga2d.animation import AnimationDef, AnimationPlayer
from saga2d.util.tween import Ease, TweenManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Sentinel frames used as resolved "ImageHandle" stand-ins.
FRAMES_3 = ["frame_a", "frame_b", "frame_c"]
FRAMES_1 = ["only_frame"]


class _Obj:
    """Minimal target for TweenManager tests."""

    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


def _run_with_timeout(fn, *, timeout: float = 2.0):
    """Run *fn* with a wall-clock timeout (Unix only).

    Raises ``TimeoutError`` if *fn* does not return within *timeout* seconds.
    On Windows (no SIGALRM) the test is simply skipped.
    """
    if sys.platform == "win32":
        pytest.skip("SIGALRM not available on Windows")

    def _handler(signum, frame):
        raise TimeoutError(f"Function did not return within {timeout}s")

    old = signal.signal(signal.SIGALRM, _handler)
    signal.setitimer(signal.ITIMER_REAL, timeout)
    try:
        return fn()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


# ======================================================================
# AnimationPlayer -- invalid frame_duration
# ======================================================================


class TestAnimationPlayerZeroFrameDuration:
    """frame_duration=0 causes an infinite loop in update() when looping.

    With loop=False the while loop terminates because frame_index eventually
    exceeds len(frames) and the non-loop branch sets _finished=True + break.
    But with loop=True, frame_index wraps back to 0 and the loop never ends
    because elapsed never decreases (subtracting 0 is a no-op).

    Expected fix: AnimationPlayer.__init__ should raise ValueError when
    frame_duration <= 0, OR update() should guard the while loop.
    """

    def test_zero_frame_duration_raises(self):
        """Construction with frame_duration=0 should raise ValueError (F21 fix)."""
        with pytest.raises(ValueError, match="frame_duration"):
            AnimationPlayer(FRAMES_3, frame_duration=0, loop=False)

    def test_zero_frame_duration_loop_also_raises(self):
        """Construction with frame_duration=0 and loop=True also raises (F21 fix)."""
        with pytest.raises(ValueError, match="frame_duration"):
            AnimationPlayer(FRAMES_3, frame_duration=0, loop=True)


class TestAnimationPlayerNegativeFrameDuration:
    """frame_duration < 0 causes an infinite loop in update() when looping.

    The while condition ``elapsed >= negative`` is always True for positive
    elapsed, and ``elapsed -= negative`` makes elapsed grow.  With loop=False
    the frame_index overshoots and the break terminates the loop.  With
    loop=True the frame_index wraps and the loop runs forever with diverging
    elapsed.
    """

    def test_negative_frame_duration_raises(self):
        """Construction with frame_duration < 0 should raise ValueError (F22 fix)."""
        with pytest.raises(ValueError, match="frame_duration"):
            AnimationPlayer(FRAMES_3, frame_duration=-0.1, loop=False)

    def test_negative_frame_duration_loop_also_raises(self):
        """Construction with frame_duration < 0 and loop=True also raises (F22 fix)."""
        with pytest.raises(ValueError, match="frame_duration"):
            AnimationPlayer(FRAMES_3, frame_duration=-0.5, loop=True)


class TestAnimationPlayerNaNFrameDuration:
    """frame_duration=NaN means the while condition is always False (NaN
    comparisons return False), so frames never advance.
    """

    def test_nan_frame_duration_raises(self):
        """Construction with NaN frame_duration should raise ValueError (F23 fix)."""
        with pytest.raises(ValueError, match="frame_duration"):
            AnimationPlayer(FRAMES_3, frame_duration=float("nan"), loop=False)


class TestAnimationPlayerInfFrameDuration:
    """frame_duration=Inf means elapsed never reaches the threshold, so
    frames never advance.  Effectively a frozen animation.
    """

    def test_inf_frame_duration_raises(self):
        """Construction with Inf frame_duration should raise ValueError (F23 fix)."""
        with pytest.raises(ValueError, match="frame_duration"):
            AnimationPlayer(FRAMES_3, frame_duration=float("inf"), loop=False)


# ======================================================================
# AnimationDef -- missing validation (documenting the gap)
# ======================================================================


class TestAnimationDefValidation:
    """AnimationDef now validates frame_duration (F21-F23 fixes)."""

    def test_def_rejects_zero_frame_duration(self):
        """AnimationDef rejects frame_duration=0."""
        with pytest.raises(ValueError, match="frame_duration"):
            AnimationDef(frames=["a", "b"], frame_duration=0)

    def test_def_rejects_negative_frame_duration(self):
        """AnimationDef rejects negative frame_duration."""
        with pytest.raises(ValueError, match="frame_duration"):
            AnimationDef(frames=["a", "b"], frame_duration=-1.0)

    def test_def_rejects_nan_frame_duration(self):
        """AnimationDef rejects NaN frame_duration."""
        with pytest.raises(ValueError, match="frame_duration"):
            AnimationDef(frames=["a", "b"], frame_duration=float("nan"))

    def test_def_rejects_inf_frame_duration(self):
        """AnimationDef rejects Inf frame_duration."""
        with pytest.raises(ValueError, match="frame_duration"):
            AnimationDef(frames=["a", "b"], frame_duration=float("inf"))

    def test_def_accepts_valid_frame_duration(self):
        """AnimationDef accepts valid positive frame_duration."""
        d = AnimationDef(frames=["a", "b"], frame_duration=0.15)
        assert d.frame_duration == 0.15


# ======================================================================
# AnimationPlayer -- normal / valid behavior (should all PASS)
# ======================================================================


class TestAnimationPlayerNormal:
    """Sanity tests for valid AnimationPlayer behavior."""

    def test_normal_update_advances_frames(self):
        """Normal multi-frame animation cycles through frames."""
        player = AnimationPlayer(FRAMES_3, frame_duration=0.1, loop=False)
        assert player.current_frame == "frame_a"

        # Not enough time to advance yet.
        result = player.update(0.05)
        assert result is None
        assert player.frame_index == 0

        # Exactly enough time to advance to frame_b.
        result = player.update(0.05)
        assert result == "frame_b"
        assert player.frame_index == 1

    def test_normal_loop(self):
        """Looping animation wraps around."""
        player = AnimationPlayer(FRAMES_3, frame_duration=0.1, loop=True)
        # Advance past all 3 frames (0.3s total).
        player.update(0.25)  # -> frame_c (index 2)
        result = player.update(0.1)  # -> wraps to frame_a (index 0)
        # After wrapping, frame_index is 0.
        assert player.frame_index == 0
        assert player.is_playing is True

    def test_non_loop_finishes(self):
        """Non-looping animation finishes and fires on_complete."""
        completed = []
        player = AnimationPlayer(
            FRAMES_3,
            frame_duration=0.1,
            loop=False,
            on_complete=lambda: completed.append(True),
        )
        # Advance far enough to finish (3 frames * 0.1 = 0.3s).
        player.update(0.5)
        assert player.is_complete is True
        assert player.is_playing is False
        assert len(completed) == 1

    def test_finished_player_returns_none(self):
        """After finishing, further updates return None."""
        player = AnimationPlayer(FRAMES_3, frame_duration=0.1, loop=False)
        player.update(1.0)  # finish
        assert player.is_complete is True
        result = player.update(0.1)
        assert result is None


class TestAnimationPlayerSingleFrame:
    """Edge case: animation with only one frame."""

    def test_single_frame_non_loop_finishes_immediately(self):
        """A 1-frame non-looping animation finishes on the first update
        that exceeds frame_duration.
        """
        completed = []
        player = AnimationPlayer(
            FRAMES_1,
            frame_duration=0.1,
            loop=False,
            on_complete=lambda: completed.append(True),
        )
        assert player.current_frame == "only_frame"
        # Advance past the single frame.
        player.update(0.2)
        assert player.is_complete is True
        assert len(completed) == 1
        # Frame index is clamped to last (only) frame.
        assert player.frame_index == 0

    def test_single_frame_loop_stays_on_frame(self):
        """A 1-frame looping animation wraps but stays on the same frame."""
        player = AnimationPlayer(FRAMES_1, frame_duration=0.1, loop=True)
        # Many updates -- still on the same frame, never finished.
        for _ in range(50):
            player.update(0.1)
        assert player.frame_index == 0
        assert player.is_playing is True


class TestAnimationPlayerLargeDt:
    """Very large dt values -- should skip many frames without issues."""

    def test_large_dt_non_loop_finishes(self):
        """A non-looping animation with huge dt completes cleanly."""
        completed = []
        player = AnimationPlayer(
            FRAMES_3,
            frame_duration=0.1,
            loop=False,
            on_complete=lambda: completed.append(True),
        )
        result = player.update(1000.0)
        assert player.is_complete is True
        assert len(completed) == 1
        # Should land on last frame.
        assert player.frame_index == 2

    def test_large_dt_loop_wraps(self):
        """A looping animation with huge dt still wraps correctly."""
        player = AnimationPlayer(FRAMES_3, frame_duration=0.1, loop=True)
        player.update(1000.0)
        # It should wrap many times; frame_index is some value in [0, 2].
        assert 0 <= player.frame_index < len(FRAMES_3)
        assert player.is_playing is True

    def test_zero_frames_raises(self):
        """Constructing with empty frames list raises ValueError."""
        with pytest.raises(ValueError, match="zero frames"):
            AnimationPlayer([], frame_duration=0.1, loop=False)


# ======================================================================
# TweenManager -- duration edge cases
# ======================================================================


class TestTweenZeroDuration:
    """TweenManager.create with duration=0.

    Duration=0 is accepted by the existing validation (>= 0 check passes).
    On the first update(), elapsed (>= 0) >= duration (0) is True,
    so the tween completes immediately -- this works correctly.
    """

    def test_zero_duration_completes_on_first_update(self):
        """A zero-duration tween should snap to to_val on the first update."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        completed = []
        tm.create(
            obj, "x", 0.0, 100.0, duration=0,
            on_complete=lambda: completed.append(True),
        )
        tm.update(0.016)
        assert obj.x == 100.0
        assert len(completed) == 1

    def test_zero_duration_with_zero_dt(self):
        """Zero-duration tween with dt=0 should still complete.

        elapsed (0) >= duration (0) is True, so the tween completes
        immediately even with dt=0.
        """
        tm = TweenManager()
        obj = _Obj(x=0.0)
        completed = []
        tm.create(
            obj, "x", 0.0, 50.0, duration=0,
            on_complete=lambda: completed.append(True),
        )
        tm.update(0.0)
        assert obj.x == 50.0
        assert len(completed) == 1


class TestTweenNegativeDuration:
    """TweenManager.create with negative duration.

    The current code validates ``duration < 0`` and raises ValueError.
    These tests confirm that validation works correctly.
    """

    def test_negative_duration_raises(self):
        """A negative-duration tween is rejected at creation time."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        with pytest.raises(ValueError, match="duration"):
            tm.create(obj, "x", 0.0, 99.0, duration=-1.0)

    def test_negative_duration_nan_raises(self):
        """NaN duration is also rejected."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        with pytest.raises(ValueError, match="duration"):
            tm.create(obj, "x", 0.0, 99.0, duration=float("nan"))

    def test_negative_duration_inf_raises(self):
        """Inf duration is also rejected."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        with pytest.raises(ValueError, match="duration"):
            tm.create(obj, "x", 0.0, 99.0, duration=float("inf"))


class TestTweenLargeDt:
    """TweenManager.update with very large dt -- numerical stability."""

    def test_large_dt_completes_tween(self):
        """A tween with dt=1e9 should complete and set to_val exactly."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        completed = []
        tm.create(
            obj, "x", 0.0, 42.0, duration=1.0,
            on_complete=lambda: completed.append(True),
        )
        tm.update(1e9)
        assert obj.x == 42.0
        assert len(completed) == 1

    def test_large_dt_does_not_produce_nan_or_inf(self):
        """Even with huge dt, the property value should be finite."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        tm.create(obj, "x", 0.0, 1.0, duration=1.0)
        tm.update(1e9)
        assert math.isfinite(obj.x)

    def test_non_finite_dt_ignored(self):
        """NaN and Inf dt values should be silently ignored."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        tm.create(obj, "x", 0.0, 100.0, duration=1.0)
        tm.update(float("nan"))
        assert obj.x == 0.0  # unchanged
        tm.update(float("inf"))
        assert obj.x == 0.0  # unchanged


class TestTweenConflict:
    """Multiple tweens on the same target+property at the same time."""

    def test_two_tweens_same_property_both_run(self):
        """Two concurrent tweens on the same property both write to it.

        The last one to execute in iteration order wins for any given frame.
        This documents current behavior (no conflict resolution).
        """
        tm = TweenManager()
        obj = _Obj(x=0.0)
        # Tween A: 0 -> 100 over 1s
        tm.create(obj, "x", 0.0, 100.0, duration=1.0)
        # Tween B: 0 -> -100 over 1s (same property!)
        tm.create(obj, "x", 0.0, -100.0, duration=1.0)
        tm.update(0.5)
        # Both tweens write to obj.x; the second one wins because it
        # iterates later (dict insertion order in Python 3.7+).
        assert obj.x == pytest.approx(-50.0)

    def test_two_tweens_same_property_both_complete(self):
        """Both tweens eventually complete; second one's to_val sticks."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        completed_a = []
        completed_b = []
        tm.create(
            obj, "x", 0.0, 100.0, duration=1.0,
            on_complete=lambda: completed_a.append(True),
        )
        tm.create(
            obj, "x", 0.0, -100.0, duration=1.0,
            on_complete=lambda: completed_b.append(True),
        )
        tm.update(2.0)
        # Both callbacks fire.
        assert len(completed_a) == 1
        assert len(completed_b) == 1
        # Final value is from the second tween (last writer wins).
        assert obj.x == -100.0

    def test_different_properties_no_conflict(self):
        """Tweens on different properties are independent."""
        tm = TweenManager()
        obj = _Obj(x=0.0, y=0.0)
        tm.create(obj, "x", 0.0, 10.0, duration=1.0)
        tm.create(obj, "y", 0.0, 20.0, duration=1.0)
        tm.update(0.5)
        assert obj.x == pytest.approx(5.0)
        assert obj.y == pytest.approx(10.0)


# ======================================================================
# TweenManager -- existing validation (should PASS)
# ======================================================================


class TestTweenExistingValidation:
    """Tests for validation that already works correctly."""

    def test_non_finite_from_val_raises(self):
        """NaN from_val is rejected."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        with pytest.raises(ValueError, match="from_val"):
            tm.create(obj, "x", float("nan"), 1.0, duration=1.0)

    def test_non_finite_to_val_raises(self):
        """Inf to_val is rejected."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        with pytest.raises(ValueError, match="to_val"):
            tm.create(obj, "x", 0.0, float("inf"), duration=1.0)

    def test_missing_attribute_raises(self):
        """Attribute that does not exist raises AttributeError."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        with pytest.raises(AttributeError):
            tm.create(obj, "nonexistent", 0.0, 1.0, duration=1.0)

    def test_cancel_tween(self):
        """Cancelling a tween prevents further updates."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        tid = tm.create(obj, "x", 0.0, 100.0, duration=1.0)
        tm.update(0.1)
        assert obj.x == pytest.approx(10.0)
        tm.cancel(tid)
        tm.update(10.0)
        # x should stay where it was when cancelled.
        assert obj.x == pytest.approx(10.0)

    def test_cancel_all(self):
        """cancel_all removes all tweens."""
        tm = TweenManager()
        obj = _Obj(x=0.0, y=0.0)
        tm.create(obj, "x", 0.0, 100.0, duration=1.0)
        tm.create(obj, "y", 0.0, 200.0, duration=1.0)
        tm.cancel_all()
        tm.update(10.0)
        assert obj.x == 0.0
        assert obj.y == 0.0


# ======================================================================
# TweenManager -- easing variants (should PASS)
# ======================================================================


class TestTweenEasing:
    """Easing functions produce correct values at boundary points."""

    @pytest.mark.parametrize("ease", list(Ease))
    def test_easing_completes_to_exact_value(self, ease: Ease):
        """All easing curves should land on to_val when complete."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        tm.create(obj, "x", 0.0, 42.0, duration=1.0, ease=ease)
        tm.update(2.0)  # well past duration
        assert obj.x == 42.0

    @pytest.mark.parametrize("ease", list(Ease))
    def test_easing_midpoint_is_finite(self, ease: Ease):
        """All easing curves produce finite values at the midpoint."""
        tm = TweenManager()
        obj = _Obj(x=0.0)
        tm.create(obj, "x", 0.0, 100.0, duration=1.0, ease=ease)
        tm.update(0.5)
        assert math.isfinite(obj.x)
        assert 0.0 <= obj.x <= 100.0
