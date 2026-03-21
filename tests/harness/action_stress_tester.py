"""Action Stress Tester — verifies action completion, edge cases, and resilience.

Stories covered:
  US6  — Create sprites, set positions, animate with MoveTo / FadeIn / FadeOut
  US7  — Composable action trees: Sequence/Parallel/Do/Delay/Repeat/FadeOut
  US8  — Action edge cases: speed=0, NaN speed, Delay(0), empty Sequence, Repeat(0)
  US9  — Sprite lifecycle: remove during action, do() on removed sprite
  US22 — Parallel with finite children completes when all done (+ BUG: vacuous truth)
  US23 — Do(callback) executes callback when reached in Sequence

Additional scenarios:
  Stress  — 100-level deep nesting, 500-wide Parallel, 200 instant chain
  NoHang  — Parallel + infinite Repeat doesn't hang tick()
  NaN     — MoveTo with NaN speed, extreme speeds, tiny dt, already-at-target

Run: python -m tests.harness.action_stress_tester [-v]
"""

from __future__ import annotations

import math
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from saga2d import (
    Delay,
    Do,
    FadeIn,
    FadeOut,
    Game,
    MoveTo,
    Parallel,
    Remove,
    Repeat,
    Scene,
    Sequence,
    Sprite,
)
from saga2d.actions import Action


# ── Helpers ──────────────────────────────────────────────────────────


def _make_asset_dir() -> Path:
    """Create temp dir with minimal assets for sprite tests."""
    root = Path(tempfile.mkdtemp(prefix="saga2d_action_stress_"))
    (root / "images" / "sprites").mkdir(parents=True)
    (root / "images" / "sprites" / "test.png").write_bytes(b"png")
    return root


def _teardown_if_needed() -> None:
    import saga2d.rendering.sprite as _sprite_mod

    if _sprite_mod._current_game is not None:
        _sprite_mod._current_game._teardown()


def _check(
    label: str,
    condition: bool,
    verbose: bool,
    detail: str = "",
) -> bool:
    tag = "OK" if condition else "FAIL"
    if verbose:
        print(f"    {label}: {tag}{f' — {detail}' if detail else ''}")
    return condition


def _tick_until_done(
    game: Game, sprite: Sprite, max_ticks: int = 5000, dt: float = 0.016
) -> int:
    """Tick the game until sprite has no current action. Returns tick count."""
    for i in range(max_ticks):
        game.tick(dt)
        if sprite._current_action is None:
            return i + 1
    return max_ticks


def _pos_finite(sprite: Sprite) -> bool:
    """Check that sprite position has no NaN/inf."""
    x, y = sprite.position
    return math.isfinite(x) and math.isfinite(y)


class _GameCtx:
    """RAII-ish context for Game + temp assets, to reduce boilerplate."""

    def __init__(self) -> None:
        _teardown_if_needed()
        self.asset_dir = _make_asset_dir()
        self.game = Game(
            "ActionStress",
            backend="mock",
            resolution=(800, 600),
            asset_path=self.asset_dir,
        )
        self.game.push(Scene())

    def sprite(self, x: float = 0, y: float = 0) -> Sprite:
        return Sprite("sprites/test", position=(x, y))

    def close(self) -> None:
        self.game._teardown()
        shutil.rmtree(self.asset_dir, ignore_errors=True)


# ═══════════════════════════════════════════════════════════════════════
# US6 — Sprite creation + MoveTo + FadeIn + FadeOut
# ═══════════════════════════════════════════════════════════════════════


