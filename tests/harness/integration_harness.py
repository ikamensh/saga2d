"""Integration harness — verifies Game + Scene + UI + Sprite + Action + Audio + Camera.

Run: python -m tests.harness.integration_harness [--scenario A|B|C|all]
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from saga2d import (
    Anchor,
    Button,
    Camera,
    Delay,
    FadeIn,
    Game,
    Layout,
    MoveTo,
    Panel,
    Parallel,
    Remove,
    Scene,
    Sequence,
    Sprite,
)
from saga2d.assets import AssetManager


def _make_asset_dir() -> Path:
    """Create temp dir with minimal assets for integration tests."""
    root = Path(tempfile.mkdtemp(prefix="saga2d_integration_"))
    (root / "images" / "sprites").mkdir(parents=True)
    (root / "images" / "sprites" / "knight.png").write_bytes(b"png")
    (root / "music").mkdir()
    (root / "music" / "theme_a.ogg").write_bytes(b"ogg")
    (root / "music" / "theme_b.ogg").write_bytes(b"ogg")
    return root


def _teardown_if_needed() -> None:
    import saga2d.rendering.sprite as _sprite_mod

    if _sprite_mod._current_game is not None:
        _sprite_mod._current_game._teardown()


# ---------------------------------------------------------------------------
# Scenes
# ---------------------------------------------------------------------------


class SceneB(Scene):
    """Second scene — plays different music."""

    def on_enter(self) -> None:
        self.game.audio.play_music("theme_b")


class SceneA(Scene):
    """Main scene: music, Button, Sprite with nested action."""

    def on_enter(self) -> None:
        self.game.audio.play_music("theme_a")
        self.camera = Camera(
            (self.game._resolution[0], self.game._resolution[1]),
            world_bounds=(0, 0, 2000, 2000),
        )
        self.camera.center_on(400, 300)

        # Button that pushes Scene B
        panel = Panel(
            anchor=Anchor.TOP_LEFT,
            layout=Layout.VERTICAL,
            spacing=10,
        )
        self._btn = Button(
            "Go to B",
            on_click=lambda: self.game.push(SceneB()),
            width=150,
            height=40,
        )
        panel.add(self._btn)
        self.ui.add(panel)

        # Sprite with Sequence(Parallel(MoveTo, FadeIn), Delay, Remove)
        self._sprite = Sprite(
            "sprites/knight",
            position=(200, 300),
            opacity=0,
        )
        self.add_sprite(self._sprite)
        self._sprite.do(
            Sequence(
                Parallel(
                    MoveTo((400, 300), speed=200),
                    FadeIn(0.3),
                ),
                Delay(0.2),
                Remove(),
            )
        )


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def _run_scenario_a(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """Scenario A: Button click pushes Scene B, verify music state."""
    _teardown_if_needed()
    game = Game("Integration", backend="mock", resolution=(800, 600))
    game.assets = AssetManager(game.backend, base_path=asset_dir)
    backend = game.backend

    try:
        game.push(SceneA())
        game.tick(dt=0.016)

        # Music should be theme_a (backend stores handle; audio tracks name)
        if game.audio._current_music_name != "theme_a":
            return (
                False,
                f"expected music theme_a, got {game.audio._current_music_name}",
            )

        # Find button center and click
        scene_a = game._scene_stack._stack[0]
        btn = scene_a._btn
        cx = btn._computed_x + btn._computed_w // 2
        cy = btn._computed_y + btn._computed_h // 2
        backend.inject_click(int(cx), int(cy))
        game.tick(dt=0.016)

        # Scene B should be on top, music should be theme_b
        stack = game._scene_stack._stack
        if len(stack) != 2:
            return False, f"expected 2 scenes, got {len(stack)}"
        if stack[-1].__class__.__name__ != "SceneB":
            return (
                False,
                f"top scene should be SceneB, got {stack[-1].__class__.__name__}",
            )
        if game.audio._current_music_name != "theme_b":
            return (
                False,
                f"expected music theme_b after push, got {game.audio._current_music_name}",
            )

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


def _run_scenario_b(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """Scenario B: Nested action completes, sprite is removed."""
    _teardown_if_needed()
    game = Game("Integration", backend="mock", resolution=(800, 600))
    game.assets = AssetManager(game.backend, base_path=asset_dir)
    backend = game.backend

    try:
        game.push(SceneA())
        scene_a = game._scene_stack._stack[0]
        sprite = scene_a._sprite
        sprite_id = sprite.sprite_id

        # Parallel(MoveTo ~1s, FadeIn 0.3s) + Delay 0.2 + Remove
        # Parallel finishes at max(1, 0.3) = 1s, then Delay 0.2, then Remove
        # Total ~1.2s
        for _ in range(100):
            game.tick(dt=0.016)
            if sprite.is_removed:
                break

        if not sprite.is_removed:
            return False, "sprite not removed after action"
        if sprite_id in backend.sprites:
            return False, "sprite still in backend.sprites after Remove"

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


def _run_scenario_c(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """Scenario C: Camera movement; UI Button position remains fixed in screen space."""
    _teardown_if_needed()
    game = Game("Integration", backend="mock", resolution=(800, 600))
    game.assets = AssetManager(game.backend, base_path=asset_dir)
    backend = game.backend

    try:
        game.push(SceneA())
        game.tick(dt=0.016)

        scene_a = game._scene_stack._stack[0]
        btn = scene_a._btn
        cam = scene_a.camera

        # Record button screen position before camera scroll
        x_before = btn._computed_x
        y_before = btn._computed_y

        # Scroll camera
        cam.scroll(100, 50)
        game.tick(dt=0.016)

        # Button should still be at same screen coordinates (UI is screen-space)
        x_after = btn._computed_x
        y_after = btn._computed_y
        if x_before != x_after or y_before != y_after:
            return False, (
                f"button moved: ({x_before}, {y_before}) -> ({x_after}, {y_after})"
            )

        # Camera offset should have changed
        if cam.x == 0 and cam.y == 0:
            return False, "camera did not scroll"

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
    """Run integration scenarios. Returns True if all pass."""
    scenarios = scenarios or ["A", "B", "C"]
    asset_dir = _make_asset_dir()
    results: list[tuple[str, bool, str]] = []

    try:
        if "A" in scenarios:
            ok, msg = _run_scenario_a(asset_dir, verbose)
            results.append(("A", ok, msg))
        if "B" in scenarios:
            ok, msg = _run_scenario_b(asset_dir, verbose)
            results.append(("B", ok, msg))
        if "C" in scenarios:
            ok, msg = _run_scenario_c(asset_dir, verbose)
            results.append(("C", ok, msg))
    finally:
        import shutil

        shutil.rmtree(asset_dir, ignore_errors=True)
        _teardown_if_needed()

    if verbose:
        for name, ok, msg in results:
            status = "PASS" if ok else "FAIL"
            print(f"  Scenario {name}: {status} — {msg}")

    return all(r[1] for r in results)


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    scenarios = ["A", "B", "C"]
    if args:
        scenarios = [s.upper() for s in args[0].split(",")]
        if "ALL" in scenarios:
            scenarios = ["A", "B", "C"]

    ok = run_harness(scenarios=scenarios, verbose=verbose)
    if verbose and ok:
        print("Integration harness: PASS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
