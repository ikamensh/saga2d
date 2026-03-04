"""Visual demo of sprite animation with PygletBackend.

Run from project root::

    PYTHONPATH=. python tests/visual/test_stage3_visual.py

Knight cycles through knight_walk frames (looping). Press A to play knight_attack
once; on_complete returns to walk animation. Close window to quit.
"""

from __future__ import annotations

from pathlib import Path

from saga2d import Game, Scene, Sprite, AnimationDef
from saga2d.backends.base import KeyEvent
from saga2d.backends.pyglet_backend import PygletBackend

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "images" / "sprites"

WALK = AnimationDef(frames="sprites/knight_walk", frame_duration=0.15, loop=True)
ATTACK = AnimationDef(frames="sprites/knight_attack", frame_duration=0.1, loop=False)


class AnimationScene(Scene):
    """Scene demonstrating sprite animation: walk loop + attack on A key."""

    def on_enter(self) -> None:
        backend = self.game.backend

        # Background
        bg = backend.create_solid_color_image(
            40, 50, 60, 255,
            backend.logical_width, backend.logical_height,
        )
        self._bg_sprite = backend.create_sprite(bg, -1)
        backend.update_sprite(self._bg_sprite, 0, 0)

        # Knight sprite with walk animation (looping)
        self._knight = Sprite("sprites/knight_walk_01", position=(400, 300))
        self._knight.play(WALK)


    def on_exit(self) -> None:
        self._knight.remove()
        self.game.backend.remove_sprite(self._bg_sprite)

    def draw(self) -> None:
        backend = self.game.backend
        backend.update_sprite(self._bg_sprite, 0, 0)
        backend.draw_text(
            "A = attack (once, then back to walk)  |  Close = quit",
            20, backend.logical_height - 30,
            24,
            (255, 255, 255, 255),
            font="Arial",
        )
        backend.draw_text(
            "Knight cycles knight_walk frames. Attack uses on_complete callback.",
            20, backend.logical_height - 55,
            24,
            (200, 200, 200, 255),
            font="Arial",
        )

    def handle_input(self, event: object) -> bool:
        if isinstance(event, KeyEvent) and event.type == "key_press":
            if event.key == "a":
                self._knight.play(
                    ATTACK,
                    on_complete=lambda: self._knight.play(WALK),
                )
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
        "Stage 3 Visual — Sprite Animation",
        resolution=(800, 600),
        fullscreen=False,
        backend=backend,
    )
    game.run(AnimationScene())


if __name__ == "__main__":
    main()
