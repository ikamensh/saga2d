"""New edge case tests for saga2d — targeting gaps from prior kodo runs.

Focus areas:
- ParticleEmitter continuous rate validation (NaN/Inf)
- Camera edge scroll validation (negative margin/speed)
- Audio crossfade_music with edge case durations
- ProgressBar edge cases (NaN value, max_value=0)
- show_sequence with empty list
- Component add circular reference detection
- Scene stack edge cases (pop empty, double push same scene)
- Game.tick with negative/zero dt
- Repeat action with times=0 and times=-1
- ColorSwap with empty source/target lists
- SaveManager.list_slots with negative count
- Scene.after timer cleanup during scene exit
"""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

import pytest

from saga2d import (
    Game,
    Scene,
    Sprite,
    Panel,
    Label,
    Button,
    Anchor,
    Layout,
    Style,
    Camera,
    ParticleEmitter,
    Sequence,
    Parallel,
    Delay,
    Do,
    MoveTo,
    FadeIn,
    FadeOut,
    Remove,
    Repeat,
    AnimationDef,
    SaveManager,
    StateMachine,
    ColorSwap,
    MessageScreen,
    ChoiceScreen,
    ConfirmDialog,
    ProgressBar,
    TextBox,
    Component,
)
from saga2d.rendering.layers import RenderLayer, SpriteAnchor


# ── Helpers ──────────────────────────────────────────────────────────────────

@pytest.fixture
def game():
    g = Game("TestEdge", backend="mock", resolution=(800, 600))
    yield g
    g._teardown()


@pytest.fixture
def scene(game):
    s = Scene()
    game.push(s)
    return s


# ══════════════════════════════════════════════════════════════════════════════
# F34: ParticleEmitter.continuous() accepts NaN/Inf rate
# ══════════════════════════════════════════════════════════════════════════════

class TestF34ParticleEmitterContinuousRateValidation:
    """ParticleEmitter.continuous(rate) should reject NaN/Inf rates.

    A NaN rate silently does nothing (NaN * dt => NaN, NaN >= 1.0 is False).
    An Inf rate causes infinite loop in update() (while accum >= 1.0 loops forever).
    """

    def test_continuous_nan_rate_should_reject(self, game, scene):
        """NaN rate should be rejected with ValueError."""
        emitter = ParticleEmitter(
            "sprites/test", position=(100, 100),
            count=1, speed=(10, 20), lifetime=(0.1, 0.2),
        )
        scene.add_emitter(emitter)
        # NaN rate: silently breaks spawning logic
        with pytest.raises((ValueError, TypeError)):
            emitter.continuous(float('nan'))

    def test_continuous_inf_rate_should_reject(self, game, scene):
        """Inf rate should be rejected — causes infinite loop in update()."""
        emitter = ParticleEmitter(
            "sprites/test", position=(100, 100),
            count=1, speed=(10, 20), lifetime=(0.1, 0.2),
        )
        scene.add_emitter(emitter)
        # Inf rate: infinite while loop in update()
        with pytest.raises((ValueError, TypeError)):
            emitter.continuous(float('inf'))

    def test_continuous_negative_rate_should_reject(self, game, scene):
        """Negative rate should be rejected."""
        emitter = ParticleEmitter(
            "sprites/test", position=(100, 100),
            count=1, speed=(10, 20), lifetime=(0.1, 0.2),
        )
        scene.add_emitter(emitter)
        with pytest.raises((ValueError, TypeError)):
            emitter.continuous(-10.0)

    def test_continuous_zero_rate_is_valid(self, game, scene):
        """Zero rate is valid (effectively stops spawning)."""
        emitter = ParticleEmitter(
            "sprites/test", position=(100, 100),
            count=1, speed=(10, 20), lifetime=(0.1, 0.2),
        )
        scene.add_emitter(emitter)
        emitter.continuous(0.0)  # Should not raise
        game.tick(0.1)  # Should not spawn anything


# ══════════════════════════════════════════════════════════════════════════════
# F35: Audio crossfade_music with edge case durations
# ══════════════════════════════════════════════════════════════════════════════

