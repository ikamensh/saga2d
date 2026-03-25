"""Stage 5 regression tests for bugs F36–F41.

Each test class targets one confirmed bug:
  - Tests FAIL before the fix is applied
  - Tests PASS after the fix is applied

F36: ParticleEmitter speed/direction NaN/Inf not validated
F37: Do() accepts non-callable fn
F38: Repeat(times=NaN/Inf) creates zombie/hanging actions
F39: PlayAnim(None) silently accepted, crashes on use
F40: Game.tick(dt=NaN/Inf) propagates to scene.update()
F41: ProgressBar value=NaN shows as full bar
"""

from __future__ import annotations

import math

import pytest

from saga2d import Game, Scene
from saga2d.actions import Delay, Do, PlayAnim, Repeat
from saga2d.rendering.particles import ParticleEmitter
from saga2d.ui.widgets import ProgressBar


# ===================================================================
# F36: ParticleEmitter speed/direction NaN/Inf validation
# ===================================================================


class TestF36ParticleEmitterSpeedDirectionValidation:
    """ParticleEmitter should reject NaN/Inf in speed and direction tuples,
    just like it already does for lifetime."""

    @pytest.fixture(autouse=True)
    def _setup_game(self):
        self.game = Game("F36Test", backend="mock")
        self.game.push(Scene())
        self.game.tick(0)
        yield
        self.game._teardown()

    def test_speed_nan_min_rejected(self):
        """NaN in speed[0] should raise ValueError."""
        with pytest.raises(ValueError, match="speed.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(float('nan'), 100),
                direction=(0, 360),
                lifetime=(0.1, 0.5),
            )

    def test_speed_nan_max_rejected(self):
        """NaN in speed[1] should raise ValueError."""
        with pytest.raises(ValueError, match="speed.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(50, float('nan')),
                direction=(0, 360),
                lifetime=(0.1, 0.5),
            )

    def test_speed_inf_rejected(self):
        """Inf in speed should raise ValueError."""
        with pytest.raises(ValueError, match="speed.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(float('inf'), 100),
                direction=(0, 360),
                lifetime=(0.1, 0.5),
            )

    def test_speed_neg_inf_rejected(self):
        """-Inf in speed should raise ValueError."""
        with pytest.raises(ValueError, match="speed.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(float('-inf'), 100),
                direction=(0, 360),
                lifetime=(0.1, 0.5),
            )

    def test_direction_nan_rejected(self):
        """NaN in direction should raise ValueError."""
        with pytest.raises(ValueError, match="direction.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(50, 100),
                direction=(float('nan'), 360),
                lifetime=(0.1, 0.5),
            )

    def test_direction_inf_rejected(self):
        """Inf in direction should raise ValueError."""
        with pytest.raises(ValueError, match="direction.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(50, 100),
                direction=(float('inf'), 360),
                lifetime=(0.1, 0.5),
            )

    def test_valid_speed_direction_still_works(self):
        """Normal values should still be accepted."""
        emitter = ParticleEmitter(
            "sprites/knight", (0, 0),
            speed=(50, 200),
            direction=(0, 360),
            lifetime=(0.1, 0.5),
        )
        emitter.burst(3)
        assert len(emitter._particles) == 3
        emitter.remove()


# ===================================================================
# F37: Do() accepts non-callable fn
# ===================================================================


class TestF37DoCallableValidation:
    """Do() should validate fn is callable at construction time."""

    def test_do_none_rejected(self):
        """Do(None) should raise TypeError."""
        with pytest.raises(TypeError, match="callable"):
            Do(None)

    def test_do_int_rejected(self):
        """Do(42) should raise TypeError."""
        with pytest.raises(TypeError, match="callable"):
            Do(42)

    def test_do_string_rejected(self):
        """Do('string') should raise TypeError."""
        with pytest.raises(TypeError, match="callable"):
            Do("string")

    def test_do_valid_lambda_works(self):
        """Do(lambda: None) should still work."""
        action = Do(lambda: None)
        action.start(None)
        assert action.update(0.016) is True


# ===================================================================
# F38: Repeat(times=NaN/Inf) creates zombie/hanging actions
# ===================================================================


