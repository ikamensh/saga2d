"""Stage 2 regression tests for bugs F42–F43.

F42: Repeat(times=negative_int) silently accepted — no-op instead of error
F43: MoveTo with scalar/1-tuple position leaks raw IndexError/TypeError
"""

from __future__ import annotations

import math

import pytest

from saga2d.actions import Delay, Do, MoveTo, Repeat


# ══════════════════════════════════════════════════════════════════════════════
# F42: Repeat(times=negative_int) must raise ValueError
# ══════════════════════════════════════════════════════════════════════════════


class TestF42RepeatNegativeTimes:
    """Repeat(action, times=<negative int>) should raise ValueError.

    Previously negative ints were silently accepted; start() treated them
    like zero (times <= 0), producing a confusing instant-finish with no
    error.  Users who accidentally pass -1 expecting "forever" (like
    some C APIs) should get an actionable error.
    """

    def test_negative_one(self):
        with pytest.raises(ValueError, match=">="):
            Repeat(Delay(0.1), times=-1)

    def test_large_negative(self):
        with pytest.raises(ValueError, match=">="):
            Repeat(Delay(0.1), times=-999)

    def test_zero_still_accepted(self):
        """times=0 is valid — means 'execute zero times'."""
        r = Repeat(Delay(0.1), times=0)
        assert r.is_finite

    def test_positive_still_accepted(self):
        r = Repeat(Delay(0.1), times=5)
        assert r.is_finite

    def test_none_still_accepted(self):
        """times=None = infinite loop."""
        r = Repeat(Delay(0.1), times=None)
        assert not r.is_finite

    def test_bool_rejected(self):
        """bool is a subclass of int but should be rejected."""
        with pytest.raises(TypeError, match="bool"):
            Repeat(Delay(0.1), times=True)
        with pytest.raises(TypeError, match="bool"):
            Repeat(Delay(0.1), times=False)


# ══════════════════════════════════════════════════════════════════════════════
# F43: MoveTo position must be validated for shape and type
# ══════════════════════════════════════════════════════════════════════════════


class TestF43MoveToPositionValidation:
    """MoveTo(position, speed) should raise a clear TypeError for
    non-tuple, too-short, or non-numeric position values — not leak
    raw IndexError or 'not subscriptable' errors.
    """

    def test_scalar_int(self):
        with pytest.raises(TypeError, match=r"\(x, y\) tuple"):
            MoveTo(100, speed=200)

    def test_scalar_float(self):
        with pytest.raises(TypeError, match=r"\(x, y\) tuple"):
            MoveTo(3.14, speed=200)

    def test_none_position(self):
        with pytest.raises(TypeError, match=r"\(x, y\) tuple"):
            MoveTo(None, speed=200)

    def test_empty_tuple(self):
        with pytest.raises(TypeError, match="at least 2 elements"):
            MoveTo((), speed=200)

    def test_1_tuple(self):
        with pytest.raises(TypeError, match="at least 2 elements"):
            MoveTo((100,), speed=200)

    def test_string_position(self):
        """Strings are iterable but elements aren't float-convertible."""
        with pytest.raises(TypeError, match="numbers"):
            MoveTo("ab", speed=200)

    def test_non_numeric_tuple(self):
        with pytest.raises(TypeError, match="numbers"):
            MoveTo(("a", "b"), speed=200)

    def test_valid_2_tuple(self):
        m = MoveTo((100, 200), speed=300)
        assert m._target_x == 100.0
        assert m._target_y == 200.0

    def test_valid_list(self):
        m = MoveTo([50, 75], speed=100)
        assert m._target_x == 50.0
        assert m._target_y == 75.0

    def test_valid_3_tuple_extra_ignored(self):
        """Extra elements beyond (x, y) are silently ignored."""
        m = MoveTo((10, 20, 30), speed=100)
        assert m._target_x == 10.0
        assert m._target_y == 20.0

    def test_nan_still_raises_valueerror(self):
        """NaN values still raise ValueError (not TypeError)."""
        with pytest.raises(ValueError, match="finite"):
            MoveTo((float("nan"), 100), speed=200)

    def test_inf_still_raises_valueerror(self):
        with pytest.raises(ValueError, match="finite"):
            MoveTo((100, float("inf")), speed=200)

    def test_zero_speed_still_raises(self):
        with pytest.raises(ValueError, match="> 0"):
            MoveTo((100, 200), speed=0)

    def test_nan_speed_still_raises(self):
        with pytest.raises(ValueError, match="finite"):
            MoveTo((100, 200), speed=float("nan"))
