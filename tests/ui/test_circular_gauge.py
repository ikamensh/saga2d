"""Properties of the iter-40 :class:`CircularGauge` widget.

The gauge is the circular counterpart to :class:`ProgressBar` — same
reactive ``value`` / ``max_value`` pattern, but rendered as two
concentric discs. Properties we check:

*   ``fraction`` is clamped to ``[0, 1]`` and tracks ``value/max_value``
    through bound callables.
*   ``value`` / ``max_value`` are re-evaluated each frame when bound
    to a callable (same contract as :class:`ProgressBar`).
*   At the pixel level (via the mock-to-PIL renderer) an empty gauge
    has no fill pixels and a full gauge's centre pixel is the fill
    colour.
"""

from __future__ import annotations

import math

import pytest

from saga2d import (
    Anchor,
    CircularGauge,
    Game,
    Panel,
    Scene,
)
from saga2d.testing.mock_renderer import render_mock_scene


@pytest.fixture
def game():
    g = Game(
        "circular-gauge-test",
        resolution=(200, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _push(game: Game, scene: Scene) -> None:
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)


# ---------------------------------------------------------------------------
# Reactive contract — shared with ProgressBar
# ---------------------------------------------------------------------------


def test_fraction_tracks_callable(game: Game) -> None:
    state = {"hp": 7, "max": 10}
    gauge = CircularGauge(
        value=lambda: state["hp"], max_value=lambda: state["max"], radius=12,
    )

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[gauge]))

    _push(game, S())
    assert math.isclose(gauge.fraction, 0.7)

    state["hp"] = 3
    game.tick(dt=1 / 60)
    assert math.isclose(gauge.fraction, 0.3)


def test_fraction_clamped_to_0_1(game: Game) -> None:
    gauge = CircularGauge(value=50, max_value=10, radius=10)

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[gauge]))

    _push(game, S())
    assert gauge.fraction == 1.0

    gauge.value = -5.0
    assert gauge.fraction == 0.0


def test_zero_max_value_yields_zero_fraction(game: Game) -> None:
    gauge = CircularGauge(value=0, max_value=0, radius=10)

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[gauge]))

    _push(game, S())
    assert gauge.fraction == 0.0


def test_callable_returning_non_finite_raises() -> None:
    """Same NaN-guard as ProgressBar: a callable that returns non-finite
    surfaces a clear error instead of propagating garbage into the
    fraction arithmetic."""
    gauge = CircularGauge(
        value=lambda: float("nan"), max_value=lambda: 10, radius=10,
    )
    with pytest.raises(ValueError):
        _ = gauge.fraction


def test_non_positive_radius_is_rejected() -> None:
    with pytest.raises(ValueError):
        CircularGauge(value=0, max_value=1, radius=0)
    with pytest.raises(ValueError):
        CircularGauge(value=0, max_value=1, radius=-5)


def test_preferred_size_is_diameter_square(game: Game) -> None:
    gauge = CircularGauge(value=0, max_value=1, radius=14)

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[gauge]))

    _push(game, S())
    assert gauge.get_preferred_size() == (28, 28)


# ---------------------------------------------------------------------------
# Visual properties via the mock-to-PIL renderer (iter-38).
# Two concentric-disc primitives + clamp arithmetic = predictable output.
# ---------------------------------------------------------------------------


def test_full_gauge_centre_pixel_is_fill_color() -> None:
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (0, 0, 0, 255)

            def on_enter(self) -> None:
                self.ui.add(CircularGauge(
                    value=lambda: 10,
                    max_value=lambda: 10,
                    radius=20,
                    fill_color=(240, 130, 160, 255),
                    empty_color=(60, 30, 40, 255),
                    anchor=Anchor.CENTER,
                ))

        game._scene_stack.push(S())

    img = render_mock_scene(setup, resolution=(100, 100))
    # Centre of the 100x100 canvas — the gauge is anchored CENTER so
    # its centre is at (50, 50) (within a 40x40 bounding box).
    # Full gauge → inner disc at full radius → centre is fill colour.
    assert img.getpixel((50, 50)) == (240, 130, 160, 255)


def test_empty_gauge_centre_is_empty_color() -> None:
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (0, 0, 0, 255)

            def on_enter(self) -> None:
                self.ui.add(CircularGauge(
                    value=lambda: 0,
                    max_value=lambda: 10,
                    radius=20,
                    fill_color=(240, 130, 160, 255),
                    empty_color=(60, 30, 40, 255),
                    anchor=Anchor.CENTER,
                ))

        game._scene_stack.push(S())

    img = render_mock_scene(setup, resolution=(100, 100))
    # Empty gauge → no inner fill disc, the slot (empty_color) fills
    # the centre.
    assert img.getpixel((50, 50)) == (60, 30, 40, 255)


def test_half_full_inner_fill_is_smaller_than_radius() -> None:
    """A half-full gauge fills half its radius → the ring between
    fill_r and r is the empty colour, and the centre is the fill colour."""
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (0, 0, 0, 255)

            def on_enter(self) -> None:
                self.ui.add(CircularGauge(
                    value=lambda: 5,
                    max_value=lambda: 10,
                    radius=20,
                    fill_color=(240, 130, 160, 255),
                    empty_color=(60, 30, 40, 255),
                    anchor=Anchor.CENTER,
                ))

        game._scene_stack.push(S())

    img = render_mock_scene(setup, resolution=(100, 100))
    # Centre should be fill (half-radius inner disc still covers it).
    assert img.getpixel((50, 50)) == (240, 130, 160, 255)
    # A pixel 15 px from centre should be in the empty-colour ring
    # (fill_r = round(20 * 0.5) = 10, so 15 is outside the fill).
    assert img.getpixel((50 + 15, 50)) == (60, 30, 40, 255)


def test_gauge_draws_empty_slot_before_fill(game: Game) -> None:
    """Mock-backend invariant: an empty gauge still emits one circle
    (the slot). This matters for layout checks and snapshot regression
    tests that count draw ops per scene."""
    gauge = CircularGauge(value=0, max_value=10, radius=8)

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[gauge]))

        def draw(self) -> None:
            pass

    _push(game, S())
    # One frame → exactly one circle (the empty slot). No fill disc
    # since value == 0.
    assert len(game.backend.circles) == 1
    assert game.backend.circles[0]["radius"] == 8
