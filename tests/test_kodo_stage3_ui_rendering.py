"""Stage 3 UI rendering edge-case tests.

Tests NaN/Inf/negative edge cases in:
  1. ParticleEmitter speed/direction with NaN/Inf
  2. ParticleEmitter burst(NaN), burst(-5), burst(0)
  3. ProgressBar NaN/Inf/negative value
  4. DataTable negative/zero row_height
  5. Grid zero cell_size
  6. Scene.add_sprite(None)
  7. ColorSwap with empty lists

Each test documents whether the observed behavior is a bug or expected.
"""

from __future__ import annotations

import math
import random
from typing import Any

import pytest

from saga2d import Game, Scene
from saga2d.rendering.color_swap import ColorSwap
from saga2d.rendering.particles import ParticleEmitter
from saga2d.ui.widgets import DataTable, Grid, ProgressBar


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def game():
    """Fresh Game with mock backend, torn down after test."""
    g = Game("Stage3UITest", resolution=(800, 600), backend="mock")
    yield g
    g._teardown()


@pytest.fixture
def game_with_scene(game):
    """Game + pushed scene for sprite/particle tests."""
    s = Scene()
    game.push(s)
    game.tick(0)  # apply deferred push
    return game, s


# ===================================================================
# 1. ParticleEmitter speed/direction NaN/Inf
# ===================================================================


class TestParticleEmitterSpeedDirectionNaN:
    """FIXED (F36): ParticleEmitter now validates speed and direction tuples
    for NaN/Inf, just like lifetime. All non-finite values are rejected
    at construction time with ValueError.
    """

    def test_speed_nan_rejected(self, game_with_scene):
        """FIXED: NaN in speed is now rejected."""
        game, scene = game_with_scene
        with pytest.raises(ValueError, match="speed.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(float('nan'), 100),
                direction=(0, 360),
                lifetime=(0.1, 0.5),
            )

    def test_speed_inf_rejected(self, game_with_scene):
        """FIXED: Inf in speed is now rejected."""
        game, scene = game_with_scene
        with pytest.raises(ValueError, match="speed.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(float('inf'), 100),
                direction=(0, 360),
                lifetime=(0.1, 0.5),
            )

    def test_direction_nan_rejected(self, game_with_scene):
        """FIXED: NaN in direction is now rejected."""
        game, scene = game_with_scene
        with pytest.raises(ValueError, match="direction.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(100, 200),
                direction=(float('nan'), 360),
                lifetime=(0.1, 0.5),
            )

    def test_speed_neg_inf_rejected(self, game_with_scene):
        """FIXED: Neg-Inf in speed is now rejected."""
        game, scene = game_with_scene
        with pytest.raises(ValueError, match="speed.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(float('-inf'), 100),
                direction=(0, 360),
                lifetime=(0.1, 0.5),
            )

    def test_direction_inf_rejected(self, game_with_scene):
        """FIXED: Inf in direction is now rejected."""
        game, scene = game_with_scene
        with pytest.raises(ValueError, match="direction.*finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(100, 200),
                direction=(float('inf'), 360),
                lifetime=(0.1, 0.5),
            )

    def test_lifetime_nan_still_rejected(self, game_with_scene):
        """Lifetime NaN continues to be correctly validated."""
        game, scene = game_with_scene
        with pytest.raises(ValueError, match="lifetime values must be finite"):
            ParticleEmitter(
                "sprites/knight", (0, 0),
                speed=(50, 100),
                direction=(0, 360),
                lifetime=(float('nan'), 0.5),
            )


# ===================================================================
# 2. ParticleEmitter burst(NaN), burst(-5), burst(0)
# ===================================================================


