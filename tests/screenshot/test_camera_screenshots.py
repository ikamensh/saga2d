"""Screenshot regression tests for the Camera system.

Run from the project root::

    pytest tests/screenshot/test_camera_screenshots.py -v

Requires pyglet (GPU context).  Excluded from the normal ``pytest tests/``
run by ``collect_ignore`` in ``tests/conftest.py``.

Each test creates a scene with distinctly-coloured sprites placed across a
large world, then captures a screenshot with the camera at a specific
position.  The camera offset shifts which sprites appear on screen and
where.

Test sprites (40x40 solid colour squares) are generated on the fly via
Pillow if they don't already exist in ``assets/images/sprites/``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from easygame import Scene, Sprite
from easygame.rendering.camera import Camera
from easygame.rendering.layers import RenderLayer, SpriteAnchor

from tests.screenshot.harness import assert_screenshot, render_scene


# ---------------------------------------------------------------------------
# Sprite asset generation — deterministic 40x40 coloured squares
# ---------------------------------------------------------------------------

_ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets" / "images" / "sprites"

# (filename, RGBA colour)
_CAMERA_SPRITES = [
    ("cam_red.png",    (220, 40, 40, 255)),
    ("cam_blue.png",   (40, 80, 220, 255)),
    ("cam_green.png",  (40, 180, 40, 255)),
    ("cam_yellow.png", (220, 200, 40, 255)),
]

_SIZE = 40  # px


def _ensure_camera_sprites() -> None:
    """Create the coloured square PNGs if they don't exist."""
    _ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    for filename, colour in _CAMERA_SPRITES:
        path = _ASSETS_DIR / filename
        if not path.exists():
            img = Image.new("RGBA", (_SIZE, _SIZE), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img, "RGBA")
            draw.rectangle((0, 0, _SIZE - 1, _SIZE - 1), fill=colour)
            img.save(path)


# ---------------------------------------------------------------------------
# Scene helper — places sprites at fixed world positions in a 1000x1000 world
# ---------------------------------------------------------------------------

# World layout (TOP_LEFT anchor, so position = draw corner):
#
#   Red    @ (  30,  20)  — near top-left
#   Blue   @ ( 200, 140)  — upper-centre area
#   Green  @ ( 140,  80)  — between red and blue
#   Yellow @ ( 280,  30)  — near top-right
#
# Resolution for all tests: 320x240  (small, matches existing screenshot style)
# The 40x40 sprites against a 320x240 viewport produce meaningful pixel diffs
# when the camera moves.

_RESOLUTION = (320, 240)


class CameraWorldScene(Scene):
    """Scene that creates four coloured sprites and sets up a camera.

    Subclass or set ``camera_setup`` before ``on_enter`` to customise the
    camera position for each test.
    """

    def __init__(self, camera_setup=None):
        self._camera_setup = camera_setup

    def on_enter(self) -> None:
        self.camera = Camera(
            _RESOLUTION,
            world_bounds=(0, 0, 1000, 1000),
        )

        Sprite(
            "sprites/cam_red", position=(30, 20),
            anchor=SpriteAnchor.TOP_LEFT, layer=RenderLayer.UNITS,
        )
        Sprite(
            "sprites/cam_green", position=(140, 80),
            anchor=SpriteAnchor.TOP_LEFT, layer=RenderLayer.UNITS,
        )
        Sprite(
            "sprites/cam_blue", position=(200, 140),
            anchor=SpriteAnchor.TOP_LEFT, layer=RenderLayer.UNITS,
        )
        Sprite(
            "sprites/cam_yellow", position=(280, 30),
            anchor=SpriteAnchor.TOP_LEFT, layer=RenderLayer.UNITS,
        )

        if self._camera_setup is not None:
            self._camera_setup(self.camera)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_camera_at_origin() -> None:
    """Camera at default (0, 0) — all four sprites visible near top-left.

    Red at (30,20), Green at (140,80), Blue at (200,140), Yellow at (280,30).
    All fit within the 320x240 viewport since all positions + 40px are < 320/240.
    """
    _ensure_camera_sprites()

    def setup(game):
        game.push(CameraWorldScene(
            camera_setup=lambda cam: None,  # keep at (0, 0)
        ))

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "camera_at_origin")


@pytest.mark.screenshot
def test_camera_centered_on_world() -> None:
    """Camera centered on (200, 150) — viewport top-left at (40, 30).

    All sprites shift left by 40 and up by 30 compared to origin view:
      Red    @ screen (30-40, 20-30)  = (-10, -10) → partially visible
      Green  @ screen (140-40, 80-30) = (100, 50)  → fully visible
      Blue   @ screen (200-40, 140-30)= (160, 110) → fully visible
      Yellow @ screen (280-40, 30-30) = (240, 0)   → fully visible
    """
    _ensure_camera_sprites()

    def setup(game):
        game.push(CameraWorldScene(
            camera_setup=lambda cam: cam.center_on(200, 150),
        ))

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "camera_centered_on_world")


@pytest.mark.screenshot
def test_camera_scrolled_right() -> None:
    """Camera scrolled right so viewport starts at x=250 — Red and Green off-screen.

    Viewport top-left at (250, 0):
      Red    @ screen (30-250, 20-0)  = (-220, 20)  → off-screen (culled)
      Green  @ screen (140-250, 80-0) = (-110, 80)  → off-screen (culled)
      Blue   @ screen (200-250, 140-0)= (-50, 140)  → partially visible (right 40-50=-10 px? No: -50+40=-10 < 0 → culled)
      Yellow @ screen (280-250, 30-0) = (30, 30)    → fully visible

    Only Yellow should be visible — a single yellow square near (30, 30).
    """
    _ensure_camera_sprites()

    def setup(game):
        game.push(CameraWorldScene(
            camera_setup=lambda cam: cam.scroll(250, 0),
        ))

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "camera_scrolled_right")


@pytest.mark.screenshot
def test_camera_scrolled_down() -> None:
    """Camera scrolled down so viewport starts at y=120 — Red and Yellow above viewport.

    Viewport top-left at (0, 120):
      Red    @ screen (30, 20-120)  = (30, -100) → off-screen (culled)
      Green  @ screen (140, 80-120) = (140, -40) → partially visible (bottom edge at -40+40=0 → exactly off)
      Blue   @ screen (200, 140-120)= (200, 20)  → fully visible
      Yellow @ screen (280, 30-120) = (280, -90) → off-screen (culled)

    Blue should be the only clearly visible sprite at screen (200, 20).
    """
    _ensure_camera_sprites()

    def setup(game):
        game.push(CameraWorldScene(
            camera_setup=lambda cam: cam.scroll(0, 120),
        ))

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "camera_scrolled_down")