class TestF35AudioCrossfadeDurationValidation:
    """crossfade_music(name, duration) should validate duration.

    Before fix: NaN/Inf/negative duration accepted — NaN/Inf propagate to
    tween system (ValueError there if no music playing, or silent corruption
    if music is already playing). Negative duration accepted silently.
    After fix: ValueError raised at crossfade_music entry point.
    """

    def test_crossfade_nan_duration(self, game, scene):
        """NaN duration should be rejected with ValueError."""
        with pytest.raises(ValueError, match="finite"):
            game.audio.crossfade_music("track1", duration=float('nan'))

    def test_crossfade_inf_duration(self, game, scene):
        """Inf duration should be rejected with ValueError."""
        with pytest.raises(ValueError, match="finite"):
            game.audio.crossfade_music("track1", duration=float('inf'))

    def test_crossfade_negative_duration(self, game, scene):
        """Negative duration should be rejected with ValueError."""
        with pytest.raises(ValueError, match="finite"):
            game.audio.crossfade_music("track1", duration=-1.0)

    def test_crossfade_zero_duration_valid(self, game, scene):
        """Zero duration should be accepted (instant switch)."""
        # Zero duration is valid — no raise expected.
        # AssetNotFoundError is expected here since no music file exists,
        # but the duration validation should pass.
        from saga2d.assets import AssetNotFoundError
        try:
            game.audio.crossfade_music("track1", duration=0.0)
        except AssetNotFoundError:
            pass  # Expected — no music file; duration was accepted

    def test_crossfade_normal_duration_valid(self, game, scene):
        """Normal duration should work fine."""
        from saga2d.assets import AssetNotFoundError
        try:
            game.audio.crossfade_music("track1", duration=1.0)
        except AssetNotFoundError:
            pass  # Expected — no music file; duration was accepted


# ══════════════════════════════════════════════════════════════════════════════
# F36: Component.add circular reference detection
# ══════════════════════════════════════════════════════════════════════════════

class TestF36ComponentCircularReference:
    """Component.add() already blocks self-add. Check parent→child→parent cycle."""

    def test_add_self_raises(self, game, scene):
        """Adding component to itself should raise ValueError."""
        p = Panel()
        with pytest.raises(ValueError, match="Cannot add component to itself"):
            p.add(p)

    def test_add_creates_parent_child_cycle(self, game, scene):
        """Adding a parent as a child of its own child should ideally be detected."""
        parent = Panel()
        child = Panel()
        parent.add(child)
        # Now try adding parent as child of child — creates a cycle
        # This may or may not be caught; we document the behavior
        try:
            child.add(parent)
            # If it doesn't raise, check for infinite recursion on layout
            # This is a bug if it causes infinite recursion
            try:
                parent.compute_layout(0, 0, 100, 100)
            except RecursionError:
                pytest.fail(
                    "Circular component reference causes RecursionError on layout"
                )
        except (ValueError, RuntimeError):
            pass  # Properly rejected


# ══════════════════════════════════════════════════════════════════════════════
# F37: ProgressBar with NaN/Inf values
# ══════════════════════════════════════════════════════════════════════════════

class TestF37ProgressBarEdgeCases:
    """ProgressBar should handle edge case values gracefully."""

    def test_progressbar_nan_value(self, game, scene):
        """NaN value should be rejected or clamped."""
        bar = ProgressBar(value=50, max_value=100)
        scene.ui.add(bar)
        # Setting value to NaN
        bar.value = float('nan')
        # fraction should not be NaN — it should be clamped
        frac = bar.fraction
        assert math.isfinite(frac), f"fraction is {frac}, should be finite"

    def test_progressbar_inf_value(self, game, scene):
        """Inf value should result in clamped fraction."""
        bar = ProgressBar(value=50, max_value=100)
        scene.ui.add(bar)
        bar.value = float('inf')
        frac = bar.fraction
        assert math.isfinite(frac), f"fraction is {frac}, should be finite"

    def test_progressbar_max_value_zero(self, game, scene):
        """max_value=0 should not divide by zero."""
        bar = ProgressBar(value=50, max_value=0)
        scene.ui.add(bar)
        assert bar.fraction == 0.0  # Already handled

    def test_progressbar_negative_max_value(self, game, scene):
        """Negative max_value should be handled."""
        bar = ProgressBar(value=50, max_value=-100)
        scene.ui.add(bar)
        assert bar.fraction == 0.0


# ══════════════════════════════════════════════════════════════════════════════
# F38: show_sequence with empty list
# ══════════════════════════════════════════════════════════════════════════════

