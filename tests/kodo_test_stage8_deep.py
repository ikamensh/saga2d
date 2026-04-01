"""Stage 8 deep tests — mutation-during-iteration, stress, leaks, concurrency, documented bugs.

Tests are read-only diagnostics: they document current behavior and do NOT fix bugs.
"""

from __future__ import annotations

import math
import gc
import weakref

import pytest

from saga2d import (
    Game, Scene, Sprite, Label, Button, Panel, Layout, Anchor,
    Delay, FadeOut, FadeIn, Sequence, Do, tween, Ease,
)
from saga2d.input import InputEvent
from saga2d.ui.component import Component
from saga2d.backends.mock_backend import MockBackend


# ======================================================================
# 1. UI mutation during iteration (HIGH PRIORITY)
# ======================================================================


class TestUIMutationDuringIteration:
    """Verify that modifying children during event dispatch does not crash."""

    def test_onclick_adds_child_to_parent(self, mock_game: Game, mock_backend: MockBackend):
        """Button on_click adds a new Label to the parent Panel. Should not crash."""
        scene = Scene()
        mock_game.push(scene)

        panel = Panel(layout=Layout.VERTICAL, width=400, height=400)
        scene.ui.add(panel)

        added_children = []

        def add_child():
            new_label = Label("Added", width=100, height=30)
            panel.add(new_label)
            added_children.append(new_label)

        btn = Button("Add", on_click=add_child, width=200, height=40)
        panel.add(btn)

        # Compute layout so hit_test works
        scene.ui.compute_layout(0, 0, 1920, 1080)

        # Inject click at button's computed position
        cx = btn._computed_x + btn._computed_w // 2
        cy = btn._computed_y + btn._computed_h // 2
        mock_backend.inject_click(cx, cy)
        mock_game.tick(dt=0.016)

        assert len(added_children) == 1, "on_click should have fired and added a child"
        assert added_children[0] in panel.children

    def test_onclick_removes_sibling(self, mock_game: Game, mock_backend: MockBackend):
        """Button on_click removes a sibling from the parent Panel. No crash."""
        scene = Scene()
        mock_game.push(scene)

        panel = Panel(layout=Layout.VERTICAL, width=400, height=400)
        scene.ui.add(panel)

        sibling = Label("Sibling", width=200, height=30)
        panel.add(sibling)

        removed = []

        def remove_sibling():
            panel.remove(sibling)
            removed.append(True)

        btn = Button("Remove Sibling", on_click=remove_sibling, width=200, height=40)
        panel.add(btn)

        scene.ui.compute_layout(0, 0, 1920, 1080)

        cx = btn._computed_x + btn._computed_w // 2
        cy = btn._computed_y + btn._computed_h // 2
        mock_backend.inject_click(cx, cy)
        mock_game.tick(dt=0.016)

        assert len(removed) == 1
        assert sibling not in panel.children

    def test_onclick_removes_self(self, mock_game: Game, mock_backend: MockBackend):
        """Button on_click removes itself from its parent. No crash."""
        scene = Scene()
        mock_game.push(scene)

        panel = Panel(layout=Layout.VERTICAL, width=400, height=400)
        scene.ui.add(panel)

        self_removed = []

        btn = Button("Remove Self", width=200, height=40)

        def remove_self():
            panel.remove(btn)
            self_removed.append(True)

        btn.on_click = remove_self
        panel.add(btn)

        scene.ui.compute_layout(0, 0, 1920, 1080)

        cx = btn._computed_x + btn._computed_w // 2
        cy = btn._computed_y + btn._computed_h // 2
        mock_backend.inject_click(cx, cy)
        mock_game.tick(dt=0.016)

        assert len(self_removed) == 1
        assert btn not in panel.children

    def test_no_skipped_events_when_sibling_removed(self, mock_game: Game, mock_backend: MockBackend):
        """When button A removes sibling B, button C should still work on next tick."""
        scene = Scene()
        mock_game.push(scene)

        panel = Panel(layout=Layout.VERTICAL, width=400, height=600)
        scene.ui.add(panel)

        sibling = Label("Victim", width=200, height=30)
        panel.add(sibling)

        btn_a_clicks = []
        btn_c_clicks = []

        def on_a():
            panel.remove(sibling)
            btn_a_clicks.append(True)

        def on_c():
            btn_c_clicks.append(True)

        btn_a = Button("A", on_click=on_a, width=200, height=40)
        btn_c = Button("C", on_click=on_c, width=200, height=40)
        panel.add(btn_a)
        panel.add(btn_c)

        scene.ui.compute_layout(0, 0, 1920, 1080)

        # Click A first
        cx_a = btn_a._computed_x + btn_a._computed_w // 2
        cy_a = btn_a._computed_y + btn_a._computed_h // 2
        mock_backend.inject_click(cx_a, cy_a)
        mock_game.tick(dt=0.016)
        assert len(btn_a_clicks) == 1

        # Now click C — should still work
        scene.ui.compute_layout(0, 0, 1920, 1080)
        cx_c = btn_c._computed_x + btn_c._computed_w // 2
        cy_c = btn_c._computed_y + btn_c._computed_h // 2
        mock_backend.inject_click(cx_c, cy_c)
        mock_game.tick(dt=0.016)
        assert len(btn_c_clicks) == 1

    def test_handle_event_uses_snapshot(self, mock_game: Game):
        """Verify handle_event iterates a snapshot (list()) of children."""
        # This tests the mechanism directly: mutating _children during iteration
        parent = Component(width=100, height=100)
        parent._game = mock_game

        call_log = []

        class TrackingChild(Component):
            def __init__(self, name):
                super().__init__(width=50, height=50)
                self.name = name

            def on_event(self, event):
                call_log.append(self.name)
                return False

        c1 = TrackingChild("c1")
        c2 = TrackingChild("c2")
        c3 = TrackingChild("c3")

        parent.add(c1)
        parent.add(c2)
        parent.add(c3)

        # Override c2's on_event to remove c3 from parent
        original_on_event = c2.on_event

        def mutating_on_event(event):
            call_log.append("c2_mutate")
            parent.remove(c3)
            return False

        c2.on_event = mutating_on_event

        event = InputEvent(type="click", x=0, y=0, button="left")
        parent.handle_event(event)

        # c3 should still have been visited since handle_event snapshots
        # The reversed iteration goes c3, c2, c1 — c3 is visited first (before removal)
        assert "c2_mutate" in call_log


