"""Comprehensive tests for saga2d UI, Input, Audio, Save/Load, FSM, Assets, and Cursor systems."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from saga2d import Game
from saga2d.assets import AssetManager, AssetNotFoundError
from saga2d.audio import AudioManager
from saga2d.cursor import CursorManager
from saga2d.input import InputEvent, InputManager, _with_world_coords
from saga2d.save import SaveError, SaveManager
from saga2d.ui.component import Component, _UIRoot
from saga2d.ui.components import Button, Label, Panel
from saga2d.ui.layout import Anchor, Layout, compute_anchor_position, compute_flow_layout
from saga2d.ui.theme import Style
from saga2d.ui.widgets import (
    DataTable,
    Grid,
    List,
    ProgressBar,
    TabGroup,
    TextBox,
    Tooltip,
)
from saga2d.util.fsm import StateMachine


# =====================================================================
# 1. UI Components
# =====================================================================


class TestPanelWithChildren:
    """Panel with children (Label, Button), verify layout computed."""

    def test_panel_with_label_and_button_layout(self, mock_game):
        panel = Panel(
            width=400,
            height=300,
            layout=Layout.VERTICAL,
            spacing=10,
        )
        label = Label("Hello")
        button = Button("Click Me", width=200, height=40)
        panel.add(label)
        panel.add(button)

        root = _UIRoot(mock_game)
        root.add(panel)
        root.compute_layout(0, 0, 1920, 1080)

        # Panel should have computed bounds
        assert panel._computed_w == 400
        assert panel._computed_h == 300
        # Children should have non-zero computed dimensions
        assert label._computed_w > 0
        assert label._computed_h > 0
        assert button._computed_w > 0
        assert button._computed_h > 0

    def test_panel_children_in_vertical_layout_are_stacked(self, mock_game):
        panel = Panel(width=400, height=300, layout=Layout.VERTICAL, spacing=10)
        l1 = Label("First", height=30)
        l2 = Label("Second", height=30)
        panel.add(l1)
        panel.add(l2)

        root = _UIRoot(mock_game)
        root.add(panel)
        root.compute_layout(0, 0, 1920, 1080)

        # l2 should be below l1
        assert l2._computed_y > l1._computed_y


class TestButtonClick:
    """Button click: inject click event at button position, verify on_click fires."""

    def test_button_click_fires_callback(self, mock_game):
        clicked = []
        button = Button("Test", on_click=lambda: clicked.append(True), width=200, height=40)
        root = _UIRoot(mock_game)
        root.add(button)
        root.compute_layout(0, 0, 1920, 1080)

        # Click at button center
        cx = button._computed_x + button._computed_w // 2
        cy = button._computed_y + button._computed_h // 2
        event = InputEvent(type="click", x=cx, y=cy, button="left")
        consumed = root.handle_event(event)

        assert consumed is True
        assert len(clicked) == 1

    def test_button_click_outside_does_not_fire(self, mock_game):
        clicked = []
        button = Button(
            "Test",
            on_click=lambda: clicked.append(True),
            width=100,
            height=40,
            anchor=Anchor.TOP_LEFT,
        )
        root = _UIRoot(mock_game)
        root.add(button)
        root.compute_layout(0, 0, 1920, 1080)

        # Click far away
        event = InputEvent(type="click", x=1900, y=1060, button="left")
        root.handle_event(event)

        assert len(clicked) == 0


class TestButtonHoverState:
    """Button hover state: inject mouse move, verify state changes."""

    def test_button_hover_on_mouse_move(self, mock_game):
        button = Button("Test", width=200, height=40)
        root = _UIRoot(mock_game)
        root.add(button)
        root.compute_layout(0, 0, 1920, 1080)

        assert button.state == "normal"

        # Move mouse over button
        cx = button._computed_x + button._computed_w // 2
        cy = button._computed_y + button._computed_h // 2
        event = InputEvent(type="move", x=cx, y=cy)
        root.handle_event(event)

        assert button.state == "hovered"

    def test_button_unhover_on_mouse_leave(self, mock_game):
        button = Button("Test", width=200, height=40, anchor=Anchor.TOP_LEFT)
        root = _UIRoot(mock_game)
        root.add(button)
        root.compute_layout(0, 0, 1920, 1080)

        # Hover first
        cx = button._computed_x + button._computed_w // 2
        cy = button._computed_y + button._computed_h // 2
        root.handle_event(InputEvent(type="move", x=cx, y=cy))
        assert button.state == "hovered"

        # Move away
        root.handle_event(InputEvent(type="move", x=1900, y=1060))
        assert button.state == "normal"


class TestEmptyPanel:
    """Empty Panel -- does it render without crash?"""

    def test_empty_panel_renders(self, mock_game):
        panel = Panel(width=100, height=100)
        root = _UIRoot(mock_game)
        root.add(panel)
        root.compute_layout(0, 0, 1920, 1080)
        # Should not crash
        root.draw()

    def test_empty_panel_no_children(self, mock_game):
        panel = Panel()
        assert len(panel.children) == 0


class TestPanelNegativeSize:
    """Panel with negative size/padding."""

    def test_panel_negative_width_raises(self):
        with pytest.raises(ValueError, match="width cannot be negative"):
            Panel(width=-10, height=100)

    def test_panel_negative_height_raises(self):
        with pytest.raises(ValueError, match="height cannot be negative"):
            Panel(width=100, height=-10)

    def test_panel_negative_spacing_raises(self):
        with pytest.raises(ValueError, match="spacing cannot be negative"):
            Panel(spacing=-5)


class TestLabelEmptyString:
    """Label with empty string."""

    def test_label_empty_string_renders(self, mock_game):
        label = Label("")
        root = _UIRoot(mock_game)
        root.add(label)
        root.compute_layout(0, 0, 1920, 1080)
        # Should not crash
        root.draw()

    def test_label_none_text(self, mock_game):
        label = Label(None)
        assert label.text == ""


class TestLabelLongString:
    """Label with very long string (1000+ chars)."""

    def test_label_long_string_preferred_size(self):
        text = "a" * 1500
        label = Label(text)
        w, h = label.get_preferred_size()
        assert w > 0
        assert h > 0

    def test_label_long_string_renders(self, mock_game):
        text = "x" * 2000
        label = Label(text)
        root = _UIRoot(mock_game)
        root.add(label)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()


class TestProgressBar:
    """ProgressBar at 0%, 50%, 100%, >100%, <0%."""

    def test_progress_bar_zero(self, mock_game):
        bar = ProgressBar(value=0, max_value=100)
        assert bar.fraction == 0.0
        root = _UIRoot(mock_game)
        root.add(bar)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()

    def test_progress_bar_fifty(self):
        bar = ProgressBar(value=50, max_value=100)
        assert bar.fraction == pytest.approx(0.5)

    def test_progress_bar_hundred(self):
        bar = ProgressBar(value=100, max_value=100)
        assert bar.fraction == pytest.approx(1.0)

    def test_progress_bar_over_hundred(self):
        bar = ProgressBar(value=150, max_value=100)
        # fraction should be clamped to 1.0
        assert bar.fraction == pytest.approx(1.0)

    def test_progress_bar_negative(self):
        bar = ProgressBar(value=-20, max_value=100)
        # fraction should be clamped to 0.0
        assert bar.fraction == pytest.approx(0.0)

    def test_progress_bar_zero_max_value(self):
        bar = ProgressBar(value=50, max_value=0)
        assert bar.fraction == 0.0

    def test_progress_bar_negative_max_value(self):
        bar = ProgressBar(value=50, max_value=-10)
        assert bar.fraction == 0.0

    def test_progress_bar_renders_at_all_states(self, mock_game):
        """Ensure rendering doesn't crash at extreme values."""
        root = _UIRoot(mock_game)
        for val in [-50, 0, 50, 100, 200]:
            bar = ProgressBar(value=val, max_value=100)
            root.add(bar)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()


