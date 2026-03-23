"""Focused regression tests for risky edge cases exercised in Stage 3.

Covers exactly the cases explicitly requested:
  1. Grid zero dimensions (0×0, 0×N, N×0)
  2. TabGroup empty / invalid key
  3. ProgressBar max_value<=0 and negative value
  4. ParticleEmitter lifetime=(0,0) with fade_out=True
  5. AnimationPlayer frame_duration=0
  6. List item_height=0

Each test is minimal, aligned with current behaviour, and avoids
duplicating the broad coverage in test_kodo_timer_widget_edge.py or
test_kodo_crossfade_repro.py.  The focus here is on *regression*:
confirming that the risky paths don't crash, produce sane output,
and that validation guards remain in place.
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from saga2d import Game, Label, Scene
from saga2d.animation import AnimationDef, AnimationPlayer
from saga2d.rendering.particles import ParticleEmitter
from saga2d.ui.widgets import Grid, List, ProgressBar, TabGroup


# ==================================================================
# Helpers
# ==================================================================


@pytest.fixture
def game() -> Game:
    """Headless Game instance for tests that need a live game context."""
    g = Game("Stage3Regression", backend="mock", resolution=(800, 600))
    yield g
    g._teardown()


def _attach_to_scene(game: Game, widget: Any) -> Scene:
    """Push a scene, add *widget* to its UI, and force layout."""
    scene = Scene()
    game.push(scene)
    scene.ui.add(widget)
    scene.ui._ensure_layout()
    return scene


# ==================================================================
# 1. Grid — zero dimensions
# ==================================================================


class TestGridZeroDimensions:
    """Grid(0, 0), Grid(0, N), and Grid(N, 0) regression."""

    def test_zero_grid_set_cell_is_noop(self) -> None:
        """set_cell on a 0×0 grid doesn't crash (out-of-range col/row)."""
        grid = Grid(0, 0)
        # No validation on col/row in set_cell — it just stores.
        grid.set_cell(0, 0, Label("x"))
        # The child is added but won't be drawn (on_draw iterates range(0)).
        assert grid.get_cell(0, 0) is not None

    def test_zero_cols_nonzero_rows(self) -> None:
        """Grid(0, 5) has zero columns — preferred width is just padding."""
        grid = Grid(0, 5)
        w, h = grid.get_preferred_size()
        assert w >= 0
        # Height should include 5 rows of cells.
        assert h > 0
        # Selection setter must clear because columns <= 0.
        grid.selected = (0, 0)
        assert grid.selected is None

    def test_nonzero_cols_zero_rows(self) -> None:
        """Grid(3, 0) has zero rows — preferred height is just padding."""
        grid = Grid(3, 0)
        w, h = grid.get_preferred_size()
        assert w > 0
        assert h >= 0
        grid.selected = (0, 0)
        assert grid.selected is None

    def test_zero_grid_full_tick_no_crash(self, game: Game) -> None:
        """Grid(0, 0) survives a full game tick with draw + event dispatch."""
        grid = Grid(0, 0)
        _attach_to_scene(game, grid)
        # A full tick includes update + draw.
        game.tick(dt=0.016)  # must not crash

    def test_zero_grid_click_event_no_crash(self, game: Game) -> None:
        """Click inside a 0×0 grid region doesn't crash (_cell_at → None)."""
        grid = Grid(0, 0, width=100, height=100)
        _attach_to_scene(game, grid)
        backend = game.backend
        backend.inject_click(50, 50)
        game.tick(dt=0.016)  # must not crash
        assert grid.selected is None


# ==================================================================
# 2. TabGroup — empty / invalid key
# ==================================================================


class TestTabGroupEmptyInvalidKey:
    """TabGroup with no tabs, empty dict, and bad select_tab calls."""

    def test_empty_tabgroup_preferred_size(self) -> None:
        """Preferred size with no content panels returns sensible defaults."""
        tg = TabGroup()
        w, h = tg.get_preferred_size()
        # Width falls back to max(0, 100) = 100; height = tab_height + 0
        assert w == 100
        assert h == tg.tab_height

    def test_empty_tabgroup_get_tab_content_returns_none(self) -> None:
        """get_tab_content on empty TabGroup returns None."""
        tg = TabGroup()
        assert tg.get_tab_content("anything") is None

    def test_select_tab_empty_raises_keyerror(self) -> None:
        """select_tab on empty TabGroup raises KeyError with informative msg."""
        tg = TabGroup()
        with pytest.raises(KeyError, match="No tab named"):
            tg.select_tab("ghost")

    def test_empty_tabgroup_full_tick_no_crash(self, game: Game) -> None:
        """Empty TabGroup survives a full game tick (draw + events)."""
        tg = TabGroup()
        _attach_to_scene(game, tg)
        game.tick(dt=0.016)

    def test_add_then_remove_tab_then_select_old_raises(self) -> None:
        """After removing the only tab, selecting it raises KeyError."""
        tg = TabGroup()
        lbl = Label("content")
        tg.add_tab("Solo", lbl)
        assert tg.active_tab == "Solo"
        # Manually remove to test stale key.
        tg._tab_labels.remove("Solo")
        del tg._tab_components["Solo"]
        tg._active_tab = None
        with pytest.raises(KeyError, match="No tab named 'Solo'"):
            tg.select_tab("Solo")

    def test_invalid_key_on_populated_tabgroup(self) -> None:
        """Selecting a non-existent key on a populated TabGroup lists available tabs."""
        tg = TabGroup(tabs={"Alpha": Label("a"), "Beta": Label("b")})
        with pytest.raises(KeyError, match="'Alpha'.*'Beta'|'Beta'.*'Alpha'"):
            tg.select_tab("Gamma")


