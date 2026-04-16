"""Handlers may optionally accept the raw InputEvent as an argument.

Backward-compatible: existing zero-arg handlers are called with no
args. Event-accepting handlers (either via ``controls`` or
``bind_key``) get the full :class:`InputEvent`.
"""

from __future__ import annotations

import pytest

from saga2d import Game, InputEvent, Scene


@pytest.fixture
def game():
    g = Game(
        "event-handler-test",
        resolution=(100, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _press(key: str | None = None, action: str | None = None) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action)


def _push(game: Game, scene: Scene) -> Scene:
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    return scene


def test_zero_arg_controls_method_called_with_no_args(game: Game) -> None:
    captured: list[str] = []

    class S(Scene):
        controls = {"space": "fire"}

        def fire(self) -> None:
            captured.append("noarg")

    scene = _push(game, S())
    scene._dispatch_key_bindings(_press(key="space"))
    assert captured == ["noarg"]


def test_one_arg_controls_method_gets_event(game: Game) -> None:
    captured: list[InputEvent] = []

    class S(Scene):
        controls = {"space": "fire"}

        def fire(self, event: InputEvent) -> None:
            captured.append(event)

    scene = _push(game, S())
    ev = _press(key="space", action="confirm")
    scene._dispatch_key_bindings(ev)
    assert len(captured) == 1
    assert captured[0].key == "space"
    assert captured[0].action == "confirm"


def test_zero_arg_bind_key_lambda_works(game: Game) -> None:
    hits: list[str] = []

    class S(Scene):
        def on_enter(self) -> None:
            self.bind_key("x", lambda: hits.append("z"))

    scene = _push(game, S())
    scene._dispatch_key_bindings(_press(key="x"))
    assert hits == ["z"]


def test_one_arg_bind_key_lambda_gets_event(game: Game) -> None:
    captured: list[str | None] = []

    class S(Scene):
        def on_enter(self) -> None:
            self.bind_key("x", lambda ev: captured.append(ev.key))

    scene = _push(game, S())
    scene._dispatch_key_bindings(_press(key="x"))
    assert captured == ["x"]


def test_repeated_presses_all_fire_correctly(game: Game) -> None:
    """Cache or no cache — signature inspection must produce the same
    verdict on every dispatch. Five presses => five callback hits."""
    calls: list[InputEvent] = []

    def handler(ev: InputEvent) -> None:
        calls.append(ev)

    class S(Scene):
        def on_enter(self) -> None:
            self.bind_key("x", handler)

    scene = _push(game, S())
    for _ in range(5):
        scene._dispatch_key_bindings(_press(key="x"))
    assert len(calls) == 5