def test_us6(verbose: bool) -> tuple[bool, str]:
    """Create sprites, set positions, animate with MoveTo / FadeIn / FadeOut."""
    ctx = _GameCtx()
    ok = True
    findings: list[str] = []
    try:
        # ── Sprite creation and position
        s = ctx.sprite(100, 200)
        ok &= _check(
            "US6-pos",
            s.position == (100.0, 200.0),
            verbose,
            f"initial position {s.position}",
        )
        ok &= _check("US6-alive", not s.is_removed, verbose, "not removed")

        # ── MoveTo
        s.do(MoveTo((300, 400), speed=5000))
        _tick_until_done(ctx.game, s, max_ticks=100)
        x, y = s.position
        ok &= _check(
            "US6-moveto",
            abs(x - 300) < 1 and abs(y - 400) < 1,
            verbose,
            f"MoveTo reached target ({x:.1f}, {y:.1f})",
        )

        # ── FadeOut
        s.do(FadeOut(duration=0.1))
        _tick_until_done(ctx.game, s, max_ticks=50)
        ok &= _check(
            "US6-fadeout", s.opacity == 0, verbose, f"FadeOut → opacity={s.opacity}"
        )

        # ── FadeIn
        s.do(FadeIn(duration=0.1))
        _tick_until_done(ctx.game, s, max_ticks=50)
        ok &= _check(
            "US6-fadein", s.opacity == 255, verbose, f"FadeIn → opacity={s.opacity}"
        )

        # ── Manual position set
        s.position = (42, 84)
        ok &= _check(
            "US6-setpos",
            s.position == (42.0, 84.0),
            verbose,
            f"manual set → {s.position}",
        )

        findings.append("Sprite create/position, MoveTo, FadeOut, FadeIn all verified")
    finally:
        ctx.close()

    if verbose:
        print(f"  US6: {'PASS' if ok else 'FAIL'}")
    return ok, "; ".join(findings)


# ═══════════════════════════════════════════════════════════════════════
# US7 — Composable action trees
# ═══════════════════════════════════════════════════════════════════════


def test_us7(verbose: bool) -> tuple[bool, str]:
    """Build composable action trees with Sequence, Parallel, Do, Delay, Repeat, FadeOut."""
    ctx = _GameCtx()
    ok = True
    findings: list[str] = []
    try:
        # ── Sequence(MoveTo, FadeOut)
        s1 = ctx.sprite(0, 0)
        s1.do(Sequence(MoveTo((100, 0), speed=5000), FadeOut(0.05)))
        _tick_until_done(ctx.game, s1, max_ticks=100)
        ok &= _check(
            "US7-seq",
            abs(s1.position[0] - 100) < 1 and s1.opacity == 0,
            verbose,
            f"Sequence(MoveTo, FadeOut): pos={s1.position}, opacity={s1.opacity}",
        )

        # ── Parallel(MoveTo, FadeIn)
        s2 = ctx.sprite(0, 0)
        s2.opacity = 0
        s2.do(Parallel(MoveTo((50, 50), speed=5000), FadeIn(0.05)))
        _tick_until_done(ctx.game, s2, max_ticks=100)
        ok &= _check(
            "US7-par",
            abs(s2.position[0] - 50) < 1 and s2.opacity == 255,
            verbose,
            f"Parallel(MoveTo, FadeIn): pos={s2.position}, opacity={s2.opacity}",
        )

        # ── Sequence(Parallel(MoveTo, FadeIn), Delay, Do)
        s3 = ctx.sprite(0, 0)
        s3.opacity = 0
        called = [False]
        s3.do(
            Sequence(
                Parallel(MoveTo((80, 0), speed=5000), FadeIn(0.05)),
                Delay(0.05),
                Do(lambda: called.__setitem__(0, True)),
            )
        )
        _tick_until_done(ctx.game, s3, max_ticks=100)
        ok &= _check(
            "US7-nested",
            called[0],
            verbose,
            "Sequence(Parallel(...), Delay, Do) completed; Do fired",
        )

        # ── Repeat(Delay, times=3)
        s4 = ctx.sprite()
        counter = [0]
        s4.do(
            Repeat(
                Sequence(
                    Delay(0.01), Do(lambda: counter.__setitem__(0, counter[0] + 1))
                ),
                times=3,
            )
        )
        _tick_until_done(ctx.game, s4, max_ticks=100)
        ok &= _check(
            "US7-repeat",
            counter[0] == 3,
            verbose,
            f"Repeat(times=3): counter={counter[0]}",
        )

        # ── 100-level deep nesting (Sequence ↔ Parallel alternating)
        inner: Action = Delay(0.01)
        for i in range(100):
            inner = Sequence(inner) if i % 2 == 0 else Parallel(inner)
        s5 = ctx.sprite()
        s5.do(inner)
        ticks = _tick_until_done(ctx.game, s5, max_ticks=200)
        ok &= _check(
            "US7-deep100",
            s5._current_action is None,
            verbose,
            f"100-level deep tree completed in {ticks} ticks",
        )

        # ── 500-wide Parallel
        s6 = ctx.sprite()
        children = [Delay(0.01 * (i % 10 + 1)) for i in range(500)]
        s6.do(Parallel(*children))
        ticks = _tick_until_done(ctx.game, s6, max_ticks=200)
        ok &= _check(
            "US7-wide500",
            s6._current_action is None,
            verbose,
            f"Parallel(500 Delays) done in {ticks} ticks",
        )

        # ── 200 instant Do() chain
        s7 = ctx.sprite()
        cnt = [0]
        s7.do(
            Sequence(*[Do(lambda: cnt.__setitem__(0, cnt[0] + 1)) for _ in range(200)])
        )
        ctx.game.tick(0.016)
        ok &= _check(
            "US7-instant200",
            cnt[0] == 200 and s7._current_action is None,
            verbose,
            f"200 Do() in Sequence: all in 1 tick (count={cnt[0]})",
        )

        findings.append(
            "Composable trees: Seq, Par, Nested, Repeat, 100-deep, 500-wide, 200-instant OK"
        )
    finally:
        ctx.close()

    if verbose:
        print(f"  US7: {'PASS' if ok else 'FAIL'}")
    return ok, "; ".join(findings)


