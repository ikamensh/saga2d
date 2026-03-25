"""Stage 3 regression tests — UI/Rendering validation edge cases.

Covers fixes F44–F56 introduced in the Stage 3 tester pass (2026-03-25).
All tests run headless (SAGA2D_HEADLESS=1).

Run:
    SAGA2D_HEADLESS=1 uv run python -m pytest tests/test_kodo_stage3_ui_rendering_regression.py -v
"""
from __future__ import annotations

import math
import os
from pathlib import Path
import tempfile
from typing import Any

import pytest

os.environ.setdefault("SAGA2D_HEADLESS", "1")

from saga2d.animation import AnimationPlayer
from saga2d.game import Game
from saga2d.rendering.camera import Camera
from saga2d.rendering.particles import ParticleEmitter
from saga2d.rendering.sprite import Sprite
from saga2d.save import SaveManager
from saga2d.scene import Scene
from saga2d.ui.components import Button
from saga2d.ui.widgets import DataTable, Grid, ProgressBar, Tooltip


# ══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════════════

@pytest.fixture()
def game():
    """Create and teardown a headless Game."""
    g = Game(resolution=(800, 600), title="stage3-ui-rendering-regression")
    yield g
    g._teardown()


@pytest.fixture()
def scene(game):
    """Push a scene onto the game."""
    s = Scene()
    game.push(s)
    return s


# ══════════════════════════════════════════════════════════════════════════════
# F44: ProgressBar constructor NaN/Inf validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF44ProgressBarConstructorValidation:
    """ProgressBar constructor should reject NaN/Inf for value and max_value."""

    def test_value_nan_raises(self):
        with pytest.raises(ValueError, match="value must be a finite"):
            ProgressBar(value=float("nan"), max_value=100)

    def test_value_inf_raises(self):
        with pytest.raises(ValueError, match="value must be a finite"):
            ProgressBar(value=float("inf"), max_value=100)

    def test_value_neg_inf_raises(self):
        with pytest.raises(ValueError, match="value must be a finite"):
            ProgressBar(value=float("-inf"), max_value=100)

    def test_max_value_nan_raises(self):
        with pytest.raises(ValueError, match="max_value must be a finite"):
            ProgressBar(value=50, max_value=float("nan"))

    def test_max_value_inf_raises(self):
        with pytest.raises(ValueError, match="max_value must be a finite"):
            ProgressBar(value=50, max_value=float("inf"))

    def test_max_value_neg_inf_raises(self):
        with pytest.raises(ValueError, match="max_value must be a finite"):
            ProgressBar(value=50, max_value=float("-inf"))

    def test_both_nan_raises(self):
        with pytest.raises(ValueError, match="finite"):
            ProgressBar(value=float("nan"), max_value=float("nan"))

    def test_valid_values_accepted(self):
        bar = ProgressBar(value=25, max_value=100)
        assert bar.fraction == 0.25

    def test_zero_max_value_accepted(self):
        bar = ProgressBar(value=0, max_value=0)
        assert bar.fraction == 0.0

    def test_negative_max_value_accepted(self):
        """Negative max_value is valid (fraction guard returns 0.0)."""
        bar = ProgressBar(value=50, max_value=-5)
        assert bar.fraction == 0.0

    def test_setter_still_validates(self):
        """The setter validation is preserved."""
        bar = ProgressBar(value=0, max_value=100)
        with pytest.raises(ValueError, match="finite"):
            bar.value = float("nan")


# ══════════════════════════════════════════════════════════════════════════════
# F45: Button.text setter None guard
# ══════════════════════════════════════════════════════════════════════════════

class TestF45ButtonTextNoneGuard:
    """Button.text setter should reject None."""

    def test_none_raises_type_error(self):
        btn = Button("OK")
        with pytest.raises(TypeError, match="must be a string"):
            btn.text = None

    def test_empty_string_accepted(self):
        btn = Button("OK")
        btn.text = ""
        assert btn.text == ""

    def test_string_accepted(self):
        btn = Button("OK")
        btn.text = "Cancel"
        assert btn.text == "Cancel"


