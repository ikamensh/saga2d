"""Reaction-time test — fifth saga2d example, timers subsystem.

The iter-25 retrospective listed "untested subsystems": save/load,
audio, sprites. iter-29/31/32/33 closed those. iter-37 catches a
subsystem I missed in that list — **timers** (``Scene.after`` /
``Scene.every``). This example exercises them end-to-end.

Gameplay:

* A disc sits in the centre. Red means *wait*, green means *click now*.
* Press Space. If the disc is green, reaction time is recorded and
  the attempt counts. If red (too early), an "early!" penalty shows.
* The disc turns green after a random delay of 1–3 seconds, handled
  by ``self.after(delay, self._go_green)``.
* R resets the run.

Under 130 lines.
"""

from __future__ import annotations

import random
import sys
import time
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from saga2d import (  # noqa: E402
    Anchor,
    Game,
    Label,
    Row,
    Scene,
    TextStyle,
    Theme,
)

BG = (18, 20, 30, 255)
RED = (220, 80, 95, 255)
GREEN = (90, 210, 110, 255)
GOLD = (255, 215, 100, 255)
DIM = (180, 190, 210, 255)

STATE_WAITING = "waiting"
STATE_READY = "ready"
STATE_DONE = "done"
STATE_EARLY = "early"


class ReactionTestScene(Scene):
    background_color = BG
    controls = {
        ("confirm", "space"): "click",
        "r":                  "reset",
    }

    def __init__(self) -> None:
        super().__init__()
        self.state = STATE_WAITING
        self.ready_at: float = 0.0
        self.last_reaction: float | None = None
        self.attempts = 0
        self.best: float | None = None

    # -- input ---------------------------------------------------------------

    def click(self) -> None:
        if self.state == STATE_WAITING:
            # Clicked too early.
            self.state = STATE_EARLY
        elif self.state == STATE_READY:
            reaction = time.monotonic() - self.ready_at
            self.last_reaction = reaction
            self.attempts += 1
            if self.best is None or reaction < self.best:
                self.best = reaction
            self.state = STATE_DONE
        # STATE_DONE / STATE_EARLY: click does nothing until reset.

    def reset(self) -> None:
        self.state = STATE_WAITING
        self.last_reaction = None
        self._schedule_go_green()

    def on_enter(self) -> None:
        self._schedule_go_green()
        self.ui.add(Label(
            "Reaction Test", text_style="title",
            anchor=Anchor.TOP_CENTER, margin=20,
        ))
        self.ui.add(Label(
            self._status_text, text_style="display",
            anchor=Anchor.CENTER, margin=0,
        ))
        self.ui.add(Row(
            Label(lambda: f"Attempts {self.attempts}", text_style="hud"),
            Label(self._last_text, text_style="hud"),
            Label(self._best_text, text_style="hud"),
            spacing=28,
            anchor=Anchor.BOTTOM_CENTER, margin=24,
        ))
        self.ui.add(Label(
            "Space: click when green   R: reset",
            text_style="caption",
            anchor=Anchor.BOTTOM_LEFT, margin=16,
        ))

    # -- timer-driven state machine ------------------------------------------

    def _schedule_go_green(self) -> None:
        """``Scene.after(delay, cb)`` — the one saga2d primitive this
        example is here to demonstrate. Delay is randomised so the
        player can't pre-empt."""
        delay = random.uniform(1.0, 3.0)
        self.after(delay, self._go_green)

    def _go_green(self) -> None:
        if self.state == STATE_WAITING:
            self.state = STATE_READY
            self.ready_at = time.monotonic()

    # -- status text sources (reactive Label bindings) -----------------------

    def _status_text(self) -> str:
        if self.state == STATE_WAITING:
            return "Wait for green..."
        if self.state == STATE_READY:
            return "CLICK!"
        if self.state == STATE_DONE:
            return f"{int(self.last_reaction * 1000)} ms"
        if self.state == STATE_EARLY:
            return "Too early — press R"
        return ""

    def _last_text(self) -> str:
        if self.last_reaction is None:
            return "Last —"
        return f"Last {int(self.last_reaction * 1000)} ms"

    def _best_text(self) -> str:
        if self.best is None:
            return "Best —"
        return f"Best {int(self.best * 1000)} ms"

    # -- draw: a single pulse-coloured disc in the centre --------------------

    def draw(self) -> None:
        w, h = self.game.resolution
        color = {
            STATE_WAITING: RED,
            STATE_READY:   GREEN,
            STATE_DONE:    DIM,
            STATE_EARLY:   RED,
        }[self.state]
        # Disc sits above the "display" label for visual emphasis.
        self.draw_circle(w // 2, h // 2 - 80, 60, color)


def build_theme() -> Theme:
    return Theme(
        font="Cinzel",
        text_styles={
            "title":   TextStyle(font_size=26, color=GOLD),
            "display": TextStyle(font_size=52, color=(245, 245, 250, 255)),
            "hud":     TextStyle(font_size=16, color=DIM),
            "caption": TextStyle(font_size=13, color=(140, 150, 170, 255)),
        },
    )


def main() -> None:
    game = Game(
        "Reaction Test",
        resolution=(800, 600),
        fullscreen=False,
        backend="pyglet",
        theme=build_theme(),
    )
    game.run(ReactionTestScene())


if __name__ == "__main__":
    main()