# ═══════════════════════════════════════════════════════════════════════
# US8 — Action edge cases (includes NaN-speed BUG confirmation)
# ═══════════════════════════════════════════════════════════════════════


def test_us8(verbose: bool) -> tuple[bool, str]:
    """Edge cases: speed=0, NaN speed (BUG), Delay(0), empty Sequence, Repeat(0)."""
    ctx = _GameCtx()
    ok = True
    bugs: list[str] = []
    findings: list[str] = []
    try:
        # ── MoveTo speed=0 → ValueError
        try:
            MoveTo((100, 100), speed=0)
            ok &= _check("US8-speed0", False, verbose, "should raise ValueError")
        except ValueError:
            ok &= _check("US8-speed0", True, verbose, "speed=0 raises ValueError")

        # ── MoveTo speed<0 → ValueError
        try:
            MoveTo((100, 100), speed=-5)
            ok &= _check("US8-speed-neg", False, verbose, "should raise ValueError")
        except ValueError:
            ok &= _check("US8-speed-neg", True, verbose, "speed<0 raises ValueError")

        # ── BUG: MoveTo speed=NaN bypasses validation, corrupts sprite position
        #    The check `speed <= 0` evaluates to False for NaN (all NaN comparisons
        #    are False), so NaN passes through. During update(), speed*dt = NaN,
        #    NaN/dist = NaN, and sprite.position becomes (NaN, NaN).
        s_nan = ctx.sprite(10, 20)
        try:
            action = MoveTo((100, 100), speed=float("nan"))
            # If we get here, NaN was NOT rejected — confirm the corruption bug
            s_nan.do(action)
            ctx.game.tick(0.016)
            x, y = s_nan.position
            nan_corrupted = not (math.isfinite(x) and math.isfinite(y))
            ok &= _check(
                "US8-nan-speed",
                nan_corrupted,
                verbose,
                f"BUG CONFIRMED: speed=NaN → position=({x}, {y})",
            )
            bugs.append(
                "MoveTo(speed=NaN) passes `speed <= 0` check, corrupts sprite position to NaN"
            )
        except ValueError:
            # If framework rejects NaN speed at construction, the bug is fixed
            ok &= _check(
                "US8-nan-speed",
                True,
                verbose,
                "speed=NaN now raises ValueError (bug fixed)",
            )
        s_nan.stop_actions()

        # ── MoveTo speed=inf: passes `speed <= 0` but snaps to target (no crash)
        s_inf = ctx.sprite(10, 20)
        try:
            action_inf = MoveTo((100, 100), speed=float("inf"))
            s_inf.do(action_inf)
            ctx.game.tick(0.016)
            ok &= _check(
                "US8-inf-speed",
                _pos_finite(s_inf),
                verbose,
                f"speed=inf snaps to target: pos={s_inf.position} (no crash)",
            )
        except ValueError:
            ok &= _check(
                "US8-inf-speed",
                True,
                verbose,
                "speed=inf now raises ValueError (validation added)",
            )
        s_inf.stop_actions()

        # ── Delay(0): should finish in first update
        s1 = ctx.sprite()
        s1.do(Delay(0))
        ctx.game.tick(0.016)
        ok &= _check(
            "US8-delay0",
            s1._current_action is None,
            verbose,
            "Delay(0) finishes in one tick",
        )

        # ── Delay negative → ValueError
        try:
            Delay(-1)
            ok &= _check("US8-delay-neg", False, verbose, "should raise ValueError")
        except ValueError:
            ok &= _check("US8-delay-neg", True, verbose, "Delay(-1) raises ValueError")

        # ── Empty Sequence: finishes immediately
        s2 = ctx.sprite()
        s2.do(Sequence())
        ctx.game.tick(0.016)
        ok &= _check(
            "US8-empty-seq",
            s2._current_action is None,
            verbose,
            "empty Sequence() finishes immediately",
        )

        # ── Empty Parallel: finishes immediately
        s2b = ctx.sprite()
        s2b.do(Parallel())
        ctx.game.tick(0.016)
        ok &= _check(
            "US8-empty-par",
            s2b._current_action is None,
            verbose,
            "empty Parallel() finishes immediately",
        )

        # ── Repeat(times=0): no-op, finishes immediately
        s3 = ctx.sprite()
        rep_counter = [0]
        s3.do(
            Repeat(Do(lambda: rep_counter.__setitem__(0, rep_counter[0] + 1)), times=0)
        )
        ctx.game.tick(0.016)
        ok &= _check(
            "US8-repeat0-done",
            s3._current_action is None,
            verbose,
            "Repeat(times=0) finishes immediately",
        )
        ok &= _check(
            "US8-repeat0-count",
            rep_counter[0] == 0,
            verbose,
            f"Repeat(times=0) ran 0 iterations (count={rep_counter[0]})",
        )

        # ── Repeat(times=1): runs exactly once
        s4 = ctx.sprite()
        rep1_counter = [0]
        s4.do(
            Repeat(
                Do(lambda: rep1_counter.__setitem__(0, rep1_counter[0] + 1)), times=1
            )
        )
        ctx.game.tick(0.016)
        ok &= _check(
            "US8-repeat1",
            rep1_counter[0] == 1,
            verbose,
            f"Repeat(times=1) ran once (count={rep1_counter[0]})",
        )

        if bugs:
            findings.append(f"BUGS: {'; '.join(bugs)}")
        findings.append(
            "Edge cases: speed=0 rejected, Delay(0)/empty Seq/Par/Repeat(0) all OK"
        )
    finally:
        ctx.close()

    if verbose:
        print(f"  US8: {'PASS' if ok else 'FAIL'}")
    return ok, "; ".join(findings)


