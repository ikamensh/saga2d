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

from saga2d import Game, InputEvent, Scene, ring_positions  # noqa: E402

BG_COLOR = (18, 14, 28, 255)
GOLD = (255, 220, 80, 255)
WHITE = (245, 245, 250, 255)
DIM = (140, 140, 150, 255)
SUB_LABEL = (210, 210, 225, 230)
MUTED = (155, 155, 170, 255)
HP_COLOR = (255, 140, 160, 255)
COIN_COLOR = (245, 205, 90, 255)
CURRENT_GLOW = (255, 255, 255, 255)

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
            return f"{node.data['hp']} HP  {node.data['atk']} atk"
        if t == TYPE_TREASURE:
            return f"+{node.data['coins']}g"
        if t == TYPE_HEART:
            return f"+{node.data['heal']} HP"
        if t == TYPE_SHOP:
            return "shop"
        if t == TYPE_PORTAL:
            return f"→ floor {self.level + 1}"
        return ""

    def draw(self) -> None:
        w, h = self.game.resolution

        # Title (top-left) and floor (top-right) stay clear of the ring area.
        self.draw_text(
            "Ring of Pain", 20, 28,
            font_size=22, color=GOLD,
            anchor_x="left", anchor_y="center",
        )
        self.draw_text(
            f"Floor {self.level}", w - 20, 28,
            font_size=18, color=WHITE,
            anchor_x="right", anchor_y="center",
        )

        # Ring geometry — sized so sub-labels never hit the title at the top
        # or the HUD / message at the bottom.
        cx = w / 2
        cy = h / 2 - 5
        ring_r = min(w, h - 120) * 0.33
        node_r = int(min(w, h - 120) * 0.09)

        positions = ring_positions(self.ring_size, (cx, cy), ring_r)

        for idx, (node, (nx_f, ny_f)) in enumerate(zip(self.nodes, positions)):
            nx, ny = int(nx_f), int(ny_f)
            style = NODE_STYLES[node.type]
            is_current = idx == self.player_idx

            # Current-node highlight — thick white ring behind the node.
            if is_current:
                self.draw_circle(nx, ny, node_r + 7, CURRENT_GLOW)

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
                font_size=13,
                color=SUB_LABEL if node.alive else MUTED,
                anchor_x="center", anchor_y="center",
            )

        # Message (above the HUD so it never fights HP/Coins for the baseline).
        self.draw_text(
            self.message, int(cx), h - 44,
            font_size=14, color=MUTED,
            anchor_x="center", anchor_y="center",
        )

        # HUD — single row across the bottom.
        self.draw_text(
            f"HP {self.hp}/{self.max_hp}", 20, h - 20,
            font_size=18, color=HP_COLOR,
            anchor_x="left", anchor_y="center",
        )
        self.draw_text(
            f"Coins {self.coins}", 160, h - 20,
            font_size=18, color=COIN_COLOR,
            anchor_x="left", anchor_y="center",
        )
        self.draw_text(
            "←  →  move     space  interact",
            w - 20, h - 20,
            font_size=14, color=MUTED,
            anchor_x="right", anchor_y="center",
        )


def main() -> None:
    game = Game(
        "Ring of Pain (saga2d sketch)",
        resolution=(800, 600),
        fullscreen=False,
        backend="pyglet",
    )
    game.run(RingOfPainScene())


if __name__ == "__main__":
    main()
