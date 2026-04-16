"""Properties of the guess_the_number example — iter-34.

Fourth saga2d example: the finished form of the declarative
tutorial's progression. Tests mirror what every other example has:
input-logic, reactive-label refresh, save/load round-trip, snapshot
regression.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from examples.guess_the_number.guess_the_number import (
    GuessScene,
    build_theme,
)
from saga2d import Game, InputEvent, Label


@pytest.fixture
def game():
    g = Game(
        "guess-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
    )
    yield g
    g._teardown()


def _push(game: Game) -> GuessScene:
    scene = GuessScene()
    scene.target = 50  # deterministic for tests
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    return scene


def _press(key=None, action=None, shift=False) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action, shift=shift)


# -- bump controls ---------------------------------------------------------


def test_up_increments_by_one(game: Game) -> None:
    scene = _push(game)
    scene._dispatch_key_bindings(_press(key="up"))
    assert scene.current == 51


def test_w_alias_works(game: Game) -> None:
    scene = _push(game)
    scene._dispatch_key_bindings(_press(key="w"))
    assert scene.current == 51


def test_shift_up_jumps_by_ten(game: Game) -> None:
    """iter-17 modifier plumbing: bump_up takes optional event and
    reads event.shift to pick step size."""
    scene = _push(game)
    scene._dispatch_key_bindings(_press(key="up", shift=True))
    assert scene.current == 60


def test_bump_clamps_at_1_and_100(game: Game) -> None:
    scene = _push(game)
    scene.current = 100
    scene._dispatch_key_bindings(_press(key="up"))
    assert scene.current == 100
    scene.current = 1
    scene._dispatch_key_bindings(_press(key="down"))
    assert scene.current == 1


# -- guess logic -----------------------------------------------------------


def test_guess_correct_sets_hint(game: Game) -> None:
    scene = _push(game)
    scene.current = 50  # == target
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert "Correct" in scene.hint
    assert scene.guesses == 1


def test_guess_too_low_reports_higher(game: Game) -> None:
    scene = _push(game)
    scene.current = 20
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.hint == "Higher"


def test_guess_too_high_reports_lower(game: Game) -> None:
    scene = _push(game)
    scene.current = 80
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.hint == "Lower"


def test_reset_picks_new_target_and_zeros_count(game: Game) -> None:
    scene = _push(game)
    scene._dispatch_key_bindings(_press(action="confirm"))
    scene._dispatch_key_bindings(_press(action="confirm"))
    scene._dispatch_key_bindings(_press(key="r"))
    assert scene.guesses == 0
    assert scene.current == 50
    assert 1 <= scene.target <= 100


# -- reactive HUD refresh --------------------------------------------------


def test_display_label_reflects_current(game: Game) -> None:
    scene = _push(game)
    scene._dispatch_key_bindings(_press(key="up", shift=True))
    game.tick(dt=1 / 60)
    display = scene.ui.find(
        lambda c: isinstance(c, Label) and c.text == "60"
    )
    assert display is not None


def test_guesses_label_updates_on_guess(game: Game) -> None:
    scene = _push(game)
    scene.current = 20
    scene._dispatch_key_bindings(_press(action="confirm"))
    game.tick(dt=1 / 60)
    guesses_label = scene.ui.find(
        lambda c: isinstance(c, Label) and c.text == "Guesses 1"
    )
    assert guesses_label is not None


# -- save/load round trip --------------------------------------------------


def test_save_load_round_trip(tmp_path: Path) -> None:
    game = Game(
        "guess-save-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
        save_dir=tmp_path,
    )
    try:
        scene = GuessScene()
        scene.target = 42
        scene.current = 37
        scene.guesses = 3
        scene.hint = "Higher"
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)
        game.save(slot=1)
    finally:
        game._teardown()

    game = Game(
        "guess-load-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
        save_dir=tmp_path,
    )
    try:
        restored = GuessScene()
        game._scene_stack.push(restored)
        game.tick(dt=1 / 60)
        game.load(slot=1)
        assert restored.target == 42
        assert restored.current == 37
        assert restored.guesses == 3
        assert restored.hint == "Higher"
    finally:
        game._teardown()


# -- snapshot --------------------------------------------------------------


def test_scene_structure_stable(game: Game, assert_snapshot) -> None:
    scene = GuessScene()
    scene.target = 50
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    assert_snapshot(scene, "guess_the_number")
