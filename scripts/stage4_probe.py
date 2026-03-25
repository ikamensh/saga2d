#!/usr/bin/env python3
"""Stage 4 runtime probes — integration/lifecycle edge cases.

Run: SAGA2D_HEADLESS=1 uv run python scripts/stage4_probe.py
"""
from __future__ import annotations
import os, sys, traceback

os.environ["SAGA2D_HEADLESS"] = "1"

RESULTS: list[tuple[str, str, str]] = []  # (name, status, detail)
ALL_PROBES: list[tuple[str, object]] = []  # (name, fn)

def probe(name: str):
    """Decorator to register and wrap a probe function."""
    def decorator(fn):
        def wrapper():
            try:
                fn()
                RESULTS.append((name, "PASS", ""))
            except AssertionError as e:
                RESULTS.append((name, "FAIL", str(e)))
            except Exception as e:
                RESULTS.append((name, "ERROR", f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))
            finally:
                # Safety: ensure singleton is cleared even if probe fails
                try:
                    import saga2d.rendering.sprite as sm
                    if sm._current_game is not None:
                        sm._current_game._teardown()
                except Exception:
                    # Force-clear the singleton if teardown itself fails
                    try:
                        import saga2d.rendering.sprite as sm
                        import saga2d.util.tween as tm
                        sm._current_game = None
                        tm._tween_manager = None
                    except Exception:
                        pass
        ALL_PROBES.append((name, wrapper))
        return wrapper
    return decorator


def make_game():
    from saga2d.game import Game
    return Game("probe", backend="mock", resolution=(800, 600))

def teardown_game(game):
    game._teardown()


# =========================================================================
# AREA 1: Scene stack transitions during active actions/timers
# =========================================================================

@probe("1a_action_survives_scene_pop")
def _():
    """Active action on scene-owned sprite: action stopped when scene pops."""
    from saga2d.scene import Scene
    from saga2d.actions import Sequence, Delay, Do
    from saga2d.rendering.sprite import Sprite

    g = make_game()
    try:
        action_log = []
        class S1(Scene):
            def on_enter(self):
                self.sp = self.add_sprite(Sprite("sprites/knight", position=(100, 100)))
                self.sp.do(Sequence(Delay(1.0), Do(lambda: action_log.append("done"))))
        s1 = S1()
        g.push(s1)
        g.tick(0.1)
        assert s1.sp._current_action is not None
        g.pop()
        for _ in range(20):
            g.tick(0.1)
        assert s1.sp.is_removed
        assert "done" not in action_log
    finally:
        teardown_game(g)

@probe("1b_timer_cancelled_on_scene_pop")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        log = []
        class S1(Scene):
            def on_enter(self):
                self.after(0.5, lambda: log.append("fired"))
        g.push(S1())
        g.tick(0.1)
        g.pop()
        for _ in range(20):
            g.tick(0.1)
        assert log == [], f"timer should be cancelled on pop, got {log}"
    finally:
        teardown_game(g)

@probe("1c_timer_survives_scene_push_over")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        log = []
        class S1(Scene):
            def on_enter(self):
                self.after(0.3, lambda: log.append("fired"))
        class S2(Scene):
            pass
        g.push(S1())
        g.tick(0.01)
        g.push(S2())
        for _ in range(10):
            g.tick(0.05)
        assert "fired" in log, f"timer should survive push-over, got {log}"
    finally:
        teardown_game(g)

@probe("1d_action_on_non_owned_sprite_survives_pop")
def _():
    from saga2d.scene import Scene
    from saga2d.actions import Sequence, Delay, Do
    from saga2d.rendering.sprite import Sprite
    g = make_game()
    try:
        log = []
        class S1(Scene):
            def on_enter(self):
                self.free_sprite = Sprite("sprites/knight", position=(100, 100))
                self.free_sprite.do(Sequence(Delay(0.3), Do(lambda: log.append("done"))))
        s1 = S1()
        g.push(s1)
        g.tick(0.1)
        free_sp = s1.free_sprite
        g.pop()
        assert not free_sp.is_removed
        for _ in range(10):
            g.tick(0.1)
        assert "done" in log, f"action on non-owned sprite should complete, got {log}"
    finally:
        teardown_game(g)

