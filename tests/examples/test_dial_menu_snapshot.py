"""Snapshot regression test for the dial_menu example.

Uses iter-25's ``assert_snapshot`` fixture (see ``conftest.py``).
If any framework change accidentally restructures this scene, the
stored snapshot's unified diff flags it — either fix the code or
delete ``snapshots/dial_menu.json`` / rerun with
``SAGA2D_UPDATE_SNAPSHOTS=1`` to accept.
"""

from __future__ import annotations

import pytest

from examples.dial_menu.dial_menu import DialMenuScene, build_theme
from saga2d import Game


@pytest.fixture
def game():
    g = Game(
        "dial-menu-snapshot-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
    )
    yield g
    g._teardown()


def test_dial_menu_scene_structure_stable(game: Game, assert_snapshot) -> None:
    scene = DialMenuScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    assert_snapshot(scene, "dial_menu")
