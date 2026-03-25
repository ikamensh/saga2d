"""Stage 2 core-actions edge-case tests.

Probes seven categories of bad-input handling in the actions and Game API:
  1. Do() with non-callable fn
  2. Repeat() times parameter validation
  3. MoveTo with bad position tuples
  4. Game.tick() NaN/Inf dt propagation
  5. Game with invalid resolution
  6. PlayAnim with None anim_def
  7. Sequence/Parallel with non-Action children

Each test documents the observed behavior:
  - Proper validation (raises on construction) = GOOD
  - Silent acceptance that later crashes on use = BUG
  - Silent acceptance that poisons state = BUG

Findings summary (see detailed docstrings per test):
  BUGS FOUND:
    B1. Do() accepts non-callable fn at construction; crashes on update().
    B2. Repeat(times=<float>) silently accepts; runs wrong number of times.
    B3. Repeat(times=NaN) with a real sprite creates an un-completable action.
    B4. Repeat(times=inf) with a real sprite: is_finite=True but never finishes.
        Parallel hangs forever waiting for it.
    B5. Game.tick(dt=NaN) propagates NaN to scene.update() unchecked.
    B6. Game.tick(dt=inf) propagates inf to scene.update() unchecked.
    B7. Game.tick(dt=<negative>) propagates negative dt unchecked.
    B8. Game accepts zero/negative resolution without validation.
    B9. PlayAnim(None) silently accepts None; crashes on attribute access.
    B10. MoveTo silently accepts 3+-tuples, ignoring extra elements.

  GOOD BEHAVIOR:
    G1. MoveTo validates NaN/Inf positions and speeds at construction.
    G2. Sequence/Parallel validate children types at construction.
    G3. Repeat(times=0) and Repeat(times=-5) finish immediately (harmless).
    G4. MoveTo(scalar) and MoveTo(None) raise TypeError at construction.
"""

from __future__ import annotations

import math

import pytest

from saga2d import Game, Scene
from saga2d.actions import (
    Action,
    Delay,
    Do,
    MoveTo,
    Parallel,
    PlayAnim,
    Repeat,
    Sequence,
)


# =====================================================================
# Helpers
# =====================================================================


@pytest.fixture
def mock_game():
    """Fresh Game with mock backend.  Torn down after each test."""
    g = Game("test", backend="mock", resolution=(800, 600))
    yield g
    g._teardown()


class FakeSprite:
    """Minimal sprite stand-in for testing actions that need start(sprite)."""
    _x = 0.0
    _y = 0.0
    is_removed = False
    opacity = 255

    def stop_actions(self):
        pass

    def stop_animation(self):
        pass


class TrackingScene(Scene):
    """Scene that records every dt it receives in update()."""

    def __init__(self):
        super().__init__()
        self.dts: list[float] = []

    def update(self, dt: float) -> None:
        self.dts.append(dt)


# =====================================================================
# 1. Do() with non-callable fn
# =====================================================================


class TestDoNonCallable:
    """Do(fn) validates callability at construction time (FIXED).

    After fix F37: Do(None), Do(42), Do("string") all raise TypeError
    at construction time with a descriptive message.
    """

    def test_do_none_rejected_at_construction(self):
        """FIXED (F37): Do(None) raises TypeError at construction."""
        with pytest.raises(TypeError, match="callable"):
            Do(None)

    @pytest.mark.parametrize("bad_fn", [42, "string", 3.14, [], {}])
    def test_do_non_callable_rejected_at_construction(self, bad_fn):
        """FIXED (F37): Do(<non-callable>) raises TypeError at construction."""
        with pytest.raises(TypeError, match="callable"):
            Do(bad_fn)


# =====================================================================
# 2. Repeat() times parameter validation
# =====================================================================