# ═══════════════════════════════════════════════════════════════════════
# US9 — Sprite lifecycle: remove during action, do() on removed sprite
# ═══════════════════════════════════════════════════════════════════════


def test_us9(verbose: bool) -> tuple[bool, str]:
    """Sprite removal during action; do() on removed sprite is no-op."""
    ctx = _GameCtx()
    ok = True
    findings: list[str] = []
    try:
        # ── Remove() action in Sequence: sprite removed mid-action
        s1 = ctx.sprite(0, 0)
        post_remove_called = [False]
        s1.do(
            Sequence(
                MoveTo((50, 0), speed=5000),
                Remove(),
                Do(lambda: post_remove_called.__setitem__(0, True)),
            )
        )
        _tick_until_done(ctx.game, s1, max_ticks=50)
        ok &= _check(
            "US9-remove-mid",
            s1.is_removed,
            verbose,
            "sprite removed by Remove() in Sequence",
        )
        # Remove() is an instant action — Sequence's while-loop continues in
        # the same tick, so subsequent instant actions (Do) DO fire.  The sprite
        # is already removed but the Sequence hasn't checked that; this is
        # expected behaviour (instant chaining).
        ctx.game.tick(0.016)
        ctx.game.tick(0.016)
        ok &= _check(
            "US9-post-fires",
            post_remove_called[0],
            verbose,
            "Do() after Remove() fires (instant chain in same tick)",
        )
        # After the tick completes the sprite is no longer ticked by the game
        ok &= _check(
            "US9-no-further-tick",
            s1._current_action is None,
            verbose,
            "sprite has no action after removal + tick",
        )

        # ── sprite.do() on already-removed sprite: silent no-op
        s2 = ctx.sprite(10, 10)
        s2.remove()
        ok &= _check("US9-already-removed", s2.is_removed, verbose, "sprite is removed")
        s2.do(MoveTo((500, 500), speed=100))
        ok &= _check(
            "US9-do-noop",
            s2._current_action is None,
            verbose,
            "do() on removed sprite is no-op",
        )

        # ── External remove while action is running
        s3 = ctx.sprite(0, 0)
        s3.do(MoveTo((1000, 0), speed=10))  # slow, takes ~100s
        ctx.game.tick(0.016)
        ok &= _check(
            "US9-action-running",
            s3._current_action is not None,
            verbose,
            "action running before remove",
        )
        s3.remove()
        ok &= _check(
            "US9-ext-remove", s3.is_removed, verbose, "sprite removed externally"
        )
        ok &= _check(
            "US9-action-cleared",
            s3._current_action is None,
            verbose,
            "action cleared after external remove",
        )
        # Tick should not crash with the sprite gone
        ctx.game.tick(0.016)
        ok &= _check(
            "US9-tick-safe", True, verbose, "tick() after sprite removal: no crash"
        )

        findings.append("Remove mid-action, do() on removed, external remove all safe")
    finally:
        ctx.close()

    if verbose:
        print(f"  US9: {'PASS' if ok else 'FAIL'}")
    return ok, "; ".join(findings)


