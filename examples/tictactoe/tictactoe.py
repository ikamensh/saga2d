"""Tic-Tac-Toe — third saga2d example.

Deliberately a *non-radial* shape so the iter-2..14 API stack gets
stressed outside rings. Uses :func:`saga2d.grid_positions` for the
3x3 board, :class:`Scene.controls` for arrow-key navigation and
space/R, reactive :class:`Label` for turn/winner text, and the
``Game(theme=…)`` / ``Anchor.TOP_CENTER`` additions from earlier
rounds.

Under 140 lines including win detection, reset, and a status bar.
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from saga2d import (  # noqa: E402
    Anchor,
    Game,
    InputEvent,
    Label,
    Scene,
    TextStyle,
    Theme,
    grid_positions,
)

BG = (18, 20, 30, 255)
LINE = (80, 90, 120, 255)
CURSOR = (255, 215, 100, 255)      # gold
X_COLOR = (120, 190, 230, 255)     # light blue
O_COLOR = (240, 120, 140, 255)     # pink
WIN_COLOR = (120, 220, 140, 255)   # green

WIN_LINES: list[tuple[int, int, int]] = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # cols
    (0, 4, 8), (2, 4, 6),               # diagonals
]


class TicTacToeScene(Scene):
    background_color = BG
    controls = {
        ("left", "a"):       "cursor_left",
        ("right", "d"):      "cursor_right",
        ("up", "w"):         "cursor_up",
        ("down", "s"):       "cursor_down",
        ("confirm", "space"): "play",
        "r":                 "reset",
    }

    def __init__(self) -> None:
        super().__init__()
        self.board: list[str] = [""] * 9
        self.cursor: int = 4  # start at centre
        self.turn: str = "X"
        self.winner: str | None = None
        self.winning_line: tuple[int, int, int] | None = None

    # -- input ---------------------------------------------------------------

    def cursor_left(self) -> None:
        if self.cursor % 3 > 0:
            self.cursor -= 1

    def cursor_right(self) -> None:
        if self.cursor % 3 < 2:
            self.cursor += 1

    def cursor_up(self) -> None:
        if self.cursor // 3 > 0:
            self.cursor -= 3

    def cursor_down(self) -> None:
        if self.cursor // 3 < 2:
            self.cursor += 3

    def play(self) -> None:
        if self.winner or self.board[self.cursor]:
            return
        self.board[self.cursor] = self.turn
        self._check_winner()
        if not self.winner and "" not in self.board:
            self.winner = "draw"
        if not self.winner:
            self.turn = "O" if self.turn == "X" else "X"

    def reset(self, event: InputEvent | None = None) -> None:
        """Reset the board. Shift+R opens with X in the centre — a
        common "let me test a losing position" shortcut. Plain R is
        a full reset. Demonstrates iter-17's event-aware modifier
        plumbing: the handler takes the event iff it signals one arg."""
        self.board = [""] * 9
        self.cursor = 4
        self.turn = "X"
        self.winner = None
        self.winning_line = None
        if event is not None and event.shift:
            self.board[4] = "X"
            self.turn = "O"

    def _check_winner(self) -> None:
        for a, b, c in WIN_LINES:
            if self.board[a] and self.board[a] == self.board[b] == self.board[c]:
                self.winner = self.board[a]
                self.winning_line = (a, b, c)
                return

    # -- status / UI ---------------------------------------------------------

    def _status_text(self) -> str:
        if self.winner == "draw":
            return "Draw!   (R to reset)"
        if self.winner:
            return f"{self.winner} wins!   (R to reset)"
        return f"{self.turn}'s turn"

    def on_enter(self) -> None:
        self.ui.add(Label(
            "Tic-Tac-Toe", text_style="title",
            anchor=Anchor.TOP_CENTER, margin=16,
        ))
        self.ui.add(Label(
            self._status_text, text_style="heading",
            anchor=Anchor.BOTTOM_CENTER, margin=24,
        ))
        self.ui.add(Label(
            "← ↑ → ↓ move   space place   R reset   Shift+R open-centre",
            text_style="caption",
            anchor=Anchor.BOTTOM_LEFT, margin=16,
        ))

    # -- drawing -------------------------------------------------------------

    def draw(self) -> None:
        w, h = self.game.resolution
        cell = min(w - 80, h - 160) // 3   # leave room for title + status
        origin_x = (w - cell * 3) // 2 + cell // 2
        origin_y = (h - cell * 3) // 2 + cell // 2 + 10
        positions = grid_positions(
            9, columns=3, cell=(cell, cell),
            origin=(origin_x, origin_y),
        )

        for i, (cx, cy) in enumerate(positions):
            cx, cy = int(cx), int(cy)
            # Cell frame: one call, not two, thanks to iter-16 border kwargs.
            self.draw_rect(
                cx - cell // 2 + 2, cy - cell // 2 + 2,
                cell - 4, cell - 4,
                BG, border_color=LINE, border_width=2,
            )
            # Winning line highlight
            if self.winning_line and i in self.winning_line:
                self.draw_rect(
                    cx - cell // 2 + 4, cy - cell // 2 + 4,
                    cell - 8, cell - 8, (*WIN_COLOR[:3], 60),
                )
            # Cursor highlight (only if no winner)
            if i == self.cursor and not self.winner:
                self.draw_rect(
                    cx - cell // 2 + 4, cy - cell // 2 + 4,
                    cell - 8, cell - 8, (*CURSOR[:3], 60),
                )
            # Piece
            glyph = self.board[i]
            if glyph:
                color = X_COLOR if glyph == "X" else O_COLOR
                self.draw_text(
                    glyph, cx, cy,
                    font_size=int(cell * 0.55),
                    color=color,
                    anchor_x="center", anchor_y="center",
                )


def build_theme() -> Theme:
    return Theme(
        font="Cinzel",  # iter-26 bundled OFL font — see assets/fonts/
        text_styles={
            "title":   TextStyle(font_size=30, color=(245, 245, 255, 255)),
            "heading": TextStyle(font_size=22, color=(245, 245, 255, 255)),
            "caption": TextStyle(font_size=13, color=(150, 155, 175, 255)),
        },
    )


def main() -> None:
    game = Game(
        "Tic-Tac-Toe Example",
        resolution=(600, 600),
        fullscreen=False,
        backend="pyglet",
        theme=build_theme(),
    )
    game.run(TicTacToeScene())


if __name__ == "__main__":
    main()
