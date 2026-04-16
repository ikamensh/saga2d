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
    Label,
    ProgressBar,
    Row,
    Scene,
    TextStyle,
    Theme,
    ring_budget,
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
    # Heart deliberately uses green, not pink — gain must read as a
    # different category from threat (red) in the palette.
    TYPE_HEART:    {"fill": (35, 100, 60, 255),  "rim": (120, 220, 140, 255), "glyph": "+"},
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

    # Declarative input map — pair aliases in tuples; values are method
    # names on this class resolved at dispatch time. Replaces the
    # iter-6 _bind_controls() imperative helper.
    controls = {
        ("right", "d"):       "rotate_cw",
        ("left", "a"):        "rotate_ccw",
        ("confirm", "space"): "interact",
    }

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
    # Key mappings live in the class-level ``controls`` dict above. These
    # methods are the targets the dispatcher resolves via getattr.

    def rotate_cw(self) -> None:
        self.player_idx = (self.player_idx + 1) % self.ring_size

    def rotate_ccw(self) -> None:
        self.player_idx = (self.player_idx - 1) % self.ring_size

    def interact(self) -> None:
        self._interact()

    # -- logic ---------------------------------------------------------------

    # -- save / load --------------------------------------------------------
    # iter-29 exercises saga2d's save subsystem (shipping since iter-1 but
    # never demonstrated through the examples). ``game.save(slot)`` calls
    # ``get_save_state`` on the top scene and writes the dict as JSON via
    # the :class:`SaveManager`. ``game.load(slot)`` reads it back and calls
    # ``load_save_state`` on the current top scene.

    def get_save_state(self) -> dict:
        return {
            "player_idx": self.player_idx,
            "max_hp": self.max_hp,
            "hp": self.hp,
            "coins": self.coins,
            "level": self.level,
            "message": self.message,
            "ring_size": self.ring_size,
            "nodes": [
                {"type": n.type, "data": n.data, "alive": n.alive}
                for n in self.nodes
            ],
        }

    def load_save_state(self, state: dict) -> None:
        self.player_idx = state["player_idx"]
        self.max_hp = state["max_hp"]
        self.hp = state["hp"]
        self.coins = state["coins"]
        self.level = state["level"]
        self.message = state["message"]
        self.ring_size = state["ring_size"]
        self.nodes = [
            Node(type=n["type"], data=dict(n["data"]), alive=n["alive"])
            for n in state["nodes"]
        ]

    def _play(self, sound: str) -> None:
        """Fire-and-forget SFX via saga2d's AudioManager. ``optional=True``
        so a game run without the WAV files (e.g. a stripped demo)
        doesn't crash — a missing sound is just silence. iter-32
        added procedurally-generated ``hit/coin/heal.wav`` under
        ``assets/sounds/``; see ``scripts/generate_sfx.py``."""
        try:
            self.game.audio.play_sound(sound, optional=True)
        except Exception:
            pass

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
            self._play("hit")
            if node.data["hp"] <= 0:
                node.alive = False
                self.message = f"Slew enemy (-{dmg} HP)."
            else:
                self.message = f"Hit enemy ({node.data['hp']} HP left, -{dmg})."
        elif t == TYPE_TREASURE:
            self.coins += node.data["coins"]
            node.alive = False
            self._play("coin")
            self.message = f"+{node.data['coins']} coins."
        elif t == TYPE_HEART:
            gain = min(node.data["heal"], self.max_hp - self.hp)
            self.hp += gain
            node.alive = False
            self._play("heal")
            self.message = f"Healed {gain} HP."
        elif t == TYPE_SHOP:
            self.message = "Shop (NYI)."
        elif t == TYPE_PORTAL:
            self.level += 1
            self.nodes = self._roll_nodes(seed=None)
            self.player_idx = 0
            self._play("coin")  # portal chime reuses coin SFX
            self.message = f"Descended to floor {self.level}."

    # -- drawing -------------------------------------------------------------

    def _sub_label(self, node: Node) -> str:
        # Short, uniform-width labels so every node caption fits in the
        # same footprint when placed centered-below (iter-9 consensus fix).
        # No horizontal arrows (their tail caused the iter-5..iter-6
        # `→ floor 2` ↔ neighbour-E collision).
        if not node.alive:
            return "cleared"
        t = node.type
        if t == TYPE_ENEMY:
            return f"{node.data['hp']} HP · {node.data['atk']} ATK"
        if t == TYPE_TREASURE:
            return f"+{node.data['coins']} GOLD"
        if t == TYPE_HEART:
            return f"+{node.data['heal']} HP"
        if t == TYPE_SHOP:
            return "SHOP"
        if t == TYPE_PORTAL:
            return f"FLOOR {self.level + 1}"
        return ""

    # -- Declarative HUD ----------------------------------------------------
    # Labels bound to scene attributes rebind every frame; no manual
    # `self.hp_label.text = …` wiring needed after each state change.

    def on_enter(self) -> None:
        # Controls come from the class-level ``controls`` dict — no
        # imperative bind_key calls needed.
        # Load the iter-33 procedurally-generated player-token sprite.
        # ``optional`` try/except so a stripped-down deploy without
        # the PNG still runs (falls back to primitive pip draw).
        try:
            self._player_token_handle = self.game.assets.image("player_token")
        except Exception:
            self._player_token_handle = None
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
        # HUD row: HP label + reactive ProgressBar + Coins label, all
        # pulling directly from scene state. No manual update wiring.
        self.ui.add(Row(
            Label(
                lambda: f"HP {self.hp}/{self.max_hp}",
                text_style="hud", text_color=HP_COLOR,
            ),
            ProgressBar(
                value=lambda: self.hp,
                max_value=lambda: self.max_hp,
                width=100, height=12,
                bar_color=HP_COLOR,
                bg_color=(60, 30, 40, 255),
            ),
            Label(
                lambda: f"Coins {self.coins}",
                text_style="hud", text_color=COIN_COLOR,
            ),
            spacing=16,
            anchor=Anchor.BOTTOM_LEFT, margin=16,
        ))
        self.ui.add(Label(
            "\u2190  \u2192  move     space  interact",
            text_style="caption",
            anchor=Anchor.BOTTOM_RIGHT, margin=20,
        ))
        # Message sits below the ring. Both Gemini and GPT flagged a
        # centre-of-ring message as "crowds the nodes" in iter-7; the
        # agreement between independent models is the signal that matters
        # (see keras.dev iter-6 meta-lesson on cross-check consensus).
        self.ui.add(Label(
            lambda: self.message,
            text_style="caption",
            anchor=Anchor.BOTTOM, margin=48,
        ))

    # -- Ring & player drawing (inherently per-frame procedural) ----------

    def draw(self) -> None:
        w, h = self.game.resolution

        # Ring geometry computed from the viewport + node-label
        # footprint — no more hand-tuned ``* 0.32`` literal. ``ring_budget``
        # reserves vertical room for the title row (top) and the HUD +
        # message row (bottom), plus one label-footprint above and below
        # the ring for the top-node and bottom-node captions.
        cx = w / 2
        cy = h / 2 - 5
        ring_r, node_r_f = ring_budget(
            (w, h),
            self.ring_size,
            margin_top=60,
            margin_bottom=88,   # HUD row + message baseline
            margin_x=40,
            label_height=14,
            label_gap=18,
        )
        node_r = int(node_r_f)

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

            # Uniform sub-label: fixed vertical offset below every node,
            # centered, same font style. Both Gemini and GPT-5.1 agreed
            # radial placement looked "chaotic" (iter-8 synthesis).
            # Short label text (see ``_sub_label``) keeps the footprint
            # inside the chord between adjacent nodes.
            self.draw_text(
                self._sub_label(node),
                nx, ny + node_r + 18,
                style="sub" if node.alive else "caption",
                anchor_x="center", anchor_y="center",
            )

        # Player token — gold pip always *above* the current node. Since
        # sub-labels live uniformly below each node (iter-9 consensus
        # fix), putting the pip uniformly above guarantees the two
        # visual channels never share pixels, regardless of which node
        # the player is on.
        #
        # iter-33 replaces the three-``draw_circle`` pip with a single
        # :class:`Sprite`-style image. The PNG is generated procedurally
        # by ``scripts/generate_sprites.py`` and checked into
        # ``assets/images/player_token.png``. Falls back to the old
        # procedural pip if the asset is missing (best-effort load in
        # ``on_enter``).
        nx_f, ny_f = positions[self.player_idx]
        px = int(nx_f)
        py = int(ny_f) - (node_r + 20)
        if self._player_token_handle is not None:
            token_size = 48
            self.draw_image(
                self._player_token_handle,
                px - token_size // 2, py - token_size // 2,
                token_size, token_size,
            )
        else:
            self.draw_circle(px, py, 18, (255, 215, 100, 55))
            self.draw_circle(px, py, 13, PLAYER_GOLD)
            self.draw_circle(px, py, 8, (20, 20, 30, 255))

        self.draw_text(
            "YOU", px, py - 32,
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

    ``font`` is now "Cinzel" — iter-26 bundled
    ``assets/fonts/Cinzel.ttf`` (SIL OFL licence; see
    ``assets/fonts/OFL.txt``). saga2d's AssetManager auto-registers
    every TTF under ``assets/fonts/`` on startup, so on pyglet
    backends the name resolves cross-platform.
    """
    return Theme(
        font="Cinzel",
        text_styles={
            "title":   TextStyle(font_size=28, color=TITLE_GOLD),
            "hud":     TextStyle(font_size=18, color=WHITE),
            "sub":     TextStyle(font_size=13, color=(220, 220, 232, 240)),
            "caption": TextStyle(font_size=12, color=(155, 155, 170, 255)),
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