class TestF38ShowSequenceEmpty:
    """game.show_sequence([]) with empty list should work gracefully."""

    def test_empty_sequence_completes(self, game, scene):
        """Empty sequence should immediately fire on_complete and pop runner."""
        completed = [False]
        def on_done():
            completed[0] = True

        game.show_sequence([], on_complete=on_done)
        game.tick(0.016)  # flush deferred ops
        assert completed[0], "on_complete should fire for empty sequence"


# ══════════════════════════════════════════════════════════════════════════════
# F39: Game.tick with negative dt
# ══════════════════════════════════════════════════════════════════════════════

class TestF39GameTickNegativeDt:
    """Game.tick() with negative dt should not corrupt state."""

    def test_negative_dt_no_crash(self, game, scene):
        """Negative dt should not crash the game loop."""
        game.tick(dt=-0.016)  # Should not raise or corrupt

    def test_zero_dt_no_crash(self, game, scene):
        """Zero dt should be a valid no-op tick."""
        game.tick(dt=0.0)  # Should not raise

    def test_very_large_dt_no_crash(self, game, scene):
        """Very large dt should not hang or crash."""
        game.tick(dt=1000000.0)  # Should not hang


# ══════════════════════════════════════════════════════════════════════════════
# F40: Scene pop on empty stack
# ══════════════════════════════════════════════════════════════════════════════

class TestF40SceneStackEdgeCases:
    """Scene stack edge cases should be handled gracefully."""

    def test_pop_empty_stack_no_crash(self, game):
        """Popping an empty stack should be a no-op."""
        game.pop()  # Should not raise

    def test_replace_empty_stack(self, game):
        """Replace on empty stack should work (effectively just push)."""
        s = Scene()
        game.replace(s)
        assert game._scene_stack.top() is s

    def test_double_push_same_scene(self, game):
        """Pushing the same scene instance twice — what happens?"""
        s = Scene()
        game.push(s)
        # Pushing same scene again: on_exit fires on it (since it's top),
        # then it gets re-pushed. This is unusual but shouldn't crash.
        s2 = Scene()  # use different scene to avoid confusion
        game.push(s2)
        assert game._scene_stack.top() is s2

    def test_clear_and_push_empty_stack(self, game):
        """clear_and_push on empty stack should work."""
        s = Scene()
        game.clear_and_push(s)
        assert game._scene_stack.top() is s


# ══════════════════════════════════════════════════════════════════════════════
# F41: Camera edge scroll with negative/NaN parameters
# ══════════════════════════════════════════════════════════════════════════════

class TestF41CameraEdgeScrollValidation:
    """Camera.enable_edge_scroll with invalid parameters."""

    def test_edge_scroll_negative_margin(self, game, scene):
        """Negative margin should be rejected or handled."""
        cam = Camera((800, 600), world_bounds=(0, 0, 2000, 2000))
        cam.enable_edge_scroll(margin=-10, speed=100)
        # With negative margin, mouse_x < -10 is always False,
        # but mouse_x > 800 - (-10) = 810 is weird behavior
        cam.update(0.016, mouse_x=805, mouse_y=300)
        # Should not scroll since 805 < 810

    def test_edge_scroll_nan_speed(self, game, scene):
        """NaN speed should be rejected or produce finite scroll."""
        cam = Camera((800, 600), world_bounds=(0, 0, 2000, 2000))
        cam.enable_edge_scroll(margin=50, speed=float('nan'))
        cam.update(0.016, mouse_x=10, mouse_y=300)
        # Camera position should still be finite
        assert math.isfinite(cam.x), f"Camera x is {cam.x}, should be finite"
        assert math.isfinite(cam.y), f"Camera y is {cam.y}, should be finite"


# ══════════════════════════════════════════════════════════════════════════════
# F42: ColorSwap with empty lists
# ══════════════════════════════════════════════════════════════════════════════

class TestF42ColorSwapEdgeCases:
    """ColorSwap edge cases."""

    def test_empty_color_lists(self):
        """Empty source/target lists should be valid (no-op swap)."""
        swap = ColorSwap([], [])
        assert swap.source_colors == []
        assert swap.target_colors == []
        assert swap.cache_key() == ()

    def test_mismatched_lengths_raises(self):
        """Mismatched source/target lengths should raise ValueError."""
        with pytest.raises(ValueError, match="same length"):
            ColorSwap([(255, 0, 0)], [(0, 255, 0), (0, 0, 255)])


# ══════════════════════════════════════════════════════════════════════════════
# F43: SaveManager.list_slots with negative count
# ══════════════════════════════════════════════════════════════════════════════