# ══════════════════════════════════════════════════════════════════════════════
# F46: ParticleEmitter.position setter NaN validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF46ParticleEmitterPositionValidation:
    """ParticleEmitter.position setter should reject NaN/Inf."""

    def test_nan_x_raises(self, game, scene):
        em = ParticleEmitter("sprites/knight", position=(50, 50),
                             speed=(10, 20), direction=(0, 360),
                             lifetime=(0.5, 1.0))
        with pytest.raises(ValueError, match="finite"):
            em.position = (float("nan"), 0)

    def test_nan_y_raises(self, game, scene):
        em = ParticleEmitter("sprites/knight", position=(50, 50),
                             speed=(10, 20), direction=(0, 360),
                             lifetime=(0.5, 1.0))
        with pytest.raises(ValueError, match="finite"):
            em.position = (0, float("nan"))

    def test_inf_raises(self, game, scene):
        em = ParticleEmitter("sprites/knight", position=(50, 50),
                             speed=(10, 20), direction=(0, 360),
                             lifetime=(0.5, 1.0))
        with pytest.raises(ValueError, match="finite"):
            em.position = (float("inf"), 0)

    def test_valid_position_accepted(self, game, scene):
        em = ParticleEmitter("sprites/knight", position=(50, 50),
                             speed=(10, 20), direction=(0, 360),
                             lifetime=(0.5, 1.0))
        em.position = (100, 200)
        assert em.position == (100.0, 200.0)


# ══════════════════════════════════════════════════════════════════════════════
# F47: AnimationPlayer.update(dt=NaN) guard
# ══════════════════════════════════════════════════════════════════════════════

class TestF47AnimationPlayerNaNGuard:
    """AnimationPlayer.update should skip NaN dt without corrupting state."""

    def test_nan_dt_returns_none(self):
        player = AnimationPlayer(["f0", "f1", "f2"],
                                 frame_duration=0.1, loop=False)
        result = player.update(float("nan"))
        assert result is None

    def test_nan_dt_preserves_elapsed(self):
        player = AnimationPlayer(["f0", "f1", "f2"],
                                 frame_duration=0.1, loop=False)
        player.update(0.05)
        old_elapsed = player._elapsed
        player.update(float("nan"))
        assert player._elapsed == old_elapsed

    def test_nan_dt_animation_recovers(self):
        """After NaN dt, normal updates should work."""
        player = AnimationPlayer(["f0", "f1", "f2"],
                                 frame_duration=0.1, loop=False)
        player.update(float("nan"))
        assert player.frame_index == 0
        player.update(0.15)
        assert player.frame_index == 1

    def test_inf_dt_returns_none(self):
        player = AnimationPlayer(["f0", "f1", "f2"],
                                 frame_duration=0.1, loop=False)
        result = player.update(float("inf"))
        assert result is None

    def test_neg_inf_dt_returns_none(self):
        player = AnimationPlayer(["f0", "f1", "f2"],
                                 frame_duration=0.1, loop=False)
        result = player.update(float("-inf"))
        assert result is None


# ══════════════════════════════════════════════════════════════════════════════
# F48: Camera.enable_edge_scroll validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF48CameraEdgeScrollValidation:
    """enable_edge_scroll should reject NaN/Inf margin and speed."""

    def test_nan_margin_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.enable_edge_scroll(margin=float("nan"), speed=100)

    def test_nan_speed_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.enable_edge_scroll(margin=50, speed=float("nan"))

    def test_inf_speed_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.enable_edge_scroll(margin=50, speed=float("inf"))

    def test_inf_margin_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.enable_edge_scroll(margin=float("inf"), speed=100)

    def test_valid_values_accepted(self):
        cam = Camera((800, 600))
        cam.enable_edge_scroll(margin=50, speed=100)
        assert cam._edge_scroll_enabled
        assert cam._edge_margin == 50
        assert cam._edge_speed == 100


# ══════════════════════════════════════════════════════════════════════════════
# F49: Camera.enable_key_scroll validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF49CameraKeyScrollValidation:
    """enable_key_scroll should reject NaN/Inf speed."""

    def test_nan_speed_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.enable_key_scroll(speed=float("nan"))

    def test_inf_speed_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.enable_key_scroll(speed=float("inf"))

    def test_neg_inf_speed_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.enable_key_scroll(speed=float("-inf"))

    def test_default_speed_accepted(self):
        cam = Camera((800, 600))
        cam.enable_key_scroll()  # default speed=300
        assert cam._key_scroll_enabled
        assert cam._key_scroll_speed == 300

    def test_custom_speed_accepted(self):
        cam = Camera((800, 600))
        cam.enable_key_scroll(speed=500)
        assert cam._key_scroll_speed == 500


