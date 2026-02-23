"""Scene base class and SceneStack.

Scene is a concrete base class with no-op lifecycle hooks. Subclasses override
only what they need. SceneStack manages a stack of scenes with push/pop/replace/
clear_and_push. Operations triggered during update() or handle_input() are
deferred and flushed after those phases complete.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from easygame.game import Game
    from easygame.input import InputEvent


class Scene:
    """Self-contained game state: title screen, world map, inventory, etc.

    Lifecycle hooks (all no-op by default):
    - on_enter: called when scene becomes active (after push/replace/clear_and_push)
    - on_exit:  called when scene is removed OR covered (pushed over)
    - on_reveal: called when the scene above is popped
    - update:    called every frame (only top scene, or below if pause_below=False)
    - draw:     called every frame (bottom-up from lowest visible)
    - handle_input: return True to consume event, False to pass through

    The `game` attribute is set by SceneStack before on_enter() so scenes can
    call self.game.push(), self.game.pop(), etc.
    """

    transparent: bool = False
    pause_below: bool = True
    show_hud: bool = True
    real_time: bool = True

    game: Game

    def on_enter(self) -> None:
        """Called when this scene becomes active (top of stack)."""
        pass

    def on_exit(self) -> None:
        """Called when this scene is removed or covered by another scene."""
        pass

    def on_reveal(self) -> None:
        """Called when the scene above this one is popped."""
        pass

    def update(self, dt: float) -> None:
        """Called every frame. Override for game logic."""
        pass

    def draw(self) -> None:
        """Called every frame. Override for rendering."""
        pass

    def handle_input(self, event: InputEvent) -> bool:
        """Handle input event. Return True to consume, False to pass through."""
        return False


class SceneStack:
    """Manages a stack of scenes with deferred push/pop/replace/clear_and_push.

    Operations requested during update() or handle_input() are queued and
    flushed after those phases complete. This avoids modifying the stack
    mid-iteration (e.g. scene receiving on_exit during its own update).
    """

    def __init__(self, game: Game) -> None:
        self._game: Game = game
        self._stack: list[Scene] = []
        self._pending_ops: list[tuple[str, ...]] = []
        self._in_tick: bool = False

    def top(self) -> Scene | None:
        """Return the top scene, or None if stack is empty."""
        return self._stack[-1] if self._stack else None

    def push(self, scene: Scene) -> None:
        """Push scene on top. Current top gets on_exit, new scene gets on_enter."""
        if self._in_tick:
            self._pending_ops.append(("push", scene))
            return
        self._apply_push(scene)

    def pop(self) -> None:
        """Pop top scene. Top gets on_exit, new top (if any) gets on_reveal."""
        if self._in_tick:
            self._pending_ops.append(("pop",))
            return
        self._apply_pop()

    def replace(self, scene: Scene) -> None:
        """Replace top scene. Old gets on_exit, new gets on_enter. No on_reveal."""
        if self._in_tick:
            self._pending_ops.append(("replace", scene))
            return
        self._apply_replace(scene)

    def clear_and_push(self, scene: Scene) -> None:
        """Clear stack, push scene. All cleared scenes get on_exit."""
        if self._in_tick:
            self._pending_ops.append(("clear_and_push", scene))
            return
        self._apply_clear_and_push(scene)

    def begin_tick(self) -> None:
        """Mark start of tick. Operations will be deferred until flush."""
        self._in_tick = True

    def flush_pending_ops(self) -> None:
        """Execute all queued operations, then end tick."""
        self._in_tick = False
        while self._pending_ops:
            op = self._pending_ops.pop(0)
            kind = op[0]
            if kind == "push":
                self._apply_push(op[1])
            elif kind == "pop":
                self._apply_pop()
            elif kind == "replace":
                self._apply_replace(op[1])
            elif kind == "clear_and_push":
                self._apply_clear_and_push(op[1])

    def _apply_push(self, scene: Scene) -> None:
        if self._stack:
            self._stack[-1].on_exit()
        scene.game = self._game
        self._stack.append(scene)
        scene.on_enter()

    def _apply_pop(self) -> None:
        if not self._stack:
            return
        self._stack[-1].on_exit()
        self._stack.pop()
        if self._stack:
            self._stack[-1].on_reveal()

    def _apply_replace(self, scene: Scene) -> None:
        if self._stack:
            self._stack[-1].on_exit()
            self._stack.pop()
        scene.game = self._game
        self._stack.append(scene)
        scene.on_enter()

    def _apply_clear_and_push(self, scene: Scene) -> None:
        for s in reversed(self._stack):
            s.on_exit()
        self._stack.clear()
        scene.game = self._game
        self._stack.append(scene)
        scene.on_enter()

    def update(self, dt: float) -> None:
        """Update the top scene (and below if pause_below=False)."""
        top = self.top()
        if not top:
            return
        scenes_to_update: list[Scene] = []
        i = len(self._stack) - 1
        while i >= 0:
            scenes_to_update.append(self._stack[i])
            if self._stack[i].pause_below:
                break
            i -= 1
        for s in reversed(scenes_to_update):
            s.update(dt)

    def draw(self) -> None:
        """Draw visible scenes from bottom to top.

        Walks the stack from the top downward to find the lowest scene
        that needs to be drawn.  An opaque scene (``transparent=False``,
        the default) blocks everything below it.  A transparent scene
        lets the scene below show through.  Drawing starts from the
        lowest visible scene and proceeds upward.
        """
        if not self._stack:
            return
        # Find the lowest scene we need to draw.  Start at the top and
        # walk downward — stop as soon as we hit an opaque scene because
        # it covers everything below.
        start = len(self._stack) - 1
        while start > 0 and self._stack[start].transparent:
            start -= 1
        # Draw from ``start`` upward (bottom-up within the visible range).
        for i in range(start, len(self._stack)):
            self._stack[i].draw()
