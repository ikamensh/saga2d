"""Edge-case tests for Camera, DragManager, SaveManager, and Scene integration.

Probes specific gaps in coverage:
- Camera follow with removed sprite, narrow bounds, NaN input, large-dt shake, pan cancellation
- DragManager start on non-draggable, drop rejection, cancel_active cleanup
- SaveManager large slot, empty directory listing, delete non-existent, non-serializable state
- Scene deferred-op depth, bind_key after pop, HUD visibility, transparent draw ordering
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import pytest

from saga2d import Camera, Component, Game, Scene, Sprite
from saga2d.input import InputEvent
from saga2d.save import SaveError, SaveManager
from saga2d.ui.component import _UIRoot
from saga2d.ui.drag_drop import DragManager


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def mock_game() -> Game:
    """Return a Game with mock backend for headless testing."""
    g = Game("EdgeTest", backend="mock", resolution=(800, 600))
    yield g
    g._teardown()


@pytest.fixture
def mock_backend(mock_game):
    return mock_game.backend


# ======================================================================
# 1. Camera: follow then sprite removed
# ======================================================================


class _FakeSprite:
    """Minimal sprite-like object for camera follow tests.

    The camera only reads .x, .y, and .is_removed on the follow target,
    so this avoids the need for a real Sprite (which requires asset files).
    """

    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y
        self.is_removed = False

    def remove(self):
        self.is_removed = True


class TestCameraFollowRemovedSprite:
    """camera.follow(sprite) then sprite.remove() then camera.update()."""

    def test_follow_then_remove_stops_following(self):
        """After following a sprite that is removed, update() should stop
        following without crashing."""
        sprite = _FakeSprite(500, 400)
        cam = Camera((800, 600))
        cam.follow(sprite)

        # One update to verify follow works.
        cam.update(0.016)
        assert cam.x == pytest.approx(500 - 400)
        assert cam.y == pytest.approx(400 - 300)

        # Now remove the sprite.
        sprite.remove()
        assert sprite.is_removed

        # Update again -- should detect is_removed and stop following.
        cam.update(0.016, None, None)

        # The camera should have cleared its follow target.
        assert cam._follow_target is None
        # Position should remain at the last follow position (no crash).
        assert cam.x == pytest.approx(100.0)
        assert cam.y == pytest.approx(100.0)

    def test_follow_target_without_is_removed_keeps_following(self):
        """If the follow target has no is_removed attr, camera keeps following."""
        class MinimalTarget:
            def __init__(self):
                self.x = 300.0
                self.y = 200.0

        target = MinimalTarget()
        cam = Camera((800, 600))
        cam.follow(target)
        cam.update(0.016)
        assert cam.x == pytest.approx(300 - 400)
        assert cam.y == pytest.approx(200 - 300)

        # Move the target -- camera should track it.
        target.x = 600.0
        target.y = 500.0
        cam.update(0.016)
        assert cam.x == pytest.approx(600 - 400)
        assert cam.y == pytest.approx(500 - 300)


# ======================================================================
# 2. Camera: world bounds narrower than viewport
# ======================================================================


class TestCameraNarrowBounds:
    """World bounds where right - left < viewport_width."""

    def test_narrow_bounds_no_crash(self):
        """Bounds (0, 0, 100, 100) with viewport (800, 600).
        The max_x = 100 - 800 = -700. Clamping should still work."""
        cam = Camera((800, 600), world_bounds=(0, 0, 100, 100))
        # _clamp should set x to max(0, min(x, -700)) -> 0
        cam.center_on(50, 50)
        # After clamping: x = max(0, min(50 - 400, -700)) = max(0, -700) = 0
        assert cam.x == 0
        assert cam.y == 0

    def test_narrow_bounds_scroll_stays_clamped(self):
        """Scrolling within narrow bounds stays clamped."""
        cam = Camera((800, 600), world_bounds=(0, 0, 200, 200))
        cam.scroll(1000, 1000)
        # max_x = 200 - 800 = -600, max(0, min(1000, -600)) = 0
        assert cam.x == 0
        assert cam.y == 0

    def test_set_bounds_narrower_after_init(self):
        """Changing world_bounds to narrow after init re-clamps immediately."""
        cam = Camera((800, 600))
        cam.center_on(500, 500)
        before_x = cam.x
        cam.world_bounds = (0, 0, 50, 50)
        assert cam.x == 0
        assert cam.y == 0


# ======================================================================
# 3. Camera: screen_to_world with NaN input
# ======================================================================


class TestCameraScreenToWorldNaN:
    """Pass NaN coordinates to screen_to_world."""

    def test_nan_input_produces_nan_output(self):
        """screen_to_world with NaN should propagate NaN (not crash)."""
        cam = Camera((800, 600))
        wx, wy = cam.screen_to_world(float("nan"), float("nan"))
        assert math.isnan(wx)
        assert math.isnan(wy)

    def test_center_on_nan_raises_valueerror(self):
        """center_on with NaN should raise ValueError."""
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.center_on(float("nan"), 0)

    def test_inf_input_to_screen_to_world(self):
        """screen_to_world with Inf should produce Inf (not crash)."""
        cam = Camera((800, 600))
        wx, wy = cam.screen_to_world(float("inf"), float("-inf"))
        assert math.isinf(wx) and wx > 0
        assert math.isinf(wy) and wy < 0


# ======================================================================
# 4. Camera: shake with very large dt
# ======================================================================


class TestCameraShakeLargeDt:
    """dt > shake_duration should result in shake being completely expired."""

    def test_large_dt_expires_shake_immediately(self):
        """A single update with dt >> duration should fully expire the shake."""
        cam = Camera((800, 600))
        cam.shake(intensity=20.0, duration=0.5, decay=1.0)

        # Before update, shake is active but offsets are 0 (no update yet).
        assert cam._shake_duration == 0.5
        assert cam._shake_elapsed == 0.0

        # Update with dt=10 >> duration=0.5.
        cam.update(10.0)

        # Shake should be fully expired.
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0
        assert cam._shake_duration == 0.0

    def test_exact_duration_expires_shake(self):
        """dt == duration should expire the shake."""
        cam = Camera((800, 600))
        cam.shake(intensity=15.0, duration=1.0, decay=2.0)
        cam.update(1.0)
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0
        assert cam._shake_duration == 0.0

    def test_zero_duration_resets_shake(self):
        """shake(duration=0) should immediately reset any active shake."""
        cam = Camera((800, 600))
        cam.shake(intensity=10, duration=0.5, decay=1.0)
        cam.update(0.1)  # Partially advance.
        # Now reset with duration=0.
        cam.shake(intensity=0, duration=0, decay=1.0)
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0


# ======================================================================
# 5. Camera: pan_to while already panning
# ======================================================================


class TestCameraPanToCancels:
    """Second pan_to should cancel the first."""

    def test_second_pan_cancels_first(self, mock_game):
        """Issue pan_to(A), then immediately pan_to(B). Only B should take
        effect after advancing tweens."""
        cam = Camera((800, 600))
        cam.center_on(0, 0)

        # First pan to (1000, 1000).
        cam.pan_to(1000, 1000, duration=1.0)
        first_tween_x = cam._pan_tween_x
        first_tween_y = cam._pan_tween_y
        assert first_tween_x is not None

        # Second pan to (200, 200) -- should cancel the first.
        cam.pan_to(200, 200, duration=1.0)
        assert cam._pan_tween_x is not None
        assert cam._pan_tween_x != first_tween_x
        assert cam._pan_tween_y != first_tween_y

        # Advance the tween manager to completion.
        for _ in range(100):
            mock_game._tween_manager.update(0.02)

        # Camera should have ended at the second target (200, 200 centered).
        expected_x = 200 - 400
        expected_y = 200 - 300
        assert cam._x == pytest.approx(expected_x, abs=2.0)
        assert cam._y == pytest.approx(expected_y, abs=2.0)


# ======================================================================
# 6. DragManager: start drag on non-draggable component
# ======================================================================


class TestDragManagerNonDraggable:
    """DragManager should not start a session on non-draggable components."""

    def test_click_on_non_draggable_no_drag(self, mock_game):
        """Clicking a component with draggable=False should not start drag."""
        scene = Scene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        # Create a non-draggable component.
        comp = Component(width=100, height=100, draggable=False)
        scene.ui.add(comp)
        scene.ui._ensure_layout()

        dm = scene.ui.drag_manager
        assert not dm.is_dragging

        # Simulate a click inside the component bounds.
        event = InputEvent(type="click", x=50, y=50, button="left")
        result = comp.handle_event(event)

        # Non-draggable, so no drag should start.
        assert not dm.is_dragging


# ======================================================================
# 7. DragManager: drop on target that rejects
# ======================================================================


class TestDragManagerDropReject:
    """drop_accept returns False -- drop should not fire on_drop."""

    def test_drop_rejected_no_on_drop(self, mock_game):
        """When drop_accept returns False, on_drop must not be called."""
        scene = Scene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        dropped = []
        source = Component(
            width=50, height=50, draggable=True, drag_data="payload"
        )
        target = Component(
            width=100,
            height=100,
            drop_accept=lambda data: False,  # Always reject
            on_drop=lambda comp, data: dropped.append(data),
        )

        scene.ui.add(source)
        scene.ui.add(target)
        scene.ui._ensure_layout()

        dm = scene.ui.drag_manager

        # Manually start the drag.
        dm._start_drag(source, "payload", 25, 25)
        assert dm.is_dragging

        # Simulate move to target area and then release.
        move_event = InputEvent(type="move", x=50, y=50)
        dm.handle_event(move_event)

        release_event = InputEvent(type="release", x=50, y=50)
        dm.handle_event(release_event)

        # on_drop should NOT have been called.
        assert dropped == []
        assert not dm.is_dragging


# ======================================================================
# 8. DragManager: cancel_active during active drag
# ======================================================================


class TestDragManagerCancelActive:
    """cancel_active() should clean up the session."""

    def test_cancel_active_cleans_up(self, mock_game):
        """cancel_active() during an active drag should clear the session."""
        scene = Scene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        source = Component(
            width=50, height=50, draggable=True, drag_data="item"
        )
        scene.ui.add(source)
        scene.ui._ensure_layout()

        dm = scene.ui.drag_manager
        dm._start_drag(source, "item", 25, 25)
        assert dm.is_dragging
        assert dm.drag_data == "item"

        dm.cancel_active()

        assert not dm.is_dragging
        assert dm.drag_data is None


# ======================================================================
# 9. SaveManager: very large slot number
# ======================================================================


class TestSaveManagerLargeSlot:
    """SaveManager with slot=999999 should just create a filename."""

    def test_large_slot_save_and_load(self):
        """slot=999999 should work -- it's just a filename."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(tmpdir)
            sm.save(999999, {"key": "value"}, "TestScene")

            # Verify the file was created.
            expected = Path(tmpdir) / "save_999999.json"
            assert expected.exists()

            # Load it back.
            data = sm.load(999999)
            assert data is not None
            assert data["state"]["key"] == "value"
            assert data["scene_class"] == "TestScene"


