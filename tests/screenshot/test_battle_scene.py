"""Screenshot regression tests for the BattleScene from battle_demo.

Run from the project root::

    pytest tests/screenshot/test_battle_scene.py -v

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
# Import BattleScene from the battle demo example.
#
# ``examples/`` is not a Python package, so we add the example directory
# to sys.path temporarily and import the module by name.
# ---------------------------------------------------------------------------
_DEMO_DIR = Path(__file__).resolve().parents[2] / "examples" / "battle_vignette"


def _load_battle_demo():
    """Import and return (BattleScene, ATTACK_DAMAGE) from battle_demo.py."""
    added = False
    if str(_DEMO_DIR) not in sys.path:
        sys.path.insert(0, str(_DEMO_DIR))
        added = True
    try:
        from battle_demo import BattleScene  # type: ignore[import-not-found]
        return BattleScene
    finally:
        if added:
            sys.path.remove(str(_DEMO_DIR))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_battle_initial_formation() -> None:
    """Render the BattleScene in its initial state.

    Shows the earthy green ground plane, 3 warriors staggered on the left,
    and 3 skeletons staggered on the right.  A few ticks advance the idle
    breathing tweens so sprites are visibly present.  Resolution is the
    demo's native 1920x1080.
    """
    BattleScene = _load_battle_demo()

    def setup(game):
        game.push(BattleScene())

    # 5 ticks at 1/60 ≈ 0.083s — enough to render sprites on the ground
    # plane with idle breathing just starting.
    image = render_scene(setup, tick_count=5, resolution=(1920, 1080))
    assert_screenshot(image, "battle_initial_formation")


@pytest.mark.screenshot
def test_battle_victory() -> None:
    """All enemies killed — VICTORY text faded in over the battlefield.

    Sets up a BattleScene, then directly marks every enemy unit as dead
    and removes their sprites (simulating completed kill sequences).
    Calls ``_trigger_victory()`` to start the opacity fade-in tween,
    then ticks 90 frames (1.5 s) so the 1-second tween completes and
    the text reaches full opacity — but before the 3-second auto-pop
    fires.  The capture should show the ground plane, the surviving
    warriors, and a bright gold "VICTORY" label at centre-screen.
    """
    BattleScene = _load_battle_demo()

    def setup(game):
        scene = BattleScene()
        game.push(scene)

        # Tick once so the scene is fully initialised (sprites drawn, tweens
        # running) before we mutate state.
        game.tick(dt=1.0 / 60.0)

        # Kill all enemy units by removing their sprites and marking dead.
        for unit in scene.units:
            if unit.team == "enemy":
                unit.alive = False
                unit.hp = 0
                unit.sprite.remove()

        # Trigger victory directly — starts the opacity tween and 3 s timer.
        scene._trigger_victory()

    # 90 ticks × (1/60) = 1.5 s — the 1 s opacity tween is finished
    # (VICTORY text at full alpha) but the 3 s auto-pop has not fired.
    image = render_scene(setup, tick_count=90, resolution=(1920, 1080))
    assert_screenshot(image, "battle_victory")
