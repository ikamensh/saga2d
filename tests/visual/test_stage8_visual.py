"""Visual demo of UI system: Panel, Label, Button.

Run from project root::

    PYTHONPATH=. python tests/visual/test_stage8_visual.py

Shows a centered panel with "Main Menu" title and three buttons:
Play, Options, Quit. Click Quit or close the window to exit.
"""

from __future__ import annotations

import pytest

from saga2d import Game, Scene, Anchor, Layout, Panel, Label, Button, Style
from saga2d.backends.pyglet_backend import PygletBackend


class MainMenuScene(Scene):
    """Scene with a centered menu panel using the UI system."""

    def on_enter(self) -> None:
        print("[MainMenuScene] on_enter")
        backend = self.game.backend
        # Background
        img = backend.create_solid_color_image(
            25, 25, 35, 255,
            backend.logical_width, backend.logical_height,
        )
        self._bg_sprite = backend.create_sprite(img, 0)
        backend.update_sprite(self._bg_sprite, 0, 0)

        # Centered panel with title and buttons
        panel = Panel(
            anchor=Anchor.CENTER,
            layout=Layout.VERTICAL,
            spacing=20,
        )
        panel.add(Label("Main Menu", style=Style(font_size=48)))
        panel.add(Button("Play", on_click=self._on_play))
        panel.add(Button("Options", on_click=self._on_options))
        panel.add(Button("Quit", on_click=self.game.quit))
        self.ui.add(panel)

    def on_exit(self) -> None:
        print("[MainMenuScene] on_exit")
        self.game.backend.remove_sprite(self._bg_sprite)

    def draw(self) -> None:
        backend = self.game.backend
        backend.update_sprite(self._bg_sprite, 0, 0)

    def _on_play(self) -> None:
        print("Play clicked")

    def _on_options(self) -> None:
        print("Options clicked")


def main() -> None:
    backend = PygletBackend()
    game = Game(
        "Stage 8 Visual — UI System",
        resolution=(800, 600),
        fullscreen=False,
        backend=backend,
    )
    game.run(MainMenuScene())


@pytest.mark.visual
def test_stage8_visual() -> None:
    """Run the Stage 8 UI demo as a pytest test.

    Requires display and pyglet. Excluded from normal pytest run via
    collect_ignore in tests/conftest.py.
    """
    main()


if __name__ == "__main__":
    main()