# ======================================================================
# 10. SaveManager: list_slots on empty directory
# ======================================================================


class TestSaveManagerListSlotsEmpty:
    """list_slots on an empty directory should return a list of Nones."""

    def test_list_slots_empty_dir(self):
        """Empty save directory should return [None, None, ...]."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(tmpdir)
            slots = sm.list_slots(count=5)
            assert len(slots) == 5
            assert all(s is None for s in slots)

    def test_list_slots_nonexistent_dir(self):
        """Non-existent directory should return all Nones (no crash)."""
        sm = SaveManager("/tmp/saga2d_test_nonexistent_12345")
        # The directory doesn't exist, but list_slots just calls load()
        # which checks path.exists() and returns None.
        slots = sm.list_slots(count=3)
        assert len(slots) == 3
        assert all(s is None for s in slots)


# ======================================================================
# 11. SaveManager: delete non-existent slot
# ======================================================================


class TestSaveManagerDeleteNonExistent:
    """delete() on a non-existent slot -- the docstring says 'No-op if slot is empty'."""

    def test_delete_nonexistent_is_noop(self):
        """Deleting a non-existent slot should be a no-op (not raise)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(tmpdir)
            # Per docstring: "No-op if slot is empty."
            # This should NOT raise.
            sm.delete(42)

    def test_delete_slot_negative_raises(self):
        """Deleting slot < 1 should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(tmpdir)
            with pytest.raises(ValueError, match="slot must be >= 1"):
                sm.delete(0)


# ======================================================================
# 12. SaveManager: save with non-serializable state
# ======================================================================


class TestSaveManagerNonSerializable:
    """Non-serializable state should raise SaveError (atomic write protects original)."""

    def test_non_serializable_raises_save_error(self):
        """Saving state containing a set (not JSON-serializable) should raise SaveError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(tmpdir)
            # First, save valid data.
            sm.save(1, {"hp": 100}, "GameScene")
            original = sm.load(1)
            assert original is not None

            # Now try to save non-serializable data.
            with pytest.raises(SaveError):
                sm.save(1, {"bad": {1, 2, 3}}, "GameScene")  # set is not serializable

            # The atomic write should have protected the original.
            data = sm.load(1)
            assert data is not None
            assert data["state"]["hp"] == 100

    def test_non_serializable_object_raises(self):
        """Saving state containing a lambda should raise SaveError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(tmpdir)
            with pytest.raises(SaveError):
                sm.save(1, {"fn": lambda: None}, "GameScene")


# ======================================================================
# 13. Scene deferred operation depth
# ======================================================================


class TestSceneDeferredOpDepth:
    """Push 100 scenes in on_enter callbacks. Should hit the 1000-iteration cap."""

    def test_recursive_push_in_on_enter_is_capped(self, mock_game):
        """Each on_enter pushes another scene. The 1000-iteration cap in
        flush_pending_ops should prevent infinite recursion."""
        push_count = [0]

        class RecursiveScene(Scene):
            def on_enter(self):
                push_count[0] += 1
                if push_count[0] < 200:
                    self.game.push(RecursiveScene())

        # Push the first scene. This triggers the cascade via deferred ops.
        mock_game.push(RecursiveScene())

        # The scene stack should have some scenes but not infinite.
        stack_size = len(mock_game._scene_stack._stack)
        assert stack_size > 0
        assert stack_size <= 1001  # Capped by max_iterations

    def test_small_depth_push_chain(self, mock_game):
        """Push 5 scenes via on_enter chain -- all should succeed."""
        entered = []

        class ChainScene(Scene):
            def __init__(self, depth):
                super().__init__()
                self.depth = depth

            def on_enter(self):
                entered.append(self.depth)
                if self.depth < 5:
                    self.game.push(ChainScene(self.depth + 1))

        mock_game.push(ChainScene(1))
        assert entered == [1, 2, 3, 4, 5]
        assert len(mock_game._scene_stack._stack) == 5


# ======================================================================
# 14. Scene.bind_key then pop
# ======================================================================


class TestSceneBindKeyThenPop:
    """Keys bound in on_enter should not fire after pop."""

    def test_bound_key_not_fired_after_pop(self, mock_game, mock_backend):
        """After popping a scene, its bound keys should not fire."""
        fired = []

        class BaseScene(Scene):
            def on_enter(self):
                self.bind_key("i", lambda: fired.append("base_i"))

        class OverlayScene(Scene):
            def on_enter(self):
                self.bind_key("i", lambda: fired.append("overlay_i"))

        base = BaseScene()
        mock_game.push(base)
        mock_game.tick(dt=0.016)

        overlay = OverlayScene()
        mock_game.push(overlay)
        mock_game.tick(dt=0.016)

        # Press "i" -- should fire overlay's handler.
        mock_backend.inject_key("i")
        mock_game.tick(dt=0.016)
        assert fired == ["overlay_i"]

        # Pop overlay.
        mock_game.pop()
        mock_game.tick(dt=0.016)

        # Press "i" again -- should fire base's handler (not overlay's).
        fired.clear()
        mock_backend.inject_key("i")
        mock_game.tick(dt=0.016)
        assert fired == ["base_i"]

    def test_pop_clears_key_handlers_from_old_scene(self, mock_game, mock_backend):
        """Popping a scene should ensure its key bindings no longer trigger
        because the scene is no longer on the stack."""
        fired = []

        class MyScene(Scene):
            def on_enter(self):
                self.bind_key("x", lambda: fired.append("x"))

        scene = MyScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        mock_backend.inject_key("x")
        mock_game.tick(dt=0.016)
        assert fired == ["x"]

        # Pop the scene.
        mock_game.pop()
        mock_game.tick(dt=0.016)

        # Now there is no scene to handle the key.
        fired.clear()
        mock_backend.inject_key("x")
        mock_game.tick(dt=0.016)
        assert fired == []  # No handler fired -- the scene is gone.


# ======================================================================
# 15. HUD visibility toggle
# ======================================================================


class TestHUDVisibilityToggle:
    """Set show_hud=False on top scene, verify HUD doesn't draw."""

    def test_show_hud_false_hides_hud(self, mock_game, mock_backend):
        """When top scene has show_hud=False, HUD.draw should not be called."""
        from saga2d.ui.component import Component

        # Create HUD with a component that draws a rect.
        class DrawingComponent(Component):
            def on_draw(self):
                game = self._game
                if game is not None:
                    game._backend.draw_rect(0, 0, 100, 20, (255, 255, 0, 255))

        hud_comp = DrawingComponent(width=100, height=20)
        mock_game.hud.add(hud_comp)

        # Push a scene with show_hud=True and draw.
        class HudScene(Scene):
            show_hud = True

        mock_game.push(HudScene())
        mock_game.tick(dt=0.016)

        # Check that the HUD component's rect was drawn.
        hud_rects = [
            r
            for r in mock_backend.rects
            if r["color"] == (255, 255, 0, 255)
        ]
        assert len(hud_rects) >= 1, "HUD should draw when show_hud=True"

        # Now push a scene with show_hud=False.
        class NoHudScene(Scene):
            show_hud = False

        mock_game.push(NoHudScene())
        mock_game.tick(dt=0.016)

        # Check that no HUD rect was drawn in this frame.
        hud_rects = [
            r
            for r in mock_backend.rects
            if r["color"] == (255, 255, 0, 255)
        ]
        assert len(hud_rects) == 0, "HUD should NOT draw when show_hud=False"

    def test_hud_visible_false_also_hides(self, mock_game, mock_backend):
        """Even with show_hud=True, setting hud.visible=False hides the HUD."""
        from saga2d.ui.component import Component

        class DrawComp(Component):
            def on_draw(self):
                game = self._game
                if game is not None:
                    game._backend.draw_rect(0, 0, 50, 10, (0, 255, 0, 255))

        mock_game.hud.add(DrawComp(width=50, height=10))
        mock_game.hud.visible = False

        class MyScene(Scene):
            show_hud = True

        mock_game.push(MyScene())
        mock_game.tick(dt=0.016)

        green_rects = [
            r for r in mock_backend.rects if r["color"] == (0, 255, 0, 255)
        ]
        assert len(green_rects) == 0, "HUD should not draw when hud.visible=False"