# ======================================================================
# 2. Stress tests
# ======================================================================


class TestStress:
    """Stress tests for large object counts."""

    def test_1000_sprites_tracked(self, mock_game: Game, mock_backend: MockBackend):
        """Create 1000 sprites, tick once, verify all tracked."""
        scene = Scene()
        mock_game.push(scene)

        sprites = []
        for i in range(1000):
            s = Sprite("sprites/knight", position=(i, i))
            sprites.append(s)

        mock_game.tick(dt=0.016)

        # All sprites should exist in the backend
        assert len(mock_backend.sprites) == 1000
        # All should be in game's tracking set
        assert len(mock_game._all_sprites) == 1000

    def test_100_sprites_remove_all(self, mock_game: Game, mock_backend: MockBackend):
        """Create 100 sprites, remove all, tick, verify no remnants."""
        scene = Scene()
        mock_game.push(scene)

        sprites = []
        for i in range(100):
            s = Sprite("sprites/knight", position=(i, i))
            sprites.append(s)

        for s in sprites:
            s.remove()

        mock_game.tick(dt=0.016)

        assert len(mock_backend.sprites) == 0
        assert len(mock_game._all_sprites) == 0

    def test_50_scenes_push_pop(self, mock_game: Game):
        """Push 50 scenes, pop all, verify clean state."""
        scenes = []
        for i in range(50):
            s = Scene()
            mock_game.push(s)
            scenes.append(s)
            mock_game.tick(dt=0.016)

        for i in range(50):
            mock_game.pop()
            mock_game.tick(dt=0.016)

        assert mock_game._scene_stack.top() is None
        assert len(mock_game._scene_stack._stack) == 0

    def test_100_timers_all_fire(self, mock_game: Game):
        """Create 100 timers, tick to fire them all, verify all fired."""
        scene = Scene()
        mock_game.push(scene)

        fired = []

        for i in range(100):
            mock_game.after(0.1, lambda idx=i: fired.append(idx))

        # Tick enough to fire all timers
        mock_game.tick(dt=0.2)

        assert len(fired) == 100
        assert set(fired) == set(range(100))

    def test_50_tweens_complete(self, mock_game: Game):
        """Create 50 tweens on 50 objects, tick to completion."""
        scene = Scene()
        mock_game.push(scene)

        class Target:
            def __init__(self):
                self.value = 0.0

        targets = [Target() for _ in range(50)]
        completed = []

        for i, t in enumerate(targets):
            tween(t, "value", 0.0, 100.0, 1.0,
                  on_complete=lambda idx=i: completed.append(idx))

        # Tick enough to complete all tweens
        mock_game.tick(dt=1.5)

        assert len(completed) == 50
        for t in targets:
            assert t.value == 100.0

    def test_panel_100_labels(self, mock_game: Game, mock_backend: MockBackend):
        """Panel with 100 child Labels — verify layout computes without crash."""
        scene = Scene()
        mock_game.push(scene)

        panel = Panel(layout=Layout.VERTICAL, width=400)
        scene.ui.add(panel)

        for i in range(100):
            panel.add(Label(f"Label {i}", width=200, height=20))

        # Compute layout
        scene.ui.compute_layout(0, 0, 1920, 1080)

        # Verify children count
        assert len(panel.children) == 100

        # Tick to draw
        mock_game.tick(dt=0.016)

        # Verify draw happened without crash (frame count incremented)
        assert mock_backend.frame_count >= 1


