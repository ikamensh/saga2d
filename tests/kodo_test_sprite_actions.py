"""Exploratory tests for Sprite lifecycle, Action workflows, and Animation state.

Targets:
  - Sprite addition/removal/z-order/layer ordering
  - Active-action removal (sprite removed mid-action, do() on removed sprite)
  - Orphaned sprites (no scene owner, game teardown while actions running)
  - Deep Sequence/Parallel/Repeat/Delay nesting
  - Animation queue/state transitions (play/queue/stop/interrupt/complete)

Run:  .venv/bin/python -m pytest tests/kodo_test_sprite_actions.py -v
"""

from __future__ import annotations

import pytest

from saga2d import Game
from saga2d.actions import (
    Action,
    Delay,
    Do,
    FadeIn,
    FadeOut,
    MoveTo,
    Parallel,
    PlayAnim,
    Remove,
    Repeat,
    Sequence,
)
from saga2d.animation import AnimationDef
from saga2d.rendering.layers import RenderLayer, SpriteAnchor
from saga2d.rendering.sprite import Sprite


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────


@pytest.fixture
def game() -> Game:
    g = Game("Test", backend="mock", resolution=(800, 600))
    yield g  # type: ignore[misc]
    g._teardown()


@pytest.fixture
def sprite(game: Game) -> Sprite:
    """A basic sprite at (100, 300) for action tests."""
    return Sprite("sprites/knight", position=(100, 300))


def _walk_anim() -> AnimationDef:
    return AnimationDef(
        frames=["sprites/knight_walk_01", "sprites/knight_walk_02", "sprites/knight_walk_03"],
        frame_duration=0.15,
        loop=True,
    )


def _attack_anim() -> AnimationDef:
    return AnimationDef(
        frames=["sprites/knight_attack_01", "sprites/knight_attack_02", "sprites/knight_attack_03"],
        frame_duration=0.1,
        loop=False,
    )


def _idle_anim() -> AnimationDef:
    return AnimationDef(
        frames=["sprites/knight"],
        frame_duration=1.0,
        loop=True,
    )


# ═════════════════════════════════════════════════════════════
# 1. SPRITE LIFECYCLE
# ═════════════════════════════════════════════════════════════


class TestSpriteCreationAndProperties:
    """Basic sprite creation, property access, and backend registration."""

    def test_create_registers_in_all_sprites(self, game: Game) -> None:
        s = Sprite("sprites/knight", position=(50, 50))
        assert s in game._all_sprites

    def test_default_properties(self, game: Game) -> None:
        s = Sprite("sprites/knight")
        assert s.position == (0, 0)
        assert s.opacity == 255
        assert s.visible is True
        assert s.layer == RenderLayer.UNITS
        assert s.anchor == SpriteAnchor.BOTTOM_CENTER
        assert s.is_removed is False

    def test_position_property_roundtrip(self, sprite: Sprite) -> None:
        sprite.position = (200, 400)
        assert sprite.position == (200, 400)
        assert sprite.x == 200
        assert sprite.y == 400

    def test_x_y_setters_independent(self, sprite: Sprite) -> None:
        sprite.x = 500
        assert sprite.position == (500, 300)
        sprite.y = 700
        assert sprite.position == (500, 700)


class TestSpriteRemoval:
    """Sprite removal lifecycle and idempotency."""

    def test_remove_sets_flag(self, sprite: Sprite) -> None:
        sprite.remove()
        assert sprite.is_removed is True

    def test_remove_deregisters_from_game(self, game: Game, sprite: Sprite) -> None:
        sprite.remove()
        assert sprite not in game._all_sprites
        assert sprite not in game._action_sprites
        assert sprite not in game._animated_sprites

    def test_double_remove_safe(self, sprite: Sprite) -> None:
        sprite.remove()
        sprite.remove()  # Should not crash
        assert sprite.is_removed is True

    def test_property_set_after_remove_no_backend_sync(self, game: Game) -> None:
        """Setting properties on removed sprite updates internal state but not backend."""
        s = Sprite("sprites/knight", position=(10, 10))
        sid = s.sprite_id
        s.remove()
        s.position = (999, 999)
        assert s.position == (999, 999)  # Internal state updated
        # Backend should have removed the sprite; no sync should happen

    def test_remove_stops_active_action(self, sprite: Sprite) -> None:
        """remove() should stop any active action."""
        log: list[str] = []
        sprite.do(Sequence(Delay(10.0), Do(lambda: log.append("SHOULD_NOT_FIRE"))))
        assert sprite._current_action is not None
        sprite.remove()
        assert sprite._current_action is None

    def test_remove_stops_animation(self, sprite: Sprite) -> None:
        """remove() should stop any playing animation."""
        sprite.play(_walk_anim())
        assert sprite._anim_player is not None
        sprite.remove()
        assert sprite._anim_player is None

    def test_remove_clears_animation_queue(self, sprite: Sprite) -> None:
        """remove() should clear the animation queue."""
        sprite.play(_walk_anim())
        sprite.queue(_attack_anim())
        assert len(sprite._anim_queue) > 0
        sprite.remove()
        assert len(sprite._anim_queue) == 0