class TestRepeatTimesValidation:
    """Repeat(action, times=X) — probing negative, zero, float, NaN, inf.

    Note: Repeat.start(None) short-circuits (_sprite is None -> _current=None
    -> update returns True immediately).  Tests that need actual Repeat
    behavior must pass a real (or fake) sprite to start().
    """

    def test_repeat_zero_times_finishes_immediately(self):
        """GOOD (G3): Repeat(delay, times=0) finishes immediately.
        start() detects times <= 0 and sets _current = None."""
        action = Repeat(Delay(0.1), times=0)
        action.start(FakeSprite())
        assert action.update(0.016) is True

    def test_repeat_negative_times_finishes_immediately(self):
        """GOOD (G3): Repeat(delay, times=-5) finishes immediately.
        start() treats negative the same as zero (times <= 0)."""
        action = Repeat(Delay(0.1), times=-5)
        action.start(FakeSprite())
        assert action.update(0.016) is True

    def test_repeat_float_times_rejected(self):
        """FIXED (F38): Repeat(delay, times=3.7) raises TypeError."""
        with pytest.raises(TypeError, match="int"):
            Repeat(Delay(0.0), times=3.7)

    def test_repeat_nan_times_rejected(self):
        """FIXED (F38): Repeat(delay, times=NaN) raises TypeError."""
        with pytest.raises(TypeError, match="int"):
            Repeat(Delay(0.0), times=float("nan"))

    def test_repeat_inf_times_rejected(self):
        """FIXED (F38): Repeat(delay, times=inf) raises TypeError."""
        with pytest.raises(TypeError, match="int"):
            Repeat(Delay(0.0), times=float("inf"))


# =====================================================================
# 3. MoveTo with bad position tuples
# =====================================================================


class TestMoveToBadPosition:
    """MoveTo validates positions at construction. Mostly GOOD, with caveats.

    MoveTo uses index-based access (position[0], position[1]) rather than
    unpacking (x, y = position), so:
    - 1-tuple raises IndexError (no position[1])
    - 3+-tuple silently works (ignores extra elements) -- a minor bug
    - NaN/Inf positions are properly validated
    """

    def test_moveto_1tuple_raises_indexerror(self):
        """MoveTo((100,), speed=50) raises IndexError on position[1]."""
        with pytest.raises(IndexError):
            MoveTo((100,), speed=50)

    def test_moveto_scalar_raises(self):
        """GOOD (G4): MoveTo(100, speed=50) raises TypeError."""
        with pytest.raises(TypeError):
            MoveTo(100, speed=50)

    def test_moveto_nan_x_raises(self):
        """GOOD (G1): MoveTo with NaN x-coordinate raises ValueError."""
        with pytest.raises(ValueError, match="finite"):
            MoveTo((float("nan"), 100), speed=50)

    def test_moveto_nan_y_raises(self):
        """GOOD (G1): MoveTo with NaN y-coordinate raises ValueError."""
        with pytest.raises(ValueError, match="finite"):
            MoveTo((100, float("nan")), speed=50)

    def test_moveto_inf_x_raises(self):
        """GOOD (G1): MoveTo with Inf x-coordinate raises ValueError."""
        with pytest.raises(ValueError, match="finite"):
            MoveTo((float("inf"), 100), speed=50)

    def test_moveto_inf_y_raises(self):
        """GOOD (G1): MoveTo with Inf y-coordinate raises ValueError."""
        with pytest.raises(ValueError, match="finite"):
            MoveTo((100, float("inf")), speed=50)

    def test_moveto_neg_inf_raises(self):
        """GOOD (G1): MoveTo with -Inf coordinate raises ValueError."""
        with pytest.raises(ValueError, match="finite"):
            MoveTo((float("-inf"), 100), speed=50)

    def test_moveto_zero_speed_raises(self):
        """GOOD (G1): MoveTo with speed=0 raises ValueError."""
        with pytest.raises(ValueError, match="speed must be > 0"):
            MoveTo((100, 200), speed=0)

    def test_moveto_negative_speed_raises(self):
        """GOOD (G1): MoveTo with negative speed raises ValueError."""
        with pytest.raises(ValueError, match="speed must be > 0"):
            MoveTo((100, 200), speed=-50)

    def test_moveto_nan_speed_raises(self):
        """GOOD (G1): MoveTo with NaN speed raises ValueError."""
        with pytest.raises(ValueError, match="finite"):
            MoveTo((100, 200), speed=float("nan"))

    def test_moveto_inf_speed_raises(self):
        """GOOD (G1): MoveTo with Inf speed raises ValueError."""
        with pytest.raises(ValueError, match="finite"):
            MoveTo((100, 200), speed=float("inf"))

    def test_moveto_3tuple_silently_ignores_extra(self):
        """BUG (B10): MoveTo((x, y, z), speed=50) silently ignores z.

        Because MoveTo uses position[0] and position[1] (indexing) rather
        than x, y = position (unpacking), extra elements are silently
        discarded. This could mask bugs where a caller passes a 3D vector."""
        action = MoveTo((100, 200, 300), speed=50)
        assert action._target_x == 100.0
        assert action._target_y == 200.0
        # Extra element silently ignored -- not validated

    def test_moveto_none_position_raises(self):
        """GOOD (G4): MoveTo(None, speed=50) raises TypeError."""
        with pytest.raises(TypeError):
            MoveTo(None, speed=50)