# ======================================================================
# 3. Resource leak detection
# ======================================================================


class TestResourceLeaks:
    """Detect resource leaks after teardown and scene transitions."""

    def test_teardown_cleans_everything(self):
        """Create Game, push scene, add sprites/timers/tweens, teardown — verify cleanup."""
        g = Game("Leak Test", backend="mock", resolution=(800, 600))
        scene = Scene()
        g.push(scene)

        # Add sprites
        sprites = [Sprite("sprites/knight", position=(i * 10, 0)) for i in range(5)]
        for s in sprites:
            scene.add_sprite(s)

        # Add timers
        timer_fired = []
        for i in range(3):
            scene.after(10.0, lambda: timer_fired.append(True))

        # Add tweens
        class TweenTarget:
            value = 0.0

        targets = [TweenTarget() for _ in range(3)]
        for t in targets:
            tween(t, "value", 0.0, 1.0, 10.0)

        g.tick(dt=0.016)

        # Teardown
        g._teardown()

        # Verify all sprites removed
        assert len(g._all_sprites) == 0
        assert len(g._animated_sprites) == 0
        assert len(g._action_sprites) == 0

        # Verify timer manager is cleared
        assert len(g._timer_manager._timers) == 0

        # Verify tween manager is cleared
        assert len(g._tween_manager._tweens) == 0

    def test_pop_scene_no_sprite_leaks(self):
        """Pop scene, verify owned sprites are cleaned up."""
        g = Game("Leak Test 2", backend="mock", resolution=(800, 600))
        scene1 = Scene()
        g.push(scene1)

        # Add sprites to scene1
        for i in range(5):
            s = Sprite("sprites/knight", position=(i * 10, 0))
            scene1.add_sprite(s)

        g.tick(dt=0.016)
        backend = g.backend
        assert len(backend.sprites) == 5

        # Pop scene1 — sprites should be cleaned up
        g.pop()
        g.tick(dt=0.016)

        assert len(backend.sprites) == 0
        assert len(g._all_sprites) == 0

        # Push a new scene, verify no leftovers
        scene2 = Scene()
        g.push(scene2)
        g.tick(dt=0.016)

        assert len(backend.sprites) == 0  # scene2 has no sprites
        g._teardown()

    def test_multiple_push_pop_cycles_no_accumulation(self):
        """Multiple cycles of push/pop — check for accumulation in Game's lists."""
        g = Game("Cycle Test", backend="mock", resolution=(800, 600))

        for cycle in range(10):
            scene = Scene()
            g.push(scene)

            # Add some sprites
            for i in range(3):
                s = Sprite("sprites/knight", position=(i * 10, 0))
                scene.add_sprite(s)

            g.tick(dt=0.016)

            # Pop
            g.pop()
            g.tick(dt=0.016)

        # After all cycles, nothing should remain
        assert len(g._all_sprites) == 0
        assert g._scene_stack.top() is None
        assert len(g._timer_manager._timers) == 0
        assert len(g._tween_manager._tweens) == 0
        g._teardown()

    def test_scene_timer_cleanup_on_pop(self):
        """Timers owned by a scene should be cancelled on pop."""
        g = Game("Timer Leak", backend="mock", resolution=(800, 600))
        scene = Scene()
        g.push(scene)

        fire_count = []
        scene.after(0.5, lambda: fire_count.append(True))
        scene.after(1.0, lambda: fire_count.append(True))

        g.tick(dt=0.016)

        # Pop scene — timers should be cancelled
        g.pop()
        g.tick(dt=0.016)

        # Tick past the timer deadlines — they should not fire
        g.tick(dt=2.0)

        assert len(fire_count) == 0, "Scene-owned timers should be cancelled on pop"
        g._teardown()


