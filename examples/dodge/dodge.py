"""Dodge — sixth saga2d example, first one built around sprites in motion.

saga2d shipped :class:`Sprite`, :mod:`saga2d.actions`, and
:meth:`Scene.after` long before any example exercised them end-to-end.
iter-43 closes that gap: a minimal arcade dodger where the player ship
slides left-right and asteroid sprites fall from the top, animated by
``Sequence(MoveTo, Remove)`` — the "fire and forget" tween pattern
that :class:`Action` was designed for.

Gameplay:

* A/D or ←/→ moves the ship continuously (held-key tracking via
  :meth:`handle_input`; saga2d has no pressed-set abstraction yet —
  see ``keras.dev`` iter-43 API-friction notes).
* Rocks spawn every ``_spawn_interval`` seconds, animated from
  ``y = -30`` to ``y = canvas_h + 50`` via a single ``MoveTo``
  action. Speed and spawn rate ramp with survived time.
* Collision is AABB, computed each frame (saga2d ships no
  collision utility yet — iter-43 writes it inline).
* Score = seconds survived. Game over freezes the field and
  prompts ``R`` to restart.

Under 230 lines. Every number is tuned for ``resolution=(600, 800)``.
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
    MoveTo,
    Remove,
    Row,
    Scene,
    Sequence,
    Sprite,
    TextStyle,
    Theme,
)

# --- palette ---------------------------------------------------------------

BG = (10, 12, 24, 255)
SCORE_COLOR = (255, 215, 100, 255)
HIGH_SCORE_COLOR = (180, 200, 255, 255)
GAME_OVER_COLOR = (255, 90, 110, 255)
DIM = (160, 170, 200, 255)

# --- geometry --------------------------------------------------------------

SHIP_W = 48
SHIP_H = 48
ROCK_W = 36
ROCK_H = 36

# Tunables — ship speed, rock spawn rate, rock fall speed all ramp with
# survived time. These are the starting values at t = 0.
PLAYER_SPEED = 300          # pixels per second
START_SPAWN_INTERVAL = 1.2  # seconds between rock spawns
START_ROCK_SPEED = 180      # pixels per second
RAMP_RATE = 0.03            # how fast spawn/speed intensify per second


class DodgeScene(Scene):
    background_color = BG

    # Only restart is a discrete one-shot. Movement is continuous, handled
    # by the held-keys set — see ``handle_input``.
    controls = {
        "r": "restart",
    }

    def __init__(self, seed: int | None = 0) -> None:
        super().__init__()
        self._rng = random.Random(seed)
        self._seed = seed
        self._held: set[str] = set()
        self.time_survived: float = 0.0
        self.high_score: float = 0.0
        self.game_over: bool = False
        self._player: Sprite | None = None
        self._rocks: list[Sprite] = []
        self._spawn_clock: float = 0.0

    # -- input --------------------------------------------------------------

    def restart(self) -> None:
        """Reset the run without rebuilding the scene. Keeps high score."""
        # Clear live sprites first so the next frame starts clean.
        if self._player is not None:
            self._player.remove()
        for rock in list(self._rocks):
            rock.remove()
        self._rocks.clear()
        self.time_survived = 0.0
        self.game_over = False
        self._spawn_clock = 0.0
        self._held.clear()
        self._spawn_player()

    def handle_input(self, event: InputEvent) -> bool:
        """Track held keys for continuous movement. saga2d has no
        ``game.input.is_pressed()`` helper yet; the Scene tracks its
        own pressed-set from press/release events instead.

        iter-43 API-friction point: every example that needs held-key
        movement will re-implement this same tracking block. A
        framework-level ``game.input.is_pressed("a")`` would cut ten
        lines from each game."""
        if event.type == "key_press" and event.key is not None:
            self._held.add(event.key)
        elif event.type == "key_release" and event.key is not None:
            self._held.discard(event.key)
        return False  # don't consume — scene stack may want it too

    # -- lifecycle ----------------------------------------------------------

    def on_enter(self) -> None:
        w, h = self.game.resolution
        # HUD Labels reactive to scene state — no manual sync needed.
        self.ui.add(Label("DODGE", text_style="title",
                          anchor=Anchor.TOP_LEFT, margin=20))
        self.ui.add(Label(
            lambda: f"Score  {self.time_survived:5.1f}",
            text_style="hud", text_color=SCORE_COLOR,
            anchor=Anchor.TOP_RIGHT, margin=20,
        ))
        self.ui.add(Label(
            lambda: f"Best   {self.high_score:5.1f}",
            text_style="hud", text_color=HIGH_SCORE_COLOR,
            anchor=Anchor.BOTTOM_RIGHT, margin=20,
        ))
        self.ui.add(Label(
            "A / D     move     R  restart",
            text_style="caption",
            anchor=Anchor.BOTTOM_LEFT, margin=20,
        ))
        self._spawn_player()

    def _spawn_player(self) -> None:
        w, h = self.game.resolution
        self._player = self.add_sprite(Sprite(
            "dodge_ship",
            position=(w // 2, h - 80),
        ))

    def _spawn_rock(self) -> None:
        w, _ = self.game.resolution
        # Random x across the playable strip (leave a little margin
        # so the rock never *starts* half-off-screen on the side).
        x = self._rng.randint(ROCK_W, w - ROCK_W)
        rock = self.add_sprite(Sprite(
            "dodge_rock",
            position=(x, -ROCK_H),
        ))
        _, h = self.game.resolution
        # Fire-and-forget tween — the rock's motion is entirely driven
        # by the Action system. No per-rock state machine, no update()
        # loop for rock position: just one ``Sequence(MoveTo, Remove)``.
        # saga2d's action subsystem is designed for this pattern but
        # no runnable example has previously demonstrated it.
        rock.do(Sequence(
            MoveTo(position=(x, h + ROCK_H), speed=self._rock_speed()),
            Remove(),
        ))
        self._rocks.append(rock)

    def _rock_speed(self) -> float:
        # Smooth ramp: starts at START_ROCK_SPEED, climbs linearly.
        return START_ROCK_SPEED + RAMP_RATE * 60 * self.time_survived

    def _spawn_interval(self) -> float:
        # Interval shrinks as time passes — more rocks at high scores.
        # Clamped so the game stays playable.
        return max(0.35, START_SPAWN_INTERVAL - RAMP_RATE * self.time_survived)

    # -- tick loop ----------------------------------------------------------

    def update(self, dt: float) -> None:
        if self.game_over:
            return

        # Advance clocks.
        self.time_survived += dt
        self._spawn_clock += dt
        if self._spawn_clock >= self._spawn_interval():
            self._spawn_clock = 0.0
            self._spawn_rock()

        # Drop removed rocks (MoveTo/Remove in the action chain will
        # have marked them). The sprite.is_removed property lets us
        # collect them here without racing the Action system.
        self._rocks = [r for r in self._rocks if not r.is_removed]

        # Continuous player movement from the held-keys set.
        if self._player is not None:
            w, _ = self.game.resolution
            dx = 0.0
            if "a" in self._held or "left" in self._held:
                dx -= PLAYER_SPEED * dt
            if "d" in self._held or "right" in self._held:
                dx += PLAYER_SPEED * dt
            new_x = max(SHIP_W / 2, min(w - SHIP_W / 2, self._player.x + dx))
            self._player.x = new_x

        # Collision. iter-43 writes inline — saga2d has no AABB helper
        # in saga2d.util yet (parked in keras.dev as API-friction #2).
        if self._player is not None:
            for rock in self._rocks:
                if _aabb_overlap(
                    self._player.x, self._player.y, SHIP_W, SHIP_H,
                    rock.x, rock.y, ROCK_W, ROCK_H,
                ):
                    self._end_run()
                    return

    def _end_run(self) -> None:
        self.game_over = True
        if self.time_survived > self.high_score:
            self.high_score = self.time_survived
        # Halt every rock so the "game over" frame is a clean freeze
        # rather than rocks continuing to fall and visually compete
        # with the game-over label. Actions can be cancelled via
        # ``sprite.stop_actions()``.
        for rock in self._rocks:
            rock.stop_actions()
        # Surface the game-over banner. Reactive, but dynamically added
        # so it only exists during game-over frames.
        self.ui.add(Label(
            "GAME OVER  —  press R",
            text_style="title", text_color=GAME_OVER_COLOR,
            anchor=Anchor.CENTER,
        ))


def _aabb_overlap(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, by: float, bw: float, bh: float,
) -> bool:
    """Centre-anchored AABB overlap. saga2d's Sprite positions are the
    sprite's visual anchor (default: ``BOTTOM_CENTER``). For the dodge
    sprites both are centered *visually* enough that a simple
    half-width distance test is correct to within 1–2 px — fine for
    arcade gameplay."""
    return (
        abs(ax - bx) < (aw + bw) / 2
        and abs(ay - by) < (ah + bh) / 2
    )


# ---------------------------------------------------------------------------
# Theme — Cinzel title like Ring of Pain, HUD styling matching the scale
# ---------------------------------------------------------------------------


def build_theme() -> Theme:
    return Theme(
        font="Cinzel",
        text_styles={
            "title":   TextStyle(font_size=32, color=(255, 230, 160, 255)),
            "hud":     TextStyle(font_size=18, color=(235, 235, 245, 255)),
            "caption": TextStyle(font_size=14, color=DIM),
        },
    )


def main() -> None:
    game = Game(
        "Dodge (saga2d sprite+actions demo)",
        resolution=(600, 800),
        fullscreen=False,
        backend="pyglet",
        theme=build_theme(),
    )
    game.run(DodgeScene())


if __name__ == "__main__":
    main()
