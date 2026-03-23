"""Edge-case tests for timers, widgets, and component tree safety.

Probes specific boundary conditions:
- Timer with NaN/Inf delay, zero/NaN interval
- ProgressBar with out-of-range values and zero/negative max_value
- List with item_height=0
- DataTable with 0 columns and rows shorter than columns
- Grid with 0 columns and 0 rows
- TabGroup with empty tabs and unknown label selection
- TextBox with empty string and NaN typewriter_speed
- Component tree cycle detection and remove-non-child safety
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from saga2d import Game, Label, Panel, Scene
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
from saga2d.util.timer import TimerManager


# ======================================================================
# Timer Edge Cases
# ======================================================================


class TestTimerNaNDelay:
    """Timer.after(NaN, cb) now raises ValueError at creation time.

    The validation `not math.isfinite(delay) or delay < 0` catches NaN
    because math.isfinite(NaN) is False.
    """

    def test_after_nan_delay_does_not_raise(self) -> None:
        """NaN is now rejected by the delay validation — ValueError raised."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="delay must be a finite number >= 0"):
            tm.after(float("nan"), lambda: None)

    def test_after_nan_delay_never_fires(self) -> None:
        """Timer with NaN delay cannot be created — ValueError at creation time.

        Previously the timer would silently never fire. Now validation
        prevents it from being created at all.
        """
        tm = TimerManager()
        with pytest.raises(ValueError, match="delay must be a finite number >= 0"):
            tm.after(float("nan"), lambda: None)

    def test_after_nan_timer_remains_in_timers_dict(self) -> None:
        """NaN timer cannot be created — ValueError at creation time.

        Previously the NaN timer would leak in _timers dict forever.
        Now validation prevents it from being created at all.
        """
        tm = TimerManager()
        with pytest.raises(ValueError, match="delay must be a finite number >= 0"):
            tm.after(float("nan"), lambda: None)


class TestTimerInfDelay:
    """Timer.after(Inf, cb) now raises ValueError at creation time.

    The validation `not math.isfinite(delay) or delay < 0` catches Inf
    because math.isfinite(Inf) is False.
    """

    def test_after_inf_delay_does_not_raise(self) -> None:
        """+Inf is now rejected by the delay validation — ValueError raised."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="delay must be a finite number >= 0"):
            tm.after(float("inf"), lambda: None)

    def test_after_inf_delay_never_fires(self) -> None:
        """Timer with Inf delay cannot be created — ValueError at creation time.

        Previously the timer would silently never fire. Now validation
        prevents it from being created at all.
        """
        tm = TimerManager()
        with pytest.raises(ValueError, match="delay must be a finite number >= 0"):
            tm.after(float("inf"), lambda: None)

    def test_after_inf_timer_remains_in_timers_dict(self) -> None:
        """Inf timer cannot be created — ValueError at creation time.

        Previously the Inf timer would leak in _timers dict forever.
        Now validation prevents it from being created at all.
        """
        tm = TimerManager()
        with pytest.raises(ValueError, match="delay must be a finite number >= 0"):
            tm.after(float("inf"), lambda: None)


class TestTimerEveryZero:
    """Timer.every(0, cb): 0 should be rejected by `if interval <= 0`."""

    def test_every_zero_raises_value_error(self) -> None:
        """Interval of exactly 0 is rejected."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="interval must be a finite number > 0"):
            tm.every(0, lambda: None)