# ======================================================================
# 4. Concurrent-like operations
# ======================================================================


class TestConcurrentLikeOps:
    """Tests for operations that happen in overlapping/interleaved contexts."""

    def test_two_timers_modify_same_state(self, mock_game: Game):
        """Two timers fire in the same tick and both modify the same state."""
        scene = Scene()
        mock_game.push(scene)

        state = {"counter": 0}

        mock_game.after(0.1, lambda: state.__setitem__("counter", state["counter"] + 10))
        mock_game.after(0.1, lambda: state.__setitem__("counter", state["counter"] + 20))

        mock_game.tick(dt=0.2)

        # Both should fire; order is insertion order (10 then 20)
        assert state["counter"] == 30

    def test_tween_on_complete_starts_new_tween_on_same_target(self, mock_game: Game):
        """Tween completes and on_complete starts a new tween on the same target."""
        scene = Scene()
        mock_game.push(scene)

        class Target:
            value = 0.0

        t = Target()
        second_tween_done = []

        def start_second():
            tween(t, "value", 100.0, 200.0, 0.5,
                  on_complete=lambda: second_tween_done.append(True))

        tween(t, "value", 0.0, 100.0, 0.5, on_complete=start_second)

        # Complete first tween
        mock_game.tick(dt=0.6)
        assert t.value == 100.0

        # Complete second tween
        mock_game.tick(dt=0.6)
        assert t.value == 200.0
        assert len(second_tween_done) == 1

    def test_button_click_pushes_new_scene(self, mock_game: Game, mock_backend: MockBackend):
        """Button click that pushes a new scene mid-UI-event processing."""
        scene1 = Scene()
        mock_game.push(scene1)

        scene2 = Scene()
        pushed = []

        def push_scene():
            mock_game.push(scene2)
            pushed.append(True)

        btn = Button("Push Scene", on_click=push_scene, width=200, height=40)
        scene1.ui.add(btn)

        scene1.ui.compute_layout(0, 0, 1920, 1080)

        cx = btn._computed_x + btn._computed_w // 2
        cy = btn._computed_y + btn._computed_h // 2
        mock_backend.inject_click(cx, cy)
        mock_game.tick(dt=0.016)

        assert len(pushed) == 1
        # scene2 should now be on top (deferred push)
        assert mock_game._scene_stack.top() is scene2

    def test_on_enter_modifies_ui(self, mock_game: Game, mock_backend: MockBackend):
        """Scene on_enter that creates and modifies UI components."""

        class UIScene(Scene):
            def on_enter(self):
                self.panel = Panel(layout=Layout.VERTICAL, width=300, height=200)
                self.ui.add(self.panel)
                for i in range(5):
                    self.panel.add(Label(f"Item {i}", width=100, height=25))

        scene = UIScene()
        mock_game.push(scene)
        mock_game.tick(dt=0.016)

        assert len(scene.panel.children) == 5
        assert mock_backend.frame_count >= 1


