"""Screenshot regression tests for Stage 11 ColorSwap.

Run from the project root::

    pytest tests/screenshot/test_color_swap_screenshots.py -v

Requires pyglet (GPU context) and pre-generated assets
(``python generate_assets.py``).  Excluded from the normal ``pytest tests/``
run by ``collect_ignore`` in ``tests/conftest.py``.

Each test creates sprites with different ColorSwap or team_palette settings,
renders a frame, and compares against a golden screenshot.  Golden images are
auto-created on first run.

The tests use the knight sprite (solid blue, 48x64) and warrior_idle_01
(multi-color with blue tones) to demonstrate color replacement.
"""

from __future__ import annotations

import pytest

from easygame import Scene, Sprite
from easygame.rendering.color_swap import ColorSwap, register_palette
from easygame.rendering.layers import RenderLayer, SpriteAnchor

from tests.screenshot.harness import assert_screenshot, render_scene


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RESOLUTION = (320, 240)


class EmptyScene(Scene):
    """Minimal scene that keeps the scene stack non-empty."""
    pass


# ---------------------------------------------------------------------------
# 1. Same sprite, original vs red color swap — side by side
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_color_swap_knight_original_vs_red() -> None:
    """Two knight sprites side by side: original blue and swapped red.

    Left knight at (60, 120) uses the original blue sprite.
    Right knight at (200, 120) uses a ColorSwap that replaces the
    knight's blue (30, 144, 255) with red (220, 20, 60).

    Expected: two knight silhouettes — blue on the left, red on the right.
    """

    red_swap = ColorSwap(
        source_colors=[(30, 144, 255)],
        target_colors=[(220, 20, 60)],
    )

    def setup(game):
        game.push(EmptyScene())
        # Original blue knight
        Sprite(
            "sprites/knight",
            position=(60, 120),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
        )
        # Red-swapped knight
        Sprite(
            "sprites/knight",
            position=(200, 120),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
            color_swap=red_swap,
        )

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "color_swap_knight_blue_vs_red")


# ---------------------------------------------------------------------------
# 2. Same sprite, original vs green color swap — side by side
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_color_swap_knight_original_vs_green() -> None:
    """Two knight sprites: original blue and swapped green.

    Left knight at (60, 120) is the original.
    Right knight at (200, 120) replaces blue with green (34, 177, 76).

    Expected: blue knight on left, green knight on right.
    """

    green_swap = ColorSwap(
        source_colors=[(30, 144, 255)],
        target_colors=[(34, 177, 76)],
    )

    def setup(game):
        game.push(EmptyScene())
        Sprite(
            "sprites/knight",
            position=(60, 120),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
        )
        Sprite(
            "sprites/knight",
            position=(200, 120),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
            color_swap=green_swap,
        )

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "color_swap_knight_blue_vs_green")


# ---------------------------------------------------------------------------
# 3. Team palette via register_palette / team_palette param
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_color_swap_team_palette() -> None:
    """Three knights using team palettes: blue (original), red, and green.

    Registers 'red_team' and 'green_team' palettes, then creates three
    sprites using the team_palette parameter.  The original (no palette)
    is blue by default.

    Expected: three knight silhouettes in a row — blue, red, green.
    """

    register_palette("red_team", ColorSwap(
        source_colors=[(30, 144, 255)],
        target_colors=[(220, 20, 60)],
    ))
    register_palette("green_team", ColorSwap(
        source_colors=[(30, 144, 255)],
        target_colors=[(34, 177, 76)],
    ))

    def setup(game):
        game.push(EmptyScene())
        # Blue (original — no palette)
        Sprite(
            "sprites/knight",
            position=(40, 120),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
        )
        # Red team
        Sprite(
            "sprites/knight",
            position=(140, 120),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
            team_palette="red_team",
        )
        # Green team
        Sprite(
            "sprites/knight",
            position=(240, 120),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
            team_palette="green_team",
        )

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "color_swap_team_palette_three")


# ---------------------------------------------------------------------------
# 4. Warrior multi-color swap (more complex sprite)
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_color_swap_warrior_red_vs_orange() -> None:
    """Two warriors with different team colors.

    The warrior_idle_01 has blue tones: (30, 144, 255), (15, 80, 160),
    (80, 180, 255).  We swap all three to red tones (left) and orange
    tones (right).

    Expected: two warrior sprites with distinctly different color schemes.
    """

    red_warrior = ColorSwap(
        source_colors=[
            (30, 144, 255),
            (15, 80, 160),
            (80, 180, 255),
        ],
        target_colors=[
            (220, 20, 60),
            (140, 10, 30),
            (255, 80, 100),
        ],
    )

    orange_warrior = ColorSwap(
        source_colors=[
            (30, 144, 255),
            (15, 80, 160),
            (80, 180, 255),
        ],
        target_colors=[
            (255, 140, 0),
            (180, 90, 0),
            (255, 190, 80),
        ],
    )

    def setup(game):
        game.push(EmptyScene())
        Sprite(
            "sprites/warrior_idle_01",
            position=(80, 120),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
            color_swap=red_warrior,
        )
        Sprite(
            "sprites/warrior_idle_01",
            position=(200, 120),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
            color_swap=orange_warrior,
        )

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "color_swap_warrior_red_vs_orange")
