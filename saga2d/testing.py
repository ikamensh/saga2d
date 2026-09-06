"""Offscreen rendering for visual verification.

::

    from saga2d.testing import render_scene

    def setup(game):
        game.push(MyScene())

    image = render_scene(setup, resolution=(800, 600), tick_count=2)
    image.save("out.png")   # then LOOK at it

The window is created hidden; the returned PIL image is the framebuffer
at physical resolution (2× the logical size on HiDPI displays).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from saga2d.game import Game

if TYPE_CHECKING:
    from PIL import Image


def render_scene(
    setup: Callable[[Game], None],
    *,
    resolution: tuple[int, int] = (800, 600),
    tick_count: int = 1,
    dt: float = 1 / 60,
) -> "Image.Image":
    game = Game("Screenshot", resolution=resolution, backend="pyglet", visible=False)
    try:
        setup(game)
        for _ in range(tick_count):
            game.tick(dt=dt)
        return game.backend.capture_frame()
    finally:
        game.close()
