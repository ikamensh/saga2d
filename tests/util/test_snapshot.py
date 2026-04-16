"""Properties of :func:`saga2d.testing.assert_scene_matches_snapshot`."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from saga2d import Anchor, Game, Label, Scene
from saga2d.testing import assert_scene_matches_snapshot


@pytest.fixture
def game():
    g = Game(
        "snapshot-test",
        resolution=(100, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _small_scene(game: Game) -> Scene:
    class S(Scene):
        background_color = (10, 20, 30, 255)
        controls = {"a": "foo"}

        def foo(self) -> None: pass

        def on_enter(self) -> None:
            self.ui.add(Label("hi", text_style="hud",
                              anchor=Anchor.CENTER))

    scene = S()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    return scene


def test_first_run_writes_snapshot(tmp_path: Path, game: Game) -> None:
    scene = _small_scene(game)
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    assert (tmp_path / "my_scene.json").exists()


def test_first_run_passes_without_raising(tmp_path: Path, game: Game) -> None:
    scene = _small_scene(game)
    # No exception on first run — this is the bootstrap behaviour.
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)


def test_matching_snapshot_passes(tmp_path: Path, game: Game) -> None:
    scene = _small_scene(game)
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)  # creates
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)  # matches


def test_mismatching_snapshot_raises_with_diff(tmp_path: Path, game: Game) -> None:
    scene = _small_scene(game)
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)  # bootstrap

    # Mutate the snapshot file to simulate a structural change.
    path = tmp_path / "my_scene.json"
    data = json.loads(path.read_text())
    data["scene"] = "RenamedScene"
    path.write_text(json.dumps(data, indent=2) + "\n")

    with pytest.raises(AssertionError) as exc:
        assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    msg = str(exc.value)
    assert "RenamedScene" in msg          # shows the old value
    assert "S" in msg                      # shows the new value
    # Unified diff markers.
    assert "---" in msg or "+++" in msg


def test_snapshot_file_is_pretty_json(tmp_path: Path, game: Game) -> None:
    """The written file should be human-readable (indented) so that git
    diffs between snapshot revisions are useful."""
    scene = _small_scene(game)
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    text = (tmp_path / "my_scene.json").read_text()
    assert "\n" in text
    # Indented JSON — a top-level key should appear on its own line.
    assert '"scene"' in text
    # Pretty-printed means each object-key is on its own line somewhere.
    assert text.count("\n") >= 3


def test_snapshot_dir_created_if_missing(tmp_path: Path, game: Game) -> None:
    scene = _small_scene(game)
    nested = tmp_path / "a" / "b" / "c"
    assert not nested.exists()
    assert_scene_matches_snapshot(scene, "my_scene", nested)
    assert (nested / "my_scene.json").exists()


def test_identical_repeated_runs_dont_rewrite_file(
    tmp_path: Path, game: Game,
) -> None:
    """Running an unchanged snapshot twice shouldn't churn the file —
    git-blame stability matters for snapshot reviews."""
    scene = _small_scene(game)
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    path = tmp_path / "my_scene.json"
    mtime_before = path.stat().st_mtime_ns
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    assert path.stat().st_mtime_ns == mtime_before


def test_mismatch_message_points_at_snapshot_path(
    tmp_path: Path, game: Game,
) -> None:
    """The AssertionError should name the snapshot file so the developer
    knows which file to delete to accept the new baseline."""
    scene = _small_scene(game)
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)

    path = tmp_path / "my_scene.json"
    data = json.loads(path.read_text())
    data["scene"] = "Different"
    path.write_text(json.dumps(data, indent=2) + "\n")

    with pytest.raises(AssertionError) as exc:
        assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    assert str(path) in str(exc.value)
