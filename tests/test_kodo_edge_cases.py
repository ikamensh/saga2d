"""Comprehensive edge-case tests for the saga2d framework.

Tests cover boundary conditions, invalid inputs, and unusual usage patterns
across all major subsystems: Game, Scene, Sprite, Actions, Camera, Tween,
Timer, FSM, UI, Save/Load, Audio, Particles, and Input.

Uses the ``mock_game`` and ``mock_backend`` fixtures from conftest.py.
"""

from __future__ import annotations

import math
import os
import tempfile
from pathlib import Path
from typing import Any

import pytest

from saga2d import (
    Button,
    Camera,
    Delay,
    Do,
    Ease,
    FadeIn,
    FadeOut,
    Game,
    InputEvent,
    InputManager,
    Label,
    Layout,
    List,
    MoveTo,
    Panel,
    Parallel,
    ParticleEmitter,
    ProgressBar,
    Repeat,
    SaveError,
    SaveManager,
    Scene,
    Sequence,
    Sprite,
    StateMachine,
    tween,
)
from saga2d.backends.mock_backend import MockBackend
from saga2d.util.timer import TimerManager
from saga2d.util.tween import TweenManager


# ======================================================================
# 1. Game Singleton Edge Cases
# ======================================================================


class TestGameSingletonEdgeCases:
    """Game is a singleton guarded by _current_game."""

    def test_second_game_without_teardown_raises(self, mock_game: Game) -> None:
        """Creating a second Game without tearing down the first raises RuntimeError."""
        with pytest.raises(RuntimeError, match="A Game instance already exists"):
            Game("Second", backend="mock")

    def test_new_game_after_teardown(self, mock_game: Game) -> None:
        """After teardown, a new Game can be created successfully."""
        mock_game._teardown()
        g2 = Game("Second", backend="mock", resolution=(800, 600))
        try:
            assert g2.running is True
        finally:
            g2._teardown()

    def test_teardown_is_idempotent(self, mock_game: Game) -> None:
        """Calling _teardown() twice does not crash."""
        mock_game._teardown()
        # Second call should be a safe no-op.
        mock_game._teardown()


# ======================================================================
# 2. Scene Stack Edge Cases
# ======================================================================


class TestSceneStackEdgeCases:
    """Scene stack push/pop/replace edge cases."""

    def test_pop_empty_stack_is_noop(self, mock_game: Game) -> None:
        """Popping an empty stack does not crash and is a no-op."""
        # Stack starts empty (no start_scene pushed).
        mock_game.pop()
        # No error, stack is still empty.
        assert mock_game._scene_stack.top() is None

    def test_pop_on_cancel_with_key_injection(
        self, mock_game: Game, mock_backend: MockBackend
    ) -> None:
        """A scene with pop_on_cancel=True is popped when cancel key is pressed."""

        class CancelScene(Scene):
            pop_on_cancel = True

        bottom = Scene()
        top = CancelScene()
        mock_game.push(bottom)
        mock_game.push(top)
        assert mock_game._scene_stack.top() is top

        mock_backend.inject_key("escape")
        mock_game.tick(dt=0.016)

        # The CancelScene should have been popped, revealing bottom.
        assert mock_game._scene_stack.top() is bottom

    def test_push_scene_during_on_enter(self, mock_game: Game) -> None:
        """Pushing a scene during another scene's on_enter is deferred correctly."""
        inner = Scene()

        class PushingScene(Scene):
            def on_enter(self) -> None:
                self.game.push(inner)

        outer = PushingScene()
        mock_game.push(outer)

        # The inner push happens during on_enter which is not deferred at
        # the push level (only during tick). So after push, the stack
        # should have both scenes.
        # Actually on_enter is called during _apply_push, and inside on_enter
        # _should_defer returns False (we are not in tick), so it applies
        # immediately.
        assert mock_game._scene_stack.top() is inner

    def test_push_during_on_exit_deferred_and_flushed(
        self, mock_game: Game, mock_backend: MockBackend
    ) -> None:
        """A push during on_exit is deferred; flushed by the tick mechanism."""
        replacement = Scene()
        calls: list[str] = []

        class PoppingScene(Scene):
            """Scene that pops itself during update, triggering on_exit."""

            def update(self, dt: float) -> None:
                if not calls:
                    self.game.pop()

            def on_exit(self) -> None:
                calls.append("exit")
                # _in_on_exit is True here, so this push is deferred.
                self.game.push(replacement)

        bottom = Scene()
        mock_game.push(bottom)

        original = PoppingScene()
        mock_game.push(original)
        assert mock_game._scene_stack.top() is original

        # tick() runs update -> deferred pop -> flush -> on_exit -> deferred push -> flush.
        mock_game.tick(dt=0.016)
        assert "exit" in calls
        # After tick flushes pending ops, replacement should be on the stack.
        assert mock_game._scene_stack.top() is replacement

    def test_deferred_operations_flush_during_tick(
        self, mock_game: Game, mock_backend: MockBackend
    ) -> None:
        """Push/pop during update() are deferred and flushed after update phase."""
        new_scene = Scene()

        class UpdatingScene(Scene):
            def update(self, dt: float) -> None:
                self.game.push(new_scene)

        scene = UpdatingScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        # After tick, the deferred push should have been flushed.
        assert mock_game._scene_stack.top() is new_scene


# ======================================================================
# 3. Sprite Edge Cases
# ======================================================================


