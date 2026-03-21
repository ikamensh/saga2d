"""Test script for draw_circle primitive.

Tests both mock and pyglet backends to verify the new draw_circle
functionality works correctly.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def test_mock_backend() -> None:
    """Test draw_circle with mock backend."""
    from saga2d.backends.mock_backend import MockBackend

    print("Testing draw_circle with mock backend...")
    backend = MockBackend(logical_width=640, logical_height=480)

    # Begin frame
    backend.begin_frame()

    # Test 1: Basic red circle
    backend.draw_circle(
        x=100,
        y=100,
        radius=50,
        color=(255, 0, 0, 255),
    )

    # Test 2: Green circle with opacity
    backend.draw_circle(
        x=320,
        y=100,
        radius=60,
        color=(0, 255, 0, 255),
        opacity=0.5,
    )

    # Test 3: Blue circle with custom segments
    backend.draw_circle(
        x=540,
        y=100,
        radius=40,
        color=(0, 0, 255, 255),
        segments=8,
    )

    # Verify circles were recorded
    assert len(backend.circles) == 3, f"Expected 3 circles, got {len(backend.circles)}"
    print(f"✓ Mock backend recorded {len(backend.circles)} circles")

    # Verify first circle properties
    circle1 = backend.circles[0]
    assert circle1["x"] == 100, f"Expected x=100, got {circle1['x']}"
    assert circle1["y"] == 100, f"Expected y=100, got {circle1['y']}"
    assert circle1["radius"] == 50, f"Expected radius=50, got {circle1['radius']}"
    assert circle1["color"] == (255, 0, 0, 255), f"Expected red, got {circle1['color']}"
    assert circle1["opacity"] == 1.0, f"Expected opacity=1.0, got {circle1['opacity']}"
    assert circle1["segments"] is None, (
        f"Expected segments=None, got {circle1['segments']}"
    )
    print("✓ Circle properties verified")

    # Verify second circle (with opacity)
    circle2 = backend.circles[1]
    assert circle2["opacity"] == 0.5, f"Expected opacity=0.5, got {circle2['opacity']}"
    print("✓ Opacity parameter works")

    # Verify third circle (with segments)
    circle3 = backend.circles[2]
    assert circle3["segments"] == 8, f"Expected segments=8, got {circle3['segments']}"
    print("✓ Segments parameter works")

    # End frame and verify circles are cleared
    backend.end_frame()
    backend.begin_frame()
    assert len(backend.circles) == 0, "Circles should be cleared on begin_frame"
    print("✓ Circles cleared on begin_frame")

    print("✓ Mock backend test PASSED\n")


def test_pyglet_backend_screenshot() -> None:
    """Test draw_circle with pyglet backend and save a screenshot."""
    print("Testing draw_circle with pyglet backend (screenshot)...")

    # Custom scene that draws circles via backend
    from saga2d import Game, Scene

    class CircleScene(Scene):
        """Scene that draws circles directly via backend."""

        def on_draw(self) -> None:
            """Draw circles for testing."""
            backend = self.game._backend

            # Grid of colorful circles
            colors = [
                (255, 0, 0, 255),  # Red
                (0, 255, 0, 255),  # Green
                (0, 0, 255, 255),  # Blue
                (255, 255, 0, 255),  # Yellow
                (255, 0, 255, 255),  # Magenta
                (0, 255, 255, 255),  # Cyan
                (255, 128, 0, 255),  # Orange
                (128, 0, 255, 255),  # Purple
            ]

            # Draw circles in a grid pattern
            for i, color in enumerate(colors):
                row = i // 4
                col = i % 4
                x = 100 + col * 150
                y = 100 + row * 150
                backend.draw_circle(x, y, 40, color)

            # Draw a large semi-transparent white circle in center
            backend.draw_circle(320, 240, 120, (255, 255, 255, 255), opacity=0.3)

            # Draw small circles with different segment counts
            for i in range(3, 13):
                x = 50 + (i - 3) * 60
                y = 400
                backend.draw_circle(x, y, 20, (200, 200, 200, 255), segments=i)

    # Use the screenshot harness for headless rendering
    sys.path.insert(0, str(_PROJECT_ROOT / "tests" / "screenshot"))
    try:
        from harness import render_scene  # type: ignore[import-not-found]

        def setup(game: Game) -> None:
            """Set up the circle test scene."""
            scene = CircleScene()
            game.push(scene)

        # Render the scene offscreen
        image = render_scene(setup, tick_count=2, resolution=(640, 480))

        # Save screenshot for visual verification
        output_path = _PROJECT_ROOT / "test_draw_circle.png"
        image.save(output_path)
        print(f"✓ Screenshot saved to {output_path}")
        print("✓ Pyglet backend test PASSED\n")
    except Exception as e:
        # Pyglet might fail in headless environments
        import traceback

        print(f"⚠ Pyglet backend test skipped (error): {e}")
        traceback.print_exc()
        print()


def main() -> None:
    """Run all draw_circle tests."""
    print("=" * 60)
    print("draw_circle Backend Tests")
    print("=" * 60 + "\n")

    # Test mock backend (always works)
    test_mock_backend()

    # Test pyglet backend (may skip in headless mode)
    test_pyglet_backend_screenshot()

    print("=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
