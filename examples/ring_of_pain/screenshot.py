"""Render the Ring of Pain sketch to a PNG and (optionally) run the
dual-model cross-check + consensus synthesis in one shot.

Usage::

    python examples/ring_of_pain/screenshot.py [out.png] [--no-review]

By default the script captures the frame *and* invokes cross_check +
synthesise_consensus so the operator sees the synthesis alongside the
PNG path. ``--no-review`` skips the LLM calls (fast when iterating on
geometry/typography before wanting another round of feedback).
"""

from __future__ import annotations

import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from tests.screenshot.harness import render_scene  # noqa: E402

from examples.ring_of_pain.ai_review import (  # noqa: E402
    cross_check,
    synthesise_consensus,
)
from examples.ring_of_pain.ring_of_pain import (  # noqa: E402
    RingOfPainScene,
    build_theme,
)


def capture(output: Path, resolution: tuple[int, int] = (800, 600)) -> None:
    def setup(game) -> None:
        # Apply the production theme so the screenshot matches what the
        # player actually sees. Uses the Game(theme=…) path via setter.
        game.theme = build_theme()
        game._scene_stack.push(RingOfPainScene(ring_size=8, seed=7))

    image = render_scene(setup, tick_count=2, resolution=resolution)
    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)
    print(f"Wrote {output} ({image.size[0]}x{image.size[1]})")


def review(output: Path) -> None:
    """Invoke the cross-check + synthesis pipeline on *output*."""
    critiques = cross_check(output)
    for provider, critique in critiques:
        print(f"\n{'=' * 60}\n=== Provider: {provider} ===\n{'=' * 60}")
        print(critique)
    synthesis = synthesise_consensus(critiques)
    if synthesis:
        print(f"\n{'=' * 60}\n=== Synthesis ===\n{'=' * 60}")
        print(synthesis)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--no-review"]
    skip_review = "--no-review" in sys.argv[1:]
    out = Path(args[0]) if args else Path("/tmp/ring_of_pain.png")
    capture(out)
    if not skip_review:
        try:
            review(out)
        except Exception as e:  # noqa: BLE001
            print(f"\n[review skipped — {type(e).__name__}: {e}]", file=sys.stderr)