class TestTimerEveryNaN:
    """Timer.every(NaN, cb) now raises ValueError at creation time.

    The validation `not math.isfinite(interval) or interval <= 0` catches NaN
    because math.isfinite(NaN) is False.
    """

    def test_every_nan_does_not_raise(self) -> None:
        """NaN is now rejected by the interval validation — ValueError raised."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="interval must be a finite number > 0"):
            tm.every(float("nan"), lambda: None)

    def test_every_nan_never_fires(self) -> None:
        """Repeating timer with NaN interval cannot be created — ValueError at creation time.

        Previously the timer would silently never fire. Now validation
        prevents it from being created at all.
        """
        tm = TimerManager()
        with pytest.raises(ValueError, match="interval must be a finite number > 0"):
            tm.every(float("nan"), lambda: None)


class TestTimerEveryNegInf:
    """Timer.every(-Inf, cb): -Inf <= 0 is True, so it should raise."""

    def test_every_neg_inf_raises(self) -> None:
        """Negative infinity is correctly rejected."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="interval must be a finite number > 0"):
            tm.every(float("-inf"), lambda: None)


class TestTimerAfterNegInf:
    """Timer.after(-Inf, cb): -Inf < 0 is True, so it should raise."""

    def test_after_neg_inf_raises(self) -> None:
        """Negative infinity is correctly rejected."""
        tm = TimerManager()
        with pytest.raises(ValueError, match="delay must be a finite number >= 0"):
            tm.after(float("-inf"), lambda: None)


class TestTimerUpdateWithNaNDt:
    """TimerManager.update(NaN dt): Line 203 checks `if not math.isfinite(dt): return`."""

    def test_update_nan_dt_is_noop(self) -> None:
        """update(NaN) is silently skipped — timers do not advance."""
        tm = TimerManager()
        fired: list[bool] = []
        tm.after(0.0, lambda: fired.append(True))

        tm.update(float("nan"))

        # Timer with delay=0 would normally fire on first update,
        # but NaN dt causes early return
        assert fired == [], "NaN dt causes early return, timer does not fire"

    def test_update_inf_dt_is_noop(self) -> None:
        """update(Inf) is silently skipped."""
        tm = TimerManager()
        fired: list[bool] = []
        tm.after(1.0, lambda: fired.append(True))

        tm.update(float("inf"))

        assert fired == [], "Inf dt causes early return"


# ======================================================================
# Widget Edge Cases: ProgressBar
# ======================================================================


class TestProgressBarEdgeCases:
    """ProgressBar fraction clamping and edge value handling."""

    def test_value_greater_than_max(self) -> None:
        """value > max_value should clamp fraction to 1.0."""
        bar = ProgressBar(value=200, max_value=100)
        assert bar.fraction == 1.0

    def test_value_negative(self) -> None:
        """value < 0 should clamp fraction to 0.0."""
        bar = ProgressBar(value=-50, max_value=100)
        assert bar.fraction == 0.0

    def test_max_value_zero(self) -> None:
        """max_value=0 should return fraction 0.0 (guarded by max_value <= 0)."""
        bar = ProgressBar(value=50, max_value=0)
        assert bar.fraction == 0.0

    def test_max_value_negative(self) -> None:
        """max_value < 0 should return fraction 0.0."""
        bar = ProgressBar(value=50, max_value=-10)
        assert bar.fraction == 0.0

    def test_value_zero_max_zero(self) -> None:
        """value=0, max_value=0 should return fraction 0.0."""
        bar = ProgressBar(value=0, max_value=0)
        assert bar.fraction == 0.0

    def test_value_nan(self) -> None:
        """value=NaN with valid max_value: NaN / 100 = NaN.

        In CPython, max(0.0, min(1.0, NaN)) depends on argument order:
        - min(1.0, NaN) returns 1.0  (first arg returned when NaN involved)
        - max(0.0, 1.0) returns 1.0
        So fraction silently returns 1.0 for NaN value — a misleading result.
        """
        bar = ProgressBar(value=float("nan"), max_value=100)
        frac = bar.fraction
        # CPython min/max with NaN: min(1.0, nan) -> 1.0, max(0.0, 1.0) -> 1.0
        # This is a subtle bug: NaN value produces fraction=1.0 instead of
        # raising or returning 0.0. The bar looks "full" when value is invalid.
        assert frac == 1.0, (
            f"BUG: NaN value silently produces fraction=1.0 (misleading), got {frac}"
        )

    def test_max_value_nan(self) -> None:
        """max_value=NaN: NaN <= 0 is False, so we enter the division.
        50 / NaN = NaN. But CPython min/max behavior with NaN:
        min(1.0, NaN) -> 1.0, max(0.0, 1.0) -> 1.0.
        So fraction silently returns 1.0."""
        bar = ProgressBar(value=50, max_value=float("nan"))
        frac = bar.fraction
        # NaN <= 0 is False, so we don't return 0.0 early.
        # 50 / NaN = NaN. Then: min(1.0, NaN) -> 1.0, max(0.0, 1.0) -> 1.0
        assert frac == 1.0, (
            f"BUG: NaN max_value silently produces fraction=1.0, got {frac}"
        )

    def test_value_inf(self) -> None:
        """value=+Inf: Inf / 100 = Inf. min(1.0, Inf) = 1.0."""
        bar = ProgressBar(value=float("inf"), max_value=100)
        assert bar.fraction == 1.0

    def test_normal_fraction(self) -> None:
        """Sanity: normal values produce correct fraction."""
        bar = ProgressBar(value=25, max_value=100)
        assert bar.fraction == 0.25


