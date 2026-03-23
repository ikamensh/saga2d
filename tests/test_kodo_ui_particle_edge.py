"""Targeted edge-case tests for UI widgets, particles, camera, and tweens.

Covers risky paths identified in audit (2026-03-23):

  EC3-EC5: Component tree mutation during draw/handle_event/update walks
  Gap 4:   Grid(0,0) keyboard nav, TabGroup empty ops, DataTable click empty
  Gap 5:   Tween from==to no-op, concurrent tweens, cancel-in-callback
  Gap 6:   Camera pan_to(Inf), shake(decay=0), update(dt=0), large viewport
  Particle: Zero lifetime, continuous+dt=0, burst(0), speed=(0,0)
  Widget:  ProgressBar(max_value=0), Grid(cell_size=0), word_wrap boundary
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import pytest

from saga2d import Game, Scene
from saga2d.rendering.camera import Camera
from saga2d.rendering.particles import ParticleEmitter
from saga2d.ui.component import Component, _UIRoot
from saga2d.ui.widgets import (
    DataTable,
    Grid,
    List,
    ProgressBar,
    TabGroup,
    TextBox,
    Tooltip,
    _word_wrap,
)
from saga2d.util.tween import Ease, TweenManager


# ===================================================================
# Fixtures
# ===================================================================


@pytest.fixture
def game():
    """Fresh Game with mock backend, torn down after test."""
    g = Game("EdgeTest", resolution=(800, 600), backend="mock")
    yield g
    g._teardown()


@pytest.fixture
def game_with_scene(game):
    """Game + pushed scene for sprite/particle tests."""
    s = Scene()
    game.push(s)
    game.tick(0)  # apply deferred push
    return game, s


# ===================================================================
# Helper: fake InputEvent
# ===================================================================


@dataclass(frozen=True)
class FakeEvent:
    """Minimal InputEvent stand-in for unit tests."""

    type: str = "click"
    button: str = "left"
    x: int = 0
    y: int = 0
    dx: int = 0
    dy: int = 0
    action: str = ""
    key: str = ""
    world_x: float = 0.0
    world_y: float = 0.0


# ===================================================================
# EC3-EC5: Component tree mutation during traversal
# ===================================================================


class TestComponentMutationDuringDraw:
    """Child removing itself from parent during draw() should not crash."""

    def test_child_removes_itself_during_draw(self, game):
        """A child calling parent.remove(self) in on_draw should not crash."""
        parent = Component(width=100, height=100)
        parent._game = game

        class SelfRemovingChild(Component):
            def on_draw(self):
                if self._parent is not None:
                    self._parent.remove(self)

        child1 = SelfRemovingChild(width=50, height=50)
        child2 = Component(width=50, height=50)
        parent.add(child1)
        parent.add(child2)

        # draw() iterates _children directly — should survive mutation
        parent.draw()  # Must not raise

        # child1 was removed
        assert child1 not in parent._children

    def test_child_removes_sibling_during_draw(self, game):
        """A child removing a later sibling during on_draw should not crash."""
        parent = Component(width=100, height=100)
        parent._game = game

        child2 = Component(width=50, height=50)

        class SiblingRemover(Component):
            def on_draw(self):
                if child2 in self._parent._children:
                    self._parent.remove(child2)

        child1 = SiblingRemover(width=50, height=50)
        parent.add(child1)
        parent.add(child2)

        parent.draw()  # Must not raise

    def test_child_adds_sibling_during_draw(self, game):
        """Adding a new child during on_draw should not crash or infinite loop."""
        parent = Component(width=100, height=100)
        parent._game = game
        added = False

        class AdderChild(Component):
            def on_draw(self):
                nonlocal added
                if not added:
                    added = True
                    self._parent.add(Component(width=10, height=10))

        child1 = AdderChild(width=50, height=50)
        parent.add(child1)

        parent.draw()  # Must not raise or infinite loop
        assert len(parent._children) == 2


class TestComponentMutationDuringHandleEvent:
    """Child removing itself during handle_event traversal."""

    def test_child_removes_itself_on_event(self, game):
        """A child that removes itself in on_event should not crash."""
        parent = Component(width=200, height=200)
        parent._game = game
        parent._computed_w = 200
        parent._computed_h = 200

        class SelfRemover(Component):
            def on_event(self, event):
                if self._parent is not None:
                    self._parent.remove(self)
                return True

        child = SelfRemover(width=100, height=100)
        child._computed_w = 100
        child._computed_h = 100
        parent.add(child)

        event = FakeEvent(type="click", button="left", x=50, y=50)
        # handle_event iterates reversed(_children) — survive mutation
        parent.handle_event(event)  # Must not raise

    def test_child_removes_sibling_on_event(self, game):
        """A child removing a sibling during event dispatch should not crash."""
        parent = Component(width=200, height=200)
        parent._game = game
        parent._computed_w = 200
        parent._computed_h = 200

        child1 = Component(width=50, height=50)
        child1._computed_w = 50
        child1._computed_h = 50

        class RemoverChild(Component):
            def on_event(self, event):
                if child1 in self._parent._children:
                    self._parent.remove(child1)
                return True

        child2 = RemoverChild(width=50, height=50)
        child2._computed_w = 50
        child2._computed_h = 50
        parent.add(child1)
        parent.add(child2)

        event = FakeEvent(type="click", button="left", x=25, y=25)
        parent.handle_event(event)  # Must not raise


class TestComponentMutationDuringUpdate:
    """Child removing itself during _update_recursive traversal."""

    def test_child_removes_itself_during_update(self, game):
        """A child removing itself in update() should not crash."""
        root = _UIRoot(game)

        class SelfRemoverOnUpdate(Component):
            def update(self, dt):
                if self._parent is not None:
                    self._parent.remove(self)

        child = SelfRemoverOnUpdate(width=50, height=50)
        root.add(child)

        root._update_tree(0.016)  # Must not raise

    def test_child_adds_sibling_during_update(self, game):
        """Adding a child during update walk should not crash or loop."""
        root = _UIRoot(game)
        added = False

        class AdderOnUpdate(Component):
            def update(self, dt):
                nonlocal added
                if not added:
                    added = True
                    self._parent.add(Component(width=10, height=10))

        child = AdderOnUpdate(width=50, height=50)
        root.add(child)

        root._update_tree(0.016)  # Must not raise


# ===================================================================
# EC3-EC5 regression: verify sibling NOT skipped after list() snapshot fix
# ===================================================================


class TestComponentMutationNoSkip:
    """F30 regression: list() snapshot ensures no sibling is skipped when
    another sibling mutates _children during draw/update/handle_event.

    Before this fix, CPython silently skipped children because iterators
    over a live list saw the mutation.  The fix snapshots with list().
    """

    def test_draw_sibling_not_skipped_when_other_removed(self, game):
        """EC4: A child removing a later sibling during draw should
        NOT cause the removed child to be skipped (it was in the snapshot)."""
        parent = Component(width=200, height=200)
        parent._game = game

        class CountDrawComponent(Component):
            def __init__(self):
                super().__init__(width=50, height=50)
                self.drawn = False

            def on_draw(self):
                self.drawn = True

        class SiblingRemover(Component):
            def __init__(self, target):
                super().__init__(width=50, height=50)
                self.target = target

            def on_draw(self):
                if self.target in self._parent._children:
                    self._parent.remove(self.target)

        child_c = CountDrawComponent()
        child_b = SiblingRemover(child_c)
        child_a = CountDrawComponent()

        parent.add(child_a)
        parent.add(child_b)
        parent.add(child_c)

        parent.draw()

        assert child_a.drawn, "child_a should have been drawn"
        assert child_c.drawn, "child_c should have been drawn (snapshot protects)"

    def test_update_sibling_not_skipped_when_other_removed(self, game):
        """EC3: A child removing a later sibling during update should
        NOT cause the removed child to be skipped."""
        root = _UIRoot(game)

        class CountUpdateComponent(Component):
            def __init__(self):
                super().__init__(width=50, height=50)
                self.updated = False

            def update(self, dt):
                self.updated = True

        class SiblingRemoverOnUpdate(Component):
            def __init__(self, target):
                super().__init__(width=50, height=50)
                self.target = target

            def update(self, dt):
                if self.target._parent is not None:
                    self.target._parent.remove(self.target)

        child_c = CountUpdateComponent()
        child_b = SiblingRemoverOnUpdate(child_c)
        child_a = CountUpdateComponent()

        root.add(child_a)
        root.add(child_b)
        root.add(child_c)

        root._update_tree(0.016)

        assert child_a.updated, "child_a should have been updated"
        assert child_c.updated, "child_c should have been updated (snapshot protects)"

    def test_handle_event_sibling_not_skipped_when_other_removed(self, game):
        """EC5: A child removing a sibling during handle_event should
        NOT cause that sibling to be skipped from the reversed snapshot."""
        parent = Component(width=400, height=100)
        parent._game = game
        parent._computed_x = 0
        parent._computed_y = 0
        parent._computed_w = 400
        parent._computed_h = 100

        class CountEventComponent(Component):
            def __init__(self, name):
                super().__init__(width=100, height=100)
                self.name = name
                self.event_received = False

            def on_event(self, event):
                self.event_received = True
                return False  # don't consume

        class EventRemover(Component):
            def __init__(self, target):
                super().__init__(width=100, height=100)
                self.target = target

            def on_event(self, event):
                if self.target._parent is not None:
                    self.target._parent.remove(self.target)
                return False

        # reversed order: [d, remover_of_d, g] → g, remover, d
        # remover removes d, but snapshot should protect d
        d = CountEventComponent("d")
        d._computed_x, d._computed_y = 0, 0
        d._computed_w, d._computed_h = 100, 100

        remover = EventRemover(d)
        remover._computed_x, remover._computed_y = 100, 0
        remover._computed_w, remover._computed_h = 100, 100

        g_child = CountEventComponent("g")
        g_child._computed_x, g_child._computed_y = 200, 0
        g_child._computed_w, g_child._computed_h = 100, 100

        parent.add(d)
        parent.add(remover)
        parent.add(g_child)

        event = FakeEvent(type="click", button="left", x=150, y=50)
        parent.handle_event(event)

        assert g_child.event_received, "g_child should have received event"
        assert d.event_received, "d should have received event (snapshot protects)"

    def test_draw_new_child_added_during_draw_not_drawn_twice(self, game):
        """Adding a child during draw should not cause infinite iteration."""
        parent = Component(width=200, height=200)
        parent._game = game
        add_count = 0

        class AdderChild(Component):
            def on_draw(self):
                nonlocal add_count
                if add_count < 1:
                    add_count += 1
                    self._parent.add(Component(width=10, height=10))

        child = AdderChild(width=50, height=50)
        parent.add(child)

        parent.draw()  # Must terminate
        assert len(parent._children) == 2
        assert add_count == 1


# ===================================================================
# Gap 4: Grid(0,0) / TabGroup empty / DataTable click empty
# ===================================================================


class TestGridZeroDimensions:
    """Grid with 0 columns or 0 rows."""

    def test_grid_0x0_creation(self):
        """Grid(0, 0) should create without crash."""
        g = Grid(0, 0)
        assert g.columns == 0
        assert g.rows == 0

    def test_grid_0x0_preferred_size(self):
        """Grid(0,0) preferred size should be computable."""
        g = Grid(0, 0, cell_size=(64, 64), spacing=4)
        w, h = g.get_preferred_size()
        # 0 columns * cell_w + max(0, -1)*spacing + 2*padding
        assert w >= 0
        assert h >= 0

    def test_grid_0x0_click(self):
        """Clicking Grid(0,0) should not crash."""
        g = Grid(0, 0)
        g._computed_x = 0
        g._computed_y = 0
        g._computed_w = 100
        g._computed_h = 100
        event = FakeEvent(type="click", button="left", x=50, y=50)
        result = g.on_event(event)
        # Should consume click (hit_test passes) but no cell selected
        assert result is True
        assert g.selected is None

    def test_grid_0x0_cell_at(self):
        """_cell_at on Grid(0,0) should return None."""
        g = Grid(0, 0)
        g._computed_x = 0
        g._computed_y = 0
        g._computed_w = 100
        g._computed_h = 100
        assert g._cell_at(50, 50) is None

    def test_grid_0x0_keyboard_nav_motion(self):
        """Motion event on Grid(0,0) should not crash."""
        g = Grid(0, 0)
        g._computed_x = 0
        g._computed_y = 0
        g._computed_w = 100
        g._computed_h = 100
        event = FakeEvent(type="motion", x=50, y=50)
        g.on_event(event)  # Must not crash

    def test_grid_0_cell_size(self):
        """Grid with cell_size (0,0) should handle _cell_at without ZeroDivisionError."""
        g = Grid(3, 3, cell_size=(0, 0))
        g._computed_x = 0
        g._computed_y = 0
        g._computed_w = 100
        g._computed_h = 100
        # _cell_at checks cell_stride <= 0 → returns None
        assert g._cell_at(50, 50) is None

    def test_grid_selected_setter_0x0(self):
        """Setting selected on Grid(0,0) should clamp to None."""
        g = Grid(0, 0)
        g.selected = (5, 5)
        # columns <= 0 → selected set to None
        assert g.selected is None

    def test_grid_draw_0x0(self, game):
        """Drawing Grid(0,0) should not crash."""
        g = Grid(0, 0)
        g._game = game
        g._computed_x = 0
        g._computed_y = 0
        g._computed_w = 100
        g._computed_h = 100
        g.on_draw()  # Must not raise


class TestTabGroupEmpty:
    """TabGroup with no tabs or empty operations."""

    def test_tabgroup_empty_init(self):
        """TabGroup with no tabs should initialize safely."""
        tg = TabGroup()
        assert tg.active_tab is None
        assert tg.tab_labels == []

    def test_tabgroup_empty_select_raises(self):
        """Selecting on empty TabGroup should raise KeyError."""
        tg = TabGroup()
        with pytest.raises(KeyError):
            tg.select_tab("nonexistent")

    def test_tabgroup_add_then_remove_all(self, game):
        """Adding and removing all content should not crash draw."""
        tg = TabGroup()
        tg._game = game
        c1 = Component(width=100, height=100)
        tg.add_tab("tab1", c1)
        assert tg.active_tab == "tab1"

        # Remove the child component directly
        tg.remove(c1)
        # Internal state still has tab1 tracked but component removed from tree
        tg._computed_x = 0
        tg._computed_y = 0
        tg._computed_w = 200
        tg._computed_h = 200
        # on_draw should not crash even if internal state is inconsistent
        tg.on_draw()  # Must not raise

    def test_tabgroup_preferred_size_empty(self):
        """get_preferred_size with no tabs should return sensible values."""
        tg = TabGroup()
        w, h = tg.get_preferred_size()
        assert w >= 100  # min width
        assert h >= tg.tab_height

    def test_tabgroup_click_empty(self):
        """Clicking empty TabGroup header should not crash."""
        tg = TabGroup()
        tg._computed_x = 0
        tg._computed_y = 0
        tg._computed_w = 200
        tg._computed_h = 100
        event = FakeEvent(type="click", button="left", x=50, y=5)
        result = tg.on_event(event)
        # Hit test passes, in header row, _tab_at returns None → no selection change
        assert result is True


class TestDataTableClickEmpty:
    """DataTable with no data rows."""

    def test_datatable_click_empty(self):
        """Clicking empty DataTable data area should not crash or select."""
        dt = DataTable(["Name", "Value"])
        dt._computed_x = 0
        dt._computed_y = 0
        dt._computed_w = 400
        dt._computed_h = 200
        # Click below header
        event = FakeEvent(type="click", button="left", x=100, y=100)
        result = dt.on_event(event)
        assert result is True
        assert dt.selected_row is None

    def test_datatable_keyboard_empty(self):
        """Keyboard nav on empty DataTable should not crash."""
        dt = DataTable(["Name", "Value"])
        dt._computed_x = 0
        dt._computed_y = 0
        dt._computed_w = 400
        dt._computed_h = 200
        event_down = FakeEvent(action="down")
        result = dt.on_event(event_down)
        assert result is True
        # _move_selection returns early if no rows
        assert dt.selected_row is None

    def test_datatable_draw_empty(self, game):
        """Drawing empty DataTable should not crash."""
        dt = DataTable(["Name", "Value"])
        dt._game = game
        dt._computed_x = 0
        dt._computed_y = 0
        dt._computed_w = 400
        dt._computed_h = 200
        dt.on_draw()  # Must not raise

    def test_datatable_scroll_empty(self):
        """Scrolling empty DataTable should not crash."""
        dt = DataTable(["Name"])
        dt._computed_x = 0
        dt._computed_y = 0
        dt._computed_w = 400
        dt._computed_h = 200
        event = FakeEvent(type="scroll", x=100, y=100, dy=5)
        dt.on_event(event)  # Must not raise

    def test_datatable_empty_columns(self):
        """DataTable with empty columns list should handle gracefully."""
        dt = DataTable([])
        w, h = dt.get_preferred_size()
        assert w >= 0
        assert h >= 0

    def test_datatable_row_shorter_than_columns(self, game):
        """DataTable with row shorter than columns should not crash on draw."""
        dt = DataTable(["A", "B", "C"], rows=[["only_one"]])
        dt._game = game
        dt._computed_x = 0
        dt._computed_y = 0
        dt._computed_w = 400
        dt._computed_h = 200
        dt.on_draw()  # Must not crash — line 1949 uses `ci < len(row_data)`


# ===================================================================
# Gap 5: Tween from==to, concurrent tweens, cancel-in-callback
# ===================================================================


class TestTweenFromEqualsTo:
    """Tween with from_val == to_val should still fire on_complete."""

    def test_noop_tween_completes(self):
        """from_val == to_val tween should complete and fire callback."""
        mgr = TweenManager()
        obj = type("Obj", (), {"x": 50.0})()
        completed = []
        mgr.create(obj, "x", 50.0, 50.0, 1.0, on_complete=lambda: completed.append(True))
        mgr.update(1.0)
        assert completed == [True]
        assert obj.x == 50.0

    def test_noop_tween_zero_duration(self):
        """from_val == to_val with duration=0 completes immediately."""
        mgr = TweenManager()
        obj = type("Obj", (), {"x": 42.0})()
        completed = []
        mgr.create(obj, "x", 42.0, 42.0, 0.0, on_complete=lambda: completed.append(True))
        mgr.update(0.001)  # any small dt
        assert completed == [True]
        assert obj.x == 42.0


class TestConcurrentTweens:
    """Multiple tweens on the same property."""

    def test_two_tweens_same_property_both_run(self):
        """Two tweens on the same property should both update (last-write wins)."""
        mgr = TweenManager()
        obj = type("Obj", (), {"x": 0.0})()

        mgr.create(obj, "x", 0.0, 100.0, 1.0)
        mgr.create(obj, "x", 0.0, 200.0, 1.0)

        mgr.update(0.5)
        # Both tweens ran; last one wins the setattr
        # Both at t=0.5 linear: tween1 sets 50, tween2 sets 100
        # Since iteration order is insertion order (dict), tween2 writes last
        assert obj.x == 100.0

    def test_cancel_one_other_continues(self):
        """Cancelling one tween should not affect the other."""
        mgr = TweenManager()
        obj = type("Obj", (), {"x": 0.0, "y": 0.0})()

        t1 = mgr.create(obj, "x", 0.0, 100.0, 1.0)
        mgr.create(obj, "y", 0.0, 200.0, 1.0)

        mgr.cancel(t1)
        mgr.update(0.5)

        assert obj.x == 0.0  # cancelled — stays at initial
        assert obj.y == 100.0  # still running


class TestCancelInCallback:
    """Cancelling tweens/creating tweens inside on_complete callback."""

    def test_cancel_other_tween_in_callback(self):
        """on_complete cancelling another tween should not crash."""
        mgr = TweenManager()
        obj = type("Obj", (), {"x": 0.0, "y": 0.0})()

        t2 = [None]
        def cancel_t2():
            mgr.cancel(t2[0])

        mgr.create(obj, "x", 0.0, 100.0, 0.5, on_complete=cancel_t2)
        t2[0] = mgr.create(obj, "y", 0.0, 200.0, 2.0)

        mgr.update(0.5)  # t1 completes → cancels t2
        assert obj.x == 100.0
        # t2 was cancelled mid-update
        mgr.update(0.5)
        # y should stay wherever it was when cancelled
        # (it was not yet complete, cancel removed it)

    def test_create_tween_in_callback(self):
        """Creating a new tween inside on_complete should not crash."""
        mgr = TweenManager()
        obj = type("Obj", (), {"x": 0.0})()
        new_tweens = []

        def chain():
            t = mgr.create(obj, "x", 100.0, 200.0, 1.0)
            new_tweens.append(t)

        mgr.create(obj, "x", 0.0, 100.0, 0.5, on_complete=chain)
        mgr.update(0.5)
        assert obj.x == 100.0
        assert len(new_tweens) == 1
        mgr.update(1.0)
        assert obj.x == 200.0

    def test_cancel_all_in_callback(self):
        """cancel_all inside on_complete should not crash."""
        mgr = TweenManager()
        obj = type("Obj", (), {"x": 0.0, "y": 0.0, "z": 0.0})()

        def nuke():
            mgr.cancel_all()

        mgr.create(obj, "x", 0.0, 100.0, 0.5, on_complete=nuke)
        mgr.create(obj, "y", 0.0, 200.0, 2.0)
        mgr.create(obj, "z", 0.0, 300.0, 2.0)

        mgr.update(0.5)  # t1 completes → cancel_all → must not crash
        # All should be gone
        mgr.update(1.0)  # No tweens left


# ===================================================================
# Gap 6: Camera edge cases
# ===================================================================


class TestCameraShakeDecayZero:
    """Camera shake(decay=0) should not crash."""

    def test_shake_decay_zero_runs(self):
        """decay=0 → (1 - progress)**0 = 1.0 always → constant intensity shake."""
        cam = Camera((800, 600))
        cam.shake(10.0, 1.0, decay=0.0)
        cam.update(0.5)
        # With decay=0, decayed_intensity = intensity * 1.0 always
        # Shake should be active with full intensity
        assert cam._shake_duration > 0
        # Offsets should be non-zero (random, but within [-10, 10])
        # We can't assert exact values due to randomness, but no crash

    def test_shake_decay_zero_completes(self):
        """Shake with decay=0 should still expire after duration."""
        cam = Camera((800, 600))
        cam.shake(10.0, 1.0, decay=0.0)
        cam.update(1.0)
        assert cam._shake_offset_x == 0.0
        assert cam._shake_offset_y == 0.0


class TestCameraUpdateDtZero:
    """Camera update(dt=0) should be safe."""

    def test_update_dt_zero_no_crash(self):
        """update(0) should not crash in any mode."""
        cam = Camera((800, 600))
        cam.update(0.0)  # Must not raise

    def test_update_dt_zero_with_follow(self, game_with_scene):
        """update(0) with follow should still track target."""
        game, scene = game_with_scene
        from saga2d.rendering.sprite import Sprite
        sp = Sprite("sprites/knight", position=(500, 300))
        scene.add_sprite(sp)
        cam = Camera((800, 600))
        cam.follow(sp)
        cam.update(0.0)
        # Camera should center on sprite
        assert cam._x == 500 - 400
        assert cam._y == 300 - 300

    def test_update_dt_zero_with_shake(self):
        """update(0) with active shake should not divide by zero."""
        cam = Camera((800, 600))
        cam.shake(10.0, 1.0, 1.0)
        cam.update(0.0)  # Must not crash
        # progress = 0/1 = 0, still valid

    def test_update_dt_zero_with_edge_scroll(self):
        """update(0) with edge scroll should not crash."""
        cam = Camera((800, 600))
        cam.enable_edge_scroll(margin=50, speed=200)
        cam.update(0.0, mouse_x=10, mouse_y=10)  # Must not crash
        # speed * 0 = 0, no scroll


class TestCameraLargeViewportSmallBounds:
    """Viewport larger than world_bounds."""

    def test_viewport_larger_than_bounds(self):
        """Viewport 800x600, bounds 100x100 → camera clamped."""
        cam = Camera((800, 600), world_bounds=(0, 0, 100, 100))
        cam.center_on(50, 50)
        # max_x = 100 - 800 = -700, max_y = 100 - 600 = -500
        # clamp: x = max(0, min(-350, -700)) = 0 (since -350 > -700 but < 0)
        # Actually: max(0, min(self._x, max_x)) where max_x = -700
        # self._x = 50 - 400 = -350
        # max(0, min(-350, -700)) = max(0, -700) = 0
        assert cam._x == 0
        assert cam._y == 0

    def test_inverted_bounds_clamps(self):
        """Inverted bounds (left > right) should still not crash."""
        cam = Camera((800, 600), world_bounds=(500, 500, 100, 100))
        cam.center_on(300, 300)
        # max_x = 100 - 800 = -700, so max(500, min(x, -700)) = 500
        assert cam._x == 500  # clamped to left bound


class TestCameraPanDuringShake:
    """Pan-to while shake is active."""

    def test_pan_during_active_shake(self, game):
        """Starting pan_to during active shake should not crash."""
        game.push(Scene())
        game.tick(0)
        cam = Camera((800, 600))
        cam.shake(10.0, 2.0, 1.0)
        cam.update(0.1)  # Start shake
        cam.pan_to(400, 300, 1.0)  # Start pan during shake
        game.tick(0.5)  # Advance tween manager
        # Both effects should coexist — shake offsets + pan position
        # Must not crash


# ===================================================================
# Particle edge cases
# ===================================================================


class TestParticleZeroLifetime:
    """ParticleEmitter with lifetime=(0,0)."""

    def test_zero_lifetime_particle_dies_immediately(self, game_with_scene):
        """Particles with lifetime=0 should die on first update."""
        game, scene = game_with_scene
        em = ParticleEmitter(
            "sprites/knight", position=(100, 100), lifetime=(0.0, 0.0)
        )
        em.burst(5)
        assert len(em._particles) == 5
        em.update(0.016)
        # All particles should be dead (remaining = 0, 0 <= 0 is True)
        assert len(em._particles) == 0

    def test_zero_lifetime_burst_self_cleaning(self, game_with_scene):
        """Zero-lifetime burst emitter becomes inactive after update."""
        game, scene = game_with_scene
        em = ParticleEmitter(
            "sprites/knight", position=(100, 100), lifetime=(0.0, 0.0)
        )
        em.burst(3)
        em.update(0.016)
        assert not em.is_active


class TestParticleContinuousDtZero:
    """Continuous emitter update(dt=0)."""

    def test_continuous_dt_zero_no_spawn(self, game_with_scene):
        """update(0) on continuous emitter should not spawn (rate*0 = 0)."""
        game, scene = game_with_scene
        em = ParticleEmitter(
            "sprites/knight", position=(100, 100)
        )
        em.continuous(rate=100)
        em.update(0.0)
        # rate * 0 = 0, accumulator stays 0, no spawn
        assert len(em._particles) == 0

    def test_continuous_very_high_rate(self, game_with_scene):
        """Very high rate should spawn many particles without crash."""
        game, scene = game_with_scene
        em = ParticleEmitter("sprites/knight", position=(100, 100))
        em.continuous(rate=10000)
        em.update(0.016)  # Should spawn ~160 particles
        # Just check no crash and some spawned
        assert len(em._particles) > 0
        em.remove()


class TestParticleBurstZero:
    """burst(0) and burst with negative."""

    def test_burst_zero_no_spawn(self, game_with_scene):
        """burst(0) should be a no-op."""
        game, scene = game_with_scene
        em = ParticleEmitter("sprites/knight", position=(100, 100))
        em.burst(0)
        assert len(em._particles) == 0

    def test_burst_negative_no_spawn(self, game_with_scene):
        """burst(-5) should be a no-op (n <= 0 guard)."""
        game, scene = game_with_scene
        em = ParticleEmitter("sprites/knight", position=(100, 100))
        em.burst(-5)
        assert len(em._particles) == 0


class TestParticleSpeedZero:
    """Particles with speed=(0,0) — stationary particles."""

    def test_speed_zero_particles_stationary(self, game_with_scene):
        """Particles with speed=(0,0) should not move."""
        game, scene = game_with_scene
        em = ParticleEmitter(
            "sprites/knight", position=(100, 100), speed=(0.0, 0.0)
        )
        em.burst(1)
        assert len(em._particles) == 1
        p = em._particles[0]
        assert p.vx == 0.0
        assert p.vy == 0.0
        initial_x = p.sprite._x
        initial_y = p.sprite._y
        em.update(0.5)
        if len(em._particles) > 0:
            assert em._particles[0].sprite._x == initial_x
            assert em._particles[0].sprite._y == initial_y


class TestParticleFadeWithZeroLifetime:
    """Fade-out with total_lifetime=0 should not divide by zero."""

    def test_fade_zero_total_lifetime_no_crash(self, game_with_scene):
        """Particle with total_lifetime=0 and fade_out=True should not ZeroDivisionError."""
        game, scene = game_with_scene
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(0.0, 0.0),
            fade_out=True,
        )
        em.burst(1)
        # total_lifetime = 0 → fade code checks `if p.total_lifetime > 0` → skip
        em.update(0.016)  # Must not crash (no division by zero)
        assert len(em._particles) == 0  # died


class TestParticleRemoveThenBurst:
    """Emitter burst after remove."""

    def test_burst_after_remove_reregisters(self, game_with_scene):
        """burst() after remove() should re-register the emitter."""
        game, scene = game_with_scene
        em = ParticleEmitter("sprites/knight", position=(100, 100))
        em.burst(1)
        em.remove()
        assert em not in game._particle_emitters
        em.burst(3)
        assert em in game._particle_emitters
        assert len(em._particles) == 3
        em.remove()


# ===================================================================
# Widget edge cases
# ===================================================================


class TestProgressBarEdgeCases:
    """ProgressBar with zero max_value, negative value, etc."""

    def test_fraction_max_zero(self):
        """max_value=0 → fraction returns 0.0 (not ZeroDivisionError)."""
        pb = ProgressBar(value=50, max_value=0)
        assert pb.fraction == 0.0

    def test_fraction_max_negative(self):
        """max_value=-10 → fraction returns 0.0."""
        pb = ProgressBar(value=50, max_value=-10)
        assert pb.fraction == 0.0

    def test_fraction_value_exceeds_max(self):
        """value > max_value → fraction clamped to 1.0."""
        pb = ProgressBar(value=200, max_value=100)
        assert pb.fraction == 1.0

    def test_fraction_negative_value(self):
        """Negative value → fraction clamped to 0.0."""
        pb = ProgressBar(value=-50, max_value=100)
        assert pb.fraction == 0.0

    def test_draw_max_zero(self, game):
        """Drawing with max_value=0 should not crash."""
        pb = ProgressBar(value=50, max_value=0, width=200, height=24)
        pb._game = game
        pb._computed_x = 10
        pb._computed_y = 10
        pb._computed_w = 200
        pb._computed_h = 24
        pb.on_draw()  # Must not raise

    def test_draw_rounded_narrow(self, game):
        """Drawing very narrow rounded bar should not crash."""
        pb = ProgressBar(value=10, max_value=100, width=5, height=24, rounded=True)
        pb._game = game
        pb._computed_x = 10
        pb._computed_y = 10
        pb._computed_w = 5
        pb._computed_h = 24
        pb.on_draw()  # Must not raise


class TestWordWrapEdges:
    """_word_wrap boundary conditions."""

    def test_wrap_empty_string(self):
        """Empty string → single empty-string line (one paragraph)."""
        result = _word_wrap("", 200, 16)
        assert result == [""]  # "".split("\n") → [""] → one empty paragraph

    def test_wrap_single_character(self):
        """Single character always fits."""
        result = _word_wrap("a", 200, 16)
        assert result == ["a"]

    def test_wrap_max_width_1(self):
        """max_width=1 → each word on its own line."""
        result = _word_wrap("hello world", 1, 16)
        assert "hello" in result
        assert "world" in result

    def test_wrap_only_newlines(self):
        """String of only newlines → empty lines."""
        result = _word_wrap("\n\n", 200, 16)
        # "\n\n".split("\n") → ["", "", ""]
        # Each paragraph: "".split(" ") → [""], current_line = "" → append ""
        assert len(result) == 3


class TestListEdgeCases:
    """List widget edge cases."""

    def test_list_empty_move_selection(self):
        """Moving selection on empty list should be a no-op."""
        lst = List(items=[])
        lst._move_selection(1)
        assert lst.selected_index is None

    def test_list_items_setter_clamps(self):
        """Setting items to shorter list clamps selected_index."""
        lst = List(items=["a", "b", "c"])
        lst.selected_index = 2
        lst.items = ["x"]
        assert lst.selected_index == 0

    def test_list_items_setter_empty(self):
        """Setting items to empty clears selection."""
        lst = List(items=["a", "b"])
        lst.selected_index = 1
        lst.items = []
        assert lst.selected_index is None

    def test_list_scroll_past_items(self):
        """Scrolling past items should clamp offset."""
        lst = List(items=["a", "b", "c"], item_height=30, height=60)
        lst._computed_h = 60
        lst._scroll_offset = 100
        lst._clamp_scroll()
        # visible_count = 60 // 30 = 2, max_offset = max(0, 3 - 2) = 1
        assert lst._scroll_offset == 1


class TestTooltipEdgeCases:
    """Tooltip edge cases."""

    def test_tooltip_delay_zero_shows_immediately(self):
        """Tooltip with delay=0 should show immediately on show()."""
        t = Tooltip("help text", delay=0)
        t.show(100, 100)
        assert t._visible_now is True

    def test_tooltip_delay_negative_shows_immediately(self):
        """Tooltip with delay=-1 should show immediately on show()."""
        t = Tooltip("help text", delay=-1)
        t.show(100, 100)
        assert t._visible_now is True

    def test_tooltip_hide_then_show_resets_timer(self):
        """hide() then show() should restart delay timer."""
        t = Tooltip("help text", delay=0.5)
        t.show(100, 100)
        t.update(0.3)  # partially through delay
        t.hide()
        assert t._visible_now is False
        t.show(200, 200)
        assert t._visible_now is False  # timer restarted
        assert t._timer == 0.0

    def test_tooltip_draw_off_screen(self, game):
        """Tooltip near screen edge should clamp position."""
        t = Tooltip("long tooltip text here")
        t._game = game
        t.show(790, 590)  # Near bottom-right of 800x600
        t._visible_now = True
        t.on_draw()  # Should clamp without crash


class TestTextBoxEdgeCases:
    """TextBox edge cases."""

    def test_textbox_empty_text(self, game):
        """TextBox with empty text should draw without crash."""
        tb = TextBox("")
        tb._game = game
        tb._computed_x = 0
        tb._computed_y = 0
        tb._computed_w = 300
        tb._computed_h = 200
        tb.on_draw()  # Must not raise

    def test_textbox_typewriter_text_change(self):
        """Changing text resets typewriter counter."""
        tb = TextBox("hello", typewriter_speed=10)
        tb.update(0.3)  # reveal 3 chars
        assert tb.revealed_count == 3
        tb.text = "new text"
        assert tb.revealed_count == 0
        assert tb._wrapped_lines is None

    def test_textbox_is_complete_empty(self):
        """is_complete on empty text should be True."""
        tb = TextBox("", typewriter_speed=10)
        assert tb.is_complete is True

    def test_textbox_skip_then_reset(self):
        """skip() reveals all, reset() goes back to 0."""
        tb = TextBox("hello world", typewriter_speed=5)
        tb.skip()
        assert tb.is_complete is True
        tb.reset()
        assert tb.revealed_count == 0


# ===================================================================
# Component tree edge cases
# ===================================================================


class TestComponentTreeEdges:
    """Component tree management edge cases."""

    def test_add_to_self_raises(self):
        """Adding a component to itself should raise ValueError."""
        c = Component(width=100, height=100)
        with pytest.raises(ValueError, match="Cannot add component to itself"):
            c.add(c)

    def test_add_reparents_child(self):
        """Adding a child that already has a parent reparents it."""
        p1 = Component(width=100, height=100)
        p2 = Component(width=100, height=100)
        child = Component(width=50, height=50)
        p1.add(child)
        assert child.parent is p1
        p2.add(child)
        assert child.parent is p2
        assert child not in p1._children
        assert child in p2._children

    def test_remove_nonexistent_child(self):
        """Removing a child that isn't in the list should be a no-op."""
        p = Component(width=100, height=100)
        c = Component(width=50, height=50)
        p.remove(c)  # Must not crash

    def test_children_returns_copy(self):
        """children property should return a copy (safe iteration)."""
        p = Component(width=100, height=100)
        c = Component(width=50, height=50)
        p.add(c)
        kids = p.children
        kids.clear()
        assert len(p._children) == 1  # original unchanged

    def test_negative_width_raises(self):
        """Negative width should raise ValueError."""
        with pytest.raises(ValueError, match="width cannot be negative"):
            Component(width=-10, height=100)

    def test_negative_height_raises(self):
        """Negative height should raise ValueError."""
        with pytest.raises(ValueError, match="height cannot be negative"):
            Component(width=100, height=-10)

    def test_negative_margin_raises(self):
        """Negative margin should raise ValueError."""
        with pytest.raises(ValueError, match="margin cannot be negative"):
            Component(width=100, height=100, margin=-5)

    def test_width_zero_is_ok(self):
        """Width=0 should be valid (content-sizing)."""
        c = Component(width=0, height=0)
        assert c._width == 0

    def test_hit_test_zero_size(self):
        """Hit test with zero-size component should always return False."""
        c = Component(width=0, height=0)
        c._computed_x = 50
        c._computed_y = 50
        c._computed_w = 0
        c._computed_h = 0
        assert c.hit_test(50, 50) is False

    def test_deeply_nested_draw(self, game):
        """100-deep component tree should draw without stack overflow."""
        root = Component(width=100, height=100)
        root._game = game
        current = root
        for _ in range(100):
            child = Component(width=10, height=10)
            current.add(child)
            current = child
        root.draw()  # Must not raise