class TestF38RepeatTimesValidation:
    """Repeat(times=NaN) and Repeat(times=Inf) should be rejected."""

    def test_repeat_nan_times_rejected(self):
        """Repeat(times=NaN) should raise ValueError."""
        with pytest.raises((ValueError, TypeError), match="(finite|int)"):
            Repeat(Delay(0.1), times=float('nan'))

    def test_repeat_inf_times_rejected(self):
        """Repeat(times=Inf) should raise ValueError."""
        with pytest.raises((ValueError, TypeError), match="(finite|int)"):
            Repeat(Delay(0.1), times=float('inf'))

    def test_repeat_neg_inf_times_rejected(self):
        """Repeat(times=-Inf) should raise ValueError."""
        with pytest.raises((ValueError, TypeError), match="(finite|int)"):
            Repeat(Delay(0.1), times=float('-inf'))

    def test_repeat_float_times_rejected(self):
        """Repeat(times=3.7) should raise TypeError (int expected)."""
        with pytest.raises((ValueError, TypeError), match="(int|integer)"):
            Repeat(Delay(0.1), times=3.7)

    def test_repeat_valid_int_works(self):
        """Repeat(times=3) should still work."""
        action = Repeat(Delay(0.0), times=3)
        assert action.is_finite is True

    def test_repeat_none_works(self):
        """Repeat(times=None) means infinite, should still work."""
        action = Repeat(Delay(0.0), times=None)
        assert action.is_finite is False


# ===================================================================
# F39: PlayAnim(None) silently accepted
# ===================================================================


class TestF39PlayAnimValidation:
    """PlayAnim should validate anim_def at construction time."""

    def test_playanim_none_rejected(self):
        """PlayAnim(None) should raise TypeError."""
        with pytest.raises(TypeError, match="AnimationDef"):
            PlayAnim(None)

    def test_playanim_string_rejected(self):
        """PlayAnim('walk') should raise TypeError."""
        with pytest.raises(TypeError, match="AnimationDef"):
            PlayAnim("walk")


# ===================================================================
# F40: Game.tick(dt=NaN/Inf) propagation
# ===================================================================


class TestF40GameTickDtValidation:
    """Game.tick() should validate dt is finite and non-negative."""

    def test_tick_nan_dt_rejected(self):
        """Game.tick(dt=NaN) should raise ValueError."""
        g = Game("test", backend="mock")
        g.push(Scene())
        with pytest.raises(ValueError, match="dt.*finite"):
            g.tick(dt=float('nan'))
        g._teardown()

    def test_tick_inf_dt_rejected(self):
        """Game.tick(dt=Inf) should raise ValueError."""
        g = Game("test", backend="mock")
        g.push(Scene())
        with pytest.raises(ValueError, match="dt.*finite"):
            g.tick(dt=float('inf'))
        g._teardown()

    def test_tick_negative_dt_rejected(self):
        """Game.tick(dt=-0.016) should raise ValueError."""
        g = Game("test", backend="mock")
        g.push(Scene())
        with pytest.raises(ValueError, match="dt.*negative"):
            g.tick(dt=-0.016)
        g._teardown()

    def test_tick_zero_dt_valid(self):
        """Game.tick(dt=0) is valid (paused frame)."""
        g = Game("test", backend="mock")
        g.push(Scene())
        g.tick(dt=0.0)  # Should not raise
        g._teardown()

    def test_tick_normal_dt_valid(self):
        """Game.tick(dt=0.016) works as expected."""
        g = Game("test", backend="mock")
        g.push(Scene())
        g.tick(dt=0.016)  # Should not raise
        g._teardown()


# ===================================================================
# F41: ProgressBar value=NaN shows full bar
# ===================================================================


class TestF41ProgressBarNaNValidation:
    """ProgressBar.value setter should reject NaN."""

    def test_value_nan_rejected(self):
        """Setting value=NaN should raise ValueError."""
        g = Game("test", backend="mock")
        scene = Scene()
        g.push(scene)
        g.tick(0)

        bar = ProgressBar(value=50, max_value=100, width=200, height=24)
        scene.ui.add(bar)
        g.tick(0)

        with pytest.raises(ValueError, match="finite"):
            bar.value = float('nan')
        g._teardown()

    def test_value_inf_rejected(self):
        """Setting value=Inf should raise ValueError."""
        g = Game("test", backend="mock")
        scene = Scene()
        g.push(scene)
        g.tick(0)

        bar = ProgressBar(value=50, max_value=100, width=200, height=24)
        scene.ui.add(bar)
        g.tick(0)

        with pytest.raises(ValueError, match="finite"):
            bar.value = float('inf')
        g._teardown()

    def test_value_normal_works(self):
        """Setting normal value still works."""
        g = Game("test", backend="mock")
        scene = Scene()
        g.push(scene)
        g.tick(0)

        bar = ProgressBar(value=50, max_value=100, width=200, height=24)
        scene.ui.add(bar)
        g.tick(0)

        bar.value = 75
        assert bar.value == 75
        assert bar.fraction == 0.75
        g._teardown()

    def test_value_negative_works(self):
        """Negative values are valid (clamped in fraction)."""
        g = Game("test", backend="mock")
        scene = Scene()
        g.push(scene)
        g.tick(0)

        bar = ProgressBar(value=50, max_value=100, width=200, height=24)
        scene.ui.add(bar)
        g.tick(0)

        bar.value = -10  # Should not raise
        assert bar.value == -10
        assert bar.fraction == 0.0  # Clamped
        g._teardown()
