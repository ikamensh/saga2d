"""Visual regression snapshots for every runnable saga2d example.

Captures the iter-38 mock-to-PIL render of each example at a fixed
resolution and compares against a stored PNG on disk. The first run
writes the baseline; subsequent runs fail if the pixels shift.

This is the iter-41 follow-up to iter-15's :func:`assert_scene_matches_snapshot`
(which protects *structural* drift) and iter-38's mock-to-PIL renderer
(which lets us see anything at all). Together they form the
"would a game developer ship this?" regression net: anything that
changes what a player sees on screen must pass through these tests
with an intentional snapshot update.

Any of these failing means *something about the rendered output
changed* — either a layout bug, a theme drift, or an intentional
improvement. For intentional changes, run
``SAGA2D_UPDATE_PNG_SNAPSHOTS=1 pytest tests/examples/test_example_png_snapshots.py``
and commit the regenerated PNGs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from saga2d import Game
from saga2d.testing import assert_scene_matches_png_snapshot


SNAPSHOT_DIR = Path(__file__).parent / "png_snapshots"


def test_dial_menu_visual_snapshot() -> None:
    from examples.dial_menu.dial_menu import DialMenuScene, build_theme

    def setup(game: Game) -> None:
        game._scene_stack.push(DialMenuScene())

    assert_scene_matches_png_snapshot(
        setup, "dial_menu",
        snapshot_dir=SNAPSHOT_DIR,
        resolution=(800, 600),
        theme=build_theme(),
    )


def test_guess_the_number_visual_snapshot() -> None:
    from examples.guess_the_number.guess_the_number import (
        GuessScene,
        build_theme,
    )

    def setup(game: Game) -> None:
        scene = GuessScene()
        # Pin the randomised target so the snapshot is deterministic.
        scene.target = 50
        game._scene_stack.push(scene)

    assert_scene_matches_png_snapshot(
        setup, "guess_the_number",
        snapshot_dir=SNAPSHOT_DIR,
        resolution=(800, 600),
        theme=build_theme(),
    )


def test_ring_of_pain_visual_snapshot() -> None:
    from examples.ring_of_pain.ring_of_pain import (
        RingOfPainScene,
        build_theme,
    )

    def setup(game: Game) -> None:
        # Fixed seed = deterministic node layout.
        game._scene_stack.push(RingOfPainScene(ring_size=8, seed=7))

    assert_scene_matches_png_snapshot(
        setup, "ring_of_pain",
        snapshot_dir=SNAPSHOT_DIR,
        resolution=(800, 600),
        theme=build_theme(),
    )


def test_tictactoe_visual_snapshot() -> None:
    from examples.tictactoe.tictactoe import TicTacToeScene, build_theme

    def setup(game: Game) -> None:
        game._scene_stack.push(TicTacToeScene())

    assert_scene_matches_png_snapshot(
        setup, "tictactoe",
        snapshot_dir=SNAPSHOT_DIR,
        resolution=(600, 600),
        theme=build_theme(),
    )


def test_reaction_test_visual_snapshot() -> None:
    from examples.reaction_test.reaction_test import (
        ReactionTestScene,
        build_theme,
    )

    def setup(game: Game) -> None:
        game._scene_stack.push(ReactionTestScene())

    assert_scene_matches_png_snapshot(
        setup, "reaction_test",
        snapshot_dir=SNAPSHOT_DIR,
        resolution=(800, 600),
        theme=build_theme(),
    )


# ---------------------------------------------------------------------------
# Framework properties of the helper itself.
# ---------------------------------------------------------------------------


def test_png_snapshot_first_run_writes_snapshot(tmp_path: Path) -> None:
    """First-run contract: no snapshot file → write it and pass."""
    from saga2d import Scene

    def setup(game: Game) -> None:
        class S(Scene):
            background_color = (10, 20, 30, 255)
        game._scene_stack.push(S())

    snap_file = tmp_path / "first_run.png"
    assert not snap_file.exists()
    assert_scene_matches_png_snapshot(
        setup, "first_run", snapshot_dir=tmp_path, resolution=(100, 100),
    )
    assert snap_file.exists()


def test_png_snapshot_mismatch_writes_actual_png(tmp_path: Path) -> None:
    """On mismatch, an ``{name}.actual.png`` is written next to the
    snapshot so the diff is visually inspectable. Without this, a
    headless CI failure gives no signal about *how* the render
    drifted — only that it did."""
    from saga2d import Scene

    def setup_a(game: Game) -> None:
        class S(Scene):
            background_color = (10, 20, 30, 255)
        game._scene_stack.push(S())

    def setup_b(game: Game) -> None:
        class S(Scene):
            background_color = (200, 50, 60, 255)  # different!
        game._scene_stack.push(S())

    # Seed the snapshot with setup A.
    assert_scene_matches_png_snapshot(
        setup_a, "diff_test", snapshot_dir=tmp_path, resolution=(50, 50),
    )
    # Re-run with setup B — should fail and drop an .actual.png
    # alongside the baseline.
    with pytest.raises(AssertionError):
        assert_scene_matches_png_snapshot(
            setup_b, "diff_test", snapshot_dir=tmp_path, resolution=(50, 50),
        )
    assert (tmp_path / "diff_test.actual.png").exists()
    assert (tmp_path / "diff_test.png").exists()


def test_png_snapshot_update_env_var_rewrites(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``SAGA2D_UPDATE_PNG_SNAPSHOTS=1`` bulk-accepts changes."""
    from saga2d import Scene

    def setup_a(game: Game) -> None:
        class S(Scene):
            background_color = (10, 20, 30, 255)
        game._scene_stack.push(S())

    def setup_b(game: Game) -> None:
        class S(Scene):
            background_color = (200, 50, 60, 255)
        game._scene_stack.push(S())

    assert_scene_matches_png_snapshot(
        setup_a, "env_test", snapshot_dir=tmp_path, resolution=(50, 50),
    )
    # Without the env var, the mismatched setup raises.
    with pytest.raises(AssertionError):
        assert_scene_matches_png_snapshot(
            setup_b, "env_test", snapshot_dir=tmp_path, resolution=(50, 50),
        )

    # With the env var, same call writes the new snapshot and passes.
    monkeypatch.setenv("SAGA2D_UPDATE_PNG_SNAPSHOTS", "1")
    assert_scene_matches_png_snapshot(
        setup_b, "env_test", snapshot_dir=tmp_path, resolution=(50, 50),
    )
    # Subsequent call without the env var should now pass (setup_b
    # is the new baseline).
    monkeypatch.delenv("SAGA2D_UPDATE_PNG_SNAPSHOTS")
    assert_scene_matches_png_snapshot(
        setup_b, "env_test", snapshot_dir=tmp_path, resolution=(50, 50),
    )
