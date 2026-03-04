"""Finite state machine — pure logic, no game/backend dependency."""

from __future__ import annotations

from typing import Any, Callable


class StateMachine:
    """Simple finite state machine with enter/exit callbacks.

    Parameters:
        states:      List of valid state names (strings).
        initial:     Starting state (must be in states).
        transitions: {state: {event: next_state}} dict.
        on_enter:    {state: callable} — called when entering a state.
        on_exit:     {state: callable} — called when leaving a state.
    """

    def __init__(
        self,
        states: list[str],
        initial: str,
        transitions: dict[str, dict[str, str]] | None = None,
        on_enter: dict[str, Callable[[], Any]] | None = None,
        on_exit: dict[str, Callable[[], Any]] | None = None,
    ) -> None:
        state_set = set(states)
        if initial not in state_set:
            raise ValueError(f"Initial state '{initial}' not in states: {states}")
        if transitions:
            for src, events in transitions.items():
                if src not in state_set:
                    raise ValueError(f"Transition source '{src}' not in states")
                for event_name, target in events.items():
                    if target not in state_set:
                        raise ValueError(
                            f"Transition target '{target}' (from '{src}' on '{event_name}') "
                            f"not in states"
                        )

        self._states = list(states)
        self._transitions = transitions or {}
        self._on_enter = on_enter or {}
        self._on_exit = on_exit or {}
        self._state = initial

        if initial in self._on_enter:
            self._on_enter[initial]()

    @property
    def state(self) -> str:
        """Current state name."""
        return self._state

    def trigger(self, event: str) -> bool:
        """Fire an event. Returns True if a transition occurred.

        If the current state has a transition for this event, the FSM:
        1. Calls on_exit[old_state] (if registered).
        2. Changes state to the target.
        3. Calls on_enter[new_state] (if registered).

        If no transition is defined for this event in the current state,
        returns False (no-op, no error).
        """
        state_trans = self._transitions.get(self._state)
        if state_trans is None:
            return False
        target = state_trans.get(event)
        if target is None:
            return False

        old_state = self._state
        if old_state in self._on_exit:
            self._on_exit[old_state]()
        self._state = target
        if target in self._on_enter:
            self._on_enter[target]()
        return True

    @property
    def valid_events(self) -> list[str]:
        """Events that can trigger transitions from the current state."""
        state_trans = self._transitions.get(self._state)
        if state_trans is None:
            return []
        return list(state_trans.keys())
