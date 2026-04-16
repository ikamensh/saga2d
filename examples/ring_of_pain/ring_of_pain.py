"""Ring of Pain — minimal sketch in saga2d.

Nodes are arranged in a circle; the player moves clockwise/counterclockwise
around the ring and interacts with the current node. Not a full port — this
is a thin slice meant to stress the saga2d API and surface friction points.
"""

from __future__ import annotations

import math
import random
import sys
from dataclasses import dataclass, field
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
    ring_positions,
)

BG_COLOR = (18, 14, 28, 255)
WHITE = (245, 245, 250, 255)
DIM = (140, 140, 150, 255)
HP_COLOR = (255, 140, 160, 255)
COIN_COLOR = (245, 205, 90, 255)
PLAYER_GOLD = (255, 215, 100, 255)
TITLE_GOLD = (255, 215, 100, 255)
CURRENT_OUTLINE = (255, 235, 170, 255)

TYPE_ENEMY = "enemy"
TYPE_TREASURE = "treasure"
TYPE_HEART = "heart"
TYPE_SHOP = "shop"
TYPE_PORTAL = "portal"

NODE_STYLES: dict[str, dict] = {
    TYPE_ENEMY:    {"fill": (110, 30, 40, 255),  "rim": (235, 80, 95, 255),   "glyph": "E"},
    TYPE_TREASURE: {"fill": (120, 85, 25, 255),  "rim": (245, 205, 90, 255),  "glyph": "$"},
    TYPE_HEART:    {"fill": (110, 35, 55, 255),  "rim": (255, 130, 150, 255), "glyph": "+"},
    TYPE_SHOP:     {"fill": (35, 80, 105, 255),  "rim": (120, 190, 230, 255), "glyph": "S"},
    TYPE_PORTAL:   {"fill": (60, 45, 115, 255),  "rim": (180, 140, 255, 255), "glyph": "O"},
}


@dataclass
class Node:
    type: str
    data: dict = field(default_factory=dict)
    alive: bool = True