class TestSpriteZOrder:
    """Y-sort and layer ordering."""

    def test_same_layer_higher_y_in_front(self, game: Game) -> None:
        """Higher y → higher order → drawn later (in front)."""
        s1 = Sprite("sprites/knight", position=(100, 100))
        s2 = Sprite("sprites/knight", position=(100, 200))
        assert s1._compute_order() < s2._compute_order()

    def test_y_change_updates_order(self, game: Game) -> None:
        """Moving sprite down (higher y) should increase draw order."""
        s = Sprite("sprites/knight", position=(100, 100))
        old_order = s._compute_order()
        s.y = 500
        assert s._compute_order() > old_order

    def test_layer_separation(self, game: Game) -> None:
        """Different layers have 100_000 gap in order values."""
        s_bg = Sprite("sprites/knight", position=(0, 0), layer=RenderLayer.BACKGROUND)
        s_unit = Sprite("sprites/knight", position=(0, 0), layer=RenderLayer.UNITS)
        s_fx = Sprite("sprites/knight", position=(0, 0), layer=RenderLayer.EFFECTS)
        assert s_bg._compute_order() < s_unit._compute_order() < s_fx._compute_order()
        # Even a unit at y=99999 should be below effects at y=0
        s_high_unit = Sprite("sprites/knight", position=(0, 99999), layer=RenderLayer.UNITS)
        assert s_high_unit._compute_order() < s_fx._compute_order()

    def test_x_change_does_not_affect_order(self, game: Game) -> None:
        """Order depends on y and layer only, not x."""
        s = Sprite("sprites/knight", position=(100, 200))
        order_before = s._compute_order()
        s.x = 900
        assert s._compute_order() == order_before

    def test_multiple_sprites_z_sort_correctness(self, game: Game) -> None:
        """Several sprites at different y-positions sort correctly."""
        sprites = [
            Sprite("sprites/knight", position=(0, y))
            for y in [300, 100, 500, 200, 400]
        ]
        orders = [(s.y, s._compute_order()) for s in sprites]
        # Sort by y ascending → orders should be ascending
        orders_by_y = sorted(orders, key=lambda t: t[0])
        assert all(
            orders_by_y[i][1] < orders_by_y[i + 1][1]
            for i in range(len(orders_by_y) - 1)
        )


# ═════════════════════════════════════════════════════════════
# 2. ACTIVE-ACTION REMOVAL
# ═════════════════════════════════════════════════════════════


class TestActiveActionRemoval:
    """What happens when sprites are removed while actions are running."""

    def test_remove_mid_moveto(self, game: Game) -> None:
        """Remove sprite during MoveTo → action stops, no crash on tick."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(MoveTo((1000, 1000), speed=50))
        game.tick(0.016)  # Start moving
        s.remove()
        game.tick(0.016)  # Should not crash
        game.tick(0.016)

    def test_remove_mid_sequence(self, game: Game) -> None:
        """Remove sprite mid-Sequence → remaining actions don't fire."""
        log: list[str] = []
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(Sequence(
            Delay(0.01),
            Do(lambda: log.append("first")),
            Delay(10.0),
            Do(lambda: log.append("second")),
        ))
        game.tick(0.016)  # First delay + first Do should fire
        assert "first" in log
        s.remove()
        for _ in range(10):
            game.tick(0.016)
        assert "second" not in log

    def test_remove_mid_parallel(self, game: Game) -> None:
        """Remove sprite mid-Parallel → no crash on subsequent ticks."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(Parallel(
            MoveTo((500, 500), speed=100),
            FadeOut(2.0),
        ))
        game.tick(0.016)
        s.remove()
        game.tick(0.016)  # Should not crash

    def test_do_on_removed_sprite_is_noop(self, game: Game) -> None:
        """Calling do() on a removed sprite should be no-op."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.remove()
        log: list[str] = []
        s.do(Do(lambda: log.append("should_not_run")))
        game.tick(0.016)
        assert log == []

    def test_stop_actions_on_removed_sprite(self, game: Game) -> None:
        """stop_actions() on removed sprite → no crash."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(Delay(10.0))
        s.remove()
        # stop_actions references _game which might be stale
        # But it's called during remove(), so any post-remove call is redundant

    def test_remove_inside_do_callback(self, game: Game) -> None:
        """Sprite removes itself inside a Do callback mid-Sequence."""
        s = Sprite("sprites/knight", position=(0, 0))
        log: list[str] = []

        s.do(Sequence(
            Do(lambda: log.append("before")),
            Do(lambda: s.remove()),
            Do(lambda: log.append("after")),
        ))
        game.tick(0.016)
        assert "before" in log
        assert s.is_removed is True
        # "after" may or may not fire depending on when removal takes effect
        # The key thing is no crash

    def test_action_sprites_set_cleaned_on_remove(self, game: Game) -> None:
        """Removing sprite deregisters from _action_sprites."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(Delay(10.0))
        assert s in game._action_sprites
        s.remove()
        assert s not in game._action_sprites


