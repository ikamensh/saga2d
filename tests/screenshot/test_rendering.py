"""Screenshot regression tests for sprite rendering.

Run from the project root::

    pytest tests/screenshot/test_rendering.py -v

These tests require pyglet (GPU context) and pre-generated assets
(``python generate_assets.py``).  They are excluded from the normal
``pytest tests/`` run by ``collect_ignore`` in ``tests/conftest.py``.
"""

from __future__ import annotations

import pytest

from easygame import AnimationDef, Scene, Sprite
from easygame.rendering.layers import RenderLayer, SpriteAnchor
from easygame.util.tween import Ease, tween

from tests.screenshot.harness import assert_screenshot, render_scene


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class EmptyScene(Scene):
    """Minimal scene that does nothing — just keeps the scene stack non-empty."""
    pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_static_sprites() -> None:
    """Place warrior-idle, tree, and crate at known positions; one frame.

    Uses 160x120 resolution so a 50px sprite shift produces >1% pixel
    difference and fails the default assert_screenshot threshold.
    """

    def setup(game):
        game.push(EmptyScene())

        # warrior_idle_01 at top-left area (64x64)
        Sprite(
            "sprites/warrior_idle_01",
            position=(20, 40),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
        )

        # tree at center (64x96)
        Sprite(
            "sprites/tree",
            position=(70, 10),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.OBJECTS,
        )

        # crate at bottom-right area (32x32)
        Sprite(
            "sprites/crate",
            position=(120, 88),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.OBJECTS,
        )

    image = render_scene(setup, tick_count=1, resolution=(160, 120))
    assert_screenshot(image, "static_sprites")


@pytest.mark.screenshot
def test_animated_sprite() -> None:
    """Play a warrior walk cycle and capture mid-animation.

    warrior_walk has 4 frames at 0.1s each.  Ticking 15 frames at 1/60s
    gives ~0.25s elapsed — enough to reach frame 3 (0-indexed: frame_02).
    """

    def setup(game):
        game.push(EmptyScene())

        sprite = Sprite(
            "sprites/warrior_idle_01",
            position=(128, 80),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
        )

        walk = AnimationDef(
            frames=[
                "sprites/warrior_walk_01",
                "sprites/warrior_walk_02",
                "sprites/warrior_walk_03",
                "sprites/warrior_walk_04",
            ],
            frame_duration=0.1,
            loop=True,
        )
        sprite.play(walk)

    # 15 ticks at 1/60 ≈ 0.25s → past frame_duration*2 = 0.20s → on frame 3
    image = render_scene(setup, tick_count=15, resolution=(320, 240))
    assert_screenshot(image, "animated_sprite")


@pytest.mark.screenshot
def test_tweened_sprite() -> None:
    """Tween a skeleton from x=10 to x=260 over 1s; capture at the midpoint.

    30 ticks at 1/60 = 0.5s elapsed.  With linear easing over 1.0s duration,
    the sprite should be at x ≈ 135 (midpoint of 10..260).
    """

    def setup(game):
        game.push(EmptyScene())

        sprite = Sprite(
            "sprites/skeleton_idle_01",
            position=(10, 100),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
        )

        tween(
            sprite, "x",
            from_val=10.0,
            to_val=260.0,
            duration=1.0,
            ease=Ease.LINEAR,
        )

    # 30 ticks × (1/60)s = 0.5s → halfway through the 1.0s tween
    image = render_scene(setup, tick_count=30, resolution=(320, 240))
    assert_screenshot(image, "tweened_sprite")
