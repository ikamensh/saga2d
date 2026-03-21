"""Lifecycle Tester — verifies Scene lifecycle hooks and SceneStack operations.

Covers:
  US4  — Push/pop/replace scenes with proper lifecycle hooks firing
  US10 — Scene lifecycle: on_enter, on_exit, on_reveal fire in correct order
  US11 — Deferred scene ops: push/pop/replace during update flushes after tick
  US12 — clear_and_push clears stack before pushing new scene
  US13 — replace() calls on_exit on replaced scene, on_enter on new scene

Run: python -m tests.harness.lifecycle_tester [-v]
"""

from __future__ import annotations

import sys
from typing import Any

import saga2d
from saga2d import Game, Scene


# ── Instrumented Scene ──────────────────────────────────────────────────


class TrackedScene(Scene):
    """Scene subclass that records every lifecycle hook call in order."""

    def __init__(self, name: str) -> None:
        super().__init__()
        self.name = name
        self.log: list[str] = []
        # Optional callback to run inside update (for US11 deferred ops)
        self._update_action: Any = None

    def on_enter(self) -> None:
        self.log.append("on_enter")

    def on_exit(self) -> None:
        self.log.append("on_exit")

    def on_reveal(self) -> None:
        self.log.append("on_reveal")

    def update(self, dt: float) -> None:
        self.log.append("update")
        if self._update_action is not None:
            self._update_action()
            self._update_action = None  # fire once

    def __repr__(self) -> str:
        return f"TrackedScene({self.name!r})"


# ── Shared log for cross-scene ordering ──────────────────────────────


_global_log: list[str] = []


class GlobalTrackedScene(TrackedScene):
    """TrackedScene that also writes to a shared global log for ordering."""

    def on_enter(self) -> None:
        super().on_enter()
        _global_log.append(f"{self.name}.on_enter")

    def on_exit(self) -> None:
        super().on_exit()
        _global_log.append(f"{self.name}.on_exit")

    def on_reveal(self) -> None:
        super().on_reveal()
        _global_log.append(f"{self.name}.on_reveal")


# ── Helpers ──────────────────────────────────────────────────────────


def _make_game() -> Game:
    return Game("LifecycleTester", resolution=(800, 600), backend="mock")


def _check(
    label: str,
    condition: bool,
    verbose: bool,
    detail: str = "",
) -> bool:
    if condition:
        if verbose:
            print(f"  {label}: OK{f' — {detail}' if detail else ''}")
        return True
    else:
        if verbose:
            print(f"  {label}: FAIL{f' — {detail}' if detail else ''}")
        return False


# ── US4: push/pop/replace with lifecycle hooks ───────────────────────


def test_us4(verbose: bool) -> bool:
    """Push/pop/replace scenes and verify lifecycle hooks fire correctly."""
    game = _make_game()
    ok = True
    try:
        a = TrackedScene("A")
        b = TrackedScene("B")

        # Push A → on_enter fires
        game.push(a)
        ok &= _check(
            "US4-a",
            a.log == ["on_enter"],
            verbose,
            f"push(A): expected ['on_enter'], got {a.log}",
        )

        # Push B → A gets on_exit, B gets on_enter
        game.push(b)
        ok &= _check(
            "US4-b",
            a.log == ["on_enter", "on_exit"],
            verbose,
            f"push(B): A expected [..., 'on_exit'], got {a.log}",
        )
        ok &= _check(
            "US4-c",
            b.log == ["on_enter"],
            verbose,
            f"push(B): B expected ['on_enter'], got {b.log}",
        )

        # Pop B → B gets on_exit, A gets on_reveal
        game.pop()
        ok &= _check(
            "US4-d",
            b.log == ["on_enter", "on_exit"],
            verbose,
            f"pop(B): B expected [..., 'on_exit'], got {b.log}",
        )
        ok &= _check(
            "US4-e",
            a.log == ["on_enter", "on_exit", "on_reveal"],
            verbose,
            f"pop(B): A expected [..., 'on_reveal'], got {a.log}",
        )

        # Replace A with C → A gets on_exit, C gets on_enter, NO on_reveal
        c = TrackedScene("C")
        game.replace(c)
        ok &= _check(
            "US4-f",
            "on_exit" in a.log and a.log.count("on_exit") == 2,
            verbose,
            f"replace(C): A expected 2nd on_exit, got {a.log}",
        )
        ok &= _check(
            "US4-g",
            c.log == ["on_enter"],
            verbose,
            f"replace(C): C expected ['on_enter'], got {c.log}",
        )

        # Verify stack has only C
        top = game._scene_stack.top()
        ok &= _check("US4-h", top is c, verbose, f"stack top: expected C, got {top}")
        ok &= _check(
            "US4-i",
            len(game._scene_stack._stack) == 1,
            verbose,
            f"stack size: expected 1, got {len(game._scene_stack._stack)}",
        )
    finally:
        game._teardown()

    if verbose:
        print(f"  US4 {'PASS' if ok else 'FAIL'}")
    return ok


