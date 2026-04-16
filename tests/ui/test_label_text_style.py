"""Properties of ``Label(text_style=…)`` theme-driven styling.

These tests mirror what ``Scene.draw_text(style="hud")`` already does
for imperative text — named theme styles become the single source of
truth for appearance, with explicit kwargs overriding per-label.
"""

from __future__ import annotations

import pytest

from saga2d import Game, Label, Panel, Scene, TextStyle, Theme


@pytest.fixture
def game():
    g = Game(
        "label-text-style-test",
        resolution=(200, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _render(game: Game, label: Label) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[label]))

    game._scene_stack.push(S())
    game.tick(dt=1 / 60)


def test_string_text_style_resolves_from_theme(game: Game) -> None:
    """``text_style="title"`` pulls font_size + color from the theme's map."""
    label = Label("Hi", text_style="title")
    _render(game, label)

    text_style = game.theme.get_text_style("title")
    resolved = label._resolve_style()
    assert resolved.font_size == text_style.font_size
    assert resolved.text_color == text_style.color


def test_textstyle_instance_takes_effect(game: Game) -> None:
    ts = TextStyle(font_size=40, color=(1, 2, 3, 255))
    label = Label("Hi", text_style=ts)
    _render(game, label)
    resolved = label._resolve_style()
    assert resolved.font_size == 40
    assert resolved.text_color == (1, 2, 3, 255)


def test_explicit_kwargs_override_text_style(game: Game) -> None:
    """A caller-supplied font_size / text_color wins over the named style."""
    label = Label(
        "Hi",
        text_style="title",
        font_size=9,
        text_color=(7, 7, 7, 255),
    )
    _render(game, label)
    resolved = label._resolve_style()
    assert resolved.font_size == 9
    assert resolved.text_color == (7, 7, 7, 255)


def test_theme_override_restyles_labels_without_touching_call_site(
    game: Game,
) -> None:
    """Swap the theme's `title` style and every ``text_style="title"``
    label restyles — the central-config win."""
    game.theme = Theme(
        text_styles={"title": TextStyle(font_size=77, color=(9, 9, 9, 255))},
    )
    label = Label("Hi", text_style="title")
    _render(game, label)
    resolved = label._resolve_style()
    assert resolved.font_size == 77
    assert resolved.text_color == (9, 9, 9, 255)


def test_unknown_text_style_name_raises(game: Game) -> None:
    """Typoed style names fail loudly at draw time, not silently."""
    label = Label("Hi", text_style="ttle")  # misspelt

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[label]))

    game._scene_stack.push(S())
    with pytest.raises(KeyError):
        game.tick(dt=1 / 60)


def test_no_text_style_uses_theme_label_defaults(game: Game) -> None:
    """Labels without any style still get the theme's label default colour."""
    label = Label("Hi")
    _render(game, label)
    resolved = label._resolve_style()
    # Label default text_color is the theme's label_text_color (near-white).
    assert resolved.text_color == (248, 250, 252, 255)
