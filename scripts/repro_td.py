#!/usr/bin/env python3
"""Reproduce the tower defense initial scene and save a screenshot.

This script loads the tower defense GameScene, renders one frame, and saves
the output to repro_td_final.png for visual inspection.

Run from project root:
    python scripts/repro_td.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

# Add tower defense example to path
TD_DIR = PROJECT_ROOT / "examples" / "tower_defense"
ASSET_DIR = TD_DIR / "assets"
sys.path.insert(0, str(TD_DIR))

# Ensure assets exist
if not ASSET_DIR.exists():
    print("Generating tower defense assets...")
    from examples.tower_defense.generate_assets import generate

    generate(ASSET_DIR)
    print()

# Import tower defense module
import main as td_main  # type: ignore[import-not-found]

from saga2d import Game, Theme
from saga2d.backends.pyglet_backend import PygletBackend


def render_scene() -> None:
    """Render the tower defense initial game scene and save screenshot."""

    # Create game with tower defense settings
    game = Game(
        "Tower Defense - Screenshot",
        resolution=(960, 540),
        fullscreen=False,
        backend="pyglet",
        asset_path=ASSET_DIR,
    )

    # Apply tower defense theme (Tailwind Slate palette)
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

    # Push the game scene
    game.push(td_main.GameScene())

    # Tick once to render initial state
    game.tick(dt=1.0 / 60.0)

    # Get backend and capture screenshot
    backend = game._backend
    if isinstance(backend, PygletBackend):
        # Render the frame
        backend.begin_frame()
        backend._batch.draw()

        # Capture the buffer
        import pyglet

        buffer = pyglet.image.get_buffer_manager().get_color_buffer()

        # Save screenshot
        output_path = PROJECT_ROOT / "repro_td_final.png"
        buffer.save(str(output_path))
        print(f"✓ Screenshot saved: {output_path}")

        # Also show dimensions
        print(f"  Resolution: {buffer.width}×{buffer.height}")
        print(f"  Map size: {td_main.MAP_WIDTH_PX}×{td_main.MAP_HEIGHT_PX} px")
        print(f"  Tile size: {td_main.TILE_SIZE}×{td_main.TILE_SIZE} px")
        print(f"  Grid: {td_main.MAP_COLS}×{td_main.MAP_ROWS} tiles")
    else:
        print(f"✗ Unexpected backend type: {type(backend)}")


if __name__ == "__main__":
    print("=== Tower Defense Screenshot Capture ===\n")
    render_scene()
    print("\nDone.")
