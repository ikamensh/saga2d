"""Visual demo of PygletBackend with scene push/pop.

Run from project root::

    PYTHONPATH=. python tests/visual/test_stage1_visual.py

SPACE pushes a second scene, ESC pops back. Close the window to exit.
Lifecycle hooks print to the console.
"""

from __future__ import annotations

from easygame import Game, Scene
from easygame.backends.base import KeyEvent
from easygame.backends.pyglet_backend import PygletBackend


class MainScene(Scene):
    """First scene — teal background."""

    def on_enter(self) -> None:
        print("[MainScene] on_enter")
        backend = self.game.backend
        img = backend.create_solid_color_image(
            30, 80, 100, 255,
            backend.logical_width, backend.logical_height,
        )
        self._bg_sprite = backend.create_sprite(img, 0)
        backend.update_sprite(self._bg_sprite, 0, 0)
        self._font = backend.load_font("Arial", 36)

    def on_exit(self) -> None:
        print("[MainScene] on_exit")
        self.game.backend.remove_sprite(self._bg_sprite)

    def on_reveal(self) -> None:
        print("[MainScene] on_reveal")
        # Recreate background sprite (was removed in on_exit when covered)
        backend = self.game.backend
        img = backend.create_solid_color_image(
            30, 80, 100, 255,
            backend.logical_width, backend.logical_height,
        )
        self._bg_sprite = backend.create_sprite(img, 0)

    def draw(self) -> None:
        backend = self.game.backend
        backend.update_sprite(self._bg_sprite, 0, 0)
        backend.draw_text(
            "Scene: Main",
            self._font,
            100, 500,
            (255, 255, 255, 255),
        )
        backend.draw_text(
            "SPACE = push overlay  |  ESC = pop  |  Close window = quit",
            self._font,
            100, 440,
            (200, 200, 200, 255),
        )

    def handle_input(self, event: object) -> bool:
        if isinstance(event, KeyEvent) and event.type == "key_press":
            if event.key == "space":
                self.game.push(OverlayScene())
                return True
        return False


class OverlayScene(Scene):
    """Second scene — coral background."""

    def on_enter(self) -> None:
        print("[OverlayScene] on_enter")
        backend = self.game.backend
        img = backend.create_solid_color_image(
            180, 90, 100, 255,
            backend.logical_width, backend.logical_height,
        )
        self._bg_sprite = backend.create_sprite(img, 0)
        backend.update_sprite(self._bg_sprite, 0, 0)
        self._font = backend.load_font("Arial", 36)

    def on_exit(self) -> None:
        print("[OverlayScene] on_exit")
        self.game.backend.remove_sprite(self._bg_sprite)

    def on_reveal(self) -> None:
        print("[OverlayScene] on_reveal")

    def draw(self) -> None:
        backend = self.game.backend
        backend.update_sprite(self._bg_sprite, 0, 0)
        backend.draw_text(
            "Scene: Overlay",
            self._font,
            100, 500,
            (255, 255, 255, 255),
        )
        backend.draw_text(
            "ESC = pop back to Main",
            self._font,
            100, 440,
            (255, 255, 220, 255),
        )

    def handle_input(self, event: object) -> bool:
        if isinstance(event, KeyEvent) and event.type == "key_press":
            if event.key == "escape":
                self.game.pop()
                return True
        return False


def main() -> None:
    backend = PygletBackend()
    game = Game(
        "Stage 1 Visual — Scene Push/Pop",
        resolution=(800, 600),
        fullscreen=False,
        backend=backend,
    )
    game.run(MainScene())


if __name__ == "__main__":
    main()
