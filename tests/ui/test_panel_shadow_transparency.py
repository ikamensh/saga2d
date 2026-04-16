"""Regression: Panel must not emit a shadow when its background is transparent.

Shipping a Panel as a transparent HUD row (HP + Coins grouped with
HORIZONTAL layout) produced a gray rectangle behind the text — the
panel's theme shadow was drawn even though there was no surface to
cast one. Caught by visual inspection of Ring of Pain v7.

The fix: skip shadow when the resolved background has alpha 0.
This test would have caught the bug without a screenshot.
"""

from __future__ import annotations

import pytest

from saga2d import Anchor, Game, Label, Layout, Panel, Scene, Style


@pytest.fixture
def game():
    g = Game(
        "panel-shadow-test",
        resolution=(200, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _render(game: Game, scene: Scene) -> None:
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)


def _fully_transparent_rects(game: Game) -> list[dict]:
    """Rects the mock backend drew with any fully-transparent colour."""
    return [r for r in game.backend.rects if r["color"][3] == 0]


def _shadow_matching_rects(game: Game, theme) -> list[dict]:
    """Rects drawn with the theme's shadow colour."""
    shadow = theme.panel_shadow_color
    return [r for r in game.backend.rects if r["color"] == shadow]


def test_transparent_panel_emits_no_shadow(game: Game) -> None:
    """A Panel with alpha-0 background produces zero shadow rects."""
    transparent = Style(
        background_color=(0, 0, 0, 0), border_width=0, padding=0,
    )

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(
                Panel(
                    anchor=Anchor.BOTTOM_LEFT, margin=10,
                    layout=Layout.HORIZONTAL, spacing=10,
                    style=transparent,
                    children=[Label("HP 10/10"), Label("Coins 0")],
                )
            )

    scene = S()
    _render(game, scene)

    # The theme's shadow colour must not appear among drawn rects.
    theme = game.theme
    assert theme.panel_shadow_offset > 0, "precondition: shadow enabled"
    shadow_draws = _shadow_matching_rects(game, theme)
    assert shadow_draws == [], (
        f"Transparent panel drew {len(shadow_draws)} shadow rects; "
        f"expected 0 because the background is alpha-0."
    )


def test_opaque_panel_still_emits_shadow(game: Game) -> None:
    """Regression guard in the other direction: opaque panels keep shadow."""
    opaque = Style(background_color=(50, 60, 80, 255))

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(
                Panel(
                    anchor=Anchor.CENTER,
                    style=opaque,
                    children=[Label("hello")],
                )
            )

    scene = S()
    _render(game, scene)

    theme = game.theme
    shadow_draws = _shadow_matching_rects(game, theme)
    assert len(shadow_draws) >= 1, (
        "Opaque panel must still cast a shadow — this is its normal look."
    )
