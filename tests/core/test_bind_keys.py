"""Properties of ``Scene.bind_keys`` — list form for multi-key aliases."""

from __future__ import annotations

import pytest

from saga2d import Game, InputEvent, Scene


@pytest.fixture
def game():
    g = Game(
        "bind-keys-test",
        resolution=(100, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def test_bind_keys_registers_all_aliases(game: Game) -> None:
    hits: list[str] = []

    class S(Scene):
        def on_enter(self) -> None:
            self.bind_keys(["right", "d"], lambda: hits.append("cw"))
            self.bind_keys(["left", "a"], lambda: hits.append("ccw"))

    game._scene_stack.push(S())
    game.tick(dt=1 / 60)

    scene = game._scene_stack.top()
    for key in ("right", "d", "left", "a"):
        assert key in scene._key_handlers, (
            f"bind_keys did not register alias {key!r}"
        )


def test_bind_keys_single_callback_fires_per_alias(game: Game) -> None:
    hits: list[str] = []

    class S(Scene):
        def on_enter(self) -> None:
            self.bind_keys(["space", "confirm"], lambda: hits.append("X"))

    scene = S()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)

    # Dispatch via the same pathway handle_input uses.
    assert scene._dispatch_key_bindings(
        InputEvent(type="key_press", key="space", action=None)
    )
    assert scene._dispatch_key_bindings(
        InputEvent(type="key_press", key="return", action="confirm")
    )
    assert hits == ["X", "X"]


def test_bind_keys_tuple_input_accepted(game: Game) -> None:
    """Tuple of aliases is accepted (bind_keys takes list or tuple)."""
    hit = {"n": 0}

    class S(Scene):
        def on_enter(self) -> None:
            self.bind_keys(("escape", "cancel"), lambda: hit.__setitem__("n", hit["n"] + 1))

    scene = S()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)

    assert "escape" in scene._key_handlers
    assert "cancel" in scene._key_handlers