class TestListWidget:
    """List with 0 items, 1 item, 100 items."""

    def test_list_zero_items(self, mock_game):
        lst = List(items=[])
        root = _UIRoot(mock_game)
        root.add(lst)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()

    def test_list_one_item(self, mock_game):
        lst = List(items=["Solo"])
        root = _UIRoot(mock_game)
        root.add(lst)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()
        assert lst.items == ["Solo"]

    def test_list_many_items(self, mock_game):
        items = [f"Item {i}" for i in range(100)]
        lst = List(items=items, height=200)
        root = _UIRoot(mock_game)
        root.add(lst)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()

    def test_list_none_items(self, mock_game):
        lst = List(items=None)
        assert lst.items == []


class TestDataTableEmpty:
    """DataTable with empty data."""

    def test_datatable_empty_rows(self, mock_game):
        dt = DataTable(columns=["Name", "Value"], rows=[], width=400)
        root = _UIRoot(mock_game)
        root.add(dt)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()

    def test_datatable_no_rows_arg(self, mock_game):
        dt = DataTable(columns=["A", "B"], width=400)
        assert dt.rows == []


class TestGridZeroColumns:
    """Grid with 0 columns."""

    def test_grid_zero_columns(self, mock_game):
        grid = Grid(columns=0, rows=3)
        root = _UIRoot(mock_game)
        root.add(grid)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()

    def test_grid_zero_rows(self, mock_game):
        grid = Grid(columns=3, rows=0)
        root = _UIRoot(mock_game)
        root.add(grid)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()


class TestTextBox:
    """TextBox: type characters, verify text updates."""

    def test_textbox_text_property(self):
        tb = TextBox("Hello World", width=300)
        assert tb.text == "Hello World"

    def test_textbox_text_setter(self):
        tb = TextBox("Initial", width=300)
        tb.text = "Updated"
        assert tb.text == "Updated"

    def test_textbox_typewriter(self):
        tb = TextBox("Hello", typewriter_speed=10, width=300)
        assert tb.revealed_count == 0
        tb.update(0.5)  # 10 * 0.5 = 5 chars
        assert tb.revealed_count == 5
        assert tb.is_complete is True

    def test_textbox_typewriter_skip(self):
        tb = TextBox("Hello World", typewriter_speed=5, width=300)
        assert tb.is_complete is False
        tb.skip()
        assert tb.is_complete is True

    def test_textbox_renders(self, mock_game):
        tb = TextBox("Sample text for rendering.", width=300)
        root = _UIRoot(mock_game)
        root.add(tb)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()

    def test_textbox_empty_string(self, mock_game):
        tb = TextBox("", width=300)
        root = _UIRoot(mock_game)
        root.add(tb)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()


class TestTabGroup:
    """TabGroup with 0 tabs, 1 tab, switching tabs."""

    def test_tabgroup_zero_tabs(self, mock_game):
        tg = TabGroup(tabs=None, width=400, height=300)
        assert tg.active_tab is None
        assert tg.tab_labels == []
        root = _UIRoot(mock_game)
        root.add(tg)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()

    def test_tabgroup_one_tab(self, mock_game):
        content = Label("Content")
        tg = TabGroup(tabs={"Tab1": content}, width=400, height=300)
        assert tg.active_tab == "Tab1"
        assert tg.tab_labels == ["Tab1"]
        root = _UIRoot(mock_game)
        root.add(tg)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()

    def test_tabgroup_switch_tabs(self, mock_game):
        c1 = Label("Content 1")
        c2 = Label("Content 2")
        tg = TabGroup(tabs={"Tab1": c1, "Tab2": c2}, width=400, height=300)
        assert tg.active_tab == "Tab1"
        assert c1.visible is True
        assert c2.visible is False

        tg.select_tab("Tab2")
        assert tg.active_tab == "Tab2"
        assert c1.visible is False
        assert c2.visible is True

    def test_tabgroup_select_nonexistent_tab(self, mock_game):
        c1 = Label("Content 1")
        tg = TabGroup(tabs={"Tab1": c1}, width=400, height=300)
        with pytest.raises(KeyError):
            tg.select_tab("NonExistent")

    def test_tabgroup_add_tab(self, mock_game):
        tg = TabGroup(tabs=None, width=400, height=300)
        c1 = Label("Content 1")
        tg.add_tab("New", c1)
        assert tg.active_tab == "New"
        assert tg.tab_labels == ["New"]


class TestTooltip:
    """Tooltip show/hide."""

    def test_tooltip_show_hide(self, mock_game):
        tt = Tooltip("Help text", delay=0.5)
        root = _UIRoot(mock_game)
        root.add(tt)
        root.compute_layout(0, 0, 1920, 1080)

        tt.show(100, 200)
        assert tt._showing is True
        assert tt._visible_now is False

        # Advance time to past delay
        tt.update(0.6)
        assert tt._visible_now is True

        tt.hide()
        assert tt._showing is False
        assert tt._visible_now is False

    def test_tooltip_zero_delay(self, mock_game):
        tt = Tooltip("Instant", delay=0)
        tt.show(100, 200)
        assert tt._visible_now is True

    def test_tooltip_draw_when_visible(self, mock_game):
        tt = Tooltip("Test", delay=0)
        root = _UIRoot(mock_game)
        root.add(tt)
        root.compute_layout(0, 0, 1920, 1080)
        tt.show(100, 200)
        root.draw()  # Should not crash


class TestNestedPanels:
    """Nested panels (5+ levels deep)."""

    def test_deeply_nested_panels(self, mock_game):
        root = _UIRoot(mock_game)
        current = root
        for i in range(7):
            p = Panel(width=100, height=100)
            current.add(p)
            current = p
        # Add a leaf label
        current.add(Label("Deep"))
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()


class TestVisibilityToggle:
    """UI component visibility toggle."""

    def test_invisible_component_not_drawn(self, mock_game):
        label = Label("Hidden")
        label.visible = False
        root = _UIRoot(mock_game)
        root.add(label)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()
        # Check no text was drawn
        backend = mock_game._backend
        assert len(backend.texts) == 0

    def test_invisible_component_does_not_receive_events(self, mock_game):
        clicked = []
        button = Button("Test", on_click=lambda: clicked.append(True), width=200, height=40)
        button.visible = False
        root = _UIRoot(mock_game)
        root.add(button)
        root.compute_layout(0, 0, 1920, 1080)

        event = InputEvent(type="click", x=100, y=20, button="left")
        root.handle_event(event)
        assert len(clicked) == 0

    def test_toggle_visibility(self, mock_game):
        label = Label("Toggle")
        root = _UIRoot(mock_game)
        root.add(label)
        root.compute_layout(0, 0, 1920, 1080)

        label.visible = False
        root.draw()
        assert len(mock_game._backend.texts) == 0

        mock_game._backend.begin_frame()
        label.visible = True
        root.draw()
        assert len(mock_game._backend.texts) > 0


# =====================================================================
# 2. Layout & Anchoring
# =====================================================================


class TestAnchorPositions:
    """compute_anchor_position for all 9 Anchor values."""

    def test_center(self):
        x, y = compute_anchor_position(Anchor.CENTER, 0, 0, 800, 600, 100, 50, 0)
        assert x == 350
        assert y == 275

    def test_top(self):
        x, y = compute_anchor_position(Anchor.TOP, 0, 0, 800, 600, 100, 50, 10)
        assert x == 350
        assert y == 10

    def test_bottom(self):
        x, y = compute_anchor_position(Anchor.BOTTOM, 0, 0, 800, 600, 100, 50, 10)
        assert x == 350
        assert y == 540  # 600 - 50 - 10

    def test_left(self):
        x, y = compute_anchor_position(Anchor.LEFT, 0, 0, 800, 600, 100, 50, 10)
        assert x == 10
        assert y == 275

    def test_right(self):
        x, y = compute_anchor_position(Anchor.RIGHT, 0, 0, 800, 600, 100, 50, 10)
        assert x == 690  # 800 - 100 - 10
        assert y == 275

    def test_top_left(self):
        x, y = compute_anchor_position(Anchor.TOP_LEFT, 0, 0, 800, 600, 100, 50, 10)
        assert x == 10
        assert y == 10

    def test_top_right(self):
        x, y = compute_anchor_position(Anchor.TOP_RIGHT, 0, 0, 800, 600, 100, 50, 10)
        assert x == 690
        assert y == 10

    def test_bottom_left(self):
        x, y = compute_anchor_position(Anchor.BOTTOM_LEFT, 0, 0, 800, 600, 100, 50, 10)
        assert x == 10
        assert y == 540

    def test_bottom_right(self):
        x, y = compute_anchor_position(Anchor.BOTTOM_RIGHT, 0, 0, 800, 600, 100, 50, 10)
        assert x == 690
        assert y == 540

    def test_with_parent_offset(self):
        x, y = compute_anchor_position(Anchor.TOP_LEFT, 100, 200, 800, 600, 50, 50, 5)
        assert x == 105
        assert y == 205