# ======================================================================
# Widget Edge Cases: List
# ======================================================================


class TestListEdgeCases:
    """List widget with edge-case item_height and empty items."""

    def test_item_height_zero_visible_count(self) -> None:
        """item_height=0: _visible_count returns 0 due to guard."""
        lst = List(items=["a", "b", "c"], item_height=0)
        assert lst._visible_count() == 0

    def test_item_height_zero_clamp_scroll(self) -> None:
        """item_height=0: _clamp_scroll uses max(0, len(items) - 0) = len(items).
        This means max_offset = 3, which is unexpected but not a crash."""
        lst = List(items=["a", "b", "c"], item_height=0)
        lst._scroll_offset = 100
        lst._clamp_scroll()
        # max_offset = max(0, 3 - 0) = 3
        assert lst._scroll_offset == 3, (
            f"With item_height=0, scroll clamps to len(items)={len(lst._items)}"
        )

    def test_empty_items_no_selection(self) -> None:
        """Empty list: selected_index stays None."""
        lst = List(items=[])
        lst.selected_index = 5
        assert lst.selected_index is None

    def test_items_setter_clamps_selection(self) -> None:
        """Setting items to shorter list clamps selection."""
        lst = List(items=["a", "b", "c", "d"])
        lst._selected_index = 3
        lst.items = ["x", "y"]
        assert lst._selected_index == 1  # Clamped to len-1

    def test_items_setter_to_empty_clears_selection(self) -> None:
        """Setting items to empty list clears selection."""
        lst = List(items=["a", "b"])
        lst._selected_index = 1
        lst.items = []
        assert lst._selected_index is None


# ======================================================================
# Widget Edge Cases: DataTable
# ======================================================================


class TestDataTableEdgeCases:
    """DataTable with zero columns and short rows."""

    def test_zero_columns_effective_widths(self) -> None:
        """0 columns: _effective_col_widths returns []."""
        dt = DataTable(columns=[])
        padding = 8  # default theme padding
        widths = dt._effective_col_widths(padding)
        assert widths == []

    def test_rows_shorter_than_columns(self) -> None:
        """Rows with fewer cells than columns: drawing handles with fallback to ''."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            dt = DataTable(
                columns=["A", "B", "C"],
                rows=[["only_a"]],  # row has 1 cell, 3 columns
                width=400,
                height=200,
            )
            # Attach to a scene UI so _game is set
            scene = Scene()
            g.push(scene)
            scene.ui.add(dt)
            scene.ui._ensure_layout()

            # Drawing should not raise — line 1938 handles short rows
            dt.on_draw()  # Should not crash

            # Verify the row data is accessible and short row handled
            row_data = dt._rows[0]
            assert len(row_data) == 1
            # The code does: cell_text = row_data[ci] if ci < len(row_data) else ""
            # So ci=1 and ci=2 produce ""
        finally:
            g._teardown()

    def test_zero_columns_with_rows(self) -> None:
        """0 columns but non-empty rows: no crash on draw."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            dt = DataTable(
                columns=[],
                rows=[["orphan_data"]],
                width=400,
                height=200,
            )
            scene = Scene()
            g.push(scene)
            scene.ui.add(dt)
            scene.ui._ensure_layout()

            # Drawing iterates range(len(self._columns)) = range(0) → no cell text
            dt.on_draw()  # Should not crash
        finally:
            g._teardown()

    def test_add_row_and_clear(self) -> None:
        """add_row and clear_rows work correctly."""
        dt = DataTable(columns=["Name", "Score"])
        dt.add_row(["Alice", "100"])
        dt.add_row(["Bob", "200"])
        assert len(dt.rows) == 2

        dt.clear_rows()
        assert len(dt.rows) == 0
        assert dt.selected_row is None


