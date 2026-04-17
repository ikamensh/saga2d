"""Properties of :func:`saga2d.testing.plot_scene`.

plot_scene is the Keras ``plot_model`` analog — takes a scene setup
callback and returns/writes a labelled PNG schematic of the scene's
widget bounds. Useful for debugging layout and for documentation.

We verify:

*   The output PIL image matches the requested resolution.
*   A schematic rendering is NOT identical to the scene's mock-to-PIL
    render (different rendering modes produce different pixels).
*   Every UI widget with bounds gets an outline drawn in palette
    colours — at least one non-background pixel exists per widget
    bounds rectangle.
*   Writing to disk produces a file of the expected size.
*   "overlay" and "schematic" modes produce different output.
*   A no-op ``output_path=""`` returns the image without writing.
*   Calling without a scene raises a clear error.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from saga2d import Anchor, Game, Label, Scene
from saga2d.testing import plot_scene


def test_plot_scene_returns_requested_resolution() -> None:
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (10, 20, 30, 255)
        game._scene_stack.push(S())

    img = plot_scene(setup, "", resolution=(320, 240))
    assert img.size == (320, 240)
    assert img.mode == "RGBA"


def test_plot_scene_writes_output_file(tmp_path: Path) -> None:
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (10, 20, 30, 255)
        game._scene_stack.push(S())

    out = tmp_path / "schematic.png"
    plot_scene(setup, str(out), resolution=(200, 200))
    assert out.is_file()
    assert out.stat().st_size > 0


def test_plot_scene_empty_output_path_returns_image_without_writing(
    tmp_path: Path,
) -> None:
    """``output_path=""`` is a supported pattern: caller gets the image
    back without touching disk — useful for in-memory pipelines and
    tests that don't want filesystem side effects."""
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (0, 0, 0, 255)
        game._scene_stack.push(S())

    img = plot_scene(setup, "", resolution=(100, 100))
    assert img is not None
    # No files should have been written under tmp_path
    assert list(tmp_path.glob("*.png")) == []


def test_plot_scene_draws_outline_for_each_widget() -> None:
    """A scene with one Label should have at least one non-bg pixel
    near the label's expected position (the outline)."""
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (0, 0, 0, 255)

            def on_enter(self) -> None:
                self.ui.add(Label(
                    "Hi",
                    anchor=Anchor.TOP_LEFT, margin=10,
                ))

        game._scene_stack.push(S())

    img = plot_scene(setup, "", resolution=(200, 100), mode="schematic")
    # A non-black pixel near the top-left somewhere (outline of the
    # Label rectangle). We don't pinpoint exact coords — PIL text
    # metrics can vary — but *some* pixel in the top 40x40 region
    # should be non-black.
    non_bg_count = sum(
        1 for x in range(0, 40, 2)
        for y in range(0, 40, 2)
        if img.getpixel((x, y)) != (0, 0, 0, 255)
    )
    assert non_bg_count > 0, "expected outline pixels near Label bounds"


def test_plot_scene_schematic_and_overlay_produce_different_output() -> None:
    """Schematic mode uses a dimmed background + outlines; overlay
    mode draws the full mock-to-PIL render plus outlines. Two modes,
    two different pixel outputs."""
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (50, 50, 80, 255)

            def on_enter(self) -> None:
                self.ui.add(Label("x", anchor=Anchor.CENTER))

        game._scene_stack.push(S())

    schematic = plot_scene(setup, "", resolution=(100, 100), mode="schematic")
    overlay = plot_scene(setup, "", resolution=(100, 100), mode="overlay")
    # Different pixels somewhere.
    assert list(schematic.getdata()) != list(overlay.getdata())


def test_plot_scene_without_scene_raises() -> None:
    """If setup_fn forgets to push a scene, we should surface a clear
    error instead of silently producing a blank schematic."""
    def setup(game: Game) -> None:
        pass  # Never pushes anything.

    with pytest.raises(ValueError, match="no scene on the stack"):
        plot_scene(setup, "", resolution=(100, 100))


def test_plot_scene_is_deterministic_for_identical_input() -> None:
    """Two calls with the same setup produce pixel-identical output —
    the Keras-parallel property that snapshot tests rely on."""
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (30, 40, 50, 255)

            def on_enter(self) -> None:
                self.ui.add(Label("A", anchor=Anchor.TOP_LEFT, margin=5))
                self.ui.add(Label("B", anchor=Anchor.TOP_RIGHT, margin=5))

        game._scene_stack.push(S())

    img1 = plot_scene(setup, "", resolution=(200, 100))
    img2 = plot_scene(setup, "", resolution=(200, 100))
    assert list(img1.getdata()) == list(img2.getdata())


def test_plot_scene_depth_color_varies() -> None:
    """Nested widgets get different outline colours from the palette
    so hierarchy is visually distinguishable."""
    from saga2d import Panel
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (0, 0, 0, 255)

            def on_enter(self) -> None:
                # Two levels of nesting: UIRoot > Panel > Label.
                self.ui.add(Panel(children=[
                    Label("inside", anchor=Anchor.CENTER),
                ], anchor=Anchor.CENTER, width=100, height=40))

        game._scene_stack.push(S())

    img = plot_scene(setup, "", resolution=(200, 100), mode="schematic")
    # Collect all non-black pixel colours.
    pixels = set()
    for x in range(0, 200, 2):
        for y in range(0, 100, 2):
            pix = img.getpixel((x, y))
            if pix[:3] != (0, 0, 0):
                # Strip alpha for comparison.
                pixels.add(pix[:3])

    # UIRoot + Panel + Label = three palette colours expected.
    # PIL anti-aliasing can produce intermediate colors, so we just
    # require more than one distinct outline colour.
    assert len(pixels) > 1, "expected multiple palette colours for nested widgets"