# ===================================================================
# Full integration: Game.tick with edge-case scenarios
# ===================================================================


class TestGameTickWithEdgeCases:
    """Full integration tests through Game.tick()."""

    def test_tick_with_particles_and_ui(self, game):
        """Tick with both particles and UI widgets active."""

        class TestScene(Scene):
            def on_enter(self):
                from saga2d.rendering.sprite import Sprite
                self.sp = Sprite("sprites/knight", position=(400, 300))
                self.add_sprite(self.sp)
                self.em = ParticleEmitter(
                    "sprites/knight", position=(400, 300),
                    lifetime=(0.1, 0.2)
                )
                self.em.burst(10)
                # Add UI
                from saga2d.ui.widgets import ProgressBar
                pb = ProgressBar(value=50, max_value=100)
                self.ui.add(pb)

        scene = TestScene()
        game.push(scene)
        game.tick(0)  # apply push
        game.tick(0.016)  # normal frame with particles + UI
        game.tick(0.016)  # another frame
        # Particles should be dying off
        assert True  # no crash

    def test_tick_zero_dt(self, game):
        """Game.tick(0) should be safe."""
        scene = Scene()
        game.push(scene)
        game.tick(0)  # apply push
        game.tick(0)  # zero dt frame
        game.tick(0)  # another zero dt
        assert True  # no crash

    def test_rapid_scene_transitions_with_particles(self, game):
        """Rapid push/pop with particle emitters should clean up properly."""

        class ParticleScene(Scene):
            def on_enter(self):
                self.em = ParticleEmitter(
                    "sprites/knight", position=(100, 100)
                )
                self.em.continuous(rate=50)

        for _ in range(10):
            game.push(ParticleScene())
            game.tick(0)
            game.tick(0.016)
            game.pop()
            game.tick(0)

        # All emitters should be cleaned up
        assert True  # no crash

    def test_camera_shake_during_particle_burst(self, game):
        """Particles + camera shake simultaneously."""

        class ShakeScene(Scene):
            def on_enter(self):
                from saga2d.rendering.camera import Camera
                self.camera = Camera((800, 600))
                self.camera.shake(5.0, 0.5, 1.0)
                self.em = ParticleEmitter(
                    "sprites/knight", position=(400, 300)
                )
                self.em.burst(20)

        scene = ShakeScene()
        game.push(scene)
        game.tick(0)
        for _ in range(30):
            game.tick(0.016)
        # Shake should have expired, particles should be dying
        assert True  # no crash
