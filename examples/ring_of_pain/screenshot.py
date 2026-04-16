"""Render the Ring of Pain sketch to a PNG for visual inspection."""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from tests.screenshot.harness import render_scene  # noqa: E402

from examples.ring_of_pain.ring_of_pain import RingOfPainScene  # noqa: E402


def capture(output: Path, resolution: tuple[int, int] = (800, 600)) -> None:
    def setup(game) -> None:
        game.run_tick = False  # not required; placeholder for reader
        game._scene_stack.push(RingOfPainScene(ring_size=8, seed=7))

    image = render_scene(setup, tick_count=2, resolution=resolution)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    print(f"Wrote {output} ({image.size[0]}x{image.size[1]})")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/ring_of_pain.png")
    capture(out)
