"""Edge-case tests for UI widget robustness.

Covers boundary conditions for List, Grid, TabGroup, ProgressBar,
Tooltip, TextBox, and DataTable widgets.  Tests are organised by widget
and numbered to match the specification.

Tests that expose KNOWN BUGS in the current code are marked with:
    # KNOWN BUG — expected to FAIL on current code
and use ``pytest.mark.xfail(reason=...)`` so the suite stays green
while clearly documenting the defects.

All other tests exercise currently-working behaviour and should PASS.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from saga2d import Game, Label, Scene
from saga2d.input import InputEvent
from saga2d.ui.component import Component
from saga2d.ui.widgets import (
    DataTable,
    Grid,
    List,
    ProgressBar,
    TabGroup,
    TextBox,
    Tooltip,
)


# =====================================================================
# Helpers
# =====================================================================


def _setup_widget(mock_game: Game, widget: Component) -> Scene:
    """Push a Scene, add *widget* to its UI, and run one layout pass.

    Returns the scene so tests can interact with it further.
    """
    scene = Scene()
    mock_game.push(scene)
    scene.ui.add(widget)
    scene.ui._ensure_layout()
    return scene


def _click_event(x: int, y: int) -> InputEvent:
    """Return a synthetic left-click InputEvent at (x, y)."""
    return InputEvent(type="click", button="left", x=x, y=y)


def _scroll_event(x: int, y: int, dy: int = 1) -> InputEvent:
    """Return a synthetic scroll InputEvent at (x, y)."""
    return InputEvent(type="scroll", x=x, y=y, dy=dy)


def _motion_event(x: int, y: int) -> InputEvent:
    """Return a synthetic motion InputEvent at (x, y)."""
    return InputEvent(type="motion", x=x, y=y)


def _key_event(action: str) -> InputEvent:
    """Return a synthetic key_press InputEvent with the given action."""
    return InputEvent(type="key_press", action=action)


# =====================================================================
# 1-8  List widget
# =====================================================================


class TestListItemHeightZero:
    """List(item_height=0) must not crash on any interaction."""

    # ------------------------------------------------------------------
    # Test 1: click should not crash (F24 fix: guard item_height <= 0)
    # ------------------------------------------------------------------
    def test_click_does_not_crash(self, mock_game: Game) -> None:
        """Test 1: Click on List(item_height=0) should not crash (F24 fix)."""
        lst = List(items=["a", "b", "c"], item_height=0, width=200, height=100)
        _setup_widget(mock_game, lst)
        # Click inside the widget bounds — previously triggered ZeroDivisionError.
        event = _click_event(x=lst._computed_x + 10, y=lst._computed_y + 10)
        lst.on_event(event)  # Should not crash after fix

    # ------------------------------------------------------------------
    # Test 2: scroll should not crash
    # ------------------------------------------------------------------
    def test_scroll_does_not_crash(self, mock_game: Game) -> None:
        """Test 2: Scroll on List(item_height=0) should not crash.

        _clamp_scroll calls _visible_count which guards item_height<=0
        and returns 0, so scroll path does not divide by zero.
        """
        lst = List(items=["a", "b", "c"], item_height=0, width=200, height=100)
        _setup_widget(mock_game, lst)
        event = _scroll_event(
            x=lst._computed_x + 10, y=lst._computed_y + 10, dy=3,
        )
        lst.on_event(event)  # Should not crash

    # ------------------------------------------------------------------
    # Test 3: motion should not crash (F24 fix: guard item_height <= 0)
    # ------------------------------------------------------------------
    def test_motion_does_not_crash(self, mock_game: Game) -> None:
        """Test 3: Motion over List(item_height=0) should not crash (F24 fix)."""
        lst = List(items=["a", "b", "c"], item_height=0, width=200, height=100)
        _setup_widget(mock_game, lst)
        event = _motion_event(x=lst._computed_x + 10, y=lst._computed_y + 10)
        lst.on_event(event)  # Should not crash after fix


class TestListEmptyItems:
    """List with no items should handle keyboard navigation gracefully."""

    # ------------------------------------------------------------------
    # Test 4: keyboard nav on empty list is no-op
    # ------------------------------------------------------------------
    def test_keyboard_nav_on_empty_list_is_noop(self, mock_game: Game) -> None:
        """Test 4: Up/down on an empty list should not change selection."""
        lst = List(items=[], width=200, height=100)
        _setup_widget(mock_game, lst)

        lst.on_event(_key_event("up"))
        assert lst.selected_index is None, "up on empty list should be no-op"

        lst.on_event(_key_event("down"))
        assert lst.selected_index is None, "down on empty list should be no-op"

    # ------------------------------------------------------------------
    # Test 5: items set to [] clears selection
    # ------------------------------------------------------------------
    def test_items_set_to_empty_clears_selection(self) -> None:
        """Test 5: Setting items to [] when there was a selection clears it."""
        lst = List(items=["alpha", "beta", "gamma"])
        lst._selected_index = 2
        lst.items = []
        assert lst.selected_index is None


class TestListScrollBeyondBounds:
    """List scroll offset must be clamped to valid range."""

    # ------------------------------------------------------------------
    # Test 6: scroll beyond bounds should clamp
    # ------------------------------------------------------------------
    def test_scroll_clamps_to_valid_range(self, mock_game: Game) -> None:
        """Test 6: Scroll offset clamps — never negative or past end."""
        lst = List(items=["a", "b", "c", "d", "e"], item_height=30,
                   width=200, height=60)
        _setup_widget(mock_game, lst)

        # Scroll way past the end.
        lst._scroll_offset = 1000
        lst._clamp_scroll()
        visible = lst._visible_count()
        max_offset = max(0, len(lst._items) - visible)
        assert lst._scroll_offset == max_offset

        # Scroll to negative.
        lst._scroll_offset = -50
        lst._clamp_scroll()
        assert lst._scroll_offset == 0


class TestListSelectedIndexSetter:
    """List.selected_index setter with out-of-range values."""

    # ------------------------------------------------------------------
    # Test 7: out-of-range selected_index is clamped
    # ------------------------------------------------------------------
    def test_out_of_range_positive(self) -> None:
        """Test 7a: selected_index larger than items count is clamped."""
        lst = List(items=["a", "b", "c"])
        lst.selected_index = 100
        assert lst.selected_index == 2  # clamped to len-1

    def test_out_of_range_negative(self) -> None:
        """Test 7b: selected_index negative is clamped to 0."""
        lst = List(items=["a", "b", "c"])
        lst.selected_index = -5
        assert lst.selected_index == 0  # clamped to 0

    def test_selected_index_none_on_empty(self) -> None:
        """Test 7c: selected_index on empty list becomes None."""
        lst = List(items=[])
        lst.selected_index = 3
        assert lst.selected_index is None


class TestListVisibleCountZeroHeight:
    """List._visible_count() with item_height=0."""

    # ------------------------------------------------------------------
    # Test 8: _visible_count returns 0 when item_height=0
    # ------------------------------------------------------------------
    def test_visible_count_zero_item_height(self) -> None:
        """Test 8: _visible_count() returns 0 when item_height=0."""
        lst = List(items=["a", "b"], item_height=0, width=200, height=100)
        assert lst._visible_count() == 0


# =====================================================================
# 9-13  Grid widget
# =====================================================================


class TestGridZeroDimensions:
    """Grid with 0 columns and/or 0 rows."""

    # ------------------------------------------------------------------
    # Test 9: Grid(0, 0) should not crash on draw
    # ------------------------------------------------------------------
    def test_zero_grid_draw_no_crash(self, mock_game: Game) -> None:
        """Test 9: Grid(0, 0) draws without error (range(0) loops)."""
        grid = Grid(0, 0)
        _setup_widget(mock_game, grid)
        grid.on_draw()  # Should not crash — loops iterate range(0)

    # ------------------------------------------------------------------
    # Test 10: selected setter handles 0 columns gracefully
    # ------------------------------------------------------------------
    def test_selected_setter_zero_columns(self) -> None:
        """Test 10: Grid(0, 0).selected = (0,0) sets to None."""
        grid = Grid(0, 0)
        grid.selected = (0, 0)
        assert grid.selected is None, (
            "Grid with 0 columns should refuse selection"
        )

    def test_selected_setter_zero_columns_positive_rows(self) -> None:
        """Test 10b: Grid(0, 5).selected = (0,0) still sets to None."""
        grid = Grid(0, 5)
        grid.selected = (0, 0)
        assert grid.selected is None


class TestGridCellAtZeroSize:
    """Grid._cell_at with cell_size (0, 0)."""

    # ------------------------------------------------------------------
    # Test 11: _cell_at returns None, does not crash
    # ------------------------------------------------------------------
    def test_cell_at_zero_size_returns_none(self) -> None:
        """Test 11: _cell_at with cell_size=(0,0) returns None, not crash.

        cell_stride_x = 0 + spacing = spacing.  If spacing > 0 stride
        is non-zero and the guard ``cell_stride <= 0`` doesn't trigger.
        But if spacing is also 0, stride is 0 and the guard returns None.
        """
        grid = Grid(3, 3, cell_size=(0, 0), spacing=0)
        grid._computed_x = 0
        grid._computed_y = 0
        grid._computed_w = 100
        grid._computed_h = 100
        result = grid._cell_at(10, 10)
        assert result is None, (
            "_cell_at with cell_size=(0,0) and spacing=0 should return None"
        )

    def test_cell_at_zero_cell_size_nonzero_spacing(self) -> None:
        """Test 11b: cell_size=(0,0) but spacing>0 — stride is spacing,
        division works but click falls in spacing gap, returns None.
        """
        grid = Grid(3, 3, cell_size=(0, 0), spacing=4)
        grid._computed_x = 0
        grid._computed_y = 0
        grid._computed_w = 100
        grid._computed_h = 100
        # With cell_w=0, any click lands in the "spacing" area (rx - col*stride >= cell_w=0)
        # Actually rx - col*stride >= 0 >= 0, so it passes. But cell_w=0 means
        # the cell has zero width — the check ``rx - col*stride >= self._cell_w``
        # i.e. ``something >= 0`` is always True, so it falls through to the
        # spacing check. Actually reading the code:
        #   if rx - col * cell_stride_x >= self._cell_w:  =>  if something >= 0
        #   That's always True, so return None.
        result = grid._cell_at(10, 10)
        assert result is None


class TestGridSetCellOutOfBounds:
    """Grid.set_cell with out-of-bounds coordinates."""

    # ------------------------------------------------------------------
    # Test 12: set_cell with out-of-bounds coords
    # ------------------------------------------------------------------
    def test_set_cell_out_of_bounds_stores_component(self) -> None:
        """Test 12: set_cell with coords outside (columns, rows) is allowed.

        The set_cell method does not validate bounds — it simply stores
        the component in the _cells dict at any (col, row) key.
        The cell will never be drawn (on_draw iterates range(rows/cols))
        and _cell_at won't return it, but it doesn't crash.
        """
        grid = Grid(2, 2)
        lbl = Label("out of bounds")
        grid.set_cell(10, 10, lbl)
        assert grid.get_cell(10, 10) is lbl
        # Cell is stored but won't be drawn/selectable.

    def test_set_cell_negative_coords(self) -> None:
        """Test 12b: set_cell with negative coords is allowed (stored, not drawn)."""
        grid = Grid(2, 2)
        lbl = Label("negative")
        grid.set_cell(-1, -1, lbl)
        assert grid.get_cell(-1, -1) is lbl


class TestGridPreferredSizeZero:
    """Grid.get_preferred_size with 0 columns/rows."""

    # ------------------------------------------------------------------
    # Test 13: get_preferred_size with 0 columns/rows
    # ------------------------------------------------------------------
    def test_preferred_size_zero_dims(self) -> None:
        """Test 13: Grid(0,0) preferred size is just 2*padding."""
        grid = Grid(0, 0)
        w, h = grid.get_preferred_size()
        # 0 * cell_w + max(0, -1) * spacing + 2 * padding
        # = 0 + 0 + 2 * padding
        assert w >= 0
        assert h >= 0
        # Both w and h should be small (just padding).
        assert w < 100, f"Expected small width, got {w}"
        assert h < 100, f"Expected small height, got {h}"


# =====================================================================
# 14-17  TabGroup widget
# =====================================================================


class TestTabGroupEmpty:
    """TabGroup with no tabs."""

    # ------------------------------------------------------------------
    # Test 14: empty TabGroup should not crash on draw/update
    # ------------------------------------------------------------------
    def test_empty_draw_no_crash(self, mock_game: Game) -> None:
        """Test 14a: Drawing an empty TabGroup does not crash."""
        tg = TabGroup()
        _setup_widget(mock_game, tg)
        tg.on_draw()  # Should not crash — iterates empty _tab_labels

    def test_empty_update_no_crash(self) -> None:
        """Test 14b: Updating an empty TabGroup does not crash."""
        tg = TabGroup()
        tg.update(0.016)  # Base Component.update — no-op

    def test_empty_preferred_size(self) -> None:
        """Test 14c: get_preferred_size on empty TabGroup returns reasonable values."""
        tg = TabGroup()
        w, h = tg.get_preferred_size()
        assert w >= 0
        assert h >= 0


class TestTabGroupInvalidKey:
    """TabGroup.select_tab with invalid key."""

    # ------------------------------------------------------------------
    # Test 15: select_tab with invalid key raises KeyError
    # ------------------------------------------------------------------
    def test_select_tab_invalid_key(self) -> None:
        """Test 15: select_tab('nonexistent') raises KeyError."""
        tg = TabGroup(tabs={"A": Label("a"), "B": Label("b")})
        with pytest.raises(KeyError, match="No tab named 'nonexistent'"):
            tg.select_tab("nonexistent")

    def test_select_tab_invalid_key_empty_tabgroup(self) -> None:
        """Test 15b: select_tab on empty TabGroup raises KeyError."""
        tg = TabGroup()
        with pytest.raises(KeyError, match="No tab named"):
            tg.select_tab("anything")


class TestTabGroupAddRemove:
    """TabGroup add then remove tab."""

    # ------------------------------------------------------------------
    # Test 16: add then remove tab
    # ------------------------------------------------------------------
    def test_add_then_remove_tab(self) -> None:
        """Test 16: After adding a tab, removing it via the component tree works.

        TabGroup has no explicit remove_tab() method.  We can remove
        the tab's component from the tree manually and update internal state.
        Since there is no public remove_tab API, we test that removing
        the underlying component from children doesn't crash, and that
        the tab still exists in _tab_components (it's not cleaned up).
        """
        tg = TabGroup()
        lbl = Label("content")
        tg.add_tab("TestTab", lbl)
        assert tg.active_tab == "TestTab"
        assert "TestTab" in tg.tab_labels

        # Remove the component from the tree (no remove_tab API exists).
        tg.remove(lbl)
        # The tab label is still tracked internally — there's no cleanup.
        assert "TestTab" in tg.tab_labels
        assert tg.get_tab_content("TestTab") is lbl


class TestTabGroupSingleTab:
    """TabGroup with a single tab."""

    # ------------------------------------------------------------------
    # Test 17: single tab auto-activates and draws
    # ------------------------------------------------------------------
    def test_single_tab(self, mock_game: Game) -> None:
        """Test 17: A single-tab TabGroup activates that tab and draws."""
        lbl = Label("only tab")
        tg = TabGroup(tabs={"Solo": lbl})
        assert tg.active_tab == "Solo"
        assert lbl.visible is True
        assert tg.tab_labels == ["Solo"]

        _setup_widget(mock_game, tg)
        tg.on_draw()  # Should not crash


# =====================================================================
# 18-22  ProgressBar widget
# =====================================================================


class TestProgressBarMaxZero:
    """ProgressBar with max_value=0."""

    # ------------------------------------------------------------------
    # Test 18: fraction should be 0.0
    # ------------------------------------------------------------------
    def test_fraction_zero_max(self) -> None:
        """Test 18: max_value=0 yields fraction 0.0."""
        bar = ProgressBar(value=50, max_value=0)
        assert bar.fraction == 0.0

    def test_fraction_zero_max_zero_value(self) -> None:
        """Test 18b: value=0, max_value=0 yields fraction 0.0."""
        bar = ProgressBar(value=0, max_value=0)
        assert bar.fraction == 0.0


class TestProgressBarNaN:
    """ProgressBar with value=NaN."""

    # ------------------------------------------------------------------
    # Test 19: value=NaN — fraction is misleading (known quirk)
    # ------------------------------------------------------------------
    def test_nan_value_fraction(self) -> None:
        """Test 19: value=NaN produces a misleading fraction due to CPython
        min/max behaviour with NaN.

        NaN / 100 = NaN.  min(1.0, NaN) -> 1.0, max(0.0, 1.0) -> 1.0.
        So fraction is 1.0 (bar looks full) — a silent bug / quirk.
        """
        bar = ProgressBar(value=float("nan"), max_value=100)
        frac = bar.fraction
        # CPython: min(1.0, NaN) -> 1.0 (returns first arg when NaN is involved)
        assert frac == 1.0, (
            f"Expected 1.0 (CPython NaN quirk), got {frac}"
        )


class TestProgressBarNegativeMax:
    """ProgressBar with negative max_value."""

    # ------------------------------------------------------------------
    # Test 20: negative max_value — fraction is 0.0
    # ------------------------------------------------------------------
    def test_negative_max_fraction(self) -> None:
        """Test 20: max_value < 0 yields fraction 0.0 (guarded)."""
        bar = ProgressBar(value=50, max_value=-10)
        assert bar.fraction == 0.0


class TestProgressBarValueExceedsMax:
    """ProgressBar with value > max_value."""

    # ------------------------------------------------------------------
    # Test 21: value > max_value — fraction clamps to 1.0
    # ------------------------------------------------------------------
    def test_value_exceeds_max(self) -> None:
        """Test 21: value > max_value is clamped to fraction 1.0."""
        bar = ProgressBar(value=200, max_value=100)
        assert bar.fraction == 1.0


class TestProgressBarRoundedNarrow:
    """ProgressBar rounded=True with very narrow width."""

    # ------------------------------------------------------------------
    # Test 22: rounded with width < height should not crash
    # ------------------------------------------------------------------
    def test_rounded_narrow_draw(self, mock_game: Game) -> None:
        """Test 22: Rounded ProgressBar with width < height draws safely.

        The _draw_rounded method handles this via the ``else`` branch:
        'Very narrow bar, just draw circle'.
        """
        bar = ProgressBar(
            value=50, max_value=100, width=10, height=30, rounded=True,
        )
        _setup_widget(mock_game, bar)
        bar.on_draw()  # Should not crash

    def test_rounded_zero_width_draw(self, mock_game: Game) -> None:
        """Test 22b: Rounded ProgressBar with width=0 draws safely."""
        bar = ProgressBar(
            value=50, max_value=100, width=0, height=24, rounded=True,
        )
        _setup_widget(mock_game, bar)
        bar.on_draw()  # Should not crash


# =====================================================================
# 23-26  Tooltip widget
# =====================================================================


class TestTooltipDelayZero:
    """Tooltip with delay=0."""

    # ------------------------------------------------------------------
    # Test 23: delay=0 should show immediately
    # ------------------------------------------------------------------
    def test_delay_zero_shows_immediately(self) -> None:
        """Test 23: Tooltip(delay=0) becomes visible on show() without update()."""
        tip = Tooltip("Instant", delay=0)
        tip.show(100, 100)
        assert tip._visible_now is True, (
            "Tooltip with delay=0 should be visible immediately after show()"
        )


class TestTooltipNegativeDelay:
    """Tooltip with negative delay."""

    # ------------------------------------------------------------------
    # Test 24: negative delay should show immediately
    # ------------------------------------------------------------------
    def test_negative_delay_shows_immediately(self) -> None:
        """Test 24: Tooltip(delay=-1) becomes visible on show() immediately."""
        tip = Tooltip("Negative delay", delay=-1.0)
        tip.show(100, 100)
        assert tip._visible_now is True, (
            "Tooltip with negative delay should show immediately"
        )


class TestTooltipShowHideShow:
    """Tooltip show(), hide(), show() — timer should restart."""

    # ------------------------------------------------------------------
    # Test 25: show/hide/show restarts the timer
    # ------------------------------------------------------------------
    def test_show_hide_show_restarts_timer(self) -> None:
        """Test 25: After show/hide/show, delay timer resets to zero."""
        tip = Tooltip("Restart test", delay=1.0)

        # First show — start the timer.
        tip.show(10, 10)
        assert tip._showing is True
        assert tip._visible_now is False
        assert tip._timer == 0.0

        # Advance partway through the delay.
        tip.update(0.5)
        assert tip._timer == 0.5
        assert tip._visible_now is False

        # Hide — resets everything.
        tip.hide()
        assert tip._showing is False
        assert tip._visible_now is False
        assert tip._timer == 0.0

        # Show again — timer should restart from 0.
        tip.show(20, 20)
        assert tip._showing is True
        assert tip._visible_now is False
        assert tip._timer == 0.0

        # Full delay needed again.
        tip.update(0.5)
        assert tip._visible_now is False
        tip.update(0.5)
        assert tip._visible_now is True


class TestTooltipLargeDt:
    """Tooltip update with very large dt."""

    # ------------------------------------------------------------------
    # Test 26: very large dt makes tooltip visible in one update
    # ------------------------------------------------------------------
    def test_large_dt_shows_tooltip(self) -> None:
        """Test 26: update(1e9) should make the tooltip visible in one call."""
        tip = Tooltip("Big dt", delay=0.5)
        tip.show(0, 0)
        tip.update(1_000_000_000.0)
        assert tip._visible_now is True

    def test_large_dt_no_crash(self) -> None:
        """Test 26b: Very large dt does not cause overflow or crash."""
        tip = Tooltip("Huge dt", delay=0.5)
        tip.show(0, 0)
        tip.update(float("inf"))
        # inf >= 0.5 is True, so tooltip becomes visible.
        assert tip._visible_now is True


# =====================================================================
# 27-31  TextBox widget
# =====================================================================


class TestTextBoxTypewriterShorterText:
    """TextBox with typewriter and text changed to shorter string."""

    # ------------------------------------------------------------------
    # Test 27: text changed to shorter string resets typewriter
    # ------------------------------------------------------------------
    def test_text_changed_to_shorter(self) -> None:
        """Test 27: Changing text to a shorter string resets typewriter to 0."""
        tb = TextBox("Hello World", typewriter_speed=10)
        tb.update(1.0)  # Reveal 10 chars
        assert tb.revealed_count == 10

        tb.text = "Hi"  # Shorter text
        assert tb.revealed_count == 0, (
            "Typewriter should reset when text changes"
        )
        assert tb.is_complete is False


class TestTextBoxTypewriterEmptyText:
    """TextBox with typewriter and text changed to empty string."""

    # ------------------------------------------------------------------
    # Test 28: text changed to empty string
    # ------------------------------------------------------------------
    def test_text_changed_to_empty(self) -> None:
        """Test 28: Changing text to '' resets typewriter and is_complete."""
        tb = TextBox("Some text", typewriter_speed=10)
        tb.update(1.0)
        assert tb.is_complete is True

        tb.text = ""
        # typewriter_speed > 0, so _revealed_count = 0.0
        # But len("") == 0, so is_complete: 0 >= 0 is True
        assert tb.is_complete is True
        assert tb.revealed_count == 0


class TestTextBoxEmptyTextInitial:
    """TextBox with empty text initial."""

    # ------------------------------------------------------------------
    # Test 29: empty text from the start
    # ------------------------------------------------------------------
    def test_empty_text_initial_instant(self) -> None:
        """Test 29a: TextBox('') with instant reveal is complete."""
        tb = TextBox("")
        assert tb.text == ""
        assert tb.is_complete is True
        assert tb.revealed_count == 0

    def test_empty_text_initial_typewriter(self) -> None:
        """Test 29b: TextBox('', typewriter_speed=10) is complete (0 >= 0)."""
        tb = TextBox("", typewriter_speed=10)
        assert tb.is_complete is True
        assert tb.revealed_count == 0


class TestTextBoxNegativeTypewriterSpeed:
    """TextBox with negative typewriter_speed."""

    # ------------------------------------------------------------------
    # Test 30: negative speed is treated as instant
    # ------------------------------------------------------------------
    def test_negative_speed_instant_reveal(self) -> None:
        """Test 30: typewriter_speed < 0 is treated as instant (all visible)."""
        tb = TextBox("ABCDE", typewriter_speed=-5)
        assert tb.is_complete is True
        assert tb.revealed_count == 5

    def test_negative_speed_update_noop(self) -> None:
        """Test 30b: update() is a no-op when typewriter_speed <= 0."""
        tb = TextBox("ABCDE", typewriter_speed=-5)
        initial_count = tb._revealed_count
        tb.update(1.0)
        assert tb._revealed_count == initial_count, (
            "update() should be a no-op for negative typewriter_speed"
        )


class TestTextBoxZeroWidth:
    """TextBox with width=0."""

    # ------------------------------------------------------------------
    # Test 31: zero width should not crash
    # ------------------------------------------------------------------
    def test_zero_width_draw(self, mock_game: Game) -> None:
        """Test 31: TextBox with width=0 draws without crashing.

        _word_wrap returns [text] when max_width <= 0, so no crash.
        """
        tb = TextBox("Hello World", width=0)
        _setup_widget(mock_game, tb)
        tb.on_draw()  # Should not crash

    def test_zero_width_preferred_size(self) -> None:
        """Test 31b: get_preferred_size with width=0 falls back to 300.

        TextBox.get_preferred_size uses ``self._width or 300``, so
        width=0 is falsy and triggers the 300 fallback.  This is
        arguably a quirk, not a crash.
        """
        tb = TextBox("Hello", width=0)
        w, h = tb.get_preferred_size()
        # width=0 is falsy, so ``self._width or 300`` returns 300.
        assert w == 300, f"Expected 300 (fallback for falsy width), got {w}"


# =====================================================================
# 32-33  DataTable widget
# =====================================================================


class TestDataTableEmptyRows:
    """DataTable with empty rows."""

    # ------------------------------------------------------------------
    # Test 32: empty rows should draw without crash
    # ------------------------------------------------------------------
    def test_empty_rows_draw(self, mock_game: Game) -> None:
        """Test 32: DataTable with 0 rows draws header, no data rows."""
        dt = DataTable(
            columns=["Name", "Score"],
            rows=[],
            width=400,
            height=200,
        )
        _setup_widget(mock_game, dt)
        dt.on_draw()  # Should draw header only, not crash

    def test_empty_rows_selected_row(self) -> None:
        """Test 32b: selected_row on empty table stays None."""
        dt = DataTable(columns=["A"], rows=[])
        dt.selected_row = 5
        assert dt.selected_row is None

    def test_empty_rows_keyboard_nav(self) -> None:
        """Test 32c: Keyboard nav on empty DataTable is no-op."""
        dt = DataTable(columns=["A"], rows=[])
        dt.on_event(_key_event("down"))
        assert dt.selected_row is None
        dt.on_event(_key_event("up"))
        assert dt.selected_row is None


class TestDataTableEmptyColumns:
    """DataTable with empty columns."""

    # ------------------------------------------------------------------
    # Test 33a: empty columns should draw without crash
    # ------------------------------------------------------------------
    def test_empty_columns_draw(self, mock_game: Game) -> None:
        """Test 33: DataTable with 0 columns draws without crash."""
        dt = DataTable(
            columns=[],
            rows=[],
            width=400,
            height=200,
        )
        _setup_widget(mock_game, dt)
        dt.on_draw()  # range(0) → no column iteration

    def test_empty_columns_with_data_draw(self, mock_game: Game) -> None:
        """Test 33b: DataTable with 0 columns but data rows draws safely."""
        dt = DataTable(
            columns=[],
            rows=[["orphan"]],
            width=400,
            height=200,
        )
        _setup_widget(mock_game, dt)
        dt.on_draw()  # Iterates data rows but range(0) cols → no cell text


class TestDataTableClickEmptyTable:
    """DataTable click on empty table."""

    # ------------------------------------------------------------------
    # Test 33c: click on empty table is handled gracefully
    # ------------------------------------------------------------------
    def test_click_on_empty_table(self, mock_game: Game) -> None:
        """Test 33 (click): Clicking an empty DataTable does not crash."""
        dt = DataTable(
            columns=["A", "B"],
            rows=[],
            width=400,
            height=200,
        )
        _setup_widget(mock_game, dt)
        event = _click_event(
            x=dt._computed_x + 10, y=dt._computed_y + 50,
        )
        dt.on_event(event)  # Should not crash
        assert dt.selected_row is None, (
            "Click on empty table should not select anything"
        )
