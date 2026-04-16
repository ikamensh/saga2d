"""Properties of ``Scene.controls`` — class-level declarative input map.

Tests cover:
- single-string keys route to the named method
- tuple-aliased keys each route to the same method
- class-level normalisation happens once per subclass definition
- instance ``bind_key`` overrides class-level entries
- unknown keys return False (fall through)
- action names route just like raw keys
"""

from __future__ import annotations

import pytest

from saga2d import Game, InputEvent, Scene


@pytest.fixture
def game():
    g = Game(
        "controls-test",
        resolution=(100, 100),
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


def _press(key: str | None = None, action: str | None = None) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action)


def test_single_string_key_dispatches_to_method(game: Game) -> None:
    hits: list[str] = []

    class S(Scene):
        controls = {"space": "fire"}

        def fire(self) -> None:
            hits.append("bang")

    scene = _push(game, S())
    assert scene._dispatch_key_bindings(_press(key="space")) is True
    assert hits == ["bang"]


def test_tuple_aliases_share_one_method(game: Game) -> None:
    hits: list[str] = []

    class S(Scene):
        controls = {
            ("right", "d"): "cw",
            ("left", "a"): "ccw",
        }

        def cw(self) -> None:
            hits.append("cw")

        def ccw(self) -> None:
            hits.append("ccw")

    scene = _push(game, S())
    for key in ("right", "d"):
        scene._dispatch_key_bindings(_press(key=key))
    for key in ("left", "a"):
        scene._dispatch_key_bindings(_press(key=key))
    assert hits == ["cw", "cw", "ccw", "ccw"]


def test_normalisation_happens_once_per_subclass() -> None:
    """__init_subclass__ flattens tuples — the subclass attribute is
    populated as soon as the class is defined, no instance needed."""

    class S(Scene):
        controls = {
            ("a", "b"): "m",
            "c": "m",
        }

    assert S._normalised_controls == {"a": "m", "b": "m", "c": "m"}


def test_instance_bind_key_overrides_class_controls(game: Game) -> None:
    hits: list[str] = []

    class S(Scene):
        controls = {"space": "cls_method"}

        def cls_method(self) -> None:
            hits.append("class")

    scene = _push(game, S())
    scene.bind_key("space", lambda: hits.append("instance"))

    scene._dispatch_key_bindings(_press(key="space"))
    assert hits == ["instance"]  # bind_key wins


def test_unknown_key_returns_false(game: Game) -> None:
    class S(Scene):
        controls = {"a": "noop"}

        def noop(self) -> None:
            pass

    scene = _push(game, S())
    assert scene._dispatch_key_bindings(_press(key="z")) is False


def test_action_dispatch_matches_controls(game: Game) -> None:
    """Named actions (confirm/cancel) resolve against controls exactly like
    raw keys. The dispatcher tries action first, then raw key."""
    hits: list[str] = []

    class S(Scene):
        controls = {"confirm": "select"}

        def select(self) -> None:
            hits.append("select")

    scene = _push(game, S())
    scene._dispatch_key_bindings(_press(action="confirm", key="return"))
    assert hits == ["select"]


def test_missing_method_does_not_crash(game: Game) -> None:
    """A typo'd method name silently falls through — better than
    crashing mid-game on a key press."""

    class S(Scene):
        controls = {"x": "this_method_does_not_exist"}

    scene = _push(game, S())
    assert scene._dispatch_key_bindings(_press(key="x")) is False


def test_empty_controls_is_fine(game: Game) -> None:
    """No controls declared → dispatch falls through cleanly."""

    class S(Scene):
        pass

    scene = _push(game, S())
    assert scene._dispatch_key_bindings(_press(key="space")) is False