# ==================================================================
# 3. ProgressBar — max_value<=0 and negative value
# ==================================================================


class TestProgressBarEdgeValues:
    """ProgressBar fraction and draw safety for degenerate max/value."""

    def test_negative_max_value_fraction_zero(self) -> None:
        """max_value < 0 ⇒ fraction returns 0.0 (guarded by <= 0 check)."""
        bar = ProgressBar(value=50, max_value=-100)
        assert bar.fraction == 0.0

    def test_negative_value_fraction_clamped(self) -> None:
        """Negative value is clamped to 0.0 by max(0.0, …)."""
        bar = ProgressBar(value=-999, max_value=100)
        assert bar.fraction == 0.0

    def test_both_negative(self) -> None:
        """value<0 and max_value<0: max_value<=0 guard returns 0.0."""
        bar = ProgressBar(value=-10, max_value=-5)
        assert bar.fraction == 0.0

    def test_zero_max_value_draw_no_crash(self, game: Game) -> None:
        """Draw with max_value=0 produces zero-width fill bar, no crash."""
        bar = ProgressBar(value=10, max_value=0, rounded=False)
        _attach_to_scene(game, bar)
        game.tick(dt=0.016)  # must not crash

    def test_negative_max_value_draw_rounded(self, game: Game) -> None:
        """Draw rounded ProgressBar with max_value<0 — fraction=0, no crash."""
        bar = ProgressBar(value=5, max_value=-10, rounded=True)
        _attach_to_scene(game, bar)
        game.tick(dt=0.016)

    def test_value_mutation_after_init(self) -> None:
        """Setting value to negative after init still gives clamped fraction."""
        bar = ProgressBar(value=50, max_value=100)
        assert bar.fraction == 0.5
        bar.value = -100
        assert bar.fraction == 0.0

    def test_max_value_zero_value_zero(self) -> None:
        """0/0 case: guarded by max_value<=0 ⇒ 0.0."""
        bar = ProgressBar(value=0, max_value=0)
        assert bar.fraction == 0.0


# ==================================================================
# 4. ParticleEmitter — lifetime=(0,0) with fade_out=True
# ==================================================================