@probe("1e_scene_replace_cleans_actions")
def _():
    from saga2d.scene import Scene
    from saga2d.actions import Sequence, Delay, Do
    from saga2d.rendering.sprite import Sprite
    g = make_game()
    try:
        log = []
        class S1(Scene):
            def on_enter(self):
                self.sp = self.add_sprite(Sprite("sprites/knight", position=(100, 100)))
                self.sp.do(Sequence(Delay(1.0), Do(lambda: log.append("s1_done"))))
        class S2(Scene):
            pass
        s1 = S1()
        g.push(s1)
        g.tick(0.1)
        g.replace(S2())
        for _ in range(20):
            g.tick(0.1)
        assert s1.sp.is_removed
        assert "s1_done" not in log
    finally:
        teardown_game(g)

@probe("1f_timer_chain_cancelled_on_pop")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        log = []
        class S1(Scene):
            def on_enter(self):
                self.after(0.1, lambda: log.append("s1")) \
                    .then(lambda: log.append("s2"), 0.1) \
                    .then(lambda: log.append("s3"), 0.1)
        g.push(S1())
        g.tick(0.05)
        g.pop()
        for _ in range(30):
            g.tick(0.1)
        assert log == [], f"timer chain should be cancelled on pop, got {log}"
    finally:
        teardown_game(g)

@probe("1g_every_timer_cancelled_on_pop")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        log = []
        class S1(Scene):
            def on_enter(self):
                self.every(0.1, lambda: log.append("t"))
        g.push(S1())
        g.tick(0.15)
        count = len(log)
        g.pop()
        for _ in range(20):
            g.tick(0.1)
        assert len(log) == count, f"repeating timer should stop on pop; was {count}, now {len(log)}"
    finally:
        teardown_game(g)

@probe("1h_scene_push_during_action_callback")
def _():
    from saga2d.scene import Scene
    from saga2d.actions import Sequence, Do
    from saga2d.rendering.sprite import Sprite
    g = make_game()
    try:
        class S2(Scene):
            pass
        class S1(Scene):
            def on_enter(self):
                self.sp = self.add_sprite(Sprite("sprites/knight", position=(100, 100)))
                self.sp.do(Sequence(Do(lambda: g.push(S2()))))
        g.push(S1())
        g.tick(0.016)
        assert isinstance(g._scene_stack.top(), S2)
    finally:
        teardown_game(g)

@probe("1i_clear_and_push_kills_all_timers_and_actions")
def _():
    from saga2d.scene import Scene
    from saga2d.actions import Sequence, Delay, Do
    from saga2d.rendering.sprite import Sprite
    g = make_game()
    try:
        log = []
        class S1(Scene):
            def on_enter(self):
                self.sp = self.add_sprite(Sprite("sprites/knight", position=(100, 100)))
                self.sp.do(Sequence(Delay(1.0), Do(lambda: log.append("s1_act"))))
                self.after(1.0, lambda: log.append("s1_tmr"))
                self.every(0.1, lambda: log.append("s1_ev"))
        class S2(Scene):
            def on_enter(self):
                self.sp = self.add_sprite(Sprite("sprites/knight", position=(200, 200)))
                self.sp.do(Sequence(Delay(1.0), Do(lambda: log.append("s2_act"))))
                self.after(1.0, lambda: log.append("s2_tmr"))
        class S3(Scene):
            pass
        g.push(S1())
        g.tick(0.05)
        g.push(S2())
        g.tick(0.05)
        log.clear()
        g.clear_and_push(S3())
        for _ in range(30):
            g.tick(0.1)
        assert log == [], f"all timers/actions from cleared scenes should be dead, got {log}"
    finally:
        teardown_game(g)


# =========================================================================
# AREA 2: Exceptions in scene hooks
# =========================================================================

@probe("2a_on_enter_exception_rollback")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        class Good(Scene):
            pass
        class Bad(Scene):
            def on_enter(self):
                raise RuntimeError("boom")
        g.push(Good())
        top_before = g._scene_stack.top()
        try:
            g.push(Bad())
        except RuntimeError:
            pass
        assert g._scene_stack.top() is top_before
    finally:
        teardown_game(g)