# ======================================================================
# 16. Transparent scene draw ordering
# ======================================================================


class TestTransparentSceneDrawOrder:
    """Push opaque base + transparent overlay, verify draw order."""

    def test_base_and_overlay_draw_order(self, mock_game, mock_backend):
        """Base scene draws first, then overlay on top."""
        draw_order = []

        class BaseScene(Scene):
            def draw(self):
                draw_order.append("base")

        class OverlayScene(Scene):
            transparent = True

            def draw(self):
                draw_order.append("overlay")

        mock_game.push(BaseScene())
        mock_game.tick(dt=0.016)

        mock_game.push(OverlayScene())
        mock_game.tick(dt=0.016)

        # The draw order should be base then overlay.
        assert draw_order[-2:] == ["base", "overlay"]

    def test_three_layer_draw_order(self, mock_game, mock_backend):
        """Opaque base + two transparent overlays in correct order."""
        draw_order = []

        class BaseScene(Scene):
            def draw(self):
                draw_order.append("base")

        class Overlay1(Scene):
            transparent = True

            def draw(self):
                draw_order.append("overlay1")

        class Overlay2(Scene):
            transparent = True

            def draw(self):
                draw_order.append("overlay2")

        mock_game.push(BaseScene())
        mock_game.tick(dt=0.016)
        mock_game.push(Overlay1())
        mock_game.tick(dt=0.016)
        mock_game.push(Overlay2())
        mock_game.tick(dt=0.016)

        # The last tick should draw all three in order.
        assert draw_order[-3:] == ["base", "overlay1", "overlay2"]

    def test_opaque_scene_hides_lower(self, mock_game, mock_backend):
        """An opaque overlay should NOT draw the base scene."""
        draw_order = []

        class BaseScene(Scene):
            def draw(self):
                draw_order.append("base")

        class OpaqueOverlay(Scene):
            transparent = False

            def draw(self):
                draw_order.append("opaque_overlay")

        mock_game.push(BaseScene())
        mock_game.tick(dt=0.016)
        draw_order.clear()

        mock_game.push(OpaqueOverlay())
        mock_game.tick(dt=0.016)

        # Only the opaque overlay should draw (base is hidden).
        assert draw_order == ["opaque_overlay"]