class TestParticleEmitterBurstEdge:
    """Tests for burst() with NaN, negative, and zero counts."""

    def test_burst_nan_count(self, game_with_scene):
        """burst(NaN) — NaN is not an int, range(NaN) raises TypeError.

        The code does `if n <= 0: return` — NaN <= 0 is False (IEEE 754),
        so the guard doesn't catch it. Then range(NaN) raises TypeError.

        VERDICT: BUG — NaN count should be validated with a clear ValueError,
        not crash with TypeError from range().
        """
        game, scene = game_with_scene
        emitter = ParticleEmitter(
            "sprites/knight", (0, 0),
            speed=(50, 100), direction=(0, 360), lifetime=(0.1, 0.5),
        )
        with pytest.raises((TypeError, ValueError)):
            emitter.burst(float('nan'))
        emitter.remove()

    def test_burst_negative_count(self, game_with_scene):
        """burst(-5) — the guard `n <= 0` returns early, no particles spawned.

        VERDICT: Expected behavior — negative count is silently ignored.
        """
        game, scene = game_with_scene
        emitter = ParticleEmitter(
            "sprites/knight", (0, 0),
            speed=(50, 100), direction=(0, 360), lifetime=(0.1, 0.5),
        )
        emitter.burst(-5)
        assert len(emitter._particles) == 0, "Negative burst should produce 0 particles"
        emitter.remove()

    def test_burst_zero_count(self, game_with_scene):
        """burst(0) — the guard `n <= 0` returns early, no particles spawned.

        VERDICT: Expected behavior — zero count produces no particles.
        """
        game, scene = game_with_scene
        emitter = ParticleEmitter(
            "sprites/knight", (0, 0),
            speed=(50, 100), direction=(0, 360), lifetime=(0.1, 0.5),
        )
        emitter.burst(0)
        assert len(emitter._particles) == 0, "Zero burst should produce 0 particles"
        emitter.remove()

    def test_burst_nan_passes_guard_check(self, game_with_scene):
        """NaN <= 0 is False (IEEE 754), so burst(NaN) passes the guard check.

        This demonstrates the subtle IEEE 754 issue: NaN comparisons with
        any number return False.

        VERDICT: BUG (minor) — the error message is confusing. Should validate
        count as finite positive integer upfront.
        """
        game, scene = game_with_scene
        emitter = ParticleEmitter(
            "sprites/knight", (0, 0),
            speed=(50, 100), direction=(0, 360), lifetime=(0.1, 0.5),
        )
        # Verify the IEEE 754 property
        assert not (float('nan') <= 0), "NaN <= 0 should be False"
        # So range(NaN) is reached, which raises TypeError
        with pytest.raises(TypeError):
            emitter.burst(float('nan'))
        emitter.remove()


# ===================================================================
# 3. ProgressBar NaN/Inf/negative value
# ===================================================================


class TestProgressBarEdgeValues:
    """ProgressBar.value setter does NO validation. NaN/Inf/negative values
    are accepted silently.

    For NaN: the `fraction` property does `max(0.0, min(1.0, NaN / 100))`.
    Due to Python's min/max behavior with NaN:
      - NaN / 100 = NaN
      - min(1.0, NaN) = 1.0 (Python returns the first arg when NaN is involved)
      - max(0.0, 1.0) = 1.0
    So NaN value produces fraction=1.0 (FULL bar), which is WRONG — a NaN
    value should not display as full.

    VERDICT: BUG — NaN value silently shows a full bar instead of raising
    an error or showing empty.
    """

    def test_value_nan_rejected(self, game):
        """FIXED (F41): NaN value is now rejected with ValueError."""
        scene = Scene()
        game.push(scene)
        game.tick(0)

        bar = ProgressBar(value=50, max_value=100, width=200, height=24)
        scene.ui.add(bar)
        game.tick(0)

        with pytest.raises(ValueError, match="finite"):
            bar.value = float('nan')

    def test_value_inf_rejected(self, game):
        """FIXED (F41): Inf value is now rejected with ValueError."""
        scene = Scene()
        game.push(scene)
        game.tick(0)

        bar = ProgressBar(value=50, max_value=100, width=200, height=24)
        scene.ui.add(bar)
        game.tick(0)

        with pytest.raises(ValueError, match="finite"):
            bar.value = float('inf')

    def test_value_negative(self, game):
        """Negative value produces fraction clamped to 0.0.

        VERDICT: Expected behavior — max(0.0, ...) handles negative values.
        The fraction clamp works correctly for negatives.
        """
        scene = Scene()
        game.push(scene)
        game.tick(0)

        bar = ProgressBar(value=50, max_value=100, width=200, height=24)
        scene.ui.add(bar)
        game.tick(0)

        bar.value = -100
        frac = bar.fraction
        assert frac == 0.0, f"Expected fraction 0.0 from negative value, got {frac}"

    def test_value_neg_inf_rejected(self, game):
        """FIXED (F41): Negative infinity is now rejected with ValueError."""
        scene = Scene()
        game.push(scene)
        game.tick(0)

        bar = ProgressBar(value=50, max_value=100, width=200, height=24)
        scene.ui.add(bar)
        game.tick(0)

        with pytest.raises(ValueError, match="finite"):
            bar.value = float('-inf')


# ===================================================================
# 4. DataTable negative/zero row_height
# ===================================================================


