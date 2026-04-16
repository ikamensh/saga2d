"""Properties of ``ring_positions`` / ``grid_positions`` / ``line_positions``.

These helpers are pure math; the right tests aren't "did it output [...]"
but "do the geometric properties hold?" — equal spacing, correct radius,
count, etc. Cheap and survives refactoring.
"""

from __future__ import annotations

import math

import pytest

from saga2d import grid_positions, line_positions, ring_positions


# -- ring_positions ---------------------------------------------------------


def test_ring_positions_count_matches_request() -> None:
    """Exactly N positions are returned."""
    assert len(ring_positions(8, (0, 0), 100)) == 8
    assert len(ring_positions(1, (0, 0), 100)) == 1
    assert len(ring_positions(0, (0, 0), 100)) == 0


def test_ring_positions_all_on_circle() -> None:
    """Every returned point is ``radius`` away from the centre."""
    center = (400.0, 300.0)
    radius = 150.0
    for p in ring_positions(16, center, radius):
        dx, dy = p[0] - center[0], p[1] - center[1]
        assert math.isclose(math.hypot(dx, dy), radius, rel_tol=1e-9)


def test_ring_positions_even_angular_spacing() -> None:
    """Consecutive positions subtend equal angles at the centre."""
    center = (0.0, 0.0)
    points = ring_positions(12, center, 100.0)
    angles = [math.atan2(p[1], p[0]) for p in points]
    # Normalise into [0, 2π) then sort ascending for gap calculation.
    normed = sorted(a % (2 * math.pi) for a in angles)
    gaps = [normed[i + 1] - normed[i] for i in range(len(normed) - 1)]
    gaps.append(2 * math.pi - normed[-1] + normed[0])
    target = 2 * math.pi / 12
    for g in gaps:
        assert math.isclose(g, target, abs_tol=1e-9)


def test_ring_positions_start_angle_puts_first_at_12_oclock() -> None:
    """Default ``start_angle=-π/2`` places index 0 directly above centre."""
    (x, y) = ring_positions(8, (100.0, 100.0), 50.0)[0]
    assert math.isclose(x, 100.0, abs_tol=1e-9)
    assert math.isclose(y, 100.0 - 50.0, abs_tol=1e-9)


def test_ring_positions_partial_arc_includes_both_ends() -> None:
    """A 180° arc over 3 points includes start *and* end exactly."""
    pts = ring_positions(
        3,
        (0.0, 0.0),
        10.0,
        start_angle=0.0,
        arc=math.pi,
    )
    # start (angle 0) and end (angle π) should sit at +x and -x on the circle.
    assert math.isclose(pts[0][0], 10.0, abs_tol=1e-9)
    assert math.isclose(pts[-1][0], -10.0, abs_tol=1e-9)


# -- grid_positions ---------------------------------------------------------


def test_grid_positions_count() -> None:
    assert len(grid_positions(12, columns=4, cell=(50, 50))) == 12
    assert grid_positions(0, columns=4, cell=(50, 50)) == []


def test_grid_positions_row_major_order() -> None:
    """Second row starts below the first, not after it on the same row."""
    pts = grid_positions(6, columns=3, cell=(10, 20), origin=(0, 0))
    assert pts[:3] == [(0, 0), (10, 0), (20, 0)]
    assert pts[3:] == [(0, 20), (10, 20), (20, 20)]


def test_grid_positions_rejects_zero_columns() -> None:
    with pytest.raises(ValueError):
        grid_positions(5, columns=0, cell=(10, 10))


# -- line_positions ---------------------------------------------------------


def test_line_positions_endpoints_are_exact() -> None:
    pts = line_positions(4, start=(0.0, 0.0), end=(30.0, 60.0))
    assert pts[0] == (0.0, 0.0)
    assert pts[-1] == (30.0, 60.0)


def test_line_positions_single_point_is_midpoint() -> None:
    """One point on a line = midpoint (stable, no division by zero)."""
    assert line_positions(1, start=(0.0, 0.0), end=(10.0, 20.0)) == [(5.0, 10.0)]


def test_line_positions_even_spacing() -> None:
    pts = line_positions(5, start=(0.0, 0.0), end=(8.0, 0.0))
    xs = [p[0] for p in pts]
    gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    assert all(math.isclose(g, 2.0, abs_tol=1e-9) for g in gaps)
