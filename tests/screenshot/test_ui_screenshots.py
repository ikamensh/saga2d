"""Screenshot regression tests for the Stage 8 UI system.

Run from the project root::

    pytest tests/screenshot/test_ui_screenshots.py -v

Requires pyglet (GPU context).  Excluded from the normal ``pytest tests/``
run by ``collect_ignore`` in ``tests/conftest.py``.

Each test creates a Scene subclass that builds a UI tree in ``on_enter()``,
then captures a screenshot via ``render_scene()`` and compares against a
golden PNG in ``tests/screenshot/golden/``.  Golden images are auto-created
on first run.

UI rendering uses ``draw_rect()`` (solid backgrounds) and ``draw_text()``
(labels and button text) — both per-frame calls that go through the pyglet
batch with high-order groups so they render on top of sprites.
"""

from __future__ import annotations

import pytest

from easygame import Scene
from easygame.ui import Anchor, Button, Label, Layout, Panel, Style

from tests.screenshot.harness import assert_screenshot, render_scene

_RESOLUTION = (480, 360)


# ---------------------------------------------------------------------------
# 1. Main menu — centered panel with title + 3 vertical buttons
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_ui_main_menu() -> None:
    """Centered panel with a title Label and 3 Buttons arranged vertically.

    This is the canonical "main menu" golden test.  The panel auto-sizes
    to fit its children (content-fit) and is anchored to screen center.

    Expected layout (480x360 screen):
      - Panel background centered on screen
      - "Main Menu" label at the top inside the panel
      - "New Game", "Load Game", "Quit" buttons stacked below with spacing
    """

    class MenuScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=8,
            )
            panel.add(Label("Main Menu", style=Style(font_size=28)))
            panel.add(Button("New Game"))
            panel.add(Button("Load Game"))
            panel.add(Button("Quit"))
            self.ui.add(panel)

    def setup(game):
        game.push(MenuScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "ui_main_menu")


# ---------------------------------------------------------------------------
# 2. Horizontal button bar
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_ui_horizontal_buttons() -> None:
    """Panel with horizontal layout containing 3 buttons.

    The panel is anchored to the bottom of the screen.  Buttons are
    arranged left-to-right with spacing, centered vertically within
    the panel.  Buttons use auto-sizing (no explicit width) so text
    fits comfortably.
    """

    class HBarScene(Scene):
        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.BOTTOM,
                layout=Layout.HORIZONTAL,
                spacing=12,
                margin=10,
            )
            panel.add(Button("Attack"))
            panel.add(Button("Defend"))
            panel.add(Button("Magic"))
            self.ui.add(panel)

    def setup(game):
        game.push(HBarScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "ui_horizontal_buttons")


# ---------------------------------------------------------------------------
# 3. Styled label — large font, custom colour
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_ui_styled_label() -> None:
    """A label with custom style: large font and distinct colour.

    The label is anchored to the centre of the screen.  This tests
    that explicit Style overrides (font_size, text_color) are applied
    correctly to the rendered text.
    """

    class LabelScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "GAME OVER",
                anchor=Anchor.CENTER,
                style=Style(
                    font_size=40,
                    text_color=(255, 60, 60, 255),
                ),
            ))

    def setup(game):
        game.push(LabelScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "ui_styled_label")


# ---------------------------------------------------------------------------
# 4. Nested panels
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_ui_nested_panels() -> None:
    """Outer panel with vertical layout containing two inner panels.

    Each inner panel uses horizontal layout with labels inside.  This
    tests that layout propagation through nested containers works
    correctly, with each level contributing its own padding, spacing,
    and background colour.

    The outer panel has a darker background; inner panels have a
    lighter tint to make nesting visible.
    """

    class NestedScene(Scene):
        def on_enter(self) -> None:
            inner_style = Style(
                background_color=(80, 80, 100, 220),
                padding=10,
            )

            top_row = Panel(
                layout=Layout.HORIZONTAL, spacing=20,
                style=inner_style,
            )
            top_row.add(Label("HP: 100", style=Style(font_size=18)))
            top_row.add(Label("MP: 50", style=Style(font_size=18)))

            bottom_row = Panel(
                layout=Layout.HORIZONTAL, spacing=20,
                style=inner_style,
            )
            bottom_row.add(Label("ATK: 25", style=Style(font_size=18)))
            bottom_row.add(Label("DEF: 18", style=Style(font_size=18)))

            outer = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=8,
                style=Style(
                    background_color=(30, 30, 45, 240),
                    padding=14,
                ),
            )
            outer.add(top_row)
            outer.add(bottom_row)
            self.ui.add(outer)

    def setup(game):
        game.push(NestedScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "ui_nested_panels")
