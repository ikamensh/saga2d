"""Regression tests for bugs found during kodo test runs.

Each test reproduces a specific bug and verifies the fix.
Tests are named test_F<n>_<description> to match the findings report.

F15-F19: From first run (already fixed)
F21-F25: From second run (new findings)
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import pytest

from saga2d import (
    Delay,
    FadeIn,
    FadeOut,
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
from saga2d.ui.widgets import TextBox
from saga2d.util.timer import TimerManager
from saga2d.util.tween import TweenManager


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


# ===========================================================================
# F21: TweenManager.create() accepts NaN/Inf/negative duration
# ===========================================================================


class TestF21TweenDurationValidation:
    """TweenManager.create() must validate duration is finite and >= 0.

    BUG: create() validates from_val and to_val with math.isfinite() but
    does NOT validate duration. NaN duration creates an immortal tween that
    never completes and produces NaN property values. Inf duration creates
    an immortal tween. Negative duration completes immediately (harmless
    but confusing).
    """

    def test_nan_duration_rejected(self) -> None:
        """NaN duration should raise ValueError, not create an immortal tween."""
        tm = TweenManager()

        class T:
            val: float = 0.0

        t = T()
        with pytest.raises(ValueError, match="duration must be"):
            tm.create(t, "val", 0.0, 100.0, float("nan"))

    def test_inf_duration_rejected(self) -> None:
        """Inf duration should raise ValueError, not create an immortal tween."""
        tm = TweenManager()

        class T:
            val: float = 0.0

        t = T()
        with pytest.raises(ValueError, match="duration must be"):
            tm.create(t, "val", 0.0, 100.0, float("inf"))

    def test_negative_inf_duration_rejected(self) -> None:
        """-Inf duration should raise ValueError."""
        tm = TweenManager()

        class T:
            val: float = 0.0

        t = T()
        with pytest.raises(ValueError, match="duration must be"):
            tm.create(t, "val", 0.0, 100.0, float("-inf"))

    def test_negative_duration_rejected(self) -> None:
        """Negative duration should raise ValueError."""
        tm = TweenManager()

        class T:
            val: float = 0.0

        t = T()
        with pytest.raises(ValueError, match="duration must be"):
            tm.create(t, "val", 0.0, 100.0, -1.0)

    def test_zero_duration_still_works(self) -> None:
        """duration=0 is valid — tween completes on first update."""
        tm = TweenManager()

        class T:
            val: float = 0.0

        t = T()
        completed = []
        tm.create(t, "val", 0.0, 100.0, 0.0, on_complete=lambda: completed.append(True))
        tm.update(0.0)
        assert t.val == 100.0
        assert len(completed) == 1

    def test_normal_duration_still_works(self) -> None:
        """Normal positive duration should still work (no regression)."""
        tm = TweenManager()

        class T:
            val: float = 0.0

        t = T()
        completed = []
        tm.create(t, "val", 0.0, 100.0, 1.0, on_complete=lambda: completed.append(True))
        tm.update(1.0)
        assert t.val == 100.0
        assert len(completed) == 1


# ===========================================================================
# F22: TimerManager.after() accepts NaN/Inf delay
# ===========================================================================


class TestF22TimerAfterNaNInfDelay:
    """TimerManager.after() must reject NaN and Inf delays.

    BUG: after() checks `if delay < 0` but NaN < 0 is False (IEEE 754),
    so NaN passes. The timer gets remaining=NaN; remaining -= dt stays NaN;
    remaining <= 0 is False for NaN, so the callback never fires. The timer
    stays in _timers forever (memory leak). Same for +Inf.
    """

    def test_nan_delay_rejected(self) -> None:
        """NaN delay should raise ValueError, not silently create a broken timer."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="delay must be"):
            tm.after(float("nan"), lambda: None)

    def test_inf_delay_rejected(self) -> None:
        """Inf delay should raise ValueError, not create a timer that never fires."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="delay must be"):
            tm.after(float("inf"), lambda: None)

    def test_negative_inf_still_rejected(self) -> None:
        """-Inf was already rejected by the < 0 check (passes before fix)."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="delay must be"):
            tm.after(float("-inf"), lambda: None)

    def test_zero_delay_still_works(self) -> None:
        """delay=0 fires on first update (no regression)."""
        tm = TimerManager()
        fired = []
        tm.after(0, lambda: fired.append(True))
        tm.update(0.016)
        assert fired == [True]

    def test_normal_delay_still_works(self) -> None:
        """Normal positive delay still works (no regression)."""
        tm = TimerManager()
        fired = []
        tm.after(1.0, lambda: fired.append(True))
        tm.update(1.0)
        assert fired == [True]


# ===========================================================================
# F23: TimerManager.every() accepts NaN/Inf interval
# ===========================================================================


class TestF23TimerEveryNaNInterval:
    """TimerManager.every() must reject NaN and Inf intervals.

    BUG: every() checks `if interval <= 0` but NaN <= 0 is False (IEEE 754),
    so NaN passes. Same pattern as F22. +Inf also passes since Inf <= 0 is
    False.
    """

    def test_nan_interval_rejected(self) -> None:
        """NaN interval should raise ValueError, not silently create a broken timer."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="interval must be"):
            tm.every(float("nan"), lambda: None)

    def test_inf_interval_rejected(self) -> None:
        """Inf interval should raise ValueError."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="interval must be"):
            tm.every(float("inf"), lambda: None)

    def test_normal_interval_still_works(self) -> None:
        """Normal positive interval still works (no regression)."""
        tm = TimerManager()
        count = []
        tm.every(0.5, lambda: count.append(1))
        tm.update(0.5)
        assert len(count) == 1
        tm.update(0.5)
        assert len(count) == 2