@probe("2b_on_exit_exception_cleanup_still_happens")
def _():
    from saga2d.scene import Scene
    from saga2d.rendering.sprite import Sprite
    g = make_game()
    try:
        class S1(Scene):
            pass
        class S2(Scene):
            def on_enter(self):
                self.sp = self.add_sprite(Sprite("sprites/knight", position=(100, 100)))
            def on_exit(self):
                raise RuntimeError("boom")
        g.push(S1())
        s2 = S2()
        g.push(s2)
        g.tick(0.01)
        try:
            g.pop()
        except RuntimeError:
            pass
        assert g._scene_stack.top().__class__.__name__ == "S1"
        assert s2.sp.is_removed
    finally:
        teardown_game(g)

@probe("2c_on_reveal_exception")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        class S1(Scene):
            def on_reveal(self):
                raise RuntimeError("boom")
        class S2(Scene):
            pass
        g.push(S1())
        g.push(S2())
        try:
            g.pop()
        except RuntimeError:
            pass
        assert g._scene_stack.top().__class__.__name__ == "S1"
    finally:
        teardown_game(g)

@probe("2d_on_exit_exception_in_clear_and_push")
def _():
    from saga2d.scene import Scene
    from saga2d.rendering.sprite import Sprite
    g = make_game()
    try:
        class S1(Scene):
            def on_enter(self):
                self.sp = self.add_sprite(Sprite("sprites/knight", position=(100, 100)))
        class S2(Scene):
            def on_enter(self):
                self.sp = self.add_sprite(Sprite("sprites/knight", position=(200, 200)))
            def on_exit(self):
                raise RuntimeError("boom")
        class S3(Scene):
            pass
        s1 = S1()
        g.push(s1)
        g.tick(0.01)
        s2 = S2()
        g.push(s2)
        g.tick(0.01)
        try:
            g.clear_and_push(S3())
        except RuntimeError:
            pass
        assert s1.sp.is_removed, "s1 sprite should be cleaned up"
        assert s2.sp.is_removed, "s2 sprite should be cleaned up"
    finally:
        teardown_game(g)

@probe("2e_on_exit_exception_in_replace")
def _():
    """Exception in on_exit during replace: what state is the stack in?"""
    from saga2d.scene import Scene
    g = make_game()
    try:
        class S1(Scene):
            def on_exit(self):
                raise RuntimeError("boom")
        class S2(Scene):
            pass
        g.push(S1())
        try:
            g.replace(S2())
        except RuntimeError:
            pass
        top = g._scene_stack.top()
        # After _apply_replace: on_exit raises, but try/finally ensures
        # cleanup + pop still happen. Then S2 should be pushed.
        RESULTS.append(("2e_detail", "INFO",
            f"top={type(top).__name__ if top else 'None'}, stack_len={len(g._scene_stack._stack)}"))
    finally:
        teardown_game(g)

@probe("2f_update_exception_propagates")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        class Bad(Scene):
            def update(self, dt):
                raise RuntimeError("boom")
        g.push(Bad())
        try:
            g.tick(0.016)
            assert False, "should propagate"
        except RuntimeError as e:
            assert "boom" in str(e)
    finally:
        teardown_game(g)

@probe("2g_deferred_push_on_enter_exception")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        class Bad(Scene):
            def on_enter(self):
                raise RuntimeError("boom")
        class S1(Scene):
            def update(self, dt):
                g.push(Bad())
        g.push(S1())
        try:
            g.tick(0.016)
        except RuntimeError:
            pass
        top = g._scene_stack.top()
        assert isinstance(top, S1), f"S1 should remain after failed deferred push, got {type(top).__name__}"
    finally:
        teardown_game(g)

@probe("2h_draw_exception_end_frame_called")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        calls = []
        orig = g._backend.end_frame
        def tracking():
            calls.append("end_frame")
            return orig()
        g._backend.end_frame = tracking
        class Bad(Scene):
            def draw(self):
                raise RuntimeError("boom")
        g.push(Bad())
        try:
            g.tick(0.016)
        except RuntimeError:
            pass
        assert "end_frame" in calls
    finally:
        teardown_game(g)


# =========================================================================
# AREA 3: Repeated Game initialization/teardown
# =========================================================================

@probe("3a_repeated_init_teardown_cycles")
def _():
    from saga2d.game import Game
    from saga2d.scene import Scene
    from saga2d.rendering.sprite import Sprite
    for i in range(5):
        g = Game("probe", backend="mock", resolution=(800, 600))
        g.push(Scene())
        sp = Sprite("sprites/knight", position=(100, 100))
        g.tick(0.016)
        g._teardown()
    g = Game("probe", backend="mock", resolution=(800, 600))
    g.tick(0.016)
    g._teardown()

