"""TimerManager — delayed and repeating callbacks.

Internal class. Users interact via :meth:`Game.after`, :meth:`Game.every`,
and :meth:`Game.cancel`. Not re-exported from easygame.

Timer IDs are monotonic ints. Safe iteration: snapshot copy, cancelled flag
checked before firing, no catch-up on large dt for repeating timers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class _Timer:
    """Internal timer state."""

    callback: Callable[[], Any]
    remaining: float  # seconds until next fire
    interval: float | None  # None for one-shot, >0 for repeating
    cancelled: bool = False


class TimerManager:
    """Manages delayed and repeating callbacks.

    Timer IDs are opaque monotonic ints. Callbacks run during update(dt).
    """

    def __init__(self) -> None:
        self._timers: dict[int, _Timer] = {}
        self._next_id: int = 0

    def after(self, delay: float, callback: Callable[[], Any]) -> int:
        """Schedule a one-shot callback after *delay* seconds.

        Returns a timer ID for cancellation.
        """
        timer_id = self._next_id
        self._next_id += 1
        self._timers[timer_id] = _Timer(
            callback=callback,
            remaining=delay,
            interval=None,
        )
        return timer_id

    def every(self, interval: float, callback: Callable[[], Any]) -> int:
        """Schedule a repeating callback every *interval* seconds.

        Returns a timer ID for cancellation. No catch-up on large dt —
        fires at most once per update.
        """
        timer_id = self._next_id
        self._next_id += 1
        self._timers[timer_id] = _Timer(
            callback=callback,
            remaining=interval,
            interval=interval,
        )
        return timer_id

    def cancel(self, timer_id: int) -> None:
        """Cancel a timer. Safe to call during a callback."""
        if timer_id in self._timers:
            self._timers[timer_id].cancelled = True
            del self._timers[timer_id]

    def cancel_all(self) -> None:
        """Cancel all active timers."""
        self._timers.clear()

    def update(self, dt: float) -> None:
        """Advance all timers by *dt* seconds. Fire due callbacks.

        Iterates a snapshot copy. Cancelled timers (e.g. via callback) are
        skipped. Repeating timers fire at most once per update (no catch-up).
        """
        to_remove: list[int] = []
        for timer_id, timer in list(self._timers.items()):
            if timer.cancelled:
                continue
            timer.remaining -= dt
            if timer.remaining <= 0:
                timer.callback()
                if timer.interval is None:
                    to_remove.append(timer_id)
                else:
                    # Repeating: reset, no catch-up
                    timer.remaining = timer.interval
        for timer_id in to_remove:
            if timer_id in self._timers:
                del self._timers[timer_id]