# ===========================================================================
# F24: FadeOut/FadeIn accept NaN/Inf/negative duration (no validation)
# ===========================================================================


class TestF24FadeOutFadeInDurationValidation:
    """FadeOut/FadeIn must validate duration is finite and >= 0.

    BUG: FadeOut and FadeIn have no duration validation at all. NaN duration
    causes ValueError crash during update (int(NaN) fails). Inf duration
    creates an action that runs forever. Negative duration completes
    immediately (harmless but confusing).
    """

    def test_fadeout_nan_rejected(self) -> None:
        """FadeOut(NaN) should raise ValueError at init, not crash during update."""
        with pytest.raises(ValueError, match="duration must be"):
            FadeOut(float("nan"))

    def test_fadein_nan_rejected(self) -> None:
        """FadeIn(NaN) should raise ValueError at init."""
        with pytest.raises(ValueError, match="duration must be"):
            FadeIn(float("nan"))

    def test_fadeout_inf_rejected(self) -> None:
        """FadeOut(Inf) should raise ValueError."""
        with pytest.raises(ValueError, match="duration must be"):
            FadeOut(float("inf"))

    def test_fadein_inf_rejected(self) -> None:
        """FadeIn(Inf) should raise ValueError."""
        with pytest.raises(ValueError, match="duration must be"):
            FadeIn(float("inf"))

    def test_fadeout_negative_rejected(self) -> None:
        """FadeOut(-1) should raise ValueError."""
        with pytest.raises(ValueError, match="duration must be"):
            FadeOut(-1.0)

    def test_fadein_negative_rejected(self) -> None:
        """FadeIn(-1) should raise ValueError."""
        with pytest.raises(ValueError, match="duration must be"):
            FadeIn(-1.0)

    def test_fadeout_zero_still_works(self) -> None:
        """FadeOut(0) still completes immediately (no regression)."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            s.opacity = 200
            action = FadeOut(0)
            action.start(s)
            assert action.update(0.0) is True
            assert s.opacity == 0
        finally:
            g._teardown()

    def test_fadein_zero_still_works(self) -> None:
        """FadeIn(0) still completes immediately (no regression)."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            s.opacity = 0
            action = FadeIn(0)
            action.start(s)
            assert action.update(0.0) is True
            assert s.opacity == 255
        finally:
            g._teardown()

    def test_fadeout_normal_still_works(self) -> None:
        """FadeOut(1.0) still works (no regression)."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            s.opacity = 255
            action = FadeOut(1.0)
            action.start(s)
            assert action.update(0.5) is False  # still running
            assert action.update(0.5) is True   # done
            assert s.opacity == 0
        finally:
            g._teardown()

    def test_fadein_normal_still_works(self) -> None:
        """FadeIn(1.0) still works (no regression)."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            s = Sprite("sprites/test", position=(100, 100))
            s.opacity = 0
            action = FadeIn(1.0)
            action.start(s)
            assert action.update(0.5) is False
            assert action.update(0.5) is True
            assert s.opacity == 255
        finally:
            g._teardown()


# ===========================================================================
# F25: TextBox accepts NaN/Inf typewriter_speed
# ===========================================================================


class TestF25TextBoxTypewriterSpeedValidation:
    """TextBox must validate typewriter_speed is finite.

    BUG: TextBox.__init__ checks `if typewriter_speed <= 0` but NaN <= 0
    is False (IEEE 754), so NaN passes and is treated as a positive speed.
    After update(), _revealed_count becomes NaN. Then revealed_count property
    calls int(NaN) which raises ValueError — a crash during normal operation.
    Same for +Inf (int(Inf) raises OverflowError).
    """

    def test_nan_typewriter_speed_rejected(self) -> None:
        """NaN typewriter_speed should raise ValueError at init."""
        with pytest.raises(ValueError, match="typewriter_speed must be"):
            TextBox("Hello", typewriter_speed=float("nan"))

    def test_inf_typewriter_speed_rejected(self) -> None:
        """Inf typewriter_speed should raise ValueError at init."""
        with pytest.raises(ValueError, match="typewriter_speed must be"):
            TextBox("Hello", typewriter_speed=float("inf"))

    def test_negative_inf_typewriter_speed_rejected(self) -> None:
        """-Inf typewriter_speed should raise ValueError at init."""
        with pytest.raises(ValueError, match="typewriter_speed must be"):
            TextBox("Hello", typewriter_speed=float("-inf"))

    def test_zero_typewriter_speed_still_works(self) -> None:
        """typewriter_speed=0 means instant reveal (no regression)."""
        tb = TextBox("Hi", typewriter_speed=0)
        assert tb.is_complete is True
        assert tb.revealed_count == 2

    def test_negative_typewriter_speed_still_works(self) -> None:
        """typewriter_speed < 0 means instant reveal (no regression)."""
        tb = TextBox("Hi", typewriter_speed=-5)
        assert tb.is_complete is True
        assert tb.revealed_count == 2

    def test_normal_typewriter_speed_still_works(self) -> None:
        """Normal positive typewriter_speed still works (no regression)."""
        tb = TextBox("ABCDE", typewriter_speed=10)
        assert tb.revealed_count == 0
        tb.update(0.1)  # 10 * 0.1 = 1 char
        assert tb.revealed_count == 1
        tb.update(0.4)  # total = 5 chars
        assert tb.revealed_count == 5
        assert tb.is_complete is True