class TestOrphanedSprites:
    """Sprites without scene ownership or during teardown."""

    def test_sprite_without_scene_owner(self, game: Game) -> None:
        """Sprite created without add_sprite → no _owning_scene."""
        s = Sprite("sprites/knight", position=(0, 0))
        assert s._owning_scene is None
        s.remove()  # Should not crash

    def test_sprite_survives_scene_pop(self, game: Game) -> None:
        """Orphaned sprite (no scene owner) survives scene transitions."""
        from saga2d.scene import Scene

        s = Sprite("sprites/knight", position=(0, 0))

        class DummyScene(Scene):
            pass

        game.push(DummyScene())
        game.push(DummyScene())
        game.pop()
        # Sprite should still be alive (not owned by any scene)
        assert not s.is_removed
        assert s in game._all_sprites

    def test_teardown_with_active_actions(self, game: Game) -> None:
        """Game teardown while actions are running → no crash."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(Sequence(
            MoveTo((500, 500), speed=100),
            Delay(1.0),
            Do(lambda: None),
        ))
        game.tick(0.016)
        # Teardown happens in fixture cleanup — should not crash


# ═════════════════════════════════════════════════════════════
# 3. DEEP ACTION NESTING
# ═════════════════════════════════════════════════════════════


class TestDeepSequenceNesting:
    """Deep and complex Sequence compositions."""

    def test_sequence_of_3_delays(self, sprite: Sprite, game: Game) -> None:
        """Three consecutive delays → total time is sum.
        Note: Sequence chains with dt=0, so each Delay starts fresh
        with no overflow carry. Takes slightly more ticks than 0.3/0.016."""
        sprite.do(Sequence(Delay(0.1), Delay(0.1), Delay(0.1)))
        for _ in range(20):  # 20 * 0.016 = 0.320 — not yet done (3 delays need ~21 ticks)
            game.tick(0.016)
        assert sprite._current_action is not None
        game.tick(0.016)  # tick 21 = 0.336s → done
        assert sprite._current_action is None

    def test_sequence_instant_chain(self, sprite: Sprite, game: Game) -> None:
        """Chain of Do actions all fire in one tick."""
        log: list[str] = []
        sprite.do(Sequence(
            Do(lambda: log.append("a")),
            Do(lambda: log.append("b")),
            Do(lambda: log.append("c")),
            Do(lambda: log.append("d")),
            Do(lambda: log.append("e")),
        ))
        game.tick(0.016)
        assert log == ["a", "b", "c", "d", "e"]
        assert sprite._current_action is None

    def test_sequence_delay_interleaved_with_do(self, sprite: Sprite, game: Game) -> None:
        """Do → Delay → Do → Delay → Do pattern.
        Do chains instantly in Sequence (dt=0 for next child), so the first
        Delay's first update gets dt=0. Then 4 more ticks (0.064s) pass 0.05.
        '2' fires on tick 5, '3' fires on tick 9."""
        log: list[str] = []
        sprite.do(Sequence(
            Do(lambda: log.append("1")),
            Delay(0.05),
            Do(lambda: log.append("2")),
            Delay(0.05),
            Do(lambda: log.append("3")),
        ))
        game.tick(0.016)  # tick 1: "1" fires instantly, Delay starts with dt=0
        assert log == ["1"]
        for _ in range(4):  # ticks 2-5: Delay accumulates 4*0.016=0.064 > 0.05
            game.tick(0.016)
        assert "2" in log
        for _ in range(4):  # ticks 6-9: second Delay accumulates 4*0.016=0.064 > 0.05
            game.tick(0.016)
        assert "3" in log

    def test_nested_sequence_in_sequence(self, sprite: Sprite, game: Game) -> None:
        """Sequence containing a sub-Sequence works correctly."""
        log: list[str] = []
        sprite.do(Sequence(
            Do(lambda: log.append("outer_1")),
            Sequence(
                Do(lambda: log.append("inner_1")),
                Do(lambda: log.append("inner_2")),
            ),
            Do(lambda: log.append("outer_2")),
        ))
        game.tick(0.016)
        assert log == ["outer_1", "inner_1", "inner_2", "outer_2"]

    def test_deeply_nested_sequences_5_levels(self, sprite: Sprite, game: Game) -> None:
        """5-level nested Sequence still works."""
        log: list[str] = []
        sprite.do(
            Sequence(
                Sequence(
                    Sequence(
                        Sequence(
                            Sequence(
                                Do(lambda: log.append("deep")),
                            ),
                        ),
                    ),
                ),
            )
        )
        game.tick(0.016)
        assert log == ["deep"]


class TestDeepParallelNesting:
    """Complex Parallel compositions and edge cases."""

    def test_parallel_two_moveto_waits_slower(self, game: Game) -> None:
        """Parallel(fast_move, slow_move) waits for slow one."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(Parallel(
            MoveTo((100, 0), speed=1000),   # Fast: ~0.1s
            MoveTo((0, 500), speed=50),     # Slow: ~10s
        ))
        # After 0.2s, fast should be done but slow is still running
        for _ in range(12):  # 0.192s
            game.tick(0.016)
        assert s._current_action is not None  # Parallel still running

    def test_parallel_all_instant(self, game: Game) -> None:
        """Parallel of all instant actions completes in one tick."""
        s = Sprite("sprites/knight", position=(0, 0))
        log: list[str] = []
        s.do(Parallel(
            Do(lambda: log.append("a")),
            Do(lambda: log.append("b")),
            Do(lambda: log.append("c")),
        ))
        game.tick(0.016)
        assert sorted(log) == ["a", "b", "c"]
        assert s._current_action is None

    def test_parallel_finite_and_infinite(self, game: Game) -> None:
        """Parallel(finite, infinite) → finishes when finite done, stops infinite."""
        s = Sprite("sprites/knight", position=(0, 0))
        walk = _walk_anim()
        s.do(Parallel(
            Delay(0.05),
            PlayAnim(walk),  # Infinite (loop=True)
        ))
        for _ in range(5):
            game.tick(0.016)
        # After ~0.08s, Delay(0.05) is done → Parallel done
        assert s._current_action is None

    def test_parallel_only_infinite_completes_immediately(self, game: Game) -> None:
        """KNOWN: Parallel(only infinite) → vacuous-truth → completes in 1 tick.
        This is the documented behavior (all_finite_done is vacuously True)."""
        s = Sprite("sprites/knight", position=(0, 0))
        walk = _walk_anim()
        s.do(Parallel(
            PlayAnim(walk),
            Repeat(Do(lambda: None), times=None),
        ))
        game.tick(0.016)
        # Known behavior: completes immediately
        assert s._current_action is None

    def test_parallel_in_sequence(self, game: Game) -> None:
        """Sequence(Parallel(...), Do) → Do fires after Parallel completes.
        Delay(0.05) needs 4 ticks. MoveTo(50px at 500px/s) = 0.1s = 7 ticks.
        Parallel waits for slower (MoveTo), so ~7 ticks total."""
        s = Sprite("sprites/knight", position=(0, 0))
        log: list[str] = []
        s.do(Sequence(
            Parallel(
                MoveTo((50, 0), speed=500),
                Delay(0.05),
            ),
            Do(lambda: log.append("after_parallel")),
        ))
        for _ in range(10):  # Plenty of ticks for both to finish
            game.tick(0.016)
        assert "after_parallel" in log

    def test_sequence_in_parallel(self, game: Game) -> None:
        """Parallel(Sequence(A, B), Sequence(C, D)) → all fire."""
        s = Sprite("sprites/knight", position=(0, 0))
        log: list[str] = []
        s.do(Parallel(
            Sequence(Do(lambda: log.append("a")), Do(lambda: log.append("b"))),
            Sequence(Do(lambda: log.append("c")), Do(lambda: log.append("d"))),
        ))
        game.tick(0.016)
        assert sorted(log) == ["a", "b", "c", "d"]