class TestFlowLayout:
    """compute_flow_layout with VERTICAL, HORIZONTAL."""

    def test_vertical_layout(self):
        positions = compute_flow_layout(
            Layout.VERTICAL, 0, 0, 400, 600, [(100, 30), (100, 30)], spacing=10, padding=5
        )
        assert len(positions) == 2
        # First child at y=padding=5
        assert positions[0][1] == 5
        # Second child at y=5+30+10=45
        assert positions[1][1] == 45

    def test_horizontal_layout(self):
        positions = compute_flow_layout(
            Layout.HORIZONTAL, 0, 0, 600, 400, [(100, 30), (100, 30)], spacing=10, padding=5
        )
        assert len(positions) == 2
        assert positions[0][0] == 5
        assert positions[1][0] == 115  # 5+100+10

    def test_layout_none_returns_empty(self):
        positions = compute_flow_layout(
            Layout.NONE, 0, 0, 400, 300, [(100, 30)], spacing=10, padding=5
        )
        assert positions == []

    def test_layout_empty_children(self):
        positions = compute_flow_layout(
            Layout.VERTICAL, 0, 0, 400, 300, [], spacing=10, padding=5
        )
        assert positions == []


class TestLayoutEdgeCases:
    """Layout with zero-size container and children larger than container."""

    def test_zero_size_container(self):
        positions = compute_flow_layout(
            Layout.VERTICAL, 0, 0, 0, 0, [(100, 30)], spacing=10, padding=0
        )
        # Should still return positions (even if they overflow)
        assert len(positions) == 1

    def test_children_larger_than_container(self):
        positions = compute_flow_layout(
            Layout.VERTICAL, 0, 0, 50, 50, [(200, 100), (200, 100)], spacing=5, padding=0
        )
        assert len(positions) == 2
        # Children will overflow, but positions should still be computed


# =====================================================================
# 3. Modal Screens
# =====================================================================


class TestMessageScreen:
    """MessageScreen: push, verify draw, dismiss."""

    def test_message_screen_push_and_draw(self, mock_game):
        from saga2d.scene import Scene
        from saga2d.ui.screens import MessageScreen

        # Push a base scene first
        class BaseScene(Scene):
            pass

        base = BaseScene()
        mock_game.push(base)
        mock_game.tick(dt=0.016)

        dismissed = []
        msg = MessageScreen("Test Message", on_dismiss=lambda: dismissed.append(True))
        mock_game.push(msg)
        mock_game.tick(dt=0.016)

        # Verify it's drawn
        assert len(mock_game._backend.texts) > 0

    def test_message_screen_dismiss_on_key(self, mock_game):
        from saga2d.scene import Scene
        from saga2d.ui.screens import MessageScreen

        class BaseScene(Scene):
            pass

        base = BaseScene()
        mock_game.push(base)
        mock_game.tick(dt=0.016)

        dismissed = []
        msg = MessageScreen("Test Message", on_dismiss=lambda: dismissed.append(True))
        mock_game.push(msg)
        mock_game.tick(dt=0.016)

        # Dismiss with key press
        mock_game._backend.inject_key("space")
        mock_game.tick(dt=0.016)

        assert len(dismissed) == 1


class TestChoiceScreen:
    """ChoiceScreen: push, select option, verify callback."""

    def test_choice_screen_select(self, mock_game):
        from saga2d.scene import Scene
        from saga2d.ui.screens import ChoiceScreen

        class BaseScene(Scene):
            pass

        base = BaseScene()
        mock_game.push(base)
        mock_game.tick(dt=0.016)

        chosen = []
        cs = ChoiceScreen("Pick:", ["A", "B", "C"], on_choice=lambda i: chosen.append(i))
        mock_game.push(cs)
        mock_game.tick(dt=0.016)

        # Press "1" to select first choice
        mock_game._backend.inject_key("1")
        mock_game.tick(dt=0.016)

        assert chosen == [0]

    def test_choice_screen_escape_cancels(self, mock_game):
        from saga2d.scene import Scene
        from saga2d.ui.screens import ChoiceScreen

        class BaseScene(Scene):
            pass

        base = BaseScene()
        mock_game.push(base)
        mock_game.tick(dt=0.016)

        chosen = []
        cs = ChoiceScreen("Pick:", ["A"], on_choice=lambda i: chosen.append(i))
        mock_game.push(cs)
        mock_game.tick(dt=0.016)

        mock_game._backend.inject_key("escape")
        mock_game.tick(dt=0.016)

        # No choice made
        assert chosen == []


class TestConfirmDialog:
    """ConfirmDialog: push, confirm/cancel via keyboard."""

    def test_confirm_dialog_confirm(self, mock_game):
        from saga2d.scene import Scene
        from saga2d.ui.screens import ConfirmDialog

        class BaseScene(Scene):
            pass

        base = BaseScene()
        mock_game.push(base)
        mock_game.tick(dt=0.016)

        confirmed = []
        cancelled = []
        cd = ConfirmDialog(
            "Sure?",
            on_confirm=lambda: confirmed.append(True),
            on_cancel=lambda: cancelled.append(True),
        )
        mock_game.push(cd)
        mock_game.tick(dt=0.016)

        # Press return to confirm
        mock_game._backend.inject_key("return")
        mock_game.tick(dt=0.016)

        assert len(confirmed) == 1
        assert len(cancelled) == 0

    def test_confirm_dialog_cancel(self, mock_game):
        from saga2d.scene import Scene
        from saga2d.ui.screens import ConfirmDialog

        class BaseScene(Scene):
            pass

        base = BaseScene()
        mock_game.push(base)
        mock_game.tick(dt=0.016)

        confirmed = []
        cancelled = []
        cd = ConfirmDialog(
            "Sure?",
            on_confirm=lambda: confirmed.append(True),
            on_cancel=lambda: cancelled.append(True),
        )
        mock_game.push(cd)
        mock_game.tick(dt=0.016)

        mock_game._backend.inject_key("escape")
        mock_game.tick(dt=0.016)

        assert len(confirmed) == 0
        assert len(cancelled) == 1


class TestSaveLoadScreen:
    """SaveLoadScreen: push in save/load mode."""

    def test_saveload_screen_invalid_mode(self):
        from saga2d.ui.screens import SaveLoadScreen

        with pytest.raises(ValueError, match="mode must be"):
            SaveLoadScreen(mode="invalid")

    def test_saveload_screen_save_mode(self, mock_game, tmp_path):
        from saga2d.scene import Scene
        from saga2d.ui.screens import SaveLoadScreen

        class BaseScene(Scene):
            pass

        base = BaseScene()
        mock_game.push(base)
        mock_game.tick(dt=0.016)

        sm = SaveManager(tmp_path / "saves")
        sls = SaveLoadScreen(mode="save", save_manager=sm)
        mock_game.push(sls)
        mock_game.tick(dt=0.016)

        # Verify it drew something
        assert len(mock_game._backend.texts) > 0

    def test_saveload_screen_load_mode(self, mock_game, tmp_path):
        from saga2d.scene import Scene
        from saga2d.ui.screens import SaveLoadScreen

        class BaseScene(Scene):
            pass

        base = BaseScene()
        mock_game.push(base)
        mock_game.tick(dt=0.016)

        sm = SaveManager(tmp_path / "saves")
        sls = SaveLoadScreen(mode="load", save_manager=sm)
        mock_game.push(sls)
        mock_game.tick(dt=0.016)

        assert len(mock_game._backend.texts) > 0