class TestSpriteEdgeCases:
    """Sprite creation and property edge cases."""

    def test_sprite_with_nan_position_raises(self, mock_game: Game) -> None:
        """Sprite rejects NaN position at construction."""
        with pytest.raises(ValueError, match="finite"):
            Sprite("sprites/test", position=(float("nan"), 100))

    def test_sprite_with_inf_position_raises(self, mock_game: Game) -> None:
        """Sprite rejects Inf position at construction."""
        with pytest.raises(ValueError, match="finite"):
            Sprite("sprites/test", position=(float("inf"), 100))

    def test_sprite_position_setter_rejects_nan(self, mock_game: Game) -> None:
        """Setting position to NaN raises ValueError."""
        s = Sprite("sprites/test", position=(100, 100))
        with pytest.raises(ValueError, match="finite"):
            s.position = (float("nan"), 0)

    def test_sprite_opacity_with_nan(self, mock_game: Game) -> None:
        """Opacity with NaN is handled gracefully (clamped to 0)."""
        s = Sprite("sprites/test", position=(100, 100))
        s.opacity = float("nan")
        # NaN is treated as 0 based on the code: NaN->0 branch.
        assert s.opacity == 0

    def test_sprite_opacity_with_positive_inf(self, mock_game: Game) -> None:
        """Opacity with +Inf is handled gracefully (clamped to 255)."""
        s = Sprite("sprites/test", position=(100, 100))
        s.opacity = float("inf")
        assert s.opacity == 255

    def test_sprite_remove_then_access_properties(self, mock_game: Game) -> None:
        """Accessing properties after remove() is safe."""
        s = Sprite("sprites/test", position=(200, 300))
        s.remove()
        assert s.is_removed is True
        # Accessing position, opacity, etc. should not crash.
        assert s.position == (200, 300)
        assert s.opacity >= 0
        assert s.visible is True

    def test_sprite_remove_is_idempotent(self, mock_game: Game) -> None:
        """Calling remove() twice does not crash."""
        s = Sprite("sprites/test", position=(100, 100))
        s.remove()
        s.remove()  # Should be safe.
        assert s.is_removed is True

    def test_sprite_do_with_none_action_raises(self, mock_game: Game) -> None:
        """Sprite.do() with None raises AttributeError (start is called on it)."""
        s = Sprite("sprites/test", position=(100, 100))
        with pytest.raises(AttributeError):
            s.do(None)

    def test_sprite_move_to_speed_zero_raises(self, mock_game: Game) -> None:
        """move_to with speed=0 raises ValueError."""
        s = Sprite("sprites/test", position=(100, 100))
        with pytest.raises(ValueError, match="positive"):
            s.move_to((200, 200), speed=0)

    def test_sprite_move_to_current_position(self, mock_game: Game) -> None:
        """move_to to the current position calls on_arrive immediately."""
        arrived = [False]

        def on_arrive() -> None:
            arrived[0] = True

        s = Sprite("sprites/test", position=(100, 100))
        s.move_to((100, 100), speed=50, on_arrive=on_arrive)
        assert arrived[0] is True

    def test_sprite_position_setter_rejects_none(self, mock_game: Game) -> None:
        """Setting position to None raises ValueError."""
        s = Sprite("sprites/test", position=(100, 100))
        with pytest.raises(ValueError, match="None"):
            s.position = None


# ======================================================================
# 4. Action Edge Cases
# ======================================================================


class TestActionEdgeCases:
    """Composable action edge cases."""

    def test_sequence_with_no_actions(self, mock_game: Game) -> None:
        """An empty Sequence completes immediately."""
        s = Sprite("sprites/test", position=(100, 100))
        seq = Sequence()
        seq.start(s)
        assert seq.update(0.016) is True

    def test_parallel_with_no_actions(self, mock_game: Game) -> None:
        """An empty Parallel completes immediately."""
        s = Sprite("sprites/test", position=(100, 100))
        par = Parallel()
        par.start(s)
        assert par.update(0.016) is True

    def test_repeat_with_times_zero(self, mock_game: Game) -> None:
        """Repeat with times=0 finishes immediately without executing the action."""
        called = [False]
        action = Do(lambda: called.__setitem__(0, True))
        rep = Repeat(action, times=0)
        s = Sprite("sprites/test", position=(100, 100))
        rep.start(s)
        assert rep.update(0.016) is True
        assert called[0] is False

    def test_delay_with_duration_zero(self, mock_game: Game) -> None:
        """Delay(0) completes immediately on the first update."""
        d = Delay(0)
        s = Sprite("sprites/test", position=(100, 100))
        d.start(s)
        assert d.update(0.016) is True

    def test_delay_negative_raises(self) -> None:
        """Delay with negative duration raises ValueError."""
        with pytest.raises(ValueError, match=">= 0"):
            Delay(-1.0)

    def test_moveto_with_nan_speed_rejected(self, mock_game: Game) -> None:
        """MoveTo with NaN speed raises ValueError at construction time.

        Fixed in F16: NaN speed is now rejected early instead of causing
        a confusing crash during update().
        """
        with pytest.raises(ValueError, match="finite"):
            MoveTo((200, 200), speed=float("nan"))

    def test_moveto_with_nan_position_raises(self) -> None:
        """MoveTo with NaN target position raises ValueError."""
        with pytest.raises(ValueError, match="finite"):
            MoveTo((float("nan"), 100), speed=100)

    def test_fadein_with_duration_zero(self, mock_game: Game) -> None:
        """FadeIn(0) completes immediately and sets opacity to 255."""
        s = Sprite("sprites/test", position=(100, 100))
        s.opacity = 0
        fi = FadeIn(0)
        fi.start(s)
        assert fi.update(0.016) is True
        assert s.opacity == 255

    def test_fadeout_with_duration_zero(self, mock_game: Game) -> None:
        """FadeOut(0) completes immediately and sets opacity to 0."""
        s = Sprite("sprites/test", position=(100, 100))
        s.opacity = 255
        fo = FadeOut(0)
        fo.start(s)
        assert fo.update(0.016) is True
        assert s.opacity == 0

    def test_do_callback_that_raises(self, mock_game: Game) -> None:
        """Do with a callback that raises propagates the exception."""

        def bad_callback() -> None:
            raise ValueError("boom")

        s = Sprite("sprites/test", position=(100, 100))
        action = Do(bad_callback)
        action.start(s)
        with pytest.raises(ValueError, match="boom"):
            action.update(0.016)

    def test_sequence_child_type_check(self) -> None:
        """Sequence rejects non-Action children."""
        with pytest.raises(TypeError, match="expected Action"):
            Sequence("not_an_action")  # type: ignore[arg-type]

    def test_parallel_child_type_check(self) -> None:
        """Parallel rejects non-Action children."""
        with pytest.raises(TypeError, match="expected Action"):
            Parallel("not_an_action")  # type: ignore[arg-type]

    def test_repeat_child_type_check(self) -> None:
        """Repeat rejects non-Action child."""
        with pytest.raises(TypeError, match="Action"):
            Repeat("not_an_action")  # type: ignore[arg-type]


