"""Save/load round-trip for the tic-tac-toe example — iter-31 parity."""

from __future__ import annotations

from pathlib import Path

import pytest

from examples.tictactoe.tictactoe import TicTacToeScene, build_theme
from saga2d import Game, InputEvent, Label


def _make_game(save_dir: Path) -> Game:
    return Game(
        "tictactoe-save-test",
        resolution=(600, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
        save_dir=save_dir,
    )


def _press(key: str | None = None, action: str | None = None) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action)


def test_save_load_round_trip_mid_match(tmp_path: Path) -> None:
    """An in-progress match round-trips: board positions, cursor, whose
    turn, and the absence of a winner."""
    game = _make_game(tmp_path)
    scene = TicTacToeScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)

    # Two plays: X at centre, O at top-left.
    scene._dispatch_key_bindings(_press(action="confirm"))  # X → 4
    for _ in range(2):
        scene._dispatch_key_bindings(_press(key="up"))       # 4 → 1 → (clamped)
    for _ in range(2):
        scene._dispatch_key_bindings(_press(key="left"))     # slide left
    scene._dispatch_key_bindings(_press(action="confirm"))  # O → 0

    saved = {
        "board": list(scene.board),
        "cursor": scene.cursor,
        "turn": scene.turn,
    }

    game.save(slot=1)
    game._teardown()

    game = _make_game(tmp_path)
    restored = TicTacToeScene()
    game._scene_stack.push(restored)
    game.tick(dt=1 / 60)
    game.load(slot=1)

    assert list(restored.board) == saved["board"]
    assert restored.cursor == saved["cursor"]
    assert restored.turn == saved["turn"]
    assert restored.winner is None
    assert restored.winning_line is None
    game._teardown()


def test_save_load_after_winning_move_preserves_winner(
    tmp_path: Path,
) -> None:
    """A finished game round-trips with winner + winning_line intact."""
    game = _make_game(tmp_path)
    scene = TicTacToeScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)

    # Force a position where X wins the top row on the next move.
    scene.board = ["X", "X", "", "O", "O", "", "", "", ""]
    scene.turn = "X"
    scene.cursor = 2
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.winner == "X"
    assert scene.winning_line == (0, 1, 2)

    game.save(slot=2)
    game._teardown()

    game = _make_game(tmp_path)
    restored = TicTacToeScene()
    game._scene_stack.push(restored)
    game.tick(dt=1 / 60)
    game.load(slot=2)

    assert restored.winner == "X"
    assert restored.winning_line == (0, 1, 2)
    assert restored.board[0] == "X"
    game._teardown()


def test_reactive_status_label_refreshes_after_load(tmp_path: Path) -> None:
    """The turn/winner status label (reactive, bound to self._status_text)
    shows the loaded state on the next tick — no manual wiring."""
    game = _make_game(tmp_path)
    scene = TicTacToeScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene._dispatch_key_bindings(_press(action="confirm"))  # X plays
    assert scene.turn == "O"
    game.save(slot=3)
    game._teardown()

    game = _make_game(tmp_path)
    restored = TicTacToeScene()
    game._scene_stack.push(restored)
    game.tick(dt=1 / 60)
    game.load(slot=3)
    game.tick(dt=1 / 60)

    # Status label now says it's O's turn.
    status_label = restored.ui.find(
        lambda c: isinstance(c, Label) and "O's turn" == c.text
    )
    assert status_label is not None
    game._teardown()
