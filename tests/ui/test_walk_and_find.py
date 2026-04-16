"""Properties of :meth:`Component.walk` / :meth:`.find` / :meth:`.find_all`.

These give tests and tooling a public surface into the UI tree. Before
iter-19, code that wanted to inspect scene widgets had to reach into
the private ``_children`` list.
"""

from __future__ import annotations

import pytest

from saga2d import Column, Game, Label, Panel, Row, Scene


@pytest.fixture
def game():
    g = Game(
        "walk-find-test",
        resolution=(100, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _build_scene(game: Game) -> Scene:
    """A small deterministic tree: Row(Label, Column(Label, Label))."""

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Row(
                Label("one"),
                Column(Label("two"), Label("three")),
                Label("four"),
            ))

    scene = S()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    return scene


def test_walk_yields_all_descendants_depth_first(game: Game) -> None:
    scene = _build_scene(game)
    components = list(scene.ui.walk())
    # Row + Label + Column + Label + Label + Label = 6 nodes (the _UIRoot
    # itself is not included because include_self defaults to False).
    assert len(components) == 6
    # Label texts encountered, in DFS order.
    label_texts = [c.text for c in components if isinstance(c, Label)]
    assert label_texts == ["one", "two", "three", "four"]


def test_walk_include_self_yields_root_first(game: Game) -> None:
    scene = _build_scene(game)
    first, *rest = list(scene.ui.walk(include_self=True))
    assert first is scene.ui


def test_find_returns_first_match(game: Game) -> None:
    scene = _build_scene(game)
    hit = scene.ui.find(lambda c: isinstance(c, Label) and c.text == "three")
    assert hit is not None
    assert hit.text == "three"


def test_find_returns_none_on_no_match(game: Game) -> None:
    scene = _build_scene(game)
    assert scene.ui.find(lambda c: False) is None


def test_find_all_returns_every_match(game: Game) -> None:
    scene = _build_scene(game)
    labels = scene.ui.find_all(lambda c: isinstance(c, Label))
    assert [c.text for c in labels] == ["one", "two", "three", "four"]


def test_find_all_returns_empty_on_no_match(game: Game) -> None:
    scene = _build_scene(game)
    assert scene.ui.find_all(lambda c: isinstance(c, Panel) and c.layout.value == "nope") == []


def test_walk_on_bare_component_yields_nothing() -> None:
    """A component with no children yields no descendants."""
    label = Label("leaf")
    assert list(label.walk()) == []


def test_walk_include_self_on_bare_component_yields_self() -> None:
    label = Label("leaf")
    result = list(label.walk(include_self=True))
    assert result == [label]
