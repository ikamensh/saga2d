"""Minimal Saga2D smoke test: Game + Scene + Sprite + MoveTo.

Runs headless (mock backend) — safe for CI and agents; no GUI window.

Run from repo root::

    uv run python scripts/smoke_game_move_to.py
"""

from __future__ import annotations

import math
import shutil
import tempfile
from pathlib import Path

from saga2d import Game, MoveTo, Scene, Sprite

# --- inputs (edit here) ---
RESOLUTION = (640, 480)
SPRITE_START = (40, 120)
MOVE_TARGET = (520, 120)
MOVE_SPEED = 400.0
DT = 1 / 60
MAX_TICKS = 600  # safety cap (~10 s at 60 Hz)
# ---


class SmokeScene(Scene):
    def on_enter(self) -> None:
        self._hero = Sprite("sprites/dot", position=SPRITE_START)
        self.add_sprite(self._hero)
        self._hero.do(MoveTo(MOVE_TARGET, speed=MOVE_SPEED))


def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="saga2d_smoke_"))
    try:
        (root / "images" / "sprites").mkdir(parents=True)
        (root / "images" / "sprites" / "dot.png").write_bytes(b"png")

        game = Game(
            "Smoke",
            backend="mock",
            resolution=RESOLUTION,
            asset_path=root,
        )
        scene = SmokeScene()
        game.push(scene)

        for _ in range(MAX_TICKS):
            game.tick(dt=DT)
            sx, sy = scene._hero.position
            if math.hypot(MOVE_TARGET[0] - sx, MOVE_TARGET[1] - sy) < 1.0:
                break
        else:
            raise RuntimeError(
                f"MoveTo did not finish within {MAX_TICKS} ticks; last position=({sx}, {sy})"
            )

        game._teardown()
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print("PASS — smoke: Game, Scene, Sprite, MoveTo")


if __name__ == "__main__":
    main()