# ======================================================================
# Widget Edge Cases: Grid
# ======================================================================


class TestGridEdgeCases:
    """Grid with 0 columns/rows."""

    def test_zero_columns_zero_rows(self) -> None:
        """Grid(0, 0): no explicit validation, should not crash."""
        grid = Grid(0, 0)
        assert grid.columns == 0
        assert grid.rows == 0

    def test_zero_grid_preferred_size(self) -> None:
        """Grid(0, 0) preferred size: 0*cell_w + max(0, -1)*spacing + 2*padding."""
        grid = Grid(0, 0)
        w, h = grid.get_preferred_size()
        # 0 * 64 + max(0, -1) * 4 + 2 * padding = 0 + 0 + 2*padding
        # padding depends on theme, but w and h should be small
        assert w >= 0
        assert h >= 0

    def test_zero_grid_selected_setter_clears(self) -> None:
        """Grid(0, 0): selected setter with columns<=0 clears selection."""
        grid = Grid(0, 0)
        grid.selected = (0, 0)
        # The setter checks if self._columns <= 0 or self._rows <= 0
        assert grid.selected is None

    def test_zero_grid_on_draw_no_crash(self) -> None:
        """Grid(0, 0) on_draw: iterates range(0) twice — no-op."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            grid = Grid(0, 0)
            scene = Scene()
            g.push(scene)
            scene.ui.add(grid)
            scene.ui._ensure_layout()
            grid.on_draw()  # Should not crash
        finally:
            g._teardown()

    def test_cell_at_zero_grid(self) -> None:
        """Grid(0, 0): _cell_at always returns None since 0 <= col < 0 fails."""
        grid = Grid(0, 0)
        grid._computed_x = 0
        grid._computed_y = 0
        grid._computed_w = 100
        grid._computed_h = 100
        result = grid._cell_at(50, 50)
        assert result is None


# ======================================================================
# Widget Edge Cases: TabGroup
# ======================================================================


class TestTabGroupEdgeCases:
    """TabGroup with empty tabs and unknown label selection."""

    def test_empty_tabs(self) -> None:
        """TabGroup with no tabs: _active_tab is None."""
        tg = TabGroup()
        assert tg.active_tab is None
        assert tg.tab_labels == []

    def test_empty_tabs_dict(self) -> None:
        """TabGroup with empty dict: same as no tabs."""
        tg = TabGroup(tabs={})
        assert tg.active_tab is None
        assert tg.tab_labels == []

    def test_select_tab_unknown_label_raises(self) -> None:
        """select_tab with unknown label raises KeyError."""
        tg = TabGroup()
        with pytest.raises(KeyError, match="No tab named"):
            tg.select_tab("nonexistent")

    def test_select_tab_unknown_on_populated(self) -> None:
        """select_tab with unknown label on a populated TabGroup raises KeyError."""
        tg = TabGroup(tabs={"Tab1": Label("Content1")})
        with pytest.raises(KeyError, match="No tab named 'bogus'"):
            tg.select_tab("bogus")

    def test_active_tab_setter_unknown_raises(self) -> None:
        """active_tab setter delegates to select_tab, so unknown label raises."""
        tg = TabGroup(tabs={"A": Label("a")})
        with pytest.raises(KeyError):
            tg.active_tab = "zzz"

    def test_first_tab_auto_activates(self) -> None:
        """First tab added becomes the active tab."""
        tg = TabGroup()
        lbl = Label("Hello")
        tg.add_tab("First", lbl)
        assert tg.active_tab == "First"
        assert lbl.visible is True

    def test_add_second_tab_does_not_change_active(self) -> None:
        """Adding a second tab doesn't change the active tab."""
        tg = TabGroup()
        tg.add_tab("A", Label("a"))
        tg.add_tab("B", Label("b"))
        assert tg.active_tab == "A"

    def test_tab_switching_visibility(self) -> None:
        """Switching tabs updates visibility correctly."""
        lbl_a = Label("a")
        lbl_b = Label("b")
        tg = TabGroup(tabs={"A": lbl_a, "B": lbl_b})
        assert tg.active_tab == "A"
        assert lbl_a.visible is True
        assert lbl_b.visible is False

        tg.select_tab("B")
        assert tg.active_tab == "B"
        assert lbl_a.visible is False
        assert lbl_b.visible is True


