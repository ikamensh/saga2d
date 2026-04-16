"""Save/load round-trip for the dial_menu example — iter-31 parity
with iter-29's Ring-of-Pain save/load tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from examples.dial_menu.dial_menu import DialMenuScene, build_theme
from saga2d import Game, InputEvent, Label


def _make_game(save_dir: Path) -> Game:
    return Game(
        "dial-menu-save-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
        save_dir=save_dir,
    )


def _press(key: str | None = None, action: str | None = None) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action)


def test_save_load_round_trip_preserves_selection_and_status(
    tmp_path: Path,
) -> None:
    game = _make_game(tmp_path)
    scene = DialMenuScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)

    scene._dispatch_key_bindings(_press(key="right"))
    scene._dispatch_key_bindings(_press(key="right"))
    scene._dispatch_key_bindings(_press(action="confirm"))
    saved_index = scene.selector.index
    saved_status = scene.status
    saved_options = list(scene.selector.options)

    game.save(slot=1)
    game._teardown()

    game = _make_game(tmp_path)
    restored = DialMenuScene()
    game._scene_stack.push(restored)
    game.tick(dt=1 / 60)
    data = game.load(slot=1)

    assert data is not None
    assert restored.selector.index == saved_index
    assert restored.status == saved_status
    assert list(restored.selector.options) == saved_options
    game._teardown()


def test_reactive_label_refreshes_after_load(tmp_path: Path) -> None:
    """The selector.value binding (heading label) picks up the loaded
    selection automatically."""
    game = _make_game(tmp_path)
    scene = DialMenuScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    # Move to a non-zero option then save.
    scene._dispatch_key_bindings(_press(key="right"))
    scene._dispatch_key_bindings(_press(key="right"))
    scene._dispatch_key_bindings(_press(key="right"))
    expected_value = scene.selector.value
    game.save(slot=3)
    game._teardown()

    game = _make_game(tmp_path)
    restored = DialMenuScene()
    game._scene_stack.push(restored)
    game.tick(dt=1 / 60)
    game.load(slot=3)
    game.tick(dt=1 / 60)

    # The heading label is reactive, bound to lambda: self.selector.value.
    heading = restored.ui.find(
        lambda c: isinstance(c, Label) and c.text == expected_value
    )
    assert heading is not None, (
        f"Reactive heading label didn't pick up loaded value "
        f"{expected_value!r}"
    )
    game._teardown()


def test_save_includes_options_for_version_drift(tmp_path: Path) -> None:
    """The saved state includes the options list itself, not just the
    index. If a future version renames an option, loading an old save
    still lands the user on the position they had."""
    game = _make_game(tmp_path)
    scene = DialMenuScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    data = scene.get_save_state()
    assert data["options"] == list(scene.selector.options)
    game._teardown()
