"""Properties of reactive ``ProgressBar(value=callable)`` bindings.

Extends the reactive-Label pattern to another widget: the bar updates
from game state each frame without the game code manually pushing
``bar.value = new_value`` after every mutation.
"""

from __future__ import annotations

import math

import pytest

from saga2d import Game, Panel, ProgressBar, Scene


@pytest.fixture
def game():
    g = Game(
        "progressbar-reactive-test",
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


def test_reactive_value_updates_fraction(game: Game) -> None:
    state = {"hp": 80, "max": 100}
    bar = ProgressBar(value=lambda: state["hp"], max_value=lambda: state["max"])

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[bar]))

    _draw_once(game, S())
    assert math.isclose(bar.fraction, 0.8)

    state["hp"] = 40
    game.tick(dt=1 / 60)
    assert math.isclose(bar.fraction, 0.4)


def test_reactive_max_value_updates_fraction(game: Game) -> None:
    state = {"hp": 50, "max": 100}
    bar = ProgressBar(value=lambda: state["hp"], max_value=lambda: state["max"])

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[bar]))

    _draw_once(game, S())
    assert math.isclose(bar.fraction, 0.5)

    # Increase the maximum — fraction should drop, not stay pinned.
    state["max"] = 200
    game.tick(dt=1 / 60)
    assert math.isclose(bar.fraction, 0.25)


def test_explicit_assignment_unbinds(game: Game) -> None:
    counter = {"n": 0}

    def read() -> float:
        counter["n"] += 1
        return 0.5

    bar = ProgressBar(value=read, max_value=1.0)

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[bar]))

    _draw_once(game, S())
    assert counter["n"] >= 1

    bar.value = 0.9  # should detach callable
    frozen = counter["n"]
    game.tick(dt=1 / 60)
    game.tick(dt=1 / 60)
    assert counter["n"] == frozen
    assert math.isclose(bar.value, 0.9)


def test_static_value_unchanged(game: Game) -> None:
    """Non-callable values still behave the way they always did."""
    bar = ProgressBar(value=30, max_value=100)

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[bar]))

    _draw_once(game, S())
    assert math.isclose(bar.fraction, 0.3)
    bar.value = 50
    game.tick(dt=1 / 60)
    assert math.isclose(bar.fraction, 0.5)


def test_reactive_non_finite_raises(game: Game) -> None:
    """A callable returning NaN/inf fails clearly at draw time."""
    bar = ProgressBar(value=lambda: float("nan"), max_value=1.0)

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Panel(children=[bar]))

    game._scene_stack.push(S())
    with pytest.raises(ValueError):
        game.tick(dt=1 / 60)
