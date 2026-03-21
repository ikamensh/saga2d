"""Edge-case / fuzzing harness — verifies saga2d handles invalid input gracefully.

Expects either: (a) appropriate exception raised, or (b) no crash.
Run: python -m tests.harness.fuzz_harness
"""

from __future__ import annotations

import sys
from typing import Callable

# Expected exception types when framework rejects invalid input
EXPECTED_EXCEPTIONS = (ValueError, TypeError, IndexError, RuntimeError, AttributeError)


def _teardown_if_needed() -> None:
    import saga2d.rendering.sprite as _sprite_mod

    if _sprite_mod._current_game is not None:
        _sprite_mod._current_game._teardown()


def _run(
    name: str,
    fn: Callable[[], None],
    expect_exception: bool = False,
) -> tuple[bool, str]:
    """Run a fuzz case. Returns (passed, message)."""
    _teardown_if_needed()
    try:
        fn()
        if expect_exception:
            return False, "expected exception, got none"
        return True, "OK"
    except EXPECTED_EXCEPTIONS as e:
        if expect_exception:
            return True, f"raised {type(e).__name__}"
        return False, f"unexpected {type(e).__name__}: {e}"
    except Exception as e:
        return False, f"crash: {type(e).__name__}: {e}"
    finally:
        _teardown_if_needed()


def _game_invalid_args() -> list[tuple[str, bool, str]]:
    import saga2d

    results = []

    # Non-tuple resolution
    def bad_resolution_int():
        saga2d.Game("Fuzz", resolution=800, backend="mock")  # type: ignore[arg-type]

    ok, msg = _run("Game(resolution=800)", bad_resolution_int, expect_exception=True)
    results.append(("Game(resolution=800)", ok, msg))

    # resolution="800x600" is accepted (str is subscriptable); backend gets ord chars
    def bad_resolution_str():
        game = saga2d.Game("Fuzz", resolution="800x600", backend="mock")  # type: ignore[arg-type]
        game._teardown()

    ok, msg = _run(
        "Game(resolution='800x600')", bad_resolution_str, expect_exception=False
    )
    results.append(("Game(resolution='800x600')", ok, msg))

    def bad_resolution_short_tuple():
        saga2d.Game("Fuzz", resolution=(800,), backend="mock")  # type: ignore[arg-type]

    ok, msg = _run(
        "Game(resolution=(800,))", bad_resolution_short_tuple, expect_exception=True
    )
    results.append(("Game(resolution=(800,))", ok, msg))

    # Invalid backend
    def bad_backend_str():
        saga2d.Game("Fuzz", backend="invalid", resolution=(800, 600))

    ok, msg = _run("Game(backend='invalid')", bad_backend_str, expect_exception=True)
    results.append(("Game(backend='invalid')", ok, msg))

    def bad_backend_int():
        saga2d.Game("Fuzz", backend=123, resolution=(800, 600))  # type: ignore[arg-type]

    ok, msg = _run("Game(backend=123)", bad_backend_int, expect_exception=True)
    results.append(("Game(backend=123)", ok, msg))

    return results


def _scene_invalid_ops() -> list[tuple[str, bool, str]]:
    import saga2d

    results = []

    # Pop on empty stack — should not crash
    def pop_empty():
        game = saga2d.Game("Fuzz", backend="mock", resolution=(800, 600))
        try:
            game.pop()
        finally:
            game._teardown()

    ok, msg = _run("pop() on empty stack", pop_empty, expect_exception=False)
    results.append(("pop() on empty stack", ok, msg))

    # Replace on empty stack — should work (replace treats empty as "push")
    def replace_empty():
        game = saga2d.Game("Fuzz", backend="mock", resolution=(800, 600))
        try:
            game.replace(saga2d.Scene())
            game.pop()
        finally:
            game._teardown()

    ok, msg = _run("replace() on empty stack", replace_empty, expect_exception=False)
    results.append(("replace() on empty stack", ok, msg))

    # Push non-Scene
    def push_non_scene():
        game = saga2d.Game("Fuzz", backend="mock", resolution=(800, 600))
        try:
            game.push("not a scene")  # type: ignore[arg-type]
        finally:
            game._teardown()

    ok, msg = _run("push(non-Scene)", push_non_scene, expect_exception=True)
    results.append(("push(non-Scene)", ok, msg))

    # Push None
    def push_none():
        game = saga2d.Game("Fuzz", backend="mock", resolution=(800, 600))
        try:
            game.push(None)  # type: ignore[arg-type]
        finally:
            game._teardown()

    ok, msg = _run("push(None)", push_none, expect_exception=True)
    results.append(("push(None)", ok, msg))

    return results