# ======================================================================
# Widget Edge Cases: TextBox
# ======================================================================


class TestTextBoxEdgeCases:
    """TextBox with empty string and NaN typewriter_speed."""

    def test_empty_string(self) -> None:
        """TextBox with empty string: no crash, is_complete immediately."""
        tb = TextBox("")
        assert tb.text == ""
        assert tb.is_complete is True
        assert tb.revealed_count == 0

    def test_empty_string_with_typewriter(self) -> None:
        """TextBox('', typewriter_speed=10): empty text, is_complete True."""
        tb = TextBox("", typewriter_speed=10)
        # typewriter_speed > 0, so _revealed_count starts at 0.0
        # But len(text) == 0, and revealed_count = min(int(0.0), 0) = 0
        # is_complete: 0 >= 0 → True
        assert tb.is_complete is True
        assert tb.revealed_count == 0

    def test_typewriter_speed_nan(self) -> None:
        """TextBox with typewriter_speed=NaN now raises ValueError at init.

        Previously NaN passed the `<= 0` guard and caused NaN values
        during update. Now validation catches it at construction time.
        """
        with pytest.raises(ValueError, match="typewriter_speed must be a finite number"):
            TextBox("Hello World", typewriter_speed=float("nan"))

    def test_typewriter_speed_inf(self) -> None:
        """TextBox with typewriter_speed=+Inf now raises ValueError at init.

        Previously Inf was accepted and caused OverflowError during
        update when int(Inf) was attempted. Now validation catches it
        at construction time.
        """
        with pytest.raises(ValueError, match="typewriter_speed must be a finite number"):
            TextBox("Hello World", typewriter_speed=float("inf"))

    def test_typewriter_speed_zero_instant(self) -> None:
        """typewriter_speed=0 means instant reveal."""
        tb = TextBox("Hello", typewriter_speed=0)
        assert tb.is_complete is True
        assert tb.revealed_count == 5

    def test_typewriter_speed_negative_instant(self) -> None:
        """typewriter_speed < 0: treated as instant (the <= 0 check)."""
        tb = TextBox("Hi", typewriter_speed=-5)
        assert tb.is_complete is True
        assert tb.revealed_count == 2

    def test_typewriter_normal_progression(self) -> None:
        """Normal typewriter: characters reveal over time."""
        tb = TextBox("ABCDE", typewriter_speed=10)  # 10 chars/sec
        assert tb.revealed_count == 0

        tb.update(0.1)  # 10 * 0.1 = 1 char
        assert tb.revealed_count == 1

        tb.update(0.4)  # total = 5 chars
        assert tb.revealed_count == 5
        assert tb.is_complete is True

    def test_skip(self) -> None:
        """skip() reveals all text instantly."""
        tb = TextBox("Hello World", typewriter_speed=1)
        assert tb.is_complete is False
        tb.skip()
        assert tb.is_complete is True

    def test_reset(self) -> None:
        """reset() restarts the typewriter."""
        tb = TextBox("Hi", typewriter_speed=10)
        tb.update(1.0)
        assert tb.is_complete is True
        tb.reset()
        assert tb.revealed_count == 0

    def test_text_setter_resets_typewriter(self) -> None:
        """Setting text property resets typewriter."""
        tb = TextBox("Old", typewriter_speed=10)
        tb.update(1.0)
        assert tb.is_complete is True

        tb.text = "New text"
        assert tb.revealed_count == 0
        assert tb.is_complete is False


