"""Visual demo of sprite functionality with PygletBackend.

Run from project root::

    PYTHONPATH=. python tests/visual/test_stage2_visual.py

Loads tree, knight, enemy from assets/images/sprites/. Trees on OBJECTS layer,
knight/enemy on UNITS layer. Arrow keys move knight, DELETE removes it.
"""

from __future__ import annotations

from pathlib import Path

from easygame import Game, Scene, RenderLayer
from easygame.backends.base import KeyEvent
from easygame.backends.pyglet_backend import PygletBackend

ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "images" / "sprites"


def _layer_order(layer: RenderLayer, y: int) -> int:
    """Compute draw order for y-sorting within a layer (higher y = in front)."""
    return int(layer) * 1000 + y


class SpriteScene(Scene):
    """Scene demonstrating sprites, layers, y-sorting, movement, and removal."""

    def on_enter(self) -> None:
        backend = self.game.backend

        # Background
        bg = backend.create_solid_color_image(
            40, 50, 60, 255,
            backend.logical_width, backend.logical_height,
        )
        self._bg_sprite = backend.create_sprite(bg, -1)  # behind everything
        backend.update_sprite(self._bg_sprite, 0, 0)

        # Load images
        tree_img = backend.load_image(str(ASSETS_DIR / "tree.png"))
        knight_img = backend.load_image(str(ASSETS_DIR / "knight.png"))
        enemy_img = backend.load_image(str(ASSETS_DIR / "enemy.png"))

        # Trees on OBJECTS layer at different y (y-sort: higher y draws in front)
        self._tree1 = backend.create_sprite(
            tree_img, _layer_order(RenderLayer.OBJECTS, 150),
        )
        backend.update_sprite(self._tree1, 150, 150)

        self._tree2 = backend.create_sprite(
            tree_img, _layer_order(RenderLayer.OBJECTS, 350),
        )
        backend.update_sprite(self._tree2, 350, 350)

        self._tree3 = backend.create_sprite(
            tree_img, _layer_order(RenderLayer.OBJECTS, 250),
        )
        backend.update_sprite(self._tree3, 500, 250)

        # Knight and enemy on UNITS layer (knight at y=400, enemy at y=300)
        # Enemy draws behind knight (lower y)
        self._knight = backend.create_sprite(
            knight_img, _layer_order(RenderLayer.UNITS, 400),
        )
        self._knight_x, self._knight_y = 400, 400
        backend.update_sprite(self._knight, self._knight_x, self._knight_y)

        self._enemy = backend.create_sprite(
            enemy_img, _layer_order(RenderLayer.UNITS, 300),
        )
        backend.update_sprite(self._enemy, 550, 300)

        self._font = backend.load_font("Arial", 24)
        self._knight_removed = False

    def on_exit(self) -> None:
        backend = self.game.backend
        backend.remove_sprite(self._bg_sprite)
        backend.remove_sprite(self._tree1)
        backend.remove_sprite(self._tree2)
        backend.remove_sprite(self._tree3)
        if not self._knight_removed:
            backend.remove_sprite(self._knight)
        backend.remove_sprite(self._enemy)

    def draw(self) -> None:
        backend = self.game.backend
        backend.update_sprite(self._bg_sprite, 0, 0)
        if not self._knight_removed:
            backend.update_sprite(self._knight, self._knight_x, self._knight_y)
            backend.set_sprite_order(
                self._knight, _layer_order(RenderLayer.UNITS, self._knight_y),
            )

        backend.draw_text(
            "Arrows = move knight  |  DELETE = remove knight  |  Close = quit",
            self._font,
            20, backend.logical_height - 30,
            (255, 255, 255, 255),
        )
        backend.draw_text(
            "Trees (OBJECTS) behind knight/enemy (UNITS). Y-sort: higher y = in front.",
            self._font,
            20, backend.logical_height - 55,
            (200, 200, 200, 255),
        )

    def handle_input(self, event: object) -> bool:
        if not isinstance(event, KeyEvent) or event.type != "key_press":
            return False

        if self._knight_removed:
            return False

        step = 12
        if event.key == "up":
            self._knight_y = min(
                self.game.backend.logical_height - 32,
                self._knight_y + step,
            )
            return True
        if event.key == "down":
            self._knight_y = max(32, self._knight_y - step)
            return True
        if event.key == "left":
            self._knight_x = max(24, self._knight_x - step)
            return True
        if event.key == "right":
            self._knight_x = min(
                self.game.backend.logical_width - 24,
                self._knight_x + step,
            )
            return True
        if event.key == "delete":
            self.game.backend.remove_sprite(self._knight)
            self._knight_removed = True
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
        "Stage 2 Visual — Sprites, Layers, Y-Sort",
        resolution=(800, 600),
        fullscreen=False,
        backend=backend,
    )
    game.run(SpriteScene())


if __name__ == "__main__":
    main()
