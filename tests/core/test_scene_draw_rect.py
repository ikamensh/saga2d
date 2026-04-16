"""Properties of :meth:`Scene.draw_rect` — with and without borders.

The iter-16 ``border_color`` / ``border_width`` convenience composes
two rects in one call. Test both that the composed output is correct
*and* that the plain (no-border) path still emits exactly one rect.
"""

from __future__ import annotations

import pytest

from saga2d import Game, Scene


@pytest.fixture
def game():
    g = Game(
        "draw-rect-test",
        resolution=(200, 200),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _render(game: Game, draw_fn) -> list[dict]:
    """Push a scene whose ``draw`` delegates to *draw_fn(self)*, tick,
    return the rect list recorded by the mock backend."""

    class S(Scene):
        def draw(self) -> None:
            draw_fn(self)

    game._scene_stack.push(S())
    game.tick(dt=1 / 60)
    return list(game.backend.rects)


def test_plain_draw_rect_emits_one_rect(game: Game) -> None:
    """No border_color → one rect, same as before iter-16."""
    rects = _render(
        game,
        lambda s: s.draw_rect(10, 20, 30, 40, (200, 50, 50, 255)),
    )
    assert len(rects) == 1
    r = rects[0]
    assert (r["x"], r["y"], r["width"], r["height"]) == (10, 20, 30, 40)
    assert r["color"] == (200, 50, 50, 255)


def test_bordered_draw_rect_emits_outer_then_inner(game: Game) -> None:
    """border_color with positive border_width → two rects: outer border
    then inner fill inset by border_width on every side."""
    rects = _render(
        game,
        lambda s: s.draw_rect(
            10, 20, 30, 40, (200, 200, 200, 255),
            border_color=(50, 50, 50, 255), border_width=3,
        ),
    )
    assert len(rects) == 2
    outer, inner = rects
    assert outer["color"] == (50, 50, 50, 255)
    assert (outer["x"], outer["y"], outer["width"], outer["height"]) == (10, 20, 30, 40)
    assert inner["color"] == (200, 200, 200, 255)
    # Inner is inset by border_width on all sides.
    assert inner["x"] == 10 + 3
    assert inner["y"] == 20 + 3
    assert inner["width"] == 30 - 2 * 3
    assert inner["height"] == 40 - 2 * 3


def test_zero_border_width_ignores_border_color(game: Game) -> None:
    """border_color alone (border_width=0) is a no-op for the border —
    still one rect. Prevents a hairline border from being drawn by
    accident when a user passes only border_color."""
    rects = _render(
        game,
        lambda s: s.draw_rect(
            0, 0, 10, 10, (100, 100, 100, 255),
            border_color=(0, 0, 0, 255),  # no width
        ),
    )
    assert len(rects) == 1


def test_border_wider_than_rect_clamps_inner_to_zero(game: Game) -> None:
    """If the border is so thick the inner would go negative, the
    inner rect collapses to zero size rather than producing negative
    width/height that the backend might misinterpret."""
    rects = _render(
        game,
        lambda s: s.draw_rect(
            0, 0, 4, 4, (255, 255, 255, 255),
            border_color=(0, 0, 0, 255), border_width=10,
        ),
    )
    assert len(rects) == 2
    inner = rects[1]
    assert inner["width"] == 0
    assert inner["height"] == 0