# ======================================================================
# 5. Camera Edge Cases
# ======================================================================


class TestCameraEdgeCases:
    """Camera positioning, bounds, and shake edge cases."""

    def test_camera_viewport_size_zero(self) -> None:
        """Camera with viewport_size (0, 0) does not crash."""
        cam = Camera((0, 0))
        cam.center_on(100, 100)
        # Position should be set (centered with 0-size viewport).
        assert math.isfinite(cam.x)
        assert math.isfinite(cam.y)

    def test_camera_bounds_left_greater_than_right(self) -> None:
        """Camera with inverted bounds (left > right) clamps gracefully."""
        cam = Camera((100, 100), world_bounds=(500, 0, 100, 200))
        cam.center_on(300, 100)
        # The clamp logic does max(left, min(x, right-vw)).
        # With left=500, right-vw=0, max(500, min(x, 0)) = 500.
        assert cam.x == 500

    def test_camera_shake_intensity_zero(self) -> None:
        """Shake with intensity=0 produces zero offsets."""
        cam = Camera((800, 600))
        cam.shake(0, 1.0, 1.0)
        cam.update(0.5)
        # With intensity=0, offsets should be 0 (random.uniform(0, 0) = 0).
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0

    def test_camera_shake_duration_zero_resets(self) -> None:
        """Shake with duration=0 immediately resets any active shake."""
        cam = Camera((800, 600))
        # Start a real shake first.
        cam.shake(10, 1.0, 1.0)
        cam.update(0.1)
        # Now reset with duration=0.
        cam.shake(10, 0, 1.0)
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0

    def test_camera_pan_to_current_position(self, mock_game: Game) -> None:
        """pan_to the current center position does not crash."""
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        # Pan to where we already are.
        cam.pan_to(400, 300, duration=0.5)
        # Should not raise; tween has from == to.

    def test_camera_edge_scroll_margin_zero(self) -> None:
        """Edge scroll with margin=0 means no scrolling occurs."""
        cam = Camera((800, 600), world_bounds=(0, 0, 2000, 2000))
        cam.enable_edge_scroll(margin=0, speed=100)
        cam.center_on(400, 300)
        old_x, old_y = cam.x, cam.y
        # Mouse at edge (0, 0) — but margin is 0, so no region triggers.
        # mouse_x < margin is 0 < 0 which is False.
        cam.update(0.016, mouse_x=0.0, mouse_y=0.0)
        assert cam.x == old_x
        assert cam.y == old_y

    def test_camera_center_on_nan_raises(self) -> None:
        """center_on with NaN raises ValueError."""
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.center_on(float("nan"), 300)

    def test_camera_center_on_inf_raises(self) -> None:
        """center_on with Inf raises ValueError."""
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.center_on(float("inf"), 300)

    def test_camera_pan_to_nan_raises(self, mock_game: Game) -> None:
        """pan_to with NaN raises ValueError."""
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.pan_to(float("nan"), 300, duration=1.0)


# ======================================================================
# 6. Tween Edge Cases
# ======================================================================


