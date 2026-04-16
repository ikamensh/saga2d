"""Properties of the tic-tac-toe example.

The third saga2d example — deliberately a non-radial shape
(grid_positions, not ring_positions). These tests cover the game's
rules and the Scene.controls wiring end-to-end through the mock
backend. Combined with the dial-menu + Ring-of-Pain tests, this
makes three structurally different games whose gameplay logic is
exercised through saga2d primitives.
"""

from __future__ import annotations

import pytest

from examples.tictactoe.tictactoe import TicTacToeScene, build_theme
from saga2d import Game, InputEvent


@pytest.fixture
def game():
    g = Game(
        "ttt-test",
        resolution=(600, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
    )
    yield g
    g._teardown()


def _push(game: Game) -> TicTacToeScene:
    scene = TicTacToeScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    return scene


def _press(key: str | None = None, action: str | None = None) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action)


# -- cursor navigation -----------------------------------------------------


def test_initial_cursor_centre(game: Game) -> None:
    scene = _push(game)
    assert scene.cursor == 4  # centre of 3x3


def test_cursor_moves_within_bounds(game: Game) -> None:
    scene = _push(game)
    # start at 4 (centre), move left, right, up, down.
    scene._dispatch_key_bindings(_press(key="left"))
    assert scene.cursor == 3
    scene._dispatch_key_bindings(_press(key="up"))
    assert scene.cursor == 0
    scene._dispatch_key_bindings(_press(key="down"))
    scene._dispatch_key_bindings(_press(key="right"))
    assert scene.cursor == 4


def test_cursor_clamped_at_edges(game: Game) -> None:
    """Tic-tac-toe deliberately clamps (doesn't wrap) so a held key
    stops at an edge — that's the behaviour a player expects."""
    scene = _push(game)
    scene._dispatch_key_bindings(_press(key="up"))   # 4 → 1
    scene._dispatch_key_bindings(_press(key="up"))   # 1 → 0 (top-left)
    scene._dispatch_key_bindings(_press(key="up"))   # still 0
    scene._dispatch_key_bindings(_press(key="left"))  # still 0
    assert scene.cursor == 0


# -- play rules ------------------------------------------------------------


def test_play_places_current_turn(game: Game) -> None:
    scene = _push(game)
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.board[4] == "X"
    assert scene.turn == "O"


def test_play_ignores_occupied_cell(game: Game) -> None:
    scene = _push(game)
    scene._dispatch_key_bindings(_press(action="confirm"))  # X at 4
    first_turn = scene.turn
    # Play same cell again — no change.
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.board[4] == "X"
    assert scene.turn == first_turn


def test_play_detects_row_winner(game: Game) -> None:
    scene = _push(game)
    scene.board = ["X", "X", "", "", "O", "O", "", "", ""]
    scene.turn = "X"
    scene.cursor = 2  # complete top row
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.winner == "X"
    assert scene.winning_line == (0, 1, 2)


def test_play_detects_diagonal_winner(game: Game) -> None:
    scene = _push(game)
    scene.board = ["X", "O", "", "O", "X", "", "", "", ""]
    scene.turn = "X"
    scene.cursor = 8  # complete main diagonal
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.winner == "X"


def test_play_detects_draw(game: Game) -> None:
    scene = _push(game)
    # Board with one cell left that doesn't complete any line.
    scene.board = [
        "X", "O", "X",
        "X", "O", "O",
        "O", "X", "",
    ]
    scene.turn = "X"
    scene.cursor = 8
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.winner == "draw"


def test_play_locked_after_winner(game: Game) -> None:
    scene = _push(game)
    scene.board = ["X", "X", "X", "", "", "", "", "", ""]
    scene.winner = "X"
    scene.cursor = 4
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.board[4] == ""  # still empty


# -- reset -----------------------------------------------------------------


def test_reset_restores_initial_state(game: Game) -> None:
    scene = _push(game)
    scene._dispatch_key_bindings(_press(action="confirm"))
    scene._dispatch_key_bindings(_press(key="right"))
    scene._dispatch_key_bindings(_press(action="confirm"))
    scene._dispatch_key_bindings(_press(key="r"))
    assert scene.board == [""] * 9
    assert scene.cursor == 4
    assert scene.turn == "X"
    assert scene.winner is None


# -- status text -----------------------------------------------------------


def test_status_text_shows_current_turn(game: Game) -> None:
    scene = _push(game)
    assert "X" in scene._status_text()


def test_status_text_shows_winner(game: Game) -> None:
    scene = _push(game)
    scene.winner = "O"
    assert "O" in scene._status_text()
    assert "wins" in scene._status_text()
