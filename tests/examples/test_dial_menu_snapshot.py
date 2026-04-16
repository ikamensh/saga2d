"""Snapshot regression test for the dial_menu example.

Demonstrates ``saga2d.testing.assert_scene_matches_snapshot`` in a
real project context. If any future framework change accidentally
restructures this scene (e.g. renames a class, silently drops a
control binding, reorders children), the stored snapshot diff will
flag it before it ships. Fixing it is then a choice: update the
saga2d API to preserve behaviour, or delete
``snapshots/dial_menu.json`` to accept the new shape.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from examples.dial_menu.dial_menu import DialMenuScene, build_theme
from saga2d import Game
from saga2d.testing import assert_scene_matches_snapshot


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


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


def test_dial_menu_scene_structure_stable(game: Game) -> None:
    """The dial menu's declared structure is frozen in
    ``snapshots/dial_menu.json``. If this test fails after a saga2d
    change, inspect the diff — either the change is intentional
    (update the snapshot) or an accident (fix the code)."""
    scene = DialMenuScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    assert_scene_matches_snapshot(scene, "dial_menu", SNAPSHOT_DIR)