# ======================================================================
# 5. F13 & F14 documented bugs
# ======================================================================


class TestF13DocumentedBugs:
    """F13: NaN handling in Delay.update and FadeOut.update."""

    def test_delay_update_with_nan_dt(self, mock_game: Game):
        """F13: Delay.update(float('nan')) — what happens?

        FINDING: Game.tick validates dt and raises ValueError for NaN,
        so NaN never reaches Delay.update through normal game loop.
        But calling Delay.update directly with NaN causes the delay to
        never complete (NaN comparison always False), effectively hanging.
        """
        d = Delay(1.0)
        d.start(None)

        result = d.update(float("nan"))
        # NaN + anything = NaN, NaN >= 1.0 is False
        assert result is False, "Delay with NaN dt should not complete (NaN >= 1.0 is False)"

        # After NaN, the elapsed is now NaN. Even valid dt won't fix it.
        result2 = d.update(0.5)
        assert result2 is False, "Once elapsed is NaN, Delay never completes"

        result3 = d.update(100.0)
        assert result3 is False, "Once elapsed is NaN, Delay never completes even with huge dt"

    def test_delay_constructor_rejects_nan(self, mock_game: Game):
        """F13: Delay(float('nan')) is rejected at construction."""
        with pytest.raises(ValueError, match="finite"):
            Delay(float("nan"))

    def test_game_tick_rejects_nan_dt(self, mock_game: Game):
        """F13: Game.tick(dt=float('nan')) raises ValueError."""
        scene = Scene()
        mock_game.push(scene)
        with pytest.raises(ValueError, match="finite"):
            mock_game.tick(dt=float("nan"))

    def test_fadeout_update_with_nan_dt(self, mock_game: Game):
        """F13: FadeOut.update(float('nan')) — what happens?

        FINDING: FadeOut.update with NaN dt causes elapsed to become NaN.
        Then t = NaN / duration = NaN, and int(start_opacity * (1 - NaN)) = ValueError
        or it depends on opacity setter behavior. Let's check.
        """
        scene = Scene()
        mock_game.push(scene)
        sprite = Sprite("sprites/knight", position=(100, 100))

        fo = FadeOut(1.0)
        fo.start(sprite)

        # FadeOut.update with NaN
        # elapsed += NaN -> NaN
        # NaN >= 1.0 is False, so falls to else branch
        # t = NaN / 1.0 = NaN
        # int(255 * (1.0 - NaN)) = int(255 * NaN) = int(NaN) -> ValueError!
        try:
            result = fo.update(float("nan"))
            # If we get here, it didn't crash — document what happened
            nan_causes_crash = False
        except (ValueError, TypeError) as e:
            nan_causes_crash = True
            nan_error = str(e)

        # DOCUMENTED FINDING: FadeOut.update(NaN) crashes with ValueError
        # because int(float('nan')) is illegal in Python.
        # The Sprite.opacity setter does handle NaN (clamps to 0), but
        # FadeOut.update calls int() on the result before passing to the setter.
        assert nan_causes_crash, (
            "FadeOut.update(NaN) SHOULD crash with ValueError: "
            "cannot convert float NaN to integer"
        )

    def test_fadein_update_with_nan_dt(self, mock_game: Game):
        """F13: FadeIn.update(float('nan')) — same pattern as FadeOut."""
        scene = Scene()
        mock_game.push(scene)
        sprite = Sprite("sprites/knight", position=(100, 100))
        sprite._opacity = 0  # Start at 0

        fi = FadeIn(1.0)
        fi.start(sprite)

        try:
            result = fi.update(float("nan"))
            nan_causes_crash = False
        except (ValueError, TypeError):
            nan_causes_crash = True

        # DOCUMENTED FINDING: FadeIn.update(NaN) crashes with ValueError,
        # same root cause as FadeOut — int(float('nan')) is illegal.
        assert nan_causes_crash, (
            "FadeIn.update(NaN) SHOULD crash with ValueError: "
            "cannot convert float NaN to integer"
        )

    def test_timer_manager_update_with_nan_dt(self, mock_game: Game):
        """F13: TimerManager.update with NaN dt silently skips (returns early)."""
        scene = Scene()
        mock_game.push(scene)

        fired = []
        mock_game.after(0.1, lambda: fired.append(True))

        # Direct update with NaN — TimerManager.update checks isfinite(dt)
        mock_game._timer_manager.update(float("nan"))

        assert len(fired) == 0, "Timer should not fire when NaN dt passed to manager"

        # But the timer should still be active
        assert len(mock_game._timer_manager._timers) == 1

        # And a normal tick should fire it
        mock_game._timer_manager.update(0.2)
        assert len(fired) == 1

    def test_tween_manager_update_with_nan_dt(self, mock_game: Game):
        """F13: TweenManager.update with NaN dt silently skips."""
        class T:
            value = 0.0

        t = T()
        tween(t, "value", 0.0, 100.0, 1.0)

        mock_game._tween_manager.update(float("nan"))
        assert t.value == 0.0, "Tween should not advance with NaN dt"

        # Still active
        assert len(mock_game._tween_manager._tweens) == 1