@probe("3b_singleton_guard")
def _():
    from saga2d.game import Game
    g1 = Game("probe", backend="mock", resolution=(800, 600))
    try:
        g2 = Game("probe2", backend="mock", resolution=(800, 600))
        g2._teardown()
        g1._teardown()
        assert False, "should raise RuntimeError"
    except RuntimeError as e:
        assert "already exists" in str(e)
    finally:
        g1._teardown()

@probe("3c_teardown_calls_on_exit_for_all")
def _():
    from saga2d.scene import Scene
    g = make_game()
    log = []
    class S(Scene):
        def __init__(self, n):
            super().__init__()
            self.n = n
        def on_exit(self):
            log.append(self.n)
    g.push(S("a"))
    g.push(S("b"))
    g.push(S("c"))
    g.tick(0.01)
    g._teardown()
    assert set(log) == {"a", "b", "c"}, f"all scenes on_exit during teardown, got {log}"

@probe("3d_teardown_survives_on_exit_exception")
def _():
    from saga2d.scene import Scene
    g = make_game()
    log = []
    class Good(Scene):
        def __init__(self, n):
            super().__init__()
            self.n = n
        def on_exit(self):
            log.append(self.n)
    class Bad(Scene):
        def __init__(self):
            super().__init__()
            self._in_teardown = False
        def on_exit(self):
            log.append("bad")
            if self._in_teardown:
                raise RuntimeError("boom")
    g.push(Good("a"))
    bad = Bad()
    g.push(bad)
    g.push(Good("c"))
    g.tick(0.01)
    # Now set flag so on_exit raises only during teardown
    bad._in_teardown = True
    log.clear()
    g._teardown()
    assert "a" in log and "bad" in log and "c" in log, f"all scenes should get on_exit, got {log}"

@probe("3e_double_teardown_safe")
def _():
    from saga2d.scene import Scene
    g = make_game()
    g.push(Scene())
    g.tick(0.01)
    g._teardown()
    g._teardown()  # should not crash

@probe("3f_tick_after_teardown")
def _():
    """Tick after teardown: observe behavior."""
    from saga2d.scene import Scene
    g = make_game()
    g.push(Scene())
    g.tick(0.01)
    g._teardown()
    try:
        g.tick(0.016)
        RESULTS.append(("3f_detail", "INFO", "tick after teardown succeeded silently"))
    except Exception as e:
        RESULTS.append(("3f_detail", "INFO", f"tick after teardown raised {type(e).__name__}: {e}"))

@probe("3g_sprite_after_teardown_fails_cleanly")
def _():
    from saga2d.scene import Scene
    from saga2d.rendering.sprite import Sprite
    g = make_game()
    g.push(Scene())
    g.tick(0.01)
    g._teardown()
    try:
        sp = Sprite("sprites/knight", position=(100, 100))
        assert False, "should raise RuntimeError"
    except RuntimeError as e:
        assert "No active Game" in str(e)

@probe("3h_teardown_cancels_game_timers")
def _():
    from saga2d.scene import Scene
    g = make_game()
    g.push(Scene())
    g.after(0.5, lambda: None)
    g.every(0.1, lambda: None)
    g.tick(0.05)
    g._teardown()
    assert g._timer_manager._timers == {}


# =========================================================================
# AREA 4: Deferred operations safety/limits
# =========================================================================

@probe("4a_deferred_push_from_update")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        class S2(Scene):
            pass
        class S1(Scene):
            pushed = False
            def update(self, dt):
                if not self.pushed:
                    self.pushed = True
                    g.push(S2())
        g.push(S1())
        g.tick(0.016)
        assert isinstance(g._scene_stack.top(), S2)
    finally:
        teardown_game(g)

@probe("4b_deferred_pop_from_update")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        class S2(Scene):
            def update(self, dt):
                g.pop()
        class S1(Scene):
            pass
        g.push(S1())
        g.push(S2())
        g.tick(0.016)
        assert isinstance(g._scene_stack.top(), S1)
    finally:
        teardown_game(g)

