"""Screenshot regression tests for Stage 13 — convenience screens, HUD, and menus.

Run from the project root::

    pytest tests/screenshot/test_stage13_screenshots.py -v

Requires pyglet (GPU context).  Excluded from the normal ``pytest tests/``
run by ``collect_ignore`` in ``tests/conftest.py``.

Tests cover:

1. **MessageScreen** — dark overlay with centred text and "Press any key…" hint.
2. **ChoiceScreen** — prompt label with 3 choice buttons.
3. **ConfirmDialog** — question text with Yes / No buttons.
4. **SaveLoadScreen** — slot list in load mode, some slots filled.
5. **HUD bar** — persistent HUD label + progress bar over a game scene.
6. **Menu scene** — full menu à la ``desired_examples/menu_desired.py``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from easygame import Game, Scene
from easygame.save import SaveManager
from easygame.ui import (
    Anchor,
    Button,
    Label,
    Layout,
    Panel,
    ProgressBar,
    Style,
)
from easygame.ui.screens import (
    ChoiceScreen,
    ConfirmDialog,
    MessageScreen,
    SaveLoadScreen,
)

from tests.screenshot.harness import assert_screenshot, render_scene

_RESOLUTION = (480, 360)


# ---------------------------------------------------------------------------
# 1. MessageScreen — dark overlay with centred text
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_message_screen() -> None:
    """MessageScreen overlay on top of a simple base scene.

    Expected: a semi-transparent dark panel centred on screen containing
    the message text in large white font and a "Press any key…" hint
    below in smaller grey text.  The base scene's label should be
    partially visible through the overlay.
    """

    class BaseScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "Game World",
                anchor=Anchor.TOP,
                margin=20,
                style=Style(font_size=20),
            ))

    def setup(game: Game) -> None:
        game.push(BaseScene())
        game.push(MessageScreen("You found a legendary sword!"))

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "stage13_message_screen")


# ---------------------------------------------------------------------------
# 2. ChoiceScreen — prompt with 3 choices
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_choice_screen() -> None:
    """ChoiceScreen overlay with a prompt and 3 choice buttons.

    Expected: a semi-transparent dark panel centred on screen with
    the prompt text at the top and 3 vertically stacked buttons
    ("Warrior", "Mage", "Rogue") below it.
    """

    class BaseScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "Character Creation",
                anchor=Anchor.TOP,
                margin=20,
                style=Style(font_size=20),
            ))

    def setup(game: Game) -> None:
        game.push(BaseScene())
        game.push(ChoiceScreen(
            "Choose your class:",
            ["Warrior", "Mage", "Rogue"],
        ))

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "stage13_choice_screen")


# ---------------------------------------------------------------------------
# 3. ConfirmDialog — question with Yes / No
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_confirm_dialog() -> None:
    """ConfirmDialog overlay with Yes and No buttons.

    Expected: a semi-transparent dark panel centred on screen with
    the question text and a horizontal row of Yes / No buttons below.
    """

    class BaseScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "Inventory",
                anchor=Anchor.TOP,
                margin=20,
                style=Style(font_size=20),
            ))

    def setup(game: Game) -> None:
        game.push(BaseScene())
        game.push(ConfirmDialog("Overwrite existing save?"))

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "stage13_confirm_dialog")


# ---------------------------------------------------------------------------
# 4. SaveLoadScreen — slot list in load mode
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_save_load_screen(tmp_path: Path) -> None:
    """SaveLoadScreen in load mode with a mix of filled and empty slots.

    Expected: a centred dark panel titled "Load Game" with slot buttons
    listing timestamps for filled slots and "Empty" for unfilled ones,
    plus a Back button at the bottom.
    """
    save_dir = tmp_path / "saves"
    mgr = SaveManager(save_dir)
    # Pre-populate some slots with save data.
    mgr.save(1, {"hero": "Arthas", "level": 10}, "CampaignScene")
    mgr.save(3, {"hero": "Jaina", "level": 15}, "BattleScene")

    class BaseScene(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label(
                "Main Menu",
                anchor=Anchor.TOP,
                margin=20,
                style=Style(font_size=20),
            ))

    def setup(game: Game) -> None:
        game.push(BaseScene())
        game.push(SaveLoadScreen(
            "load",
            save_manager=mgr,
            slot_count=5,
        ))

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "stage13_save_load_screen")


# ---------------------------------------------------------------------------
# 5. HUD bar — persistent label + progress bar over a game scene
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_hud_bar() -> None:
    """Game scene with a HUD containing a gold label and a health bar.

    Expected: the base scene renders normally with its own UI; the HUD
    layer renders a label ("Gold: 500") at the top-right and a health
    progress bar at the top-left, both above the scene content.
    """

    class GameScene(Scene):
        """Simple base scene representing an in-game view."""
        show_hud = True

        def on_enter(self) -> None:
            # Something in the scene's own UI.
            self.ui.add(Label(
                "Explore the Dungeon",
                anchor=Anchor.CENTER,
                style=Style(font_size=22, text_color=(180, 180, 180, 255)),
            ))

    def setup(game: Game) -> None:
        game.push(GameScene())

        # Add HUD elements.
        # Top-left: health bar.
        hp_panel = Panel(
            anchor=Anchor.TOP_LEFT,
            margin=10,
            layout=Layout.HORIZONTAL,
            spacing=6,
        )
        hp_panel.add(Label(
            "HP",
            style=Style(font_size=16, text_color=(255, 80, 80, 255)),
        ))
        hp_panel.add(ProgressBar(
            value=72,
            max_value=100,
            width=120,
            height=18,
            bar_color=(200, 40, 40, 255),
            bg_color=(60, 20, 20, 200),
        ))
        game.hud.add(hp_panel)

        # Top-right: gold counter.
        game.hud.add(Label(
            "Gold: 500",
            anchor=Anchor.TOP_RIGHT,
            margin=10,
            style=Style(font_size=16, text_color=(255, 215, 0, 255)),
        ))

    image = render_scene(setup, tick_count=1, resolution=_RESOLUTION)
    assert_screenshot(image, "stage13_hud_bar")


# ---------------------------------------------------------------------------
# 6. Menu scene — full menu matching desired_examples/menu_desired.py
# ---------------------------------------------------------------------------

@pytest.mark.screenshot
def test_menu_scene() -> None:
    """Full main menu scene inspired by desired_examples/menu_desired.py.

    Expected: a centred vertical panel with a large title label
    ("Chronicles of the Realm") and four stacked buttons
    (New Game, Load Game, Settings, Quit).  This demonstrates the
    framework's ability to render a classic RPG main menu with
    minimal code.
    """

    class MainMenu(Scene):
        show_hud = False

        def on_enter(self) -> None:
            panel = Panel(
                anchor=Anchor.CENTER,
                layout=Layout.VERTICAL,
                spacing=20,
                style=Style(
                    background_color=(20, 20, 35, 220),
                    padding=40,
                ),
            )
            panel.add(Label(
                "Chronicles of the Realm",
                style=Style(
                    font_size=36,
                    text_color=(220, 200, 140, 255),
                ),
            ))
            panel.add(Button("New Game", style=Style(font_size=20, padding=10)))
            panel.add(Button("Load Game", style=Style(font_size=20, padding=10)))
            panel.add(Button("Settings", style=Style(font_size=20, padding=10)))
            panel.add(Button("Quit", style=Style(font_size=20, padding=10)))
            self.ui.add(panel)

    def setup(game: Game) -> None:
        game.push(MainMenu())

    image = render_scene(setup, tick_count=1, resolution=(640, 480))
    assert_screenshot(image, "stage13_menu_scene")