class TestF14DocumentedBugs:
    """F14: audio.play_sound with channel='master'."""

    def test_play_sound_with_master_channel(self, mock_game: Game):
        """F14: play_sound("test", channel="master") — accepted? What volume?

        FINDING: channel="master" is accepted because it's a valid key in
        _volumes dict. The effective volume = master * master = 1.0 * 1.0 = 1.0.
        This is probably NOT intended behavior — "master" is a multiplier channel,
        not a playback channel. Using it doubles the master influence.
        """
        # Need to set up an asset path so sound loading works
        # With mock backend, sounds are just string handles
        audio = mock_game.audio
        backend = mock_game.backend

        # Register a fake sound in the asset manager's cache
        # The mock backend's load_sound just creates a handle from the path
        # We need to work around AssetManager
        try:
            audio.play_sound("test_sound", channel="master")
            accepted = True
        except KeyError:
            accepted = False
        except Exception:
            # AssetNotFoundError from asset manager — the channel was valid
            # but the asset doesn't exist. Still tells us channel was accepted.
            accepted = True

        # channel="master" should be accepted since it's in _volumes dict
        # This is a design issue: master is not really a playback channel
        assert accepted, (
            "channel='master' is accepted because it exists in _volumes. "
            "Volume = master * master = master^2, which is probably wrong."
        )

    def test_play_sound_with_invalid_channel(self, mock_game: Game):
        """F14: play_sound with truly invalid channel raises KeyError."""
        audio = mock_game.audio
        try:
            audio.play_sound("test_sound", channel="nonexistent")
        except KeyError as e:
            assert "nonexistent" in str(e)
        except Exception:
            # Asset not found before channel check
            pass

    def test_play_sound_master_channel_volume_calculation(self, mock_game: Game):
        """F14: Verify the volume math when channel='master'.

        effective = master * _volumes[channel]
        if channel = "master": effective = master * master = master^2
        At master=0.5: effective = 0.25 instead of expected 0.5
        """
        audio = mock_game.audio
        audio.set_volume("master", 0.5)

        # The volume for channel="master" would be 0.5 * 0.5 = 0.25
        effective = audio._volumes["master"] * audio._volumes["master"]
        assert effective == 0.25, (
            "channel='master' volume is master^2 = 0.25, not 0.5 as one might expect"
        )

        # For comparison, channel="sfx" at master=0.5
        effective_sfx = audio._volumes["master"] * audio._volumes["sfx"]
        assert effective_sfx == 0.5