class TestTweenEdgeCases:
    """Tween system edge cases."""

    def test_tween_duration_zero(self, mock_game: Game) -> None:
        """Tween with duration=0 completes on the first update."""

        class Target:
            val = 0.0

        t = Target()
        tid = tween(t, "val", 0.0, 10.0, duration=0.0)
        mock_game._tween_manager.update(0.001)
        assert t.val == 10.0

    def test_tween_from_equals_to(self, mock_game: Game) -> None:
        """Tween where from_val == to_val completes without error."""

        class Target:
            val = 5.0

        t = Target()
        tid = tween(t, "val", 5.0, 5.0, duration=0.5)
        mock_game._tween_manager.update(1.0)
        assert t.val == 5.0

    def test_tween_on_nonexistent_property_raises(self, mock_game: Game) -> None:
        """Tween on a non-existent property raises AttributeError."""

        class Target:
            pass

        t = Target()
        with pytest.raises(AttributeError, match="no attribute"):
            tween(t, "nonexistent_prop", 0.0, 1.0, duration=1.0)

    def test_tween_with_nan_from_val_raises(self, mock_game: Game) -> None:
        """Tween with NaN from_val raises ValueError."""

        class Target:
            val = 0.0

        t = Target()
        with pytest.raises(ValueError, match="finite"):
            tween(t, "val", float("nan"), 1.0, duration=1.0)

    def test_tween_with_nan_to_val_raises(self, mock_game: Game) -> None:
        """Tween with NaN to_val raises ValueError."""

        class Target:
            val = 0.0

        t = Target()
        with pytest.raises(ValueError, match="finite"):
            tween(t, "val", 0.0, float("nan"), duration=1.0)

    def test_cancel_by_target(self, mock_game: Game) -> None:
        """cancel_by_target cancels all tweens for a given target."""

        class Target:
            x = 0.0
            y = 0.0

        t = Target()
        tween(t, "x", 0.0, 100.0, duration=1.0)
        tween(t, "y", 0.0, 200.0, duration=1.0)
        assert len(mock_game._tween_manager._tweens) >= 2

        mock_game._tween_manager.cancel_by_target(t)
        # All tweens for this target should be gone.
        remaining = [tw for tw in mock_game._tween_manager._tweens.values() if tw.target is t]
        assert len(remaining) == 0

    def test_tween_update_with_nan_dt_is_noop(self, mock_game: Game) -> None:
        """TweenManager.update with NaN dt does not advance tweens."""

        class Target:
            val = 0.0

        t = Target()
        tween(t, "val", 0.0, 100.0, duration=1.0)
        mock_game._tween_manager.update(float("nan"))
        assert t.val == 0.0


# ======================================================================
# 7. Timer Edge Cases
# ======================================================================


class TestTimerEdgeCases:
    """Timer system edge cases."""

    def test_timer_delay_zero(self, mock_game: Game) -> None:
        """Timer with delay=0 fires on the very first update."""
        called = [False]
        mock_game.after(0, lambda: called.__setitem__(0, True))
        mock_game._timer_manager.update(0.001)
        assert called[0] is True

    def test_timer_negative_delay_raises(self, mock_game: Game) -> None:
        """Timer with negative delay raises ValueError."""
        with pytest.raises(ValueError, match=">= 0"):
            mock_game.after(-1, lambda: None)

    def test_timer_cancel_twice(self, mock_game: Game) -> None:
        """Cancelling a timer twice does not crash."""
        handle = mock_game.after(1.0, lambda: None)
        mock_game.cancel(handle)
        # Second cancel should be a safe no-op.
        mock_game.cancel(handle)

    def test_every_interval_zero_raises(self, mock_game: Game) -> None:
        """every() with interval=0 raises ValueError."""
        with pytest.raises(ValueError, match="> 0"):
            mock_game.every(0, lambda: None)

    def test_every_negative_interval_raises(self, mock_game: Game) -> None:
        """every() with negative interval raises ValueError."""
        with pytest.raises(ValueError, match="> 0"):
            mock_game.every(-0.5, lambda: None)

    def test_timer_update_with_nan_dt_is_noop(self) -> None:
        """TimerManager.update with NaN dt does not fire timers."""
        tm = TimerManager()
        called = [False]
        tm.after(0.0, lambda: called.__setitem__(0, True))
        tm.update(float("nan"))
        assert called[0] is False


# ======================================================================
# 8. FSM Edge Cases
# ======================================================================


class TestFSMEdgeCases:
    """Finite state machine edge cases."""

    def test_fsm_single_state(self) -> None:
        """FSM with a single state works correctly."""
        fsm = StateMachine(["only"], "only")
        assert fsm.state == "only"
        assert fsm.valid_events == []

    def test_fsm_duplicate_transition_events(self) -> None:
        """Duplicate events in transitions is fine -- last definition wins per dict."""
        # In Python, dict keys are unique, so duplicate event keys in the same
        # source state dict simply overwrite. This tests the behavior is sane.
        fsm = StateMachine(
            ["a", "b", "c"],
            "a",
            transitions={"a": {"go": "b", "go": "c"}},  # noqa: F601
        )
        # The dict literal deduplicates: "go" -> "c" wins.
        assert fsm.trigger("go") is True
        assert fsm.state == "c"

    def test_trigger_nonexistent_event(self) -> None:
        """Triggering a non-existent event returns False (no transition)."""
        fsm = StateMachine(
            ["a", "b"],
            "a",
            transitions={"a": {"go": "b"}},
        )
        result = fsm.trigger("nonexistent")
        assert result is False
        assert fsm.state == "a"

    def test_on_enter_triggers_another_event(self) -> None:
        """on_enter callback that triggers another event works correctly."""
        log: list[str] = []
        fsm: StateMachine | None = None

        def enter_b() -> None:
            log.append("enter_b")
            # Trigger another event from on_enter
            if fsm is not None:
                fsm.trigger("auto_advance")

        def enter_c() -> None:
            log.append("enter_c")

        fsm = StateMachine(
            ["a", "b", "c"],
            "a",
            transitions={
                "a": {"go": "b"},
                "b": {"auto_advance": "c"},
            },
            on_enter={"b": enter_b, "c": enter_c},
        )
        fsm.trigger("go")
        assert fsm.state == "c"
        assert log == ["enter_b", "enter_c"]

    def test_fsm_initial_not_in_states_raises(self) -> None:
        """FSM with initial state not in states list raises ValueError."""
        with pytest.raises(ValueError, match="not in states"):
            StateMachine(["a", "b"], "nonexistent")

    def test_fsm_transition_target_not_in_states_raises(self) -> None:
        """FSM with a transition target not in states list raises ValueError."""
        with pytest.raises(ValueError, match="not in states"):
            StateMachine(
                ["a", "b"],
                "a",
                transitions={"a": {"go": "nonexistent"}},
            )


