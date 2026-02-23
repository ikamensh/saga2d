"""Backend protocol, event types, and opaque handle type aliases.

This module defines the interface that all backends must satisfy (via structural
subtyping / Protocol), the event dataclasses dispatched through the framework,
and opaque handle types that the framework passes around without inspecting.

The Backend protocol starts minimal (Stage 0: lifecycle + events + quit) and
grows as later stages add rendering, audio, and asset operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


# ---------------------------------------------------------------------------
# Opaque handle type aliases
# ---------------------------------------------------------------------------
# These are intentionally Any.  The mock backend uses string IDs; the pyglet
# backend uses real pyglet objects.  Framework code passes handles around
# opaquely and never inspects their internals.

ImageHandle = Any
"""Opaque reference to a loaded image.

Mock: ``"img_0"``  /  Pyglet: ``pyglet.image.AbstractImage``
"""

SoundHandle = Any
"""Opaque reference to a loaded sound effect (non-streaming).

Mock: ``"sound_path"``  /  Pyglet: ``pyglet.media.Source``
"""

FontHandle = Any
"""Opaque reference to a loaded font at a particular size.

Mock: ``"font_name_16"``  /  Pyglet: ``(name, size)`` tuple
"""


# ---------------------------------------------------------------------------
# Event dataclasses  (frozen — events are immutable value objects)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class KeyEvent:
    """Keyboard press or release.

    Attributes:
        type: ``"key_press"`` or ``"key_release"``.
        key:  Backend-agnostic string name, e.g. ``"space"``, ``"a"``,
              ``"escape"``, ``"return"``, ``"up"``, ``"down"``.
    """

    type: str  # "key_press" | "key_release"
    key: str


@dataclass(frozen=True)
class MouseEvent:
    """Mouse click, release, movement, drag, or scroll.

    Coordinates are in *logical* space (the framework's fixed coordinate
    system, e.g. 0..1920, 0..1080).  The backend converts from physical
    pixels before creating the event.

    Attributes:
        type:   ``"click"`` | ``"release"`` | ``"move"`` | ``"drag"`` | ``"scroll"``
        x:      Logical x coordinate.
        y:      Logical y coordinate.
        button: ``"left"`` | ``"right"`` | ``"middle"`` | ``None``
                (``None`` for move / scroll events).
        dx:     Horizontal scroll delta (scroll events) or drag delta. 0 by default.
        dy:     Vertical scroll delta (scroll events) or drag delta. 0 by default.
    """

    type: str  # "click" | "release" | "move" | "drag" | "scroll"
    x: int
    y: int
    button: str | None = None
    dx: int = 0
    dy: int = 0


@dataclass(frozen=True)
class WindowEvent:
    """Window lifecycle events.

    Attributes:
        type: ``"close"`` | ``"resize"``
    """

    type: str  # "close" | "resize"


#: Union of all event types dispatched by a backend.
Event = KeyEvent | MouseEvent | WindowEvent


# ---------------------------------------------------------------------------
# Backend protocol
# ---------------------------------------------------------------------------

class Backend(Protocol):
    """Interface that every backend must satisfy (structural subtyping).

    Backends are never subclassed from this class — they simply implement the
    same method signatures.  This keeps the mock backend and the pyglet
    backend fully decoupled.

    The protocol is shown in its *full planned* form.  Stage 0 tests only
    exercise the lifecycle / event / quit subset; later stages exercise
    rendering, audio, and asset methods as they are implemented.
    """

    # -- Lifecycle -----------------------------------------------------------

    def create_window(
        self,
        width: int,
        height: int,
        title: str,
        fullscreen: bool,
        visible: bool = True,
    ) -> None:
        """Create (or reconfigure) the application window.

        *width* and *height* are the logical resolution.  The backend may
        open a physical window at a different size and compute the scale
        factor accordingly.  *visible* controls whether the window is
        initially visible (default ``True``).
        """
        ...

    def begin_frame(self) -> None:
        """Begin a new frame.

        Called once per tick before any draw calls.  GPU backends use this to
        clear the backbuffer; the mock backend resets per-frame state.
        """
        ...

    def end_frame(self) -> None:
        """End the current frame.

        GPU backends submit the batch and flip/present.  The mock backend
        increments its frame counter.
        """
        ...

    def poll_events(self) -> list[Event]:
        """Drain and return all pending input / window events.

        Returns a (possibly empty) list of :class:`Event` objects.  Events
        use logical coordinates — the backend converts physical pixels to
        the framework's coordinate space before returning them.
        """
        ...

    def get_display_info(self) -> tuple[int, int]:
        """Return ``(physical_width, physical_height)`` of the display."""
        ...

    def get_dt(self) -> float:
        """Return seconds elapsed since the last frame (delta time).

        Used by ``Game.run()`` to feed real wall-clock dt into the loop.
        ``Game.tick(dt=...)`` bypasses this by accepting an explicit value.
        """
        ...

    def quit(self) -> None:
        """Tear down the window and release backend resources."""
        ...

    # -- Image / sprite rendering -------------------------------------------

    def load_image(self, path: str) -> ImageHandle:
        """Load an image from *path* and return an opaque handle."""
        ...

    def create_solid_color_image(
        self,
        r: int,
        g: int,
        b: int,
        a: int,
        width: int,
        height: int,
    ) -> ImageHandle:
        """Create a solid-color image of the given size and return a handle.

        Useful for programmatic backgrounds and overlays that don't need
        a PNG file on disk.
        """
        ...

    def create_sprite(
        self,
        image_handle: ImageHandle,
        layer_order: int,
    ) -> Any:
        """Create a persistent sprite in the render batch.

        *layer_order* determines draw order (lower = behind).
        Returns an opaque sprite id that the framework uses to update or
        remove the sprite later.
        """
        ...

    def update_sprite(
        self,
        sprite_id: Any,
        x: int,
        y: int,
        *,
        image: ImageHandle | None = None,
        opacity: int = 255,
        visible: bool = True,
    ) -> None:
        """Update a sprite's position and visual properties.

        Called every frame for each live sprite.  Coordinates are *physical*
        (the framework converts logical -> physical before calling).
        """
        ...

    def remove_sprite(self, sprite_id: Any) -> None:
        """Remove a sprite from the render batch."""
        ...

    def get_image_size(self, image_handle: ImageHandle) -> tuple[int, int]:
        """Return ``(width, height)`` of a loaded image.

        Used by the Sprite class to compute anchor offsets (e.g.
        BOTTOM_CENTER needs the image height to offset upward).
        """
        ...

    def set_sprite_order(self, sprite_id: Any, order: int) -> None:
        """Update the draw order of an existing sprite.

        Called when a sprite's y-position changes (y-sorting) so that
        sprites further down the screen are drawn in front.  *order*
        combines the render layer and y-position into a single integer.
        """
        ...

    def capture_frame(self) -> "PIL.Image.Image":
        """Return a PIL Image of the current framebuffer contents.

        The returned image has the same dimensions as the window
        (logical or physical, backend-dependent) and is in RGBA format.
        """
        ...

    # -- Text rendering -----------------------------------------------------

    def load_font(self, name: str, size: int) -> FontHandle:
        """Load a font at the given logical *size* and return a handle."""
        ...

    def draw_text(
        self,
        text: str,
        font_handle: FontHandle,
        x: int,
        y: int,
        color: tuple[int, int, int, int],
        *,
        width: int | None = None,
        align: str = "left",
    ) -> None:
        """Draw *text* at ``(x, y)`` using *font_handle*.

        This is a per-frame call (not persistent like sprites).  The backend
        may batch text draws within the current frame's begin/end cycle.
        """
        ...

    # -- Audio --------------------------------------------------------------

    def load_sound(self, path: str) -> SoundHandle:
        """Load a short sound effect from *path* (non-streaming)."""
        ...

    def play_sound(self, handle: SoundHandle, volume: float = 1.0) -> None:
        """Play a previously loaded sound effect."""
        ...

    def load_music(self, path: str) -> SoundHandle:
        """Load a music track from *path* (streaming)."""
        ...

    def play_music(
        self,
        handle: SoundHandle,
        *,
        loop: bool = True,
        volume: float = 1.0,
    ) -> Any:
        """Start playing a music track.

        Returns an opaque player id for volume / stop control.
        """
        ...

    def set_player_volume(self, player_id: Any, volume: float) -> None:
        """Set the volume on a currently-playing music player."""
        ...

    def stop_player(self, player_id: Any) -> None:
        """Stop and dispose of a music player."""
        ...