class TestParticleEmitterZeroLifetimeFadeOut:
    """lifetime=(0,0) + fade_out=True: particles die immediately
    and the fade path (ratio = remaining / total_lifetime) must not
    divide by zero because particles are removed before the fade
    branch executes (remaining <= 0 check comes first).
    """

    def test_burst_zero_lifetime_fade_all_die_immediately(self, game: Game) -> None:
        """All particles die on the first update tick (remaining <= 0)."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(0.0, 0.0),
            fade_out=True,
            speed=(0, 0),
        )
        em.burst(10)
        assert len(em._particles) == 10
        em.update(0.001)  # any positive dt kills them
        assert len(em._particles) == 0

    def test_burst_zero_lifetime_fade_no_nan_opacity(self, game: Game) -> None:
        """Even with fade_out=True, particles never reach the fade branch
        because they are removed first (remaining <= 0 before fade calc).
        No sprite should have NaN opacity.
        """
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(0.0, 0.0),
            fade_out=True,
            speed=(0, 0),
        )
        em.burst(5)
        # Check that total_lifetime is 0 on all particles.
        for p in em._particles:
            assert p.total_lifetime == 0.0
            assert p.fade_out is True
        em.update(0.001)
        # All dead — no opacity calculation occurred with 0 denominator.
        assert len(em._particles) == 0

    def test_continuous_zero_lifetime_fade_cleanup(self, game: Game) -> None:
        """Continuous emitter with zero lifetime: spawned particles die
        each tick, emitter stays active due to continuous_rate > 0."""
        em = ParticleEmitter(
            "sprites/knight",
            position=(100, 100),
            lifetime=(0.0, 0.0),
            fade_out=True,
            speed=(0, 0),
        )
        em.continuous(rate=100)
        em.update(0.1)  # spawns ~10 particles, all die immediately
        # Particles spawned during update die in the same update cycle's
        # next iteration — but actually they're spawned first, then aged.
        # With remaining=0, they all die.
        assert len(em._particles) == 0
        assert em.is_active  # still active because rate > 0
        em.stop()


# ==================================================================
# 5. AnimationPlayer — frame_duration=0
# ==================================================================


class TestAnimationPlayerFrameDurationZero:
    """frame_duration=0 caused an infinite loop pre-fix.
    Now both AnimationDef and AnimationPlayer reject it at init.
    This test confirms the guard remains in place.
    """

    def test_animationdef_rejects_zero(self) -> None:
        """AnimationDef(frame_duration=0) → ValueError."""
        with pytest.raises(ValueError, match="positive finite number"):
            AnimationDef(frames=["a", "b"], frame_duration=0.0)

    def test_animationdef_rejects_negative(self) -> None:
        """AnimationDef(frame_duration=-1) → ValueError."""
        with pytest.raises(ValueError, match="positive finite number"):
            AnimationDef(frames=["a", "b"], frame_duration=-1.0)

    def test_animationplayer_rejects_zero(self) -> None:
        """AnimationPlayer(frame_duration=0) → ValueError."""
        with pytest.raises(ValueError, match="positive finite number"):
            AnimationPlayer(frames=["h1", "h2"], frame_duration=0.0, loop=True)

    def test_animationplayer_rejects_negative(self) -> None:
        """AnimationPlayer(frame_duration=-0.5) → ValueError."""
        with pytest.raises(ValueError, match="positive finite number"):
            AnimationPlayer(frames=["h1"], frame_duration=-0.5, loop=False)

    def test_animationplayer_rejects_nan(self) -> None:
        """AnimationPlayer(frame_duration=NaN) → ValueError."""
        with pytest.raises(ValueError, match="positive finite number"):
            AnimationPlayer(
                frames=["h1", "h2"], frame_duration=float("nan"), loop=True
            )

    def test_animationplayer_rejects_inf(self) -> None:
        """AnimationPlayer(frame_duration=+Inf) → ValueError."""
        with pytest.raises(ValueError, match="positive finite number"):
            AnimationPlayer(
                frames=["h1", "h2"], frame_duration=float("inf"), loop=False
            )

    def test_valid_frame_duration_plays_normally(self) -> None:
        """Positive frame_duration works fine (sanity check)."""
        player = AnimationPlayer(
            frames=["h1", "h2", "h3"], frame_duration=0.1, loop=False
        )
        assert player.is_playing
        # Advance past all frames.
        player.update(0.35)
        assert player.is_complete


# ==================================================================
# 6. List — item_height=0
# ==================================================================


class TestListItemHeightZero:
    """List with item_height=0: visible_count returns 0, clicks are
    guarded, keyboard nav still works (selection moves, draw is safe).
    """

    def test_visible_count_zero(self) -> None:
        """_visible_count returns 0 when item_height=0."""
        lst = List(items=["a", "b", "c"], item_height=0)
        assert lst._visible_count() == 0

    def test_preferred_size_height_uses_item_height(self) -> None:
        """With item_height=0 and no explicit height,
        preferred height = max(0*3, 0) = 0."""
        lst = List(items=["a", "b", "c"], item_height=0)
        _, h = lst.get_preferred_size()
        assert h == 0

    def test_click_with_zero_item_height_no_crash(self, game: Game) -> None:
        """Click event on List(item_height=0) hits the guard and returns True
        without attempting division by zero."""
        lst = List(items=["a", "b"], item_height=0, width=200, height=100)
        _attach_to_scene(game, lst)
        backend = game.backend
        backend.inject_click(100, 50)
        game.tick(dt=0.016)  # must not crash
        # Selection unchanged — click guard returns early.
        assert lst.selected_index is None

    def test_keyboard_nav_still_works(self) -> None:
        """Keyboard navigation (move_selection) is independent of item_height."""
        lst = List(items=["x", "y", "z"], item_height=0)
        lst._move_selection(1)  # select first
        assert lst.selected_index == 0
        lst._move_selection(1)
        assert lst.selected_index == 1

    def test_draw_with_game_no_crash(self, game: Game) -> None:
        """on_draw with item_height=0 draws background but skips item rows
        because visible_count=0 → end = min(0+0, len) = 0."""
        lst = List(items=["a", "b", "c"], item_height=0, width=200, height=100)
        _attach_to_scene(game, lst)
        game.tick(dt=0.016)  # draw path must not crash

    def test_motion_with_zero_item_height_no_crash(self, game: Game) -> None:
        """Mouse motion event on List(item_height=0) hits the guard."""
        lst = List(items=["a"], item_height=0, width=200, height=100)
        _attach_to_scene(game, lst)
        backend = game.backend
        backend.inject_mouse_move(100, 50)
        game.tick(dt=0.016)  # must not crash
