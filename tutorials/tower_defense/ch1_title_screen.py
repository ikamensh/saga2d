"""Chapter 1 — Title Screen
===========================

Your first EasyGame program!  This chapter creates a window with a
title screen scene.  You'll learn:

*   How to create a :class:`Game` and run it.
*   How to define a :class:`Scene` with lifecycle hooks.
*   How to build a UI with :class:`Panel`, :class:`Label`, and :class:`Button`.
*   How button callbacks work (``on_click``).
*   How to quit the game cleanly.

Run from the project root::

    python tutorials/tower_defense/ch1_title_screen.py

Or from the tutorial directory::

    cd tutorials/tower_defense
    python ch1_title_screen.py

The assets/ folder must exist (run ``generate_td_assets.py`` first if needed).
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — ensures ``import easygame`` works regardless of where you
# invoke this script from.  We climb two directories up from this file to
# reach the project root, then add that to sys.path.
# ---------------------------------------------------------------------------
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

# ---------------------------------------------------------------------------
# Auto-generate assets if the assets/ folder is missing.
# This calls the same generator from Chapter 0 (generate_td_assets.py) so
# you never have to remember to run it manually.
# ---------------------------------------------------------------------------
_asset_dir = Path(__file__).resolve().parent / "assets"
if not _asset_dir.exists():
    print("Assets not found — generating placeholder art...")
    from tutorials.tower_defense.generate_td_assets import generate

    generate(_asset_dir)
    print()

# ---------------------------------------------------------------------------
# EasyGame imports — everything comes from the top-level ``easygame`` package.
# ---------------------------------------------------------------------------
from easygame import (  # noqa: E402
    Anchor,        # Where a UI component sits within its parent
    AssetManager,  # Loads images/sounds from a base directory
    Button,        # Clickable button with hover/press states
    Game,          # Top-level object: owns the window, scene stack, and loop
    InputEvent,    # Unified input (keyboard/mouse) event
    Label,         # Static text display
    Layout,        # VERTICAL / HORIZONTAL / NONE — child arrangement
    Panel,         # Container with background and flow layout
    Scene,         # A self-contained game state (title, gameplay, pause…)
    Style,         # Per-component visual overrides (color, font, padding…)
    Theme,         # Global UI defaults (applied when Style fields are None)
)


# ======================================================================
# Constants
# ======================================================================

# Logical resolution — the coordinate space your game thinks in.
# EasyGame scales this to the actual window size automatically.
# 960×540 is a clean 16:9 ratio that works well for a small-window TD game.
SCREEN_W, SCREEN_H = 960, 540

# Colour palette (RGBA tuples, 0–255 per channel)
BG_COLOR = (25, 30, 40, 255)         # Dark blue-grey background
TITLE_COLOR = (255, 220, 80, 255)    # Gold — for the game title
SUBTITLE_COLOR = (180, 180, 190, 255)  # Muted grey — for the subtitle


# ======================================================================
# TitleScene
# ======================================================================

class TitleScene(Scene):
    """The title screen — shown when the game starts.

    EasyGame's Scene class has lifecycle hooks you can override:

    *   ``on_enter()``  — called when this scene becomes the active scene.
                          Set up sprites, UI, and state here.
    *   ``on_exit()``   — called when the scene is removed or covered.
                          Clean up resources here.
    *   ``draw()``      — called every frame for custom rendering.
    *   ``handle_input(event)`` — called for each input event.  Return
                          ``True`` to consume it, ``False`` to pass through.

    The UI system handles button clicks automatically, so we only need
    ``handle_input`` for keyboard shortcuts.
    """

    def on_enter(self) -> None:
        """Build the title-screen UI when this scene becomes active.

        ``self.game`` is available here — it was set by the scene stack
        just before calling ``on_enter()``.
        """
        # -----------------------------------------------------------------
        # 1. Create a solid-colour background that fills the screen.
        #
        #    We use the backend's low-level API to create a coloured image
        #    and place it behind everything.  This is the simplest way to
        #    set a background colour — no PNG file needed.
        # -----------------------------------------------------------------
        backend = self.game.backend
        bg_image = backend.create_solid_color_image(
            BG_COLOR[0], BG_COLOR[1], BG_COLOR[2], BG_COLOR[3],
            SCREEN_W, SCREEN_H,
        )
        from easygame import RenderLayer

        self._bg_sprite_id = backend.create_sprite(
            bg_image,
            RenderLayer.BACKGROUND.value * 100_000,
        )
        backend.update_sprite(self._bg_sprite_id, 0, 0)

        # -----------------------------------------------------------------
        # 2. Build the UI tree.
        #
        #    EasyGame's UI is a tree of Components.  Every Scene has a
        #    ``self.ui`` root that covers the full logical screen.  You add
        #    Panels, Labels, and Buttons as children.
        #
        #    Layout flow:
        #       _UIRoot (full screen)
        #         └── menu_panel (VERTICAL layout, anchored to CENTER)
        #               ├── title_label    ("Tower Defense")
        #               ├── subtitle_label ("A step-by-step tutorial")
        #               ├── play_button    ("Play")
        #               └── quit_button    ("Quit")
        # -----------------------------------------------------------------

        # --- Title label ---
        # Style overrides let you customise individual components without
        # changing the global Theme.  Here we make the title bigger and gold.
        title_label = Label(
            "Tower Defense",
            style=Style(
                font_size=48,
                text_color=TITLE_COLOR,
            ),
        )

        # --- Subtitle label ---
        subtitle_label = Label(
            "A step-by-step tutorial",
            style=Style(
                font_size=18,
                text_color=SUBTITLE_COLOR,
            ),
        )

        # --- Play button ---
        # The ``on_click`` callback fires when the user clicks the button.
        # In later chapters this will transition to the gameplay scene.
        play_button = Button(
            "Play",
            on_click=self._on_play_clicked,
        )

        # --- Quit button ---
        quit_button = Button(
            "Quit",
            on_click=self._on_quit_clicked,
        )

        # --- Menu panel ---
        # A Panel with ``Layout.VERTICAL`` stacks its children top-to-bottom
        # with ``spacing`` pixels between each.  ``Anchor.CENTER`` places
        # the panel in the middle of its parent (the full screen).
        #
        # The panel auto-sizes to fit its children (content-fit) because
        # we don't set explicit width/height.
        menu_panel = Panel(
            layout=Layout.VERTICAL,
            spacing=20,
            anchor=Anchor.CENTER,
            style=Style(
                background_color=(30, 35, 50, 220),
                padding=40,
            ),
            children=[
                title_label,
                subtitle_label,
                play_button,
                quit_button,
            ],
        )

        # Add the panel to the scene's UI root.  From here the framework
        # handles layout, drawing, and input dispatch automatically.
        self.ui.add(menu_panel)

    # ------------------------------------------------------------------
    # Button callbacks
    # ------------------------------------------------------------------

    def _on_play_clicked(self) -> None:
        """Called when the Play button is clicked.

        In Chapter 2 we'll replace this with:
            self.game.replace(GameplayScene())
        For now, just print a message so we know it works.
        """
        print("Starting game...")  # placeholder — wired up in Chapter 2

    def _on_quit_clicked(self) -> None:
        """Called when the Quit button is clicked.

        ``game.quit()`` sets ``game.running = False``, which exits the
        main loop cleanly.  The backend window closes and the process ends.
        """
        self.game.quit()

    # ------------------------------------------------------------------
    # Keyboard input
    # ------------------------------------------------------------------

    def handle_input(self, event: InputEvent) -> bool:
        """Handle keyboard shortcuts.

        EasyGame translates raw key presses into semantic *actions*:
        *   ``"confirm"`` — Enter key (start the game)
        *   ``"cancel"``  — Escape key (quit)

        The UI system already handles mouse clicks on buttons, so this
        method only adds keyboard equivalents for convenience.
        """
        if event.action == "confirm":
            self._on_play_clicked()
            return True  # consumed — don't pass to other handlers

        if event.action == "cancel":
            self._on_quit_clicked()
            return True

        return False  # not consumed — let other handlers see it

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def on_exit(self) -> None:
        """Remove the background when leaving this scene.

        The UI tree is cleaned up automatically by the framework, but
        backend-level resources (like our manually created background
        sprite) need explicit removal.
        """
        if self._bg_sprite_id is not None:
            self.game.backend.remove_sprite(self._bg_sprite_id)
            self._bg_sprite_id = None


# ======================================================================
# Main — entry point
# ======================================================================

def main() -> None:
    """Create the Game and run the title screen.

    This is the minimal EasyGame setup:

    1. Create a :class:`Game` with a title and resolution.
    2. Point the :class:`AssetManager` at your assets/ directory.
    3. (Optional) Customise the :class:`Theme` for your game's look.
    4. Call ``game.run(StartScene())`` — this enters the main loop.
    """

    # --- Step 1: Create the Game -----------------------------------------
    # ``fullscreen=False`` opens a resizable window instead of going
    # fullscreen — much more convenient during development.
    # ``backend="pyglet"`` uses the pyglet GPU-accelerated backend.
    game = Game(
        "Tower Defense — Chapter 1",
        resolution=(SCREEN_W, SCREEN_H),
        fullscreen=False,
        backend="pyglet",
    )

    # --- Step 2: Point assets at our local directory ---------------------
    # AssetManager resolves image names relative to this base path.
    # For example, ``"sprites/tower_basic"`` loads
    # ``tutorials/tower_defense/assets/images/sprites/tower_basic.png``.
    #
    # We don't load any images in this chapter (the UI uses backend
    # drawing primitives), but setting this up now means Chapter 2 can
    # load tower/enemy sprites without extra setup.
    game.assets = AssetManager(
        game.backend,
        base_path=_asset_dir,
    )

    # --- Step 3: Customise the Theme (optional) --------------------------
    # The Theme controls default colours, fonts, and sizes for all UI
    # components.  Components inherit from the theme unless overridden
    # by an explicit Style.
    #
    # Here we tweak the button and panel colours to match our dark
    # blue-grey aesthetic.
    game.theme = Theme(
        font="serif",
        font_size=24,
        text_color=(220, 220, 230, 255),
        # Panel
        panel_background_color=(30, 35, 50, 220),
        panel_padding=16,
        # Button
        button_background_color=(50, 55, 80, 255),
        button_hover_color=(70, 80, 120, 255),
        button_press_color=(35, 40, 60, 255),
        button_text_color=(220, 220, 230, 255),
        button_padding=14,
        button_font_size=26,
        button_min_width=220,
    )

    # --- Step 4: Run! ----------------------------------------------------
    # ``game.run()`` pushes the TitleScene onto the scene stack, enters
    # the main loop, and blocks until ``game.quit()`` is called.
    # After the loop exits it tears down the backend (closes the window).
    game.run(TitleScene())


if __name__ == "__main__":
    main()
