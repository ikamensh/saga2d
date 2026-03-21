#!/usr/bin/env python3
"""Capture baseline screenshots for Tower Defense example.

This script renders three key states of the Tower Defense game and saves
them as PNG files in the td_baseline/ directory for visual comparison.

Run from the project root::

    python scripts/capture_td_baseline.py

Requires:
    - pyglet (GPU context)
    - Pre-generated assets (runs generate_assets.py if missing)

Outputs:
    - td_baseline/td_title.png          -- Title screen
    - td_baseline/td_game_initial.png   -- Initial game state (no enemies)
    - td_baseline/td_game_action.png    -- Game with enemies and combat
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup -- add project root and tower defense example to sys.path
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
_TD_DIR = _PROJECT_ROOT / "examples" / "tower_defense"
_ASSET_DIR = _TD_DIR / "assets"
_OUTPUT_DIR = _SCRIPT_DIR.parent / "td_baseline"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

if str(_TD_DIR) not in sys.path:
    sys.path.insert(0, str(_TD_DIR))

# ---------------------------------------------------------------------------
# Ensure assets exist
# ---------------------------------------------------------------------------
if not _ASSET_DIR.exists() or not (_ASSET_DIR / "images").exists():
    print("Assets not found -- generating placeholder art...")
    sys.path.insert(0, str(_TD_DIR))
    from generate_assets import generate  # type: ignore[import-not-found]

    generate(_ASSET_DIR)
    print()

# ---------------------------------------------------------------------------
# Import tower defense module and harness
# ---------------------------------------------------------------------------
import main as td_main  # type: ignore[import-not-found]
from tests.screenshot.harness import render_scene

from saga2d import Theme

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
_RESOLUTION = (960, 540)


def _configure_game(game) -> None:
    """Set asset path and theme to match tower defense main()."""
    # Point the lazy AssetManager at the example's assets directory.
    game._asset_path = _ASSET_DIR

    # Apply the same theme the game uses in main().
    game.theme = Theme(
        font="serif",
        font_size=24,
        text_color=(226, 232, 240, 255),  # Slate 200
        panel_background_color=(30, 41, 59, 220),  # Slate 800
        panel_padding=16,
        button_background_color=(51, 65, 85, 255),  # Slate 700
        button_hover_color=(71, 85, 105, 255),  # Slate 600
        button_press_color=(30, 41, 59, 255),  # Slate 800
        button_text_color=(226, 232, 240, 255),  # Slate 200
        button_padding=14,
        button_font_size=26,
        button_min_width=220,
    )


# ---------------------------------------------------------------------------
# Capture functions
# ---------------------------------------------------------------------------


def capture_title() -> None:
    """Capture the title screen."""
    print("Capturing td_title.png...")

    def setup(game):
        _configure_game(game)
        game.push(td_main.TitleScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)

    # Handle HiDPI/retina scaling -- resize to requested resolution if needed
    if image.size != _RESOLUTION:
        from PIL import Image

        image = image.resize(_RESOLUTION, Image.Resampling.LANCZOS)

    output_path = _OUTPUT_DIR / "td_title.png"
    image.save(output_path)
    print(f"  Saved {output_path} ({image.size[0]}×{image.size[1]})")


def capture_game_initial() -> None:
    """Capture the initial game state (map, HUD, no enemies)."""
    print("Capturing td_game_initial.png...")

    def setup(game):
        _configure_game(game)
        game.push(td_main.GameScene())

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)

    # Handle HiDPI/retina scaling -- resize to requested resolution if needed
    if image.size != _RESOLUTION:
        from PIL import Image

        image = image.resize(_RESOLUTION, Image.Resampling.LANCZOS)

    output_path = _OUTPUT_DIR / "td_game_initial.png"
    image.save(output_path)
    print(f"  Saved {output_path} ({image.size[0]}×{image.size[1]})")


def capture_game_action() -> None:
    """Capture gameplay with enemies and a tower."""
    print("Capturing td_game_action.png...")

    def setup(game):
        _configure_game(game)
        scene = td_main.GameScene()
        game.push(scene)

        # Tick once to initialize scene (tile map, slots, UI).
        game.tick(dt=1.0 / 60.0)

        # Place a Basic tower at the first slot (4, 4).
        scene._placing_tower_def = td_main.TOWER_DEFS[0]
        slot_col, slot_row = td_main.TOWER_SLOTS[0]
        world_x = slot_col * td_main.TILE_SIZE + td_main.TILE_SIZE / 2
        world_y = slot_row * td_main.TILE_SIZE + td_main.TILE_SIZE / 2
        placed = scene._try_place_tower(world_x, world_y)
        assert placed, "Tower placement should succeed"

        # Start wave 1 manually (bypasses 2-second timer).
        scene._start_next_wave()

        # Spawn 3 enemies with spacing so they're spread along the path.
        for i in range(3):
            scene._spawn_enemy()
            # Tick to let each enemy move down the path before spawning next.
            # 1.5 seconds × 80 px/s = 120 pixels of travel per enemy.
            game.tick(dt=1.5)

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)

    # Handle HiDPI/retina scaling -- resize to requested resolution if needed
    if image.size != _RESOLUTION:
        from PIL import Image

        image = image.resize(_RESOLUTION, Image.Resampling.LANCZOS)

    output_path = _OUTPUT_DIR / "td_game_action.png"
    image.save(output_path)
    print(f"  Saved {output_path} ({image.size[0]}×{image.size[1]})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Capture all three baseline screenshots."""
    print("=== Tower Defense Baseline Screenshot Capture ===\n")

    # Create output directory.
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Capture all three states.
    capture_title()
    capture_game_initial()
    capture_game_action()

    print(f"\n{'=' * 50}")
    print(f"Saved 3 screenshots to {_OUTPUT_DIR}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