# ═══════════════════════════════════════════════════════════════════════
# US22 — Parallel completion (+ BUG: vacuous truth with only-infinite)
# ═══════════════════════════════════════════════════════════════════════


def test_us22(verbose: bool) -> tuple[bool, str]:
    """Parallel with finite children: done when BOTH complete.
    BUG: Parallel(only infinite children) completes immediately (vacuous truth).
    """
    ctx = _GameCtx()
    ok = True
    bugs: list[str] = []
    findings: list[str] = []
    try:
        # ── 22a: Two delays — Parallel waits for longer one
        s = ctx.sprite(100, 100)
        done_a = [False]
        done_b = [False]

        class MarkerDelay(Action):
            """Delay that sets a flag when done."""

            def __init__(self, secs: float, flag: list[bool]) -> None:
                self._secs = secs
                self._elapsed = 0.0
                self._flag = flag

            def start(self, sprite: Sprite) -> None:
                pass

            def update(self, dt: float) -> bool:
                self._elapsed += dt
                if self._elapsed >= self._secs:
                    self._flag[0] = True
                    return True
                return False

        s.do(Parallel(MarkerDelay(0.05, done_a), MarkerDelay(0.2, done_b)))
        for _ in range(4):  # ~0.064s: short done, long not
            ctx.game.tick(0.016)
        ok &= _check("US22-a1", done_a[0], verbose, "short delay finished")
        ok &= _check("US22-a2", not done_b[0], verbose, "long delay still running")
        ok &= _check(
            "US22-a3", s._current_action is not None, verbose, "Parallel not done yet"
        )

        ticks = _tick_until_done(ctx.game, s, max_ticks=200)
        ok &= _check("US22-a4", done_b[0], verbose, "long delay now finished")
        ok &= _check(
            "US22-a5",
            s._current_action is None,
            verbose,
            f"Parallel done after {ticks} extra ticks",
        )

        # ── 22b: Two MoveTos — waits for slower one
        s2 = ctx.sprite(0, 0)
        s2.do(Parallel(MoveTo((100, 0), speed=5000), MoveTo((0, 200), speed=50)))
        for _ in range(31):  # ~0.5s
            ctx.game.tick(0.016)
        ok &= _check(
            "US22-b1",
            s2._current_action is not None,
            verbose,
            "Parallel still alive (slow MoveTo)",
        )
        ticks = _tick_until_done(ctx.game, s2, max_ticks=500)
        ok &= _check(
            "US22-b2",
            abs(s2.position[1] - 200) < 1,
            verbose,
            f"slow MoveTo reached target (y={s2.position[1]:.1f})",
        )

        # ── 22c: Infinite + finite — completes when finite done, stops infinite
        s3 = ctx.sprite(50, 50)
        counter = [0]

        class Counter(Action):
            def start(self, sprite: Sprite) -> None:
                pass

            def update(self, dt: float) -> bool:
                counter[0] += 1
                return True

        s3.do(
            Parallel(Repeat(Sequence(Delay(0.01), Counter()), times=None), Delay(0.1))
        )
        ticks = _tick_until_done(ctx.game, s3, max_ticks=200)
        ok &= _check(
            "US22-c1",
            s3._current_action is None,
            verbose,
            f"Parallel(infinite, finite) done after {ticks} ticks",
        )
        ok &= _check(
            "US22-c2",
            counter[0] > 0,
            verbose,
            f"infinite child ran {counter[0]} times before stop",
        )
        count_snapshot = counter[0]
        ctx.game.tick(0.016)
        ctx.game.tick(0.016)
        ok &= _check(
            "US22-c3",
            counter[0] == count_snapshot,
            verbose,
            "infinite child stopped (no more increments)",
        )

        # ── 22d: BUG — Parallel(only infinite children) completes immediately
        #    The Parallel.update() check:
        #        all(self._done[i] or not action.is_finite for ...)
        #    When ALL children have is_finite=False, the `not action.is_finite`
        #    clause is True for each, making the whole expression vacuously True.
        #    Result: Parallel finishes in 1 tick and stop()s all children.
        #
        #    Ideally Parallel(only infinite) SHOULD run forever (or until the
        #    sprite is manually stopped). This is a design gap.
        s4 = ctx.sprite(200, 200)
        inf_counter = [0]

        class InfCounter(Action):
            def start(self, sprite: Sprite) -> None:
                pass

            def update(self, dt: float) -> bool:
                inf_counter[0] += 1
                return True

        s4.do(
            Parallel(
                Repeat(InfCounter(), times=None),
                Repeat(Delay(0.01), times=None),
            )
        )
        ctx.game.tick(0.016)
        vacuous_done = s4._current_action is None
        ok &= _check(
            "US22-d1",
            vacuous_done,
            verbose,
            "BUG CONFIRMED: Parallel(only infinite) finishes in 1 tick (vacuous truth)",
        )
        ok &= _check(
            "US22-d2",
            inf_counter[0] <= 1,
            verbose,
            f"BUG CONFIRMED: infinite child ran only {inf_counter[0]} time(s)",
        )
        bugs.append(
            "Parallel(only infinite children) completes immediately — "
            "vacuous truth in all_finite_done check"
        )

        if bugs:
            findings.append(f"BUGS: {'; '.join(bugs)}")
        findings.append(
            "Parallel finite-completion: two-delay, two-MoveTo, infinite+finite all correct"
        )
    finally:
        ctx.close()

    if verbose:
        print(f"  US22: {'PASS' if ok else 'FAIL'}")
    return ok, "; ".join(findings)


