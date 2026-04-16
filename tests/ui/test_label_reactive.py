"""Properties of reactive ``Label(text=callable)`` bindings.

Instead of asserting specific pixels on a screenshot (which is covered
by the visual harness), these tests verify the *binding semantics*:

* a callable text source is re-evaluated each draw
* the label's ``text`` property reflects the latest evaluation
* explicit ``label.text = "…"`` unbinds the callable
* static string behaviour is unchanged
"""

from __future__ import annotations

import pytest

from saga2d import Game, Label, Panel, Scene


@pytest.fixture
def game():
    g = Game(
        "reactive-label-test",
        resolution=(200, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _draw_once(game: Game, scene: Scene) -> None:
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)


def test_reactive_label_evaluates_on_draw(game: Game) -> None:
    """Label text reflects the callable's return value after a draw."""
    state = {"hp": 10, "max": 10}

    label = Label(lambda: f"HP {state['hp']}/{state['max']}")

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[label]))

    scene = S()
    _draw_once(game, scene)
    assert label.text == "HP 10/10"

    # Mutate the bound state; next draw picks it up without label.text =
    state["hp"] = 7
    game.tick(dt=1 / 60)
    assert label.text == "HP 7/10"


def test_reactive_label_unbinds_on_explicit_set(game: Game) -> None:
    """Assigning .text explicitly stops the callable from firing again."""
    counter = {"n": 0}

    def read() -> str:
        counter["n"] += 1
        return f"call #{counter['n']}"

    label = Label(read)

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[label]))

    scene = S()
    _draw_once(game, scene)
    before = counter["n"]
    assert before >= 1  # callable was invoked

    # Explicit assignment detaches the callable.
    label.text = "frozen"
    frozen_count = counter["n"]

    game.tick(dt=1 / 60)
    game.tick(dt=1 / 60)

    # No further calls to the callable after unbind.
    assert counter["n"] == frozen_count
    assert label.text == "frozen"


def test_static_string_label_unchanged(game: Game) -> None:
    """Plain-string Labels still behave the way they always did."""
    label = Label("Hello")

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[label]))

    scene = S()
    _draw_once(game, scene)

    assert label.text == "Hello"

    label.text = "World"
    game.tick(dt=1 / 60)
    assert label.text == "World"


def test_reactive_label_handles_none_like_empty(game: Game) -> None:
    """Callable returning an empty string is allowed (draw is a no-op)."""
    label = Label(lambda: "")

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[label]))

    scene = S()
    _draw_once(game, scene)

    assert label.text == ""
