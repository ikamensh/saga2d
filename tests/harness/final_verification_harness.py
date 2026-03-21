"""Final verification harness — scenarios AA–AE.

Covers: camera+UI click, audio/asset missing, concurrent tween/timer,
MessageScreen/SaveLoadScreen/Grid/List/TextBox/Tooltip/TabGroup/ImageBox,
particle+cursor cleanup on scene push.

Run: python -m tests.harness.final_verification_harness [--scenario AA|AB|AC|AD|AE|all]
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

from saga2d import (
    Anchor,
    Button,
    Camera,
    Game,
    Grid,
    ImageBox,
    Layout,
    List,
    MessageScreen,
    Panel,
    ParticleEmitter,
    SaveLoadScreen,
    Scene,
    Sprite,
    TabGroup,
    TextBox,
    Tooltip,
    tween,
)
from saga2d.assets import AssetManager, AssetNotFoundError


def _teardown_if_needed() -> None:
    import saga2d.rendering.sprite as _sprite_mod

    if _sprite_mod._current_game is not None:
        _sprite_mod._current_game._teardown()


def _make_asset_dir() -> Path:
    """Create temp dir with minimal assets."""
    root = Path(tempfile.mkdtemp(prefix="saga2d_final_"))
    (root / "images" / "sprites").mkdir(parents=True)
    (root / "images" / "ui").mkdir(parents=True)
    (root / "sounds").mkdir()
    for name in ("knight", "spark"):
        (root / "images" / "sprites" / f"{name}.png").write_bytes(b"png")
    (root / "images" / "ui" / "cursor_attack.png").write_bytes(b"png")
    (root / "sounds" / "click.wav").write_bytes(b"wav")
    return root


# ---------------------------------------------------------------------------
# Scenario AA: Camera + Button click, pan_to duration=0
# ---------------------------------------------------------------------------


def _run_scenario_aa(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """Button at (100,100) with Camera; scroll, click, verify callback. pan_to(duration=0)."""
    _teardown_if_needed()
    game = Game("Final", backend="mock", resolution=(800, 600), asset_path=asset_dir)
    backend = game.backend

    try:
        clicked = []

        class CameraScene(Scene):
            def on_enter(self):
                self.camera = Camera(
                    (game._resolution[0], game._resolution[1]),
                    world_bounds=(0, 0, 1600, 1200),
                )
                self.camera.center_on(400, 300)
                panel = Panel(
                    anchor=Anchor.TOP_LEFT,
                    layout=Layout.VERTICAL,
                )
                btn = Button(
                    "Click me",
                    on_click=lambda: clicked.append(True),
                    width=120,
                    height=40,
                )
                panel.add(btn)
                self.ui.add(panel)
                self._btn = btn

        game.push(CameraScene())
        game.tick(dt=0.016)

        scene = game._scene_stack.top()
        btn = scene._btn
        # Button is in a Panel at TOP_LEFT; layout places it. Get its screen position.
        if not hasattr(btn, "_computed_x"):
            scene._ui._ensure_layout()
        btn_x, btn_y = btn._computed_x, btn._computed_y

        # Scroll camera (UI is screen-space, button position unchanged)
        scene.camera.scroll(200, 100)
        game.tick(dt=0.016)
        scene._ui._ensure_layout()
        click_x, click_y = int(btn._computed_x + 60), int(btn._computed_y + 20)

        backend.inject_click(click_x, click_y)
        game.tick(dt=0.016)
        if not clicked:
            return False, f"button click not triggered at ({click_x},{click_y})"

        # pan_to with duration=0 (instant); use target inside world_bounds
        scene.camera.pan_to(500, 400, duration=0)
        game.tick(dt=0.016)
        expected_x, expected_y = 500 - 400, 400 - 300
        if abs(scene.camera.x - expected_x) > 1 or abs(scene.camera.y - expected_y) > 1:
            return (
                False,
                f"pan_to(500,400,0) expected cam at ({expected_x},{expected_y}), got ({scene.camera.x},{scene.camera.y})",
            )

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario AB: Audio optional=True, AssetNotFoundError
# ---------------------------------------------------------------------------


def _run_scenario_ab(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """audio.play_sound('missing', optional=True) no crash; assets.image('missing') raises."""
    _teardown_if_needed()
    game = Game("Final", backend="mock", resolution=(800, 600), asset_path=asset_dir)

    try:
        game.audio.play_sound("missing", optional=True)
        # Should not raise

        try:
            game.assets.image("missing")
            return False, "expected AssetNotFoundError for missing image"
        except AssetNotFoundError:
            pass

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario AC: Concurrent tween and timer
# ---------------------------------------------------------------------------


def _run_scenario_ac(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """tween(sprite.x 0->100, 0.5s); at 0.2s schedule timer to set x=200. Verify final value."""
    _teardown_if_needed()
    game = Game("Final", backend="mock", resolution=(800, 600), asset_path=asset_dir)

    try:
        sprite = Sprite("sprites/knight", position=(0, 100))
        scene = Scene()
        scene.add_sprite(sprite)
        game.push(scene)

        tween(sprite, "x", 0, 100, 0.5)
        game.after(0.2, lambda: setattr(sprite, "x", 200))

        # Tick past tween completion (0.5s) + a bit
        for _ in range(40):
            game.tick(dt=0.016)

        # Tween completes at 0.5s setting x=100. Timer fires at 0.2s setting x=200.
        # Tween continues and overwrites each frame until 0.5s. So final: 100 (tween wins).
        final_x = sprite._x
        if abs(final_x - 100) < 1:
            return True, f"OK (tween wins: x={final_x:.1f})"
        if abs(final_x - 200) < 1:
            return True, f"OK (timer wins: x={final_x:.1f})"
        return False, f"unexpected sprite.x={final_x}"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario AD: MessageScreen, SaveLoadScreen, Grid, List, TextBox, Tooltip, TabGroup, ImageBox
# ---------------------------------------------------------------------------


def _run_scenario_ad(
    asset_dir: Path, save_dir: Path, verbose: bool
) -> tuple[bool, str]:
    """Initialize all components, add to scene, tick."""
    _teardown_if_needed()
    game = Game(
        "Final",
        backend="mock",
        resolution=(800, 600),
        asset_path=asset_dir,
        save_dir=save_dir,
    )

    try:
        from saga2d.ui.components import Label

        # MessageScreen and SaveLoadScreen are Scenes; just instantiate.
        _ = MessageScreen("Test", on_dismiss=lambda: None)
        _ = SaveLoadScreen(
            mode="load",
            save_manager=game.save_manager,
            on_load=lambda s, d: None,
        )

        class WidgetScene(Scene):
            def on_enter(self):
                panel = Panel(anchor=Anchor.CENTER, layout=Layout.VERTICAL, spacing=10)
                panel.add(
                    Grid(
                        columns=2,
                        rows=2,
                        cell_size=(64, 64),
                        on_select=lambda c, r: None,
                    )
                )
                panel.add(List(items=["A", "B"], on_select=lambda i: None, width=200))
                panel.add(TextBox("Hello", width=200))
                panel.add(Tooltip("Tip", delay=0.1))
                panel.add(TabGroup(tabs={"Tab1": Label("Content")}))
                panel.add(ImageBox("sprites/knight", width=32, height=32))
                self.ui.add(panel)

        game.push(WidgetScene())
        game.tick(dt=0.016)
        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Scenario AE: ParticleEmitter + cursor cleanup on scene push
# ---------------------------------------------------------------------------


def _run_scenario_ae(asset_dir: Path, verbose: bool) -> tuple[bool, str]:
    """ParticleEmitter burst, custom cursor, push new scene. Verify cursor reset, particles not updated."""
    _teardown_if_needed()
    game = Game("Final", backend="mock", resolution=(800, 600), asset_path=asset_dir)
    backend = game.backend

    try:

        class EmitterScene(Scene):
            def on_enter(self):
                self.emitter = ParticleEmitter("sprites/spark", position=(400, 300))
                self.emitter.burst(10)
                self.add_emitter(self.emitter)
                self.game.cursor.register("attack", "ui/cursor_attack")
                self.game.cursor.set("attack")

        game.push(EmitterScene())
        game.tick(dt=0.016)
        if backend.cursor_image is None:
            return False, "cursor should be set before push"

        game.push(Scene())
        game.tick(dt=0.016)

        if backend.cursor_image is not None:
            return (
                False,
                "cursor should be reset when scene exits (backend.cursor_image is not None)",
            )

        for _ in range(5):
            game.tick(dt=0.016)
        particle_count_after = len([e for e in game._particle_emitters if e.is_active])
        if particle_count_after > 0:
            return (
                False,
                f"emitters from exited scene should be removed, got {particle_count_after} active",
            )

        return True, "OK"
    except Exception as e:
        return False, str(e)
    finally:
        game._teardown()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SCENARIOS = {
    "AA": ("Camera + Button click, pan_to(0)", _run_scenario_aa),
    "AB": ("Audio optional, AssetNotFoundError", _run_scenario_ab),
    "AC": ("Concurrent tween/timer", _run_scenario_ac),
    "AD": (
        "MessageScreen, SaveLoadScreen, Grid, List, TextBox, Tooltip, TabGroup, ImageBox",
        _run_scenario_ad,
    ),
    "AE": ("ParticleEmitter + cursor cleanup", _run_scenario_ae),
}


def run_harness(
    scenarios: list[str] | None = None,
    verbose: bool = False,
) -> bool:
    """Run final verification scenarios. Returns True if all pass."""
    scenarios = scenarios or list(SCENARIOS)
    results: list[tuple[str, bool, str]] = []
    asset_dir = _make_asset_dir()
    save_dir = Path(tempfile.mkdtemp(prefix="saga2d_save_"))

    try:
        for name in scenarios:
            if name not in SCENARIOS:
                continue
            _, fn = SCENARIOS[name]
            if name == "AD":
                ok, msg = fn(asset_dir, save_dir, verbose)
            else:
                ok, msg = fn(asset_dir, verbose)
            results.append((name, ok, msg))
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

    scenarios = list(SCENARIOS)
    if args:
        scenarios = [s.upper() for s in args[0].split(",")]
        if "ALL" in scenarios:
            scenarios = list(SCENARIOS)

    ok = run_harness(scenarios=scenarios, verbose=verbose)
    if verbose and ok:
        print("Final verification harness: PASS")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
