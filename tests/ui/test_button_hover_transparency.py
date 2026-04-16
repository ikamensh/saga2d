"""Regression: Button hover outline must not fire on a transparent button.

Mirrors the Panel-shadow-transparency regression. The bug pattern is
"theme-sourced opaque draw that triggers even when the component's own
background is alpha 0." A ghost (text-only) button with alpha-0 bg
should stay invisible on hover, not sprout a blue outline.
"""

from __future__ import annotations

import pytest

from saga2d import Anchor, Button, Game, Scene, Style


@pytest.fixture
def game():
    g = Game(
        "button-hover-transparency-test",
        resolution=(200, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _render(game: Game, button: Button) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(button)

    game._scene_stack.push(S())
    game.tick(dt=1 / 60)


def _hover_color_rects(game: Game) -> list[dict]:
    """Rects drawn using the theme's hover outline colour."""
    hover = game.theme.button_hover_outline_color
    return [r for r in game.backend.rects if r["color"] == hover]


def test_hovered_transparent_button_draws_no_outline(game: Game) -> None:
    """A hovered button with alpha-0 background emits no hover-glow rects."""
    transparent = Style(background_color=(0, 0, 0, 0), border_width=0)
    b = Button("Ghost", style=transparent, anchor=Anchor.CENTER)
    _render(game, b)

    # Force hover state.
    b._state = "hovered"  # type: ignore[assignment]
    game.tick(dt=1 / 60)

    assert _hover_color_rects(game) == [], (
        "Transparent button emitted a visible hover outline; "
        "expected zero rects at the theme's hover outline colour."
    )


def test_hovered_opaque_button_still_draws_outline(game: Game) -> None:
    """Regression guard the other way: opaque buttons keep the hover glow."""
    b = Button("Solid", anchor=Anchor.CENTER)  # default opaque bg
    _render(game, b)

    b._state = "hovered"  # type: ignore[assignment]
    game.tick(dt=1 / 60)

    assert len(_hover_color_rects(game)) >= 1, (
        "Opaque button must still draw a hover glow — this is its normal "
        "feedback."
    )