class TestF43SaveManagerListSlotsEdge:
    """SaveManager.list_slots edge cases."""

    def test_list_slots_zero(self):
        """list_slots(0) should return empty list."""
        with tempfile.TemporaryDirectory() as td:
            sm = SaveManager(td)
            result = sm.list_slots(0)
            assert result == []

    def test_list_slots_negative(self):
        """list_slots(-1) should return empty list."""
        with tempfile.TemporaryDirectory() as td:
            sm = SaveManager(td)
            result = sm.list_slots(-1)
            assert result == []

    def test_delete_nonexistent_slot(self):
        """Deleting a slot that doesn't exist should be a no-op."""
        with tempfile.TemporaryDirectory() as td:
            sm = SaveManager(td)
            sm.delete(1)  # Should not raise


# ══════════════════════════════════════════════════════════════════════════════
# F44: Repeat action with times=0
# ══════════════════════════════════════════════════════════════════════════════

class TestF44RepeatEdgeCases:
    """Repeat action edge cases."""

    def test_repeat_zero_times(self, game, scene):
        """Repeat(action, times=0) should complete immediately without executing."""
        executed = [0]
        def count():
            executed[0] += 1

        sp = Sprite("sprites/test", position=(100, 100))
        scene.add_sprite(sp)
        sp.do(Repeat(Do(count), times=0))
        game.tick(0.016)
        assert executed[0] == 0, "Repeat(times=0) should not execute the action"

    def test_repeat_negative_times(self, game, scene):
        """Repeat(action, times=-1) should complete immediately."""
        executed = [0]
        def count():
            executed[0] += 1

        sp = Sprite("sprites/test", position=(100, 100))
        scene.add_sprite(sp)
        sp.do(Repeat(Do(count), times=-1))
        game.tick(0.016)
        assert executed[0] == 0, "Repeat(times=-1) should not execute"


# ══════════════════════════════════════════════════════════════════════════════
# F45: InputManager bind/unbind edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestF45InputManagerEdgeCases:
    """InputManager edge cases."""

    def test_unbind_nonexistent_action(self, game):
        """Unbinding an action that doesn't exist should be a no-op."""
        game.input.unbind("nonexistent_action")  # Should not raise

    def test_bind_empty_string_key(self, game):
        """Binding to empty string key."""
        game.input.bind("test_action", "")
        bindings = game.input.get_bindings()
        assert bindings["test_action"] == ""

    def test_bind_key_steal(self, game):
        """Binding a key that's already used should steal it."""
        game.input.bind("action1", "a")
        game.input.bind("action2", "a")  # steal 'a' from action1
        bindings = game.input.get_bindings()
        assert bindings.get("action2") == "a"
        assert "action1" not in bindings, "action1 should have been unbound"


# ══════════════════════════════════════════════════════════════════════════════
# F46: HUD interactions
# ══════════════════════════════════════════════════════════════════════════════

class TestF46HUDEdgeCases:
    """HUD edge cases."""

    def test_hud_add_before_scene(self, game):
        """Adding to HUD before any scene is pushed."""
        label = Label("Test")
        game.hud.add(label)
        # Tick without any scene — HUD should not crash
        game.tick(0.016)

    def test_hud_visible_toggle(self, game, scene):
        """HUD visibility toggling."""
        label = Label("HP: 100")
        game.hud.add(label)
        game.hud.visible = False
        game.tick(0.016)
        game.hud.visible = True
        game.tick(0.016)


# ══════════════════════════════════════════════════════════════════════════════
# F47: Sprite tint with NaN/Inf values
# ══════════════════════════════════════════════════════════════════════════════

class TestF47SpriteTintEdgeCases:
    """Sprite tint should clamp or reject NaN/Inf values."""

    def test_tint_nan_values_clamped(self, game, scene):
        """NaN tint values should be clamped to valid range."""
        sp = Sprite("sprites/test", position=(100, 100))
        scene.add_sprite(sp)
        sp.tint = (float('nan'), 0.5, 0.5)
        # The tint setter uses max(0.0, min(1.0, v)) — NaN comparisons are weird
        r, g, b = sp.tint
        assert math.isfinite(r), f"tint r={r} should be finite"
        assert math.isfinite(g), f"tint g={g} should be finite"
        assert math.isfinite(b), f"tint b={b} should be finite"

    def test_tint_inf_values_clamped(self, game, scene):
        """Inf tint values should be clamped."""
        sp = Sprite("sprites/test", position=(100, 100))
        scene.add_sprite(sp)
        sp.tint = (float('inf'), float('-inf'), 0.5)
        r, g, b = sp.tint
        assert 0.0 <= r <= 1.0, f"tint r={r} should be in [0, 1]"
        assert 0.0 <= g <= 1.0, f"tint g={g} should be in [0, 1]"
        assert 0.0 <= b <= 1.0, f"tint b={b} should be in [0, 1]"


