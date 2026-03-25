"""Fresh edge-case tests for Rendering (Sprite, Camera, Particles) and UI widgets.

Covers boundary values, error handling, and degenerate inputs that the main
test suite does not exercise.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from saga2d import Do, Game, Scene, Sprite
from saga2d.actions import Action, Sequence
from saga2d.assets import AssetManager
from saga2d.backends.mock_backend import MockBackend
from saga2d.input import InputEvent
from saga2d.rendering.camera import Camera
from saga2d.rendering.layers import RenderLayer, SpriteAnchor
from saga2d.rendering.particles import ParticleEmitter
from saga2d.ui import (
    Button,
    DataTable,
    DragManager,
    Grid,
    Label,
    List,
    Panel,
    ProgressBar,
    Style,
    TabGroup,
    TextBox,
    Theme,
    Tooltip,
)
from saga2d.ui.component import _UIRoot
from saga2d.ui.layout import Layout
from saga2d.ui.widgets import _word_wrap


# ======================================================================
# Fixtures
# ======================================================================


@pytest.fixture
def asset_dir(tmp_path: Path) -> Path:
    """Create a temporary asset directory with test images."""
    images = tmp_path / "images"
    images.mkdir()
    sprites = images / "sprites"
    sprites.mkdir()
    (sprites / "knight.png").write_bytes(b"png")
    (sprites / "spark.png").write_bytes(b"png")
    (sprites / "smoke.png").write_bytes(b"png")
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


@pytest.fixture
def ui_game() -> Game:
    """Game with mock backend for UI testing at 800x600."""
    g = Game("UITest", backend="mock", resolution=(800, 600))
    yield g
    g._teardown()


@pytest.fixture
def ui_root(ui_game: Game) -> _UIRoot:
    """A _UIRoot attached to the UI game."""
    return _UIRoot(ui_game)


# ======================================================================
# 1. SPRITE EDGE CASES
# ======================================================================


class TestSpriteZeroPosition:
    """Test sprite at origin (0, 0)."""

    def test_position_zero_zero(self, game: Game, backend: MockBackend) -> None:
        """Sprite at (0, 0) should be valid and register in backend."""
        sprite = Sprite("sprites/knight", position=(0, 0))
        assert sprite.position == (0.0, 0.0)
        assert sprite.sprite_id in backend.sprites

    def test_set_position_to_zero(self, game: Game) -> None:
        """Moving a sprite back to (0, 0) should work."""
        sprite = Sprite("sprites/knight", position=(100, 200))
        sprite.position = (0, 0)
        assert sprite.position == (0.0, 0.0)


class TestSpriteOpacity:
    """Test opacity boundary values and clamping."""

    def test_opacity_zero_transparent(self, game: Game, backend: MockBackend) -> None:
        """opacity=0 makes sprite fully transparent."""
        sprite = Sprite("sprites/knight", opacity=0)
        assert sprite.opacity == 0
        record = backend.sprites[sprite.sprite_id]
        assert record["opacity"] == 0

    def test_opacity_255_opaque(self, game: Game, backend: MockBackend) -> None:
        """opacity=255 makes sprite fully opaque."""
        sprite = Sprite("sprites/knight", opacity=255)
        assert sprite.opacity == 255

    def test_opacity_above_255_clamps(self, game: Game) -> None:
        """Values above 255 should clamp to 255."""
        sprite = Sprite("sprites/knight")
        sprite.opacity = 300
        assert sprite.opacity == 255

    def test_opacity_below_zero_clamps(self, game: Game) -> None:
        """Negative values should clamp to 0."""
        sprite = Sprite("sprites/knight")
        sprite.opacity = -50
        assert sprite.opacity == 0

    def test_opacity_float_truncated(self, game: Game) -> None:
        """Float opacity is truncated to int after clamping."""
        sprite = Sprite("sprites/knight")
        sprite.opacity = 127.9
        assert sprite.opacity == 127

    def test_opacity_nan_handled(self, game: Game) -> None:
        """NaN opacity should be handled without crashing (clamps to 0)."""
        sprite = Sprite("sprites/knight")
        sprite.opacity = float("nan")
        assert sprite.opacity == 0

    def test_opacity_inf_handled(self, game: Game) -> None:
        """Inf opacity should be handled without crashing (clamps to 255)."""
        sprite = Sprite("sprites/knight")
        sprite.opacity = float("inf")
        assert sprite.opacity == 255

    def test_opacity_neg_inf_handled(self, game: Game) -> None:
        """-Inf opacity should be handled (clamps to 0)."""
        sprite = Sprite("sprites/knight")
        sprite.opacity = float("-inf")
        assert sprite.opacity == 0


class TestSpriteTint:
    """Test tint values and clamping."""

    def test_tint_default_white(self, game: Game) -> None:
        """Default tint is (1.0, 1.0, 1.0) — no tinting."""
        sprite = Sprite("sprites/knight")
        assert sprite.tint == (1.0, 1.0, 1.0)

    def test_tint_above_one_clamps(self, game: Game) -> None:
        """Tint values > 1.0 should clamp to 1.0."""
        sprite = Sprite("sprites/knight")
        sprite.tint = (1.5, 2.0, 3.0)
        assert sprite.tint == (1.0, 1.0, 1.0)

    def test_tint_below_zero_clamps(self, game: Game) -> None:
        """Tint values < 0.0 should clamp to 0.0."""
        sprite = Sprite("sprites/knight")
        sprite.tint = (-0.5, -1.0, -0.1)
        assert sprite.tint == (0.0, 0.0, 0.0)

    def test_tint_mixed_values_clamp(self, game: Game) -> None:
        """Mixed in-range and out-of-range tint values each clamp independently."""
        sprite = Sprite("sprites/knight")
        sprite.tint = (-0.1, 0.5, 1.5)
        assert sprite.tint == (0.0, 0.5, 1.0)

    def test_tint_zero_is_black(self, game: Game) -> None:
        """Tint (0, 0, 0) means completely black tint."""
        sprite = Sprite("sprites/knight")
        sprite.tint = (0.0, 0.0, 0.0)
        assert sprite.tint == (0.0, 0.0, 0.0)


class TestSpriteLargeCoordinates:
    """Test sprite with very large coordinates."""

    def test_large_position(self, game: Game) -> None:
        """Sprite at (1e6, 1e6) should work without errors."""
        sprite = Sprite("sprites/knight", position=(1e6, 1e6))
        assert sprite.x == 1e6
        assert sprite.y == 1e6

    def test_negative_large_position(self, game: Game) -> None:
        """Sprite at (-1e6, -1e6) should work without errors."""
        sprite = Sprite("sprites/knight", position=(-1e6, -1e6))
        assert sprite.x == -1e6
        assert sprite.y == -1e6

    def test_position_nan_raises(self, game: Game) -> None:
        """Sprite with NaN position should raise ValueError."""
        with pytest.raises(ValueError, match="finite"):
            Sprite("sprites/knight", position=(float("nan"), 100))

    def test_position_inf_raises(self, game: Game) -> None:
        """Sprite with Inf position should raise ValueError."""
        with pytest.raises(ValueError, match="finite"):
            Sprite("sprites/knight", position=(float("inf"), 100))

    def test_set_position_nan_raises(self, game: Game) -> None:
        """Setting position to NaN after creation should raise ValueError."""
        sprite = Sprite("sprites/knight")
        with pytest.raises(ValueError, match="finite"):
            sprite.position = (float("nan"), 0)

    def test_set_x_nan_raises(self, game: Game) -> None:
        """Setting x to NaN should raise ValueError."""
        sprite = Sprite("sprites/knight")
        with pytest.raises(ValueError, match="finite"):
            sprite.x = float("nan")

    def test_set_y_inf_raises(self, game: Game) -> None:
        """Setting y to Inf should raise ValueError."""
        sprite = Sprite("sprites/knight")
        with pytest.raises(ValueError, match="finite"):
            sprite.y = float("inf")


class TestSpriteRemoval:
    """Test double removal and operations on removed sprites."""

    def test_remove_twice_idempotent(self, game: Game) -> None:
        """Calling remove() twice should not raise."""
        sprite = Sprite("sprites/knight")
        sprite.remove()
        sprite.remove()  # Second call should be a no-op
        assert sprite.is_removed

    def test_set_position_on_removed_sprite(self, game: Game) -> None:
        """Setting position on removed sprite should not crash."""
        sprite = Sprite("sprites/knight", position=(100, 200))
        sprite.remove()
        # The _sync_to_backend returns early when _removed is True
        # but position setters still update _x/_y before calling _sync
        sprite.position = (500, 600)
        # Sprite internally has the value but backend is not updated

    def test_set_opacity_on_removed_sprite(self, game: Game) -> None:
        """Setting opacity on removed sprite should not crash."""
        sprite = Sprite("sprites/knight")
        sprite.remove()
        sprite.opacity = 128
        # Should not raise — _sync_to_backend returns early

    def test_set_image_on_removed_sprite(self, game: Game) -> None:
        """Setting image on removed sprite is a no-op."""
        sprite = Sprite("sprites/knight")
        old_image = sprite.image
        sprite.remove()
        sprite.image = "sprites/knight"  # Should not crash
        # Image name not changed on removed sprite
        assert sprite.image == old_image

    def test_do_action_on_removed_sprite(self, game: Game) -> None:
        """do() on a removed sprite should be a no-op."""
        sprite = Sprite("sprites/knight")
        sprite.remove()
        called = []
        action = Do(lambda: called.append(True))
        sprite.do(action)
        # Action should not have been started
        assert sprite._current_action is None

    def test_visible_setter_on_removed_sprite(self, game: Game) -> None:
        """Setting visible on removed sprite should not crash."""
        sprite = Sprite("sprites/knight")
        sprite.remove()
        sprite.visible = False  # Should not crash

    def test_tint_on_removed_sprite(self, game: Game) -> None:
        """Setting tint on removed sprite should not crash."""
        sprite = Sprite("sprites/knight")
        sprite.remove()
        sprite.tint = (0.5, 0.5, 0.5)  # Should not crash


class TestSpriteDefaults:
    """Test sprite with all default parameters."""

    def test_default_position_is_origin(self, game: Game) -> None:
        """Default position is (0, 0)."""
        sprite = Sprite("sprites/knight")
        assert sprite.position == (0.0, 0.0)

    def test_default_opacity_is_255(self, game: Game) -> None:
        """Default opacity is 255 (fully opaque)."""
        sprite = Sprite("sprites/knight")
        assert sprite.opacity == 255

    def test_default_visible_is_true(self, game: Game) -> None:
        """Default visible is True."""
        sprite = Sprite("sprites/knight")
        assert sprite.visible is True

    def test_default_layer_is_units(self, game: Game) -> None:
        """Default layer is RenderLayer.UNITS."""
        sprite = Sprite("sprites/knight")
        assert sprite.layer == RenderLayer.UNITS

    def test_default_anchor_is_bottom_center(self, game: Game) -> None:
        """Default anchor is BOTTOM_CENTER."""
        sprite = Sprite("sprites/knight")
        assert sprite.anchor == SpriteAnchor.BOTTOM_CENTER

    def test_default_tint_is_white(self, game: Game) -> None:
        """Default tint is (1.0, 1.0, 1.0)."""
        sprite = Sprite("sprites/knight")
        assert sprite.tint == (1.0, 1.0, 1.0)

    def test_default_is_not_removed(self, game: Game) -> None:
        """Default is_removed is False."""
        sprite = Sprite("sprites/knight")
        assert sprite.is_removed is False


# ======================================================================
# 2. CAMERA EDGE CASES
# ======================================================================


class TestCameraCenterOn:
    """Test center_on with invalid coordinates."""

    def test_center_on_nan_raises(self) -> None:
        """center_on(NaN, 0) should raise ValueError."""
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.center_on(float("nan"), 0)

    def test_center_on_inf_raises(self) -> None:
        """center_on(0, Inf) should raise ValueError."""
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.center_on(0, float("inf"))

    def test_center_on_neg_inf_raises(self) -> None:
        """center_on(-Inf, -Inf) should raise ValueError."""
        cam = Camera((800, 600))
        with pytest.raises(ValueError, match="finite"):
            cam.center_on(float("-inf"), float("-inf"))

    def test_center_on_valid(self) -> None:
        """center_on with finite coords should work."""
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        # Viewport center at (400, 300) means top-left = (0, 0)
        assert cam.x == 0.0
        assert cam.y == 0.0


class TestCameraFollow:
    """Test camera following a sprite that gets removed."""

    def test_follow_removed_sprite_handled(self, game: Game) -> None:
        """Following a removed sprite should stop following gracefully."""
        cam = Camera((1920, 1080))
        sprite = Sprite("sprites/knight", position=(500, 400))
        cam.follow(sprite)

        # First update follows the sprite
        cam.update(0.016)
        assert cam._follow_target is sprite

        # Remove the sprite
        sprite.remove()

        # Next update should detect removal and stop following
        cam.update(0.016)
        assert cam._follow_target is None

    def test_follow_none_stops(self) -> None:
        """follow(None) should stop following."""
        cam = Camera((800, 600))
        cam._follow_target = object()  # fake target
        cam.follow(None)
        assert cam._follow_target is None


class TestCameraPanTo:
    """Test pan_to during active pan."""

    def test_pan_to_nan_raises(self, game: Game) -> None:
        """pan_to with NaN should raise ValueError."""
        cam = Camera((1920, 1080))
        with pytest.raises(ValueError, match="finite"):
            cam.pan_to(float("nan"), 0, 1.0)

    def test_pan_to_inf_raises(self, game: Game) -> None:
        """pan_to with Inf should raise ValueError."""
        cam = Camera((1920, 1080))
        with pytest.raises(ValueError, match="finite"):
            cam.pan_to(0, float("inf"), 1.0)


class TestCameraShake:
    """Test shake with edge-case parameters."""

    def test_shake_duration_zero_resets(self) -> None:
        """shake with duration=0 should reset any active shake."""
        cam = Camera((800, 600))
        # Start a shake
        cam.shake(10.0, 1.0, 1.0)
        cam.update(0.1)  # Build up some shake offset

        # Now reset with duration=0
        cam.shake(10.0, 0.0, 1.0)
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0
        assert cam._shake_duration == 0.0

    def test_shake_negative_duration_resets(self) -> None:
        """shake with negative duration should reset shake (treated as <=0)."""
        cam = Camera((800, 600))
        cam.shake(10.0, 1.0, 1.0)
        cam.update(0.1)

        cam.shake(10.0, -1.0, 1.0)
        assert cam.shake_offset_x == 0.0
        assert cam.shake_offset_y == 0.0

    def test_shake_negative_intensity(self) -> None:
        """shake with negative intensity should work (random.uniform handles it)."""
        cam = Camera((800, 600))
        # Negative intensity: random.uniform(-(-5), -5) = uniform(5, -5)
        # random.uniform handles min > max by just swapping.
        cam.shake(-5.0, 1.0, 1.0)
        cam.update(0.1)
        # Should not crash, offset values will be whatever random produces


class TestCameraEdgeScroll:
    """Test edge scroll when disabled."""

    def test_edge_scroll_disabled_no_movement(self) -> None:
        """When edge scroll is disabled, mouse position has no effect."""
        cam = Camera((800, 600))
        cam.center_on(400, 300)
        old_x, old_y = cam.x, cam.y

        # Mouse near edge but edge scroll not enabled
        cam.update(0.016, mouse_x=0, mouse_y=0)
        assert cam.x == old_x
        assert cam.y == old_y


class TestCameraKeyScroll:
    """Test key scroll with conflicting directions."""

    def test_conflicting_left_right_cancel_out(self) -> None:
        """Pressing left and right simultaneously should cancel horizontal movement."""
        cam = Camera((800, 600))
        cam.enable_key_scroll(speed=300)

        # Press both left and right
        cam.handle_input(InputEvent(type="key_press", action="left"))
        cam.handle_input(InputEvent(type="key_press", action="right"))

        old_x = cam.x
        cam.update(0.1)
        # dx = -speed*dt + speed*dt = 0
        assert cam.x == old_x

    def test_conflicting_up_down_cancel_out(self) -> None:
        """Pressing up and down simultaneously should cancel vertical movement."""
        cam = Camera((800, 600))
        cam.enable_key_scroll(speed=300)

        cam.handle_input(InputEvent(type="key_press", action="up"))
        cam.handle_input(InputEvent(type="key_press", action="down"))

        old_y = cam.y
        cam.update(0.1)
        assert cam.y == old_y

    def test_key_scroll_disabled_ignores(self) -> None:
        """When key scroll is disabled, key events return False."""
        cam = Camera((800, 600))
        # Key scroll NOT enabled
        result = cam.handle_input(InputEvent(type="key_press", action="left"))
        assert result is False


class TestCameraCoordinateConversion:
    """Test screen_to_world / world_to_screen roundtrip."""

    def test_roundtrip_identity_at_origin(self) -> None:
        """At default position, roundtrip should preserve coordinates."""
        cam = Camera((800, 600))
        # Camera at (0, 0), no shake
        wx, wy = cam.screen_to_world(100, 200)
        sx, sy = cam.world_to_screen(wx, wy)
        assert abs(sx - 100) < 1e-9
        assert abs(sy - 200) < 1e-9

    def test_roundtrip_after_scroll(self) -> None:
        """After scrolling, roundtrip should still preserve coordinates."""
        cam = Camera((800, 600))
        cam.scroll(500, 300)

        sx, sy = 100.0, 200.0
        wx, wy = cam.screen_to_world(sx, sy)
        sx2, sy2 = cam.world_to_screen(wx, wy)
        assert abs(sx2 - sx) < 1e-9
        assert abs(sy2 - sy) < 1e-9

    def test_roundtrip_after_center_on(self) -> None:
        """After center_on, roundtrip should preserve coordinates."""
        cam = Camera((800, 600))
        cam.center_on(1000, 2000)

        wx, wy = cam.screen_to_world(400, 300)
        # Should be at (1000, 2000) since we centered there and screen center is (400,300)
        assert abs(wx - 1000) < 1e-9
        assert abs(wy - 2000) < 1e-9


class TestCameraWorldBounds:
    """Test camera with world_bounds smaller than viewport."""

    def test_bounds_smaller_than_viewport(self) -> None:
        """When world is smaller than viewport, camera clamps so bounds are respected."""
        cam = Camera((800, 600), world_bounds=(0, 0, 400, 300))
        cam.center_on(200, 150)
        # max_x = 400 - 800 = -400, max_y = 300 - 600 = -300
        # x = max(0, min(200 - 400, -400)) = max(0, -400) = 0
        # y = max(0, min(150 - 300, -300)) = max(0, -300) = 0
        assert cam.x == 0.0
        assert cam.y == 0.0

    def test_bounds_exactly_viewport_size(self) -> None:
        """World bounds equal to viewport size: camera locked at (0,0)."""
        cam = Camera((800, 600), world_bounds=(0, 0, 800, 600))
        cam.scroll(100, 100)
        # After clamp: max_x = 0, max_y = 0
        assert cam.x == 0.0
        assert cam.y == 0.0


# ======================================================================
# 3. PARTICLE EDGE CASES
# ======================================================================


class TestParticleBurst:
    """Test burst with edge-case counts."""

    def test_burst_count_zero(self, game: Game) -> None:
        """burst(0) should spawn no particles."""
        emitter = ParticleEmitter("sprites/spark", position=(100, 100))
        emitter.burst(0)
        assert len(emitter._particles) == 0

    def test_burst_count_negative(self, game: Game) -> None:
        """burst(-5) should spawn no particles (count <= 0 returns early)."""
        emitter = ParticleEmitter("sprites/spark", position=(100, 100))
        emitter.burst(-5)
        assert len(emitter._particles) == 0


class TestParticleContinuous:
    """Test continuous with edge-case rates."""

    def test_continuous_rate_zero(self, game: Game) -> None:
        """continuous(rate=0) should not spawn anything on update."""
        emitter = ParticleEmitter("sprites/spark", position=(100, 100))
        emitter.continuous(rate=0)
        emitter.update(1.0)  # Even after 1 second, rate=0 means 0 particles
        assert len(emitter._particles) == 0

    def test_continuous_then_stop(self, game: Game) -> None:
        """After stop(), no new particles should spawn."""
        emitter = ParticleEmitter("sprites/spark", position=(100, 100))
        emitter.continuous(rate=100)
        emitter.update(0.1)  # Should spawn ~10 particles
        count_before = len(emitter._particles)
        assert count_before > 0

        emitter.stop()
        emitter.update(0.1)
        # No new particles, but existing ones should have been updated
        assert len(emitter._particles) <= count_before


class TestParticleLifetime:
    """Test emitter with zero lifetime."""

    def test_zero_lifetime_particles_die_immediately(self, game: Game) -> None:
        """Particles with lifetime (0, 0) should die on first update."""
        emitter = ParticleEmitter(
            "sprites/spark",
            position=(100, 100),
            lifetime=(0.0001, 0.0001),  # Very short lifetime
        )
        emitter.burst(5)
        assert len(emitter._particles) == 5

        # After update with enough dt, all particles should die
        emitter.update(1.0)
        assert len(emitter._particles) == 0


class TestParticleRemoveDuringBurst:
    """Test removing emitter during burst."""

    def test_remove_clears_particles(self, game: Game) -> None:
        """remove() should kill all particles immediately."""
        emitter = ParticleEmitter("sprites/spark", position=(100, 100))
        emitter.burst(10)
        assert len(emitter._particles) == 10

        emitter.remove()
        assert len(emitter._particles) == 0
        assert not emitter.is_active


class TestParticlePositionUpdate:
    """Test emitter position update during active particles."""

    def test_position_update(self, game: Game) -> None:
        """Changing emitter position affects new particles, not existing ones."""
        emitter = ParticleEmitter("sprites/spark", position=(100, 100))
        emitter.burst(3)
        old_positions = [
            (p.sprite.x, p.sprite.y) for p in emitter._particles
        ]

        # Move the emitter
        emitter.position = (500, 500)
        assert emitter.position == (500.0, 500.0)

        # Existing particles should not have moved (they move on update via velocity)
        for i, p in enumerate(emitter._particles):
            assert (p.sprite.x, p.sprite.y) == old_positions[i]


# ======================================================================
# 4. UI WIDGET EDGE CASES
# ======================================================================


class TestPanelEdgeCases:
    """Test Panel with degenerate inputs."""

    def test_panel_no_children(self) -> None:
        """Panel with no children should have a default size."""
        panel = Panel()
        w, h = panel.get_preferred_size()
        assert w > 0
        assert h > 0

    def test_panel_negative_spacing_raises(self) -> None:
        """Panel with negative spacing should raise ValueError."""
        with pytest.raises(ValueError, match="negative"):
            Panel(spacing=-1)

    def test_panel_spacing_none_defaults_zero(self) -> None:
        """Panel with spacing=None should default to 0."""
        panel = Panel(spacing=None)
        assert panel.spacing == 0

    def test_panel_vertical_no_children(self) -> None:
        """Vertical panel with no children has a valid preferred size."""
        panel = Panel(layout=Layout.VERTICAL)
        w, h = panel.get_preferred_size()
        assert w >= 0
        assert h >= 0


class TestButtonEdgeCases:
    """Test Button with edge-case inputs."""

    def test_button_click_outside_bounds(self) -> None:
        """Click outside button bounds should not trigger callback."""
        clicked = []
        btn = Button("Test", on_click=lambda: clicked.append(True))
        # Simulate layout (button needs computed bounds for hit testing)
        btn.compute_layout(100, 100, 200, 50)

        # Click outside bounds
        event = InputEvent(type="click", x=50, y=50, button="left")
        result = btn.on_event(event)
        assert result is False
        assert len(clicked) == 0

    def test_button_click_inside_bounds(self) -> None:
        """Click inside button bounds should trigger callback."""
        clicked = []
        btn = Button("Test", on_click=lambda: clicked.append(True))
        btn.compute_layout(100, 100, 200, 50)

        event = InputEvent(type="click", x=150, y=125, button="left")
        result = btn.on_event(event)
        assert result is True
        assert len(clicked) == 1

    def test_button_empty_text(self) -> None:
        """Button with empty text should work without error."""
        btn = Button("")
        w, h = btn.get_preferred_size()
        assert w >= 0
        assert h >= 0

    def test_button_right_click_ignored(self) -> None:
        """Right-click on button should not trigger callback."""
        clicked = []
        btn = Button("Test", on_click=lambda: clicked.append(True))
        btn.compute_layout(100, 100, 200, 50)

        event = InputEvent(type="click", x=150, y=125, button="right")
        result = btn.on_event(event)
        assert result is False
        assert len(clicked) == 0


class TestLabelEdgeCases:
    """Test Label with edge-case text values."""

    def test_label_empty_text(self) -> None:
        """Label with empty text should be valid."""
        label = Label("")
        assert label.text == ""
        w, h = label.get_preferred_size()
        assert w == 0  # No characters, estimated width is 0
        assert h > 0  # Still has line height

    def test_label_none_text(self) -> None:
        """Label with None text should convert to empty string."""
        label = Label(None)
        assert label.text == ""

    def test_label_very_long_text(self) -> None:
        """Label with 1000+ chars should have a valid preferred size."""
        long_text = "A" * 1000
        label = Label(long_text)
        w, h = label.get_preferred_size()
        assert w > 0
        assert h > 0

    def test_label_set_text_to_none(self) -> None:
        """Setting label text to None should convert to empty string."""
        label = Label("hello")
        label.text = None
        assert label.text == ""


class TestListEdgeCases:
    """Test List with edge-case inputs."""

    def test_list_empty_items(self) -> None:
        """List with empty items list should work."""
        lst = List(items=[])
        assert lst.items == []
        assert lst.selected_index is None

    def test_list_none_items(self) -> None:
        """List with items=None should default to empty list."""
        lst = List(items=None)
        assert lst.items == []

    def test_list_selection_out_of_bounds_clamps(self) -> None:
        """Setting selected_index beyond item count should clamp."""
        lst = List(items=["a", "b", "c"])
        lst.selected_index = 100
        assert lst.selected_index == 2  # Clamped to last index

    def test_list_selection_negative_clamps(self) -> None:
        """Setting selected_index to negative value should clamp to 0."""
        lst = List(items=["a", "b", "c"])
        lst.selected_index = -5
        assert lst.selected_index == 0

    def test_list_selection_on_empty_is_none(self) -> None:
        """Setting selected_index on empty list should result in None."""
        lst = List(items=[])
        lst.selected_index = 0
        assert lst.selected_index is None

    def test_list_items_update_clamps_selection(self) -> None:
        """Reducing items should clamp an out-of-bounds selection."""
        lst = List(items=["a", "b", "c", "d"])
        lst.selected_index = 3  # Last item
        lst.items = ["x"]  # Now only 1 item
        assert lst.selected_index == 0  # Clamped


class TestGridEdgeCases:
    """Test Grid with edge-case parameters."""

    def test_grid_zero_columns(self) -> None:
        """Grid with 0 columns should be valid (just empty)."""
        grid = Grid(0, 3)
        assert grid.columns == 0
        assert grid.rows == 3

    def test_grid_zero_rows(self) -> None:
        """Grid with 0 rows should be valid (just empty)."""
        grid = Grid(3, 0)
        assert grid.columns == 3
        assert grid.rows == 0

    def test_grid_negative_spacing_raises(self) -> None:
        """Grid with negative spacing should raise ValueError."""
        with pytest.raises(ValueError, match="negative"):
            Grid(3, 3, spacing=-1)

    def test_grid_selection_on_zero_dims_is_none(self) -> None:
        """Setting selection on grid with 0 columns should result in None."""
        grid = Grid(0, 0)
        grid.selected = (0, 0)
        assert grid.selected is None

    def test_grid_selection_clamps(self) -> None:
        """Setting selection beyond grid dimensions should clamp."""
        grid = Grid(3, 3)
        grid.selected = (10, 10)
        assert grid.selected == (2, 2)

    def test_grid_selection_negative_clamps(self) -> None:
        """Setting negative selection should clamp to (0, 0)."""
        grid = Grid(3, 3)
        grid.selected = (-1, -1)
        assert grid.selected == (0, 0)


class TestDataTableEdgeCases:
    """Test DataTable with edge-case inputs."""

    def test_datatable_no_rows(self) -> None:
        """DataTable with no rows should be valid."""
        dt = DataTable(columns=["Name", "Score"])
        assert dt.rows == []
        assert dt.selected_row is None

    def test_datatable_empty_columns(self) -> None:
        """DataTable with empty columns list should work."""
        dt = DataTable(columns=[])
        assert dt.columns == []

    def test_datatable_mismatched_column_count(self) -> None:
        """DataTable with rows having fewer cells than columns should work.

        The on_draw method handles this via: cell_text = row_data[ci] if ci < len(row_data) else ""
        """
        dt = DataTable(
            columns=["Name", "Score", "Level"],
            rows=[["Alice"]],  # Only 1 cell, columns expect 3
        )
        assert len(dt.rows) == 1
        assert len(dt.rows[0]) == 1  # Row has fewer cells than columns

    def test_datatable_selection_on_empty_is_none(self) -> None:
        """Setting selected_row on empty table should result in None."""
        dt = DataTable(columns=["A", "B"])
        dt.selected_row = 0
        assert dt.selected_row is None

    def test_datatable_selection_clamps(self) -> None:
        """Setting selected_row beyond row count should clamp."""
        dt = DataTable(columns=["A"], rows=[["1"], ["2"], ["3"]])
        dt.selected_row = 100
        assert dt.selected_row == 2

    def test_datatable_clear_rows(self) -> None:
        """clear_rows() should empty the table and reset selection."""
        dt = DataTable(columns=["A"], rows=[["1"], ["2"]])
        dt.selected_row = 1
        dt.clear_rows()
        assert dt.rows == []
        assert dt.selected_row is None


class TestProgressBarEdgeCases:
    """Test ProgressBar with edge-case values."""

    def test_value_exceeds_max(self) -> None:
        """value > max_value should clamp fraction to 1.0."""
        bar = ProgressBar(value=150, max_value=100)
        assert bar.fraction == 1.0

    def test_max_value_zero(self) -> None:
        """max_value=0 should result in fraction=0.0 (guard against division by zero)."""
        bar = ProgressBar(value=50, max_value=0)
        assert bar.fraction == 0.0

    def test_negative_value(self) -> None:
        """Negative value should clamp fraction to 0.0."""
        bar = ProgressBar(value=-10, max_value=100)
        assert bar.fraction == 0.0

    def test_value_equals_max(self) -> None:
        """value == max_value should give fraction=1.0."""
        bar = ProgressBar(value=100, max_value=100)
        assert bar.fraction == 1.0

    def test_value_zero(self) -> None:
        """value=0 should give fraction=0.0."""
        bar = ProgressBar(value=0, max_value=100)
        assert bar.fraction == 0.0

    def test_value_setter(self) -> None:
        """value setter should update the internal value."""
        bar = ProgressBar(value=0, max_value=100)
        bar.value = 75
        assert bar.value == 75
        assert bar.fraction == 0.75


class TestTextBoxEdgeCases:
    """Test TextBox with edge-case text values."""

    def test_empty_text(self) -> None:
        """TextBox with empty text should be valid."""
        tb = TextBox("")
        assert tb.text == ""
        assert tb.is_complete

    def test_very_long_text(self) -> None:
        """TextBox with 1000+ chars should work."""
        long_text = "word " * 200  # 1000 chars
        tb = TextBox(long_text, width=300)
        w, h = tb.get_preferred_size()
        assert w == 300
        assert h > 0

    def test_typewriter_empty_text(self) -> None:
        """TextBox with typewriter speed but empty text is immediately complete."""
        tb = TextBox("", typewriter_speed=10)
        assert tb.is_complete  # No characters to reveal

    def test_text_setter_resets_typewriter(self) -> None:
        """Changing text should reset typewriter progress."""
        tb = TextBox("hello", typewriter_speed=10)
        tb.update(1.0)  # Reveal some chars
        assert tb.revealed_count > 0
        tb.text = "new text"
        assert tb.revealed_count == 0

    def test_skip_reveals_all(self) -> None:
        """skip() should reveal all characters immediately."""
        tb = TextBox("hello world", typewriter_speed=1)
        tb.skip()
        assert tb.is_complete
        assert tb.revealed_count == len("hello world")


class TestWordWrap:
    """Test _word_wrap helper with edge cases."""

    def test_empty_text(self) -> None:
        """Empty text wraps to a single empty-string line (one paragraph)."""
        result = _word_wrap("", 200, 16)
        # "".split("\n") == [""], which produces one paragraph with one empty line.
        # This is correct: even empty text occupies one logical line.
        assert result == [""]

    def test_single_word_wider_than_max(self) -> None:
        """A single word wider than max_width gets its own line."""
        result = _word_wrap("superlongword", 10, 16)
        assert len(result) == 1
        assert result[0] == "superlongword"

    def test_max_width_zero(self) -> None:
        """max_width=0 returns the text as-is in a single element."""
        result = _word_wrap("hello world", 0, 16)
        assert result == ["hello world"]

    def test_newlines_preserved(self) -> None:
        """Explicit newlines should be respected."""
        result = _word_wrap("line1\nline2\nline3", 1000, 16)
        assert len(result) == 3
        assert result[0] == "line1"
        assert result[1] == "line2"
        assert result[2] == "line3"


class TestTooltipEdgeCases:
    """Test Tooltip with edge-case delay values."""

    def test_negative_delay_raises(self) -> None:
        """Tooltip with negative delay now raises ValueError (F51 fix)."""
        with pytest.raises(ValueError, match="delay must be >= 0"):
            Tooltip("info", delay=-1.0)

    def test_zero_delay_shows_immediately(self) -> None:
        """Tooltip with delay=0 should show immediately."""
        tip = Tooltip("info", delay=0)
        tip.show(100, 200)
        assert tip._visible_now is True

    def test_hide_resets_state(self) -> None:
        """hide() should reset all timer state."""
        tip = Tooltip("info", delay=0.5)
        tip.show(100, 200)
        tip.update(0.6)  # Delay elapsed
        assert tip._visible_now is True

        tip.hide()
        assert tip._visible_now is False
        assert tip._showing is False
        assert tip._timer == 0.0


class TestTabGroupEdgeCases:
    """Test TabGroup with invalid tab selection."""

    def test_select_nonexistent_tab_raises(self) -> None:
        """Selecting a tab that doesn't exist should raise KeyError."""
        tg = TabGroup(tabs={"Tab1": Label("content1")})
        with pytest.raises(KeyError, match="nonexistent"):
            tg.select_tab("nonexistent")

    def test_empty_tabgroup(self) -> None:
        """TabGroup with no tabs should have active_tab=None."""
        tg = TabGroup()
        assert tg.active_tab is None
        assert tg.tab_labels == []

    def test_add_first_tab_activates(self) -> None:
        """Adding the first tab should make it active."""
        tg = TabGroup()
        label = Label("content")
        tg.add_tab("First", label)
        assert tg.active_tab == "First"

    def test_active_tab_setter_raises_on_missing(self) -> None:
        """Setting active_tab to missing label raises KeyError."""
        tg = TabGroup(tabs={"A": Label("a"), "B": Label("b")})
        with pytest.raises(KeyError):
            tg.active_tab = "missing"


