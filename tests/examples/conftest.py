"""Shared fixtures for the example snapshot tests.

Collapses the ~15-line boilerplate each snapshot test used to carry
(imports, SNAPSHOT_DIR, directory setup) into two pytest fixtures:

* :func:`snapshot_dir` — resolves ``tests/examples/snapshots/``
  relative to each test file's location.
* :func:`assert_snapshot` — a closure that takes a scene + name and
  runs :func:`saga2d.testing.assert_scene_matches_snapshot` against
  the directory above.

After migration, a snapshot test collapses to::

    def test_my_scene_stable(game, assert_snapshot):
        scene = MyScene()
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)
        assert_snapshot(scene, "my_scene")
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from saga2d.scene import Scene
from saga2d.testing import assert_scene_matches_snapshot


@pytest.fixture
def snapshot_dir(request: pytest.FixtureRequest) -> Path:
    """Path to ``tests/examples/snapshots/`` — resolved from the
    current test file's directory."""
    return Path(request.fspath.dirname) / "snapshots"


@pytest.fixture
def assert_snapshot(snapshot_dir: Path) -> Callable[[Scene, str], None]:
    """Return a closure ``(scene, name) -> None`` that asserts the
    scene's ``summary_json()`` matches ``snapshot_dir / {name}.json``.

    The closure respects ``SAGA2D_UPDATE_SNAPSHOTS=1`` bulk-update
    mode (iter-24) and produces a unified-diff error message on
    mismatch.
    """

    def _assert(scene: Scene, name: str) -> None:
        assert_scene_matches_snapshot(scene, name, snapshot_dir)

    return _assert