# ══════════════════════════════════════════════════════════════════════════════
# F50: Camera.world_bounds setter validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF50CameraWorldBoundsValidation:
    """world_bounds setter should reject NaN, Inf, and inverted bounds."""

    def test_nan_left_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.world_bounds = (float("nan"), 0, 800, 600)

    def test_nan_right_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.world_bounds = (0, 0, float("nan"), 600)

    def test_inf_top_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.world_bounds = (0, float("inf"), 800, 600)

    def test_inf_bottom_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.world_bounds = (0, 0, 800, float("-inf"))

    def test_inverted_left_right_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="left.*right"):
            cam.world_bounds = (100, 0, 50, 600)

    def test_inverted_top_bottom_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="top.*bottom"):
            cam.world_bounds = (0, 600, 800, 100)

    def test_none_accepted(self):
        cam = Camera((800, 600))
        cam.world_bounds = None
        assert cam.world_bounds is None

    def test_valid_bounds_accepted(self):
        cam = Camera((800, 600))
        cam.world_bounds = (0, 0, 1600, 1200)
        assert cam.world_bounds == (0, 0, 1600, 1200)

    def test_equal_left_right_accepted(self):
        """Degenerate bounds (left == right) are valid."""
        cam = Camera((800, 600))
        cam.world_bounds = (100, 0, 100, 600)
        assert cam.world_bounds == (100, 0, 100, 600)


# ══════════════════════════════════════════════════════════════════════════════
# F51: Tooltip delay validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF51TooltipDelayValidation:
    """Tooltip constructor should reject NaN, Inf, and negative delay."""

    def test_nan_delay_raises(self):
        with pytest.raises(ValueError, match="finite"):
            Tooltip("help", delay=float("nan"))

    def test_inf_delay_raises(self):
        with pytest.raises(ValueError, match="finite"):
            Tooltip("help", delay=float("inf"))

    def test_neg_inf_delay_raises(self):
        with pytest.raises(ValueError, match="finite"):
            Tooltip("help", delay=float("-inf"))

    def test_negative_delay_raises(self):
        with pytest.raises(ValueError, match="delay must be >= 0"):
            Tooltip("help", delay=-1)

    def test_negative_float_delay_raises(self):
        with pytest.raises(ValueError, match="delay must be >= 0"):
            Tooltip("help", delay=-0.001)

    def test_zero_delay_accepted(self):
        tip = Tooltip("help", delay=0)
        assert tip._delay == 0

    def test_positive_delay_accepted(self):
        tip = Tooltip("help", delay=0.5)
        assert tip._delay == 0.5

    def test_default_delay_accepted(self):
        tip = Tooltip("help")
        assert tip._delay == 0.5


# ══════════════════════════════════════════════════════════════════════════════
# F52: Sprite.tint NaN/Inf validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF52SpriteTintValidation:
    """Sprite.tint setter should reject NaN/Inf components."""

    def test_nan_r_raises(self, game, scene):
        sprite = Sprite("sprites/knight", position=(100, 100))
        scene.add_sprite(sprite)
        with pytest.raises(ValueError, match="finite"):
            sprite.tint = (float("nan"), 0.5, 0.5)

    def test_nan_g_raises(self, game, scene):
        sprite = Sprite("sprites/knight", position=(100, 100))
        scene.add_sprite(sprite)
        with pytest.raises(ValueError, match="finite"):
            sprite.tint = (0.5, float("nan"), 0.5)

    def test_nan_b_raises(self, game, scene):
        sprite = Sprite("sprites/knight", position=(100, 100))
        scene.add_sprite(sprite)
        with pytest.raises(ValueError, match="finite"):
            sprite.tint = (0.5, 0.5, float("nan"))

    def test_inf_raises(self, game, scene):
        sprite = Sprite("sprites/knight", position=(100, 100))
        scene.add_sprite(sprite)
        with pytest.raises(ValueError, match="finite"):
            sprite.tint = (float("inf"), 0.0, float("-inf"))

    def test_valid_tint_clamped(self, game, scene):
        sprite = Sprite("sprites/knight", position=(100, 100))
        scene.add_sprite(sprite)
        sprite.tint = (2.0, -1.0, 0.5)
        assert sprite.tint == (1.0, 0.0, 0.5)

    def test_normal_tint(self, game, scene):
        sprite = Sprite("sprites/knight", position=(100, 100))
        scene.add_sprite(sprite)
        sprite.tint = (0.2, 0.4, 0.8)
        assert sprite.tint == (0.2, 0.4, 0.8)


