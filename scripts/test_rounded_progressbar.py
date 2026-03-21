"""Test rounded ProgressBar functionality."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from saga2d import Game
from saga2d.backends.mock_backend import MockBackend
from saga2d.ui import ProgressBar


def test_rounded_progressbar() -> None:
    """Test that rounded ProgressBar draws circles and rects."""
    print("Testing rounded ProgressBar...")

    # Create a mock backend game
    game = Game("Test", backend="mock", resolution=(800, 600))
    backend = game._backend

    # Create a rounded progress bar
    bar = ProgressBar(
        value=65,
        max_value=100,
        width=200,
        height=24,
        rounded=True,
        bar_color=(0, 255, 0, 255),
        bg_color=(50, 50, 50, 255),
    )
    bar._game = game
    bar.compute_layout(100, 100, 200, 24)

    # Draw the bar
    backend.begin_frame()
    bar.on_draw()

    # Verify circles were drawn (rounded ends)
    assert len(backend.circles) > 0, "No circles drawn for rounded ProgressBar"
    print(f"✓ Drew {len(backend.circles)} circles for rounded ends")

    # Verify rectangles were drawn (center sections)
    assert len(backend.rects) > 0, "No rectangles drawn for rounded ProgressBar"
    print(f"✓ Drew {len(backend.rects)} rectangles for center sections")

    # Check that we have both background and fill elements
    bg_color = (50, 50, 50, 255)
    bar_color = (0, 255, 0, 255)

    bg_circles = [c for c in backend.circles if c["color"] == bg_color]
    bar_circles = [c for c in backend.circles if c["color"] == bar_color]

    print(f"  Background circles: {len(bg_circles)}")
    print(f"  Fill circles: {len(bar_circles)}")

    assert len(bg_circles) >= 2, "Should have at least 2 background circles (ends)"
    assert len(bar_circles) >= 2, "Should have at least 2 fill circles (ends)"

    print("✓ Rounded ProgressBar test PASSED\n")
    return game


def test_rectangular_progressbar() -> None:
    """Test that non-rounded ProgressBar only draws rects (no circles)."""
    print("Testing rectangular (non-rounded) ProgressBar...")

    game = Game("Test", backend="mock", resolution=(800, 600))
    backend = game._backend

    # Create a non-rounded progress bar
    bar = ProgressBar(
        value=65,
        max_value=100,
        width=200,
        height=24,
        rounded=False,  # Explicitly disable rounding
    )
    bar._game = game
    bar.compute_layout(100, 100, 200, 24)

    # Draw the bar
    backend.begin_frame()
    bar.on_draw()

    # Verify NO circles were drawn
    assert len(backend.circles) == 0, (
        f"Circles drawn for non-rounded bar: {backend.circles}"
    )
    print("✓ No circles drawn for non-rounded bar")

    # Verify rectangles were drawn
    assert len(backend.rects) == 2, (
        f"Expected 2 rects (bg + fill), got {len(backend.rects)}"
    )
    print("✓ Drew 2 rectangles (background + fill)")

    print("✓ Rectangular ProgressBar test PASSED\n")
    return game


def main() -> None:
    """Run all ProgressBar tests."""
    print("=" * 60)
    print("ProgressBar Rounded Feature Tests")
    print("=" * 60 + "\n")

    # Test 1
    game1 = test_rounded_progressbar()
    if game1:
        try:
            game1._teardown()
        except Exception:
            pass

    # Test 2
    game2 = test_rectangular_progressbar()
    if game2:
        try:
            game2._teardown()
        except Exception:
            pass

    print("=" * 60)
    print("All tests passed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
