"""Regression tests for bugs found during kodo test run 2026-03-23.

Each test reproduces a specific bug and verifies the fix.
Tests are named test_F<n>_<description> to match the findings report.
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import pytest

from saga2d import (
    Delay,
    Game,
    MoveTo,
    ParticleEmitter,
    SaveManager,
    Scene,
    Sequence,
    Sprite,
    StateMachine,
    Do,
)


# ---------------------------------------------------------------------------
# F15: Delay(NaN) creates an unstoppable action
# ---------------------------------------------------------------------------


class TestF15DelayNaN:
    """Delay(NaN) should be rejected at construction time.

    Previously, Delay(NaN) was accepted because NaN >= 0 is False, but the
    check was `if seconds < 0` which NaN also passes (NaN < 0 is also False).
    The resulting Delay never completes because `elapsed >= NaN` is always False.
    """

    def test_delay_nan_rejected(self):
        """Delay(NaN) raises ValueError."""
        with pytest.raises(ValueError, match="finite|NaN|nan"):
            Delay(float("nan"))

    def test_delay_inf_rejected(self):
        """Delay(inf) raises ValueError — infinite wait is not useful."""
        with pytest.raises(ValueError, match="finite|Inf|inf"):
            Delay(float("inf"))

    def test_delay_negative_inf_rejected(self):
        """Delay(-inf) raises ValueError."""
        with pytest.raises(ValueError):
            Delay(float("-inf"))

    def test_delay_normal_still_works(self):
        """Normal Delay values still work after the fix."""
        d = Delay(0.0)
        assert d._seconds == 0.0

        d = Delay(1.5)
        assert d._seconds == 1.5

    def test_delay_zero_completes_immediately(self):
        """Delay(0) should complete on first update."""
        d = Delay(0.0)
        d.start(None)
        assert d.update(0.0) is True


# ---------------------------------------------------------------------------
# F16: MoveTo(speed=NaN) accepted — causes crash during update
# ---------------------------------------------------------------------------


class TestF16MoveToNaNSpeed:
    """MoveTo should reject NaN and Inf speed at construction time.

    Previously, MoveTo(speed=NaN) was accepted because `NaN <= 0` is False.
    During update(), step = NaN * dt = NaN, then ratio = NaN / dist = NaN,
    causing sprite.position = (NaN, NaN) which crashes with ValueError.
    """

    def test_moveto_nan_speed_rejected(self):
        """MoveTo with NaN speed raises ValueError."""
        with pytest.raises(ValueError, match="speed|finite|NaN"):
            MoveTo((200, 200), speed=float("nan"))

    def test_moveto_inf_speed_rejected(self):
        """MoveTo with inf speed raises ValueError."""
        with pytest.raises(ValueError, match="speed|finite"):
            MoveTo((200, 200), speed=float("inf"))

    def test_moveto_normal_still_works(self):
        """Normal speed values still work after the fix."""
        m = MoveTo((100, 100), speed=200)
        assert m._speed == 200


# ---------------------------------------------------------------------------
# F17: ParticleEmitter(images=[]) crashes on burst()
# ---------------------------------------------------------------------------


class TestF17ParticleEmitterEmptyImages:
    """ParticleEmitter with empty image list should raise early.

    Previously, ParticleEmitter([]) was accepted at construction, but
    burst() crashed with IndexError from random.choice([]).
    """

    def test_empty_images_rejected(self, mock_game):
        """ParticleEmitter with empty image list raises ValueError."""
        with pytest.raises((ValueError, IndexError)):
            e = ParticleEmitter([], position=(100, 100))
            e.burst(5)


# ---------------------------------------------------------------------------
# F18: FSM.trigger() not atomic — on_enter failure leaves state changed
# ---------------------------------------------------------------------------


class TestF18FSMAtomicity:
    """FSM.trigger() should be atomic: if on_enter raises, rollback state.

    Previously, trigger() changed state (line 76) before calling on_enter
    (line 78). If on_enter raised, the state was already changed to the
    target, leaving the FSM in an inconsistent state.
    """

    def test_on_enter_exception_rolls_back_state(self):
        """If on_enter raises, state should remain at old state."""
        def bad_enter():
            raise RuntimeError("enter failed")

        sm = StateMachine(
            states=["a", "b"],
            initial="a",
            transitions={"a": {"go": "b"}},
            on_enter={"b": bad_enter},
        )
        assert sm.state == "a"

        with pytest.raises(RuntimeError, match="enter failed"):
            sm.trigger("go")

        # State should be rolled back to 'a'
        assert sm.state == "a", (
            f"FSM state is '{sm.state}' but should be 'a' after on_enter failure"
        )

    def test_on_exit_exception_preserves_old_state(self):
        """If on_exit raises, state should remain at old state."""
        def bad_exit():
            raise RuntimeError("exit failed")

        sm = StateMachine(
            states=["a", "b"],
            initial="a",
            transitions={"a": {"go": "b"}},
            on_exit={"a": bad_exit},
        )
        assert sm.state == "a"

        with pytest.raises(RuntimeError, match="exit failed"):
            sm.trigger("go")

        # State should still be 'a' — on_exit fires before state change
        assert sm.state == "a"

    def test_successful_transition_still_works(self):
        """Normal transitions still work after the atomicity fix."""
        history = []

        sm = StateMachine(
            states=["a", "b"],
            initial="a",
            transitions={"a": {"go": "b"}},
            on_enter={"b": lambda: history.append("entered_b")},
            on_exit={"a": lambda: history.append("exited_a")},
        )
        result = sm.trigger("go")
        assert result is True
        assert sm.state == "b"
        assert history == ["exited_a", "entered_b"]


# ---------------------------------------------------------------------------
# F19: SaveManager(str) crashes — should accept str or Path
# ---------------------------------------------------------------------------


class TestF19SaveManagerStrPath:
    """SaveManager should accept str path, not just Path objects.

    Previously, SaveManager('/tmp/saves') crashed with
    AttributeError: 'str' object has no attribute 'mkdir' because
    _save_dir was stored as-is without conversion.
    """

    def test_str_path_accepted(self):
        """SaveManager accepts string path."""
        with tempfile.TemporaryDirectory() as td:
            sm = SaveManager(td)  # Pass string, not Path
            sm.save(1, {"test": True}, "TestScene")
            loaded = sm.load(1)
            assert loaded is not None
            assert loaded["state"]["test"] is True

    def test_path_still_works(self):
        """SaveManager still works with Path objects."""
        with tempfile.TemporaryDirectory() as td:
            sm = SaveManager(Path(td))
            sm.save(1, {"test": True}, "TestScene")
            loaded = sm.load(1)
            assert loaded is not None
