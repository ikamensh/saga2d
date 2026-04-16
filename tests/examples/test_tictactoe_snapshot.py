"""Snapshot regression test for the tic-tac-toe example.

Completes the regression coverage for all three saga2d examples
(dial_menu, ring_of_pain, tictactoe). Any framework change that
restructures tic-tac-toe's grid-based UI or rebinds a control
produces a readable diff.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from examples.tictactoe.tictactoe import TicTacToeScene, build_theme
from saga2d import Game
from saga2d.testing import assert_scene_matches_snapshot


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


@pytest.fixture
def game():
    g = Game(
        "tictactoe-snapshot-test",
        resolution=(600, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
    )
    yield g
    g._teardown()


def test_tictactoe_scene_structure_stable(game: Game) -> None:
    """Tic-tac-toe's declared structure is frozen in
    ``snapshots/tictactoe.json``. Covers the third example shape
    (grid, non-radial) under the same regression guard as the
    dial-menu and Ring of Pain snapshots."""
    scene = TicTacToeScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    assert_scene_matches_snapshot(scene, "tictactoe", SNAPSHOT_DIR)