# =====================================================================
# 4. Game.tick() NaN/Inf dt propagation
# =====================================================================


class TestTickDtPropagation:
    """Game.tick(dt=NaN/Inf/negative) — FIXED (F40): all are now rejected
    with ValueError at the top of tick() before reaching scene.update().
    """

    def test_nan_dt_rejected(self, mock_game):
        """FIXED (F40): NaN dt raises ValueError."""
        scene = TrackingScene()
        mock_game.push(scene)
        with pytest.raises(ValueError, match="finite"):
            mock_game.tick(dt=float("nan"))
        assert len(scene.dts) == 0, "Scene should not have received NaN dt"

    def test_inf_dt_rejected(self, mock_game):
        """FIXED (F40): Inf dt raises ValueError."""
        scene = TrackingScene()
        mock_game.push(scene)
        with pytest.raises(ValueError, match="finite"):
            mock_game.tick(dt=float("inf"))
        assert len(scene.dts) == 0, "Scene should not have received Inf dt"

    def test_negative_dt_rejected(self, mock_game):
        """FIXED (F40): Negative dt raises ValueError."""
        scene = TrackingScene()
        mock_game.push(scene)
        with pytest.raises(ValueError, match="negative"):
            mock_game.tick(dt=-0.016)
        assert len(scene.dts) == 0, "Scene should not have received negative dt"

    def test_zero_dt_is_valid(self, mock_game):
        """GOOD: zero dt is a legitimate value (paused frame)."""
        scene = TrackingScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.0)
        assert len(scene.dts) == 1
        assert scene.dts[0] == 0.0

    def test_normal_dt_works(self, mock_game):
        """Baseline: normal dt passes through correctly."""
        scene = TrackingScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)
        assert len(scene.dts) == 1
        assert scene.dts[0] == pytest.approx(0.016)


# =====================================================================
# 5. Game with invalid resolution
# =====================================================================


class TestGameInvalidResolution:
    """Game(resolution=...) — zero, negative, and extreme values.

    BUG (B8): Game.__init__ performs no validation on resolution.
    Zero and negative dimensions are silently accepted.
    """

    def test_zero_resolution_accepted(self):
        """BUG (B8): Game accepts (0, 0) resolution without validation."""
        g = Game("test", backend="mock", resolution=(0, 0))
        assert g._resolution == (0, 0)
        g._teardown()

    def test_negative_width_accepted(self):
        """BUG (B8): Game accepts negative width without validation."""
        g = Game("test", backend="mock", resolution=(-800, 600))
        assert g._resolution == (-800, 600)
        g._teardown()

    def test_negative_height_accepted(self):
        """BUG (B8): Game accepts negative height without validation."""
        g = Game("test", backend="mock", resolution=(800, -600))
        assert g._resolution == (800, -600)
        g._teardown()

    def test_both_negative_accepted(self):
        """BUG (B8): Game accepts both-negative resolution."""
        g = Game("test", backend="mock", resolution=(-800, -600))
        assert g._resolution == (-800, -600)
        g._teardown()

    def test_normal_resolution_works(self):
        """Baseline: standard resolution works fine."""
        g = Game("test", backend="mock", resolution=(1920, 1080))
        assert g._resolution == (1920, 1080)
        g._teardown()


