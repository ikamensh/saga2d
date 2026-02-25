"""Tests for TimerHandle.then() chaining."""

from __future__ import annotations

import pytest

from easygame.util.timer import TimerHandle, TimerManager


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture
def tm() -> TimerManager:
    return TimerManager()


# ------------------------------------------------------------------
# Basic chaining
# ------------------------------------------------------------------


def test_basic_then_fires_after_parent(tm: TimerManager) -> None:
    """after().then() fires the child only after the parent completes."""
    order: list[str] = []

    tm.after(0.1, lambda: order.append("A")).then(
        lambda: order.append("B"), 0.1,
    )

    tm.update(0.05)
    assert order == []

    tm.update(0.05)  # t=0.1 — A fires, B scheduled
    assert order == ["A"]

    tm.update(0.05)  # t=0.15 — B not yet
    assert order == ["A"]

    tm.update(0.05)  # t=0.2 — B fires
    assert order == ["A", "B"]


def test_chained_thens_sequential(tm: TimerManager) -> None:
    """A three-step chain fires sequentially, not in parallel."""
    order: list[str] = []

    tm.after(0.1, lambda: order.append("A")).then(
        lambda: order.append("B"), 0.1,
    ).then(
        lambda: order.append("C"), 0.1,
    )

    tm.update(0.1)  # A fires
    assert order == ["A"]

    tm.update(0.1)  # B fires
    assert order == ["A", "B"]

    tm.update(0.1)  # C fires
    assert order == ["A", "B", "C"]


# ------------------------------------------------------------------
# Cancellation
# ------------------------------------------------------------------


def test_cancel_parent_prevents_chain(tm: TimerManager) -> None:
    """Cancelling before any timer fires prevents the entire chain."""
    order: list[str] = []

    handle = tm.after(0.1, lambda: order.append("A")).then(
        lambda: order.append("B"), 0.1,
    )

    tm.cancel(handle)
    tm.update(0.5)
    assert order == []


def test_cancel_handle_mid_chain(tm: TimerManager) -> None:
    """Cancelling after the first step prevents remaining steps."""
    order: list[str] = []

    handle = tm.after(0.1, lambda: order.append("A")).then(
        lambda: order.append("B"), 0.1,
    ).then(
        lambda: order.append("C"), 0.1,
    )

    tm.update(0.1)  # A fires, B scheduled
    assert order == ["A"]

    tm.cancel(handle)  # cancels B (C was never scheduled)
    tm.update(0.5)
    assert order == ["A"]


# ------------------------------------------------------------------
# Repeating timers
# ------------------------------------------------------------------


def test_repeating_timer_then_fires_after_each(tm: TimerManager) -> None:
    """every().then() fires the chained callback after each repetition."""
    order: list[str] = []

    tm.every(0.5, lambda: order.append("A")).then(
        lambda: order.append("B"), 0.1,
    )

    tm.update(0.5)  # A fires
    assert order == ["A"]

    tm.update(0.1)  # B fires
    assert order == ["A", "B"]

    tm.update(0.4)  # second A fires (0.5 interval reset)
    assert order == ["A", "B", "A"]

    tm.update(0.1)  # second B fires
    assert order == ["A", "B", "A", "B"]


def test_cancel_repeating_timer_chain(tm: TimerManager) -> None:
    """Cancelling a repeating handle stops repeats and pending children."""
    order: list[str] = []

    handle = tm.every(0.5, lambda: order.append("A")).then(
        lambda: order.append("B"), 0.1,
    )

    tm.update(0.5)  # A fires, B scheduled
    assert order == ["A"]

    tm.cancel(handle)  # cancel everything

    tm.update(0.1)  # B should not fire
    tm.update(0.5)  # no more A
    assert order == ["A"]


# ------------------------------------------------------------------
# Handle API
# ------------------------------------------------------------------


def test_then_returns_chainable_handle(tm: TimerManager) -> None:
    """.then() returns the same handle for fluent chaining."""
    h1 = tm.after(1.0, lambda: None)
    h2 = h1.then(lambda: None, 0.5)

    assert h2 is h1
    assert isinstance(h2, TimerHandle)