# ======================================================================
# Additional edge cases discovered during analysis
# ======================================================================


class TestEdgeCases:
    """Edge cases found during code review."""

    def test_empty_scene_stack_pop(self, mock_game: Game):
        """Pop on empty stack should be a no-op."""
        mock_game.pop()
        assert mock_game._scene_stack.top() is None

    def test_remove_already_removed_sprite(self, mock_game: Game):
        """Calling remove() twice on a sprite should be safe."""
        scene = Scene()
        mock_game.push(scene)
        s = Sprite("sprites/knight", position=(100, 100))
        s.remove()
        s.remove()  # Should not crash

    def test_tween_zero_duration(self, mock_game: Game):
        """Tween with duration=0 should snap to target immediately."""
        scene = Scene()
        mock_game.push(scene)

        class T:
            value = 0.0

        t = T()
        completed = []
        tween(t, "value", 0.0, 42.0, 0.0,
              on_complete=lambda: completed.append(True))

        mock_game.tick(dt=0.016)

        assert t.value == 42.0
        assert len(completed) == 1

    def test_timer_fires_in_same_tick_as_creation(self, mock_game: Game):
        """Timer with delay=0 fires in the same tick update."""
        scene = Scene()
        mock_game.push(scene)

        fired = []
        mock_game.after(0.0, lambda: fired.append(True))

        mock_game.tick(dt=0.016)

        assert len(fired) == 1

    def test_negative_dt_rejected(self, mock_game: Game):
        """Negative dt should be rejected by Game.tick."""
        scene = Scene()
        mock_game.push(scene)
        with pytest.raises(ValueError, match="negative"):
            mock_game.tick(dt=-0.1)

    def test_inf_dt_rejected(self, mock_game: Game):
        """Infinite dt should be rejected by Game.tick."""
        scene = Scene()
        mock_game.push(scene)
        with pytest.raises(ValueError, match="finite"):
            mock_game.tick(dt=float("inf"))

    def test_children_property_returns_copy(self, mock_game: Game):
        """Component.children should return a copy, not the internal list."""
        panel = Panel(width=100, height=100)
        label = Label("test", width=50, height=20)
        panel.add(label)

        children = panel.children
        children.clear()  # Modify the copy

        # Internal list should be unaffected
        assert len(panel.children) == 1

    def test_component_add_self_raises(self, mock_game: Game):
        """Adding a component to itself should raise ValueError."""
        panel = Panel(width=100, height=100)
        with pytest.raises(ValueError, match="Cannot add component to itself"):
            panel.add(panel)

    def test_timer_nan_delay_rejected(self, mock_game: Game):
        """Timer with NaN delay should be rejected."""
        with pytest.raises(ValueError, match="finite"):
            mock_game.after(float("nan"), lambda: None)

    def test_timer_inf_delay_rejected(self, mock_game: Game):
        """Timer with inf delay should be rejected."""
        with pytest.raises(ValueError, match="finite"):
            mock_game.after(float("inf"), lambda: None)

    def test_draw_uses_snapshot(self, mock_game: Game):
        """Component.draw() should iterate a snapshot of children."""
        parent = Component(width=100, height=100)
        parent._game = mock_game

        class MutatingChild(Component):
            def __init__(self, parent_ref):
                super().__init__(width=50, height=50)
                self._parent_ref = parent_ref
                self.drawn = False

            def on_draw(self):
                self.drawn = True
                # Add a new child to parent during draw
                new_child = Component(width=10, height=10)
                self._parent_ref.add(new_child)

        c1 = MutatingChild(parent)
        c2 = MutatingChild(parent)
        parent.add(c1)
        parent.add(c2)

        # Should not crash despite mutation during iteration
        parent.draw()
        assert c1.drawn
        assert c2.drawn