# ═══════════════════════════════════════════════════════════════════════
# US23 — Do(callback) fires when reached in Sequence
# ═══════════════════════════════════════════════════════════════════════


def test_us23(verbose: bool) -> tuple[bool, str]:
    """Do(callback) executes exactly once when reached in Sequence."""
    ctx = _GameCtx()
    ok = True
    findings: list[str] = []
    try:
        # ── 23a: Sequence(Delay, Do) — fires after delay
        s = ctx.sprite()
        called = [0]
        s.do(Sequence(Delay(0.05), Do(lambda: called.__setitem__(0, called[0] + 1))))
        ctx.game.tick(0.016)
        ctx.game.tick(0.016)
        ok &= _check(
            "US23-a1", called[0] == 0, verbose, f"not yet (called={called[0]})"
        )
        _tick_until_done(ctx.game, s, max_ticks=50)
        ok &= _check(
            "US23-a2", called[0] == 1, verbose, f"fired once (called={called[0]})"
        )

        # ── 23b: Sequence(Do, Do, Do) — all fire in one frame
        s2 = ctx.sprite()
        order: list[str] = []
        s2.do(
            Sequence(
                Do(lambda: order.append("a")),
                Do(lambda: order.append("b")),
                Do(lambda: order.append("c")),
            )
        )
        ctx.game.tick(0.016)
        ok &= _check(
            "US23-b1",
            order == ["a", "b", "c"],
            verbose,
            f"three Do() chain in one tick: {order}",
        )
        ok &= _check("US23-b2", s2._current_action is None, verbose, "done in 1 tick")

        # ── 23c: Do(cb) in middle of Sequence captures correct state
        s3 = ctx.sprite(0, 0)
        mid_val = [None]
        s3.do(
            Sequence(
                MoveTo((100, 0), speed=5000),
                Do(lambda: mid_val.__setitem__(0, s3.position)),
                MoveTo((200, 0), speed=5000),
            )
        )
        _tick_until_done(ctx.game, s3, max_ticks=200)
        ok &= _check("US23-c1", mid_val[0] is not None, verbose, "mid-Do fired")
        if mid_val[0] is not None:
            ok &= _check(
                "US23-c2",
                abs(mid_val[0][0] - 100) < 1,
                verbose,
                f"captured pos=(~100, _), got {mid_val[0]}",
            )

        findings.append(
            "Do(cb) fires at correct time, chains instantly, works mid-Sequence"
        )
    finally:
        ctx.close()

    if verbose:
        print(f"  US23: {'PASS' if ok else 'FAIL'}")
    return ok, "; ".join(findings)


