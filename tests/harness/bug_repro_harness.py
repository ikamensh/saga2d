"""Bug reproduction and final verification harness.

Scenarios R–Y exercise edge cases: Parallel hangs, NaN propagation,
scene stack edges, timer cleanup, input state, utils, window events, Do action.

Run: python -m tests.harness.bug_repro_harness [--scenario R|S|T|U|V|W|X|Y|all]
"""

from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

from saga2d import (
    Delay,
    Do,
    Game,
    MoveTo,
    Parallel,
    Scene,
    Sprite,
    compute_anchor_position,
)
from saga2d.backends.base import WindowEvent
from saga2d.ui import Anchor
from saga2d.util.tween import Ease


def _make_asset_dir() -> Path:
    """Create temp dir with minimal assets for sprite tests."""
    root = Path(tempfile.mkdtemp(prefix="saga2d_bugrepro_"))
    (root / "images" / "sprites").mkdir(parents=True)
    (root / "images" / "sprites" / "knight.png").write_bytes(b"png")
    return root


def _teardown_if_needed() -> None:
    import saga2d.rendering.sprite as _sprite_mod

    if _sprite_mod._current_game is not None:
        _sprite_mod._current_game._teardown()


# ---------------------------------------------------------------------------
# Scenario R: Parallel — finish one early, verify completion
# ---------------------------------------------------------------------------