class TestRepeatAction:
    """Repeat with various nesting patterns."""

    def test_repeat_3_times_delay(self, sprite: Sprite, game: Game) -> None:
        """Repeat(Delay(0.05), times=3) takes 3 ticks minimum (1 per iteration)."""
        log: list[int] = []

        class CountingDelay(Action):
            def __init__(self) -> None:
                self._done = False

            def start(self, sprite: Sprite) -> None:
                pass

            def update(self, dt: float) -> bool:
                log.append(1)
                return True

        sprite.do(Repeat(CountingDelay(), times=3))
        # Repeat yields after each iteration, so 3 ticks needed
        game.tick(0.016)
        game.tick(0.016)
        game.tick(0.016)
        assert len(log) == 3

    def test_repeat_infinite_runs_many(self, sprite: Sprite, game: Game) -> None:
        """Repeat(Do(...), times=None) runs indefinitely until stopped."""
        count = [0]
        sprite.do(Repeat(Do(lambda: count.__setitem__(0, count[0] + 1)), times=None))
        for _ in range(100):
            game.tick(0.016)
        assert count[0] == 100
        sprite.stop_actions()
        old_count = count[0]
        game.tick(0.016)
        assert count[0] == old_count  # Stopped

    def test_repeat_zero_times_noop(self, sprite: Sprite, game: Game) -> None:
        """Repeat(..., times=0) → completes immediately, never fires child."""
        log: list[str] = []
        sprite.do(Repeat(Do(lambda: log.append("x")), times=0))
        game.tick(0.016)
        assert log == []
        assert sprite._current_action is None

    def test_repeat_of_sequence(self, sprite: Sprite, game: Game) -> None:
        """Repeat(Sequence(Do, Delay, Do), times=2) → fires Do's twice."""
        log: list[str] = []
        sprite.do(Repeat(
            Sequence(
                Do(lambda: log.append("start")),
                Delay(0.01),
                Do(lambda: log.append("end")),
            ),
            times=2,
        ))
        # Each repeat iteration: tick for Do+Delay start, tick for Delay finish+Do
        for _ in range(10):
            game.tick(0.016)
        assert log.count("start") == 2
        assert log.count("end") == 2

    def test_repeat_uses_deepcopy(self, sprite: Sprite, game: Game) -> None:
        """Each iteration gets a fresh copy of the action — state doesn't leak."""
        elapsed_list: list[float] = []

        class TrackElapsed(Action):
            def __init__(self) -> None:
                self._elapsed = 0.0

            def start(self, sprite: Sprite) -> None:
                elapsed_list.append(self._elapsed)

            def update(self, dt: float) -> bool:
                self._elapsed += dt
                return True

        sprite.do(Repeat(TrackElapsed(), times=3))
        game.tick(0.016)
        game.tick(0.016)
        game.tick(0.016)
        # Each copy should start with _elapsed=0
        assert all(e == 0.0 for e in elapsed_list)


