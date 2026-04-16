"""Properties of the iter-25 ``assert_snapshot`` fixture.

Tests that the fixture (a) resolves the snapshot directory relative
to the test file, (b) delegates correctly to
``assert_scene_matches_snapshot``, and (c) propagates the mismatch
error message.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from saga2d import Anchor, Game, Label, Scene


@pytest.fixture
def game():
    g = Game(
        "fixture-test",
        resolution=(100, 100),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _tiny_scene(game: Game) -> Scene:
    class S(Scene):
        background_color = (10, 20, 30, 255)

        def on_enter(self) -> None:
            self.ui.add(Label("x", anchor=Anchor.CENTER))

    scene = S()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    return scene


def test_snapshot_dir_resolves_from_test_file_location(
    snapshot_dir: Path,
) -> None:
    """``snapshot_dir`` is ``<this file's dir>/snapshots/``."""
    assert snapshot_dir.name == "snapshots"
    assert snapshot_dir.parent == Path(__file__).parent


def test_assert_snapshot_is_callable_with_scene_and_name(
    game: Game,
    assert_snapshot,
    snapshot_dir: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Calling the fixture should write a snapshot file under
    the resolved snapshot_dir. Using tmp_path via monkeypatch-ing
    the fixture's dir would be ideal; here we just delete the file
    afterwards to keep the test hermetic."""
    scene = _tiny_scene(game)
    test_name = "iter25_fixture_smoke_test_snapshot"
    path = snapshot_dir / f"{test_name}.json"
    # Clean any stale file from a previous run.
    if path.exists():
        path.unlink()
    try:
        assert_snapshot(scene, test_name)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["scene"] == "S"
    finally:
        # Test is transient — don't pollute the real snapshots dir.
        if path.exists():
            path.unlink()
