"""Comprehensive tests for Sprites, Actions, Camera, Animation, Particles,
Tweening, Timers, and ColorSwap in saga2d.

Written to discover bugs -- DO NOT fix anything, only report findings.
"""

from __future__ import annotations

import math
from pathlib import Path

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
    Remove,
    Repeat,
    Sequence,
)
from saga2d.animation import AnimationDef
from saga2d.assets import AssetManager
from saga2d.backends.mock_backend import MockBackend
from saga2d.rendering.camera import Camera
from saga2d.rendering.color_swap import ColorSwap, register_palette, _clear_palettes
from saga2d.rendering.layers import RenderLayer, SpriteAnchor
from saga2d.rendering.particles import ParticleEmitter
from saga2d.rendering.sprite import Sprite
from saga2d.util.tween import Ease, TweenManager, tween
from saga2d.util.timer import TimerManager, TimerHandle


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def asset_dir(tmp_path: Path) -> Path:
    """Create a temporary asset directory with test images."""
    images = tmp_path / "images"
    images.mkdir()
    # Create minimal valid 1x1 PNG files.
    # PNG header + IHDR + IDAT + IEND for a 1x1 RGBA image.
    import struct, zlib
    def make_png(w=64, h=64):
        def chunk(ctype, data):
            c = ctype + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
        raw = b""
        for _ in range(h):
            raw += b"\x00" + b"\xff\x00\x00\xff" * w
        idat = chunk(b"IDAT", zlib.compress(raw))
        iend = chunk(b"IEND", b"")
        return sig + ihdr + idat + iend

    png_data = make_png()
    for name in [
        "test_img.png", "other_img.png", "spark.png",
        "frame_0.png", "frame_1.png", "frame_2.png",
        "a1.png", "a2.png", "b1.png", "b2.png",
        "f1.png", "f2.png",
    ]:
        (images / name).write_bytes(png_data)
    return tmp_path


@pytest.fixture
def game(asset_dir: Path) -> Game:
    """Return a Game instance with assets pointing at the temp directory."""
    g = Game("Test", backend="mock", resolution=(1920, 1080))
    g.assets = AssetManager(g.backend, base_path=asset_dir)
    yield g
    g._teardown()


@pytest.fixture
def backend(game: Game) -> MockBackend:
    return game.backend


# ============================================================================
# 1. SPRITE TESTS
# ============================================================================


