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

from saga2d import Game, InputEvent, Scene  # noqa: E402

BG_COLOR = (18, 14, 28, 255)
RING_TRAIL = (70, 50, 100, 160)

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
        self.message = "Arrow keys: move   Space: interact"

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

    def draw(self) -> None:
        w, h = self.game.resolution
        cx, cy = w / 2, h / 2
        radius = min(w, h) * 0.32
        node_r = int(min(w, h) * 0.085)

        # Faint ring trail (dotted)
        for i in range(72):
            a = 2 * math.pi * i / 72
            x = cx + radius * math.cos(a)
            y = cy + radius * math.sin(a)
            self.draw_circle(int(x), int(y), 2, RING_TRAIL)

        # Nodes
        for idx, node in enumerate(self.nodes):
            ang = -math.pi / 2 + 2 * math.pi * idx / self.ring_size
            nx = int(cx + radius * math.cos(ang))
            ny = int(cy + radius * math.sin(ang))
            style = NODE_STYLES[node.type]
            if node.alive:
                # Outer rim
                self.draw_circle(nx, ny, node_r + 3, style["rim"])
                self.draw_circle(nx, ny, node_r, style["fill"])
            else:
                self.draw_circle(nx, ny, node_r, (50, 50, 60, 255))
            glyph = style["glyph"] if node.alive else "x"
            self.draw_text(
                glyph, nx, ny,
                font_size=int(node_r * 0.9),
                color=(255, 255, 255, 255) if node.alive else (140, 140, 150, 255),
                anchor_x="center", anchor_y="center",
            )
            # Tiny HP / coin hint under enemies/treasure
            hint: str | None = None
            if node.alive and node.type == TYPE_ENEMY:
                hint = f"HP {node.data['hp']}"
            elif node.alive and node.type == TYPE_TREASURE:
                hint = f"{node.data['coins']}g"
            if hint:
                self.draw_text(
                    hint, nx, ny + node_r + 14,
                    font_size=12,
                    color=(210, 210, 220, 255),
                    anchor_x="center", anchor_y="center",
                )

        # Player marker — small disc just inside the ring on the current node
        ang = -math.pi / 2 + 2 * math.pi * self.player_idx / self.ring_size
        px = int(cx + (radius - node_r - 14) * math.cos(ang))
        py = int(cy + (radius - node_r - 14) * math.sin(ang))
        self.draw_circle(px, py, 11, (245, 245, 255, 255))
        self.draw_circle(px, py, 6, (20, 20, 30, 255))

        # Center emblem
        self.draw_circle(int(cx), int(cy), 18, (40, 30, 55, 255))
        self.draw_text(
            "YOU", int(cx), int(cy),
            font_size=12, color=(230, 230, 240, 255),
            anchor_x="center", anchor_y="center",
        )

        # Title
        self.draw_text(
            "Ring of Pain", int(cx), 40,
            font_size=30, color=(255, 220, 80, 255),
            anchor_x="center", anchor_y="center",
        )
        self.draw_text(
            "(saga2d sketch)", int(cx), 66,
            font_size=13, color=(170, 170, 190, 255),
            anchor_x="center", anchor_y="center",
        )

        # HUD
        self.draw_text(
            f"HP {self.hp}/{self.max_hp}", 20, h - 24,
            font_size=18, color=(255, 140, 160, 255),
            anchor_x="left", anchor_y="center",
        )
        self.draw_text(
            f"Coins {self.coins}", 20, h - 48,
            font_size=18, color=(245, 205, 90, 255),
            anchor_x="left", anchor_y="center",
        )
        self.draw_text(
            f"Floor {self.level}", w - 20, h - 24,
            font_size=18, color=(220, 220, 235, 255),
            anchor_x="right", anchor_y="center",
        )

        # Message
        self.draw_text(
            self.message, int(cx), h - 24,
            font_size=14, color=(200, 200, 215, 255),
            anchor_x="center", anchor_y="center",
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
