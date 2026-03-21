"""Systems and Util harness — Save, StateMachine, Cursor, Audio, Timer, Tween, Input, Teardown, show_sequence.

Run: python -m tests.harness.systems_util_harness [--scenario J|K|L|M|N|O|P|Q|all]
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from saga2d import (
    Game,
    MessageScreen,
    Scene,
    StateMachine,
    tween,
)
from saga2d.assets import AssetManager


def _make_asset_dir() -> Path:
    """Create temp dir with minimal assets."""
    from PIL import Image

    root = Path(tempfile.mkdtemp(prefix="saga2d_systems_"))
    (root / "images" / "sprites").mkdir(parents=True)
    (root / "images" / "ui").mkdir(parents=True)
    (root / "sounds").mkdir()
    for name in ("knight", "spark"):
        img = Image.new("RGBA", (16, 16), (128, 128, 128, 255))
        img.save(root / "images" / "sprites" / f"{name}.png")
    img = Image.new("RGBA", (16, 16), (255, 0, 0, 255))
    img.save(root / "images" / "ui" / "cursor_attack.png")
    (root / "sounds" / "click.wav").write_bytes(b"wav")
    return root


def _teardown_if_needed() -> None:
    import saga2d.rendering.sprite as _sprite_mod
    from saga2d.rendering.color_swap import _clear_palettes

    _clear_palettes()
    if _sprite_mod._current_game is not None:
        _sprite_mod._current_game._teardown()


# ---------------------------------------------------------------------------
# Scenario J: SaveManager save/load
# ---------------------------------------------------------------------------


def _run_scenario_j(save_dir: Path, verbose: bool) -> tuple[bool, str]:
    """Save and load a test object."""
    _teardown_if_needed()
    game = Game("Systems", backend="mock", resolution=(800, 600), save_dir=save_dir)

    try:

        class SaveableScene(Scene):
            def get_save_state(self) -> dict:
                return {"score": 42, "level": 3}

            def load_save_state(self, state: dict) -> None:
                self._loaded = state

        scene = SaveableScene()
        game.push(scene)
        game.save(1)

        data = game.load(1)
        if data is None:
            return False, "load returned None"
        if data.get("state", {}).get("score") != 42:
            return False, f"state.score expected 42, got {data}"
        if scene._loaded.get("score") != 42:
            return False, f"load_save_state score expected 42, got {scene._loaded}"

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario K: StateMachine
# ---------------------------------------------------------------------------


def _run_scenario_k(verbose: bool) -> tuple[bool, str]:
    """StateMachine with Start, Play, End. Trigger transitions."""
    _teardown_if_needed()

    try:
        entered = []

        fsm = StateMachine(
            states=["Start", "Play", "End"],
            initial="Start",
            transitions={
                "Start": {"go": "Play"},
                "Play": {"win": "End", "lose": "Start"},
                "End": {"restart": "Start"},
            },
            on_enter={
                "Start": lambda: entered.append("Start"),
                "Play": lambda: entered.append("Play"),
                "End": lambda: entered.append("End"),
            },
        )

        if fsm.state != "Start":
            return False, f"initial state expected Start, got {fsm.state}"
        if entered != ["Start"]:
            return False, f"on_enter Start expected, got {entered}"

        if not fsm.trigger("go"):
            return False, "trigger(go) should transition"
        if fsm.state != "Play":
            return False, f"state expected Play, got {fsm.state}"
        if entered != ["Start", "Play"]:
            return False, f"on_enter Play expected, got {entered}"

        fsm.trigger("win")
        if fsm.state != "End":
            return False, f"state expected End, got {fsm.state}"

        return True, "OK"
    except Exception as e:
        return False, str(e)


# ---------------------------------------------------------------------------
# Scenario L: CursorManager
# ---------------------------------------------------------------------------


def _run_scenario_l(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """CursorManager change cursor type."""
    _teardown_if_needed()
    game = Game("Systems", backend="mock", resolution=(800, 600))
    game.assets = AssetManager(game.backend, base_path=asset_dir)
    backend = game.backend

    try:
        game.cursor.register("attack", "ui/cursor_attack", hotspot=(8, 8))
        game.cursor.set("attack")

        if backend.cursor_image is None:
            return False, "cursor_image should be set"
        if backend.cursor_hotspot != (8, 8):
            return False, f"hotspot expected (8,8), got {backend.cursor_hotspot}"
        if game.cursor.current != "attack":
            return False, f"cursor.current expected attack, got {game.cursor.current}"

        game.cursor.set("default")
        if backend.cursor_image is not None:
            return False, "cursor_image should be None after default"
        if game.cursor.current != "default":
            return False, f"cursor.current expected default, got {game.cursor.current}"

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario M: AudioManager
# ---------------------------------------------------------------------------


def _run_scenario_m(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """AudioManager play sound, set master volume."""
    _teardown_if_needed()
    game = Game("Systems", backend="mock", resolution=(800, 600))
    game.assets = AssetManager(game.backend, base_path=asset_dir)
    backend = game.backend

    try:
        game.audio.set_volume("master", 0.5)
        if game.audio.get_volume("master") != 0.5:
            return (
                False,
                f"master volume expected 0.5, got {game.audio.get_volume('master')}",
            )

        game.audio.play_sound("click")
        if len(backend.sounds_played) != 1:
            return False, f"sounds_played expected 1, got {len(backend.sounds_played)}"
        if backend.sounds_played[0]["handle"] is None:
            return False, "sound handle should be set"

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario N: TimerHandle and tween
# ---------------------------------------------------------------------------


def _run_scenario_n(verbose: bool) -> tuple[bool, str]:
    """Timer and tween callbacks triggered."""
    _teardown_if_needed()
    game = Game("Systems", backend="mock", resolution=(800, 600))

    try:
        timer_fired = []
        tween_fired = []

        game.after(0.05, lambda: timer_fired.append(True))
        obj = type("Obj", (), {"x": 0})()
        tween(obj, "x", 0, 100, 0.0, on_complete=lambda: tween_fired.append(True))

        # dt=0.0 for tween: duration 0 means it completes immediately
        game.tick(dt=0.016)
        assert len(tween_fired) == 1, f"tween on_complete expected, got {tween_fired}"

        # Timer needs a few ticks
        for _ in range(5):
            game.tick(dt=0.016)
            if timer_fired:
                break

        if not timer_fired:
            return False, "timer callback not fired"

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario O: Inject KeyEvent and MouseEvent, verify handle_input
# ---------------------------------------------------------------------------


def _run_scenario_o(verbose: bool) -> tuple[bool, str]:
    """Inject events, verify scene handle_input receives them."""
    _teardown_if_needed()
    game = Game("Systems", backend="mock", resolution=(800, 600))
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
            return False, f"key_press not received, got {received}"

        received.clear()
        backend.inject_click(100, 200)
        game.tick(dt=0.016)

        if not any(r[0] == "click" and r[2] == 100 and r[3] == 200 for r in received):
            return False, f"click not received, got {received}"

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario P: Game._teardown() cleanup
# ---------------------------------------------------------------------------


def _run_scenario_p(verbose: bool) -> tuple[bool, str]:
    """Teardown cleans up resources."""
    _teardown_if_needed()
    game = Game("Systems", backend="mock", resolution=(800, 600))

    try:
        scene = Scene()
        game.push(scene)
        game.tick(dt=0.016)

        game._teardown()

        if game._scene_stack._stack:
            return (
                False,
                f"scene stack should be empty, got {len(game._scene_stack._stack)}",
            )
        if game._audio is not None:
            return False, "audio should be None"

        import saga2d.rendering.sprite as _sprite_mod

        if _sprite_mod._current_game is not None:
            return False, "_current_game should be None"

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        _teardown_if_needed()


# ---------------------------------------------------------------------------
# Scenario Q: show_sequence
# ---------------------------------------------------------------------------


def _run_scenario_q(verbose: bool) -> tuple[bool, str]:
    """show_sequence with MessageScreens, verify order and on_complete."""
    _teardown_if_needed()
    game = Game("Systems", backend="mock", resolution=(800, 600))
    backend = game.backend

    try:
        order = []
        complete_fired = []

        screens = [
            MessageScreen("First", on_dismiss=lambda: order.append(1)),
            MessageScreen("Second", on_dismiss=lambda: order.append(2)),
            MessageScreen("Third", on_dismiss=lambda: order.append(3)),
        ]
        game.show_sequence(screens, on_complete=lambda: complete_fired.append(True))
        game.tick(dt=0.016)

        # Stack: _SequenceRunner (bottom), MessageScreen "First" (top)
        if len(game._scene_stack._stack) != 2:
            return (
                False,
                f"expected 2 scenes (runner + first), got {len(game._scene_stack._stack)}",
            )

        # Dismiss first
        backend.inject_key("space")
        game.tick(dt=0.016)
        if order != [1]:
            return False, f"after first dismiss order expected [1], got {order}"

        # Dismiss second
        backend.inject_key("space")
        game.tick(dt=0.016)
        if order != [1, 2]:
            return False, f"after second dismiss order expected [1,2], got {order}"

        # Dismiss third
        backend.inject_key("space")
        game.tick(dt=0.016)
        if order != [1, 2, 3]:
            return False, f"after third dismiss order expected [1,2,3], got {order}"
        if not complete_fired:
            return False, "on_complete not fired"
        if len(game._scene_stack._stack) != 0:
            return False, f"stack should be empty, got {len(game._scene_stack._stack)}"

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def run_harness(
    scenarios: list[str] | None = None,
    verbose: bool = False,
) -> bool:
    """Run systems/util scenarios. Returns True if all pass."""
    scenarios = scenarios or ["J", "K", "L", "M", "N", "O", "P", "Q"]
    asset_dir = _make_asset_dir()
    save_dir = Path(tempfile.mkdtemp(prefix="saga2d_save_"))
    results: list[tuple[str, bool, str]] = []

    try:
        if "J" in scenarios:
            ok, msg = _run_scenario_j(save_dir, verbose)
            results.append(("J", ok, msg))
        if "K" in scenarios:
            ok, msg = _run_scenario_k(verbose)
            results.append(("K", ok, msg))
        if "L" in scenarios:
            ok, msg = _run_scenario_l(asset_dir, verbose)
            results.append(("L", ok, msg))
        if "M" in scenarios:
            ok, msg = _run_scenario_m(asset_dir, verbose)
            results.append(("M", ok, msg))
        if "N" in scenarios:
            ok, msg = _run_scenario_n(verbose)
            results.append(("N", ok, msg))
        if "O" in scenarios:
            ok, msg = _run_scenario_o(verbose)
            results.append(("O", ok, msg))
        if "P" in scenarios:
            ok, msg = _run_scenario_p(verbose)
            results.append(("P", ok, msg))
        if "Q" in scenarios:
            ok, msg = _run_scenario_q(verbose)
            results.append(("Q", ok, msg))
    finally:
        import shutil

        shutil.rmtree(asset_dir, ignore_errors=True)
        shutil.rmtree(save_dir, ignore_errors=True)
        _teardown_if_needed()

    if verbose:
        for name, ok, msg in results:
            status = "PASS" if ok else "FAIL"
            print(f"  Scenario {name}: {status} — {msg}")

    return all(r[1] for r in results)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    scenarios = ["J", "K", "L", "M", "N", "O", "P", "Q"]
    if args:
        scenarios = [s.upper() for s in args[0].split(",")]
        if "ALL" in scenarios:
            scenarios = ["J", "K", "L", "M", "N", "O", "P", "Q"]

    ok = run_harness(scenarios=scenarios, verbose=verbose)
    if verbose and ok:
        print("Systems/Util harness: PASS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
