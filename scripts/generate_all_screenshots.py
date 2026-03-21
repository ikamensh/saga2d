"""Generate ALL screenshot golden images using MockBackend + PIL.

This script generates golden images for:
1. Widget screenshots (8 tests)
2. Stage13 screenshots (6 tests) - includes ProgressBar usage
3. UI screenshots (if needed in future)

All use the actual Saga2D code with MockBackend to record draw calls,
then replay them onto PIL Images.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to Python path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from saga2d import Game, Scene
from saga2d.save import SaveManager
from saga2d.ui import (
    Anchor,
    Button,
    DataTable,
    Grid,
    Label,
    Layout,
    List,
    Panel,
    ProgressBar,
    Style,
    TabGroup,
    TextBox,
    Tooltip,
)
from saga2d.ui.screens import (
    ChoiceScreen,
    ConfirmDialog,
    MessageScreen,
    SaveLoadScreen,
)

from mock_to_pil_renderer import MockToPILRenderer

# Output directory
GOLDEN_DIR = _PROJECT_ROOT / "tests" / "screenshot" / "golden"
GOLDEN_DIR.mkdir(parents=True, exist_ok=True)

# Resolution for screenshots
_RESOLUTION = (480, 360)


def render_widget_to_image(setup_fn, resolution=_RESOLUTION):
    """Render a widget scene using MockBackend and return PIL Image."""
    game = Game(
        "Screenshot Test",
        resolution=resolution,
        backend="mock",
    )

    setup_fn(game)
    game.tick(dt=1.0 / 60.0)

    backend = game._backend
    renderer = MockToPILRenderer(resolution[0], resolution[1])
    image = renderer.render_all(
        backend.rects, backend.circles, backend.texts, backend.images
    )

    game._teardown()
    return image


# =============================================================================
# Widget Screenshots (from test_widget_screenshots.py)
# =============================================================================


def generate_widget_screenshots():
    """Generate all 8 widget golden images."""
    print("\n" + "=" * 60)
    print("Generating Widget Screenshots")
    print("=" * 60)

    # 1. ProgressBar
    def test_progress_bar():
        class BarScene(Scene):
            def on_enter(self):
                panel = Panel(anchor=Anchor.CENTER, layout=Layout.VERTICAL, spacing=8)
                panel.add(Label("Health", style=Style(font_size=20)))
                panel.add(ProgressBar(value=75, max_value=100, width=300, height=28))
                self.ui.add(panel)

        def setup(game):
            game.push(BarScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "widget_progress_bar.png")
        print("✓ widget_progress_bar.png")

    # 2. TextBox
    def test_textbox():
        class TextScene(Scene):
            def on_enter(self):
                panel = Panel(
                    anchor=Anchor.CENTER,
                    layout=Layout.VERTICAL,
                    spacing=6,
                    style=Style(padding=12),
                )
                panel.add(Label("Journal Entry", style=Style(font_size=22)))
                panel.add(
                    TextBox(
                        "The ancient fortress loomed ahead, its crumbling towers "
                        "silhouetted against the crimson sky. Our party pressed "
                        "forward through the overgrown courtyard, weapons drawn.",
                        width=350,
                        style=Style(font_size=16),
                    )
                )
                self.ui.add(panel)

        def setup(game):
            game.push(TextScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "widget_textbox_instant.png")
        print("✓ widget_textbox_instant.png")

    # 3. List
    def test_list():
        class ListScene(Scene):
            def on_enter(self):
                panel = Panel(anchor=Anchor.CENTER, layout=Layout.VERTICAL, spacing=8)
                panel.add(Label("Save Files", style=Style(font_size=20)))
                lst = List(
                    [
                        "Slot 1 - Castle",
                        "Slot 2 - Forest",
                        "Slot 3 - Dungeon",
                        "Slot 4 - Village",
                        "Slot 5 - Empty",
                    ],
                    width=280,
                    item_height=28,
                )
                lst.selected_index = 2
                panel.add(lst)
                self.ui.add(panel)

        def setup(game):
            game.push(ListScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "widget_list_with_selection.png")
        print("✓ widget_list_with_selection.png")

    # 4. Grid
    def test_grid():
        class GridScene(Scene):
            def on_enter(self):
                panel = Panel(anchor=Anchor.CENTER, layout=Layout.VERTICAL, spacing=8)
                panel.add(Label("Inventory", style=Style(font_size=20)))
                grid = Grid(3, 3, cell_size=(64, 64), spacing=4, style=Style(padding=6))
                grid.set_cell(0, 0, Label("Sw", style=Style(font_size=14)))
                grid.set_cell(1, 0, Label("Sh", style=Style(font_size=14)))
                grid.set_cell(2, 0, Label("Bw", style=Style(font_size=14)))
                grid.set_cell(0, 1, Label("Hp", style=Style(font_size=14)))
                grid.set_cell(1, 1, Label("Mp", style=Style(font_size=14)))
                grid.selected = (1, 1)
                panel.add(grid)
                self.ui.add(panel)

        def setup(game):
            game.push(GridScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "widget_grid_with_cells.png")
        print("✓ widget_grid_with_cells.png")

    # 5. Tooltip
    def test_tooltip():
        class TipScene(Scene):
            def on_enter(self):
                self.ui.add(
                    Label(
                        "Hover over items for details",
                        anchor=Anchor.TOP,
                        margin=20,
                        style=Style(font_size=16),
                    )
                )
                self._tooltip = Tooltip(
                    "Sword of Flames (+12 ATK)", delay=0.3, style=Style(font_size=14)
                )
                self.ui.add(self._tooltip)
                self._tooltip.show(150, 180)

        def setup(game):
            game.push(TipScene())
            for _ in range(30):
                game.tick(dt=1.0 / 60.0)

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "widget_tooltip_visible.png")
        print("✓ widget_tooltip_visible.png")

    # 6. TabGroup
    def test_tabgroup():
        class TabScene(Scene):
            def on_enter(self):
                stats_panel = Panel(
                    layout=Layout.VERTICAL,
                    spacing=6,
                    width=300,
                    height=120,
                    style=Style(padding=10),
                )
                stats_panel.add(Label("STR: 18", style=Style(font_size=16)))
                stats_panel.add(Label("DEX: 14", style=Style(font_size=16)))
                stats_panel.add(Label("INT: 12", style=Style(font_size=16)))

                skills_panel = Panel(
                    layout=Layout.VERTICAL,
                    spacing=6,
                    width=300,
                    height=120,
                    style=Style(padding=10),
                )
                skills_panel.add(Label("Fireball Lv.3", style=Style(font_size=16)))
                skills_panel.add(Label("Heal Lv.2", style=Style(font_size=16)))

                items_panel = Panel(
                    layout=Layout.VERTICAL,
                    spacing=6,
                    width=300,
                    height=120,
                    style=Style(padding=10),
                )
                items_panel.add(Label("Potion x5", style=Style(font_size=16)))
                items_panel.add(Label("Elixir x2", style=Style(font_size=16)))

                tabs = TabGroup(
                    {
                        "Stats": stats_panel,
                        "Skills": skills_panel,
                        "Items": items_panel,
                    },
                    width=320,
                    height=160,
                    anchor=Anchor.CENTER,
                )
                self.ui.add(tabs)

        def setup(game):
            game.push(TabScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "widget_tabgroup.png")
        print("✓ widget_tabgroup.png")

    # 7. DataTable
    def test_datatable():
        class TableScene(Scene):
            def on_enter(self):
                dt = DataTable(
                    ["Unit", "Class", "Level"],
                    [
                        ["Arthas", "Paladin", "10"],
                        ["Jaina", "Mage", "12"],
                        ["Thrall", "Shaman", "15"],
                        ["Sylvanas", "Ranger", "18"],
                        ["Uther", "Cleric", "9"],
                    ],
                    width=360,
                    anchor=Anchor.CENTER,
                )
                dt.selected_row = 1
                self.ui.add(dt)

        def setup(game):
            game.push(TableScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "widget_datatable.png")
        print("✓ widget_datatable.png")

    # 8. Combined Dialog
    def test_dialog():
        class DialogScene(Scene):
            def on_enter(self):
                dialog = Panel(
                    anchor=Anchor.BOTTOM,
                    margin=10,
                    layout=Layout.VERTICAL,
                    spacing=8,
                    width=460,
                    style=Style(background_color=(25, 25, 40, 240), padding=12),
                )

                top_row = Panel(
                    layout=Layout.HORIZONTAL,
                    spacing=10,
                    style=Style(padding=0, background_color=(0, 0, 0, 0)),
                )

                portrait_panel = Panel(
                    width=64,
                    height=64,
                    style=Style(background_color=(80, 60, 100, 255), padding=4),
                )
                portrait_panel.add(Label("NPC", style=Style(font_size=14)))
                top_row.add(portrait_panel)

                text = TextBox(
                    "Greetings, adventurer! I have a quest for you. "
                    "The goblins in the eastern caves have stolen our "
                    "sacred relic. Will you retrieve it for us?",
                    typewriter_speed=100,
                    width=350,
                    style=Style(font_size=15),
                )
                text.skip()
                top_row.add(text)
                dialog.add(top_row)

                button_row = Panel(
                    layout=Layout.HORIZONTAL,
                    spacing=12,
                    style=Style(padding=0, background_color=(0, 0, 0, 0)),
                )
                button_row.add(Button("Accept", style=Style(font_size=16, padding=8)))
                button_row.add(Button("Decline", style=Style(font_size=16, padding=8)))
                dialog.add(button_row)

                self.ui.add(dialog)

        def setup(game):
            game.push(DialogScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "widget_combined_dialog.png")
        print("✓ widget_combined_dialog.png")

    # Run all
    test_progress_bar()
    test_textbox()
    test_list()
    test_grid()
    test_tooltip()
    test_tabgroup()
    test_datatable()
    test_dialog()


# =============================================================================
# Stage13 Screenshots (from test_stage13_screenshots.py)
# =============================================================================


def generate_stage13_screenshots():
    """Generate all 6 stage13 golden images."""
    print("\n" + "=" * 60)
    print("Generating Stage13 Screenshots")
    print("=" * 60)

    # 1. MessageScreen
    def test_message_screen():
        class BaseScene(Scene):
            def on_enter(self):
                self.ui.add(
                    Label(
                        "Game World",
                        anchor=Anchor.TOP,
                        margin=20,
                        style=Style(font_size=20),
                    )
                )

        def setup(game):
            game.push(BaseScene())
            game.push(MessageScreen("You found a legendary sword!"))

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "stage13_message_screen.png")
        print("✓ stage13_message_screen.png")

    # 2. ChoiceScreen
    def test_choice_screen():
        class BaseScene(Scene):
            def on_enter(self):
                self.ui.add(
                    Label(
                        "Character Creation",
                        anchor=Anchor.TOP,
                        margin=20,
                        style=Style(font_size=20),
                    )
                )

        def setup(game):
            game.push(BaseScene())
            game.push(ChoiceScreen("Choose your class:", ["Warrior", "Mage", "Rogue"]))

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "stage13_choice_screen.png")
        print("✓ stage13_choice_screen.png")

    # 3. ConfirmDialog
    def test_confirm_dialog():
        class BaseScene(Scene):
            def on_enter(self):
                self.ui.add(
                    Label(
                        "Inventory",
                        anchor=Anchor.TOP,
                        margin=20,
                        style=Style(font_size=20),
                    )
                )

        def setup(game):
            game.push(BaseScene())
            game.push(ConfirmDialog("Overwrite existing save?"))

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "stage13_confirm_dialog.png")
        print("✓ stage13_confirm_dialog.png")

    # 4. SaveLoadScreen
    def test_save_load_screen():
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            save_dir = Path(tmp_dir) / "saves"
            mgr = SaveManager(save_dir)
            mgr.save(1, {"hero": "Arthas", "level": 10}, "CampaignScene")
            mgr.save(3, {"hero": "Jaina", "level": 15}, "BattleScene")

            class BaseScene(Scene):
                def on_enter(self):
                    self.ui.add(
                        Label(
                            "Main Menu",
                            anchor=Anchor.TOP,
                            margin=20,
                            style=Style(font_size=20),
                        )
                    )

            def setup(game):
                game.push(BaseScene())
                game.push(SaveLoadScreen("load", save_manager=mgr, slot_count=5))

            image = render_widget_to_image(setup)
            image.save(GOLDEN_DIR / "stage13_save_load_screen.png")
            print("✓ stage13_save_load_screen.png")

    # 5. HUD Bar (contains ProgressBar!)
    def test_hud_bar():
        class GameScene(Scene):
            show_hud = True

            def on_enter(self):
                self.ui.add(
                    Label(
                        "Explore the Dungeon",
                        anchor=Anchor.CENTER,
                        style=Style(font_size=22, text_color=(180, 180, 180, 255)),
                    )
                )

        def setup(game):
            game.push(GameScene())

            # Add HUD elements
            hp_panel = Panel(
                anchor=Anchor.TOP_LEFT, margin=10, layout=Layout.HORIZONTAL, spacing=6
            )
            hp_panel.add(
                Label("HP", style=Style(font_size=16, text_color=(255, 80, 80, 255)))
            )
            hp_panel.add(
                ProgressBar(
                    value=72,
                    max_value=100,
                    width=120,
                    height=18,
                    bar_color=(200, 40, 40, 255),
                    bg_color=(60, 20, 20, 200),
                )
            )
            game.hud.add(hp_panel)

            game.hud.add(
                Label(
                    "Gold: 500",
                    anchor=Anchor.TOP_RIGHT,
                    margin=10,
                    style=Style(font_size=16, text_color=(255, 215, 0, 255)),
                )
            )

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "stage13_hud_bar.png")
        print("✓ stage13_hud_bar.png")

    # 6. Menu Scene
    def test_menu_scene():
        class MenuScene(Scene):
            def on_enter(self):
                # Title
                self.ui.add(
                    Label(
                        "SAGA2D",
                        anchor=Anchor.TOP,
                        margin=60,
                        style=Style(font_size=48, text_color=(255, 215, 0, 255)),
                    )
                )

                # Menu buttons
                menu_panel = Panel(
                    anchor=Anchor.CENTER,
                    layout=Layout.VERTICAL,
                    spacing=12,
                    style=Style(padding=20),
                )
                menu_panel.add(
                    Button("New Game", style=Style(font_size=20, padding=10))
                )
                menu_panel.add(
                    Button("Continue", style=Style(font_size=20, padding=10))
                )
                menu_panel.add(
                    Button("Settings", style=Style(font_size=20, padding=10))
                )
                menu_panel.add(Button("Quit", style=Style(font_size=20, padding=10)))
                self.ui.add(menu_panel)

                # Footer
                self.ui.add(
                    Label(
                        "Press ESC to return",
                        anchor=Anchor.BOTTOM,
                        margin=20,
                        style=Style(font_size=14, text_color=(120, 120, 120, 255)),
                    )
                )

        def setup(game):
            game.push(MenuScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "stage13_menu_scene.png")
        print("✓ stage13_menu_scene.png")

    # Run all
    test_message_screen()
    test_choice_screen()
    test_confirm_dialog()
    test_save_load_screen()
    test_hud_bar()
    test_menu_scene()


# =============================================================================
# UI Screenshots (from test_ui_screenshots.py)
# =============================================================================


def generate_ui_screenshots():
    """Generate all 4 UI golden images."""
    print("\n" + "=" * 60)
    print("Generating UI Screenshots")
    print("=" * 60)

    # 1. Main Menu
    def test_ui_main_menu():
        class MenuScene(Scene):
            def on_enter(self):
                panel = Panel(anchor=Anchor.CENTER, layout=Layout.VERTICAL, spacing=8)
                panel.add(Label("Main Menu", style=Style(font_size=28)))
                panel.add(Button("New Game"))
                panel.add(Button("Load Game"))
                panel.add(Button("Quit"))
                self.ui.add(panel)

        def setup(game):
            game.push(MenuScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "ui_main_menu.png")
        print("✓ ui_main_menu.png")

    # 2. Horizontal Buttons
    def test_ui_horizontal_buttons():
        class HBarScene(Scene):
            def on_enter(self):
                panel = Panel(
                    anchor=Anchor.BOTTOM,
                    layout=Layout.HORIZONTAL,
                    spacing=12,
                    margin=10,
                )
                panel.add(Button("Attack"))
                panel.add(Button("Defend"))
                panel.add(Button("Magic"))
                self.ui.add(panel)

        def setup(game):
            game.push(HBarScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "ui_horizontal_buttons.png")
        print("✓ ui_horizontal_buttons.png")

    # 3. Styled Label
    def test_ui_styled_label():
        class LabelScene(Scene):
            def on_enter(self):
                self.ui.add(
                    Label(
                        "GAME OVER",
                        anchor=Anchor.CENTER,
                        style=Style(font_size=40, text_color=(255, 60, 60, 255)),
                    )
                )

        def setup(game):
            game.push(LabelScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "ui_styled_label.png")
        print("✓ ui_styled_label.png")

    # 4. Nested Panels
    def test_ui_nested_panels():
        class NestedScene(Scene):
            def on_enter(self):
                inner_style = Style(background_color=(80, 80, 100, 220), padding=10)

                top_row = Panel(layout=Layout.HORIZONTAL, spacing=20, style=inner_style)
                top_row.add(Label("HP: 100", style=Style(font_size=18)))
                top_row.add(Label("MP: 50", style=Style(font_size=18)))

                bottom_row = Panel(
                    layout=Layout.HORIZONTAL, spacing=20, style=inner_style
                )
                bottom_row.add(Label("ATK: 25", style=Style(font_size=18)))
                bottom_row.add(Label("DEF: 18", style=Style(font_size=18)))

                outer = Panel(
                    anchor=Anchor.CENTER,
                    layout=Layout.VERTICAL,
                    spacing=8,
                    style=Style(background_color=(30, 30, 45, 240), padding=14),
                )
                outer.add(top_row)
                outer.add(bottom_row)
                self.ui.add(outer)

        def setup(game):
            game.push(NestedScene())

        image = render_widget_to_image(setup)
        image.save(GOLDEN_DIR / "ui_nested_panels.png")
        print("✓ ui_nested_panels.png")

    # Run all
    test_ui_main_menu()
    test_ui_horizontal_buttons()
    test_ui_styled_label()
    test_ui_nested_panels()


# =============================================================================
# Main
# =============================================================================


def main():
    """Generate all screenshot golden images."""
    print("\n" + "=" * 70)
    print("Generating ALL Screenshot Golden Images")
    print("Using MockBackend + PIL Renderer")
    print("=" * 70)

    generate_widget_screenshots()
    generate_stage13_screenshots()
    generate_ui_screenshots()

    print("\n" + "=" * 70)
    print("✓ All golden images generated successfully!")
    print("=" * 70)
    print(f"\nOutput directory: {GOLDEN_DIR}")
    print(f"\nGenerated {len(list(GOLDEN_DIR.glob('*.png')))} total images")


if __name__ == "__main__":
    main()