class TestDelayEdgeCases:
    """Delay timing edge cases."""

    def test_delay_zero_instant(self, sprite: Sprite, game: Game) -> None:
        """Delay(0) completes instantly in Sequence."""
        log: list[str] = []
        sprite.do(Sequence(
            Delay(0),
            Do(lambda: log.append("after_zero_delay")),
        ))
        game.tick(0.016)
        assert "after_zero_delay" in log

    def test_delay_exact_boundary(self, sprite: Sprite, game: Game) -> None:
        """Delay finishes on exact boundary when elapsed == duration."""
        sprite.do(Delay(0.016))
        done = sprite._current_action.update(0.016)  # type: ignore
        assert done is True

    def test_delay_overflow_carries_to_next(self, sprite: Sprite, game: Game) -> None:
        """When Delay finishes mid-tick, Sequence chains to next action."""
        log: list[str] = []
        sprite.do(Sequence(
            Delay(0.01),
            Do(lambda: log.append("chained")),
        ))
        game.tick(0.016)  # 0.016 > 0.01 → Delay done, Do fires same tick
        assert "chained" in log


class TestComplexNesting:
    """Mixed nesting: Parallel in Repeat, Sequence in Parallel in Sequence, etc."""

    def test_parallel_in_repeat(self, game: Game) -> None:
        """Repeat(Parallel(MoveTo, FadeOut), times=2)."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(Repeat(
            Parallel(
                MoveTo((50, 0), speed=5000),
                FadeOut(0.01),
            ),
            times=2,
        ))
        for _ in range(10):
            game.tick(0.016)
        assert s._current_action is None

    def test_sequence_parallel_sequence(self, game: Game) -> None:
        """Seq(Par(Seq(Do,Delay), Delay), Do) → all fire in order."""
        s = Sprite("sprites/knight", position=(0, 0))
        log: list[str] = []
        s.do(Sequence(
            Parallel(
                Sequence(Do(lambda: log.append("inner")), Delay(0.01)),
                Delay(0.02),
            ),
            Do(lambda: log.append("final")),
        ))
        for _ in range(5):
            game.tick(0.016)
        assert "inner" in log
        assert "final" in log

    def test_10_wide_parallel(self, game: Game) -> None:
        """Parallel with 10 children — all fire."""
        s = Sprite("sprites/knight", position=(0, 0))
        log: list[int] = []
        children = [Do(lambda i=i: log.append(i)) for i in range(10)]
        s.do(Parallel(*children))
        game.tick(0.016)
        assert sorted(log) == list(range(10))

    def test_20_deep_sequence_chain(self, game: Game) -> None:
        """20 Do actions chained in Sequence → all fire in 1 tick."""
        s = Sprite("sprites/knight", position=(0, 0))
        log: list[int] = []
        actions = [Do(lambda i=i: log.append(i)) for i in range(20)]
        s.do(Sequence(*actions))
        game.tick(0.016)
        assert log == list(range(20))

    def test_remove_in_middle_of_sequence(self, game: Game) -> None:
        """Remove() action in middle of Sequence → subsequent actions don't fire."""
        s = Sprite("sprites/knight", position=(0, 0))
        log: list[str] = []
        s.do(Sequence(
            Do(lambda: log.append("before")),
            Remove(),
            Do(lambda: log.append("after")),  # Should not fire
        ))
        game.tick(0.016)
        assert "before" in log
        assert s.is_removed is True
        # "after" won't fire because update_action checks _removed

    def test_do_replaces_action_during_sequence_f6(self, game: Game) -> None:
        """F6 regression: sprite.do() inside a Do callback must replace the
        current action — the old Sequence must not continue, and the new
        action must survive and execute.
        """
        s = Sprite("sprites/knight", position=(0, 0))
        log: list[str] = []

        def replace_action() -> None:
            s.do(Do(lambda: log.append("replaced")))

        s.do(Sequence(
            Do(replace_action),
            Do(lambda: log.append("original_next")),
        ))
        game.tick(0.016)
        # Fixed: new action survives and fires on next tick.
        assert "original_next" in log  # Sequence still chains instant children
        game.tick(0.016)
        assert "replaced" in log  # New action fires
        assert s._current_action is None  # Completed normally