# =====================================================================
# 6. PlayAnim with None anim_def
# =====================================================================


class TestPlayAnimNone:
    """PlayAnim(None) — FIXED (F39): validates anim_def at construction.

    After fix: PlayAnim(None) and PlayAnim("string") raise TypeError
    at construction time with a descriptive message.
    """

    def test_playanim_none_rejected(self):
        """FIXED (F39): PlayAnim(None) raises TypeError at construction."""
        with pytest.raises(TypeError, match="AnimationDef"):
            PlayAnim(None)

    def test_playanim_string_rejected(self):
        """FIXED (F39): PlayAnim("walk") raises TypeError at construction."""
        with pytest.raises(TypeError, match="AnimationDef"):
            PlayAnim("walk")


# =====================================================================
# 7. Sequence/Parallel with non-Action children
# =====================================================================


class TestSequenceParallelNonActionChildren:
    """Sequence and Parallel validate children at construction.

    GOOD (G2): Both classes check isinstance(action, Action) for every
    child and raise TypeError with a descriptive message. This is
    exemplary input validation.
    """

    def test_sequence_string_raises(self):
        """GOOD (G2): Sequence("not_an_action") raises TypeError."""
        with pytest.raises(TypeError, match="Sequence child 0.*str.*expected Action"):
            Sequence("not_an_action")

    def test_sequence_int_raises(self):
        """GOOD (G2): Sequence(42) raises TypeError."""
        with pytest.raises(TypeError, match="Sequence child 0.*int.*expected Action"):
            Sequence(42)

    def test_sequence_none_raises(self):
        """GOOD (G2): Sequence(None) raises TypeError."""
        with pytest.raises(TypeError, match="Sequence child 0.*NoneType.*expected Action"):
            Sequence(None)

    def test_parallel_int_raises(self):
        """GOOD (G2): Parallel(42) raises TypeError."""
        with pytest.raises(TypeError, match="Parallel child 0.*int.*expected Action"):
            Parallel(42)

    def test_parallel_string_raises(self):
        """GOOD (G2): Parallel("not_an_action") raises TypeError."""
        with pytest.raises(TypeError, match="Parallel child 0.*str.*expected Action"):
            Parallel("not_an_action")

    def test_parallel_none_raises(self):
        """GOOD (G2): Parallel(None) raises TypeError."""
        with pytest.raises(TypeError, match="Parallel child 0.*NoneType.*expected Action"):
            Parallel(None)

    def test_sequence_mixed_valid_invalid_raises(self):
        """GOOD (G2): Sequence(valid, invalid) catches the invalid child."""
        with pytest.raises(TypeError, match="Sequence child 1.*int.*expected Action"):
            Sequence(Delay(0.1), 42)

    def test_parallel_mixed_valid_invalid_raises(self):
        """GOOD (G2): Parallel(valid, invalid) catches the invalid child."""
        with pytest.raises(TypeError, match="Parallel child 1.*str.*expected Action"):
            Parallel(Delay(0.1), "bad")

    def test_sequence_empty_succeeds(self):
        """GOOD: Sequence() with no children is valid (finishes immediately)."""
        seq = Sequence()
        seq.start(None)
        assert seq.update(0.016) is True

    def test_parallel_empty_succeeds(self):
        """GOOD: Parallel() with no children is valid (finishes immediately)."""
        par = Parallel()
        par.start(None)
        assert par.update(0.016) is True