# =====================================================================
# 4. Drag & Drop
# =====================================================================


class TestDragAndDrop:
    """Drag and drop system tests."""

    def test_drag_and_drop_valid_target(self, mock_game):
        from saga2d.scene import Scene

        class TestScene(Scene):
            pass

        scene = TestScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        dropped = []
        source = Component(
            width=50, height=50, draggable=True, drag_data="item_a"
        )
        target = Component(
            width=50,
            height=50,
            drop_accept=lambda data: True,
            on_drop=lambda comp, data: dropped.append(data),
        )

        scene.ui.add(source)
        scene.ui.add(target)

        # Position them
        source.compute_layout(10, 10, 50, 50)
        target.compute_layout(200, 10, 50, 50)

        # Start drag
        scene.ui.drag_manager._start_drag(source, "item_a", 30, 30)
        assert scene.ui.drag_manager.is_dragging is True

        # End drag on target
        scene.ui.drag_manager._end_drag(220, 30)
        assert scene.ui.drag_manager.is_dragging is False
        assert "item_a" in dropped

    def test_drag_cancel(self, mock_game):
        from saga2d.scene import Scene

        class TestScene(Scene):
            pass

        scene = TestScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        source = Component(width=50, height=50, draggable=True, drag_data="item_a")
        scene.ui.add(source)
        source.compute_layout(10, 10, 50, 50)

        scene.ui.drag_manager._start_drag(source, "item_a", 30, 30)
        assert scene.ui.drag_manager.is_dragging is True

        scene.ui.drag_manager._cancel_drag()
        assert scene.ui.drag_manager.is_dragging is False

    def test_drag_no_valid_targets(self, mock_game):
        from saga2d.scene import Scene

        class TestScene(Scene):
            pass

        scene = TestScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        dropped = []
        source = Component(width=50, height=50, draggable=True, drag_data="item_a")
        # Target that rejects everything
        target = Component(
            width=50,
            height=50,
            drop_accept=lambda data: False,
            on_drop=lambda comp, data: dropped.append(data),
        )

        scene.ui.add(source)
        scene.ui.add(target)
        source.compute_layout(10, 10, 50, 50)
        target.compute_layout(200, 10, 50, 50)

        scene.ui.drag_manager._start_drag(source, "item_a", 30, 30)
        scene.ui.drag_manager._end_drag(220, 30)

        assert len(dropped) == 0


# =====================================================================
# 5. Input
# =====================================================================


class TestInputDefaultBindings:
    """Default bindings (confirm->return, cancel->escape)."""

    def test_default_bindings(self):
        im = InputManager()
        bindings = im.get_bindings()
        assert bindings["confirm"] == "return"
        assert bindings["cancel"] == "escape"
        assert bindings["up"] == "up"
        assert bindings["down"] == "down"
        assert bindings["left"] == "left"
        assert bindings["right"] == "right"


class TestInputRebind:
    """Rebind key, verify old binding removed."""

    def test_rebind_key(self):
        im = InputManager()
        im.bind("confirm", "space")
        bindings = im.get_bindings()
        assert bindings["confirm"] == "space"
        # Old return key should no longer be bound
        assert "return" not in bindings.values()

    def test_unbind(self):
        im = InputManager()
        im.unbind("confirm")
        bindings = im.get_bindings()
        assert "confirm" not in bindings


class TestInputTranslation:
    """Translate raw events to InputEvents."""

    def test_translate_key_event(self):
        from saga2d.backends.base import KeyEvent

        im = InputManager()
        events = im.translate([KeyEvent(type="key_press", key="return")])
        assert len(events) == 1
        assert events[0].type == "key_press"
        assert events[0].key == "return"
        assert events[0].action == "confirm"

    def test_translate_mouse_event(self):
        from saga2d.backends.base import MouseEvent

        im = InputManager()
        events = im.translate(
            [MouseEvent(type="click", x=100, y=200, button="left")]
        )
        assert len(events) == 1
        assert events[0].type == "click"
        assert events[0].x == 100
        assert events[0].y == 200
        assert events[0].button == "left"

    def test_translate_none_events(self):
        im = InputManager()
        events = im.translate(None)
        assert events == []

    def test_translate_unbound_key(self):
        from saga2d.backends.base import KeyEvent

        im = InputManager()
        events = im.translate([KeyEvent(type="key_press", key="z")])
        assert events[0].action is None


class TestMouseWorldCoordinates:
    """Mouse event world coordinate population."""

    def test_world_coords_no_camera(self):
        event = InputEvent(type="click", x=100, y=200, button="left")
        result = _with_world_coords(event, None)
        assert result.world_x == 100.0
        assert result.world_y == 200.0

    def test_non_mouse_event_unchanged(self):
        event = InputEvent(type="key_press", key="a")
        result = _with_world_coords(event, None)
        assert result.world_x is None
        assert result.world_y is None


class TestKeyStealingBehavior:
    """Bind same key to different action (key stealing)."""

    def test_key_stealing(self):
        im = InputManager()
        # "return" is bound to "confirm"
        im.bind("attack", "return")
        bindings = im.get_bindings()
        # "attack" now has "return", "confirm" should be unbound
        assert bindings["attack"] == "return"
        assert "confirm" not in bindings


# =====================================================================
# 6. Audio
# =====================================================================


class TestAudioVolume:
    """Set volume, get volume."""

    def test_set_get_volume(self, mock_game):
        audio = mock_game.audio
        audio.set_volume("master", 0.5)
        assert audio.get_volume("master") == pytest.approx(0.5)

    def test_volume_clamped_high(self, mock_game):
        audio = mock_game.audio
        audio.set_volume("master", 1.5)
        assert audio.get_volume("master") == pytest.approx(1.0)

    def test_volume_clamped_low(self, mock_game):
        audio = mock_game.audio
        audio.set_volume("master", -0.5)
        assert audio.get_volume("master") == pytest.approx(0.0)

    def test_invalid_channel_raises(self, mock_game):
        audio = mock_game.audio
        with pytest.raises(KeyError, match="Unknown audio channel"):
            audio.set_volume("nonexistent", 0.5)

    def test_get_invalid_channel_raises(self, mock_game):
        audio = mock_game.audio
        with pytest.raises(KeyError, match="Unknown audio channel"):
            audio.get_volume("nonexistent")


class TestAudioPlaySound:
    """Play sound, verify backend called."""

    def test_play_sound(self, mock_game, tmp_path):
        # Create a fake sound file
        sound_file = tmp_path / "sounds" / "hit.wav"
        sound_file.parent.mkdir(parents=True, exist_ok=True)
        sound_file.write_bytes(b"RIFF" + b"\x00" * 100)

        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        audio.play_sound("hit")

        assert len(mock_game._backend.sounds_played) == 1

    def test_play_sound_missing_raises(self, mock_game, tmp_path):
        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        with pytest.raises(AssetNotFoundError):
            audio.play_sound("nonexistent")

    def test_play_sound_optional_missing(self, mock_game, tmp_path):
        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        # Should not raise
        audio.play_sound("nonexistent", optional=True)


class TestAudioPlayMusic:
    """Play music, verify backend called."""

    def test_play_music(self, mock_game, tmp_path):
        music_file = tmp_path / "music" / "theme.ogg"
        music_file.parent.mkdir(parents=True, exist_ok=True)
        music_file.write_bytes(b"OggS" + b"\x00" * 100)

        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        audio.play_music("theme")

        assert mock_game._backend.music_playing is not None

    def test_play_music_missing_optional(self, mock_game, tmp_path):
        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        audio.play_music("nonexistent", optional=True)
        # Should not raise and no music playing
        assert mock_game._backend.music_playing is None