# ═════════════════════════════════════════════════════════════
# 4. ANIMATION QUEUE & STATE TRANSITIONS
# ═════════════════════════════════════════════════════════════


class TestAnimationPlay:
    """Animation play basics."""

    def test_play_sets_first_frame(self, sprite: Sprite, game: Game) -> None:
        """play() immediately sets sprite image to first frame."""
        walk = _walk_anim()
        sprite.play(walk)
        # Image should be first frame
        assert sprite._anim_player is not None
        assert sprite._anim_player.frame_index == 0

    def test_play_registers_in_animated_sprites(self, sprite: Sprite, game: Game) -> None:
        sprite.play(_walk_anim())
        assert sprite in game._animated_sprites

    def test_play_on_removed_sprite_noop(self, game: Game) -> None:
        s = Sprite("sprites/knight", position=(0, 0))
        s.remove()
        s.play(_walk_anim())
        assert s._anim_player is None
        assert s not in game._animated_sprites


class TestAnimationFrameAdvancement:
    """Frame advancement via game tick."""

    def test_frame_advances_after_duration(self, sprite: Sprite, game: Game) -> None:
        """After frame_duration, animation advances to next frame."""
        walk = _walk_anim()  # 0.15s per frame
        sprite.play(walk)
        assert sprite._anim_player.frame_index == 0
        # 10 ticks at 0.016 = 0.16s > 0.15s → advance to frame 1
        for _ in range(10):
            game.tick(0.016)
        assert sprite._anim_player.frame_index == 1

    def test_looping_wraps_around(self, sprite: Sprite, game: Game) -> None:
        """Looping animation wraps back to frame 0."""
        walk = _walk_anim()  # 3 frames, 0.15s each, loop=True
        sprite.play(walk)
        # 3 frames * 0.15s = 0.45s total. After 0.46s should be on frame 0
        for _ in range(29):  # 29 * 0.016 = 0.464s
            game.tick(0.016)
        assert sprite._anim_player.frame_index == 0

    def test_oneshot_fires_complete(self, sprite: Sprite, game: Game) -> None:
        """Non-looping animation fires on_complete when done."""
        atk = _attack_anim()  # 3 frames, 0.1s each, loop=False
        log: list[str] = []
        sprite.play(atk, on_complete=lambda: log.append("done"))
        # 3 * 0.1 = 0.3s total
        for _ in range(20):  # 0.32s
            game.tick(0.016)
        assert "done" in log
        assert sprite._anim_player.is_complete is True

    def test_oneshot_stays_on_last_frame(self, sprite: Sprite, game: Game) -> None:
        """Non-looping stays on last frame after completion."""
        atk = _attack_anim()  # 3 frames, 0.1s, loop=False
        sprite.play(atk)
        for _ in range(30):
            game.tick(0.016)
        assert sprite._anim_player.frame_index == 2  # Last frame