# ═══════════════════════════════════════════════════════════════════════
# Parallel + infinite Repeat: tick() must not hang
# ═══════════════════════════════════════════════════════════════════════


def test_parallel_infinite_no_hang(verbose: bool) -> tuple[bool, str]:
    """Parallel with infinite Repeat: tick() returns promptly."""
    ctx = _GameCtx()
    ok = True
    findings: list[str] = []
    try:
        s = ctx.sprite()
        loop_count = [0]

        class LoopCounter(Action):
            def start(self, sprite: Sprite) -> None:
                pass

            def update(self, dt: float) -> bool:
                loop_count[0] += 1
                return True

        s.do(Parallel(Repeat(LoopCounter(), times=None), Delay(0.1)))
        t0 = time.monotonic()
        for _ in range(20):
            ctx.game.tick(0.016)
        elapsed = time.monotonic() - t0

        ok &= _check(
            "hang-time", elapsed < 5.0, verbose, f"20 ticks in {elapsed:.3f}s (< 5s)"
        )
        ticks = _tick_until_done(ctx.game, s, max_ticks=200)
        ok &= _check(
            "hang-done",
            s._current_action is None,
            verbose,
            f"done after {ticks} extra ticks",
        )
        count_snap = loop_count[0]
        ctx.game.tick(0.016)
        ok &= _check(
            "hang-stopped",
            loop_count[0] == count_snap,
            verbose,
            "infinite child stopped after Parallel completed",
        )

        findings.append(
            f"No hang; infinite iterated {count_snap}x; stopped on completion"
        )
    finally:
        ctx.close()

    if verbose:
        print(f"  NoHang: {'PASS' if ok else 'FAIL'}")
    return ok, "; ".join(findings)


# ═══════════════════════════════════════════════════════════════════════
# MoveTo NaN / extreme speed edge cases
# ═══════════════════════════════════════════════════════════════════════