class RingOfPainScene(Scene):
    background_color = BG_COLOR

    def __init__(self, ring_size: int = 8, seed: int | None = 7) -> None:
        super().__init__()
        self.ring_size = ring_size
        self._seed = seed
        self.nodes: list[Node] = self._roll_nodes(seed)
        self.player_idx = 0
        self.max_hp = 10
        self.hp = 10
        self.coins = 0
        self.level = 1
        self.message = "Floor 1 — clear the ring."

    def _roll_nodes(self, seed: int | None) -> list[Node]:
        rng = random.Random(seed)
        pool = [
            TYPE_ENEMY, TYPE_ENEMY, TYPE_ENEMY,
            TYPE_TREASURE, TYPE_TREASURE,
            TYPE_HEART,
            TYPE_SHOP,
            TYPE_PORTAL,
        ]
        rng.shuffle(pool)
        nodes: list[Node] = []
        for t in pool[: self.ring_size]:
            if t == TYPE_ENEMY:
                nodes.append(Node(t, data={"hp": rng.randint(2, 4), "atk": rng.randint(1, 2)}))
            elif t == TYPE_TREASURE:
                nodes.append(Node(t, data={"coins": rng.randint(2, 5)}))
            elif t == TYPE_HEART:
                nodes.append(Node(t, data={"heal": 3}))
            else:
                nodes.append(Node(t))
        return nodes

    # -- input ---------------------------------------------------------------

    def handle_input(self, event: InputEvent) -> bool:
        if event.type != "key_press":
            return False
        if event.action == "right" or event.key in ("right", "d"):
            self.player_idx = (self.player_idx + 1) % self.ring_size
            return True
        if event.action == "left" or event.key in ("left", "a"):
            self.player_idx = (self.player_idx - 1) % self.ring_size
            return True
        if event.action == "confirm" or event.key == "space":
            self._interact()
            return True
        return False

    # -- logic ---------------------------------------------------------------

    def _interact(self) -> None:
        node = self.nodes[self.player_idx]
        if not node.alive:
            self.message = "Nothing here."
            return
        t = node.type
        if t == TYPE_ENEMY:
            node.data["hp"] -= 2
            dmg = node.data.get("atk", 1)
            self.hp = max(0, self.hp - dmg)
            if node.data["hp"] <= 0:
                node.alive = False
                self.message = f"Slew enemy (-{dmg} HP)."
            else:
                self.message = f"Hit enemy ({node.data['hp']} HP left, -{dmg})."
        elif t == TYPE_TREASURE:
            self.coins += node.data["coins"]
            node.alive = False
            self.message = f"+{node.data['coins']} coins."
        elif t == TYPE_HEART:
            gain = min(node.data["heal"], self.max_hp - self.hp)
            self.hp += gain
            node.alive = False
            self.message = f"Healed {gain} HP."
        elif t == TYPE_SHOP:
            self.message = "Shop (NYI)."
        elif t == TYPE_PORTAL:
            self.level += 1
            self.nodes = self._roll_nodes(seed=None)
            self.player_idx = 0
            self.message = f"Descended to floor {self.level}."

    # -- drawing -------------------------------------------------------------

    def _sub_label(self, node: Node) -> str:
        if not node.alive:
            return "cleared"
        t = node.type
        if t == TYPE_ENEMY:
            return f"{node.data['hp']} HP  {node.data['atk']} ATK"
        if t == TYPE_TREASURE:
            return f"+{node.data['coins']}g"
        if t == TYPE_HEART:
            return f"+{node.data['heal']} HP"
        if t == TYPE_SHOP:
            return "shop"
        if t == TYPE_PORTAL:
            return f"→ floor {self.level + 1}"
        return ""

    # -- Declarative HUD ----------------------------------------------------
    # Labels bound to scene attributes rebind every frame; no manual
    # `self.hp_label.text = …` wiring needed after each state change.

    def on_enter(self) -> None:
        # Corner labels use named theme styles — appearance lives in
        # build_theme(), not scattered across call sites.
        self.ui.add(Label(
            "Ring of Pain",
            text_style="title",
            anchor=Anchor.TOP_LEFT, margin=20,
        ))
        self.ui.add(Label(
            lambda: f"Floor {self.level}",
            text_style="hud",
            anchor=Anchor.TOP_RIGHT, margin=20,
        ))
        # HUD row: Row() is a transparent horizontal container. Children
        # are positional; each HP/Coins label binds reactively.
        self.ui.add(Row(
            Label(
                lambda: f"HP {self.hp}/{self.max_hp}",
                text_style="hud", text_color=HP_COLOR,
            ),
            Label(
                lambda: f"Coins {self.coins}",
                text_style="hud", text_color=COIN_COLOR,
            ),
            spacing=26,
            anchor=Anchor.BOTTOM_LEFT, margin=16,
        ))
        self.ui.add(Label(
            "\u2190  \u2192  move     space  interact",
            text_style="caption",
            anchor=Anchor.BOTTOM_RIGHT, margin=20,
        ))
        # Message sits in the empty ring centre — lots of clear space, and
        # no risk of collision with the bottom sub-label or the HUD row.
        self.ui.add(Label(
            lambda: self.message,
            text_style="sub",
            anchor=Anchor.CENTER,
        ))

    # -- Ring & player drawing (inherently per-frame procedural) ----------

    def draw(self) -> None:
        w, h = self.game.resolution

        # Ring geometry — sub-labels must clear HUD (bottom) and title (top).
        cx = w / 2
        cy = h / 2 - 5
        ring_r = min(w, h - 120) * 0.33
        node_r = int(min(w, h - 120) * 0.09)

        positions = ring_positions(self.ring_size, (cx, cy), ring_r)

        for idx, (node, (nx_f, ny_f)) in enumerate(zip(self.nodes, positions)):
            nx, ny = int(nx_f), int(ny_f)
            style = NODE_STYLES[node.type]
            is_current = idx == self.player_idx

            # Subtle outline behind the current node — pairs with the
            # external gold pip for both semantic (YOU token) and visual
            # (rim emphasis) feedback. Kept thin (2 px) so it reads as
            # *"focus"* rather than *"selected styling"*.
            if is_current:
                self.draw_circle(nx, ny, node_r + 6, CURRENT_OUTLINE)

            if node.alive:
                self.draw_circle(nx, ny, node_r + 3, style["rim"])
                self.draw_circle(nx, ny, node_r, style["fill"])
            else:
                self.draw_circle(nx, ny, node_r + 3, (70, 70, 85, 255))
                self.draw_circle(nx, ny, node_r, (40, 40, 52, 255))

            self.draw_text(
                style["glyph"] if node.alive else "x",
                nx, ny,
                font_size=int(node_r * 0.85),
                color=WHITE if node.alive else DIM,
                anchor_x="center", anchor_y="center",
            )

            # Consistent sub-label under every node.
            self.draw_text(
                self._sub_label(node),
                nx, ny + node_r + 18,
                style="sub" if node.alive else "caption",
                anchor_x="center", anchor_y="center",
            )

        # Player token — a distinct gold pip *outside* the ring, visually
        # separate from node styling. Previously a white glow around the
        # current node which read as "selected state" rather than "player".
        nx_f, ny_f = positions[self.player_idx]
        dx, dy = nx_f - cx, ny_f - cy
        d = math.hypot(dx, dy) or 1.0
        pip_offset = node_r + 20
        px = int(nx_f + dx / d * pip_offset)
        py = int(ny_f + dy / d * pip_offset)
        # Faint halo so the pip reads as emissive against dark bg.
        self.draw_circle(px, py, 18, (255, 215, 100, 55))
        self.draw_circle(px, py, 13, PLAYER_GOLD)
        self.draw_circle(px, py, 8, (20, 20, 30, 255))

        # "YOU" caption just beyond the pip — bigger than before so the
        # player indicator carries real visual weight.
        cap_offset = pip_offset + 26
        cx2 = int(nx_f + dx / d * cap_offset)
        cy2 = int(ny_f + dy / d * cap_offset)
        self.draw_text(
            "YOU", cx2, cy2,
            font_size=18, color=PLAYER_GOLD,
            anchor_x="center", anchor_y="center",
        )


def build_theme() -> Theme:
    """Dungeon-crawl theme — passed through Game(theme=…) so the same
    styling applies to production and to the screenshot harness.

    Every text role Ring of Pain uses lives here. Adding a new HUD
    element is then a one-liner at the call site::

        Label(lambda: f"Stamina {self.stamina}", text_style="hud")

    …with zero appearance decisions duplicated.
    """
    return Theme(
        text_styles={
            "title":   TextStyle(font_size=26, color=TITLE_GOLD),
            "hud":     TextStyle(font_size=18, color=WHITE),
            "sub":     TextStyle(font_size=14, color=(220, 220, 232, 240)),
            "caption": TextStyle(font_size=13, color=(155, 155, 170, 255)),
        },
    )


def main() -> None:
    game = Game(
        "Ring of Pain (saga2d sketch)",
        resolution=(800, 600),
        fullscreen=False,
        backend="pyglet",
        theme=build_theme(),
    )
    game.run(RingOfPainScene())


if __name__ == "__main__":
    main()
