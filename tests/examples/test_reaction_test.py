"""Properties of the reaction_test example — iter-37.

Fifth saga2d example. The iter-37 rationale: the iter-25 retrospective
missed timers (``Scene.after`` / ``Scene.every``) from the "untested
subsystems" list. This example exercises them via a game's natural
state machine (wait → ready → done), and the tests verify both the
game logic and the timer integration end-to-end through
``game.tick(dt=…)``.
"""

from __future__ import annotations

import pytest

from examples.reaction_test.reaction_test import (
    STATE_DONE,
    STATE_EARLY,
    STATE_READY,
    STATE_WAITING,
    ReactionTestScene,
    build_theme,
)
from saga2d import Game, InputEvent


@pytest.fixture
def game():
    g = Game(
        "reaction-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
    )
    yield g
    g._teardown()


def _push(game: Game) -> ReactionTestScene:
    scene = ReactionTestScene()
    game._scene_stack.push(scene)
    game.tick(dt=0.0)
    return scene


def _press(key=None, action=None) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action)


# -- initial state --------------------------------------------------------


def test_initial_state_is_waiting(game: Game) -> None:
    scene = _push(game)
    assert scene.state == STATE_WAITING
    assert scene.attempts == 0
    assert scene.best is None


# -- timer-driven transitions ---------------------------------------------


def test_go_green_fires_after_scheduled_delay(game: Game) -> None:
    """``Scene.after(delay, cb)`` fires on the first tick whose
    accumulated dt has exceeded *delay*. Force a known schedule
    by replacing ``_schedule_go_green`` with a fixed 0.5 s delay."""
    scene = ReactionTestScene()
    game._scene_stack.push(scene)

    # Override the scheduled timer created by on_enter — cancel it and
    # schedule a deterministic one.
    scene._owned_timers = set()  # type: ignore[attr-defined]
    scene.after(0.5, scene._go_green)

    # 0.4 s elapsed — not there yet.
    game.tick(dt=0.4)
    assert scene.state == STATE_WAITING

    # Another 0.2 s — total 0.6 s, past the 0.5 s threshold.
    game.tick(dt=0.2)
    assert scene.state == STATE_READY


def test_click_before_green_marks_early(game: Game) -> None:
    scene = _push(game)
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.state == STATE_EARLY
    assert scene.attempts == 0


def test_click_when_ready_records_reaction_and_advances(game: Game) -> None:
    scene = ReactionTestScene()
    game._scene_stack.push(scene)
    game.tick(dt=0.0)
    # Force READY immediately.
    scene._go_green()
    assert scene.state == STATE_READY
    # Simulate a short reaction time by moving the clock reference.
    scene.ready_at -= 0.25
    scene._dispatch_key_bindings(_press(key="space"))
    assert scene.state == STATE_DONE
    assert scene.last_reaction is not None
    assert scene.last_reaction > 0.2
    assert scene.attempts == 1
    assert scene.best == scene.last_reaction


def test_best_tracks_minimum_across_attempts(game: Game) -> None:
    scene = ReactionTestScene()
    game._scene_stack.push(scene)
    game.tick(dt=0.0)

    # Simulate three attempts with known reaction times.
    for fake_reaction in (0.35, 0.20, 0.45):
        scene.state = STATE_READY
        scene.ready_at = 0.0  # "now" minus fake_reaction would be negative
        # Force a precise reaction time by temporarily patching time.
        import time as _time
        orig = _time.monotonic
        _time.monotonic = lambda: fake_reaction  # type: ignore[assignment]
        try:
            scene.click()
        finally:
            _time.monotonic = orig

    assert scene.attempts == 3
    assert scene.best == pytest.approx(0.20)


def test_reset_returns_to_waiting_and_rearms_timer(game: Game) -> None:
    """Reset should put the scene back into STATE_WAITING and schedule
    a fresh go-green timer — the mechanism a real player uses to try
    again after 'too early'."""
    scene = _push(game)
    # Force early-click state.
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.state == STATE_EARLY
    # Reset.
    scene._dispatch_key_bindings(_press(key="r"))
    assert scene.state == STATE_WAITING
    assert scene.last_reaction is None
    # The reset scheduled a new timer — after a long tick we should
    # reach READY (assuming the random delay is ≤ 3.0 s).
    game.tick(dt=3.1)
    assert scene.state == STATE_READY


# -- status-text reactive bindings ----------------------------------------


def test_status_text_reflects_each_state(game: Game) -> None:
    scene = _push(game)
    assert "Wait" in scene._status_text()
    scene.state = STATE_READY
    assert scene._status_text() == "CLICK!"
    scene.state = STATE_DONE
    scene.last_reaction = 0.312
    assert "312" in scene._status_text()  # 312 ms
    scene.state = STATE_EARLY
    assert "early" in scene._status_text().lower()


def test_last_text_shows_dash_when_no_attempts(game: Game) -> None:
    scene = _push(game)
    assert scene._last_text() == "Last —"
    assert scene._best_text() == "Best —"


def test_click_after_done_is_ignored(game: Game) -> None:
    """Once DONE, further clicks don't touch attempts / best / state —
    the user has to press R to try again."""
    scene = ReactionTestScene()
    game._scene_stack.push(scene)
    game.tick(dt=0.0)
    scene.state = STATE_DONE
    scene.attempts = 5
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.state == STATE_DONE
    assert scene.attempts == 5


# -- snapshot -------------------------------------------------------------


def test_scene_structure_stable(game: Game, assert_snapshot) -> None:
    scene = ReactionTestScene()
    game._scene_stack.push(scene)
    game.tick(dt=0.0)
    assert_snapshot(scene, "reaction_test")