class TestAudioCrossfade:
    """Crossfade music."""

    def test_crossfade_when_no_music(self, mock_game, tmp_path):
        music_file = tmp_path / "music" / "theme.ogg"
        music_file.parent.mkdir(parents=True, exist_ok=True)
        music_file.write_bytes(b"OggS" + b"\x00" * 100)

        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        # Crossfade with no music playing should just play
        audio.crossfade_music("theme")
        assert mock_game._backend.music_playing is not None

    def test_crossfade_same_track_noop(self, mock_game, tmp_path):
        music_file = tmp_path / "music" / "theme.ogg"
        music_file.parent.mkdir(parents=True, exist_ok=True)
        music_file.write_bytes(b"OggS" + b"\x00" * 100)

        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        audio.play_music("theme")
        player_count_before = len(mock_game._backend._music_players)

        audio.crossfade_music("theme")
        # Should be a no-op
        assert len(mock_game._backend._music_players) == player_count_before


class TestSoundPools:
    """Sound pools -- register, play from pool."""

    def test_register_and_play_pool(self, mock_game, tmp_path):
        sounds_dir = tmp_path / "sounds"
        sounds_dir.mkdir(parents=True, exist_ok=True)
        for i in range(3):
            (sounds_dir / f"hit_{i}.wav").write_bytes(b"RIFF" + b"\x00" * 100)

        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        audio.register_pool("hits", ["hit_0", "hit_1", "hit_2"])
        audio.play_pool("hits")

        assert len(mock_game._backend.sounds_played) == 1

    def test_play_pool_unregistered_raises(self, mock_game, tmp_path):
        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        with pytest.raises(KeyError):
            audio.play_pool("nonexistent")

    def test_play_pool_single_sound(self, mock_game, tmp_path):
        sounds_dir = tmp_path / "sounds"
        sounds_dir.mkdir(parents=True, exist_ok=True)
        (sounds_dir / "only.wav").write_bytes(b"RIFF" + b"\x00" * 100)

        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        audio.register_pool("solo", ["only"])
        audio.play_pool("solo")
        assert len(mock_game._backend.sounds_played) == 1

    def test_play_pool_empty_list(self, mock_game, tmp_path):
        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        audio.register_pool("empty", [])
        # Should not crash -- pool is empty, just return
        audio.play_pool("empty")


class TestAudioInvalidChannel:
    """Invalid channel name."""

    def test_play_sound_invalid_channel(self, mock_game, tmp_path):
        sounds_dir = tmp_path / "sounds"
        sounds_dir.mkdir(parents=True, exist_ok=True)
        (sounds_dir / "test.wav").write_bytes(b"RIFF" + b"\x00" * 100)

        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        with pytest.raises(KeyError, match="Unknown audio channel"):
            audio.play_sound("test", channel="bogus")


# =====================================================================
# 7. Save/Load
# =====================================================================