@probe("4c_deferred_ops_limit_1000")
def _():
    """Verify the 1000-iteration cap in flush_pending_ops prevents infinite loops.
    Must test via deferred path (from update, not direct on_enter)."""
    from saga2d.scene import Scene
    g = make_game()
    try:
        count = [0]
        class Inf(Scene):
            def on_enter(self):
                count[0] += 1
                if count[0] < 2000:
                    g.push(Inf())  # deferred during flush (flushing=True)

        class Trigger(Scene):
            done = False
            def update(self, dt):
                if not self.done:
                    self.done = True
                    g.push(Inf())  # deferred during tick

        g.push(Trigger())
        g.tick(0.016)
        RESULTS.append(("4c_detail", "INFO", f"push_count={count[0]} (cap should limit near 1000)"))
        assert count[0] <= 1100, f"should be capped, got {count[0]}"
    finally:
        teardown_game(g)

@probe("4d_deferred_push_from_on_exit")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        class Repl(Scene):
            pass
        class S2(Scene):
            def on_exit(self):
                g.push(Repl())
        g.push(Scene())
        g.push(S2())
        g.pop()
        assert isinstance(g._scene_stack.top(), Repl)
    finally:
        teardown_game(g)

@probe("4e_deferred_ops_fifo_order")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        log = []
        class S3(Scene):
            def on_enter(self):
                log.append("s3")
        class S2(Scene):
            def on_enter(self):
                log.append("s2")
        class S1(Scene):
            def update(self, dt):
                g.push(S2())
                g.push(S3())
        g.push(S1())
        g.tick(0.016)
        assert log == ["s2", "s3"], f"FIFO order, got {log}"
        assert isinstance(g._scene_stack.top(), S3)
    finally:
        teardown_game(g)

@probe("4f_deferred_clear_and_push_from_update")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        class Fresh(Scene):
            pass
        class S1(Scene):
            def update(self, dt):
                g.clear_and_push(Fresh())
        g.push(S1())
        g.tick(0.016)
        assert isinstance(g._scene_stack.top(), Fresh)
        assert len(g._scene_stack._stack) == 1
    finally:
        teardown_game(g)

@probe("4g_deferred_replace_from_input")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        class Fresh(Scene):
            pass
        class S1(Scene):
            def handle_input(self, event):
                if event.type == "key_press":
                    g.replace(Fresh())
                    return True
                return False
        g.push(S1())
        g._backend.inject_key("space")
        g.tick(0.016)
        assert isinstance(g._scene_stack.top(), Fresh)
    finally:
        teardown_game(g)

@probe("4h_nested_deferred_ops")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        log = []
        class S3(Scene):
            def on_enter(self):
                log.append("s3")
        class S2(Scene):
            def on_enter(self):
                log.append("s2")
                g.push(S3())
        class S1(Scene):
            def update(self, dt):
                g.push(S2())
        g.push(S1())
        g.tick(0.016)
        assert "s2" in log and "s3" in log
        assert isinstance(g._scene_stack.top(), S3)
    finally:
        teardown_game(g)

@probe("4i_pop_on_cancel_deferred")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        class S2(Scene):
            pop_on_cancel = True
        class S1(Scene):
            pass
        g.push(S1())
        g.push(S2())
        g._backend.inject_key("escape")
        g.tick(0.016)
        assert isinstance(g._scene_stack.top(), S1)
    finally:
        teardown_game(g)


# =========================================================================
# AREA 5: Additional edge cases
# =========================================================================

@probe("5a_pause_below_false_updates_both")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        log = []
        class S1(Scene):
            def update(self, dt):
                log.append("s1")
        class S2(Scene):
            pause_below = False
            def update(self, dt):
                log.append("s2")
        g.push(S1())
        g.push(S2())
        log.clear()
        g.tick(0.016)
        assert "s1" in log and "s2" in log
    finally:
        teardown_game(g)

@probe("5b_action_callback_exception")
def _():
    from saga2d.scene import Scene
    from saga2d.actions import Sequence, Do
    from saga2d.rendering.sprite import Sprite
    g = make_game()
    try:
        class S1(Scene):
            def on_enter(self):
                self.sp = self.add_sprite(Sprite("sprites/knight", position=(100, 100)))
                def boom():
                    raise RuntimeError("Do boom")
                self.sp.do(Do(boom))
        g.push(S1())
        try:
            g.tick(0.016)
            RESULTS.append(("5b_detail", "INFO", "Do() exception did NOT propagate (absorbed)"))
        except RuntimeError:
            RESULTS.append(("5b_detail", "INFO", "Do() exception propagated to tick caller"))
    finally:
        teardown_game(g)