# ── US10: on_enter / on_exit / on_reveal fire in correct order ───────


def test_us10(verbose: bool) -> bool:
    """Verify cross-scene hook ordering using a global log."""
    global _global_log
    _global_log = []
    game = _make_game()
    ok = True
    try:
        a = GlobalTrackedScene("A")
        b = GlobalTrackedScene("B")

        game.push(a)  # A.on_enter
        game.push(b)  # A.on_exit, B.on_enter
        game.pop()  # B.on_exit, A.on_reveal

        expected = [
            "A.on_enter",
            "A.on_exit",
            "B.on_enter",
            "B.on_exit",
            "A.on_reveal",
        ]
        ok &= _check(
            "US10",
            _global_log == expected,
            verbose,
            f"expected {expected}, got {_global_log}",
        )
    finally:
        game._teardown()

    if verbose:
        print(f"  US10 {'PASS' if ok else 'FAIL'}")
    return ok


# ── US11: deferred ops during update() flush after tick ──────────────


def test_us11(verbose: bool) -> bool:
    """Push/pop during update() are deferred until after the tick."""
    game = _make_game()
    ok = True
    try:
        a = TrackedScene("A")
        b = TrackedScene("B")
        game.push(a)

        # Schedule: during A's update, push B
        deferred_push_fired = [False]

        def deferred_push():
            deferred_push_fired[0] = True
            game.push(b)

        a._update_action = deferred_push

        # Tick — A.update runs (pushes B deferred), then flush applies push(B)
        game.tick(0.016)

        ok &= _check(
            "US11-a",
            deferred_push_fired[0],
            verbose,
            "deferred push callback should have fired",
        )
        # After tick, B should be on top (deferred push was flushed)
        top = game._scene_stack.top()
        ok &= _check(
            "US11-b",
            top is b,
            verbose,
            f"after tick with deferred push(B): top expected B, got {top}",
        )
        ok &= _check(
            "US11-c",
            "on_enter" in b.log,
            verbose,
            f"B should have on_enter after flush, got {b.log}",
        )

        # Now test deferred pop: schedule pop from B's update
        b._update_action = lambda: game.pop()
        game.tick(0.016)

        top = game._scene_stack.top()
        ok &= _check(
            "US11-d",
            top is a,
            verbose,
            f"after tick with deferred pop: top expected A, got {top}",
        )
        ok &= _check(
            "US11-e",
            "on_reveal" in a.log,
            verbose,
            f"A should have on_reveal after deferred pop, got {a.log}",
        )

        # Test deferred replace: schedule replace from A's update
        c = TrackedScene("C")
        a._update_action = lambda: game.replace(c)
        game.tick(0.016)

        top = game._scene_stack.top()
        ok &= _check(
            "US11-f",
            top is c,
            verbose,
            f"after tick with deferred replace(C): top expected C, got {top}",
        )
        ok &= _check(
            "US11-g",
            "on_enter" in c.log,
            verbose,
            f"C should have on_enter after deferred replace, got {c.log}",
        )
    finally:
        game._teardown()

    if verbose:
        print(f"  US11 {'PASS' if ok else 'FAIL'}")
    return ok


# ── US12: clear_and_push resets stack ────────────────────────────────