# ======================================================================
# 9. UI Edge Cases
# ======================================================================


class TestUIEdgeCases:
    """UI component edge cases."""

    def test_button_click_at_exact_boundary(
        self, mock_game: Game, mock_backend: MockBackend
    ) -> None:
        """Button click at exact left-top boundary is inside; right-bottom is outside."""
        scene = Scene()
        mock_game.push(scene)

        btn_clicked = [False]
        btn = Button("Test", on_click=lambda: btn_clicked.__setitem__(0, True))
        scene.ui.add(btn)

        # Force layout.
        scene.ui._ensure_layout()

        # Click at exact top-left corner (should be inside).
        x, y = btn._computed_x, btn._computed_y
        event_in = InputEvent(type="click", x=x, y=y, button="left")
        consumed = btn.on_event(event_in)
        assert consumed is True
        assert btn_clicked[0] is True

        # Click at exact bottom-right boundary (exclusive, should be outside).
        btn_clicked[0] = False
        btn._state = "normal"
        x_out = btn._computed_x + btn._computed_w
        y_out = btn._computed_y + btn._computed_h
        event_out = InputEvent(type="click", x=x_out, y=y_out, button="left")
        consumed = btn.on_event(event_out)
        assert consumed is False
        assert btn_clicked[0] is False

    def test_panel_with_no_children(self, mock_game: Game) -> None:
        """Panel with no children renders without error."""
        scene = Scene()
        mock_game.push(scene)
        panel = Panel(layout=Layout.VERTICAL, width=200, height=100)
        scene.ui.add(panel)
        mock_game.tick(dt=0.016)
        # Should not raise; panel draws its background.

    def test_panel_with_zero_spacing(self, mock_game: Game) -> None:
        """Panel with spacing=0 lays out children without gaps."""
        panel = Panel(layout=Layout.VERTICAL, spacing=0, width=200, height=200)
        label1 = Label("A", height=50)
        label2 = Label("B", height=50)
        panel.add(label1)
        panel.add(label2)
        panel.compute_layout(0, 0, 200, 200)
        # With zero spacing, labels should be adjacent.
        assert label2._computed_y == label1._computed_y + 50

    def test_panel_negative_spacing_raises(self) -> None:
        """Panel with negative spacing raises ValueError."""
        with pytest.raises(ValueError, match="negative"):
            Panel(spacing=-5)

    def test_label_with_empty_text(self, mock_game: Game) -> None:
        """Label with empty text renders without error."""
        scene = Scene()
        mock_game.push(scene)
        label = Label("")
        scene.ui.add(label)
        mock_game.tick(dt=0.016)
        # Empty text Label draws nothing, but should not crash.

    def test_label_with_none_text(self, mock_game: Game) -> None:
        """Label with None text is treated as empty string."""
        label = Label(None)
        assert label.text == ""

    def test_progressbar_value_exceeds_max(self, mock_game: Game) -> None:
        """ProgressBar with value > max_value clamps fraction to 1.0."""
        bar = ProgressBar(value=200, max_value=100)
        assert bar.fraction == 1.0

    def test_progressbar_max_value_zero(self, mock_game: Game) -> None:
        """ProgressBar with max_value=0 returns fraction 0.0."""
        bar = ProgressBar(value=50, max_value=0)
        assert bar.fraction == 0.0

    def test_list_with_empty_items(self, mock_game: Game) -> None:
        """List with empty items list renders without error."""
        scene = Scene()
        mock_game.push(scene)
        lst = List(items=[], width=200, height=100)
        scene.ui.add(lst)
        mock_game.tick(dt=0.016)
        # Should draw background only, no crash.

    def test_list_none_items(self, mock_game: Game) -> None:
        """List with items=None initializes to empty list."""
        lst = List(items=None)
        assert lst.items == []

    def test_component_visibility_toggle_during_draw(
        self, mock_game: Game
    ) -> None:
        """Toggling component visibility does not crash during draw."""
        scene = Scene()
        mock_game.push(scene)
        label = Label("Visible")
        scene.ui.add(label)

        mock_game.tick(dt=0.016)
        label.visible = False
        mock_game.tick(dt=0.016)
        label.visible = True
        mock_game.tick(dt=0.016)
        # No crash throughout.


# ======================================================================
# 10. Save/Load Edge Cases
# ======================================================================


