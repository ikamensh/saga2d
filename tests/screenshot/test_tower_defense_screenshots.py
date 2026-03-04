"""Screenshot regression tests for the Tower Defense example.

Run from the project root::

    pytest tests/screenshot/test_tower_defense_screenshots.py -v

Requires pyglet (GPU context) and pre-generated assets
(``python examples/tower_defense/generate_assets.py``).  Excluded from
the normal ``pytest tests/`` run by ``collect_ignore`` in
``tests/conftest.py``.

Each test imports TitleScene / GameScene from the example, configures
assets and theme to match the game's ``main()``, then renders via
``render_scene()`` and compares against golden PNGs.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.screenshot.harness import assert_screenshot, render_scene

# ---------------------------------------------------------------------------
# Import helpers from the tower defense example.
#
# ``examples/`` is not a Python package, so we add the example directory
# to sys.path temporarily and import by module name.
# ---------------------------------------------------------------------------
_DEMO_DIR = Path(__file__).resolve().parents[2] / "examples" / "tower_defense"
_ASSET_DIR = _DEMO_DIR / "assets"

_RESOLUTION = (960, 540)


def _load_td_module():
    """Import and return the tower defense ``main`` module."""
    added = False
    if str(_DEMO_DIR) not in sys.path:
        sys.path.insert(0, str(_DEMO_DIR))
        added = True
    try:
        import main as td_main  # type: ignore[import-not-found]

        return td_main
    finally:
        if added:
            sys.path.remove(str(_DEMO_DIR))


def _configure_game(game) -> None:
    """Set asset path and theme to match the tower defense ``main()``."""
    from saga2d import Theme

    # Point the lazy AssetManager at the example's assets directory.
    game._asset_path = _ASSET_DIR

    # Apply the same theme the game uses in main().
    game.theme = Theme(
        font="serif",
        font_size=24,
        text_color=(220, 220, 230, 255),
        panel_background_color=(30, 35, 50, 220),
        panel_padding=16,
        button_background_color=(50, 55, 80, 255),
        button_hover_color=(70, 80, 120, 255),
        button_press_color=(35, 40, 60, 255),
        button_text_color=(220, 220, 230, 255),
        button_padding=14,
        button_font_size=26,
        button_min_width=220,
    )


# ---------------------------------------------------------------------------
# 1. Title screen
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_td_title() -> None:
    """Title screen: centered panel with "Tower Defense" title, subtitle,
    Play and Quit buttons on a dark background.

    Uses the game's custom serif theme.  The panel should be centred on
    the 960×540 screen with the dark blue background colour visible.
    """
    td = _load_td_module()

    def setup(game):
        _configure_game(game)
        game.push(td.TitleScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "td_title")


# ---------------------------------------------------------------------------
# 2. Game scene — initial map (no towers, no enemies yet)
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_td_game_initial() -> None:
    """Game scene in its initial state: tile map with grass and path,
    13 tower slot markers, HUD showing Wave 0/5 · Gold 200 · Lives 20,
    and the build menu on the right.

    The first wave hasn't started yet (2-second delay), so no enemies
    are present.  Camera is centred on the map.
    """
    td = _load_td_module()

    def setup(game):
        _configure_game(game)
        game.push(td.GameScene())

    # 1 tick renders the initial frame — map, slots, HUD, and menu
    # are all visible.  No enemies because the 2 s wave-start delay
    # hasn't elapsed.
    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "td_game_initial")


# ---------------------------------------------------------------------------
# 3. Game scene — tower placed
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_td_game_tower_placed() -> None:
    """Game scene with one Basic tower placed at the first slot (4, 4).

    After initialisation, the test enters placement mode for the Basic
    tower, then calls ``_try_place_tower()`` at the slot's pixel centre.
    The slot marker should be replaced by a tower sprite, gold should
    decrease from 200 to 150, and the HUD should reflect the change.
    """
    td = _load_td_module()

    def setup(game):
        _configure_game(game)
        scene = td.GameScene()
        game.push(scene)

        # Tick once so the scene is fully initialised (tile map built,
        # slots placed, UI wired up).
        game.tick(dt=1.0 / 60.0)

        # Enter placement mode for the Basic tower (cost 50).
        scene._placing_tower_def = td.TOWER_DEFS[0]

        # Place at the first tower slot (col=4, row=4).
        # _try_place_tower expects world-pixel coordinates.
        slot_col, slot_row = td.TOWER_SLOTS[0]
        world_x = slot_col * td.TILE_SIZE + td.TILE_SIZE / 2
        world_y = slot_row * td.TILE_SIZE + td.TILE_SIZE / 2
        placed = scene._try_place_tower(world_x, world_y)
        assert placed, "Tower placement at slot (4, 4) should succeed"

    # One more tick to render the updated state (tower sprite, updated HUD).
    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "td_game_tower_placed")
