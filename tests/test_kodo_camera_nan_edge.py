"""Regression tests for Camera NaN/Inf edge cases (F31, F32, F33).

F31: Camera.shake() silently accepted NaN/Inf for intensity, duration, decay,
     causing NaN shake offsets → corrupted world_to_screen / screen_to_world.

F32: Camera.update() with NaN/Inf dt silently corrupted _x/_y through
     key_scroll and edge_scroll code paths.

F33: Camera follow() silently copied NaN position from a followed sprite
     with non-finite coordinates, corrupting the camera position.
"""

import math

import pytest

from saga2d.rendering.camera import Camera


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeSprite:
    """Minimal sprite-like object for follow() tests (no Game needed)."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.is_removed = False


# ===========================================================================
# F31 — Camera.shake() NaN/Inf guard
# ===========================================================================


class TestCameraShakeNaNInf:
    """shake() must reject non-finite intensity, duration, and decay."""

    # --- intensity ---

    def test_shake_nan_intensity_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.shake(float("nan"), 1.0, 1.0)

    def test_shake_inf_intensity_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.shake(float("inf"), 1.0, 1.0)

    def test_shake_neg_inf_intensity_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.shake(float("-inf"), 1.0, 1.0)

    # --- duration ---

    def test_shake_nan_duration_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.shake(10.0, float("nan"), 1.0)

    def test_shake_inf_duration_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.shake(10.0, float("inf"), 1.0)

    def test_shake_neg_inf_duration_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.shake(10.0, float("-inf"), 1.0)

    # --- decay ---

    def test_shake_nan_decay_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.shake(10.0, 1.0, float("nan"))

    def test_shake_inf_decay_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.shake(10.0, 1.0, float("inf"))

    def test_shake_neg_inf_decay_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.shake(10.0, 1.0, float("-inf"))

    # --- normal values still work ---

    def test_shake_finite_values_still_work(self):
        cam = Camera((800, 600))
        cam.shake(10.0, 1.0, 1.0)
        cam.update(0.016)
        assert math.isfinite(cam.shake_offset_x)
        assert math.isfinite(cam.shake_offset_y)

    def test_shake_zero_duration_still_resets(self):
        """duration=0 is valid — it resets any active shake."""
        cam = Camera((800, 600))
        cam.shake(10.0, 1.0, 1.0)
        cam.update(0.5)  # get a non-zero offset
        cam.shake(10.0, 0, 1.0)  # reset
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0

    def test_shake_negative_duration_still_resets(self):
        """Negative duration is treated as reset, not rejected."""
        cam = Camera((800, 600))
        cam.shake(10.0, -1.0, 1.0)
        assert cam._shake_duration == 0.0


# ===========================================================================
# F32 — Camera.update() NaN/Inf dt guard
# ===========================================================================


class TestCameraUpdateNaNInfDt:
    """update() must skip the frame when dt is non-finite."""

    # --- key scroll ---

    def test_key_scroll_nan_dt_preserves_position(self):
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        cam.enable_key_scroll(speed=300)
        cam._held_dirs.add("right")
        old_x = cam.x
        cam.update(float("nan"))
        assert cam.x == old_x

    def test_key_scroll_inf_dt_preserves_position(self):
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        cam.enable_key_scroll(speed=300)
        cam._held_dirs.add("right")
        old_x = cam.x
        cam.update(float("inf"))
        assert cam.x == old_x

    def test_key_scroll_neg_inf_dt_preserves_position(self):
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        cam.enable_key_scroll(speed=300)
        cam._held_dirs.add("left")
        old_x = cam.x
        cam.update(float("-inf"))
        assert cam.x == old_x

    # --- edge scroll ---

    def test_edge_scroll_nan_dt_preserves_position(self):
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        cam.enable_edge_scroll(margin=50, speed=200)
        old_x = cam.x
        cam.update(float("nan"), mouse_x=10, mouse_y=300)
        assert cam.x == old_x

    def test_edge_scroll_inf_dt_preserves_position(self):
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        cam.enable_edge_scroll(margin=50, speed=200)
        old_x = cam.x
        cam.update(float("inf"), mouse_x=10, mouse_y=300)
        assert cam.x == old_x

    # --- shake elapsed ---

    def test_shake_nan_dt_preserves_elapsed(self):
        cam = Camera((800, 600))
        cam.shake(10.0, 1.0, 1.0)
        cam.update(float("nan"))
        assert cam._shake_elapsed == 0.0
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0

    # --- follow (dt-independent, but entire frame is skipped) ---

    def test_follow_nan_dt_skips_frame(self):
        """Follow is dt-independent but update() skips the whole frame."""
        sprite = _FakeSprite(400, 300)
        cam = Camera((800, 600))
        cam.center_on(100, 100)
        old_x, old_y = cam.x, cam.y
        cam.follow(sprite)
        cam.update(float("nan"))
        # Follow didn't execute because entire frame was skipped.
        assert cam.x == old_x
        assert cam.y == old_y

    # --- normal dt still works ---

    def test_normal_dt_still_works(self):
        cam = Camera((800, 600))
        cam.enable_key_scroll(speed=300)
        cam._held_dirs.add("right")
        cam.update(0.016)
        assert cam.x > 0.0


# ===========================================================================
# F33 — Camera.follow() NaN target position guard
# ===========================================================================


class TestCameraFollowNaNTarget:
    """follow() must not copy non-finite positions from the followed sprite."""

    def test_follow_nan_x_preserves_position(self):
        sprite = _FakeSprite(float("nan"), 300)
        cam = Camera((800, 600))
        cam.center_on(100, 100)
        old_x, old_y = cam.x, cam.y
        cam.follow(sprite)
        cam.update(0.016)
        assert cam.x == old_x
        assert cam.y == old_y

    def test_follow_nan_y_preserves_position(self):
        sprite = _FakeSprite(400, float("nan"))
        cam = Camera((800, 600))
        cam.center_on(100, 100)
        old_x, old_y = cam.x, cam.y
        cam.follow(sprite)
        cam.update(0.016)
        assert cam.x == old_x
        assert cam.y == old_y

    def test_follow_inf_preserves_position(self):
        sprite = _FakeSprite(float("inf"), 300)
        cam = Camera((800, 600))
        cam.center_on(100, 100)
        old_x = cam.x
        cam.follow(sprite)
        cam.update(0.016)
        assert cam.x == old_x

    def test_follow_target_becomes_nan_preserves_last_valid(self):
        """If a followed sprite's position becomes NaN mid-flight, the camera
        keeps its last valid position rather than corrupting."""
        sprite = _FakeSprite(400, 300)
        cam = Camera((800, 600))
        cam.follow(sprite)
        cam.update(0.016)
        valid_x, valid_y = cam.x, cam.y
        assert math.isfinite(valid_x)

        # Corrupt the sprite position.
        sprite.x = float("nan")
        cam.update(0.016)
        assert cam.x == valid_x
        assert cam.y == valid_y

    def test_follow_target_recovers_from_nan(self):
        """After the sprite's position returns to finite, following resumes."""
        sprite = _FakeSprite(400, 300)
        cam = Camera((800, 600))
        cam.follow(sprite)
        cam.update(0.016)
        valid_x = cam.x

        # NaN frame — position frozen.
        sprite.x = float("nan")
        cam.update(0.016)
        assert cam.x == valid_x

        # Recover.
        sprite.x = 600
        cam.update(0.016)
        assert cam.x != valid_x  # moved to follow new position
        assert math.isfinite(cam.x)

    def test_follow_finite_still_works(self):
        sprite = _FakeSprite(500, 400)
        cam = Camera((800, 600))
        cam.follow(sprite)
        cam.update(0.016)
        # Camera should be centered on sprite.
        expected_x = 500 - 800 / 2
        expected_y = 400 - 600 / 2
        assert cam.x == expected_x
        assert cam.y == expected_y

    def test_follow_nan_with_world_bounds_preserves_position(self):
        """With world_bounds, NaN still doesn't corrupt — the guard fires
        before _clamp() which would produce IEEE-754-dependent results."""
        sprite = _FakeSprite(float("nan"), 300)
        cam = Camera((800, 600), world_bounds=(0, 0, 2000, 2000))
        cam.center_on(500, 500)
        old_x, old_y = cam.x, cam.y
        cam.follow(sprite)
        cam.update(0.016)
        assert cam.x == old_x
        assert cam.y == old_y


# ===========================================================================
# Integration: coordinate conversion remains clean after NaN rejection
# ===========================================================================


class TestCameraCoordinateConversionAfterNaNGuard:
    """Verify that world_to_screen / screen_to_world stay finite after
    NaN inputs are properly rejected."""

    def test_world_to_screen_after_shake_rejection(self):
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        with pytest.raises(ValueError):
            cam.shake(float("nan"), 1.0, 1.0)
        sx, sy = cam.world_to_screen(400, 300)
        assert math.isfinite(sx) and math.isfinite(sy)

    def test_screen_to_world_after_update_nan_dt(self):
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        cam.enable_key_scroll(speed=300)
        cam._held_dirs.add("right")
        cam.update(float("nan"))
        wx, wy = cam.screen_to_world(100, 100)
        assert math.isfinite(wx) and math.isfinite(wy)

    def test_world_to_screen_after_follow_nan(self):
        sprite = _FakeSprite(float("nan"), float("nan"))
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        cam.follow(sprite)
        cam.update(0.016)
        sx, sy = cam.world_to_screen(400, 300)
        assert math.isfinite(sx) and math.isfinite(sy)