class TestDataTableRowHeight:
    """DataTable does NOT validate row_height in __init__. Negative or zero
    row_height is accepted silently.

    - row_height=0: The click handler has `if self._row_height <= 0: return True`,
      preventing division by zero. get_preferred_size returns height = header_height
      (rows contribute 0 each). Drawing may produce overlapping rows at same y.

    - row_height=-10: get_preferred_size returns header_height + rows * (-10),
      which can go negative. Click handler returns True (guard catches it).
      Drawing will draw rows at decreasing y, going above the header.

    VERDICT: BUG — negative/zero row_height should be rejected in __init__.
    """

    def test_negative_row_height_accepted(self, game):
        """Negative row_height is silently accepted — this is a bug."""
        scene = Scene()
        game.push(scene)
        game.tick(0)

        table = DataTable(columns=["A", "B"], row_height=-10)
        scene.ui.add(table)
        game.tick(0)

        assert table.row_height == -10, "Negative row_height should be stored as-is"

        # Preferred size can go negative
        w, h = table.get_preferred_size()
        # With 0 rows: h = header_height(32) + 0 * (-10) = 32
        assert h == 32, f"Expected h=32 with 0 rows, got {h}"

        # Add some rows — preferred height shrinks below header
        table.add_row(["1", "2"])
        table.add_row(["3", "4"])
        w2, h2 = table.get_preferred_size()
        # h = 32 + 2 * (-10) = 12 — absurd but accepted
        assert h2 == 12, f"Expected h=12 with 2 rows at row_height=-10, got {h2}"

    def test_zero_row_height_accepted(self, game):
        """Zero row_height is silently accepted — this is a bug."""
        scene = Scene()
        game.push(scene)
        game.tick(0)

        table = DataTable(columns=["A", "B"], row_height=0)
        scene.ui.add(table)
        game.tick(0)

        assert table.row_height == 0, "Zero row_height should be stored"
        # All rows contribute 0 height
        table.add_row(["1", "2"])
        table.add_row(["3", "4"])
        w, h = table.get_preferred_size()
        # h = 32 + 2 * 0 = 32
        assert h == 32, f"Expected h=32, got {h}"

    def test_zero_row_height_click_guard(self, game):
        """The click handler guards `if self._row_height <= 0: return True`
        to prevent ZeroDivisionError. This guard works, but the constructor
        should still reject invalid values.

        Note: on_event only returns True if hit_test passes. Without proper
        layout bounds, the click coordinates may not hit the table. We verify
        the guard by checking the code path directly.
        """
        scene = Scene()
        game.push(scene)
        game.tick(0)

        table = DataTable(columns=["A", "B"], row_height=0, width=200, height=100)
        table.add_row(["1", "2"])
        scene.ui.add(table)
        game.tick(0)  # layout computes bounds

        from saga2d.input import InputEvent
        # Simulate a click within the table's computed bounds
        evt = InputEvent(
            type="click",
            x=table._computed_x + 10,
            y=table._computed_y + 50,
            button="left",
        )
        result = table.on_event(evt)
        # The guard `if self._row_height <= 0: return True` catches this
        assert result is True, "Click on row_height=0 table should be consumed"


# ===================================================================
# 5. Grid zero cell_size
# ===================================================================


class TestGridZeroCellSize:
    """Grid accepts cell_size=(0,0) silently. Layout math still works
    (0*col = 0), but all cells overlap at the same position.

    VERDICT: BUG — zero cell size should be rejected or warned about.
    """

    def test_zero_cell_size_accepted(self, game):
        """Zero cell_size is silently accepted."""
        scene = Scene()
        game.push(scene)
        game.tick(0)

        grid = Grid(columns=3, rows=3, cell_size=(0, 0))
        scene.ui.add(grid)
        game.tick(0)

        assert grid.cell_size == (0, 0), "Zero cell_size should be stored"

    def test_zero_cell_size_preferred_size(self, game):
        """Preferred size with zero cells = just spacing + padding."""
        scene = Scene()
        game.push(scene)
        game.tick(0)

        grid = Grid(columns=3, rows=3, cell_size=(0, 0), spacing=4)
        scene.ui.add(grid)
        game.tick(0)

        w, h = grid.get_preferred_size()
        # w = 3*0 + 2*4 + 2*padding, h = 3*0 + 2*4 + 2*padding
        # With default theme padding (let's just check it's non-negative)
        assert w >= 0, f"Width should be >= 0, got {w}"
        assert h >= 0, f"Height should be >= 0, got {h}"

    def test_zero_cell_size_set_cell(self, game):
        """Setting cells in a zero-cell-size grid should not crash."""
        scene = Scene()
        game.push(scene)
        game.tick(0)

        grid = Grid(columns=3, rows=3, cell_size=(0, 0))
        scene.ui.add(grid)
        game.tick(0)

        # Create a simple child component
        from saga2d.ui.component import Component
        child = Component(width=10, height=10)
        grid.set_cell(0, 0, child)

        # Layout should not crash
        game.tick(0)