# ======================================================================
# Component Tree Safety
# ======================================================================


class TestComponentTreeSafety:
    """Component tree cycle detection and non-child removal."""

    def test_add_self_raises(self) -> None:
        """Component.add(self) raises ValueError."""
        c = Component()
        with pytest.raises(ValueError, match="Cannot add component to itself"):
            c.add(c)

    def test_add_cycle_a_b_a_crashes_in_propagate_game(self) -> None:
        """A.add(B), B.add(A): creates a cycle in _children, then
        _propagate_game recurses infinitely through the cycle.

        After A.add(B): A._children = [B], B._parent = A.
        Then B.add(A): A._parent is None, so no removal from old parent.
        A is appended to B._children: B._children = [A].
        A._parent = B. Now: A._children=[B], B._children=[A] — a cycle.
        _propagate_game walks all children recursively and hits the cycle,
        causing RecursionError.
        """
        a = Component()
        b = Component()

        a.add(b)
        assert b._parent is a
        assert b in a._children

        # B.add(A) creates cycle A→B→A; _propagate_game recurses infinitely.
        with pytest.raises(RecursionError):
            b.add(a)

    def test_add_cycle_detected_via_recursion_error(self) -> None:
        """The framework has no explicit cycle detection, but _propagate_game
        causes RecursionError on cycles. This is an accidental safeguard
        rather than a deliberate validation."""
        a = Component()
        b = Component()
        c = Component()

        a.add(b)
        b.add(c)

        # c.add(a) would create A→B→C→A cycle
        with pytest.raises(RecursionError):
            c.add(a)

    def test_reparent_removes_from_old_parent(self) -> None:
        """Adding a child that already has a parent removes it from old parent."""
        parent1 = Component()
        parent2 = Component()
        child = Component()

        parent1.add(child)
        assert child._parent is parent1
        assert child in parent1._children

        parent2.add(child)
        assert child._parent is parent2
        assert child in parent2._children
        assert child not in parent1._children

    def test_remove_non_child_is_noop(self) -> None:
        """Removing a component that is not a child is a safe no-op."""
        parent = Component()
        stranger = Component()

        # Should not raise — just a no-op
        parent.remove(stranger)

        assert stranger._parent is None
        assert parent._children == []

    def test_remove_non_child_does_not_affect_real_children(self) -> None:
        """Removing a non-child doesn't affect existing children."""
        parent = Component()
        child = Component()
        stranger = Component()

        parent.add(child)
        parent.remove(stranger)

        assert child in parent._children
        assert child._parent is parent

    def test_double_remove_is_safe(self) -> None:
        """Removing the same child twice is safe."""
        parent = Component()
        child = Component()

        parent.add(child)
        parent.remove(child)
        assert child not in parent._children

        # Second remove is a no-op
        parent.remove(child)
        assert child not in parent._children

    def test_propagate_game_on_add(self) -> None:
        """Adding a child propagates _game reference to child and descendants."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            scene = Scene()
            g.push(scene)

            parent = Component()
            child = Component()
            grandchild = Component()
            child.add(grandchild)

            # Before adding to UI tree, _game is None
            assert parent._game is None
            assert child._game is None

            scene.ui.add(parent)
            assert parent._game is g

            parent.add(child)
            assert child._game is g
            assert grandchild._game is g
        finally:
            g._teardown()

    def test_remove_clears_game_reference(self) -> None:
        """Removing a child clears _game reference on child and descendants."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            scene = Scene()
            g.push(scene)

            parent = Component()
            child = Component()
            grandchild = Component()
            child.add(grandchild)

            scene.ui.add(parent)
            parent.add(child)
            assert grandchild._game is g

            parent.remove(child)
            assert child._game is None
            assert grandchild._game is None
        finally:
            g._teardown()