@probe("5c_game_timer_exception_does_not_kill_others")
def _():
    from saga2d.scene import Scene
    g = make_game()
    try:
        g.push(Scene())
        g.after(0.01, lambda: 1/0)
        log = []
        g.after(0.01, lambda: log.append("ok"))
        g.tick(0.02)
        assert "ok" in log
    finally:
        teardown_game(g)

@probe("5d_tween_manager_cleared_on_teardown")
def _():
    from saga2d.scene import Scene
    g = make_game()
    g.push(Scene())
    g.tick(0.01)
    g._teardown()
    assert len(g._tween_manager._tweens) == 0

@probe("5e_on_exit_push_processed")
def _():
    """Operations pushed from on_exit during direct pop are processed."""
    from saga2d.scene import Scene
    g = make_game()
    try:
        log = []
        class Repl(Scene):
            def on_enter(self):
                log.append("repl_enter")
        class S2(Scene):
            def on_exit(self):
                g.push(Repl())
        g.push(Scene())  # base
        g.push(S2())
        g.pop()  # direct pop (not deferred)
        assert "repl_enter" in log, f"on_exit push should be processed, got {log}"
    finally:
        teardown_game(g)

@probe("5f_timer_still_fires_after_one_shot_timer_in_chain_cancelled")
def _():
    """Partial chain cancellation: cancelled one-shot timer shouldn't affect others."""
    from saga2d.scene import Scene
    g = make_game()
    try:
        g.push(Scene())
        log = []
        h1 = g.after(0.1, lambda: log.append("h1"))
        h2 = g.after(0.2, lambda: log.append("h2"))
        g.cancel(h1)
        for _ in range(10):
            g.tick(0.05)
        assert "h1" not in log
        assert "h2" in log
    finally:
        teardown_game(g)

@probe("5g_scene_pop_during_input_handling")
def _():
    """Pop from handle_input is deferred, remaining input events still processed."""
    from saga2d.scene import Scene
    g = make_game()
    try:
        log = []
        class S2(Scene):
            def handle_input(self, event):
                if event.type == "key_press" and event.key == "a":
                    g.pop()
                    return True
                return False
        class S1(Scene):
            def handle_input(self, event):
                log.append(f"s1_got_{event.key}")
                return True
        g.push(S1())
        g.push(S2())
        g._backend.inject_key("a")
        g.tick(0.016)
        # After tick, S2 should be popped
        assert isinstance(g._scene_stack.top(), S1)
    finally:
        teardown_game(g)


# =========================================================================
# Run all probes
# =========================================================================

if __name__ == "__main__":
    print(f"Running {len(ALL_PROBES)} Stage 4 probes...\n")

    for name, fn in ALL_PROBES:
        print(f"  Running {name}...", end="", flush=True)
        fn()
        # Get the last result for this probe
        last = [r for r in RESULTS if r[0] == name]
        if last:
            print(f" {last[-1][1]}")
        else:
            print(" ???")

    passes = sum(1 for _, s, _ in RESULTS if s == "PASS")
    fails = sum(1 for _, s, _ in RESULTS if s == "FAIL")
    errors = sum(1 for _, s, _ in RESULTS if s == "ERROR")
    infos = sum(1 for _, s, _ in RESULTS if s == "INFO")

    print(f"\n{'='*70}")
    print(f"Results: {passes} PASS, {fails} FAIL, {errors} ERROR, {infos} INFO")
    print(f"{'='*70}\n")

    for name, status, detail in RESULTS:
        icon = {"PASS": "✓", "FAIL": "✗", "ERROR": "⚠", "INFO": "ℹ"}.get(status, "?")
        line = f"  {icon} [{status}] {name}"
        if detail:
            # Truncate long tracebacks
            short = detail.split("\n")[0] if len(detail) > 200 else detail
            line += f"\n    → {short}"
        print(line)

    if fails or errors:
        print(f"\n{'='*70}")
        print(f"ATTENTION: {fails + errors} issue(s) found!")
        sys.exit(1)
    else:
        print(f"\nAll probes passed.")