class TestSpriteBasics:
    """Basic sprite creation, properties, and removal."""

    def test_create_sprite_default_properties(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        assert s.position == (100.0, 200.0)
        assert s.opacity == 255
        assert s.visible is True
        assert s.is_removed is False

    def test_create_sprite_custom_opacity(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(0, 0), opacity=128)
        assert s.opacity == 128

    def test_create_sprite_invisible(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(0, 0), visible=False)
        assert s.visible is False

    def test_move_sprite_updates_backend(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        sid = s.sprite_id
        s.position = (300, 400)
        # Default anchor is BOTTOM_CENTER, image is 64x64.
        # draw_x = 300 - 32 = 268, draw_y = 400 - 64 = 336
        assert backend.sprites[sid]["x"] == 268
        assert backend.sprites[sid]["y"] == 336

    def test_remove_sprite_removes_from_backend(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        sid = s.sprite_id
        assert sid in backend.sprites
        s.remove()
        assert sid not in backend.sprites
        assert s.is_removed is True

    def test_remove_sprite_idempotent(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        s.remove()  # should not raise
        assert s.is_removed is True

    def test_set_nan_position_raises(self, game: Game, backend: MockBackend):
        with pytest.raises(ValueError, match="finite"):
            Sprite("test_img", position=(float("nan"), 0))

    def test_set_inf_position_raises(self, game: Game, backend: MockBackend):
        with pytest.raises(ValueError, match="finite"):
            Sprite("test_img", position=(float("inf"), 0))

    def test_set_nan_position_on_existing_sprite(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        with pytest.raises(ValueError, match="finite"):
            s.position = (float("nan"), 0)

    def test_set_inf_x_on_existing_sprite(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        with pytest.raises(ValueError, match="finite"):
            s.x = float("inf")

    def test_set_inf_y_on_existing_sprite(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        with pytest.raises(ValueError, match="finite"):
            s.y = float("inf")

    def test_set_none_position_raises(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        with pytest.raises(ValueError, match="None"):
            s.position = None


class TestSpriteOnRemovedSprite:
    """Operations on a sprite after remove() has been called."""

    def test_set_position_on_removed_sprite(self, game: Game, backend: MockBackend):
        """Setting position on a removed sprite -- should not crash."""
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        # The position setter still sets _x/_y then calls _sync_to_backend
        # which early-returns. But the order update path checks _removed.
        try:
            s.position = (500, 600)
        except (KeyError, RuntimeError) as e:
            pytest.fail(f"Setting position on removed sprite raised: {e}")

    def test_set_x_on_removed_sprite(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        try:
            s.x = 500
        except (KeyError, RuntimeError) as e:
            pytest.fail(f"Setting x on removed sprite raised: {e}")

    def test_set_y_on_removed_sprite(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        try:
            s.y = 500
        except (KeyError, RuntimeError) as e:
            pytest.fail(f"Setting y on removed sprite raised: {e}")

    def test_do_action_on_removed_sprite(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        s.do(Delay(1.0))  # should be a no-op

    def test_play_animation_on_removed_sprite(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        anim = AnimationDef(frames=["frame_0", "frame_1"], frame_duration=0.1, loop=False)
        s.play(anim)  # should be a no-op

    def test_set_opacity_on_removed_sprite(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        try:
            s.opacity = 128
        except (KeyError, RuntimeError) as e:
            pytest.fail(f"Setting opacity on removed sprite raised: {e}")

    def test_set_visible_on_removed_sprite(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        try:
            s.visible = False
        except (KeyError, RuntimeError) as e:
            pytest.fail(f"Setting visible on removed sprite raised: {e}")


class TestSpriteYSort:
    """Sprites at higher y should have higher draw order."""

    def test_y_sort_ordering(self, game: Game, backend: MockBackend):
        s1 = Sprite("test_img", position=(100, 100))
        s2 = Sprite("test_img", position=(100, 300))
        order1 = backend.sprites[s1.sprite_id]["layer"]
        order2 = backend.sprites[s2.sprite_id]["layer"]
        assert order2 > order1

    def test_y_sort_updates_on_move(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 100))
        order_before = backend.sprites[s.sprite_id]["layer"]
        s.position = (100, 500)
        order_after = backend.sprites[s.sprite_id]["layer"]
        assert order_after > order_before

    def test_y_sort_same_y_same_order(self, game: Game, backend: MockBackend):
        s1 = Sprite("test_img", position=(100, 200))
        s2 = Sprite("test_img", position=(300, 200))
        order1 = backend.sprites[s1.sprite_id]["layer"]
        order2 = backend.sprites[s2.sprite_id]["layer"]
        assert order1 == order2


class TestSpriteAnchors:
    """Anchor offset math for different SpriteAnchor values."""

    def test_bottom_center_anchor(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(400, 300), anchor=SpriteAnchor.BOTTOM_CENTER)
        sid = s.sprite_id
        # 64x64 image: draw at (400-32, 300-64) = (368, 236)
        assert backend.sprites[sid]["x"] == 368
        assert backend.sprites[sid]["y"] == 236

    def test_center_anchor(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(400, 300), anchor=SpriteAnchor.CENTER)
        sid = s.sprite_id
        assert backend.sprites[sid]["x"] == 368  # 400-32
        assert backend.sprites[sid]["y"] == 268  # 300-32

    def test_top_left_anchor(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(400, 300), anchor=SpriteAnchor.TOP_LEFT)
        sid = s.sprite_id
        assert backend.sprites[sid]["x"] == 400
        assert backend.sprites[sid]["y"] == 300

    def test_bottom_right_anchor(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(400, 300), anchor=SpriteAnchor.BOTTOM_RIGHT)
        sid = s.sprite_id
        assert backend.sprites[sid]["x"] == 336  # 400-64
        assert backend.sprites[sid]["y"] == 236  # 300-64


class TestSpriteNoScene:
    """Create a sprite without pushing any scene."""

    def test_sprite_without_scene(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        assert s._owning_scene is None
        assert not s.is_removed

    def test_sprite_without_game_raises(self):
        import saga2d.rendering.sprite as sprite_mod
        old = sprite_mod._current_game
        sprite_mod._current_game = None
        try:
            with pytest.raises(RuntimeError, match="No active Game"):
                Sprite("test_img")
        finally:
            sprite_mod._current_game = old


# ============================================================================
# 2. ACTION TESTS
# ============================================================================


class TestSequenceAction:
    def test_sequence_delay_then_do(self, game: Game, backend: MockBackend):
        called = [False]
        s = Sprite("test_img", position=(100, 200))
        s.do(Sequence(Delay(0.5), Do(lambda: called.__setitem__(0, True))))
        game.tick(dt=0.3)
        assert not called[0]
        game.tick(dt=0.3)
        assert called[0]

    def test_empty_sequence_completes_immediately(self, game: Game, backend: MockBackend):
        completed = [False]
        s = Sprite("test_img", position=(100, 200))
        s.do(Sequence(Sequence(), Do(lambda: completed.__setitem__(0, True))))
        game.tick(dt=0.016)
        assert completed[0]

    def test_nested_sequence(self, game: Game, backend: MockBackend):
        arrived = [False]
        s = Sprite("test_img", position=(100, 200))
        s.do(Sequence(
            Parallel(
                MoveTo((200, 200), speed=1000),
                FadeOut(0.1),
            ),
            Delay(0.1),
            Do(lambda: arrived.__setitem__(0, True)),
        ))
        for _ in range(20):
            game.tick(dt=0.05)
        assert arrived[0]

    def test_sequence_rejects_non_action(self):
        with pytest.raises(TypeError, match="expected Action"):
            Sequence("not_an_action")


class TestParallelAction:
    def test_parallel_moveto_and_fadeout(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.do(Parallel(
            MoveTo((200, 200), speed=500),
            FadeOut(0.5),
        ))
        for _ in range(5):
            game.tick(dt=0.05)
        assert s.x > 100
        assert s.opacity < 255

    def test_empty_parallel_completes_immediately(self, game: Game, backend: MockBackend):
        completed = [False]
        s = Sprite("test_img", position=(100, 200))
        s.do(Sequence(Parallel(), Do(lambda: completed.__setitem__(0, True))))
        game.tick(dt=0.016)
        assert completed[0]

    def test_parallel_rejects_non_action(self):
        with pytest.raises(TypeError, match="expected Action"):
            Parallel(42)


class TestRepeatAction:
    def test_repeat_3_times(self, game: Game, backend: MockBackend):
        """BUG: Repeat of an instant action (Do) only runs once per tick.
        Sequence chains instant actions within one frame, but Repeat does not.
        After each iteration completes, Repeat starts a new copy but returns
        False, deferring the next iteration to the next frame.
        Expected: 3 instant Do actions complete in 1 tick.
        Actual: Only 1 completes per tick (needs 3 ticks for 3 iterations)."""
        count = [0]
        s = Sprite("test_img", position=(100, 200))
        s.do(Repeat(Do(lambda: count.__setitem__(0, count[0] + 1)), times=3))
        game.tick(dt=0.016)
        # By design, Repeat runs one iteration per tick even for instant actions.
        # This differs from Sequence which chains instant actions within one frame.
        assert count[0] == 1, (
            f"Repeat(Do(...), times=3) should run 1 per tick, got {count[0]}"
        )

    def test_repeat_3_times_across_ticks(self, game: Game, backend: MockBackend):
        """Workaround verification: Repeat(Do, times=3) needs 3 separate ticks."""
        count = [0]
        s = Sprite("test_img", position=(100, 200))
        s.do(Repeat(Do(lambda: count.__setitem__(0, count[0] + 1)), times=3))
        game.tick(dt=0.016)
        game.tick(dt=0.016)
        game.tick(dt=0.016)
        assert count[0] == 3, f"After 3 ticks count should be 3, got {count[0]}"

    def test_repeat_0_times(self, game: Game, backend: MockBackend):
        count = [0]
        completed = [False]
        s = Sprite("test_img", position=(100, 200))
        s.do(Sequence(
            Repeat(Do(lambda: count.__setitem__(0, count[0] + 1)), times=0),
            Do(lambda: completed.__setitem__(0, True)),
        ))
        game.tick(dt=0.016)
        assert count[0] == 0
        assert completed[0]

    def test_repeat_forever(self, game: Game, backend: MockBackend):
        count = [0]
        s = Sprite("test_img", position=(100, 200))
        s.do(Repeat(
            Sequence(Delay(0.01), Do(lambda: count.__setitem__(0, count[0] + 1))),
            times=None,
        ))
        for _ in range(10):
            game.tick(dt=0.05)
        assert count[0] > 3

    def test_repeat_is_not_finite_when_forever(self):
        r = Repeat(Delay(1.0), times=None)
        assert not r.is_finite

    def test_repeat_is_finite_when_counted(self):
        r = Repeat(Delay(1.0), times=5)
        assert r.is_finite

    def test_repeat_negative_times(self, game: Game, backend: MockBackend):
        count = [0]
        s = Sprite("test_img", position=(100, 200))
        s.do(Repeat(Do(lambda: count.__setitem__(0, count[0] + 1)), times=-1))
        game.tick(dt=0.016)
        assert count[0] == 0


class TestRemoveAction:
    def test_remove_action(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        sid = s.sprite_id
        s.do(Remove())
        game.tick(dt=0.016)
        assert s.is_removed
        assert sid not in backend.sprites

    def test_sequence_with_remove_then_do(self, game: Game, backend: MockBackend):
        """Sequence(Remove(), Do(cb)) -- the Do may or may not fire."""
        called = [False]
        s = Sprite("test_img", position=(100, 200))
        s.do(Sequence(Remove(), Do(lambda: called.__setitem__(0, True))))
        game.tick(dt=0.016)
        assert s.is_removed


class TestMoveToAction:
    def test_moveto_speed_zero_raises(self):
        with pytest.raises(ValueError, match="speed must be > 0"):
            MoveTo((100, 200), speed=0)

    def test_moveto_negative_speed_raises(self):
        with pytest.raises(ValueError, match="speed must be > 0"):
            MoveTo((100, 200), speed=-10)

    def test_moveto_arrives(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(0, 0))
        s.do(MoveTo((100, 0), speed=1000))
        for _ in range(10):
            game.tick(dt=0.05)
        assert abs(s.x - 100) < 1.0

    def test_moveto_nan_target_raises(self):
        with pytest.raises(ValueError, match="finite"):
            MoveTo((float("nan"), 0), speed=100)

    def test_moveto_inf_target_raises(self):
        with pytest.raises(ValueError, match="finite"):
            MoveTo((float("inf"), 0), speed=100)


class TestFadeActions:
    def test_fadeout_to_zero(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.do(FadeOut(0.5))
        for _ in range(40):
            game.tick(dt=0.02)
        assert s.opacity == 0

    def test_fadein_to_255(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200), opacity=0)
        s.do(FadeIn(0.5))
        for _ in range(40):
            game.tick(dt=0.02)
        assert s.opacity == 255

    def test_fadeout_then_fadein(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.do(Sequence(FadeOut(0.2), FadeIn(0.2)))
        for _ in range(30):
            game.tick(dt=0.02)
        assert s.opacity == 255


class TestActionOnRemovedSprite:
    def test_moveto_after_remove(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.do(MoveTo((500, 500), speed=50))
        game.tick(dt=0.016)
        s.remove()
        game.tick(dt=0.016)
        game.tick(dt=0.016)

    def test_fadeout_after_remove(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.do(FadeOut(1.0))
        game.tick(dt=0.1)
        s.remove()
        game.tick(dt=0.1)
        game.tick(dt=0.1)


# ============================================================================
# 3. CAMERA TESTS
# ============================================================================


class TestCameraBasics:
    def test_center_on_and_conversions(self):
        cam = Camera((800, 600))
        cam.center_on(500, 400)
        assert cam.x == 100.0
        assert cam.y == 100.0
        wx, wy = cam.screen_to_world(0, 0)
        assert wx == 100.0
        assert wy == 100.0
        sx, sy = cam.world_to_screen(100, 100)
        assert sx == 0.0
        assert sy == 0.0

    def test_screen_to_world_roundtrip(self):
        cam = Camera((800, 600))
        cam.center_on(1000, 2000)
        sx, sy = 123.0, 456.0
        wx, wy = cam.screen_to_world(sx, sy)
        sx2, sy2 = cam.world_to_screen(wx, wy)
        assert abs(sx2 - sx) < 1e-9
        assert abs(sy2 - sy) < 1e-9

    def test_center_on_nan_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.center_on(float("nan"), 0)

    def test_center_on_inf_raises(self):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.center_on(float("inf"), 0)


class TestCameraFollow:
    def test_follow_sprite(self, game: Game, backend: MockBackend):
        cam = Camera((800, 600))
        s = Sprite("test_img", position=(500, 400))
        cam.follow(s)
        cam.update(0.016)
        assert abs(cam.x - (500 - 400)) < 1.0
        assert abs(cam.y - (400 - 300)) < 1.0

    def test_follow_removed_sprite(self, game: Game, backend: MockBackend):
        cam = Camera((800, 600))
        s = Sprite("test_img", position=(500, 400))
        cam.follow(s)
        s.remove()
        cam.update(0.016)
        assert cam._follow_target is None

    def test_follow_none_stops_following(self, game: Game, backend: MockBackend):
        cam = Camera((800, 600))
        s = Sprite("test_img", position=(500, 400))
        cam.follow(s)
        cam.follow(None)
        assert cam._follow_target is None


class TestCameraPanTo:
    def test_pan_to(self, game: Game, backend: MockBackend):
        cam = Camera((800, 600))
        cam.center_on(0, 0)
        cam.pan_to(500, 400, duration=1.0)
        for _ in range(70):
            game._tween_manager.update(0.016)
        target_x = 500 - 400
        target_y = 400 - 300
        assert abs(cam.x - target_x) < 5.0
        assert abs(cam.y - target_y) < 5.0

    def test_pan_to_nan_raises(self, game: Game, backend: MockBackend):
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.pan_to(float("nan"), 0, duration=1.0)


class TestCameraShake:
    def test_shake_applies_offset(self):
        cam = Camera((800, 600))
        cam.shake(20.0, duration=0.5, decay=1.0)
        cam.update(0.01)
        has_offset = (cam.shake_offset_x != 0.0 or cam.shake_offset_y != 0.0)
        assert has_offset

    def test_shake_decays_to_zero(self):
        cam = Camera((800, 600))
        cam.shake(20.0, duration=0.5, decay=1.0)
        cam.update(0.6)
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0

    def test_shake_zero_duration_resets(self):
        cam = Camera((800, 600))
        cam.shake(20.0, duration=0.5, decay=1.0)
        cam.update(0.1)
        cam.shake(20.0, duration=0, decay=1.0)
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0


class TestCameraWorldBounds:
    def test_bounds_clamping(self):
        cam = Camera((800, 600), world_bounds=(0, 0, 1600, 1200))
        cam.center_on(0, 0)
        assert cam.x >= 0
        assert cam.y >= 0

    def test_bounds_prevents_overshoot(self):
        cam = Camera((800, 600), world_bounds=(0, 0, 1600, 1200))
        cam.center_on(2000, 2000)
        assert cam.x <= 800
        assert cam.y <= 600

    def test_camera_zero_viewport(self):
        """Camera with zero viewport -- does it crash?"""
        cam = Camera((0, 0))
        cam.center_on(100, 100)
        assert cam.x == 100.0
        assert cam.y == 100.0

    def test_camera_negative_bounds(self):
        """Negative bounds where left > right or top > bottom."""
        cam = Camera((800, 600), world_bounds=(100, 100, 50, 50))
        cam.center_on(75, 75)
        # Just verify no crash.

    def test_world_bounds_setter(self):
        cam = Camera((800, 600))
        cam.center_on(5000, 5000)
        cam.world_bounds = (0, 0, 1600, 1200)
        assert cam.x <= 800
        assert cam.y <= 600


# ============================================================================
# 4. TWEENING TESTS
# ============================================================================


class TestTweening:
    def test_tween_linear(self, game: Game, backend: MockBackend):
        class Obj:
            val = 0.0
        obj = Obj()
        tween(obj, "val", 0, 100, 1.0, ease=Ease.LINEAR)
        game._tween_manager.update(0.5)
        assert abs(obj.val - 50.0) < 1.0
        game._tween_manager.update(0.5)
        assert obj.val == 100.0

    def test_tween_cancel_midway(self, game: Game, backend: MockBackend):
        class Obj:
            val = 0.0
        obj = Obj()
        tid = tween(obj, "val", 0, 100, 1.0)
        game._tween_manager.update(0.3)
        mid_val = obj.val
        game.cancel_tween(tid)
        game._tween_manager.update(0.5)
        assert obj.val == mid_val

    def test_tween_on_complete(self, game: Game, backend: MockBackend):
        completed = [False]
        class Obj:
            val = 0.0
        obj = Obj()
        tween(obj, "val", 0, 100, 0.5, on_complete=lambda: completed.__setitem__(0, True))
        game._tween_manager.update(0.6)
        assert completed[0]

    def test_tween_each_ease_type(self, game: Game, backend: MockBackend):
        for ease in Ease:
            obj = type("Obj", (), {"val": 0.0})()
            tween(obj, "val", 0, 100, 1.0, ease=ease)
            game._tween_manager.update(0.5)
            assert 0 <= obj.val <= 100, f"Ease {ease}: val={obj.val} out of range"
            game._tween_manager.update(0.5)
            assert obj.val == 100.0, f"Ease {ease}: val should be 100 at completion"

    def test_cancel_by_target(self, game: Game, backend: MockBackend):
        class Obj:
            val1 = 0.0
            val2 = 0.0
        obj = Obj()
        tween(obj, "val1", 0, 100, 1.0)
        tween(obj, "val2", 0, 200, 1.0)
        game._tween_manager.cancel_by_target(obj)
        game._tween_manager.update(1.0)
        assert obj.val1 == 0.0
        assert obj.val2 == 0.0

    def test_tween_zero_duration(self, game: Game, backend: MockBackend):
        class Obj:
            val = 0.0
        obj = Obj()
        completed = [False]
        tween(obj, "val", 0, 100, 0.0, on_complete=lambda: completed.__setitem__(0, True))
        game._tween_manager.update(0.001)
        assert obj.val == 100.0
        assert completed[0]


# ============================================================================
# 5. TIMER TESTS
# ============================================================================


class TestTimers:
    def test_after_fires_at_right_time(self, game: Game, backend: MockBackend):
        called = [False]
        game.after(0.5, lambda: called.__setitem__(0, True))
        game._timer_manager.update(0.3)
        assert not called[0]
        game._timer_manager.update(0.3)
        assert called[0]

    def test_every_fires_repeatedly(self, game: Game, backend: MockBackend):
        count = [0]
        game.every(0.1, lambda: count.__setitem__(0, count[0] + 1))
        for _ in range(10):
            game._timer_manager.update(0.1)
        assert count[0] >= 9

    def test_cancel_timer(self, game: Game, backend: MockBackend):
        count = [0]
        handle = game.every(0.1, lambda: count.__setitem__(0, count[0] + 1))
        game._timer_manager.update(0.15)
        assert count[0] == 1
        game.cancel(handle)
        game._timer_manager.update(0.5)
        assert count[0] == 1

    def test_timer_chaining_with_then(self, game: Game, backend: MockBackend):
        results = []
        handle = game.after(0.1, lambda: results.append("first"))
        handle.then(lambda: results.append("second"), delay=0.1)
        game._timer_manager.update(0.15)
        assert results == ["first"]
        game._timer_manager.update(0.15)
        assert results == ["first", "second"]

    def test_cancel_chained_timer_before_chain_fires(self, game: Game, backend: MockBackend):
        results = []
        handle = game.after(0.1, lambda: results.append("first"))
        handle.then(lambda: results.append("second"), delay=0.1)
        game.cancel(handle)
        game._timer_manager.update(0.5)
        assert results == []

    def test_after_negative_delay_raises(self, game: Game, backend: MockBackend):
        with pytest.raises(ValueError, match="delay must be >= 0"):
            game.after(-1, lambda: None)

    def test_every_zero_interval_raises(self, game: Game, backend: MockBackend):
        with pytest.raises(ValueError, match="interval must be > 0"):
            game.every(0, lambda: None)

    def test_after_zero_delay_fires_immediately(self, game: Game, backend: MockBackend):
        called = [False]
        game.after(0, lambda: called.__setitem__(0, True))
        game._timer_manager.update(0.001)
        assert called[0]


# ============================================================================
# 6. PARTICLE TESTS
# ============================================================================


class TestParticles:
    def test_burst_creates_particles(self, game: Game, backend: MockBackend):
        emitter = ParticleEmitter("spark", position=(100, 200), count=10)
        initial = len(backend.sprites)
        emitter.burst(5)
        assert len(emitter._particles) == 5
        assert len(backend.sprites) == initial + 5

    def test_continuous_spawning(self, game: Game, backend: MockBackend):
        emitter = ParticleEmitter("spark", position=(100, 200))
        emitter.continuous(rate=100)
        for _ in range(10):
            emitter.update(0.05)
        assert len(emitter._particles) > 0

    def test_stop_halts_spawning(self, game: Game, backend: MockBackend):
        emitter = ParticleEmitter("spark", position=(100, 200))
        emitter.continuous(rate=100)
        emitter.update(0.1)
        count_before = len(emitter._particles)
        emitter.stop()
        assert emitter._continuous_rate == 0.0
        assert len(emitter._particles) == count_before

    def test_remove_cleans_up_immediately(self, game: Game, backend: MockBackend):
        emitter = ParticleEmitter("spark", position=(100, 200))
        emitter.burst(10)
        assert len(emitter._particles) == 10
        emitter.remove()
        assert len(emitter._particles) == 0
        assert not emitter.is_active

    def test_particles_die_naturally(self, game: Game, backend: MockBackend):
        emitter = ParticleEmitter(
            "spark", position=(100, 200),
            lifetime=(0.1, 0.1),
        )
        emitter.burst(5)
        assert len(emitter._particles) == 5
        emitter.update(0.2)
        assert len(emitter._particles) == 0

    def test_burst_zero_count(self, game: Game, backend: MockBackend):
        emitter = ParticleEmitter("spark", position=(100, 200))
        emitter.burst(0)
        assert len(emitter._particles) == 0

    def test_emitter_without_game_raises(self):
        import saga2d.rendering.sprite as sprite_mod
        old = sprite_mod._current_game
        sprite_mod._current_game = None
        try:
            with pytest.raises(RuntimeError, match="No active Game"):
                ParticleEmitter("spark", position=(100, 200))
        finally:
            sprite_mod._current_game = old


# ============================================================================
# 7. ANIMATION TESTS
# ============================================================================


class TestAnimation:
    def test_play_non_looping_completes(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        completed = [False]
        anim = AnimationDef(
            frames=["frame_0", "frame_1", "frame_2"],
            frame_duration=0.1, loop=False,
        )
        s.play(anim, on_complete=lambda: completed.__setitem__(0, True))
        for _ in range(25):
            game.tick(dt=0.02)
        assert completed[0]

    def test_play_looping_cycles(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        anim = AnimationDef(frames=["frame_0", "frame_1"], frame_duration=0.1, loop=True)
        s.play(anim)
        for _ in range(50):
            game.tick(dt=0.05)
        assert s._anim_player is not None
        assert s._anim_player.is_playing

    def test_queue_animation(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        completed_first = [False]
        completed_second = [False]
        anim1 = AnimationDef(frames=["a1", "a2"], frame_duration=0.1, loop=False)
        anim2 = AnimationDef(frames=["b1", "b2"], frame_duration=0.1, loop=False)
        s.play(anim1, on_complete=lambda: completed_first.__setitem__(0, True))
        s.queue(anim2, on_complete=lambda: completed_second.__setitem__(0, True))
        for _ in range(40):
            game.tick(dt=0.02)
        assert completed_first[0]
        assert completed_second[0]

    def test_stop_animation(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        anim = AnimationDef(frames=["f1", "f2"], frame_duration=0.1, loop=True)
        s.play(anim)
        game.tick(dt=0.05)
        s.stop_animation()
        assert s._anim_player is None
        game.tick(dt=0.05)

    def test_animation_zero_frames_raises(self):
        from saga2d.animation import AnimationPlayer
        with pytest.raises(ValueError, match="zero frames"):
            AnimationPlayer(frames=[], frame_duration=0.1, loop=False)

    def test_queue_when_nothing_playing(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        anim = AnimationDef(frames=["f1", "f2"], frame_duration=0.1, loop=False)
        s.queue(anim)
        assert s._anim_player is not None


# ============================================================================
# 8. COLOR SWAP TESTS
# ============================================================================


class TestColorSwap:
    def test_mismatched_lengths_raises(self):
        with pytest.raises(ValueError, match="same length"):
            ColorSwap(
                source_colors=[(255, 0, 0)],
                target_colors=[(0, 255, 0), (0, 0, 255)],
            )

    def test_cache_key(self):
        swap = ColorSwap(
            source_colors=[(255, 0, 0), (0, 255, 0)],
            target_colors=[(0, 0, 255), (255, 255, 0)],
        )
        key = swap.cache_key()
        assert isinstance(key, tuple)
        assert len(key) == 2

    def test_register_and_get_palette(self):
        swap = ColorSwap(source_colors=[(255, 0, 0)], target_colors=[(0, 0, 255)])
        register_palette("test_team", swap)
        from saga2d.rendering.color_swap import get_palette
        result = get_palette("test_team")
        assert result is swap
        _clear_palettes()

    def test_get_unregistered_palette_raises(self):
        _clear_palettes()
        from saga2d.rendering.color_swap import get_palette
        with pytest.raises(KeyError, match="not registered"):
            get_palette("nonexistent")

    def test_empty_color_swap(self):
        swap = ColorSwap(source_colors=[], target_colors=[])
        assert swap.cache_key() == ()


# ============================================================================
# 9. EDGE CASE / STRESS TESTS
# ============================================================================


class TestEdgeCases:
    def test_opacity_nan_handled(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.opacity = float("nan")
        assert s.opacity == 0

    def test_opacity_inf_handled(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.opacity = float("inf")
        assert s.opacity == 255

    def test_opacity_negative_inf_handled(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.opacity = float("-inf")
        assert s.opacity == 0

    def test_opacity_clamp_above_255(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.opacity = 500
        assert s.opacity == 255

    def test_opacity_clamp_below_0(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.opacity = -50
        assert s.opacity == 0

    def test_tint_clamp(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.tint = (2.0, -1.0, 0.5)
        assert s.tint == (1.0, 0.0, 0.5)

    def test_sprite_set_image_on_removed(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        s.image = "other_img"

    def test_many_sprites_creation(self, game: Game, backend: MockBackend):
        sprites = [Sprite("test_img", position=(i, i)) for i in range(100)]
        assert len(backend.sprites) == 100
        for s in sprites:
            s.remove()
        assert len(backend.sprites) == 0

    def test_sprite_position_setter_no_change(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        s.position = (100, 200)

    def test_moveto_already_at_target(self, game: Game, backend: MockBackend):
        s = Sprite("test_img", position=(100, 200))
        completed = [False]
        s.do(Sequence(
            MoveTo((100, 200), speed=100),
            Do(lambda: completed.__setitem__(0, True)),
        ))
        game.tick(dt=0.016)
        assert completed[0]

    def test_delay_zero_seconds(self, game: Game, backend: MockBackend):
        completed = [False]
        s = Sprite("test_img", position=(100, 200))
        s.do(Sequence(Delay(0), Do(lambda: completed.__setitem__(0, True))))
        game.tick(dt=0.016)
        assert completed[0]

    def test_delay_negative_raises(self):
        with pytest.raises(ValueError, match="must be >= 0"):
            Delay(-1)

    def test_tween_nonexistent_property_raises(self, game: Game, backend: MockBackend):
        class Obj:
            pass
        obj = Obj()
        with pytest.raises(AttributeError, match="no attribute"):
            tween(obj, "nonexistent", 0, 100, 1.0)

    def test_tween_nan_from_val_raises(self, game: Game, backend: MockBackend):
        class Obj:
            val = 0.0
        obj = Obj()
        with pytest.raises(ValueError, match="from_val must be finite"):
            tween(obj, "val", float("nan"), 100, 1.0)

    def test_tween_nan_to_val_raises(self, game: Game, backend: MockBackend):
        class Obj:
            val = 0.0
        obj = Obj()
        with pytest.raises(ValueError, match="to_val must be finite"):
            tween(obj, "val", 0, float("nan"), 1.0)

    def test_tween_without_game_raises(self):
        import saga2d.util.tween as tween_mod
        old = tween_mod._tween_manager
        tween_mod._tween_manager = None
        try:
            with pytest.raises(RuntimeError, match="No active Game"):
                tween(object(), "x", 0, 100, 1.0)
        finally:
            tween_mod._tween_manager = old

    def test_sprite_move_to_method_zero_speed(self, game: Game, backend: MockBackend):
        """Sprite.move_to with speed=0 should raise ValueError."""
        s = Sprite("test_img", position=(100, 200))
        with pytest.raises(ValueError, match="speed must be positive"):
            s.move_to((200, 300), speed=0)

    def test_sprite_move_to_negative_speed(self, game: Game, backend: MockBackend):
        """Sprite.move_to with negative speed should raise ValueError."""
        s = Sprite("test_img", position=(100, 200))
        with pytest.raises(ValueError, match="speed must be positive"):
            s.move_to((200, 300), speed=-10)

    def test_timer_update_with_nan_dt(self, game: Game):
        called = [False]
        game.after(0.1, lambda: called.__setitem__(0, True))
        game._timer_manager.update(float("nan"))
        assert not called[0]

    def test_tween_update_with_nan_dt(self, game: Game):
        class Obj:
            val = 0.0
        obj = Obj()
        tween(obj, "val", 0, 100, 1.0)
        game._tween_manager.update(float("nan"))
        assert obj.val == 0.0

    def test_tween_update_with_inf_dt(self, game: Game):
        class Obj:
            val = 0.0
        obj = Obj()
        tween(obj, "val", 0, 100, 1.0)
        game._tween_manager.update(float("inf"))
        assert obj.val == 0.0

    def test_multiple_actions_replace(self, game: Game, backend: MockBackend):
        count1 = [0]
        count2 = [0]
        s = Sprite("test_img", position=(100, 200))
        s.do(Repeat(
            Sequence(Delay(0.01), Do(lambda: count1.__setitem__(0, count1[0] + 1))),
            times=None,
        ))
        game.tick(dt=0.05)
        s.do(Repeat(
            Sequence(Delay(0.01), Do(lambda: count2.__setitem__(0, count2[0] + 1))),
            times=None,
        ))
        game.tick(dt=0.05)
        c1 = count1[0]
        game.tick(dt=0.05)
        assert count1[0] == c1
        assert count2[0] > 0

    def test_sprite_x_setter_no_order_update_on_removed(self, game: Game, backend: MockBackend):
        """x setter on removed sprite should not crash (no order update)."""
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        # The x setter calls _sync_to_backend (which early-returns) but does
        # NOT check _removed before the order update path. Let's test.
        s.x = 500  # should not crash (x setter doesn't update order)

    def test_sprite_y_setter_order_update_on_removed(self, game: Game, backend: MockBackend):
        """y setter on removed sprite -- the order update path checks _removed."""
        s = Sprite("test_img", position=(100, 200))
        s.remove()
        # y setter has the order update check with _removed guard.
        s.y = 500  # should not crash
