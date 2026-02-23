"""Screenshot regression tests for Stage 12 Drag-and-Drop.

Run from the project root::

    pytest tests/screenshot/test_drag_drop_screenshots.py -v

Requires pyglet (GPU context).  Excluded from the normal ``pytest tests/``
run by ``collect_ignore`` in ``tests/conftest.py``.

Each test builds a grid of coloured panels, programmatically initiates a
drag session via :meth:`DragManager._start_drag`, moves the ghost to a
target position, and renders a frame.  The ghost overlay (semi-transparent
rect) and drop target highlight (green/red) are drawn by ``_UIRoot.draw()``
during the capture.

Golden images are auto-created on first run.
"""

from __future__ import annotations

import pytest

from easygame import Game, Scene
from easygame.ui import Anchor, Layout, Panel, Style

from tests.screenshot.harness import assert_screenshot, render_scene

_RESOLUTION = (480, 360)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _color_panel(
    color: tuple[int, int, int, int],
    w: int = 80,
    h: int = 80,
    **kwargs,
) -> Panel:
    """Create a small Panel with a solid colour, useful as a drag item."""
    return Panel(
        width=w,
        height=h,
        style=Style(background_color=color, padding=4),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# 1. Drag ghost visible at a different position from original
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_drag_ghost_visible() -> None:
    """A grid of coloured boxes with one being dragged.

    Four coloured panels are arranged in a horizontal row inside a
    container.  The second panel (orange) is dragged — the ghost
    appears as a semi-transparent rectangle offset to the lower-right,
    demonstrating that the ghost follows the cursor independently of
    the original component position.

    Expected: row of 4 coloured boxes.  A faint grey ghost rectangle
    (the drag ghost of the orange box) floats below-right of the row.
    """

    class DragScene(Scene):
        def on_enter(self) -> None:
            # Container row of 4 coloured boxes.
            row = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.HORIZONTAL,
                spacing=8,
                margin=40,
                style=Style(
                    background_color=(30, 30, 45, 220),
                    padding=12,
                ),
            )

            blue = _color_panel((50, 80, 200, 255))
            orange = _color_panel(
                (230, 130, 30, 255),
                draggable=True,
                drag_data="orange_item",
            )
            green = _color_panel((40, 180, 60, 255))
            purple = _color_panel((140, 50, 180, 255))

            row.add(blue)
            row.add(orange)
            row.add(green)
            row.add(purple)
            self.ui.add(row)

            # Force a layout pass so computed positions are set.
            self.ui._ensure_layout()

            # Programmatically start a drag on the orange panel.
            dm = self.ui.drag_manager
            # Simulate a click in the centre of the orange panel.
            click_x = orange._computed_x + orange._computed_w // 2
            click_y = orange._computed_y + orange._computed_h // 2
            dm._start_drag(orange, orange.drag_data, click_x, click_y)

            # Move the ghost to a position below-right of the row.
            ghost_target_x = orange._computed_x + 120
            ghost_target_y = orange._computed_y + 100
            dm._active.ghost_x = ghost_target_x
            dm._active.ghost_y = ghost_target_y

    def setup(game: Game) -> None:
        game.push(DragScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "drag_ghost_visible")


# ---------------------------------------------------------------------------
# 2. Drag hovering over valid drop target (green highlight)
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_drag_valid_target_highlight() -> None:
    """Drag hovering over a panel that accepts the drop — green highlight.

    A source panel (orange, top-left area) is being dragged.  Its ghost
    hovers over a target panel (dark, right area) that returns True from
    ``drop_accept``.  The target should show a green overlay.

    Expected: two panels side by side — the left one orange (source),
    the right one with a green highlight overlay.  A faint ghost rect
    over the target area.
    """

    class ValidScene(Scene):
        def on_enter(self) -> None:
            # Source box on the left.
            source = _color_panel(
                (230, 130, 30, 255),
                w=100, h=100,
                draggable=True,
                drag_data="valid_item",
            )

            # Target box on the right.
            target = _color_panel(
                (50, 50, 70, 255),
                w=120, h=120,
                drop_accept=lambda data: True,
                on_drop=lambda c, d: None,
            )

            # Container that spaces them apart.
            row = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.HORIZONTAL,
                spacing=60,
                style=Style(
                    background_color=(25, 25, 40, 200),
                    padding=20,
                ),
            )
            row.add(source)
            row.add(target)
            self.ui.add(row)

            self.ui._ensure_layout()

            # Start a drag from the source.
            dm = self.ui.drag_manager
            cx = source._computed_x + source._computed_w // 2
            cy = source._computed_y + source._computed_h // 2
            dm._start_drag(source, source.drag_data, cx, cy)

            # Position the ghost over the target's centre.
            tx = target._computed_x + (target._computed_w - source._computed_w) // 2
            ty = target._computed_y + (target._computed_h - source._computed_h) // 2
            dm._active.ghost_x = tx
            dm._active.ghost_y = ty

            # Update current_target and target_accepts for the highlight.
            dm._active.current_target = target
            dm._active.target_accepts = True

    def setup(game: Game) -> None:
        game.push(ValidScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "drag_valid_target_highlight")


# ---------------------------------------------------------------------------
# 3. Drag hovering over invalid drop target (red highlight)
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_drag_invalid_target_highlight() -> None:
    """Drag hovering over a panel that rejects the drop — red highlight.

    Same layout as the valid-target test, but the target's
    ``drop_accept`` returns False.  The target should show a red overlay
    instead of green.

    Expected: two panels side by side — orange source on the left,
    the right panel has a red highlight overlay.  A faint ghost rect
    over the target area.
    """

    class InvalidScene(Scene):
        def on_enter(self) -> None:
            source = _color_panel(
                (230, 130, 30, 255),
                w=100, h=100,
                draggable=True,
                drag_data="wrong_item",
            )

            target = _color_panel(
                (50, 50, 70, 255),
                w=120, h=120,
                drop_accept=lambda data: False,
            )

            row = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.HORIZONTAL,
                spacing=60,
                style=Style(
                    background_color=(25, 25, 40, 200),
                    padding=20,
                ),
            )
            row.add(source)
            row.add(target)
            self.ui.add(row)

            self.ui._ensure_layout()

            dm = self.ui.drag_manager
            cx = source._computed_x + source._computed_w // 2
            cy = source._computed_y + source._computed_h // 2
            dm._start_drag(source, source.drag_data, cx, cy)

            tx = target._computed_x + (target._computed_w - source._computed_w) // 2
            ty = target._computed_y + (target._computed_h - source._computed_h) // 2
            dm._active.ghost_x = tx
            dm._active.ghost_y = ty

            dm._active.current_target = target
            dm._active.target_accepts = False

    def setup(game: Game) -> None:
        game.push(InvalidScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "drag_invalid_target_highlight")