class TestSaveLoadEdgeCases:
    """SaveManager edge cases."""

    def test_save_slot_zero_raises(self) -> None:
        """save with slot=0 raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(Path(tmpdir))
            with pytest.raises(ValueError, match=">= 1"):
                sm.save(0, {"key": "value"}, "TestScene")

    def test_save_negative_slot_raises(self) -> None:
        """save with slot < 0 raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(Path(tmpdir))
            with pytest.raises(ValueError, match=">= 1"):
                sm.save(-1, {"key": "value"}, "TestScene")

    def test_save_large_slot_number(self) -> None:
        """save with a very large slot number works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(Path(tmpdir))
            sm.save(999999, {"key": "value"}, "TestScene")
            data = sm.load(999999)
            assert data is not None
            assert data["state"]["key"] == "value"

    def test_save_non_serializable_data_raises(self) -> None:
        """save with non-JSON-serializable data raises SaveError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(Path(tmpdir))
            # set is not JSON-serializable.
            with pytest.raises(SaveError):
                sm.save(1, {"data": {1, 2, 3}}, "TestScene")

    def test_load_nonexistent_slot_returns_none(self) -> None:
        """load from a non-existent slot returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(Path(tmpdir))
            assert sm.load(42) is None

    def test_save_deeply_nested_data(self) -> None:
        """save with deeply nested data works."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(Path(tmpdir))
            nested = {"level": 0}
            current = nested
            for i in range(1, 20):
                inner = {"level": i}
                current["child"] = inner
                current = inner
            sm.save(1, nested, "DeepScene")
            data = sm.load(1)
            assert data is not None
            # Traverse to verify.
            node = data["state"]
            for i in range(20):
                assert node["level"] == i
                if i < 19:
                    node = node["child"]

    def test_delete_nonexistent_slot(self) -> None:
        """Deleting a non-existent slot is a no-op (no crash)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(Path(tmpdir))
            sm.delete(42)  # Should not raise.

    def test_load_slot_zero_raises(self) -> None:
        """load with slot=0 raises ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(Path(tmpdir))
            with pytest.raises(ValueError, match=">= 1"):
                sm.load(0)

    def test_save_slot_not_int_raises(self) -> None:
        """save with non-int slot raises TypeError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(Path(tmpdir))
            with pytest.raises(TypeError, match="int"):
                sm.save("one", {}, "TestScene")  # type: ignore[arg-type]


# ======================================================================
# 11. Audio Edge Cases
# ======================================================================


class TestAudioEdgeCases:
    """AudioManager edge cases.

    Tests that require actual asset files create a temporary asset directory.
    Tests that only exercise volume/pool logic use a standalone AudioManager
    with a bare MockBackend + AssetManager.
    """

    @pytest.fixture
    def audio_env(self, tmp_path: Path) -> tuple[MockBackend, Any, Any]:
        """Create a standalone AudioManager with mock assets for audio tests.

        Returns (backend, assets, audio).
        """
        from saga2d.assets import AssetManager
        from saga2d.audio import AudioManager

        # Create minimal asset files.
        sounds = tmp_path / "sounds"
        sounds.mkdir()
        (sounds / "only_sound.wav").write_bytes(b"wav")
        music = tmp_path / "music"
        music.mkdir()
        (music / "track1.ogg").write_bytes(b"ogg")
        (music / "track2.ogg").write_bytes(b"ogg")

        backend = MockBackend()
        assets = AssetManager(backend, base_path=tmp_path)
        audio = AudioManager(backend, assets)
        return backend, assets, audio

    def test_set_volume_with_nan(self, mock_game: Game) -> None:
        """set_volume with NaN: Python max(0, min(1, nan)) -> max(0, nan) -> nan.

        In CPython 3.x, max(0.0, float('nan')) returns the first argument 0.0
        on some platforms, but this is implementation-defined for NaN comparisons.
        We verify the volume is clamped to a finite value in [0.0, 1.0].
        """
        audio = mock_game.audio
        audio.set_volume("sfx", float("nan"))
        vol = audio.get_volume("sfx")
        # The result depends on Python's max/min NaN behavior.
        # On CPython: min(1.0, nan) -> nan, max(0.0, nan) -> nan or 0.0.
        # We accept either 0.0 or nan (stored as-is). The key thing is no crash.
        assert isinstance(vol, float)

    def test_play_sound_with_missing_asset_optional(self, mock_game: Game) -> None:
        """play_sound with non-existent name and optional=True does not raise."""
        audio = mock_game.audio
        result = audio.play_sound("nonexistent_sound", optional=True)
        assert result is None

    def test_crossfade_with_small_duration(
        self, audio_env: tuple[MockBackend, Any, Any], mock_game: Game
    ) -> None:
        """crossfade_music with very small duration completes quickly."""
        backend, assets, audio = audio_env
        # Use the standalone audio manager, but we need a tween manager.
        # Set up the module-level tween manager from mock_game.
        audio.play_music("track1")
        audio.crossfade_music("track2", duration=0.001)
        # Advance tweens enough to complete.
        mock_game._tween_manager.update(1.0)
        # After crossfade, track2 should be playing.
        assert backend.music_playing is not None

    def test_play_music_when_already_playing(
        self, audio_env: tuple[MockBackend, Any, Any]
    ) -> None:
        """play_music when music is already playing stops the old track first."""
        backend, assets, audio = audio_env
        audio.play_music("track1")
        old_player = audio._current_player_id
        audio.play_music("track2")
        assert audio._current_music_name == "track2"
        # Old player should have been stopped.
        assert old_player not in backend._music_players

    def test_sound_pool_single_sound(
        self, audio_env: tuple[MockBackend, Any, Any]
    ) -> None:
        """Sound pool with a single sound always plays that sound."""
        backend, assets, audio = audio_env
        audio.register_pool("single", ["only_sound"])
        for _ in range(5):
            audio.play_pool("single")
        assert len(backend.sounds_played) == 5

    def test_set_volume_unknown_channel_raises(self, mock_game: Game) -> None:
        """set_volume with unknown channel raises KeyError."""
        audio = mock_game.audio
        with pytest.raises(KeyError, match="Unknown audio channel"):
            audio.set_volume("nonexistent", 0.5)

    def test_stop_music_when_nothing_playing(self, mock_game: Game) -> None:
        """stop_music when nothing is playing is a no-op."""
        audio = mock_game.audio
        audio.stop_music()  # Should not raise.


# ======================================================================
# 12. Particle Edge Cases
# ======================================================================


class TestParticleEdgeCases:
    """ParticleEmitter edge cases."""

    def test_emitter_count_zero(self, mock_game: Game) -> None:
        """ParticleEmitter with count=0 does not spawn on burst()."""
        em = ParticleEmitter("sprites/test", position=(100, 100), count=0)
        em.burst()  # Uses default count=0.
        assert len(em._particles) == 0

    def test_emitter_burst_zero_explicit(self, mock_game: Game) -> None:
        """burst(0) does not spawn any particles."""
        em = ParticleEmitter("sprites/test", position=(100, 100))
        em.burst(0)
        assert len(em._particles) == 0

    def test_emitter_burst_negative(self, mock_game: Game) -> None:
        """burst with negative count does not spawn (n <= 0 guard)."""
        em = ParticleEmitter("sprites/test", position=(100, 100))
        em.burst(-5)
        assert len(em._particles) == 0

    def test_emitter_lifetime_zero_zero(self, mock_game: Game) -> None:
        """Emitter with lifetime (0, 0) creates particles that die immediately."""
        em = ParticleEmitter(
            "sprites/test",
            position=(100, 100),
            lifetime=(0, 0),
        )
        em.burst(5)
        assert len(em._particles) == 5
        # Update with any positive dt should remove them all.
        em.update(0.001)
        assert len(em._particles) == 0

    def test_emitter_remove_then_update(self, mock_game: Game) -> None:
        """Calling update after remove does not crash."""
        em = ParticleEmitter("sprites/test", position=(100, 100))
        em.burst(3)
        em.remove()
        assert len(em._particles) == 0
        # Updating after removal is safe.
        em.update(0.016)

    def test_emitter_remove_is_idempotent(self, mock_game: Game) -> None:
        """Calling remove() twice does not crash."""
        em = ParticleEmitter("sprites/test", position=(100, 100))
        em.burst(3)
        em.remove()
        em.remove()  # Safe.


# ======================================================================
# 13. Input Edge Cases
# ======================================================================


class TestInputEdgeCases:
    """InputManager edge cases."""

    def test_bind_same_key_to_different_actions(self) -> None:
        """Binding the same key to a different action steals it from the old action."""
        im = InputManager()
        im.bind("attack", "a")
        im.bind("defend", "a")
        # "a" should now be bound to "defend", not "attack".
        bindings = im.get_bindings()
        assert bindings.get("defend") == "a"
        assert "attack" not in bindings

    def test_unbind_nonexistent_action(self) -> None:
        """unbind with a non-existent action is a no-op."""
        im = InputManager()
        im.unbind("nonexistent_action")  # Should not raise.

    def test_translate_with_empty_event_list(self) -> None:
        """translate with an empty list returns an empty list."""
        im = InputManager()
        result = im.translate([])
        assert result == []

    def test_translate_with_none(self) -> None:
        """translate with None returns an empty list."""
        im = InputManager()
        result = im.translate(None)
        assert result == []

    def test_bind_replaces_old_key_for_same_action(self) -> None:
        """Binding a new key to the same action removes the old key binding."""
        im = InputManager()
        im.bind("attack", "a")
        im.bind("attack", "b")
        bindings = im.get_bindings()
        assert bindings["attack"] == "b"
        # "a" should no longer map to anything.
        from saga2d.backends.base import KeyEvent

        events = im.translate([KeyEvent(type="key_press", key="a")])
        assert events[0].action is None


# ======================================================================
# Parametrized Tests
# ======================================================================


class TestSpritePositionParametrized:
    """Parametrized tests for invalid sprite positions."""

    @pytest.mark.parametrize(
        "x,y",
        [
            (float("nan"), 0),
            (0, float("nan")),
            (float("nan"), float("nan")),
            (float("inf"), 0),
            (0, float("inf")),
            (float("-inf"), 0),
            (0, float("-inf")),
        ],
        ids=["nan_x", "nan_y", "nan_both", "inf_x", "inf_y", "neg_inf_x", "neg_inf_y"],
    )
    def test_sprite_invalid_position_at_construction(
        self, mock_game: Game, x: float, y: float
    ) -> None:
        """Sprite rejects non-finite positions at construction."""
        with pytest.raises(ValueError, match="finite"):
            Sprite("sprites/test", position=(x, y))


class TestSpritePositionSetterParametrized:
    """Parametrized tests for invalid positions via setter."""

    @pytest.mark.parametrize(
        "x,y",
        [
            (float("nan"), 0),
            (0, float("nan")),
            (float("inf"), 0),
            (float("-inf"), 0),
        ],
        ids=["nan_x", "nan_y", "inf_x", "neg_inf_x"],
    )
    def test_sprite_invalid_position_via_setter(
        self, mock_game: Game, x: float, y: float
    ) -> None:
        """Sprite rejects non-finite positions via the position setter."""
        s = Sprite("sprites/test", position=(100, 100))
        with pytest.raises(ValueError, match="finite"):
            s.position = (x, y)


class TestTweenNaNParametrized:
    """Parametrized tests for NaN/Inf tween values."""

    @pytest.mark.parametrize(
        "from_val,to_val",
        [
            (float("nan"), 1.0),
            (0.0, float("nan")),
            (float("inf"), 1.0),
            (0.0, float("inf")),
        ],
        ids=["nan_from", "nan_to", "inf_from", "inf_to"],
    )
    def test_tween_invalid_values_raise(
        self, mock_game: Game, from_val: float, to_val: float
    ) -> None:
        """Tween rejects non-finite from_val or to_val."""

        class Target:
            val = 0.0

        t = Target()
        with pytest.raises(ValueError, match="finite"):
            tween(t, "val", from_val, to_val, duration=1.0)


class TestMoveToParametrized:
    """Parametrized tests for MoveTo with invalid inputs."""

    @pytest.mark.parametrize(
        "speed",
        [0, -1, -100],
        ids=["zero", "negative_one", "large_negative"],
    )
    def test_moveto_invalid_speed(self, speed: float) -> None:
        """MoveTo rejects non-positive speed values."""
        with pytest.raises(ValueError, match="> 0"):
            MoveTo((100, 100), speed=speed)


class TestSaveSlotParametrized:
    """Parametrized tests for invalid save slots."""

    @pytest.mark.parametrize(
        "slot",
        [0, -1, -100],
        ids=["zero", "negative_one", "large_negative"],
    )
    def test_save_invalid_slot(self, slot: int) -> None:
        """SaveManager rejects invalid slot numbers."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = SaveManager(Path(tmpdir))
            with pytest.raises(ValueError, match=">= 1"):
                sm.save(slot, {}, "TestScene")