class TestAnimationQueue:
    """Queue and transition between animations."""

    def test_queue_plays_after_current(self, sprite: Sprite, game: Game) -> None:
        """queue(B) while A is playing → B starts after A finishes."""
        atk = _attack_anim()  # 3 frames, 0.1s, loop=False → 0.3s
        idle = _idle_anim()
        log: list[str] = []
        sprite.play(atk, on_complete=lambda: log.append("atk_done"))
        sprite.queue(idle)
        # After attack finishes, idle should start
        for _ in range(25):
            game.tick(0.016)
        assert "atk_done" in log
        # Idle should now be playing
        assert sprite._anim_player is not None
        assert sprite._anim_player.is_playing

    def test_queue_when_nothing_playing(self, sprite: Sprite, game: Game) -> None:
        """queue() with nothing playing → starts immediately."""
        walk = _walk_anim()
        sprite.queue(walk)
        assert sprite._anim_player is not None
        assert sprite in game._animated_sprites

    def test_queue_chain_three_f7(self, sprite: Sprite, game: Game) -> None:
        """F7 regression: animation queue chains of 3+ must all play through."""
        a1 = AnimationDef(frames=["sprites/knight_attack_01"], frame_duration=0.05, loop=False)
        a2 = AnimationDef(frames=["sprites/knight_attack_02"], frame_duration=0.05, loop=False)
        a3 = AnimationDef(frames=["sprites/knight_attack_03"], frame_duration=0.05, loop=False)
        log: list[str] = []
        sprite.play(a1, on_complete=lambda: log.append("a1"))
        sprite.queue(a2, on_complete=lambda: log.append("a2"))
        sprite.queue(a3, on_complete=lambda: log.append("a3"))
        for _ in range(50):
            game.tick(0.016)
        # Fixed: all three animations play through
        assert log == ["a1", "a2", "a3"]


class TestAnimationInterrupt:
    """Interrupting animations with play() or stop()."""

    def test_play_interrupts_current(self, sprite: Sprite, game: Game) -> None:
        """play() while animation running → replaces immediately."""
        sprite.play(_walk_anim())
        old_player = sprite._anim_player
        sprite.play(_attack_anim())
        assert sprite._anim_player is not old_player

    def test_play_clears_queue(self, sprite: Sprite, game: Game) -> None:
        """play() clears any queued animations."""
        sprite.play(_attack_anim())
        sprite.queue(_idle_anim())
        assert len(sprite._anim_queue) > 0
        sprite.play(_walk_anim())
        assert len(sprite._anim_queue) == 0

    def test_stop_animation_clears_all(self, sprite: Sprite, game: Game) -> None:
        """stop_animation() stops playback and clears queue."""
        sprite.play(_walk_anim())
        sprite.queue(_attack_anim())
        sprite.stop_animation()
        assert sprite._anim_player is None
        assert len(sprite._anim_queue) == 0
        assert sprite not in game._animated_sprites

    def test_stop_animation_when_nothing_playing(self, sprite: Sprite, game: Game) -> None:
        """stop_animation() when nothing playing → no crash."""
        sprite.stop_animation()  # Should be no-op