def test_moveto_nan_edge(verbose: bool) -> tuple[bool, str]:
    """MoveTo with NaN/inf target rejected; extreme speeds; tiny dt."""
    ctx = _GameCtx()
    ok = True
    findings: list[str] = []
    try:
        # ── NaN target → ValueError
        try:
            MoveTo((float("nan"), 100), speed=100)
            ok &= _check("nan-target", False, verbose, "should raise")
        except ValueError:
            ok &= _check("nan-target", True, verbose, "NaN target raises ValueError")

        # ── inf target → ValueError
        try:
            MoveTo((float("inf"), 100), speed=100)
            ok &= _check("inf-target", False, verbose, "should raise")
        except ValueError:
            ok &= _check("inf-target", True, verbose, "inf target raises ValueError")

        # ── Very high speed: snap to target in 1 tick
        s = ctx.sprite(0, 0)
        s.do(MoveTo((1000, 1000), speed=1e9))
        ctx.game.tick(0.016)
        ok &= _check(
            "highspeed",
            _pos_finite(s) and abs(s.position[0] - 1000) < 1,
            verbose,
            f"speed=1e9 → pos={s.position}",
        )

        # ── Very slow speed: makes progress without NaN
        s2 = ctx.sprite(0, 0)
        s2.do(MoveTo((1, 0), speed=0.001))
        for _ in range(10):
            ctx.game.tick(0.016)
        ok &= _check(
            "slowspeed",
            _pos_finite(s2) and s2.position[0] > 0,
            verbose,
            f"speed=0.001 → pos={s2.position}",
        )
        s2.stop_actions()

        # ── Near-zero dt: no NaN
        s3 = ctx.sprite(0, 0)
        s3.do(MoveTo((100, 0), speed=100))
        for _ in range(10):
            ctx.game.tick(1e-10)
        ok &= _check(
            "tinydt", _pos_finite(s3), verbose, f"dt=1e-10 → pos={s3.position}"
        )
        s3.stop_actions()

        # ── Already at target: instant finish, no div-by-zero
        s4 = ctx.sprite(50, 50)
        s4.do(MoveTo((50, 50), speed=100))
        ctx.game.tick(0.016)
        ok &= _check(
            "at-target",
            s4._current_action is None and _pos_finite(s4),
            verbose,
            "already at target → instant finish, no crash",
        )

        findings.append(
            "NaN/inf targets rejected; extreme speeds safe; no NaN propagation"
        )
    finally:
        ctx.close()

    if verbose:
        print(f"  NaN/edge: {'PASS' if ok else 'FAIL'}")
    return ok, "; ".join(findings)


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

# Map: test label → (story IDs covered, test function)
TESTS: list[tuple[str, list[str], Any]] = [
    ("US6", ["US6"], test_us6),
    ("US7", ["US7"], test_us7),
    ("US8", ["US8"], test_us8),
    ("US9", ["US9"], test_us9),
    ("US22", ["US22"], test_us22),
    ("US23", ["US23"], test_us23),
    ("NoHang", [], test_parallel_infinite_no_hang),
    ("NaN", [], test_moveto_nan_edge),
]


def run_harness(verbose: bool = False) -> dict[str, tuple[bool, str]]:
    """Run all action stress tests. Returns {label: (passed, findings)}."""
    results: dict[str, tuple[bool, str]] = {}
    for label, _stories, test_fn in TESTS:
        try:
            passed, findings = test_fn(verbose)
            results[label] = (passed, findings)
        except Exception as e:
            results[label] = (False, f"EXCEPTION: {e}")
            if verbose:
                print(f"  {label}: EXCEPTION — {e}")
                import traceback

                traceback.print_exc()
    return results


def main() -> int:
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    results = run_harness(verbose=verbose)

    # ── Story-level summary ──
    story_status: dict[str, bool] = {}
    for label, stories, _fn in TESTS:
        if label in results:
            passed, _ = results[label]
            for sid in stories:
                story_status[sid] = passed

    passed_count = sum(1 for v in results.values() if v[0])
    total = len(results)

    print(f"\n{'=' * 60}")
    print(f"Action stress tester: {passed_count}/{total} scenarios passed")
    print(f"{'=' * 60}")

    # Per-scenario results
    for label, (ok, findings) in results.items():
        print(f"  {label:8s}: {'PASS' if ok else 'FAIL'} — {findings}")

    # Per-story summary
    print(f"\n{'─' * 60}")
    print("Story results:")
    for sid in ["US6", "US7", "US8", "US9", "US22", "US23"]:
        if sid in story_status:
            print(f"  {sid}: {'PASS' if story_status[sid] else 'FAIL'}")
        else:
            print(f"  {sid}: NOT TESTED")
    print(f"{'─' * 60}")

    return 0 if all(v[0] for v in results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