def _run_scenario_r(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """Parallel with two sub-actions; one finishes early."""
    _teardown_if_needed()
    game = Game("BugRepro", backend="mock", resolution=(800, 600), asset_path=asset_dir)

    try:

        class ActionScene(Scene):
            def on_enter(self):
                self.sprite = self.add_sprite(
                    Sprite("sprites/knight", position=(100, 100))
                )
                # Short Delay (0.05s) + long MoveTo (~2s at 100px/s for 200px)
                self.sprite.do(
                    Parallel(
                        Delay(0.05),
                        MoveTo((300, 100), speed=100),
                    )
                )

        game.push(ActionScene())
        # Tick until Parallel completes (both finite actions done)
        for _ in range(150):
            game.tick(dt=0.016)
            if game._scene_stack.top() is None:
                break
        # Should complete; sprite near (300, 100)
        scene = game._scene_stack._stack[0] if game._scene_stack._stack else None
        if scene is None:
            return False, "scene stack empty unexpectedly"
        sprite = scene.sprite
        if abs(sprite._x - 300) > 5 or abs(sprite._y - 100) > 5:
            return (
                False,
                f"sprite expected near (300,100), got ({sprite._x:.1f},{sprite._y:.1f})",
            )
        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario S: NaN propagation — MoveTo with NaN fails early
# ---------------------------------------------------------------------------


def _run_scenario_s(verbose: bool) -> tuple[bool, str]:
    """MoveTo with NaN coordinates fails at construction or doesn't corrupt sprite."""
    _teardown_if_needed()

    try:
        # MoveTo.__init__ raises ValueError for NaN
        MoveTo((float("nan"), 100), speed=50)
        return False, "expected ValueError for NaN position"
    except ValueError:
        pass  # expected

    # Also verify a valid MoveTo doesn't corrupt sprite
    asset_dir = _make_asset_dir()
    try:
        game = Game(
            "BugRepro", backend="mock", resolution=(800, 600), asset_path=asset_dir
        )
        sprite = Sprite("sprites/knight", position=(100, 100))
        scene = Scene()
        scene.add_sprite(sprite)
        game.push(scene)
        sprite.do(MoveTo((200, 200), speed=100))
        for _ in range(60):
            game.tick(dt=0.016)
        if not math.isfinite(sprite._x) or not math.isfinite(sprite._y):
            return (
                False,
                f"sprite position corrupted to NaN: ({sprite._x}, {sprite._y})",
            )
        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()
        import shutil

        shutil.rmtree(asset_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Scenario T: Scene stack edges — push same twice, pop while pushing
# ---------------------------------------------------------------------------


def _run_scenario_t(verbose: bool) -> tuple[bool, str]:
    """Push same scene twice, pop while pushing; no crash."""
    _teardown_if_needed()
    game = Game("BugRepro", backend="mock", resolution=(800, 600))

    try:
        scene = Scene()

        # Push same scene twice (allowed; stack has two instances)
        game.push(scene)
        game.push(scene)
        if len(game._scene_stack._stack) != 2:
            return (
                False,
                f"expected 2 scenes after double push, got {len(game._scene_stack._stack)}",
            )

        # Pop both
        game.pop()
        game.pop()
        if game._scene_stack._stack:
            return False, f"stack should be empty, got {len(game._scene_stack._stack)}"

        # Pop while pushing: scene that pushes on_enter, then we pop
        class PushOnEnter(Scene):
            def on_enter(self):
                self.game.push(Scene())  # deferred

        game.push(PushOnEnter())
        game.tick(dt=0.016)  # flush deferred push
        game.pop()  # pop the inner scene
        game.pop()  # pop PushOnEnter
        if game._scene_stack._stack:
            return (
                False,
                f"stack should be empty after pop-while-push, got {len(game._scene_stack._stack)}",
            )

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario U: Timer cleanup — timer.after then push scene
# ---------------------------------------------------------------------------


def _run_scenario_u(verbose: bool) -> tuple[bool, str]:
    """Start scene.after, push new scene; verify timer is cleaned up (scene-bound)."""
    _teardown_if_needed()
    game = Game("BugRepro", backend="mock", resolution=(800, 600))

    try:
        fired = []

        class TimerScene(Scene):
            def on_enter(self):
                self.after(0.05, lambda: fired.append(True))

        game.push(TimerScene())
        game.tick(dt=0.016)

        # Push new scene — TimerScene gets on_exit + _cleanup_owned_timers, so
        # scene-bound timer is cancelled. It should NOT fire.
        game.push(Scene())
        for _ in range(10):
            game.tick(dt=0.016)

        if fired:
            return False, "scene-bound timer should be cancelled on push, but fired"

        # Also verify game.after (non-scene-bound) still fires after push
        game_fired = []
        game.after(0.05, lambda: game_fired.append(True))
        for _ in range(10):
            game.tick(dt=0.016)
            if game_fired:
                break
        if not game_fired:
            return False, "game.after timer did not fire after push"

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario V: Input state — verify injection updates mouse/key state
# ---------------------------------------------------------------------------


def _run_scenario_v(verbose: bool) -> tuple[bool, str]:
    """Verify input injection: key reaches handle_input, mouse pos updates."""
    _teardown_if_needed()
    game = Game("BugRepro", backend="mock", resolution=(800, 600))
    backend = game.backend

    try:
        received = []

        class InputScene(Scene):
            def handle_input(self, event) -> bool:
                received.append(
                    (
                        event.type,
                        getattr(event, "key", None),
                        getattr(event, "x", 0),
                        getattr(event, "y", 0),
                    )
                )
                return True

        game.push(InputScene())
        game.tick(dt=0.016)

        backend.inject_key("space")
        game.tick(dt=0.016)
        if not any(r[0] == "key_press" and r[1] == "space" for r in received):
            return False, f"key_press space not received: {received}"

        backend.inject_mouse_move(320, 240)
        game.tick(dt=0.016)
        if game._mouse_x != 320 or game._mouse_y != 240:
            return (
                False,
                f"mouse pos expected (320,240), got ({game._mouse_x},{game._mouse_y})",
            )

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario W: Utils — Ease.quad_in_out and compute_anchor_position
# ---------------------------------------------------------------------------


def _run_scenario_w(verbose: bool) -> tuple[bool, str]:
    """Test Ease.EASE_IN_OUT(0.5) and compute_anchor_position."""
    from saga2d.util.tween import _EASE_FNS

    # Ease.EASE_IN_OUT is quadratic ease-in-out; at t=0.5 expect ~0.5 (symmetric)
    eased = _EASE_FNS[Ease.EASE_IN_OUT](0.5)
    if not 0.4 <= eased <= 0.6:
        return False, f"EASE_IN_OUT(0.5) expected ~0.5, got {eased}"

    # compute_anchor_position: CENTER in 100x100 parent, 20x20 child
    x, y = compute_anchor_position(Anchor.CENTER, 0, 0, 100, 100, 20, 20, margin=0)
    if x != 40 or y != 40:
        return False, f"compute_anchor_position CENTER expected (40,40), got ({x},{y})"

    return True, "OK"


# ---------------------------------------------------------------------------
# Scenario X: Window events — inject RESIZE, verify no crash
# ---------------------------------------------------------------------------


def _run_scenario_x(verbose: bool) -> tuple[bool, str]:
    """Inject WindowEvent(resize), verify no crash; resolution unchanged (mock)."""
    _teardown_if_needed()
    game = Game("BugRepro", backend="mock", resolution=(800, 600))
    backend = game.backend

    try:
        backend.inject_event(WindowEvent(type="resize"))
        game.tick(dt=0.016)
        # Mock backend doesn't update game._resolution on resize; just verify no crash
        if game._resolution != (800, 600):
            return False, f"resolution changed unexpectedly: {game._resolution}"
        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario Y: Do action — callback is called
# ---------------------------------------------------------------------------


def _run_scenario_y(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """Do(lambda: ...) action; verify callback runs."""
    _teardown_if_needed()
    game = Game("BugRepro", backend="mock", resolution=(800, 600), asset_path=asset_dir)

    try:
        called = []

        class DoScene(Scene):
            def on_enter(self):
                sprite = self.add_sprite(Sprite("sprites/knight", position=(100, 100)))
                sprite.do(Do(lambda: called.append(True)))

        game.push(DoScene())
        game.tick(dt=0.016)

        if not called:
            return False, "Do callback was not called"
        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SCENARIOS = {
    "R": ("Parallel hangs", _run_scenario_r),
    "S": ("NaN propagation", _run_scenario_s),
    "T": ("Scene stack edges", _run_scenario_t),
    "U": ("Timer cleanup", _run_scenario_u),
    "V": ("Input state", _run_scenario_v),
    "W": ("Utils", _run_scenario_w),
    "X": ("Window events", _run_scenario_x),
    "Y": ("Do action", _run_scenario_y),
}


def run_harness(
    scenarios: list[str] | None = None,
    verbose: bool = False,
) -> bool:
    """Run bug repro scenarios. Returns True if all pass."""
    scenarios = scenarios or list(SCENARIOS)
    results: list[tuple[str, bool, str]] = []
    asset_dir = _make_asset_dir()

    try:
        for name in scenarios:
            if name not in SCENARIOS:
                continue
            _, fn = SCENARIOS[name]
            if name in ("R", "Y"):
                ok, msg = fn(asset_dir, verbose)
            elif name == "S":
                ok, msg = fn(verbose)  # S creates its own asset_dir for second part
            else:
                ok, msg = fn(verbose)
            results.append((name, ok, msg))
    finally:
        import shutil

        shutil.rmtree(asset_dir, ignore_errors=True)

    if verbose:
        for name, ok, msg in results:
            status = "PASS" if ok else "FAIL"
            print(f"  Scenario {name}: {status} — {msg}")

    return all(r[1] for r in results)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    scenarios = list(SCENARIOS)
    if args:
        scenarios = [s.upper() for s in args[0].split(",")]
        if "ALL" in scenarios:
            scenarios = list(SCENARIOS)

    ok = run_harness(scenarios=scenarios, verbose=verbose)
    if verbose and ok:
        print("Bug repro harness: PASS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
