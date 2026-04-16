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


# -- SAGA2D_UPDATE_SNAPSHOTS env-var mode ---------------------------------


def test_update_env_var_overwrites_stored_snapshot(
    tmp_path: Path, game: Game, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """With the env-var set, a mismatch that would normally raise
    instead overwrites the file with the new value and passes."""
    scene = _small_scene(game)
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)

    # Corrupt the stored snapshot.
    path = tmp_path / "my_scene.json"
    path.write_text('{"scene": "Deliberately Wrong"}\n')

    # Without env-var → raises.
    monkeypatch.delenv("SAGA2D_UPDATE_SNAPSHOTS", raising=False)
    with pytest.raises(AssertionError):
        assert_scene_matches_snapshot(scene, "my_scene", tmp_path)

    # With env-var → passes + overwrites.
    monkeypatch.setenv("SAGA2D_UPDATE_SNAPSHOTS", "1")
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    data = json.loads(path.read_text())
    assert data["scene"] == "S"  # overwritten with current value


def test_update_env_var_accepts_truthy_values(
    tmp_path: Path, game: Game, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Developer-friendly truthy values should all work — 1 / true /
    yes / on (case-insensitive)."""
    scene = _small_scene(game)
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    path = tmp_path / "my_scene.json"

    for truthy in ("1", "true", "True", "yes", "YES", "on", "ON"):
        path.write_text('{"scene": "Wrong"}\n')
        monkeypatch.setenv("SAGA2D_UPDATE_SNAPSHOTS", truthy)
        assert_scene_matches_snapshot(scene, "my_scene", tmp_path)  # no raise


def test_update_env_var_rejects_falsy_values(
    tmp_path: Path, game: Game, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """0, empty string, or unset = no overwrite; a mismatch still raises."""
    scene = _small_scene(game)
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    path = tmp_path / "my_scene.json"

    for falsy in ("0", "", "no", "off", "false"):
        path.write_text('{"scene": "Wrong"}\n')
        monkeypatch.setenv("SAGA2D_UPDATE_SNAPSHOTS", falsy)
        with pytest.raises(AssertionError):
            assert_scene_matches_snapshot(scene, "my_scene", tmp_path)


def test_mismatch_message_mentions_env_var(
    tmp_path: Path, game: Game, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The error message should tell the user about the bulk-update
    escape hatch — discoverability matters."""
    scene = _small_scene(game)
    assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    path = tmp_path / "my_scene.json"
    path.write_text('{"scene": "Wrong"}\n')
    monkeypatch.delenv("SAGA2D_UPDATE_SNAPSHOTS", raising=False)
    with pytest.raises(AssertionError) as exc:
        assert_scene_matches_snapshot(scene, "my_scene", tmp_path)
    assert "SAGA2D_UPDATE_SNAPSHOTS" in str(exc.value)