class TestDragManagerEdgeCases:
    """Test DragManager with no drop targets."""

    def test_drag_manager_no_active_drag(self, ui_game: Game) -> None:
        """DragManager with no active drag should not consume events."""
        root = _UIRoot(ui_game)
        dm = DragManager(root)
        assert dm.is_dragging is False
        assert dm.drag_data is None

        event = InputEvent(type="move", x=100, y=100)
        consumed = dm.handle_event(event)
        assert consumed is False

    def test_cancel_when_no_drag(self, ui_game: Game) -> None:
        """cancel_active() when no drag in progress should be a no-op."""
        root = _UIRoot(ui_game)
        dm = DragManager(root)
        dm.cancel_active()  # Should not raise
        assert dm.is_dragging is False


# ======================================================================
# 5. THEME & STYLE
# ======================================================================


class TestStyleAllNone:
    """Test Style with all None values (inherit everything)."""

    def test_style_all_none(self) -> None:
        """Style() with all defaults should have all fields as None."""
        s = Style()
        assert s.font is None
        assert s.font_size is None
        assert s.text_color is None
        assert s.background_color is None
        assert s.padding is None
        assert s.border_color is None
        assert s.border_width is None
        assert s.hover_color is None
        assert s.press_color is None


class TestThemeResolve:
    """Test Theme resolve methods for each component type."""

    def test_resolve_label_with_none_style(self) -> None:
        """resolve_label_style(None) should use theme defaults."""
        theme = Theme()
        resolved = theme.resolve_label_style(None)
        assert resolved.font == "serif"
        assert resolved.font_size == 24
        assert resolved.text_color == (248, 250, 252, 255)
        # Labels have transparent background
        assert resolved.background_color == (0, 0, 0, 0)

    def test_resolve_button_with_none_style(self) -> None:
        """resolve_button_style(None, 'normal') should use theme defaults."""
        theme = Theme()
        resolved = theme.resolve_button_style(None, "normal")
        assert resolved.font == "serif"
        assert resolved.font_size == 24
        assert resolved.background_color == (51, 65, 85, 255)

    def test_resolve_button_hovered(self) -> None:
        """resolve_button_style in hovered state uses hover color."""
        theme = Theme()
        resolved = theme.resolve_button_style(None, "hovered")
        assert resolved.background_color == (71, 85, 105, 255)

    def test_resolve_button_pressed(self) -> None:
        """resolve_button_style in pressed state uses press color."""
        theme = Theme()
        resolved = theme.resolve_button_style(None, "pressed")
        assert resolved.background_color == (56, 189, 248, 255)

    def test_resolve_button_disabled(self) -> None:
        """resolve_button_style in disabled state uses disabled color."""
        theme = Theme()
        resolved = theme.resolve_button_style(None, "disabled")
        assert resolved.background_color == (30, 41, 59, 255)
        assert resolved.text_color == (100, 116, 139, 200)

    def test_resolve_panel_with_none_style(self) -> None:
        """resolve_panel_style(None) should use theme defaults."""
        theme = Theme()
        resolved = theme.resolve_panel_style(None)
        assert resolved.padding == 16
        assert resolved.border_width == 2
        assert resolved.background_color == (30, 41, 59, 255)

    def test_resolve_list_with_none_style(self) -> None:
        """resolve_list_style(None) should use theme defaults."""
        theme = Theme()
        resolved = theme.resolve_list_style(None)
        assert resolved.padding == 4
        assert resolved.background_color == (30, 41, 59, 255)

    def test_resolve_grid_with_none_style(self) -> None:
        """resolve_grid_style(None) should use theme defaults."""
        theme = Theme()
        resolved = theme.resolve_grid_style(None)
        assert resolved.padding == 4

    def test_resolve_tooltip_with_none_style(self) -> None:
        """resolve_tooltip_style(None) should use theme defaults."""
        theme = Theme()
        resolved = theme.resolve_tooltip_style(None)
        assert resolved.font_size == 18
        assert resolved.padding == 6
        assert resolved.background_color == (15, 23, 42, 240)

    def test_resolve_tabgroup_with_none_style(self) -> None:
        """resolve_tabgroup_style(None) should use theme defaults."""
        theme = Theme()
        resolved = theme.resolve_tabgroup_style(None)
        assert resolved.font_size == 20
        assert resolved.padding == 10

    def test_resolve_datatable_with_none_style(self) -> None:
        """resolve_datatable_style(None) should use theme defaults."""
        theme = Theme()
        resolved = theme.resolve_datatable_style(None)
        assert resolved.padding == 6

    def test_style_overrides_theme(self) -> None:
        """Explicit Style values should override theme defaults."""
        theme = Theme()
        custom_style = Style(font_size=42, padding=20)
        resolved = theme.resolve_label_style(custom_style)
        assert resolved.font_size == 42
        assert resolved.padding == 20
        # Non-overridden fields still use theme defaults
        assert resolved.font == "serif"

    def test_theme_properties(self) -> None:
        """Theme should expose all its properties."""
        theme = Theme()
        # ProgressBar
        assert theme.progressbar_color == (56, 189, 248, 255)
        assert theme.progressbar_bg_color == (15, 23, 42, 220)
        # Selection
        assert theme.selected_color == (56, 189, 248, 80)
        # Grid
        assert theme.grid_cell_bg_color == (40, 48, 68, 180)
        # Tab
        assert theme.tab_active_color == (51, 65, 85, 255)
        assert theme.tab_inactive_color == (30, 41, 59, 220)
        # DataTable
        assert theme.datatable_header_bg_color == (51, 65, 85, 255)
        assert theme.datatable_row_bg_color == (30, 41, 59, 180)
        assert theme.datatable_alt_row_bg_color == (15, 23, 42, 180)
        # Drag-drop
        assert theme.drop_accept_color == (0, 180, 0, 80)
        assert theme.drop_reject_color == (180, 0, 0, 80)
        assert theme.ghost_opacity == 0.5
        # Panel shadow
        assert theme.panel_shadow_offset == 4
        assert theme.panel_shadow_color == (0, 0, 0, 120)
        # Button
        assert theme.button_min_width == 200
        assert theme.button_hover_outline_width == 3
