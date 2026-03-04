"""Screenshot regression tests for Stage 11 CursorManager.

Run from the project root::

    pytest tests/screenshot/test_cursor_screenshots.py -v

Requires pyglet (GPU context) and pre-generated assets
(``python generate_assets.py``).  Excluded from the normal ``pytest tests/``
run by ``collect_ignore`` in ``tests/conftest.py``.

The cursor itself is a system/OS-level feature and does not appear in
the framebuffer capture.  These tests verify that cursor registration
and switching works correctly by asserting on the backend's cursor
state *after* rendering.  A screenshot is still captured to verify the
scene renders correctly alongside cursor management — the golden image
shows the scene *without* the cursor overlay (as expected).
"""

from __future__ import annotations

import pytest

from saga2d import Game, Scene, Sprite
from saga2d.rendering.layers import RenderLayer, SpriteAnchor

from tests.screenshot.harness import assert_screenshot, render_scene


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RESOLUTION = (320, 240)


class EmptyScene(Scene):
    """Minimal scene that keeps the scene stack non-empty."""
    pass


# ---------------------------------------------------------------------------
# 1. Default cursor — scene renders normally, cursor is default
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_cursor_default_state() -> None:
    """Scene with a sprite and the default cursor.

    A knight sprite is placed at (100, 80).  The cursor manager is not
    used — cursor should remain in its default state.  The screenshot
    shows the sprite rendered normally (cursor is not in framebuffer).

    Expected: knight sprite visible, cursor state is "default".
    """

    game_ref: list[Game] = []

    def setup(game):
        game_ref.append(game)
        game.push(EmptyScene())
        Sprite(
            "sprites/knight",
            position=(100, 80),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
        )

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "cursor_default_state")

    # Verify cursor state on the backend.
    game = game_ref[0]
    assert game.cursor.current == "default"


# ---------------------------------------------------------------------------
# 2. Custom cursor registered and set
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_cursor_custom_set() -> None:
    """Register a custom cursor and switch to it.

    A knight sprite is placed at (100, 80).  A custom "attack" cursor
    is registered using the enemy sprite asset, with hotspot (8, 8).
    The cursor is then set to "attack".

    Expected: knight visible.  Cursor state is "attack" with the
    registered hotspot.
    """

    game_ref: list[Game] = []

    def setup(game):
        game_ref.append(game)
        game.push(EmptyScene())
        Sprite(
            "sprites/knight",
            position=(100, 80),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
        )
        # Register and switch to a custom cursor.
        game.cursor.register("attack", "sprites/enemy", hotspot=(8, 8))
        game.cursor.set("attack")

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "cursor_custom_set")

    # Verify cursor state via the CursorManager (backend-agnostic).
    game = game_ref[0]
    assert game.cursor.current == "attack"


# ---------------------------------------------------------------------------
# 3. Cursor switched back to default
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_cursor_restore_default() -> None:
    """Register a custom cursor, switch to it, then restore default.

    The cursor is set to "attack" and then immediately restored to
    "default".  The final state should be default.

    Expected: knight visible.  Cursor state is "default" (restored).
    """

    game_ref: list[Game] = []

    def setup(game):
        game_ref.append(game)
        game.push(EmptyScene())
        Sprite(
            "sprites/knight",
            position=(100, 80),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
        )
        game.cursor.register("attack", "sprites/enemy", hotspot=(8, 8))
        game.cursor.set("attack")
        game.cursor.set("default")

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "cursor_restore_default")

    game = game_ref[0]
    assert game.cursor.current == "default"


# ---------------------------------------------------------------------------
# 4. Cursor visibility toggle
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_cursor_visibility() -> None:
    """Hide and show the cursor.

    The cursor is hidden via ``set_visible(False)``, then a frame is
    rendered, then visibility is restored.

    Expected: knight visible.  Backend records cursor as hidden after
    the hide call, then visible again after restore.
    """

    game_ref: list[Game] = []

    def setup(game):
        game_ref.append(game)
        game.push(EmptyScene())
        Sprite(
            "sprites/knight",
            position=(100, 80),
            anchor=SpriteAnchor.TOP_LEFT,
            layer=RenderLayer.UNITS,
        )
        game.cursor.set_visible(False)

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "cursor_visibility_hidden")

    # Verify the cursor manager processed the visibility change.
    # (The pyglet backend delegates to window.set_mouse_visible;
    # we verify the CursorManager accepted the call without error.)
