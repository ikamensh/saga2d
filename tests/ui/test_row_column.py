"""Properties of the Row / Column transparent-container helpers.

Row/Column are thin Panel subclasses whose purpose is to remove HUD-row
boilerplate. Tests verify they (a) produce no visible background/border,
(b) arrange children in the expected direction, (c) accept positional
children so declarative HUDs read naturally.
"""

from __future__ import annotations

import pytest

from saga2d import (
    Anchor,
    Column,
    Game,
    Label,
    Layout,
    Panel,
    Row,
    Scene,
    Style,
)


@pytest.fixture
def game():
    g = Game(
        "row-col-test",
        resolution=(200, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _render(game: Game, container: Panel) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(container)

    game._scene_stack.push(S())
    game.tick(dt=1 / 60)


def _shadow_color_rects(game: Game) -> list[dict]:
    shadow = game.theme.panel_shadow_color
    return [r for r in game.backend.rects if r["color"] == shadow]


def _opaque_rects(game: Game) -> list[dict]:
    """Rects that have alpha > 0 (visible background or border)."""
    return [r for r in game.backend.rects if r["color"][3] > 0]


def test_row_is_horizontal_panel() -> None:
    row = Row(Label("a"), Label("b"))
    assert isinstance(row, Panel)
    assert row.layout == Layout.HORIZONTAL


def test_column_is_vertical_panel() -> None:
    col = Column(Label("a"), Label("b"))
    assert isinstance(col, Panel)
    assert col.layout == Layout.VERTICAL


def test_row_children_laid_out_left_to_right(game: Game) -> None:
    a, b, c = Label("A"), Label("B"), Label("C")
    row = Row(a, b, c, spacing=4, anchor=Anchor.TOP_LEFT, margin=0)
    _render(game, row)

    # Row children sit on the same y, increasing x.
    assert a._computed_y == b._computed_y == c._computed_y
    assert a._computed_x < b._computed_x < c._computed_x


def test_column_children_laid_out_top_to_bottom(game: Game) -> None:
    a, b, c = Label("A"), Label("B"), Label("C")
    col = Column(a, b, c, spacing=4, anchor=Anchor.TOP_LEFT, margin=0)
    _render(game, col)

    assert a._computed_x == b._computed_x == c._computed_x
    assert a._computed_y < b._computed_y < c._computed_y


def test_row_emits_no_background_or_shadow_draws(game: Game) -> None:
    """A bare Row must be truly invisible as a container — no rect."""
    row = Row(Label("hp"), Label("mp"), anchor=Anchor.TOP_LEFT, margin=0)
    _render(game, row)

    assert _shadow_color_rects(game) == [], "Row drew a shadow"
    # Only rects drawn should be for visible content (none for bare labels
    # in mock backend), so no opaque container-background rect either.
    container_rects = [
        r for r in _opaque_rects(game)
        if r["width"] >= 1 and r["height"] >= 1
    ]
    # Label draws text, not rects — so there should be no visible rects at
    # all from a bare Row with Labels.
    assert container_rects == [], (
        f"Row emitted visible container rects: {container_rects}"
    )


def test_row_accepts_explicit_style_for_background(game: Game) -> None:
    """Row can be re-styled to *have* a background when needed."""
    opaque = Style(background_color=(30, 30, 60, 255), border_width=0)
    row = Row(Label("x"), style=opaque, anchor=Anchor.TOP_LEFT, margin=0)
    _render(game, row)

    visible = [r for r in _opaque_rects(game) if r["color"][0] == 30]
    assert len(visible) >= 1, (
        "Row with opaque style should draw at least one background rect"
    )
