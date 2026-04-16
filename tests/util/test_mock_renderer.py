"""Properties of the iter-38 mock-to-PIL renderer.

The renderer's correctness is hard to assert pixel-perfectly (PIL
text rendering differs from pyglet), but coarse invariants can be
checked: image size, non-empty result, background-color pass-through,
image composition when a scene uses a sprite.
"""

from __future__ import annotations

import pytest

from saga2d import Anchor, Game, Label, Scene
from saga2d.testing.mock_renderer import render_mock_scene


def test_returns_image_of_requested_resolution() -> None:
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (10, 20, 30, 255)
        game._scene_stack.push(S())

    img = render_mock_scene(setup, resolution=(400, 300))
    assert img.size == (400, 300)
    assert img.mode == "RGBA"


def test_background_color_fills_canvas() -> None:
    """A scene with a background_color renders the canvas in that colour."""
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (200, 50, 60, 255)
        game._scene_stack.push(S())

    img = render_mock_scene(setup, resolution=(100, 100))
    # Every pixel should be the background colour (no other draws).
    sample = img.getpixel((50, 50))
    assert sample == (200, 50, 60, 255)


def test_scene_with_draw_rect_produces_rectangle() -> None:
    """A scene drawing a single rect produces a canvas with that rect's
    colour at the drawn location."""
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (0, 0, 0, 255)
            def draw(self) -> None:
                self.draw_rect(10, 10, 50, 50, (255, 0, 0, 255))
        game._scene_stack.push(S())

    img = render_mock_scene(setup, resolution=(100, 100))
    # Centre of the rect should be red.
    assert img.getpixel((35, 35)) == (255, 0, 0, 255)
    # Outside should be black (background).
    assert img.getpixel((80, 80)) == (0, 0, 0, 255)


def test_scene_with_draw_circle_produces_disc() -> None:
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (0, 0, 0, 255)
            def draw(self) -> None:
                self.draw_circle(50, 50, 20, (0, 255, 0, 255))
        game._scene_stack.push(S())

    img = render_mock_scene(setup, resolution=(100, 100))
    # Centre of the disc should be green.
    assert img.getpixel((50, 50)) == (0, 255, 0, 255)
    # Far corner should be background.
    assert img.getpixel((5, 5)) == (0, 0, 0, 255)


def test_scene_with_label_produces_some_foreground_pixels() -> None:
    """A scene with a single Label at CENTER should paint *some* pixels
    near the centre with the label's colour (not a tight pixel check —
    PIL's text metrics differ from pyglet's)."""
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (0, 0, 0, 255)
            def on_enter(self) -> None:
                self.ui.add(Label(
                    "HI",
                    anchor=Anchor.CENTER,
                    font_size=32,
                    text_color=(255, 255, 255, 255),
                ))
        game._scene_stack.push(S())

    img = render_mock_scene(setup, resolution=(200, 100))
    # Scan a horizontal band near the centre. At least a handful of
    # pixels should be non-black (the text strokes).
    non_black = sum(
        1 for x in range(0, 200, 2)
        for y in range(30, 70, 2)
        if img.getpixel((x, y)) != (0, 0, 0, 255)
    )
    assert non_black > 5, "expected some label pixels near centre"


def test_missing_sprite_path_is_skipped_silently() -> None:
    """Mock blits that reference a handle without a corresponding
    _loaded_images entry produce no output but also no crash."""
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (0, 0, 0, 255)
            def draw(self) -> None:
                # Fake an image blit with a handle the renderer can't
                # resolve to a file — the renderer should skip it.
                self.game._backend.draw_image(
                    "nonexistent-handle", 0, 0, 50, 50,
                )
        game._scene_stack.push(S())

    img = render_mock_scene(setup, resolution=(100, 100))
    assert img.size == (100, 100)


def test_render_is_deterministic_for_identical_input() -> None:
    """Two render_mock_scene calls with the same setup produce
    pixel-identical output — useful for snapshot-testing layouts."""
    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (30, 40, 50, 255)
            def draw(self) -> None:
                self.draw_rect(20, 20, 30, 30, (200, 100, 50, 255))
        game._scene_stack.push(S())

    img1 = render_mock_scene(setup, resolution=(100, 100))
    img2 = render_mock_scene(setup, resolution=(100, 100))
    assert list(img1.getdata()) == list(img2.getdata())