# ══════════════════════════════════════════════════════════════════════════════
# F53: Sprite.move_to NaN target validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF53SpriteMoveToTargetValidation:
    """Sprite.move_to should reject NaN/Inf target coordinates."""

    def test_nan_x_raises(self, game, scene):
        sprite = Sprite("sprites/knight", position=(0, 0))
        scene.add_sprite(sprite)
        with pytest.raises(ValueError, match="finite"):
            sprite.move_to((float("nan"), 100), speed=100)

    def test_nan_y_raises(self, game, scene):
        sprite = Sprite("sprites/knight", position=(0, 0))
        scene.add_sprite(sprite)
        with pytest.raises(ValueError, match="finite"):
            sprite.move_to((100, float("nan")), speed=100)

    def test_inf_target_raises(self, game, scene):
        sprite = Sprite("sprites/knight", position=(0, 0))
        scene.add_sprite(sprite)
        with pytest.raises(ValueError, match="finite"):
            sprite.move_to((float("inf"), 0), speed=100)

    def test_neg_inf_target_raises(self, game, scene):
        sprite = Sprite("sprites/knight", position=(0, 0))
        scene.add_sprite(sprite)
        with pytest.raises(ValueError, match="finite"):
            sprite.move_to((0, float("-inf")), speed=100)

    def test_valid_target_accepted(self, game, scene):
        sprite = Sprite("sprites/knight", position=(0, 0))
        scene.add_sprite(sprite)
        arrived = [False]
        sprite.move_to((100, 200), speed=1000,
                       on_arrive=lambda: arrived.__setitem__(0, True))
        # Advance enough time for arrival
        for _ in range(100):
            game.tick(0.016)
        assert arrived[0], "Sprite should have arrived at valid target"


# ══════════════════════════════════════════════════════════════════════════════
# F54: DataTable row_height validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF54DataTableRowHeightValidation:
    """DataTable constructor should reject row_height <= 0."""

    def test_zero_row_height_raises(self):
        with pytest.raises(ValueError, match="row_height must be positive"):
            DataTable(columns=["A"], rows=[["x"]], row_height=0)

    def test_negative_row_height_raises(self):
        with pytest.raises(ValueError, match="row_height must be positive"):
            DataTable(columns=["A"], rows=[["x"]], row_height=-10)

    def test_row_height_1_accepted(self):
        dt = DataTable(columns=["A"], rows=[["x"]], row_height=1)
        assert dt._row_height == 1

    def test_default_row_height_accepted(self):
        dt = DataTable(columns=["A"], rows=[["x"]])
        assert dt._row_height == 28

    def test_large_row_height_accepted(self):
        dt = DataTable(columns=["A"], rows=[["x"]], row_height=100)
        assert dt._row_height == 100


class TestDataTableShortColWidthsAcceptable:
    """DataTable with col_widths shorter than columns is ACCEPTABLE.

    The on_draw code handles this gracefully with fallback:
        cw = col_ws[i] if i < len(col_ws) else 0
    Columns beyond col_widths get width 0 (text overlaps at same x).
    This is deliberate API flexibility — not a crash bug.
    """

    def test_short_col_widths_accepted(self):
        dt = DataTable(
            columns=["Name", "Score", "Level"],
            col_widths=[100, 80],  # 2 widths for 3 columns
            rows=[["Alice", "100", "5"]],
        )
        ew = dt._effective_col_widths(8)
        assert len(ew) == 2  # shorter than columns, intentional
        assert ew == [100, 80]

    def test_short_col_widths_draw_no_crash(self, game):
        s = Scene()
        game.push(s)
        dt = DataTable(
            columns=["Name", "Score", "Level"],
            col_widths=[100],  # only 1 width for 3 columns
            rows=[["Alice", "100", "5"]],
            width=400, height=200,
        )
        s.ui.add(dt)
        game.tick(0.016)  # must not crash

    def test_empty_col_widths_accepted(self):
        dt = DataTable(
            columns=["Name", "Score"],
            col_widths=[],  # empty list
            rows=[["Alice", "100"]],
        )
        ew = dt._effective_col_widths(8)
        assert ew == []


