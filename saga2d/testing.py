"""Offscreen rendering for visual verification.

::

    from saga2d.testing import render_scene

    def setup(game):
        game.push(MyScene())

    image = render_scene(setup, resolution=(800, 600), tick_count=2)
    image.save("out.png")   # then LOOK at it

The window is created hidden; the returned PIL image is the framebuffer
at physical resolution (2× the logical size on HiDPI displays).
"""

from __future__ import annotations

import collections
import statistics
import time
from typing import TYPE_CHECKING, Any, Callable

from saga2d.game import Game

if TYPE_CHECKING:
    from PIL import Image


def render_scene(
    setup: Callable[[Game], None],
    *,
    resolution: tuple[int, int] = (800, 600),
    tick_count: int = 1,
    dt: float = 1 / 60,
) -> "Image.Image":
    game = Game("Screenshot", resolution=resolution, backend="pyglet", visible=False)
    try:
        setup(game)
        for _ in range(tick_count):
            game.tick(dt=dt)
        return game.backend.capture_frame()
    finally:
        game._teardown()
        game.backend.quit()



class FrameTimer:
    """Wall-clock frame times and the share each wrapped phase takes.

    ::

        timer = FrameTimer()
        timer.wrap(scene.world, "step", "world.step")
        timer.wrap(game.backend, "end_frame", "backend.end_frame")
        for _ in range(600):
            timer.frame(lambda: game.tick(1 / 60))
        print(timer.report())

    Wrapping replaces the method on that object with a timed version; the
    label defaults to the method name.  Time frames this way rather than under
    a profiler or ``tracemalloc``, which slow tight Python loops several times
    over and shift the blame.
    """

    def __init__(self) -> None:
        self.frames: list[float] = []  # milliseconds per frame
        self.seconds: dict[str, float] = collections.defaultdict(float)
        self.calls: collections.Counter[str] = collections.Counter()

    def wrap(self, obj: Any, name: str, label: str | None = None) -> None:
        fn = getattr(obj, name)
        label = label or name

        def timed(*args: Any, **kwargs: Any) -> Any:
            t0 = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                self.seconds[label] += time.perf_counter() - t0
                self.calls[label] += 1

        setattr(obj, name, timed)

    def frame(self, fn: Callable[[], Any]) -> float:
        """Run one frame through *fn* and record its wall-clock time; returns it in ms."""
        t0 = time.perf_counter()
        fn()
        ms = (time.perf_counter() - t0) * 1000
        self.frames.append(ms)
        return ms

    def percentile(self, p: float) -> float:
        if not self.frames:
            raise ValueError("no frames timed yet")
        ordered = sorted(self.frames)
        return ordered[min(len(ordered) - 1, int(p / 100 * len(ordered)))]

    def report(self) -> str:
        """Frame percentiles, then every phase by share of the timed frames."""
        total = sum(self.frames) / 1000
        lines = [f"{len(self.frames)} frames: p50 {statistics.median(self.frames):.1f} ms, p95 {self.percentile(95):.1f} ms, max {max(self.frames):.1f} ms"]
        for label, seconds in sorted(self.seconds.items(), key=lambda kv: -kv[1]):
            calls = self.calls[label]
            lines.append(f"  {label:20s} {seconds * 1000:8.0f} ms  {100 * seconds / total if total else 0:5.1f}%  {calls} calls, {seconds * 1000 / max(1, calls):.2f} ms each")
        return "\n".join(lines)
