"""Screenshot regression test for the TitleScene from battle_demo.

Run from the project root::

    pytest tests/screenshot/test_title_scene.py -v

Requires pyglet (GPU context) and pre-generated assets
(``python generate_assets.py``).  Excluded from the normal ``pytest tests/``
run by ``collect_ignore`` in ``tests/conftest.py``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.screenshot.harness import assert_screenshot, render_scene

# ---------------------------------------------------------------------------
# Import TitleScene from the battle demo example.
#
# ``examples/`` is not a Python package, so we add the example directory
# to sys.path temporarily and import the module by name.
# ---------------------------------------------------------------------------
_DEMO_DIR = Path(__file__).resolve().parents[2] / "examples" / "battle_vignette"


def _load_title_scene_class():
    """Import and return the TitleScene class from battle_demo.py."""
    added = False
    if str(_DEMO_DIR) not in sys.path:
        sys.path.insert(0, str(_DEMO_DIR))
        added = True
    try:
        from battle_demo import TitleScene  # type: ignore[import-not-found]
        return TitleScene
    finally:
        if added:
            sys.path.remove(str(_DEMO_DIR))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_title_scene() -> None:
    """Push TitleScene, tick a few frames so tweens start, capture.

    TitleScene creates:
    - A dark-slate background (solid colour, full screen)
    - 2 warrior sprites with walk animation + y-axis bobbing tween
    - 2 skeleton sprites with walk animation + opacity pulse tween
    - Title text "BATTLE VIGNETTE" and instruction text (drawn each frame)

    10 ticks at 1/60 ≈ 0.167s — enough for animations to advance a couple
    of frames and tweens to begin moving sprites.  The resolution matches
    the demo's native 1920×1080 so sprites land at their intended positions.
    """
    TitleScene = _load_title_scene_class()

    def setup(game):
        game.push(TitleScene())

    image = render_scene(setup, tick_count=10, resolution=(1920, 1080))
    assert_screenshot(image, "title_scene")
