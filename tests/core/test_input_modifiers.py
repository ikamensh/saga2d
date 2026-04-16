"""Properties of the iter-17 InputEvent modifier fields.

End-to-end: mock backend inject_key(..., shift=True) flows through
InputManager.translate → InputEvent, and event-aware Scene handlers
read the modifier booleans.
"""

from __future__ import annotations

import pytest

from saga2d import Game, InputEvent, Scene


@pytest.fixture
def game():
    g = Game(
        "input-modifiers-test",
        resolution=(100, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def test_inject_key_no_modifiers_defaults_false(game: Game) -> None:
    game.backend.inject_key("a")
    events = game._input.translate(game.backend.poll_events())
    assert len(events) == 1
    ev = events[0]
    assert ev.shift is False
    assert ev.ctrl is False
    assert ev.alt is False
    assert ev.meta is False


def test_inject_key_shift_flows_to_input_event(game: Game) -> None:
    game.backend.inject_key("r", shift=True)
    events = game._input.translate(game.backend.poll_events())
    ev = events[0]
    assert ev.shift is True
    assert ev.ctrl is False


def test_inject_key_meta_plus_ctrl(game: Game) -> None:
    game.backend.inject_key("z", meta=True, ctrl=True)
    ev = game._input.translate(game.backend.poll_events())[0]
    assert ev.meta is True
    assert ev.ctrl is True


def test_event_aware_handler_reads_modifier_state(game: Game) -> None:
    """A Scene.controls method taking one arg can read event.shift and
    route behaviour accordingly. This is the iter-11 event-aware
    dispatch meeting the iter-17 modifier plumbing end-to-end."""
    hits: list[str] = []

    class S(Scene):
        controls = {"r": "reset"}

        def reset(self, event: InputEvent) -> None:
            hits.append("checkpoint" if event.shift else "full")

    scene = S()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)

    game.backend.inject_key("r", shift=True)
    game.tick(dt=1 / 60)
    game.backend.inject_key("r")
    game.tick(dt=1 / 60)

    assert hits == ["checkpoint", "full"]


def test_bind_key_handler_sees_modifiers(game: Game) -> None:
    captured: list[bool] = []

    class S(Scene):
        def on_enter(self) -> None:
            self.bind_key("k", lambda ev: captured.append(ev.ctrl))

    game._scene_stack.push(S())
    game.tick(dt=1 / 60)

    game.backend.inject_key("k", ctrl=True)
    game.tick(dt=1 / 60)
    game.backend.inject_key("k")
    game.tick(dt=1 / 60)

    assert captured == [True, False]
