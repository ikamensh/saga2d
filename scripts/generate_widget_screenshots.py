"""Generate widget screenshot golden images using MockBackend + PIL.

This script runs the actual Saga2D widget code with MockBackend to record
draw calls, then replays them onto PIL Images to generate golden screenshots
without requiring a display/GPU.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from saga2d import Game
from saga2d.ui import (
    Anchor,
    Button,
    DataTable,
    Grid,
    Label,
    Layout,
    List,
    Panel,
    ProgressBar,
    Style,
    TabGroup,
    TextBox,
    Tooltip,
)

from mock_to_pil_renderer import MockToPILRenderer

# Output directory
GOLDEN_DIR = _PROJECT_ROOT / "tests" / "screenshot" / "golden"
GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

# Resolution for widget screenshots
_RESOLUTION = (480, 360)


def render_widget_to_image(setup_fn, resolution=_RESOLUTION):
    """Render a widget scene using MockBackend and return PIL Image.

    Args:
        setup_fn: Function that receives a Game and sets up the scene
        resolution: (width, height) tuple

    Returns:
        PIL Image of the rendered scene
    """
    # Create game with mock backend
    game = Game(
        "Screenshot Test",
        resolution=resolution,
        backend="mock",
    )

    # Set up the scene
    setup_fn(game)

    # Tick one frame to trigger layout and drawing
    game.tick(dt=1.0 / 60.0)

    # Get the recorded draw calls from the mock backend
    backend = game._backend
    rects = backend.rects
    circles = backend.circles
    texts = backend.texts
    images = backend.images

    # Create PIL renderer and render
    renderer = MockToPILRenderer(resolution[0], resolution[1])
    image = renderer.render_all(rects, circles, texts, images)

    # Clean up
    game._teardown()

    return image


# =============================================================================
# Widget test scenes (matching tests/screenshot/test_widget_screenshots.py)
# =============================================================================


def test_progress_bar():
    """ProgressBar at 75% value centered on screen."""

    def setup(game):
        from saga2d import Scene

        class BarScene(Scene):
            def on_enter(self):
                panel = Panel(
                    anchor=Anchor.CENTER,
                    layout=Layout.VERTICAL,
                    spacing=8,
                )
                panel.add(Label("Health", style=Style(font_size=20)))
                panel.add(
                    ProgressBar(
                        value=75,
                        max_value=100,
                        width=300,
                        height=28,
                    )
                )
                self.ui.add(panel)

        game.push(BarScene())

    image = render_widget_to_image(setup)
    image.save(GOLDEN_DIR / "widget_progress_bar.png")
    print("✓ Generated widget_progress_bar.png")


def test_textbox_instant():
    """TextBox displaying wrapped multi-line text, all revealed instantly."""

    def setup(game):
        from saga2d import Scene

        class TextScene(Scene):
            def on_enter(self):
                panel = Panel(
                    anchor=Anchor.CENTER,
                    layout=Layout.VERTICAL,
                    spacing=6,
                    style=Style(padding=12),
                )
                panel.add(Label("Journal Entry", style=Style(font_size=22)))
                panel.add(
                    TextBox(
                        "The ancient fortress loomed ahead, its crumbling towers "
                        "silhouetted against the crimson sky. Our party pressed "
                        "forward through the overgrown courtyard, weapons drawn.",
                        width=350,
                        style=Style(font_size=16),
                    )
                )
                self.ui.add(panel)

        game.push(TextScene())

    image = render_widget_to_image(setup)
    image.save(GOLDEN_DIR / "widget_textbox_instant.png")
    print("✓ Generated widget_textbox_instant.png")


def test_list_with_selection():
    """List widget with 5 items, the third item (index 2) selected."""

    def setup(game):
        from saga2d import Scene

        class ListScene(Scene):
            def on_enter(self):
                panel = Panel(
                    anchor=Anchor.CENTER,
                    layout=Layout.VERTICAL,
                    spacing=8,
                )
                panel.add(Label("Save Files", style=Style(font_size=20)))
                lst = List(
                    [
                        "Slot 1 - Castle",
                        "Slot 2 - Forest",
                        "Slot 3 - Dungeon",
                        "Slot 4 - Village",
                        "Slot 5 - Empty",
                    ],
                    width=280,
                    item_height=28,
                )
                lst.selected_index = 2
                panel.add(lst)
                self.ui.add(panel)

        game.push(ListScene())

    image = render_widget_to_image(setup)
    image.save(GOLDEN_DIR / "widget_list_with_selection.png")
    print("✓ Generated widget_list_with_selection.png")


def test_grid_with_cells():
    """3x3 Grid with Labels in several cells, cell (1,1) selected."""

    def setup(game):
        from saga2d import Scene

        class GridScene(Scene):
            def on_enter(self):
                panel = Panel(
                    anchor=Anchor.CENTER,
                    layout=Layout.VERTICAL,
                    spacing=8,
                )
                panel.add(Label("Inventory", style=Style(font_size=20)))
                grid = Grid(
                    3,
                    3,
                    cell_size=(64, 64),
                    spacing=4,
                    style=Style(padding=6),
                )
                # Place labels in some cells.
                grid.set_cell(0, 0, Label("Sw", style=Style(font_size=14)))
                grid.set_cell(1, 0, Label("Sh", style=Style(font_size=14)))
                grid.set_cell(2, 0, Label("Bw", style=Style(font_size=14)))
                grid.set_cell(0, 1, Label("Hp", style=Style(font_size=14)))
                grid.set_cell(1, 1, Label("Mp", style=Style(font_size=14)))
                # (2,1), (0,2), (1,2), (2,2) are empty
                grid.selected = (1, 1)
                panel.add(grid)
                self.ui.add(panel)

        game.push(GridScene())

    image = render_widget_to_image(setup)
    image.save(GOLDEN_DIR / "widget_grid_with_cells.png")
    print("✓ Generated widget_grid_with_cells.png")


def test_tooltip_visible():
    """Tooltip that has passed its delay and is now visible."""

    def setup(game):
        from saga2d import Scene

        class TipScene(Scene):
            def on_enter(self):
                # Add a label so the scene is not completely empty.
                self.ui.add(
                    Label(
                        "Hover over items for details",
                        anchor=Anchor.TOP,
                        margin=20,
                        style=Style(font_size=16),
                    )
                )
                self._tooltip = Tooltip(
                    "Sword of Flames (+12 ATK)",
                    delay=0.3,
                    style=Style(font_size=14),
                )
                self.ui.add(self._tooltip)
                # Start the delay timer at the desired position.
                self._tooltip.show(150, 180)

        game.push(TipScene())

        # Advance enough frames to pass the 0.3 s delay.
        # 30 ticks × (1/60) = 0.5 s > 0.3 s delay.
        for _ in range(30):
            game.tick(dt=1.0 / 60.0)

    image = render_widget_to_image(setup)
    image.save(GOLDEN_DIR / "widget_tooltip_visible.png")
    print("✓ Generated widget_tooltip_visible.png")


def test_tabgroup():
    """TabGroup with 3 tabs, the first tab active by default."""

    def setup(game):
        from saga2d import Scene

        class TabScene(Scene):
            def on_enter(self):
                stats_panel = Panel(
                    layout=Layout.VERTICAL,
                    spacing=6,
                    width=300,
                    height=120,
                    style=Style(padding=10),
                )
                stats_panel.add(Label("STR: 18", style=Style(font_size=16)))
                stats_panel.add(Label("DEX: 14", style=Style(font_size=16)))
                stats_panel.add(Label("INT: 12", style=Style(font_size=16)))

                skills_panel = Panel(
                    layout=Layout.VERTICAL,
                    spacing=6,
                    width=300,
                    height=120,
                    style=Style(padding=10),
                )
                skills_panel.add(Label("Fireball Lv.3", style=Style(font_size=16)))
                skills_panel.add(Label("Heal Lv.2", style=Style(font_size=16)))

                items_panel = Panel(
                    layout=Layout.VERTICAL,
                    spacing=6,
                    width=300,
                    height=120,
                    style=Style(padding=10),
                )
                items_panel.add(Label("Potion x5", style=Style(font_size=16)))
                items_panel.add(Label("Elixir x2", style=Style(font_size=16)))

                tabs = TabGroup(
                    {
                        "Stats": stats_panel,
                        "Skills": skills_panel,
                        "Items": items_panel,
                    },
                    width=320,
                    height=160,
                    anchor=Anchor.CENTER,
                )
                self.ui.add(tabs)

        game.push(TabScene())

    image = render_widget_to_image(setup)
    image.save(GOLDEN_DIR / "widget_tabgroup.png")
    print("✓ Generated widget_tabgroup.png")


def test_datatable():
    """DataTable with 3 columns and 5 data rows, row 1 selected."""

    def setup(game):
        from saga2d import Scene

        class TableScene(Scene):
            def on_enter(self):
                dt = DataTable(
                    ["Unit", "Class", "Level"],
                    [
                        ["Arthas", "Paladin", "10"],
                        ["Jaina", "Mage", "12"],
                        ["Thrall", "Shaman", "15"],
                        ["Sylvanas", "Ranger", "18"],
                        ["Uther", "Cleric", "9"],
                    ],
                    width=360,
                    anchor=Anchor.CENTER,
                )
                dt.selected_row = 1
                self.ui.add(dt)

        game.push(TableScene())

    image = render_widget_to_image(setup)
    image.save(GOLDEN_DIR / "widget_datatable.png")
    print("✓ Generated widget_datatable.png")


def test_combined_dialog():
    """RPG-style dialog box with portrait, text, and buttons."""

    def setup(game):
        from saga2d import Scene

        class DialogScene(Scene):
            def on_enter(self):
                # -- Outer dialog panel (bottom-anchored, full width) ----------
                dialog = Panel(
                    anchor=Anchor.BOTTOM,
                    margin=10,
                    layout=Layout.VERTICAL,
                    spacing=8,
                    width=460,
                    style=Style(
                        background_color=(25, 25, 40, 240),
                        padding=12,
                    ),
                )

                # -- Top row: portrait placeholder + text ----------------------
                top_row = Panel(
                    layout=Layout.HORIZONTAL,
                    spacing=10,
                    style=Style(padding=0, background_color=(0, 0, 0, 0)),
                )

                # Use a small coloured panel as a portrait placeholder
                portrait_panel = Panel(
                    width=64,
                    height=64,
                    style=Style(
                        background_color=(80, 60, 100, 255),
                        padding=4,
                    ),
                )
                portrait_panel.add(Label("NPC", style=Style(font_size=14)))
                top_row.add(portrait_panel)

                text = TextBox(
                    "Greetings, adventurer! I have a quest for you. "
                    "The goblins in the eastern caves have stolen our "
                    "sacred relic. Will you retrieve it for us?",
                    typewriter_speed=100,
                    width=350,
                    style=Style(font_size=15),
                )
                # Skip the typewriter so all text is visible for the screenshot.
                text.skip()
                top_row.add(text)

                dialog.add(top_row)

                # -- Bottom row: action buttons --------------------------------
                button_row = Panel(
                    layout=Layout.HORIZONTAL,
                    spacing=12,
                    style=Style(padding=0, background_color=(0, 0, 0, 0)),
                )
                button_row.add(
                    Button(
                        "Accept",
                        style=Style(font_size=16, padding=8),
                    )
                )
                button_row.add(
                    Button(
                        "Decline",
                        style=Style(font_size=16, padding=8),
                    )
                )
                dialog.add(button_row)

                self.ui.add(dialog)

        game.push(DialogScene())

    image = render_widget_to_image(setup)
    image.save(GOLDEN_DIR / "widget_combined_dialog.png")
    print("✓ Generated widget_combined_dialog.png")


def main():
    """Generate all widget screenshot golden images."""
    print("=" * 60)
    print("Generating Widget Screenshot Golden Images")
    print("Using MockBackend + PIL Renderer")
    print("=" * 60)
    print()

    # Generate all screenshots
    test_progress_bar()
    test_textbox_instant()
    test_list_with_selection()
    test_grid_with_cells()
    test_tooltip_visible()
    test_tabgroup()
    test_datatable()
    test_combined_dialog()

    print()
    print("=" * 60)
    print("✓ All golden images generated successfully!")
    print("=" * 60)
    print()
    print(f"Output directory: {GOLDEN_DIR}")
    print()
    print("Generated files:")
    for png in sorted(GOLDEN_DIR.glob("widget_*.png")):
        print(f"  - {png.name}")


if __name__ == "__main__":
    main()