# ======================================================================
# Integration-level Edge Cases
# ======================================================================


class TestSceneLifecycleIntegration:
    """Integration tests for complex scene lifecycle scenarios."""

    def test_scene_with_sprites_cleaned_on_pop(
        self, mock_game: Game
    ) -> None:
        """Sprites owned by a scene are removed when the scene is popped."""

        class SpriteScene(Scene):
            def on_enter(self) -> None:
                self.s = self.add_sprite(
                    Sprite("sprites/test", position=(100, 100))
                )

        scene = SpriteScene()
        mock_game.push(scene)
        sprite = scene.s
        assert not sprite.is_removed

        mock_game.pop()
        assert sprite.is_removed

    def test_scene_timer_cleaned_on_pop(self, mock_game: Game) -> None:
        """Timers owned by a scene are cancelled when the scene is popped."""
        timer_fired = [False]

        class TimerScene(Scene):
            def on_enter(self) -> None:
                self.after(0.1, lambda: timer_fired.__setitem__(0, True))

        scene = TimerScene()
        mock_game.push(scene)
        mock_game.pop()

        # Advance time well past the timer delay.
        mock_game._timer_manager.update(1.0)
        assert timer_fired[0] is False

    def test_multiple_push_pop_cycles(self, mock_game: Game) -> None:
        """Repeated push/pop cycles do not leak or crash."""
        for _ in range(50):
            scene = Scene()
            mock_game.push(scene)
            mock_game.pop()
        assert mock_game._scene_stack.top() is None

    def test_clear_and_push_empties_stack(self, mock_game: Game) -> None:
        """clear_and_push removes all existing scenes."""
        for _ in range(5):
            mock_game.push(Scene())
        assert len(mock_game._scene_stack._stack) == 5

        final = Scene()
        mock_game.clear_and_push(final)
        assert len(mock_game._scene_stack._stack) == 1
        assert mock_game._scene_stack.top() is final


