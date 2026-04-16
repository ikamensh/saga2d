"""Guess-the-number — fourth saga2d example.

The runnable version of the scene the declarative tutorial
(``tutorials/declarative/tutorial.md``) builds up in five steps.
Shipping it as a standalone example validates that the tutorial's
final form actually runs end-to-end with ``python …/guess_the_number.py``.

Mechanics:

* Target is a hidden integer in [1, 100].
* Up/W and Down/S adjust the current guess by 1.
* Shift+Up / Shift+Down jump by 10 (iter-17 modifier demonstration).
* Enter/Space locks in the guess; the status says Higher / Lower / Correct!
* R rolls a new target and resets.

Under 90 lines including save/load.
"""

from __future__ import annotations

import random
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
    Row,
    Scene,
    TextStyle,
    Theme,
)

BG = (18, 20, 30, 255)
GOLD = (255, 215, 100, 255)
WHITE = (245, 245, 250, 255)
DIM = (180, 190, 210, 255)


class GuessScene(Scene):
    background_color = BG
    controls = {
        ("up", "w"):          "bump_up",
        ("down", "s"):        "bump_down",
        ("confirm", "space"): "guess",
        "r":                  "reset",
    }

    def __init__(self) -> None:
        super().__init__()
        self.target = random.randint(1, 100)
        self.current = 50
        self.guesses = 0
        self.hint = "Guess 1–100. Shift to jump by 10."

    # -- input ---------------------------------------------------------------

    def bump_up(self, event: InputEvent | None = None) -> None:
        step = 10 if event is not None and event.shift else 1
        self.current = min(100, self.current + step)

    def bump_down(self, event: InputEvent | None = None) -> None:
        step = 10 if event is not None and event.shift else 1
        self.current = max(1, self.current - step)

    def guess(self) -> None:
        self.guesses += 1
        if self.current == self.target:
            self.hint = f"Correct in {self.guesses}!  (R to play again)"
        elif self.current < self.target:
            self.hint = "Higher"
        else:
            self.hint = "Lower"

    def reset(self) -> None:
        self.target = random.randint(1, 100)
        self.current = 50
        self.guesses = 0
        self.hint = "Guess 1–100. Shift to jump by 10."

    # -- save / load ---------------------------------------------------------

    def get_save_state(self) -> dict:
        return {
            "target": self.target,
            "current": self.current,
            "guesses": self.guesses,
            "hint": self.hint,
        }

    def load_save_state(self, state: dict) -> None:
        self.target = state["target"]
        self.current = state["current"]
        self.guesses = state["guesses"]
        self.hint = state["hint"]

    # -- declarative UI ------------------------------------------------------

    def on_enter(self) -> None:
        self.ui.add(Label(
            "Guess the Number", text_style="title",
            anchor=Anchor.TOP_CENTER, margin=20,
        ))
        self.ui.add(Label(
            lambda: str(self.current), text_style="display",
            anchor=Anchor.CENTER,
        ))
        self.ui.add(Row(
            Label(lambda: f"Guesses {self.guesses}", text_style="hud"),
            Label(lambda: self.hint, text_style="hud"),
            spacing=24,
            anchor=Anchor.BOTTOM_CENTER, margin=24,
        ))
        self.ui.add(Label(
            "↑/W up   ↓/S down   Shift = ±10   Space guess   R reset",
            text_style="caption",
            anchor=Anchor.BOTTOM_LEFT, margin=16,
        ))


def build_theme() -> Theme:
    return Theme(
        font="Cinzel",  # iter-26 bundled
        text_styles={
            "title":   TextStyle(font_size=26, color=GOLD),
            "display": TextStyle(font_size=72, color=WHITE),
            "hud":     TextStyle(font_size=18, color=DIM),
            "caption": TextStyle(font_size=13, color=(140, 150, 170, 255)),
        },
    )


def main() -> None:
    game = Game(
        "Guess the Number",
        resolution=(800, 600),
        fullscreen=False,
        backend="pyglet",
        theme=build_theme(),
    )
    game.run(GuessScene())


if __name__ == "__main__":
    main()