# ══════════════════════════════════════════════════════════════════════════════
# F55: Grid cell_size validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF55GridCellSizeValidation:
    """Grid constructor should reject negative cell_size dimensions."""

    def test_negative_width_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Grid(3, 3, cell_size=(-10, 64))

    def test_negative_height_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Grid(3, 3, cell_size=(64, -10))

    def test_both_negative_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Grid(3, 3, cell_size=(-5, -5))

    def test_zero_cell_size_accepted(self):
        """Zero cell_size is degenerate but valid (guarded by _cell_at)."""
        grid = Grid(3, 3, cell_size=(0, 0))
        assert grid._cell_w == 0
        assert grid._cell_h == 0

    def test_zero_width_only_accepted(self):
        grid = Grid(3, 3, cell_size=(0, 64))
        assert grid._cell_w == 0
        assert grid._cell_h == 64

    def test_positive_cell_size_accepted(self):
        grid = Grid(3, 3, cell_size=(64, 64))
        assert grid._cell_w == 64
        assert grid._cell_h == 64

    def test_default_cell_size_accepted(self):
        grid = Grid(3, 3)
        assert grid._cell_w == 64
        assert grid._cell_h == 64


class TestGridZeroCellSizeAcceptable:
    """Grid(cell_size=(0,0)) is ACCEPTABLE — guarded, no crash.

    _cell_at returns None for zero stride. Clicks select nothing.
    Draw emits zero-dimension rects. This is degenerate but safe.
    """

    def test_zero_cell_at_returns_none(self):
        grid = Grid(3, 3, cell_size=(0, 0), spacing=0)
        grid._computed_x, grid._computed_y = 0, 0
        grid._computed_w, grid._computed_h = 200, 200
        assert grid._cell_at(10, 10) is None

    def test_zero_cell_preferred_size_non_negative(self):
        grid = Grid(3, 3, cell_size=(0, 0), spacing=4)
        w, h = grid.get_preferred_size()
        assert w >= 0
        assert h >= 0

    def test_zero_cell_draw_no_crash(self, game):
        s = Scene()
        game.push(s)
        grid = Grid(2, 2, cell_size=(0, 0), width=100, height=100)
        s.ui.add(grid)
        game.tick(0.016)  # must not crash


# ══════════════════════════════════════════════════════════════════════════════
# F56: SaveLoadScreen slot_count validation
# ══════════════════════════════════════════════════════════════════════════════

class TestF56SaveLoadScreenSlotCountValidation:
    """SaveLoadScreen constructor should reject slot_count <= 0."""

    def test_zero_slot_count_raises(self):
        from saga2d.ui.screens import SaveLoadScreen
        with pytest.raises(ValueError, match="slot_count must be positive"):
            SaveLoadScreen(mode="load", slot_count=0)

    def test_negative_slot_count_raises(self):
        from saga2d.ui.screens import SaveLoadScreen
        with pytest.raises(ValueError, match="slot_count must be positive"):
            SaveLoadScreen(mode="load", slot_count=-1)

    def test_slot_count_1_accepted(self):
        from saga2d.ui.screens import SaveLoadScreen
        screen = SaveLoadScreen(mode="load", slot_count=1)
        assert screen._slot_count == 1

    def test_default_slot_count_accepted(self):
        from saga2d.ui.screens import SaveLoadScreen
        screen = SaveLoadScreen(mode="load")
        assert screen._slot_count == 10

    def test_large_slot_count_accepted(self):
        from saga2d.ui.screens import SaveLoadScreen
        screen = SaveLoadScreen(mode="save", slot_count=100)
        assert screen._slot_count == 100
