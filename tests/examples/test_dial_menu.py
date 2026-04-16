"""Properties of the dial_menu example.

Tests live alongside the framework tests because the dial menu is this
iteration's "generalisation check" — proof the saga2d API stack
(Scene.controls, reactive Label, ring_positions, ring_budget, themed
text styles) composes cleanly into a second game under 100 LOC.
"""

from __future__ import annotations

import pytest

from examples.dial_menu.dial_menu import DialMenuScene, build_theme
from saga2d import Game, InputEvent


@pytest.fixture
def game():
    g = Game(
        "dial-menu-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
    )
    yield g
    g._teardown()


def _push(game: Game, scene: DialMenuScene) -> DialMenuScene:
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    return scene


def _press(key: str | None = None, action: str | None = None) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action)


def test_initial_selection_is_zero(game: Game) -> None:
    scene = _push(game, DialMenuScene())
    assert scene.selected == 0


def test_right_arrow_rotates_clockwise(game: Game) -> None:
    scene = _push(game, DialMenuScene())
    scene._dispatch_key_bindings(_press(key="right"))
    assert scene.selected == 1
    scene._dispatch_key_bindings(_press(key="d"))  # WASD alias
    assert scene.selected == 2


def test_left_arrow_rotates_counterclockwise_and_wraps(game: Game) -> None:
    scene = _push(game, DialMenuScene())
    scene._dispatch_key_bindings(_press(key="left"))
    assert scene.selected == len(scene.options) - 1  # wrapped


def test_confirm_updates_status_with_selection(game: Game) -> None:
    scene = _push(game, DialMenuScene())
    scene._dispatch_key_bindings(_press(key="right"))
    scene._dispatch_key_bindings(_press(key="right"))
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.options[scene.selected] in scene.status
    assert "Selected" in scene.status


def test_cancel_action_updates_status(game: Game) -> None:
    scene = _push(game, DialMenuScene())
    scene._dispatch_key_bindings(_press(action="cancel"))
    assert scene.status.lower() == "cancelled."


def test_custom_options_length_respected(game: Game) -> None:
    scene = _push(game, DialMenuScene(options=["A", "B", "C"]))
    assert len(scene.options) == 3
    # Wrap after three right-presses.
    for _ in range(3):
        scene._dispatch_key_bindings(_press(key="right"))
    assert scene.selected == 0


def test_controls_dict_is_validated_at_class_def() -> None:
    """DialMenuScene's controls dict survived the iter-11 hasattr check,
    so the class loaded at import. If it didn't, this import would have
    crashed before the test ran. Belt-and-braces: make the assumption
    explicit."""
    for method_name in DialMenuScene._normalised_controls.values():
        assert hasattr(DialMenuScene, method_name), (
            f"DialMenuScene declares controls method '{method_name}' "
            f"that does not exist."
        )
