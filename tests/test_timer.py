"""Tests for TimerManager and Game.after/every/cancel."""

from __future__ import annotations

import pytest

from easygame import Game


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def game() -> Game:
    return Game("Test", backend="mock", resolution=(800, 600))


# ------------------------------------------------------------------
# after()
# ------------------------------------------------------------------


def test_after_fires_after_accumulated_dt(game: Game) -> None:
    """after() fires callback after correct elapsed time across ticks."""
    fired = []

    game.after(0.3, lambda: fired.append(True))

    game.tick(dt=0.1)
    assert len(fired) == 0
    game.tick(dt=0.1)
    assert len(fired) == 0
    game.tick(dt=0.1)
    assert len(fired) == 1


def test_after_returns_monotonic_id(game: Game) -> None:
    """after() returns distinct monotonic IDs."""
    id1 = game.after(1.0, lambda: None)
    id2 = game.after(1.0, lambda: None)
    id3 = game.after(1.0, lambda: None)
    assert id1 < id2 < id3


def test_after_zero_delay_fires_on_next_tick(game: Game) -> None:
    """Timer with 0 delay fires on next update, not immediately."""
    fired = []

    game.after(0.0, lambda: fired.append(True))
    assert len(fired) == 0

    game.tick(dt=0.016)
    assert len(fired) == 1


# ------------------------------------------------------------------
# every()
# ------------------------------------------------------------------


def test_every_fires_repeatedly(game: Game) -> None:
    """every() fires at correct intervals."""
    count = []

    game.every(0.2, lambda: count.append(1))

    game.tick(dt=0.2)
    assert len(count) == 1
    game.tick(dt=0.2)
    assert len(count) == 2
    game.tick(dt=0.2)
    assert len(count) == 3


def test_every_no_catchup_on_large_dt(game: Game) -> None:
    """Repeating timers fire at most once per update (no catch-up)."""
    count = []

    game.every(0.1, lambda: count.append(1))

    game.tick(dt=0.5)  # Would be 5 fires if we caught up
    assert len(count) == 1


# ------------------------------------------------------------------
# cancel()
# ------------------------------------------------------------------


def test_cancel_prevents_fire(game: Game) -> None:
    """cancel() prevents future fires."""
    fired = []

    tid = game.after(0.5, lambda: fired.append(True))
    game.tick(dt=0.2)
    game.cancel(tid)
    game.tick(dt=0.5)
    assert len(fired) == 0


def test_cancel_during_callback_is_safe(game: Game) -> None:
    """Cancelling another timer during a callback is safe."""
    order = []

    def fire_a() -> None:
        order.append("A")
        game.cancel(tid_b)

    def fire_b() -> None:
        order.append("B")

    # A fires first (added first), cancels B before B is processed
    game.after(0.1, fire_a)
    tid_b = game.after(0.1, fire_b)

    game.tick(dt=0.2)
    assert order == ["A"]  # B was cancelled by A's callback, never fired


def test_callback_creates_timer_not_fired_same_frame(game: Game) -> None:
    """Timer created in a callback does not fire in the same frame."""
    fired = []

    def create_timer() -> None:
        game.after(0.0, lambda: fired.append("nested"))

    game.after(0.0, create_timer)
    game.tick(dt=0.016)

    assert "nested" not in fired


def test_callback_creates_timer_fires_next_frame(game: Game) -> None:
    """Timer created in a callback fires on the next tick."""
    fired = []

    def create_timer() -> None:
        game.after(0.0, lambda: fired.append("nested"))

    game.after(0.0, create_timer)
    game.tick(dt=0.016)
    game.tick(dt=0.016)

    assert fired == ["nested"]


# ------------------------------------------------------------------
# cancel_all()
# ------------------------------------------------------------------


def test_cancel_all_clears_timers(game: Game) -> None:
    """cancel_all() clears all active timers."""
    fired = []

    game.after(0.5, lambda: fired.append(1))
    game.every(0.2, lambda: fired.append(2))
    game._timer_manager.cancel_all()

    game.tick(dt=1.0)
    assert len(fired) == 0