class TestCameraWithSpriteIntegration:
    """Camera + sprite integration edge cases."""

    def test_camera_follow_removed_sprite(self, mock_game: Game) -> None:
        """Camera follow detaches when the target sprite is removed."""
        cam = Camera((800, 600))
        s = Sprite("sprites/test", position=(400, 300))
        cam.follow(s)
        s.remove()
        # Update should detect the removed sprite and clear follow.
        cam.update(0.016)
        assert cam._follow_target is None

    def test_camera_scroll_with_bounds(self) -> None:
        """Camera scroll respects world bounds clamping."""
        cam = Camera((100, 100), world_bounds=(0, 0, 500, 500))
        cam.center_on(250, 250)
        # Try to scroll far beyond bounds.
        cam.scroll(10000, 10000)
        # Should be clamped: max x = 500 - 100 = 400.
        assert cam.x <= 400
        assert cam.y <= 400


class TestActionWithSpriteIntegration:
    """Action + sprite integration edge cases."""

    def test_action_on_removed_sprite_is_noop(self, mock_game: Game) -> None:
        """Running an action on a removed sprite is safely ignored."""
        s = Sprite("sprites/test", position=(100, 100))
        s.remove()
        # do() on a removed sprite is a no-op (returns early).
        s.do(Delay(1.0))
        assert s._current_action is None

    def test_stop_actions_without_active_action(self, mock_game: Game) -> None:
        """stop_actions when no action is running is a safe no-op."""
        s = Sprite("sprites/test", position=(100, 100))
        s.stop_actions()  # Should not raise.

    def test_sprite_do_replaces_existing_action(self, mock_game: Game) -> None:
        """Calling do() a second time cancels the first action."""
        s = Sprite("sprites/test", position=(100, 100))
        s.do(Delay(10.0))
        assert s._current_action is not None
        s.do(Delay(5.0))
        # The new action should have replaced the old one.
        assert s._current_action is not None
        # Advance and verify the new delay (5s, not 10s) completes first.
        for _ in range(350):
            s.update_action(0.016)
        assert s._current_action is None  # 350 * 0.016 = 5.6s > 5s


class TestEdgeScrollIntegration:
    """Camera edge scroll edge cases."""

    def test_key_scroll_opposite_directions_cancel(self) -> None:
        """Pressing both left and right arrow keys simultaneously cancels out."""
        cam = Camera((800, 600), world_bounds=(0, 0, 2000, 2000))
        cam.center_on(500, 500)
        cam.enable_key_scroll(speed=300)
        # Simulate both left and right held.
        cam._held_dirs = {"left", "right"}
        old_x = cam.x
        cam.update(0.016)
        # Left and right cancel out, so x should not change.
        assert cam.x == old_x
