"""Repro / verification for F28 fix: scene timers survive overlay push/pop.

Run: uv run python scripts/overlay_timer_se12_repro.py

Uses only valid saga2d APIs: Game(mock), Scene.every(interval>0), push/pop.
"""

from __future__ import annotations

from saga2d import Game, Scene

DT = 1.0 / 60.0


def ticks(game: Game, n: int) -> None:
    for _ in range(n):
        game.tick(DT)


class PlayScene(Scene):
    """Registers a 1 Hz repeating timer in on_enter."""

    def on_enter(self) -> None:
        self.fires: list[int] = [0]

        def bump() -> None:
            self.fires[0] += 1

        self.every(1.0, bump)


class OverlayScene(Scene):
    transparent = True
    pop_on_cancel = True

    def on_enter(self) -> None:
        pass


def main() -> None:
    g = Game("F28", backend="mock", resolution=(800, 600))
    try:
        base = PlayScene()
        g.push(base)
        ticks(g, 130)  # ~2.17 s → expect ≥2 fires
        after_warmup = base.fires[0]
        print(f"After ~2.17s on base only: fires={after_warmup}")

        g.push(OverlayScene())
        ticks(g, 5)
        g.pop()
        ticks(g, 2)
        after_overlay = base.fires[0]
        print(f"After push overlay + pop (short ticks): fires={after_overlay}")

        ticks(g, 130)  # another ~2.17s on revealed base
        after_wait = base.fires[0]
        print(f"After another ~2.17s with base revealed: fires={after_wait}")

        # F28 fix: owned timers survive overlay push/pop cycle.
        delta = after_wait - after_overlay
        print(f"Fires gained while base was top after overlay: {delta}")

        if after_warmup < 2:
            print("UNEXPECTED: warmup too weak; increase tick count")
        if delta > 0:
            print("CONFIRMED F28 FIX: timer still firing after overlay cycle")
        else:
            print("REGRESSION: timer NOT firing after overlay (SE12 still present)")
    finally:
        g._teardown()


if __name__ == "__main__":
    main()
