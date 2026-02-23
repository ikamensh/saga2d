"""Camera — pure-math viewport into a scrolling world.

The :class:`Camera` translates between world coordinates and screen (logical)
coordinates.  It supports centering, following a sprite, edge-scroll, manual
scroll, world-bounds clamping, and smooth ``pan_to()`` via the tween system.

**No backend dependency.** The camera is pure math — it produces an offset
that the rendering layer applies before sending positions to the backend.

Coordinate convention (y-down, top-left origin):

    screen_to_world(sx, sy) = (sx + camera.x, sy + camera.y)
    world_to_screen(wx, wy) = (wx - camera.x, wy - camera.y)

where ``camera.x``, ``camera.y`` is the top-left corner of the viewport in
world space.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from easygame.rendering.sprite import Sprite


class Camera:
    """A 2D camera that maps a viewport onto a larger world.

    Parameters:
        viewport_size: ``(width, height)`` of the logical screen.
        world_bounds:  Optional ``(left, top, right, bottom)`` rectangle that
                       the camera is clamped inside.  ``None`` means no limits.
    """

    def __init__(
        self,
        viewport_size: tuple[int, int],
        *,
        world_bounds: tuple[float, float, float, float] | None = None,
    ) -> None:
        self._vw: int = viewport_size[0]
        self._vh: int = viewport_size[1]

        # Top-left corner of the viewport in world space.
        self._x: float = 0.0
        self._y: float = 0.0

        # Optional world-bounds clamping: (left, top, right, bottom).
        self._world_bounds = world_bounds

        # Follow mode.
        self._follow_target: Sprite | None = None

        # Edge scroll.
        self._edge_scroll_enabled: bool = False
        self._edge_margin: int = 0
        self._edge_speed: float = 0.0

        # Pan-to tween ids (so we can cancel on follow / center_on / scroll).
        self._pan_tween_x: int | None = None
        self._pan_tween_y: int | None = None

    # ------------------------------------------------------------------
    # Read-only properties
    # ------------------------------------------------------------------

    @property
    def x(self) -> float:
        """Top-left x of the viewport in world space (read-only)."""
        return self._x

    @property
    def y(self) -> float:
        """Top-left y of the viewport in world space (read-only)."""
        return self._y

    @property
    def viewport_width(self) -> int:
        return self._vw

    @property
    def viewport_height(self) -> int:
        return self._vh

    @property
    def world_bounds(self) -> tuple[float, float, float, float] | None:
        return self._world_bounds

    @world_bounds.setter
    def world_bounds(
        self, value: tuple[float, float, float, float] | None,
    ) -> None:
        self._world_bounds = value
        self._clamp()

    # ------------------------------------------------------------------
    # Positioning
    # ------------------------------------------------------------------

    def center_on(self, x: float, y: float) -> None:
        """Center the viewport on world position ``(x, y)``.

        Cancels any active pan and disables follow.
        """
        self._cancel_pan()
        self._follow_target = None
        self._x = x - self._vw / 2
        self._y = y - self._vh / 2
        self._clamp()

    def follow(self, sprite: Sprite | None) -> None:
        """Follow *sprite* each frame (center on its position).

        Cancels any active pan.  Pass ``None`` to stop following.
        """
        self._cancel_pan()
        self._follow_target = sprite

    def scroll(self, dx: float, dy: float) -> None:
        """Manually scroll the camera by ``(dx, dy)`` pixels.

        Cancels any active pan and disables follow.
        """
        self._cancel_pan()
        self._follow_target = None
        self._x += dx
        self._y += dy
        self._clamp()

    # ------------------------------------------------------------------
    # Edge scroll
    # ------------------------------------------------------------------

    def enable_edge_scroll(self, margin: int, speed: float) -> None:
        """Enable edge scrolling.

        When the mouse is within *margin* pixels of the viewport edge,
        the camera scrolls at *speed* pixels per second toward that edge.
        """
        self._edge_scroll_enabled = True
        self._edge_margin = margin
        self._edge_speed = speed

    def disable_edge_scroll(self) -> None:
        """Disable edge scrolling."""
        self._edge_scroll_enabled = False

    # ------------------------------------------------------------------
    # Coordinate conversion
    # ------------------------------------------------------------------

    def screen_to_world(
        self, sx: float, sy: float,
    ) -> tuple[float, float]:
        """Convert screen (logical) coordinates to world coordinates."""
        return (sx + self._x, sy + self._y)

    def world_to_screen(
        self, wx: float, wy: float,
    ) -> tuple[float, float]:
        """Convert world coordinates to screen (logical) coordinates."""
        return (wx - self._x, wy - self._y)

    # ------------------------------------------------------------------
    # Smooth pan
    # ------------------------------------------------------------------

    def pan_to(
        self,
        x: float,
        y: float,
        duration: float,
        easing: Any = None,
    ) -> None:
        """Smoothly pan the viewport center to ``(x, y)`` over *duration* seconds.

        Uses the existing tween system.  Disables follow.  If a pan is already
        active it is cancelled first.

        Parameters:
            x:        Target world x to center on.
            y:        Target world y to center on.
            duration: Seconds for the pan animation.
            easing:   An :class:`~easygame.util.tween.Ease` value (default
                      ``Ease.EASE_IN_OUT``).
        """
        from easygame.util.tween import Ease, tween

        self._cancel_pan()
        self._follow_target = None

        if easing is None:
            easing = Ease.EASE_IN_OUT

        # Target top-left so that (x, y) is centered.
        target_x = x - self._vw / 2
        target_y = y - self._vh / 2

        # Clamp target the same way _clamp() would.
        if self._world_bounds is not None:
            left, top, right, bottom = self._world_bounds
            target_x = max(left, min(target_x, right - self._vw))
            target_y = max(top, min(target_y, bottom - self._vh))

        self._pan_tween_x = tween(
            self, "_x", self._x, target_x, duration,
            ease=easing,
        )
        self._pan_tween_y = tween(
            self, "_y", self._y, target_y, duration,
            ease=easing,
            on_complete=self._on_pan_complete,
        )

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(
        self,
        dt: float,
        mouse_x: float | None = None,
        mouse_y: float | None = None,
    ) -> None:
        """Advance per-frame camera logic.

        Called once per frame by :meth:`Game.tick` before the render-sync pass.

        Handles:
        1. Follow tracking — center on the followed sprite.
        2. Edge scroll — scroll when the mouse is near a viewport edge.

        Parameters:
            dt:      Delta time in seconds.
            mouse_x: Current mouse x in logical screen coordinates (or ``None``).
            mouse_y: Current mouse y in logical screen coordinates (or ``None``).
        """
        # 1. Follow tracking.
        if self._follow_target is not None:
            target = self._follow_target
            # Guard against removed sprites.
            if hasattr(target, "is_removed") and target.is_removed:
                self._follow_target = None
            else:
                self._x = target.x - self._vw / 2
                self._y = target.y - self._vh / 2
                self._clamp()

        # 2. Edge scroll.
        if (
            self._edge_scroll_enabled
            and mouse_x is not None
            and mouse_y is not None
        ):
            scroll_dx = 0.0
            scroll_dy = 0.0
            margin = self._edge_margin
            speed = self._edge_speed

            if mouse_x < margin:
                scroll_dx = -speed * dt
            elif mouse_x > self._vw - margin:
                scroll_dx = speed * dt

            if mouse_y < margin:
                scroll_dy = -speed * dt
            elif mouse_y > self._vh - margin:
                scroll_dy = speed * dt

            if scroll_dx != 0.0 or scroll_dy != 0.0:
                self._x += scroll_dx
                self._y += scroll_dy
                self._clamp()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _clamp(self) -> None:
        """Clamp ``(_x, _y)`` so the viewport stays inside world_bounds."""
        if self._world_bounds is None:
            return
        left, top, right, bottom = self._world_bounds
        # Maximum top-left so bottom-right of viewport doesn't exceed bounds.
        max_x = right - self._vw
        max_y = bottom - self._vh
        self._x = max(left, min(self._x, max_x))
        self._y = max(top, min(self._y, max_y))

    def _cancel_pan(self) -> None:
        """Cancel any active pan tweens."""
        from easygame.util import tween as tween_mod

        mgr = tween_mod._tween_manager
        if mgr is not None:
            if self._pan_tween_x is not None:
                mgr.cancel(self._pan_tween_x)
                self._pan_tween_x = None
            if self._pan_tween_y is not None:
                mgr.cancel(self._pan_tween_y)
                self._pan_tween_y = None
        else:
            # No tween manager yet (during tests or before Game init) — just clear ids.
            self._pan_tween_x = None
            self._pan_tween_y = None

    def _on_pan_complete(self) -> None:
        """Called when a pan_to animation finishes."""
        self._pan_tween_x = None
        self._pan_tween_y = None
        self._clamp()