def test_us12(verbose: bool) -> bool:
    """clear_and_push clears all scenes (each gets on_exit), then pushes new."""
    game = _make_game()
    ok = True
    try:
        a = TrackedScene("A")
        b = TrackedScene("B")
        c = TrackedScene("C")

        game.push(a)
        game.push(b)

        # Stack is [A, B]. clear_and_push(C) should:
        #   - on_exit B, on_exit A (reverse order)
        #   - clear stack
        #   - push C, on_enter C
        a.log.clear()
        b.log.clear()
        game.clear_and_push(c)

        ok &= _check(
            "US12-a", "on_exit" in b.log, verbose, f"B should have on_exit, got {b.log}"
        )
        ok &= _check(
            "US12-b", "on_exit" in a.log, verbose, f"A should have on_exit, got {a.log}"
        )
        ok &= _check(
            "US12-c",
            c.log == ["on_enter"],
            verbose,
            f"C expected ['on_enter'], got {c.log}",
        )

        # Stack should have only C
        ok &= _check(
            "US12-d",
            len(game._scene_stack._stack) == 1,
            verbose,
            f"stack size expected 1, got {len(game._scene_stack._stack)}",
        )
        ok &= _check(
            "US12-e",
            game._scene_stack.top() is c,
            verbose,
            f"top expected C, got {game._scene_stack.top()}",
        )

        # Verify deferred clear_and_push works too
        d = TrackedScene("D")
        c._update_action = lambda: game.clear_and_push(d)
        game.tick(0.016)

        ok &= _check(
            "US12-f",
            game._scene_stack.top() is d,
            verbose,
            f"deferred clear_and_push: top expected D, got {game._scene_stack.top()}",
        )
        ok &= _check(
            "US12-g",
            len(game._scene_stack._stack) == 1,
            verbose,
            f"deferred clear_and_push: stack size expected 1, got {len(game._scene_stack._stack)}",
        )
    finally:
        game._teardown()

    if verbose:
        print(f"  US12 {'PASS' if ok else 'FAIL'}")
    return ok


# ── US13: replace() hooks ────────────────────────────────────────────


def test_us13(verbose: bool) -> bool:
    """replace() calls on_exit on old scene, on_enter on new; no on_reveal."""
    global _global_log
    _global_log = []
    game = _make_game()
    ok = True
    try:
        a = GlobalTrackedScene("A")
        b = GlobalTrackedScene("B")

        game.push(a)
        _global_log.clear()  # reset to only see replace effects

        game.replace(b)

        expected = ["A.on_exit", "B.on_enter"]
        ok &= _check(
            "US13-a",
            _global_log == expected,
            verbose,
            f"replace(B): expected {expected}, got {_global_log}",
        )

        # A should NOT have on_reveal — replace removes A before pushing B
        ok &= _check(
            "US13-b",
            "on_reveal" not in a.log,
            verbose,
            f"A should NOT have on_reveal, got {a.log}",
        )

        # Verify stack: only B
        ok &= _check(
            "US13-c",
            game._scene_stack.top() is b,
            verbose,
            f"top expected B, got {game._scene_stack.top()}",
        )
        ok &= _check(
            "US13-d",
            len(game._scene_stack._stack) == 1,
            verbose,
            f"stack size expected 1, got {len(game._scene_stack._stack)}",
        )

        # Replace B with C while B has scenes below it
        # First push D on top of B, then replace D with E
        c = GlobalTrackedScene("C")
        d = GlobalTrackedScene("D")
        game.push(c)
        game.push(d)
        _global_log.clear()

        e = GlobalTrackedScene("E")
        game.replace(e)

        expected_deep = ["D.on_exit", "E.on_enter"]
        ok &= _check(
            "US13-e",
            _global_log == expected_deep,
            verbose,
            f"replace(E) from [B,C,D]: expected {expected_deep}, got {_global_log}",
        )

        # Stack should be [B, C, E]
        ok &= _check(
            "US13-f",
            len(game._scene_stack._stack) == 3,
            verbose,
            f"stack size expected 3, got {len(game._scene_stack._stack)}",
        )
        ok &= _check(
            "US13-g",
            game._scene_stack.top() is e,
            verbose,
            f"top expected E, got {game._scene_stack.top()}",
        )
    finally:
        game._teardown()

    if verbose:
        print(f"  US13 {'PASS' if ok else 'FAIL'}")
    return ok


# ── Main ─────────────────────────────────────────────────────────────


TESTS = [
    ("US4", test_us4),
    ("US10", test_us10),
    ("US11", test_us11),
    ("US12", test_us12),
    ("US13", test_us13),
]


def run_harness(verbose: bool = False) -> dict[str, bool]:
    """Run all lifecycle tests. Returns {story_id: passed}."""
    results: dict[str, bool] = {}
    for story_id, test_fn in TESTS:
        try:
            results[story_id] = test_fn(verbose)
        except Exception as e:
            results[story_id] = False
            if verbose:
                print(f"  {story_id}: EXCEPTION — {e}")
    return results


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    results = run_harness(verbose=verbose)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    print(f"\nLifecycle tester: {passed}/{total} stories passed")
    for story_id, ok in results.items():
        print(f"  {story_id}: {'PASS' if ok else 'FAIL'}")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