def _action_invalid_params() -> list[tuple[str, bool, str]]:
    import saga2d

    results = []

    # Delay(seconds < 0)
    def delay_negative():
        saga2d.Delay(-1)

    ok, msg = _run("Delay(-1)", delay_negative, expect_exception=True)
    results.append(("Delay(-1)", ok, msg))

    # Delay(NaN) — framework does not validate; no crash
    def delay_nan():
        saga2d.Delay(float("nan"))

    ok, msg = _run("Delay(float('nan'))", delay_nan, expect_exception=False)
    results.append(("Delay(float('nan'))", ok, msg))

    # Delay(Inf) — framework does not validate; no crash
    def delay_inf():
        saga2d.Delay(float("inf"))

    ok, msg = _run("Delay(float('inf'))", delay_inf, expect_exception=False)
    results.append(("Delay(float('inf'))", ok, msg))

    # MoveTo(speed=0)
    def moveto_speed_zero():
        saga2d.MoveTo((100, 100), 0)

    ok, msg = _run("MoveTo(..., speed=0)", moveto_speed_zero, expect_exception=True)
    results.append(("MoveTo(..., speed=0)", ok, msg))

    # MoveTo(NaN position)
    def moveto_nan_pos():
        saga2d.MoveTo((float("nan"), 100), 100)

    ok, msg = _run("MoveTo((nan, 100), 100)", moveto_nan_pos, expect_exception=True)
    results.append(("MoveTo((nan, 100), 100)", ok, msg))

    # MoveTo(non-numeric position)
    def moveto_str_pos():
        saga2d.MoveTo(("x", 100), 100)  # type: ignore[arg-type]

    ok, msg = _run("MoveTo(('x', 100), 100)", moveto_str_pos, expect_exception=True)
    results.append(("MoveTo(('x', 100), 100)", ok, msg))

    # Sequence with non-Action
    def sequence_non_action():
        saga2d.Sequence(1, 2, 3)  # type: ignore[arg-type]

    ok, msg = _run("Sequence(1, 2, 3)", sequence_non_action, expect_exception=True)
    results.append(("Sequence(1, 2, 3)", ok, msg))

    # Parallel with non-Action
    def parallel_non_action():
        saga2d.Parallel("x")  # type: ignore[arg-type]

    ok, msg = _run("Parallel('x')", parallel_non_action, expect_exception=True)
    results.append(("Parallel('x')", ok, msg))

    # Repeat with non-Action
    def repeat_non_action():
        saga2d.Repeat(42)  # type: ignore[arg-type]

    ok, msg = _run("Repeat(42)", repeat_non_action, expect_exception=True)
    results.append(("Repeat(42)", ok, msg))

    return results


def run_harness(verbose: bool = False) -> bool:
    """Run all fuzz cases. Returns True if all pass."""
    all_results: list[tuple[str, bool, str]] = []
    all_results.extend(_game_invalid_args())
    all_results.extend(_scene_invalid_ops())
    all_results.extend(_action_invalid_params())

    passed = sum(1 for _, ok, _ in all_results if ok)
    total = len(all_results)

    if verbose:
        for name, ok, msg in all_results:
            status = "PASS" if ok else "FAIL"
            print(f"  {status}: {name} — {msg}")

    _teardown_if_needed()
    return passed == total


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    ok = run_harness(verbose=verbose)
    if verbose and ok:
        print("Fuzz harness: PASS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
