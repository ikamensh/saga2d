"""Snapshot regression test for the Ring of Pain example.

Keeps the largest declarative scene in the examples under iter-23's
structured-regression coverage. If a framework change restructures
the ring scene's UI tree or rebinds a control, this fails with a
structured diff.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from examples.ring_of_pain.ring_of_pain import RingOfPainScene, build_theme
from saga2d import Game
from saga2d.testing import assert_scene_matches_snapshot


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


@pytest.fixture
def game():
    g = Game(
        "ring-of-pain-snapshot-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
    )
    yield g
    g._teardown()


def test_ring_of_pain_scene_structure_stable(game: Game) -> None:
    """Ring of Pain's declared structure is frozen in
    ``snapshots/ring_of_pain.json``. A framework change that shifts
    the scene's HUD or controls flags here — diff shows exactly what
    moved."""
    # Fixed seed so the node roll is deterministic across runs.
    scene = RingOfPainScene(ring_size=8, seed=7)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    assert_scene_matches_snapshot(
        scene, "ring_of_pain", SNAPSHOT_DIR,
    )
