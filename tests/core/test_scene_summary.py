"""Properties of :meth:`Scene.summary` — Keras ``Model.summary()``-style dump.

Tests check shape, not literal strings: what information is present, not
how commas are spaced. Lets the formatting evolve without breaking
tests.
"""

from __future__ import annotations

import pytest

from saga2d import (
    Anchor,
    Game,
    Label,
    ProgressBar,
    Row,
    Scene,
)


@pytest.fixture
def game():
    g = Game(
        "summary-test",
        resolution=(200, 200),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _push(game: Game, scene: Scene) -> Scene:
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    return scene


def test_summary_includes_scene_class_name(game: Game) -> None:
    class MyFancyScene(Scene):
        pass

    scene = _push(game, MyFancyScene())
    out = scene.summary()
    assert "Scene: MyFancyScene" in out


def test_summary_includes_background_color_when_set(game: Game) -> None:
    class S(Scene):
        background_color = (10, 20, 30, 255)

    scene = _push(game, S())
    out = scene.summary()
    assert "background_color" in out
    assert "10" in out and "20" in out and "30" in out


def test_summary_skips_background_when_none(game: Game) -> None:
    class S(Scene):
        pass  # background_color default None

    scene = _push(game, S())
    out = scene.summary()
    assert "background_color" not in out


def test_summary_groups_aliased_controls_on_one_line(game: Game) -> None:
    """Tuple-aliased keys should appear together pointing at one method
    — the point of grouping is readability."""

    class S(Scene):
        controls = {
            ("right", "d"): "step_cw",
            ("left", "a"): "step_ccw",
        }

        def step_cw(self) -> None: pass
        def step_ccw(self) -> None: pass

    scene = _push(game, S())
    out = scene.summary()
    # Both aliases on the same line, arrow to method.
    cw_line = next(l for l in out.splitlines() if "step_cw" in l)
    assert "right" in cw_line and "d" in cw_line
    ccw_line = next(l for l in out.splitlines() if "step_ccw" in l)
    assert "left" in ccw_line and "a" in ccw_line


def test_summary_labels_show_literal_text_when_static(game: Game) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("Static Title"))

    scene = _push(game, S())
    out = scene.summary()
    assert '"Static Title"' in out


def test_summary_labels_show_callable_marker_when_reactive(game: Game) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(lambda: "dynamic"))

    scene = _push(game, S())
    out = scene.summary()
    assert "← callable" in out


def test_summary_includes_text_style_tag(game: Game) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("X", text_style="hud"))

    scene = _push(game, S())
    out = scene.summary()
    assert "text_style=hud" in out


def test_summary_includes_anchor_and_margin(game: Game) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("X", anchor=Anchor.TOP_LEFT, margin=12))

    scene = _push(game, S())
    out = scene.summary()
    assert "TOP_LEFT" in out
    assert "margin=12" in out


def test_summary_progressbar_shows_callable_marker(game: Game) -> None:
    class S(Scene):
        hp = 7
        max_hp = 10

        def on_enter(self) -> None:
            self.ui.add(ProgressBar(
                value=lambda: self.hp,
                max_value=lambda: self.max_hp,
            ))

    scene = _push(game, S())
    out = scene.summary()
    assert "ProgressBar" in out
    assert "← callable" in out


def test_summary_indents_nested_children(game: Game) -> None:
    """A Row inside the UI tree should render its children indented one
    level deeper than the Row itself."""

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Row(Label("child1"), Label("child2")))

    scene = _push(game, S())
    lines = scene.summary().splitlines()
    # Find the Row line and the first child line after it.
    row_line_idx = next(i for i, l in enumerate(lines) if "Row" in l)
    child_line = lines[row_line_idx + 1]
    row_line = lines[row_line_idx]
    row_indent = len(row_line) - len(row_line.lstrip())
    child_indent = len(child_line) - len(child_line.lstrip())
    assert child_indent > row_indent


def test_summary_empty_scene_still_renders(game: Game) -> None:
    """A bare Scene with no controls, no UI — summary shouldn't crash."""

    class S(Scene):
        pass

    scene = _push(game, S())
    out = scene.summary()
    assert "Scene: S" in out
    # No "controls:" header when the dict is empty.
    assert "controls:" not in out


def test_summary_returns_multiline_string(game: Game) -> None:
    class S(Scene):
        controls = {"a": "foo"}

        def foo(self) -> None: pass

    scene = _push(game, S())
    out = scene.summary()
    assert isinstance(out, str)
    assert "\n" in out  # multi-line