# ===================================================================
# 6. Scene.add_sprite(None)
# ===================================================================


class TestSceneAddSpriteNone:
    """Scene.add_sprite(None) — the method calls `sprite.is_removed` on None,
    which raises AttributeError.

    VERDICT: BUG — should raise TypeError/ValueError with a clear message,
    or at minimum check for None before accessing attributes.
    """

    def test_add_sprite_none_raises(self, game):
        """add_sprite(None) should raise, not pass silently."""
        scene = Scene()
        game.push(scene)
        game.tick(0)

        with pytest.raises((AttributeError, TypeError, ValueError)):
            scene.add_sprite(None)


# ===================================================================
# 7. ColorSwap with empty lists
# ===================================================================


class TestColorSwapEmptyLists:
    """ColorSwap with empty source_colors=[] and target_colors=[] is accepted.
    The lengths match (0 == 0), so no ValueError.

    The `apply()` method builds an empty color_map dict — no pixels match,
    so the image is returned unchanged. The `cache_key()` returns an empty
    tuple.

    VERDICT: Expected behavior — empty swap is a valid no-op identity mapping.
    """

    def test_empty_lists_accepted(self):
        """Empty lists create a valid ColorSwap (no-op)."""
        swap = ColorSwap(source_colors=[], target_colors=[])
        assert swap.source_colors == []
        assert swap.target_colors == []

    def test_empty_cache_key(self):
        """cache_key() returns empty tuple for empty swap."""
        swap = ColorSwap(source_colors=[], target_colors=[])
        key = swap.cache_key()
        assert key == (), f"Expected empty tuple, got {key}"

    def test_mismatched_lengths_rejected(self):
        """Mismatched lengths still raise ValueError."""
        with pytest.raises(ValueError, match="same length"):
            ColorSwap(
                source_colors=[(255, 0, 0)],
                target_colors=[],
            )


# ===================================================================
# Summary / Documentation
# ===================================================================
#
# BUGS FOUND:
#
# 1. ParticleEmitter speed/direction NaN/Inf NOT validated (5 sub-cases)
#    - speed=(NaN, ...) silently accepted, produces NaN velocity on burst
#    - speed=(Inf, ...) silently accepted
#    - direction=(NaN, ...) silently accepted, produces NaN velocity on burst
#    Lifetime IS validated, but speed and direction are not.
#    Severity: MEDIUM — corrupts particle positions over time.
#
# 2. ParticleEmitter burst(NaN) crashes with confusing TypeError
#    - NaN passes the `n <= 0` guard (IEEE 754: NaN <= 0 is False)
#    - Then range(NaN) raises TypeError
#    Severity: LOW — crashes, but with a Python error not a silent bug.
#
# 3. ProgressBar value=NaN shows full bar (fraction=1.0)
#    - Python's min(1.0, NaN) = 1.0, so fraction chain produces 1.0
#    - A NaN health bar silently shows as 100% full — misleading!
#    Severity: MEDIUM — silent wrong display rather than error/empty.
#
# 4. DataTable negative/zero row_height silently accepted
#    - row_height=-10 causes preferred height to shrink below header
#    - row_height=0 collapses all rows to zero height
#    - Click handler IS guarded (no crash), but layout is nonsensical.
#    Severity: LOW — no crash, but visual corruption.
#
# 5. Grid cell_size=(0,0) silently accepted
#    - All cells overlap at same position
#    - No crash, but useless layout.
#    Severity: LOW — no crash, but useless.
#
# 6. Scene.add_sprite(None) raises AttributeError
#    - Should raise TypeError/ValueError with descriptive message
#    Severity: LOW — crashes, but with confusing error.
#
# EXPECTED BEHAVIOR (NOT BUGS):
#
# 7. ColorSwap([], []) — valid no-op identity mapping
# 8. burst(-5) and burst(0) — silently return with 0 particles
# 9. ProgressBar value=-100 — fraction clamped to 0.0
# 10. ProgressBar value=Inf — fraction clamped to 1.0 (reasonable)
