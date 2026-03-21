"""Test hover effects for List and Grid widgets."""

from __future__ import annotations

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from saga2d import Game, Scene
from saga2d.ui import Anchor, Grid, Label, Layout, List, Panel


class HoverTestScene(Scene):
    """Scene to test hover effects on List and Grid."""

    def on_enter(self) -> None:
        """Set up the UI with List and Grid widgets."""
        # Main container
        container = Panel(
            anchor=Anchor.CENTER,
            layout=Layout.HORIZONTAL,
            spacing=40,
            style={"padding": 20, "background_color": (20, 25, 35, 255)},
        )

        # Left: List widget
        left_panel = Panel(
            layout=Layout.VERTICAL,
            spacing=10,
            style={"padding": 0, "background_color": (0, 0, 0, 0)},
        )
        left_panel.add(Label("List (hover over items)", style={"font_size": 18}))

        test_list = List(
            items=["Sword", "Shield", "Potion", "Elixir", "Scroll"],
            width=200,
            height=180,
            item_height=30,
        )
        test_list.selected_index = 1
        left_panel.add(test_list)

        container.add(left_panel)

        # Right: Grid widget
        right_panel = Panel(
            layout=Layout.VERTICAL,
            spacing=10,
            style={"padding": 0, "background_color": (0, 0, 0, 0)},
        )
        right_panel.add(Label("Grid (hover over cells)", style={"font_size": 18}))

        test_grid = Grid(
            columns=3,
            rows=3,
            cell_size=(60, 60),
            spacing=6,
        )
        # Add some content to a few cells
        test_grid.set_cell(0, 0, Label("A", style={"font_size": 16}))
        test_grid.set_cell(1, 0, Label("B", style={"font_size": 16}))
        test_grid.set_cell(0, 1, Label("C", style={"font_size": 16}))
        test_grid.set_cell(2, 2, Label("D", style={"font_size": 16}))
        test_grid.selected = (1, 1)
        right_panel.add(test_grid)

        container.add(right_panel)

        self.ui.add(container)

        # Instructions
        instructions = Label(
            "Move your mouse over the List items and Grid cells to see hover effects",
            anchor=Anchor.BOTTOM,
            margin=20,
            style={"font_size": 14, "text_color": (150, 150, 150, 255)},
        )
        self.ui.add(instructions)


def main() -> None:
    """Run the hover effects test."""
    game = Game(
        "Hover Effects Test",
        resolution=(800, 600),
        backend="pyglet",
    )

    scene = HoverTestScene()
    game.push(scene)
    game.run()


if __name__ == "__main__":
    main()
