"""Visualize draw_circle results using PIL.

Since we're in a headless environment, this script uses the mock backend
to record circle draw calls, then renders them with PIL for visual verification.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Add project root to Python path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from saga2d.backends.mock_backend import MockBackend


def render_circles_with_pil(
    backend: MockBackend, width: int, height: int
) -> Image.Image:
    """Render recorded circles to a PIL image."""
    img = Image.new("RGBA", (width, height), (30, 30, 40, 255))  # Dark background
    draw = ImageDraw.Draw(img)

    for circle in backend.circles:
        x = circle["x"]
        y = circle["y"]
        radius = circle["radius"]
        color = circle["color"]
        opacity = circle["opacity"]

        # Apply opacity to alpha channel
        r, g, b, a = color
        final_alpha = int(a * opacity)
        final_color = (r, g, b, final_alpha)

        # Draw circle (PIL uses bounding box)
        bbox = [
            x - radius,
            y - radius,
            x + radius,
            y + radius,
        ]
        draw.ellipse(bbox, fill=final_color)

    return img


def main() -> None:
    """Create and visualize various circle drawing tests."""
    print("Visualizing draw_circle results...")

    backend = MockBackend(logical_width=800, logical_height=600)
    backend.begin_frame()

    # Test 1: Basic solid colors in a grid
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

    for i, color in enumerate(colors):
        row = i // 4
        col = i % 4
        x = 120 + col * 160
        y = 100 + row * 120
        backend.draw_circle(x, y, 50, color)

    # Test 2: Large semi-transparent white circle (overlay)
    backend.draw_circle(400, 250, 150, (255, 255, 255, 255), opacity=0.2)

    # Test 3: Opacity variations
    for i in range(10):
        opacity = 0.1 + i * 0.1
        x = 100 + i * 70
        y = 380
        backend.draw_circle(x, y, 30, (100, 200, 255, 255), opacity=opacity)

    # Test 4: Size variations
    for i in range(8):
        radius = 10 + i * 8
        x = 120 + i * 80
        y = 500
        backend.draw_circle(x, y, radius, (255, 200, 100, 255))

    # Test 5: Overlapping circles (blending test)
    backend.draw_circle(650, 480, 60, (255, 0, 0, 255), opacity=0.5)
    backend.draw_circle(700, 480, 60, (0, 255, 0, 255), opacity=0.5)
    backend.draw_circle(675, 530, 60, (0, 0, 255, 255), opacity=0.5)

    print(f"Recorded {len(backend.circles)} circles")

    # Render to image
    img = render_circles_with_pil(backend, 800, 600)

    # Save image
    output_path = _PROJECT_ROOT / "test_draw_circle_visualization.png"
    img.save(output_path)
    print(f"✓ Visualization saved to {output_path}")

    # Display circle statistics
    print("\nCircle Statistics:")
    print(f"  Total circles: {len(backend.circles)}")
    print(
        f"  Circles with opacity < 1.0: {sum(1 for c in backend.circles if c['opacity'] < 1.0)}"
    )
    print(
        f"  Circles with custom segments: {sum(1 for c in backend.circles if c['segments'] is not None)}"
    )

    # Find min/max radius
    radii = [c["radius"] for c in backend.circles]
    print(f"  Radius range: {min(radii)} - {max(radii)} pixels")


if __name__ == "__main__":
    main()
