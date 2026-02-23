"""Pyglet backend — GPU-accelerated rendering via OpenGL.

This module is **never imported at module level** by the framework.  The
``Game`` class performs a lazy ``from easygame.backends.pyglet_backend import
PygletBackend`` inside ``if backend == "pyglet"`` so that tests never need
pyglet installed.

Implements the full :class:`~easygame.backends.base.Backend` protocol.
Stage 1 only exercises lifecycle + events + quit; rendering and audio
methods are stubbed (functional but minimal) and will be fleshed out in
later stages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from easygame.backends.base import (
    Event,
    KeyEvent,
    MouseEvent,
    WindowEvent,
)

if TYPE_CHECKING:
    import pyglet


def _symbol_to_name(symbol: int) -> str:
    """Convert a pyglet key symbol to a lowercase backend-agnostic name."""
    from pyglet.window import key as pyglet_key

    overrides = {
        pyglet_key._0: "0",
        pyglet_key._1: "1",
        pyglet_key._2: "2",
        pyglet_key._3: "3",
        pyglet_key._4: "4",
        pyglet_key._5: "5",
        pyglet_key._6: "6",
        pyglet_key._7: "7",
        pyglet_key._8: "8",
        pyglet_key._9: "9",
        pyglet_key.ENTER: "return",
    }
    return overrides.get(symbol) or pyglet_key.symbol_string(symbol).lower()


def _button_to_name(button: int) -> str:
    """Convert a pyglet mouse button constant to left/right/middle."""
    from pyglet.window import mouse as pyglet_mouse

    if button == pyglet_mouse.LEFT:
        return "left"
    if button == pyglet_mouse.RIGHT:
        return "right"
    if button == pyglet_mouse.MIDDLE:
        return "middle"
    return "unknown"


def _buttons_to_name(buttons: int) -> str | None:
    """Convert pyglet buttons bitmask to a single button name, or None."""
    from pyglet.window import mouse as pyglet_mouse

    if buttons & pyglet_mouse.LEFT:
        return "left"
    if buttons & pyglet_mouse.RIGHT:
        return "right"
    if buttons & pyglet_mouse.MIDDLE:
        return "middle"
    return None


# ---------------------------------------------------------------------------
# PygletBackend
# ---------------------------------------------------------------------------

class PygletBackend:
    """GPU-accelerated backend using pyglet 2.x.

    Satisfies the :class:`~easygame.backends.base.Backend` protocol via
    structural subtyping — does **not** inherit from ``Backend``.
    """

    def __init__(self) -> None:
        # Populated by create_window.
        self.window: pyglet.window.Window | None = None
        self.batch: pyglet.graphics.Batch | None = None

        self.logical_width: int = 0
        self.logical_height: int = 0
        self.scale_factor: float = 1.0
        self.offset_x: float = 0.0
        self.offset_y: float = 0.0

        self._event_queue: list[Event] = []

        # Sprite tracking (populated in later stages)
        self._sprites: dict[int, pyglet.sprite.Sprite] = {}
        self._next_sprite_id: int = 0

        # Frame-local text labels (cleared each begin_frame)
        self._text_labels: list[pyglet.text.Label] = []

    # ==================================================================
    # Coordinate conversion
    # ==================================================================

    def _compute_viewport(
        self,
        logical_w: int,
        logical_h: int,
        physical_w: int,
        physical_h: int,
    ) -> None:
        """Compute scale factor and letterbox/pillarbox offsets."""
        physical_ratio = physical_w / physical_h
        logical_ratio = logical_w / logical_h

        if physical_ratio > logical_ratio:
            # Physical is wider → pillarbox (black bars on sides)
            self.scale_factor = physical_h / logical_h
            self.offset_x = (physical_w - logical_w * self.scale_factor) / 2
            self.offset_y = 0.0
        else:
            # Physical is taller → letterbox (black bars top/bottom)
            self.scale_factor = physical_w / logical_w
            self.offset_x = 0.0
            self.offset_y = (physical_h - logical_h * self.scale_factor) / 2

    def _to_physical(
        self, logical_x: float, logical_y: float,
    ) -> tuple[float, float]:
        """Convert framework logical coords → pyglet physical coords.

        Includes y-axis flip (framework: top-left origin, y-down;
        pyglet/OpenGL: bottom-left origin, y-up) and scale + offset.
        """
        physical_x = logical_x * self.scale_factor + self.offset_x
        physical_y = (
            (self.logical_height - logical_y) * self.scale_factor
            + self.offset_y
        )
        return physical_x, physical_y

    def _to_logical(
        self, physical_x: float, physical_y: float,
    ) -> tuple[int, int]:
        """Convert pyglet physical coords → framework logical coords.

        Inverse of :meth:`_to_physical`.
        """
        logical_x = (physical_x - self.offset_x) / self.scale_factor
        logical_y = (
            self.logical_height
            - (physical_y - self.offset_y) / self.scale_factor
        )
        return int(logical_x), int(logical_y)

    # ==================================================================
    # Backend protocol — lifecycle
    # ==================================================================

    def create_window(
        self,
        width: int,
        height: int,
        title: str,
        fullscreen: bool,
    ) -> None:
        import pyglet
        import pyglet.event

        self.logical_width = width
        self.logical_height = height

        self.window = pyglet.window.Window(
            width=width,
            height=height,
            caption=title,
            fullscreen=fullscreen,
            vsync=True,
        )

        # Persistent batch — NOT recreated per frame.
        self.batch = pyglet.graphics.Batch()

        # Compute viewport from actual physical window size.
        self._compute_viewport(
            width, height, self.window.width, self.window.height,
        )

        # --- Register event handlers ONCE ---------------------------------
        backend = self  # capture for closures

        @self.window.event
        def on_key_press(symbol: int, modifiers: int) -> None:
            backend._event_queue.append(
                KeyEvent(type="key_press", key=_symbol_to_name(symbol)),
            )

        @self.window.event
        def on_key_release(symbol: int, modifiers: int) -> None:
            backend._event_queue.append(
                KeyEvent(type="key_release", key=_symbol_to_name(symbol)),
            )

        @self.window.event
        def on_mouse_press(
            x: int, y: int, button: int, modifiers: int,
        ) -> None:
            lx, ly = backend._to_logical(x, y)
            backend._event_queue.append(
                MouseEvent(
                    type="click", x=lx, y=ly,
                    button=_button_to_name(button),
                ),
            )

        @self.window.event
        def on_mouse_release(
            x: int, y: int, button: int, modifiers: int,
        ) -> None:
            lx, ly = backend._to_logical(x, y)
            backend._event_queue.append(
                MouseEvent(
                    type="release", x=lx, y=ly,
                    button=_button_to_name(button),
                ),
            )

        @self.window.event
        def on_mouse_motion(x: int, y: int, dx: int, dy: int) -> None:
            lx, ly = backend._to_logical(x, y)
            backend._event_queue.append(
                MouseEvent(type="move", x=lx, y=ly),
            )

        @self.window.event
        def on_mouse_drag(
            x: int, y: int, dx: int, dy: int,
            buttons: int, modifiers: int,
        ) -> None:
            lx, ly = backend._to_logical(x, y)
            ldx = int(dx / backend.scale_factor)
            ldy = int(dy / backend.scale_factor)
            button = _buttons_to_name(buttons)
            backend._event_queue.append(
                MouseEvent(
                    type="drag", x=lx, y=ly, button=button, dx=ldx, dy=ldy,
                ),
            )

        @self.window.event
        def on_mouse_scroll(
            x: int, y: int, scroll_x: float, scroll_y: float,
        ) -> None:
            lx, ly = backend._to_logical(x, y)
            backend._event_queue.append(
                MouseEvent(
                    type="scroll", x=lx, y=ly,
                    dx=int(scroll_x), dy=int(scroll_y),
                ),
            )

        @self.window.event
        def on_close() -> bool:
            # Prevent pyglet's default window.close().  The framework
            # handles quit via Game.quit() after seeing the WindowEvent.
            backend._event_queue.append(WindowEvent(type="close"))
            return pyglet.event.EVENT_HANDLED  # type: ignore[return-value]

        @self.window.event
        def on_resize(new_width: int, new_height: int) -> None:
            backend._compute_viewport(
                backend.logical_width, backend.logical_height,
                new_width, new_height,
            )
            backend._event_queue.append(WindowEvent(type="resize"))

    def begin_frame(self) -> None:
        if self.window is None:
            return
        self.window.clear()
        # Discard per-frame text labels from the previous frame.
        for label in self._text_labels:
            label.delete()
        self._text_labels.clear()

    def end_frame(self) -> None:
        if self.window is None or self.batch is None:
            return
        self.batch.draw()
        self.window.flip()

    def poll_events(self) -> list[Event]:
        if self.window is not None:
            self.window.dispatch_events()
        events = self._event_queue.copy()
        self._event_queue.clear()
        return events

    def get_display_info(self) -> tuple[int, int]:
        if self.window is not None:
            return (self.window.width, self.window.height)
        return (self.logical_width, self.logical_height)

    def get_dt(self) -> float:
        import pyglet
        return pyglet.clock.tick()

    def quit(self) -> None:
        if self.window is not None:
            self.window.close()
            self.window = None

    # ==================================================================
    # Backend protocol — image / sprite rendering
    # ==================================================================

    def create_solid_color_image(
        self,
        r: int,
        g: int,
        b: int,
        a: int,
        width: int,
        height: int,
    ):
        """Create a solid-color image (PygletBackend-specific, for demos)."""
        import pyglet
        pattern = pyglet.image.SolidColorImagePattern((r, g, b, a))
        return pattern.create_image(width, height)

    def load_image(self, path: str):
        import pyglet
        return pyglet.image.load(path)

    def create_sprite(
        self,
        image_handle,
        layer_order: int,
    ) -> int:
        import pyglet
        group = pyglet.graphics.Group(order=layer_order)
        pyg_sprite = pyglet.sprite.Sprite(
            image_handle, batch=self.batch, group=group,
        )
        sid = self._next_sprite_id
        self._next_sprite_id += 1
        self._sprites[sid] = pyg_sprite
        return sid

    def update_sprite(
        self,
        sprite_id: int,
        x: int,
        y: int,
        *,
        image=None,
        opacity: int = 255,
        visible: bool = True,
    ) -> None:
        phys_x, phys_y = self._to_physical(x, y)
        pyg = self._sprites[sprite_id]
        pyg.x = phys_x
        pyg.y = phys_y
        pyg.opacity = opacity
        pyg.visible = visible
        if image is not None:
            pyg.image = image

    def remove_sprite(self, sprite_id: int) -> None:
        self._sprites[sprite_id].delete()
        del self._sprites[sprite_id]

    def get_image_size(self, image_handle) -> tuple[int, int]:
        """Return ``(width, height)`` of a loaded pyglet image."""
        return (image_handle.width, image_handle.height)

    def set_sprite_order(self, sprite_id: int, order: int) -> None:
        """Update the draw order of an existing sprite.

        Replaces the sprite's group with a new one at the given *order*.
        """
        import pyglet
        pyg = self._sprites[sprite_id]
        pyg.group = pyglet.graphics.Group(order=order)

    # ==================================================================
    # Backend protocol — text rendering
    # ==================================================================

    def load_font(self, name: str, size: int) -> tuple[str, int]:
        """Return ``(font_name, logical_size)`` tuple.

        Physical size is computed at draw time using the scale factor.
        """
        return (name, size)

    def draw_text(
        self,
        text: str,
        font_handle: tuple[str, int],
        x: int,
        y: int,
        color: tuple[int, int, int, int],
        *,
        width: int | None = None,
        align: str = "left",
    ) -> None:
        if self.batch is None:
            return
        import pyglet
        name, logical_size = font_handle
        physical_size = int(logical_size * self.scale_factor)
        phys_x, phys_y = self._to_physical(x, y)
        physical_width = int(width * self.scale_factor) if width else None
        label = pyglet.text.Label(
            text,
            font_name=name,
            font_size=physical_size,
            x=int(phys_x),
            y=int(phys_y),
            color=color,
            width=physical_width,
            multiline=physical_width is not None,
            anchor_x=align,
            batch=self.batch,
        )
        # Keep a reference so the label survives until end_frame draws
        # the batch; delete in the next begin_frame.
        self._text_labels.append(label)

    # ==================================================================
    # Backend protocol — audio
    # ==================================================================

    def load_sound(self, path: str):
        import pyglet
        return pyglet.media.load(path, streaming=False)

    def play_sound(self, handle, volume: float = 1.0) -> None:
        player = handle.play()
        player.volume = volume

    def load_music(self, path: str):
        import pyglet
        return pyglet.media.load(path, streaming=True)

    def play_music(
        self,
        handle,
        *,
        loop: bool = True,
        volume: float = 1.0,
    ):
        import pyglet
        player = pyglet.media.Player()
        player.queue(handle)
        player.loop = loop
        player.volume = volume
        player.play()
        return player

    def set_player_volume(self, player_id, volume: float) -> None:
        player_id.volume = volume

    def stop_player(self, player_id) -> None:
        player_id.pause()
        player_id.delete()
