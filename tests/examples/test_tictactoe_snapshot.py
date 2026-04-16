"""Snapshot regression test for the tic-tac-toe example.

Non-radial grid scene — frozen via iter-25's ``assert_snapshot`` fixture.
Completes the 3/3 example-game regression coverage.
"""

from __future__ import annotations

import pytest

from examples.tictactoe.tictactoe import TicTacToeScene, build_theme
from saga2d import Game


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


def test_tictactoe_scene_structure_stable(game: Game, assert_snapshot) -> None:
    scene = TicTacToeScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    assert_snapshot(scene, "tictactoe")