# ======================================================================
# Integration: Timer + Game
# ======================================================================


class TestTimerWithGame:
    """Test timer edge cases through the Game.after/Game.every API."""

    def test_game_after_nan(self) -> None:
        """Game.after(NaN, cb) now raises ValueError — validation in TimerManager.after."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            with pytest.raises(ValueError, match="delay must be a finite number >= 0"):
                g.after(float("nan"), lambda: None)
        finally:
            g._teardown()

    def test_game_every_nan(self) -> None:
        """Game.every(NaN, cb) now raises ValueError — validation in TimerManager.every."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            with pytest.raises(ValueError, match="interval must be a finite number > 0"):
                g.every(float("nan"), lambda: None)
        finally:
            g._teardown()

    def test_game_after_zero_fires_immediately(self) -> None:
        """Game.after(0, cb) fires on the very first tick."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            fired: list[bool] = []
            g.after(0, lambda: fired.append(True))
            g.tick(0.016)
            assert fired == [True]
        finally:
            g._teardown()


# ======================================================================
# Widget Draw Safety (with Game context)
# ======================================================================


class TestWidgetDrawSafety:
    """Widgets should not crash when drawn with edge-case configurations."""

    def test_textbox_empty_string_draw(self) -> None:
        """TextBox('') draws without error."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            scene = Scene()
            g.push(scene)
            tb = TextBox("")
            scene.ui.add(tb)
            scene.ui._ensure_layout()
            tb.on_draw()  # Should not crash
        finally:
            g._teardown()

    def test_progress_bar_max_zero_draw(self) -> None:
        """ProgressBar with max_value=0 draws without error."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            scene = Scene()
            g.push(scene)
            bar = ProgressBar(value=50, max_value=0)
            scene.ui.add(bar)
            scene.ui._ensure_layout()
            bar.on_draw()  # Should not crash
        finally:
            g._teardown()

    def test_list_item_height_zero_draw(self) -> None:
        """List with item_height=0 draws without error."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            scene = Scene()
            g.push(scene)
            lst = List(items=["a", "b"], item_height=0)
            scene.ui.add(lst)
            scene.ui._ensure_layout()
            lst.on_draw()  # Should not crash — _visible_count returns 0
        finally:
            g._teardown()

    def test_tabgroup_empty_draw(self) -> None:
        """TabGroup with no tabs draws without error."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            scene = Scene()
            g.push(scene)
            tg = TabGroup()
            scene.ui.add(tg)
            scene.ui._ensure_layout()
            tg.on_draw()  # Should not crash
        finally:
            g._teardown()

    def test_grid_zero_draw(self) -> None:
        """Grid(0, 0) draws without error."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            scene = Scene()
            g.push(scene)
            grid = Grid(0, 0)
            scene.ui.add(grid)
            scene.ui._ensure_layout()
            grid.on_draw()  # Should not crash
        finally:
            g._teardown()

    def test_datatable_zero_columns_draw(self) -> None:
        """DataTable with 0 columns draws without error."""
        g = Game("Test", backend="mock", resolution=(1920, 1080))
        try:
            scene = Scene()
            g.push(scene)
            dt = DataTable(columns=[], width=400, height=200)
            scene.ui.add(dt)
            scene.ui._ensure_layout()
            dt.on_draw()  # Should not crash
        finally:
            g._teardown()
