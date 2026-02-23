"""Visual demo of Timer, Tween, and Input systems.

Run from project root::

    PYTHONPATH=. python tests/visual/test_stage45_visual.py

Demonstrates:
1. Sliding sprite (crate) — tween with EASE_IN_OUT, slides left-right
2. Fading sprite (enemy) — tween opacity 255 <-> 128
3. Click-to-move — click anywhere, knight moves there
4. Action bindings — press Enter/ESC/arrows, action names print to console
5. Timer — every 2s prints "Timer: 2s" and teleports a crate
6. ESC (cancel action) — quits

Close window or press ESC to exit.
"""

from __future__ import annotations

import random
from pathlib import Path

from easygame import Game, Scene, Sprite, Ease, tween
from easygame.input import InputEvent
from easygame.backends.pyglet_backend import PygletBackend

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "images" / "sprites"


class Stage45Scene(Scene):
    """Scene demonstrating Timer, Tween, and Input systems."""

    def on_enter(self) -> None:
        backend = self.game.backend

        # Background
        bg = backend.create_solid_color_image(
            40, 50, 60, 255,
            backend.logical_width, backend.logical_height,
        )
        self._bg_sprite = backend.create_sprite(bg, -1)
        backend.update_sprite(self._bg_sprite, 0, 0)

        # 1. Sliding sprite (crate) — EASE_IN_OUT
        self._slider = Sprite("sprites/crate", position=(100, 150))
        self._slide_right()

        # 2. Fading sprite (enemy)
        self._fader = Sprite("sprites/enemy", position=(400, 400))
        self._fade_down()

        # 3. Click-to-move sprite (knight)
        self._knight = Sprite("sprites/knight", position=(400, 300))

        # 4. Timer sprite — teleports every 2s
        self._timer_sprite = Sprite("sprites/crate", position=(600, 100))
        self.game.every(2.0, self._on_timer)


    def _slide_right(self) -> None:
        tween(
            self._slider, "x", self._slider.x, 700.0, 2.0,
            ease=Ease.EASE_IN_OUT,
            on_complete=self._slide_left,
        )

    def _slide_left(self) -> None:
        tween(
            self._slider, "x", self._slider.x, 100.0, 2.0,
            ease=Ease.EASE_IN_OUT,
            on_complete=self._slide_right,
        )

    def _fade_down(self) -> None:
        tween(
            self._fader, "opacity", self._fader.opacity, 128, 1.0,
            ease=Ease.LINEAR,
            on_complete=self._fade_up,
        )

    def _fade_up(self) -> None:
        tween(
            self._fader, "opacity", self._fader.opacity, 255, 1.0,
            ease=Ease.LINEAR,
            on_complete=self._fade_down,
        )

    def _on_timer(self) -> None:
        print("Timer: 2s")
        x = random.randint(100, 700)
        y = random.randint(80, 500)
        self._timer_sprite.position = (x, y)

    def on_exit(self) -> None:
        self._slider.remove()
        self._fader.remove()
        self._knight.remove()
        self._timer_sprite.remove()
        self.game.backend.remove_sprite(self._bg_sprite)

    def draw(self) -> None:
        backend = self.game.backend
        backend.update_sprite(self._bg_sprite, 0, 0)
        backend.draw_text(
            "Click = move knight  |  Keys = print action  |  ESC = quit",
            20, backend.logical_height - 25,
            20,
            (255, 255, 255, 255),
            font="Arial",
        )
        backend.draw_text(
            "Sliding crate (EASE_IN_OUT) | Fading enemy | Timer sprite teleports every 2s",
            20, backend.logical_height - 48,
            20,
            (200, 200, 200, 255),
            font="Arial",
        )

    def handle_input(self, event: InputEvent) -> bool:
        # 6. ESC (cancel) quits
        if event.action == "cancel":
            self.game.quit()
            return True

        # 4. Action bindings — print action names
        if event.type == "key_press" and event.action:
            print(f"Action: {event.action}")
            return True

        # 3. Click-to-move
        if event.type == "click" and event.button == "left":
            self._knight.move_to((event.x, event.y), speed=200.0)
            return True

        return False


def main() -> None:
    if not ASSETS_DIR.exists():
        raise SystemExit(
            f"Assets not found at {ASSETS_DIR}. "
            "Run: python generate_assets.py"
        )

    backend = PygletBackend()
    game = Game(
        "Stage 4+5 Visual — Timer, Tween, Input",
        resolution=(800, 600),
        fullscreen=False,
        backend=backend,
    )
    game.run(Stage45Scene())


if __name__ == "__main__":
    main()
