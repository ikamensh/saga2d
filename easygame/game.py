"""Game class — top-level object that owns the backend and scene stack.

The Game is created once and drives the main loop.  It accepts a backend
by name (``"mock"``, ``"pyglet"``) or by instance (duck-typed).

Two entry points:

* ``game.run(start_scene)`` — production loop, runs until ``game.quit()``
  or window close.
* ``game.tick(dt=0.016)`` — single frame, for deterministic testing.

Scene stack convenience methods (``push``, ``pop``, ``replace``,
``clear_and_push``) delegate to the internal :class:`SceneStack`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from easygame.backends.base import Event, WindowEvent
from easygame.scene import Scene, SceneStack

if TYPE_CHECKING:
    from easygame.assets import AssetManager


class Game:
    """Top-level game object.  Owns the backend, the scene stack, and the
    ``running`` flag.

    Parameters:
        title:      Window title.
        resolution: ``(width, height)`` logical coordinate space.
        fullscreen: Whether to open in fullscreen mode.
        backend:    ``"mock"`` or ``"pyglet"`` (string), or a backend
                    instance that satisfies the
                    :class:`~easygame.backends.base.Backend` protocol.
        visible:    Whether the window is initially visible (default
                    ``True``).  Pass ``False`` to create a hidden window
                    (useful for headless rendering or testing).
    """

    def __init__(
        self,
        title: str,
        *,
        resolution: tuple[int, int] = (1920, 1080),
        fullscreen: bool = True,
        backend: str | object = "pyglet",
        visible: bool = True,
    ) -> None:
        self._title = title
        self._resolution = resolution
        self._fullscreen = fullscreen
        self._visible = visible

        # --- Backend selection ------------------------------------------------
        if backend == "mock":
            from easygame.backends.mock_backend import MockBackend

            self._backend = MockBackend(resolution[0], resolution[1])
        elif backend == "pyglet":
            from easygame.backends.pyglet_backend import PygletBackend  # type: ignore[import-not-found]

            self._backend = PygletBackend()
        elif hasattr(backend, "poll_events"):  # duck-type check
            self._backend = backend
        else:
            raise ValueError(
                f"Unknown backend {backend!r}. "
                "Pass 'mock', 'pyglet', or a backend instance."
            )

        # --- Core state -------------------------------------------------------
        self._scene_stack = SceneStack(self)
        self.running: bool = True
        self._assets: AssetManager | None = None
        self._animated_sprites: set = set()

        from easygame.input import InputManager
        import easygame.util.tween as _tween_mod
        from easygame.util.timer import TimerManager

        self._input = InputManager()

        self._timer_manager = TimerManager()
        self._tween_manager = _tween_mod.TweenManager()
        _tween_mod._tween_manager = self._tween_manager

        # Tell the backend to (notionally) create a window.  The mock backend
        # stores the resolution; the pyglet backend opens a real window.
        self._backend.create_window(
            resolution[0], resolution[1], title, fullscreen, visible,
        )

        # Set the module-level game reference so Sprite() can find us.
        import easygame.rendering.sprite as _sprite_mod

        _sprite_mod._current_game = self

    # ------------------------------------------------------------------
    # Public properties
    # ------------------------------------------------------------------

    @property
    def backend(self) -> object:
        """The underlying backend (for test assertions).

        Not part of the public game-code API, but necessary for test
        fixtures that need ``mock_game.backend.inject_key(...)`` etc.
        """
        return self._backend

    @property
    def assets(self) -> AssetManager:
        """The :class:`~easygame.assets.AssetManager`, created lazily.

        Defaults to ``AssetManager(backend, Path("assets"),
        scale_factor=backend.scale_factor)``.  Set ``game.assets``
        directly to override the base path or scale factor.
        """
        if self._assets is None:
            from easygame.assets import AssetManager as _AM

            scale = getattr(self._backend, "scale_factor", 1.0)
            self._assets = _AM(
                self._backend,
                base_path=Path("assets"),
                scale_factor=scale,
            )
        return self._assets

    @assets.setter
    def assets(self, value: AssetManager) -> None:
        self._assets = value

    @property
    def input(self) -> object:
        """The :class:`~easygame.input.InputManager`.

        Use to rebind actions at runtime::

            game.input.bind("attack", "a")
            game.input.unbind("cancel")
        """
        return self._input

    # ------------------------------------------------------------------
    # Scene stack convenience methods (delegate to SceneStack)
    # ------------------------------------------------------------------

    def push(self, scene: Scene) -> None:
        """Push *scene* onto the stack.  Current top gets ``on_exit``,
        new scene gets ``on_enter``."""
        self._scene_stack.push(scene)

    def pop(self) -> None:
        """Pop the top scene.  It gets ``on_exit``; the new top (if any)
        gets ``on_reveal``."""
        self._scene_stack.pop()

    def replace(self, scene: Scene) -> None:
        """Replace the top scene.  Old top gets ``on_exit``, new scene
        gets ``on_enter``.  No ``on_reveal``."""
        self._scene_stack.replace(scene)

    def clear_and_push(self, scene: Scene) -> None:
        """Clear the entire stack (all scenes get ``on_exit``), then push
        *scene*."""
        self._scene_stack.clear_and_push(scene)

    # ------------------------------------------------------------------
    # Timers
    # ------------------------------------------------------------------

    def after(self, delay: float, callback: Callable[[], Any]) -> int:
        """Schedule a one-shot callback after *delay* seconds.

        Returns a timer ID for cancellation.
        """
        return self._timer_manager.after(delay, callback)

    def every(self, interval: float, callback: Callable[[], Any]) -> int:
        """Schedule a repeating callback every *interval* seconds.

        Returns a timer ID for cancellation.
        """
        return self._timer_manager.every(interval, callback)

    def cancel(self, timer_id: int) -> None:
        """Cancel a timer by ID."""
        self._timer_manager.cancel(timer_id)

    def cancel_tween(self, tween_id: int) -> None:
        """Cancel a tween by ID."""
        self._tween_manager.cancel(tween_id)

    # ------------------------------------------------------------------
    # Quit
    # ------------------------------------------------------------------

    def quit(self) -> None:
        """Set ``running`` to False.

        ``run()`` will exit its loop on the next iteration.  ``tick()``
        callers can inspect ``game.running`` after each tick.
        """
        self.running = False

    # ------------------------------------------------------------------
    # Tick — single frame (primary test entry point)
    # ------------------------------------------------------------------

    def tick(self, dt: float | None = None) -> None:
        """Run exactly **one** iteration of the game loop.

        Parameters:
            dt: Delta time in seconds.  Pass explicitly for deterministic
                tests (e.g. ``dt=0.016`` for 60 fps).  If ``None``, the
                backend's clock is queried via ``get_dt()``.

        Order of operations (matches architecture doc)::

            poll_events → translate → handle_input (deferred) → flush
            → update (deferred) → flush → timers → tweens → animations
            → begin_frame → draw → end_frame
        """
        if dt is None:
            dt = self._backend.get_dt()

        # -- Input phase ---------------------------------------------------
        raw_events: list[Event] = self._backend.poll_events()

        # Handle window events before translation.
        non_window: list[Event] = []
        for event in raw_events:
            if isinstance(event, WindowEvent) and event.type == "close":
                self.quit()
            elif not isinstance(event, WindowEvent):
                non_window.append(event)

        # Translate raw key/mouse events to InputEvents with action mapping.
        input_events = self._input.translate(non_window)

        self._scene_stack.begin_tick()

        for event in input_events:
            top = self._scene_stack.top()
            if top is not None:
                top.handle_input(event)

        self._scene_stack.flush_pending_ops()

        # -- Update phase --------------------------------------------------
        self._scene_stack.begin_tick()
        self._scene_stack.update(dt)
        self._scene_stack.flush_pending_ops()

        # -- Timer phase ---------------------------------------------------
        self._timer_manager.update(dt)

        # -- Tween phase ---------------------------------------------------
        self._tween_manager.update(dt)

        # -- Animation phase -----------------------------------------------
        self._update_animations(dt)

        # -- Draw phase ----------------------------------------------------
        self._backend.begin_frame()
        self._scene_stack.draw()
        self._backend.end_frame()

    # ------------------------------------------------------------------
    # Animation update
    # ------------------------------------------------------------------

    def _update_animations(self, dt: float) -> None:
        """Advance all animated sprites.

        Iterates a *copy* of the set because ``on_complete`` callbacks may
        add or remove sprites (mutating the set during iteration).
        """
        for sprite in list(self._animated_sprites):
            sprite.update_animation(dt)

    # ------------------------------------------------------------------
    # Run — production game loop
    # ------------------------------------------------------------------

    def run(self, start_scene: Scene) -> None:
        """Enter the main loop.  Pushes *start_scene* and loops until
        ``game.quit()`` is called or the window is closed.

        Each iteration calls :meth:`tick` (which internally handles
        ``poll_events``, ``get_dt``, input dispatch, update, and draw).
        After the loop exits the backend is torn down via ``quit()``.

        This is the production entry point.  For testing, use
        :meth:`tick` instead.
        """
        self.push(start_scene)

        while self.running:
            self.tick()

        self._backend.quit()