class TestSaveLoad:
    """Save state, load it back, verify data matches."""

    def test_save_and_load(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        state = {"hp": 100, "name": "Hero", "items": ["sword", "shield"]}
        sm.save(1, state, "TestScene")

        loaded = sm.load(1)
        assert loaded is not None
        assert loaded["state"] == state
        assert loaded["scene_class"] == "TestScene"
        assert loaded["version"] == 1
        assert "timestamp" in loaded


class TestSaveLoadNonExistent:
    """Load non-existent slot."""

    def test_load_nonexistent_slot(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        result = sm.load(1)
        assert result is None


class TestSaveDelete:
    """Delete slot."""

    def test_delete_slot(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        sm.save(1, {"data": "test"}, "Scene")
        assert sm.load(1) is not None

        sm.delete(1)
        assert sm.load(1) is None

    def test_delete_nonexistent_slot(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        # Should not raise
        sm.delete(99)


class TestSaveListSlots:
    """list_slots."""

    def test_list_slots_empty(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        slots = sm.list_slots(5)
        assert len(slots) == 5
        assert all(s is None for s in slots)

    def test_list_slots_with_data(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        sm.save(1, {"a": 1}, "S1")
        sm.save(3, {"b": 2}, "S2")

        slots = sm.list_slots(5)
        assert slots[0] is not None
        assert slots[1] is None
        assert slots[2] is not None
        assert slots[3] is None
        assert slots[4] is None

    def test_list_slots_zero(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        slots = sm.list_slots(0)
        assert slots == []


class TestSaveNonSerializable:
    """Save with non-JSON-serializable data (e.g., a set or custom object)."""

    def test_save_set_raises(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        with pytest.raises(SaveError):
            sm.save(1, {"items": {1, 2, 3}}, "TestScene")

    def test_save_custom_object_raises(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")

        class MyObj:
            pass

        with pytest.raises(SaveError):
            sm.save(1, {"obj": MyObj()}, "TestScene")


class TestSaveCorruptedFile:
    """Corrupted save file (invalid JSON)."""

    def test_corrupted_json_raises(self, tmp_path):
        save_dir = tmp_path / "saves"
        save_dir.mkdir(parents=True, exist_ok=True)
        (save_dir / "save_1.json").write_text("NOT VALID JSON {{{")

        sm = SaveManager(save_dir)
        with pytest.raises(SaveError, match="Corrupted save file"):
            sm.load(1)


class TestSaveSpecialChars:
    """Save with special characters in data."""

    def test_special_chars_roundtrip(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        state = {
            "name": "He\u0301ro\u2605",
            "dialog": 'She said "hello\nworld"',
            "path": "C:\\Users\\test",
            "emoji": "\U0001f600",
        }
        sm.save(1, state, "Scene")
        loaded = sm.load(1)
        assert loaded["state"] == state


class TestSaveSlotValidation:
    """Slot validation edge cases."""

    def test_slot_not_int(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        with pytest.raises(TypeError):
            sm.save("one", {"a": 1}, "Scene")  # type: ignore

    def test_slot_zero(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        with pytest.raises(ValueError):
            sm.save(0, {"a": 1}, "Scene")

    def test_slot_negative(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        with pytest.raises(ValueError):
            sm.save(-1, {"a": 1}, "Scene")


# =====================================================================
# 8. FSM
# =====================================================================


class TestFSMBasic:
    """Create FSM, trigger valid transitions."""

    def test_basic_transitions(self):
        fsm = StateMachine(
            states=["idle", "walking", "running"],
            initial="idle",
            transitions={
                "idle": {"walk": "walking"},
                "walking": {"run": "running", "stop": "idle"},
                "running": {"stop": "idle"},
            },
        )
        assert fsm.state == "idle"
        assert fsm.trigger("walk") is True
        assert fsm.state == "walking"
        assert fsm.trigger("run") is True
        assert fsm.state == "running"
        assert fsm.trigger("stop") is True
        assert fsm.state == "idle"


class TestFSMInvalidEvent:
    """Trigger invalid event (no transition for current state)."""

    def test_invalid_event_returns_false(self):
        fsm = StateMachine(
            states=["idle", "walking"],
            initial="idle",
            transitions={"idle": {"walk": "walking"}},
        )
        result = fsm.trigger("run")
        assert result is False
        assert fsm.state == "idle"


class TestFSMValidEvents:
    """valid_events in different states."""

    def test_valid_events(self):
        fsm = StateMachine(
            states=["idle", "walking"],
            initial="idle",
            transitions={
                "idle": {"walk": "walking", "jump": "idle"},
                "walking": {"stop": "idle"},
            },
        )
        assert set(fsm.valid_events) == {"walk", "jump"}
        fsm.trigger("walk")
        assert fsm.valid_events == ["stop"]

    def test_valid_events_no_transitions(self):
        fsm = StateMachine(
            states=["only"],
            initial="only",
        )
        assert fsm.valid_events == []


class TestFSMCallbacks:
    """on_enter/on_exit callbacks fire correctly."""

    def test_callbacks(self):
        log = []
        fsm = StateMachine(
            states=["a", "b"],
            initial="a",
            transitions={"a": {"go": "b"}},
            on_enter={
                "a": lambda: log.append("enter_a"),
                "b": lambda: log.append("enter_b"),
            },
            on_exit={
                "a": lambda: log.append("exit_a"),
                "b": lambda: log.append("exit_b"),
            },
        )
        # Initial state fires on_enter
        assert "enter_a" in log
        log.clear()

        fsm.trigger("go")
        assert log == ["exit_a", "enter_b"]

    def test_no_callback_on_invalid_event(self):
        log = []
        fsm = StateMachine(
            states=["a", "b"],
            initial="a",
            transitions={"a": {"go": "b"}},
            on_enter={"b": lambda: log.append("enter_b")},
        )
        fsm.trigger("invalid")
        assert "enter_b" not in log


class TestFSMSingleState:
    """FSM with single state and no transitions."""

    def test_single_state(self):
        fsm = StateMachine(states=["only"], initial="only")
        assert fsm.state == "only"
        assert fsm.trigger("anything") is False
        assert fsm.state == "only"


class TestFSMDuplicateStates:
    """Duplicate state names."""

    def test_duplicate_states_in_list(self):
        # Duplicates in the list should not crash; set() deduplicates internally
        fsm = StateMachine(
            states=["a", "a", "b"],
            initial="a",
            transitions={"a": {"go": "b"}},
        )
        assert fsm.state == "a"
        assert fsm.trigger("go") is True
        assert fsm.state == "b"


class TestFSMValidation:
    """FSM validation errors."""

    def test_invalid_initial_state(self):
        with pytest.raises(ValueError, match="Initial state"):
            StateMachine(states=["a", "b"], initial="c")

    def test_invalid_transition_source(self):
        with pytest.raises(ValueError, match="Transition source"):
            StateMachine(
                states=["a"],
                initial="a",
                transitions={"x": {"go": "a"}},
            )

    def test_invalid_transition_target(self):
        with pytest.raises(ValueError, match="Transition target"):
            StateMachine(
                states=["a"],
                initial="a",
                transitions={"a": {"go": "x"}},
            )


# =====================================================================
# 9. Assets
# =====================================================================


class TestAssetsMissingImage:
    """Load image that doesn't exist -> AssetNotFoundError."""

    def test_missing_image(self, mock_game, tmp_path):
        am = AssetManager(mock_game._backend, tmp_path)
        with pytest.raises(AssetNotFoundError):
            am.image("nonexistent_sprite")


class TestAssetsMissingSound:
    """Load sound that doesn't exist."""

    def test_missing_sound(self, mock_game, tmp_path):
        am = AssetManager(mock_game._backend, tmp_path)
        with pytest.raises(AssetNotFoundError):
            am.sound("nonexistent_sound")


class TestAssetsFramesNoMatch:
    """frames() with no matching files."""

    def test_frames_no_match(self, mock_game, tmp_path):
        images_dir = tmp_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        am = AssetManager(mock_game._backend, tmp_path)
        with pytest.raises(AssetNotFoundError):
            am.frames("nonexistent_animation")


class TestAssetsImageCaching:
    """Image caching -- same name returns same handle."""

    def test_image_cached(self, mock_game, tmp_path):
        images_dir = tmp_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "test.png").write_bytes(b"\x89PNG" + b"\x00" * 100)

        am = AssetManager(mock_game._backend, tmp_path)
        h1 = am.image("test")
        h2 = am.image("test")
        assert h1 == h2


# =====================================================================
# 10. Cursor
# =====================================================================


class TestCursorDefault:
    """set("default") -- restores system cursor."""

    def test_set_default_cursor(self, mock_game):
        cursor = mock_game.cursor
        cursor.set("default")
        assert cursor.current == "default"
        assert mock_game._backend.cursor_image is None


class TestCursorVisibility:
    """set_visible(True/False)."""

    def test_cursor_visible_toggle(self, mock_game):
        cursor = mock_game.cursor
        cursor.set_visible(False)
        assert mock_game._backend.cursor_visible is False

        cursor.set_visible(True)
        assert mock_game._backend.cursor_visible is True


class TestCursorUnknown:
    """set unknown cursor name."""

    def test_set_unknown_cursor_raises(self, mock_game):
        cursor = mock_game.cursor
        with pytest.raises(KeyError, match="not registered"):
            cursor.set("unknown_cursor")


class TestCursorRegisterAndSet:
    """Register and set a custom cursor."""

    def test_register_and_set(self, mock_game, tmp_path):
        images_dir = tmp_path / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        (images_dir / "crosshair.png").write_bytes(b"\x89PNG" + b"\x00" * 100)

        am = AssetManager(mock_game._backend, tmp_path)
        cursor = CursorManager(mock_game._backend, am)
        cursor.register("attack", "crosshair", hotspot=(16, 16))
        cursor.set("attack")
        assert cursor.current == "attack"
        assert mock_game._backend.cursor_image is not None
        assert mock_game._backend.cursor_hotspot == (16, 16)


# =====================================================================
# Additional edge case tests
# =====================================================================


class TestComponentNegativeMargin:
    """Component with negative margin."""

    def test_negative_margin_raises(self):
        with pytest.raises(ValueError, match="margin cannot be negative"):
            Component(margin=-5)


class TestComponentSelfAdd:
    """Cannot add component to itself."""

    def test_add_self_raises(self):
        c = Component()
        with pytest.raises(ValueError, match="Cannot add component to itself"):
            c.add(c)


class TestComponentReparent:
    """Adding a child that already has a parent reparents it."""

    def test_reparent(self):
        p1 = Panel()
        p2 = Panel()
        child = Label("X")
        p1.add(child)
        assert child.parent is p1

        p2.add(child)
        assert child.parent is p2
        assert child not in p1.children
        assert child in p2.children


class TestDisabledButton:
    """Disabled button does not receive click events."""

    def test_disabled_button_no_click(self, mock_game):
        clicked = []
        button = Button(
            "Test", on_click=lambda: clicked.append(True), width=200, height=40, enabled=False
        )
        root = _UIRoot(mock_game)
        root.add(button)
        root.compute_layout(0, 0, 1920, 1080)

        cx = button._computed_x + button._computed_w // 2
        cy = button._computed_y + button._computed_h // 2
        event = InputEvent(type="click", x=cx, y=cy, button="left")
        root.handle_event(event)

        assert len(clicked) == 0


# =====================================================================
# Deeper bug-probing tests
# =====================================================================


class TestButtonPressReleaseFlow:
    """Verify full button press/release state machine."""

    def test_click_sets_pressed_then_release_returns_to_hovered(self, mock_game):
        button = Button("Test", width=200, height=40)
        root = _UIRoot(mock_game)
        root.add(button)
        root.compute_layout(0, 0, 1920, 1080)
        cx = button._computed_x + button._computed_w // 2
        cy = button._computed_y + button._computed_h // 2

        # Hover first
        root.handle_event(InputEvent(type="move", x=cx, y=cy))
        assert button.state == "hovered"

        # Click
        root.handle_event(InputEvent(type="click", x=cx, y=cy, button="left"))
        assert button.state == "pressed"

        # Release over button -> hovered
        root.handle_event(InputEvent(type="release", x=cx, y=cy, button="left"))
        assert button.state == "hovered"

    def test_click_release_outside_returns_normal(self, mock_game):
        button = Button("Test", width=200, height=40, anchor=Anchor.TOP_LEFT)
        root = _UIRoot(mock_game)
        root.add(button)
        root.compute_layout(0, 0, 1920, 1080)
        cx = button._computed_x + button._computed_w // 2
        cy = button._computed_y + button._computed_h // 2

        # Click on button
        root.handle_event(InputEvent(type="click", x=cx, y=cy, button="left"))
        assert button.state == "pressed"

        # Release far away -> normal
        root.handle_event(InputEvent(type="release", x=1900, y=1060, button="left"))
        assert button.state == "normal"

    def test_button_no_callback_still_clickable(self, mock_game):
        """Button with on_click=None should still change state."""
        button = Button("Test", on_click=None, width=200, height=40)
        root = _UIRoot(mock_game)
        root.add(button)
        root.compute_layout(0, 0, 1920, 1080)
        cx = button._computed_x + button._computed_w // 2
        cy = button._computed_y + button._computed_h // 2

        consumed = root.handle_event(
            InputEvent(type="click", x=cx, y=cy, button="left")
        )
        assert consumed is True
        assert button.state == "pressed"


class TestButtonRightClick:
    """Right click should NOT trigger button on_click."""

    def test_right_click_ignored(self, mock_game):
        clicked = []
        button = Button("Test", on_click=lambda: clicked.append(True), width=200, height=40)
        root = _UIRoot(mock_game)
        root.add(button)
        root.compute_layout(0, 0, 1920, 1080)
        cx = button._computed_x + button._computed_w // 2
        cy = button._computed_y + button._computed_h // 2

        root.handle_event(InputEvent(type="click", x=cx, y=cy, button="right"))
        assert len(clicked) == 0


class TestPanelHorizontalLayout:
    """Panel with HORIZONTAL layout positions children side by side."""

    def test_horizontal_children_positioned(self, mock_game):
        panel = Panel(width=600, height=100, layout=Layout.HORIZONTAL, spacing=10)
        b1 = Button("A", width=100, height=40)
        b2 = Button("B", width=100, height=40)
        panel.add(b1)
        panel.add(b2)

        root = _UIRoot(mock_game)
        root.add(panel)
        root.compute_layout(0, 0, 1920, 1080)

        # b2 should be to the right of b1
        assert b2._computed_x > b1._computed_x


class TestListSelection:
    """List selection and keyboard navigation."""

    def test_list_keyboard_selection(self, mock_game):
        selected = []
        lst = List(items=["A", "B", "C"], on_select=lambda i: selected.append(i))
        root = _UIRoot(mock_game)
        root.add(lst)
        root.compute_layout(0, 0, 1920, 1080)

        # Navigate down
        lst.on_event(InputEvent(type="key_press", action="down"))
        assert lst.selected_index == 0
        lst.on_event(InputEvent(type="key_press", action="down"))
        assert lst.selected_index == 1

    def test_list_selection_clamped(self, mock_game):
        lst = List(items=["A", "B"])
        lst.selected_index = 10
        assert lst.selected_index == 1  # clamped to last

    def test_list_selection_on_empty(self, mock_game):
        lst = List(items=[])
        lst.selected_index = 0
        assert lst.selected_index is None  # no items to select


class TestGridSelection:
    """Grid cell selection edge cases."""

    def test_grid_selection_clamped(self, mock_game):
        grid = Grid(columns=3, rows=3)
        grid.selected = (10, 10)
        assert grid.selected == (2, 2)  # clamped

    def test_grid_selection_on_zero_grid(self, mock_game):
        grid = Grid(columns=0, rows=0)
        grid.selected = (0, 0)
        assert grid.selected is None


class TestDataTableSelection:
    """DataTable selection and scrolling."""

    def test_datatable_selection_clamped(self, mock_game):
        dt = DataTable(columns=["A"], rows=[["x"], ["y"]], width=400)
        dt.selected_row = 100
        assert dt.selected_row == 1  # clamped to last row

    def test_datatable_selection_on_empty(self, mock_game):
        dt = DataTable(columns=["A"], rows=[], width=400)
        dt.selected_row = 0
        assert dt.selected_row is None

    def test_datatable_add_row(self, mock_game):
        dt = DataTable(columns=["A", "B"], width=400)
        dt.add_row(["x", "y"])
        assert dt.rows == [["x", "y"]]

    def test_datatable_clear_rows(self, mock_game):
        dt = DataTable(columns=["A"], rows=[["x"], ["y"]], width=400)
        dt.selected_row = 1
        dt.clear_rows()
        assert dt.rows == []
        assert dt.selected_row is None

    def test_datatable_row_with_fewer_cols_than_headers(self, mock_game):
        """Rows with fewer cells than column headers should render without crash."""
        dt = DataTable(columns=["A", "B", "C"], rows=[["x"]], width=400)
        root = _UIRoot(mock_game)
        root.add(dt)
        root.compute_layout(0, 0, 1920, 1080)
        dt.on_draw()  # Should not raise IndexError


class TestDataTableZeroColumns:
    """DataTable with zero columns."""

    def test_datatable_zero_columns(self, mock_game):
        dt = DataTable(columns=[], rows=[], width=400)
        root = _UIRoot(mock_game)
        root.add(dt)
        root.compute_layout(0, 0, 1920, 1080)
        dt.on_draw()


class TestTextBoxWordWrap:
    """TextBox word wrapping edge cases."""

    def test_textbox_single_long_word(self):
        tb = TextBox("a" * 500, width=100)
        # Should not crash; single long word placed on its own line
        w, h = tb.get_preferred_size()
        assert h > 0

    def test_textbox_newlines(self):
        tb = TextBox("Line1\nLine2\nLine3", width=400)
        w, h = tb.get_preferred_size()
        # Should have at least 3 lines of height
        assert h > 0


class TestTooltipNegativeDelay:
    """Tooltip with negative delay should raise ValueError."""

    def test_negative_delay_raises(self):
        import pytest
        with pytest.raises(ValueError, match="delay must be >= 0"):
            Tooltip("Test", delay=-1.0)


class TestTabGroupEmptyDraw:
    """TabGroup with 0 tabs drawing."""

    def test_tabgroup_zero_tabs_get_preferred_size(self):
        tg = TabGroup(tabs=None, width=400, height=300)
        w, h = tg.get_preferred_size()
        assert w == 400
        assert h == 300


class TestDragManagerEventInterception:
    """DragManager intercepts ALL events during drag."""

    def test_drag_intercepts_key_events(self, mock_game):
        from saga2d.scene import Scene

        class TestScene(Scene):
            pass

        scene = TestScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        source = Component(width=50, height=50, draggable=True, drag_data="x")
        scene.ui.add(source)
        source.compute_layout(10, 10, 50, 50)

        dm = scene.ui.drag_manager
        dm._start_drag(source, "x", 30, 30)

        # Key events should be consumed during drag
        result = dm.handle_event(InputEvent(type="key_press", key="a"))
        assert result is True  # swallowed

    def test_drag_cancel_via_escape(self, mock_game):
        from saga2d.scene import Scene

        class TestScene(Scene):
            pass

        scene = TestScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        source = Component(width=50, height=50, draggable=True, drag_data="x")
        scene.ui.add(source)
        source.compute_layout(10, 10, 50, 50)

        dm = scene.ui.drag_manager
        dm._start_drag(source, "x", 30, 30)
        assert dm.is_dragging is True

        # Cancel via escape action
        dm.handle_event(InputEvent(type="key_press", key="escape", action="cancel"))
        assert dm.is_dragging is False

    def test_drag_data_property(self, mock_game):
        from saga2d.scene import Scene

        class TestScene(Scene):
            pass

        scene = TestScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        source = Component(width=50, height=50, draggable=True, drag_data="payload")
        scene.ui.add(source)
        source.compute_layout(10, 10, 50, 50)

        dm = scene.ui.drag_manager
        assert dm.drag_data is None
        dm._start_drag(source, "payload", 30, 30)
        assert dm.drag_data == "payload"


class TestDragManagerGhostMovement:
    """Drag ghost follows mouse."""

    def test_ghost_follows_mouse(self, mock_game):
        from saga2d.scene import Scene

        class TestScene(Scene):
            pass

        scene = TestScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        source = Component(width=50, height=50, draggable=True, drag_data="x")
        scene.ui.add(source)
        source.compute_layout(10, 10, 50, 50)

        dm = scene.ui.drag_manager
        dm._start_drag(source, "x", 30, 30)

        # Move event
        dm.handle_event(InputEvent(type="move", x=200, y=200))
        session = dm._active
        assert session is not None
        # Ghost should have moved
        assert session.ghost_x != 10 or session.ghost_y != 10


class TestInputMultipleBindings:
    """Multiple bindings edge cases."""

    def test_rebind_same_key_same_action(self):
        im = InputManager()
        im.bind("confirm", "return")  # Already bound
        bindings = im.get_bindings()
        assert bindings["confirm"] == "return"

    def test_unbind_nonexistent_action(self):
        im = InputManager()
        # Should not raise
        im.unbind("nonexistent_action")


class TestAudioStopMusic:
    """Stop music clears state."""

    def test_stop_music(self, mock_game, tmp_path):
        music_file = tmp_path / "music" / "theme.ogg"
        music_file.parent.mkdir(parents=True, exist_ok=True)
        music_file.write_bytes(b"OggS" + b"\x00" * 100)

        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        audio.play_music("theme")
        assert mock_game._backend.music_playing is not None

        audio.stop_music()
        assert mock_game._backend.music_playing is None


class TestAudioVolumeAppliedToMusic:
    """Changing master/music volume re-applies to current player."""

    def test_volume_reapplied(self, mock_game, tmp_path):
        music_file = tmp_path / "music" / "theme.ogg"
        music_file.parent.mkdir(parents=True, exist_ok=True)
        music_file.write_bytes(b"OggS" + b"\x00" * 100)

        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        audio.play_music("theme")

        audio.set_volume("master", 0.5)
        # The music volume should be adjusted
        # master=0.5 * music=1.0 * base=1.0 = 0.5
        assert mock_game._backend.music_volume == pytest.approx(0.5)


class TestSoundPoolNoRepeat:
    """Sound pool avoids immediate repetition."""

    def test_pool_no_immediate_repeat(self, mock_game, tmp_path):
        sounds_dir = tmp_path / "sounds"
        sounds_dir.mkdir(parents=True, exist_ok=True)
        for i in range(3):
            (sounds_dir / f"s_{i}.wav").write_bytes(b"RIFF" + b"\x00" * 100)

        audio = AudioManager(mock_game._backend, AssetManager(mock_game._backend, tmp_path))
        audio.register_pool("test", ["s_0", "s_1", "s_2"])

        # Play many times and check no immediate repeats
        last_handle = None
        for _ in range(20):
            before = len(mock_game._backend.sounds_played)
            audio.play_pool("test")
            after = len(mock_game._backend.sounds_played)
            assert after == before + 1
            current_handle = mock_game._backend.sounds_played[-1]["handle"]
            if last_handle is not None:
                assert current_handle != last_handle, "Immediate repeat detected"
            last_handle = current_handle


class TestSaveOverwrite:
    """Saving to an existing slot overwrites data."""

    def test_overwrite_slot(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        sm.save(1, {"hp": 100}, "Scene")
        sm.save(1, {"hp": 50}, "Scene")

        loaded = sm.load(1)
        assert loaded["state"]["hp"] == 50


class TestSaveListSlotsMetadata:
    """list_slots includes slot number."""

    def test_list_slots_has_slot_key(self, tmp_path):
        sm = SaveManager(tmp_path / "saves")
        sm.save(2, {"x": 1}, "S")

        slots = sm.list_slots(3)
        assert slots[1] is not None
        assert slots[1]["slot"] == 2


class TestFSMSelfTransition:
    """FSM transition from state to itself."""

    def test_self_transition(self):
        log = []
        fsm = StateMachine(
            states=["a"],
            initial="a",
            transitions={"a": {"loop": "a"}},
            on_enter={"a": lambda: log.append("enter_a")},
            on_exit={"a": lambda: log.append("exit_a")},
        )
        log.clear()

        fsm.trigger("loop")
        # exit_a and enter_a should both fire
        assert log == ["exit_a", "enter_a"]
        assert fsm.state == "a"


class TestComponentHitTestBoundary:
    """Hit test at exact boundary pixels."""

    def test_hit_test_inside(self):
        c = Component(width=100, height=50)
        c._computed_x = 10
        c._computed_y = 20
        c._computed_w = 100
        c._computed_h = 50

        # Top-left corner (inclusive)
        assert c.hit_test(10, 20) is True
        # Just inside bottom-right (exclusive)
        assert c.hit_test(109, 69) is True
        # Exact bottom-right (exclusive -- should be outside)
        assert c.hit_test(110, 70) is False
        # Just outside
        assert c.hit_test(9, 20) is False
        assert c.hit_test(10, 19) is False


class TestProgressBarDrawRounded:
    """ProgressBar rounded mode drawing edge cases."""

    def test_very_narrow_bar(self, mock_game):
        """Bar narrower than height -- should still render."""
        bar = ProgressBar(value=50, max_value=100, width=10, height=24, rounded=True)
        root = _UIRoot(mock_game)
        root.add(bar)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()

    def test_rectangular_mode(self, mock_game):
        bar = ProgressBar(value=50, max_value=100, rounded=False)
        root = _UIRoot(mock_game)
        root.add(bar)
        root.compute_layout(0, 0, 1920, 1080)
        root.draw()


class TestTabGroupClickSwitching:
    """TabGroup tab switching via click event."""

    def test_tab_switch_via_click(self, mock_game):
        c1 = Label("Content 1")
        c2 = Label("Content 2")
        tg = TabGroup(
            tabs={"Tab1": c1, "Tab2": c2},
            width=400,
            height=300,
            anchor=Anchor.TOP_LEFT,
        )
        root = _UIRoot(mock_game)
        root.add(tg)
        root.compute_layout(0, 0, 1920, 1080)

        assert tg.active_tab == "Tab1"

        # The tab headers are at the top of the component.
        # We need to click on "Tab2" header area.
        # Tab widths are computed from text width + padding.
        # Let's compute where Tab2 starts.
        from saga2d.ui.components import _estimate_text_width
        from saga2d.ui.theme import Theme

        theme = Theme()
        resolved = theme.resolve_tabgroup_style(None)
        font_size = resolved.font_size
        padding = resolved.padding

        tab1_w = _estimate_text_width("Tab1", font_size) + 2 * padding
        # Click in the middle of Tab2 header
        click_x = tg._computed_x + tab1_w + 10
        click_y = tg._computed_y + tg._tab_height // 2

        root.handle_event(
            InputEvent(type="click", x=click_x, y=click_y, button="left")
        )
        assert tg.active_tab == "Tab2"


class TestListScrolling:
    """List scrolling behavior."""

    def test_scroll_clamp(self, mock_game):
        lst = List(items=["A", "B", "C"], height=30, item_height=30)
        root = _UIRoot(mock_game)
        root.add(lst)
        root.compute_layout(0, 0, 1920, 1080)

        # Only 1 item visible at a time (height=30, item_height=30)
        # Scroll should clamp
        lst._scroll_offset = 100
        lst._clamp_scroll()
        assert lst._scroll_offset <= 2  # max offset = 3 items - 1 visible


class TestWorldCoordsWithCamera:
    """World coordinate mapping with a mock camera."""

    def test_world_coords_with_camera(self):
        class FakeCamera:
            def screen_to_world(self, x, y):
                return (x + 100.0, y + 200.0)

        event = InputEvent(type="click", x=50, y=60, button="left")
        result = _with_world_coords(event, FakeCamera())
        assert result.world_x == 150.0
        assert result.world_y == 260.0


class TestDragManagerCancelActive:
    """Public cancel_active method."""

    def test_cancel_active(self, mock_game):
        from saga2d.scene import Scene

        class TestScene(Scene):
            pass

        scene = TestScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        source = Component(width=50, height=50, draggable=True, drag_data="x")
        scene.ui.add(source)
        source.compute_layout(10, 10, 50, 50)

        dm = scene.ui.drag_manager
        dm._start_drag(source, "x", 30, 30)
        assert dm.is_dragging is True

        dm.cancel_active()
        assert dm.is_dragging is False