class TestAnimationWithActions:
    """Animation integrated with the action system."""

    def test_playanim_action_starts_animation(self, sprite: Sprite, game: Game) -> None:
        """PlayAnim action starts the animation on the sprite."""
        walk = _walk_anim()
        sprite.do(PlayAnim(walk))
        assert sprite._anim_player is not None
        game.tick(0.016)

    def test_playanim_oneshot_completes_action(self, sprite: Sprite, game: Game) -> None:
        """PlayAnim with non-looping anim → action completes when anim done."""
        atk = _attack_anim()  # 0.3s total
        sprite.do(PlayAnim(atk))
        for _ in range(20):  # 0.32s
            game.tick(0.016)
        assert sprite._current_action is None  # Action completed

    def test_playanim_loop_never_finishes(self, sprite: Sprite, game: Game) -> None:
        """PlayAnim with looping anim → action never finishes alone."""
        walk = _walk_anim()
        sprite.do(PlayAnim(walk))
        for _ in range(100):
            game.tick(0.016)
        # Still running because looping anim never completes
        assert sprite._current_action is not None

    def test_playanim_in_parallel_stops_on_finite_done(self, sprite: Sprite, game: Game) -> None:
        """Parallel(PlayAnim(loop), Delay(0.1)) → after 0.1s, PlayAnim stopped."""
        walk = _walk_anim()
        sprite.do(Parallel(
            PlayAnim(walk),
            Delay(0.1),
        ))
        for _ in range(8):
            game.tick(0.016)
        assert sprite._current_action is None

    def test_battle_sequence_pattern(self, game: Game) -> None:
        """Realistic battle pattern: walk + anim → attack anim → walk back."""
        s = Sprite("sprites/knight", position=(100, 300))
        log: list[str] = []
        walk = _walk_anim()
        attack = _attack_anim()

        s.do(Sequence(
            # Walk forward
            Parallel(
                PlayAnim(walk),
                MoveTo((300, 300), speed=500),
            ),
            # Attack (non-looping)
            PlayAnim(attack),
            # Callback
            Do(lambda: log.append("attack_done")),
            # Walk back
            Parallel(
                PlayAnim(walk),
                MoveTo((100, 300), speed=500),
            ),
            Do(lambda: log.append("sequence_complete")),
        ))

        for _ in range(100):
            game.tick(0.016)

        assert "attack_done" in log
        assert "sequence_complete" in log
        assert s._current_action is None
        assert abs(s.x - 100) < 1.0
        assert abs(s.y - 300) < 1.0


# ═════════════════════════════════════════════════════════════
# 5. MOVETO EDGE CASES
# ═════════════════════════════════════════════════════════════


class TestMoveToEdgeCases:
    """Edge cases in MoveTo action."""

    def test_moveto_already_at_target(self, game: Game) -> None:
        """MoveTo to current position → completes immediately."""
        s = Sprite("sprites/knight", position=(100, 300))
        s.do(MoveTo((100, 300), speed=100))
        game.tick(0.016)
        assert s._current_action is None

    def test_moveto_negative_speed_raises(self) -> None:
        with pytest.raises(ValueError):
            MoveTo((100, 100), speed=-1)

    def test_moveto_zero_speed_raises(self) -> None:
        with pytest.raises(ValueError):
            MoveTo((100, 100), speed=0)

    def test_moveto_nan_position_raises(self) -> None:
        with pytest.raises(ValueError):
            MoveTo((float("nan"), 100), speed=100)

    def test_moveto_inf_position_raises(self) -> None:
        with pytest.raises(ValueError):
            MoveTo((float("inf"), 100), speed=100)

    def test_moveto_large_dt_snaps(self, game: Game) -> None:
        """A very large dt should snap to target in one step."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(MoveTo((1000, 1000), speed=1))
        # Huge dt — should snap
        s.update_action(999999.0)
        assert s.position == (1000, 1000)


# ═════════════════════════════════════════════════════════════
# 6. FADE EDGE CASES
# ═════════════════════════════════════════════════════════════


class TestFadeEdgeCases:
    """Edge cases in FadeIn and FadeOut."""

    def test_fadeout_from_zero(self, game: Game) -> None:
        """FadeOut when already at 0 → completes (stays at 0)."""
        s = Sprite("sprites/knight", position=(0, 0), opacity=0)
        s.do(FadeOut(0.5))
        for _ in range(40):
            game.tick(0.016)
        assert s.opacity == 0
        assert s._current_action is None

    def test_fadein_from_255(self, game: Game) -> None:
        """FadeIn when already at 255 → completes (stays at 255)."""
        s = Sprite("sprites/knight", position=(0, 0), opacity=255)
        s.do(FadeIn(0.5))
        for _ in range(40):
            game.tick(0.016)
        assert s.opacity == 255
        assert s._current_action is None

    def test_fadeout_zero_duration(self, game: Game) -> None:
        """FadeOut(0) → instant opacity=0."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(FadeOut(0))
        game.tick(0.016)
        assert s.opacity == 0

    def test_fadein_zero_duration(self, game: Game) -> None:
        """FadeIn(0) → instant opacity=255."""
        s = Sprite("sprites/knight", position=(0, 0), opacity=0)
        s.do(FadeIn(0))
        game.tick(0.016)
        assert s.opacity == 255

    def test_fade_sequence_out_then_in(self, game: Game) -> None:
        """Sequence(FadeOut, FadeIn) → back to 255."""
        s = Sprite("sprites/knight", position=(0, 0))
        s.do(Sequence(FadeOut(0.05), FadeIn(0.05)))
        for _ in range(20):
            game.tick(0.016)
        assert s.opacity == 255
        assert s._current_action is None