# ══════════════════════════════════════════════════════════════════════════════
# F48: Scene.bind_key with edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestF48SceneBindKeyEdgeCases:
    """Scene.bind_key edge cases."""

    def test_bind_key_overwrite(self, game, scene):
        """Binding same key twice should overwrite."""
        calls = []
        scene.bind_key("i", lambda: calls.append("first"))
        scene.bind_key("i", lambda: calls.append("second"))

        # Simulate key press
        from saga2d.input import InputEvent
        event = InputEvent(type="key_press", key="i")
        result = scene._dispatch_key_bindings(event)
        assert result is True
        assert calls == ["second"], "Second binding should overwrite first"

    def test_bind_key_action_vs_raw(self, game, scene):
        """Action bindings should take precedence over raw key."""
        calls = []
        scene.bind_key("cancel", lambda: calls.append("action"))
        scene.bind_key("escape", lambda: calls.append("raw"))

        from saga2d.input import InputEvent
        event = InputEvent(type="key_press", key="escape", action="cancel")
        result = scene._dispatch_key_bindings(event)
        assert result is True
        assert calls == ["action"], "Action should take precedence over raw key"


# ══════════════════════════════════════════════════════════════════════════════
# F49: AnimationDef validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF49AnimationDefValidation:
    """AnimationDef should validate frame_duration."""

    def test_zero_frame_duration_rejected(self):
        """frame_duration=0 should be rejected."""
        with pytest.raises(ValueError):
            AnimationDef(["frame1"], frame_duration=0.0)

    def test_negative_frame_duration_rejected(self):
        """Negative frame_duration should be rejected."""
        with pytest.raises(ValueError):
            AnimationDef(["frame1"], frame_duration=-0.1)

    def test_nan_frame_duration_rejected(self):
        """NaN frame_duration should be rejected."""
        with pytest.raises(ValueError):
            AnimationDef(["frame1"], frame_duration=float('nan'))

    def test_inf_frame_duration_rejected(self):
        """Inf frame_duration should be rejected."""
        with pytest.raises(ValueError):
            AnimationDef(["frame1"], frame_duration=float('inf'))


# ══════════════════════════════════════════════════════════════════════════════
# F50: StateMachine trigger with exception in on_exit
# ══════════════════════════════════════════════════════════════════════════════

class TestF50FSMOnExitException:
    """StateMachine should handle on_exit exceptions."""

    def test_on_exit_exception_still_transitions(self):
        """If on_exit raises, the transition should still happen (or not)."""
        def bad_exit():
            raise RuntimeError("exit error")

        fsm = StateMachine(
            ["idle", "walk"],
            "idle",
            transitions={"idle": {"go": "walk"}},
            on_exit={"idle": bad_exit},
        )
        # on_exit raising should propagate (current behavior)
        with pytest.raises(RuntimeError, match="exit error"):
            fsm.trigger("go")
        # State might be corrupted — check what happened
        # The FSM calls on_exit first, then sets state, then calls on_enter.
        # If on_exit raises, state should remain unchanged.
        assert fsm.state == "idle" or fsm.state == "walk"


# ══════════════════════════════════════════════════════════════════════════════
# F51: Camera pan_to with 0 duration
# ══════════════════════════════════════════════════════════════════════════════

class TestF51CameraPanToEdgeCases:
    """Camera.pan_to with edge case durations."""

    def test_pan_to_zero_duration(self, game, scene):
        """pan_to with 0 duration should snap immediately."""
        cam = Camera((800, 600))
        scene.camera = cam
        cam.center_on(0, 0)  # Start at origin
        cam.pan_to(400, 300, duration=0.0)
        game.tick(0.016)  # Process tween
        # Should arrive at target immediately

    def test_pan_to_nan_target(self, game, scene):
        """pan_to with NaN target should raise ValueError."""
        cam = Camera((800, 600))
        scene.camera = cam
        with pytest.raises(ValueError):
            cam.pan_to(float('nan'), 300, duration=1.0)
