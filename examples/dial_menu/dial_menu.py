"""Dial menu — a radial selector.

Proof-of-concept second example for saga2d's iter-2..12 API stack:

* :func:`saga2d.ring_positions` arranges N options around a circle.
* :func:`saga2d.ring_budget` sizes the ring without magic literals.
* ``Scene.controls`` is a declarative dict — arrow keys rotate
  selection, Enter/Space confirm, Esc cancels.
* Reactive :class:`Label` binds to ``self.selected`` for live status.
* ``Game(theme=…)`` shares typography between production and harness.

Under 100 lines.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from saga2d import (  # noqa: E402
    Anchor,
    Game,
    Label,
    Scene,
    Selector,
    TextStyle,
    Theme,
    ring_budget,
    ring_positions,
)

BG = (16, 18, 28, 255)
DIM = (90, 95, 115, 255)
ACCENT = (80, 200, 255, 255)
GOLD = (255, 215, 100, 255)
WHITE = (245, 245, 250, 255)

OPTIONS = [
    "New Game",
    "Continue",
    "Settings",
    "Achievements",
    "Credits",
    "Quit",
]


class DialMenuScene(Scene):
    background_color = BG
    controls = {
        ("right", "d"):        "rotate_cw",
        ("left", "a"):         "rotate_ccw",
        ("confirm", "space"):  "confirm",
        "cancel":              "cancel",
    }

    def __init__(self, options: list[str] | None = None) -> None:
        super().__init__()
        self.selector: Selector[str] = Selector(options or OPTIONS)
        self.status = "Use ← / → to choose, Enter to confirm."

    def get_save_state(self) -> dict:
        return {
            "selected_index": self.selector.index,
            "options": list(self.selector.options),
            "status": self.status,
        }

    def load_save_state(self, state: dict) -> None:
        # Replace-then-set guards against the options list drifting from
        # what was saved (e.g. a later version added a new menu item).
        self.selector.replace(state.get("options", list(OPTIONS)))
        self.selector.set_index(state["selected_index"])
        self.status = state["status"]

    def rotate_cw(self) -> None:
        self.selector.next()

    def rotate_ccw(self) -> None:
        self.selector.prev()

    def confirm(self) -> None:
        self.status = f"Selected: {self.selector.value}"

    def cancel(self) -> None:
        self.status = "Cancelled."

    def on_enter(self) -> None:
        self.ui.add(Label(
            "Dial Menu",
            text_style="title",
            anchor=Anchor.TOP_LEFT, margin=20,
        ))
        self.ui.add(Label(
            lambda: self.selector.value,
            text_style="heading", text_color=GOLD,
            anchor=Anchor.CENTER,
        ))
        self.ui.add(Label(
            lambda: self.status,
            text_style="caption",
            anchor=Anchor.BOTTOM, margin=24,
        ))

    def draw(self) -> None:
        w, h = self.game.resolution
        cx, cy = w / 2, h / 2
        ring_r, node_r_f = ring_budget(
            (w, h), len(self.selector),
            margin_top=60, margin_bottom=60,
            margin_x=40, label_height=14, label_gap=18,
        )
        node_r = int(node_r_f)
        positions = ring_positions(len(self.selector), (cx, cy), ring_r)

        for idx, (opt, (nx, ny)) in enumerate(zip(self.selector.options, positions)):
            nx, ny = int(nx), int(ny)
            is_current = idx == self.selector.index
            if is_current:
                self.draw_circle(nx, ny, node_r + 6, ACCENT)
            self.draw_circle(nx, ny, node_r + 2, DIM)
            self.draw_circle(nx, ny, node_r, BG)
            self.draw_text(
                opt, nx, ny,
                font_size=int(node_r * 0.28),
                color=WHITE if is_current else DIM,
                anchor_x="center", anchor_y="center",
            )


def build_theme() -> Theme:
    return Theme(
        font="Cinzel",  # iter-26 bundled OFL font — see assets/fonts/
        text_styles={
            "title":   TextStyle(font_size=28, color=ACCENT),
            "heading": TextStyle(font_size=42, color=GOLD),
            "caption": TextStyle(font_size=13, color=DIM),
        },
    )


def main() -> None:
    game = Game(
        "Dial Menu Example",
        resolution=(800, 600),
        fullscreen=False,
        backend="pyglet",
        theme=build_theme(),
    )
    game.run(DialMenuScene())


if __name__ == "__main__":
    main()
