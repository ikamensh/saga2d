"""Snapshot regression test for the Ring of Pain example.

Largest declarative scene in the examples — frozen via iter-25's
``assert_snapshot`` fixture.
"""

from __future__ import annotations

import pytest

from examples.ring_of_pain.ring_of_pain import RingOfPainScene, build_theme
from saga2d import Game


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


def test_ring_of_pain_scene_structure_stable(game: Game, assert_snapshot) -> None:
    scene = RingOfPainScene(ring_size=8, seed=7)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    assert_snapshot(scene, "ring_of_pain")
