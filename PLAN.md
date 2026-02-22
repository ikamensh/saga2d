# EasyGame — Implementation Plan

## How to use this document

This is a step-by-step implementation plan for the EasyGame framework. Each stage
produces a working, testable increment. Do not skip stages — later ones depend on
earlier ones.

**Reference documents:**
- `DESIGN.md` — API design, abstractions, motivations. This is the source of truth for
  what each class/method should look like. Read the relevant section before implementing.
- `BACKEND.md` — Pyglet-specific implementation details (coordinate conversion, sprite
  batching, text rendering, audio). Read this before writing backend code.
- `desired_examples/` — Before/after code showing the target developer experience.
  These are your acceptance tests — the `_desired.py` files show how the API should
  feel to use.

**Principles:**
- Each stage has a validation script. Write it, run it, confirm it works before moving on.
- Keep the public API clean. Users import from `easygame` and `easygame.ui`, never from
  `easygame.backends` or internal modules.
- Follow the file structure defined in DESIGN.md (section "File / Project Structure").
- Do not add features beyond what the current stage requires.
- When in doubt about API shape, check `desired_examples/` and `DESIGN.md`.

---

## Stage 1 — Window, Game Loop, Scenes

**Goal:** A running window with a game loop where you can push/pop scenes that draw
colored backgrounds. This proves the backend protocol, game loop, and scene lifecycle.

**Files to create:**
```
easygame/
    __init__.py
    game.py              # Game class
    scene.py             # Scene, SceneStack
    backends/
        __init__.py
        base.py          # Backend protocol
        pyglet_backend.py
```

**What to implement:**

1. `backends/base.py` — Backend protocol (Python Protocol class) with:
   - `create_window(width, height, title, fullscreen)`
   - `begin_frame()` / `end_frame()`
   - `poll_events() -> list[Event]`
   - `get_display_info() -> (physical_width, physical_height)`
   - `quit()`
   - Define event types: `KeyEvent`, `MouseEvent`, `WindowEvent` (close, resize)
   - Define opaque handle types as TypeVar or NewType placeholders

2. `backends/pyglet_backend.py` — Pyglet implementation of the protocol:
   - Window creation (fullscreen or windowed)
   - `begin_frame()`: clear window
   - `end_frame()`: flip window
   - Event collection: register pyglet event handlers once at init, drain queue in
     `poll_events()`. See BACKEND.md section "Input events" — do NOT re-register
     handlers per poll.
   - Compute scale_factor: `physical_width / logical_width` (see BACKEND.md
     "Resolution: Logical Coordinates, Native Rendering")
   - Compute letterbox/pillarbox offset (see BACKEND.md "Aspect ratio handling")
   - `to_physical()` / `to_logical()` coordinate conversion (see BACKEND.md
     "Coordinate System" — includes y-axis flip)
   - Game loop: do NOT use `pyglet.app.run()`. Use manual loop with
     `window.dispatch_events()` + `pyglet.clock.tick()`. See BACKEND.md
     "Game loop integration".

3. `scene.py` — Scene base class and SceneStack:
   - Scene has: `on_enter()`, `on_exit()`, `on_reveal()`, `update(dt)`, `draw(ctx)`,
     `handle_input(event) -> bool`
   - Scene properties: `transparent` (default False), `pause_below` (default True),
     `show_hud` (default True), `real_time` (default True)
   - Scene holds a reference to `game` (set by SceneStack when pushed)
   - SceneStack: `push(scene)`, `pop()`, `replace(scene)`, `clear_and_push(scene)`
   - Draw: iterate stack bottom-up, skip non-transparent scenes below the topmost
     opaque scene. Draw from the lowest visible scene upward.
   - Update: only update top scene. If `pause_below` is False, also update below.
   - Input: dispatch to top scene first. If `handle_input` returns True, consumed.

4. `game.py` — Game class:
   - Constructor: `Game(title, resolution=(1920, 1080), fullscreen=True, backend="pyglet")`
   - Owns: backend, scene_stack
   - `run(start_scene)` — enter main loop
   - Main loop order (see DESIGN.md "Game Loop"):
     ```
     dt = clock.tick()
     events = backend.poll_events()
     for event in events: scene_stack dispatch
     scene_stack.update(dt)
     backend.begin_frame()
     scene_stack.draw(ctx)
     backend.end_frame()
     ```
   - `quit()` — set running = False
   - Expose `push()`, `pop()`, `replace()`, `clear_and_push()` as Game methods that
     delegate to SceneStack
   - Handle window close event in the loop

5. `__init__.py` — re-export: `Game`, `Scene`

**Validation — write and run `tests/test_stage1.py`:**
```python
from easygame import Game, Scene

class RedScene(Scene):
    """Draws a red-tinted screen. Press SPACE to push blue, ESC to pop."""
    def draw(self, ctx):
        pass  # just clear color for now

    def handle_input(self, event):
        if event.type == "key_press" and event.key == "space":
            self.game.push(BlueScene())
            return True
        if event.type == "key_press" and event.key == "escape":
            self.game.pop()
            return True

class BlueScene(Scene):
    transparent = True  # should still see red underneath (once drawing exists)

    def handle_input(self, event):
        if event.type == "key_press" and event.key == "escape":
            self.game.pop()
            return True

game = Game("Stage 1 Test", resolution=(1920, 1080), fullscreen=False)
game.run(RedScene())
```

**Done when:** Window opens. Pressing SPACE pushes a scene (no visual change yet, but
on_enter prints or logging confirms). Pressing ESC pops it. Closing window exits cleanly.
Scene lifecycle methods (on_enter, on_exit, on_reveal) fire in correct order — add print
statements to verify. No crashes, no orphaned pyglet processes.

---

## Stage 2 — Assets and Sprites

**Goal:** Load images by name, place sprites on screen with layers and y-sorting.

**Depends on:** Stage 1 (backend can draw, game loop ticks)

**Files to create:**
```
easygame/
    assets.py
    rendering/
        __init__.py
        sprite.py
        layers.py
```

**What to implement:**

1. Extend backend protocol and pyglet backend with:
   - `load_image(path) -> ImageHandle`
   - `create_sprite(image_handle, layer_order) -> SpriteId` — creates a persistent
     pyglet Sprite in the Batch (see BACKEND.md "Efficient sprite rendering")
   - `update_sprite(sprite_id, x, y, image=None, opacity=255, visible=True)`
   - `remove_sprite(sprite_id)`
   - `draw_batch()` — single call renders all sprites
   - Use pyglet `Batch` with one `Group` per render layer (see BACKEND.md). Sprites are
     persistent objects in the batch — update positions each frame, don't recreate.
   - All coordinates passed to backend are physical (after conversion). The framework
     does logical→physical conversion before calling backend methods.

2. `rendering/layers.py` — `RenderLayer` enum:
   - BACKGROUND = 0, OBJECTS = 1, UNITS = 2, EFFECTS = 3, UI_WORLD = 4
   - Y-sorting within a layer: sprites with higher y draw later (on top).
     Implementation: each sprite's group order = `layer * 10000 + y_position`,
     updated when position changes. Or use pyglet OrderedGroup with dynamic order.

3. `rendering/sprite.py` — Sprite class:
   - Constructor: `Sprite(image, position=(0,0), anchor=SpriteAnchor.BOTTOM_CENTER,
     layer=RenderLayer.UNITS, opacity=255, visible=True, scaling="linear")`
   - `image` is a string name (resolved by asset manager)
   - Properties: `position`, `x`, `y`, `opacity`, `visible`, `layer`
   - When any property changes, call backend `update_sprite()`
   - `remove()` — remove from backend batch and unregister
   - Sprites register themselves with a global or game-scoped sprite manager that
     handles y-sort updates and draw coordination
   - `SpriteAnchor` enum: BOTTOM_CENTER (default), CENTER, TOP_LEFT, etc.
     Anchor affects the offset applied before drawing.

4. `assets.py` — AssetManager:
   - Convention: assets live in `assets/` directory relative to the game script
   - `image(name) -> ImageHandle` — loads `assets/images/{name}.png`, caches result
   - Support `@2x` variants: if scale_factor >= 1.5 and `{name}@2x.png` exists,
     load that instead (see DESIGN.md "Assets" and BACKEND.md "Resolution" sections)
   - Sprite sheet support (defer to Stage 3 — for now, single images only)
   - Clear error messages on missing assets: `AssetNotFoundError: No image found for
     'sprites/knight'. Looked in: assets/images/sprites/knight.png`
   - `sound(name)` and `font(name, size)` — stub methods, implement in later stages

5. Update `Game` to own an `AssetManager` instance (`game.assets`).

6. Update Scene `draw()` — the framework draws all registered sprites automatically
   (via the batch). The scene's `draw()` is for additional custom drawing.

**Validation — write and run `tests/test_stage2.py`:**
```python
from easygame import Game, Scene, Sprite, RenderLayer

class SpriteTest(Scene):
    def on_enter(self):
        # Place some sprites — trees behind, knight in front (by layer)
        Sprite("sprites/tree", position=(400, 400), layer=RenderLayer.OBJECTS)
        Sprite("sprites/tree", position=(500, 350), layer=RenderLayer.OBJECTS)
        Sprite("sprites/knight", position=(450, 420), layer=RenderLayer.UNITS)
        # Knight should appear in front of trees (UNITS > OBJECTS layer)

game = Game("Stage 2 Test", fullscreen=False)
game.run(SpriteTest())
```

You will need test PNG files in `assets/images/sprites/`. Create simple colored
rectangles with Pillow if no art is available:
```python
from PIL import Image
img = Image.new("RGBA", (64, 64), (0, 150, 0, 255))  # green for tree
img.save("assets/images/sprites/tree.png")
```

**Done when:** Window shows sprites at correct positions. Trees render behind knight
(layer ordering works). Sprites with higher y within the same layer render in front
(y-sorting works). Changing `sprite.position = (x, y)` at runtime moves the sprite
on screen. `sprite.remove()` makes it disappear.

---

## Stage 3 — Animation

**Goal:** Define animations as reusable templates, play them on sprites with callbacks.

**Depends on:** Stage 2 (sprites exist and can change images)

**Files to create:**
```
easygame/
    rendering/
        animation.py
```

**What to implement:**

1. Extend `AssetManager` with sprite sheet support:
   - Naming convention: `knight_walk_01.png`, `knight_walk_02.png`, ... — load as
     ordered frame list by prefix
   - Alternatively: single `knight_walk.png` sheet + companion `knight_walk.json`
     with frame rects (Aseprite/TexturePacker compatible)
   - `assets.frames(name) -> list[ImageHandle]` — returns ordered frames

2. `rendering/animation.py`:
   - `AnimationDef(frames, frame_duration=0.15, loop=True)` — reusable template.
     `frames` is either a string name (resolved to frame list by asset manager) or
     an explicit list of image names.
   - `AnimationPlayer` — internal class that tracks playback state:
     - current_frame_index, elapsed_time, is_playing, on_complete callback
     - `update(dt)` — advance time, change frame when threshold crossed, fire
       on_complete when non-looping animation finishes
   - Add to Sprite: `play(anim_def, on_complete=None)` — start playing, replacing
     current animation
   - Add to Sprite: `queue(anim_def, on_complete=None)` — play after current finishes
   - Animation player update must be called each frame. Register animated sprites with
     a system that updates them all during the update phase.

3. Wire animation updates into the game loop. In the update phase (after scene update),
   advance all active animation players.

**Validation — write and run `tests/test_stage3.py`:**
```python
from easygame import Game, Scene, Sprite, AnimationDef

idle = AnimationDef(frames="sprites/knight_idle", frame_duration=0.2, loop=True)
walk = AnimationDef(frames="sprites/knight_walk", frame_duration=0.15, loop=True)
attack = AnimationDef(frames="sprites/knight_attack", frame_duration=0.1, loop=False)

class AnimTest(Scene):
    def on_enter(self):
        self.knight = Sprite("sprites/knight_idle_01", position=(400, 400))
        self.knight.play(idle)

    def handle_input(self, event):
        if event.type == "key_press" and event.key == "a":
            self.knight.play(attack, on_complete=lambda: self.knight.play(idle))
            return True

game = Game("Stage 3 Test", fullscreen=False)
game.run(AnimTest())
```

Create test frames: 3-4 colored rectangles with slightly different shading or a
number drawn on them so you can see frames cycling.

**Done when:** Sprite cycles through idle frames visibly. Pressing A plays attack
frames once, then on_complete fires and switches back to idle. `queue()` works —
queued animation starts when current finishes.

---

## Stage 4 — Timers and Tweening

**Goal:** Schedule delayed callbacks, interpolate any numeric property over time.

**Depends on:** Stage 1 (game loop ticks with dt)

**Files to create:**
```
easygame/
    util/
        __init__.py
        timer.py
        tween.py
```

**What to implement:**

1. `util/timer.py` — Timer system:
   - `after(delay, callback) -> timer_id` — call once after delay seconds
   - `every(interval, callback) -> timer_id` — call repeatedly
   - `cancel(timer_id)` — cancel a pending timer
   - `update(dt)` — advance all timers, fire callbacks. Must handle callbacks that
     create new timers or cancel other timers during iteration (iterate over a copy).
   - Owned by Game: `game.after(...)`, `game.every(...)`, `game.cancel(...)`

2. `util/tween.py` — Tween system:
   - `tween(target, property, from_val, to_val, duration, ease=Ease.LINEAR,
     on_complete=None) -> tween_id`
   - Easing functions: `LINEAR`, `EASE_IN`, `EASE_OUT`, `EASE_IN_OUT`
     (quadratic is fine for all of these)
   - `update(dt)` — advance all active tweens, set property values, fire on_complete
   - `cancel(tween_id)`

3. Add `Sprite.move_to(target_pos, speed, on_arrive=None)`:
   - Compute duration from distance and speed
   - Create tweens on `x` and `y` properties
   - Fire on_arrive when both complete

4. Wire timer and tween updates into the game loop, after scene update but before draw.

**Validation — write and run `tests/test_stage4.py`:**
```python
from easygame import Game, Scene, Sprite
from easygame.util.tween import tween, Ease

class TweenTest(Scene):
    def on_enter(self):
        self.box = Sprite("sprites/box", position=(100, 400))
        # Move right over 2 seconds
        tween(self.box, "x", 100, 700, duration=2.0, ease=Ease.EASE_IN_OUT)
        # Fade out over 3 seconds
        tween(self.box, "opacity", 255, 0, duration=3.0)
        # Timer: print after 1 second
        self.game.after(1.0, lambda: print("1 second elapsed"))

    def handle_input(self, event):
        if event.type == "click":
            # Click to move sprite there
            self.box.move_to((event.x, event.y), speed=300)
            return True

game = Game("Stage 4 Test", fullscreen=False)
game.run(TweenTest())
```

**Done when:** Sprite slides from left to right with easing (starts slow, speeds up,
slows down). Opacity fades smoothly. Timer fires after 1 second. Clicking moves
sprite to click position smoothly. Multiple tweens on the same sprite run concurrently.
Starting a new move_to cancels the previous one (no conflict).

---

## Stage 5 — Input System

**Goal:** Map physical keys to named actions. Dispatch events through the scene stack.

**Depends on:** Stage 1 (events exist), Stage 4 (needed before UI)

**Files to create:**
```
easygame/
    input.py
```

**What to implement:**

1. `InputManager`:
   - Default action bindings (see DESIGN.md "Input"):
     - "confirm" → Enter/Return
     - "cancel" → Escape
     - "menu" → Escape (same as cancel by default)
     - "up"/"down"/"left"/"right" → arrow keys
   - `bind(action, key)` — game-defined custom actions
   - `unbind(action)` — remove binding
   - `get_bindings() -> dict` — for settings screen later
   - Translate raw key events from backend into `InputEvent` with `.action` field
     (None if no action mapped to that key, but raw key still available as `.key`)
   - Mouse events become `InputEvent` with `.type` = "click", "hover", "drag", "scroll"
     and `.x`, `.y` in logical coordinates (converted from physical via backend)

2. Update game loop to translate events through InputManager before dispatching to
   scene stack. Dispatch order (see DESIGN.md "Game Loop"):
   ```
   for event in translated_events:
       if scene_stack.top().handle_input(event): continue
   ```
   (HUD and UI dispatch will be added in Stage 8.)

3. Coordinate conversion for mouse events: use backend's `to_logical()` so that
   scenes see logical coordinates (0..1920, 0..1080), never physical pixels.

**Validation — write and run `tests/test_stage5.py`:**
```python
from easygame import Game, Scene

class InputTest(Scene):
    def on_enter(self):
        self.game.input.bind("attack", "a")
        self.game.input.bind("build", "b")

    def handle_input(self, event):
        if event.action == "confirm":
            print("Confirm pressed")
            return True
        if event.action == "attack":
            print("Attack!")
            return True
        if event.type == "click":
            print(f"Clicked at logical ({event.x}, {event.y})")
            return True

game = Game("Stage 5 Test", fullscreen=False)
game.run(InputTest())
```

**Done when:** Pressing Enter prints "Confirm pressed". Pressing A prints "Attack!".
Clicking prints logical coordinates (within 0-1920, 0-1080 range regardless of actual
window size). Pressing unmapped keys does nothing (no crash). ESC quits (default
"cancel" action).

---

## Stage 6 — Camera

**Goal:** Scroll around a world larger than the screen. Convert between screen and
world coordinates.

**Depends on:** Stage 2 (sprites), Stage 4 (tweens for smooth pan), Stage 5 (mouse input)

**Files to create:**
```
easygame/
    rendering/
        camera.py
```

**What to implement:**

1. `Camera` class (see DESIGN.md "Camera & Viewport"):
   - Constructor: `Camera(viewport_size=(1920, 1080), world_bounds=(w, h))`
   - `center_on(x, y)` — center viewport on world position, clamp to world bounds
   - `follow(sprite)` — each frame, center on sprite's position
   - `scroll(dx, dy)` — manual scroll (arrow keys, edge scroll)
   - `enable_edge_scroll(speed, margin)` — scroll when mouse near screen edge.
     Needs mouse position each frame (from input system).
   - `screen_to_world(sx, sy) -> (wx, wy)` — for click handling
   - `world_to_screen(wx, wy) -> (sx, sy)` — for drawing
   - `pan_to(position, speed)` — smooth camera movement using tweens

2. Integrate camera with sprite rendering: when drawing sprites, offset positions by
   camera scroll. The sprite's world position + camera offset = screen position.
   Only sprites within the viewport are sent to the backend (frustum culling).

3. Integrate camera with mouse input: mouse click coordinates must be converted from
   screen to world space using the camera before reaching scene code.

4. Camera owned by Scene (each scene can have its own camera, or none for UI-only
   scenes). Scenes without a camera render sprites at their raw positions (no scroll).

**Validation — write and run `tests/test_stage6.py`:**
```python
from easygame import Game, Scene, Sprite, Camera, RenderLayer
import random

class WorldTest(Scene):
    def on_enter(self):
        self.camera = Camera(viewport_size=(1920, 1080), world_bounds=(4096, 4096))

        # Scatter sprites across the world
        for _ in range(100):
            Sprite("sprites/tree",
                   position=(random.randint(0, 4096), random.randint(0, 4096)),
                   layer=RenderLayer.OBJECTS)

        self.player = Sprite("sprites/knight", position=(2048, 2048))
        self.camera.follow(self.player)
        self.camera.enable_edge_scroll(speed=8, margin=30)

    def handle_input(self, event):
        if event.type == "click":
            world_pos = self.camera.screen_to_world(event.x, event.y)
            self.player.move_to(world_pos, speed=200)
            return True

game = Game("Stage 6 Test", fullscreen=False)
game.run(WorldTest())
```

**Done when:** Window shows a portion of a large world. Moving mouse to screen edges
scrolls the view. Clicking makes the player move to that world position (coordinate
conversion works). Camera follows the player as it moves. Sprites far off-screen are
not visibly glitched (frustum culling works). Scrolling stops at world bounds (no
black void beyond edges).

---

## Stage 7 — Audio

**Goal:** Play music with crossfade, sound effects through channels, sound pools.

**Depends on:** Stage 1 (backend), Stage 2 (asset manager for loading)

**Files to create:**
```
easygame/
    audio.py
```

**What to implement:**

1. Extend backend protocol and pyglet backend with audio methods:
   - `load_sound(path) -> SoundHandle` — non-streaming (sfx)
   - `load_music(path) -> MusicHandle` — streaming (long tracks)
   - `play_sound(handle) -> PlaybackId`
   - `create_music_player() -> MusicPlayerId` — for managing multiple players
     (needed for crossfade: two players, one fading out, one fading in)
   - `set_player_volume(player_id, volume)`
   - `stop_player(player_id)`
   - See BACKEND.md "Audio" section

2. `audio.py` — AudioManager (see DESIGN.md "Audio"):
   - Channels: `master`, `music`, `sfx`, `ui` with volume 0.0-1.0
   - `set_volume(channel, level)` — effective volume = master * channel
   - `play_sound(name)` — load via asset manager, play once on sfx channel
   - `play_music(name, loop=True)` — load as streaming, play on music channel
   - `crossfade_music(name, duration=1.0)` — non-blocking. Create a new music player,
     tween old player volume down and new player volume up simultaneously, then
     dispose old player. Uses tween system from Stage 4.
   - `register_pool(name, sound_names)` — create a sound pool
   - `play_pool(name)` — play random from pool, no immediate repeat of same index

3. Extend `AssetManager`:
   - `sound(name) -> SoundHandle` — loads `assets/sounds/{name}.wav|ogg`
   - `music(name) -> MusicHandle` — loads `assets/music/{name}.ogg` as streaming

4. Owned by Game: `game.audio`

**Validation — write and run `tests/test_stage7.py`:**
```python
from easygame import Game, Scene

class AudioTest(Scene):
    def on_enter(self):
        self.game.audio.play_music("exploration")
        self.game.audio.register_pool("hit", ["hit_01", "hit_02", "hit_03"])

    def handle_input(self, event):
        if event.type == "key_press" and event.key == "1":
            self.game.audio.crossfade_music("battle", duration=1.5)
            return True
        if event.type == "key_press" and event.key == "2":
            self.game.audio.crossfade_music("exploration", duration=1.5)
            return True
        if event.type == "key_press" and event.key == "space":
            self.game.audio.play_pool("hit")
            return True
        if event.type == "key_press" and event.key == "m":
            vol = self.game.audio.get_volume("music")
            self.game.audio.set_volume("music", 0.0 if vol > 0 else 0.7)
            return True

game = Game("Stage 7 Test", fullscreen=False)
game.run(AudioTest())
```

You will need test audio files. Generate with Python if needed:
```python
# Generate a simple sine wave WAV
import struct, wave, math
def make_tone(path, freq=440, duration=0.3, rate=44100):
    with wave.open(path, 'w') as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(rate)
        for i in range(int(rate * duration)):
            f.writeframes(struct.pack('h', int(32767 * math.sin(2*math.pi*freq*i/rate))))
```

**Done when:** Music plays and loops. Pressing 1 crossfades smoothly to battle music
(old fades out, new fades in, no gap, no pop). Pressing 2 crossfades back. SPACE plays
a random hit sound (no immediate repeats when pressing rapidly). M toggles music mute.
No audio glitches or crashes.

---

## Stage 8 — UI Foundation

**Goal:** Component base class, layout system (anchoring + flow), Label, Button, Panel.
Enough to build the menu from `desired_examples/menu_desired.py`.

**Depends on:** Stage 2 (rendering), Stage 5 (input for click/hover)

**Files to create:**
```
easygame/
    ui/
        __init__.py
        component.py
        components.py
        layout.py
        theme.py
```

**What to implement:**

1. `ui/layout.py`:
   - `Anchor` enum: CENTER, TOP, BOTTOM, LEFT, RIGHT, TOP_LEFT, TOP_RIGHT,
     BOTTOM_LEFT, BOTTOM_RIGHT
   - `Layout` enum: VERTICAL, HORIZONTAL, NONE
   - Layout math: given an anchor, parent bounds, and component size, compute
     position. Given a layout direction and spacing, compute child positions.
   - All in logical coordinates.

2. `ui/component.py` — Base `Component` class:
   - Properties: `position`, `size`, `visible`, `enabled`, `style`, `parent`
   - `children: list[Component]`
   - `add(child)` — add child component
   - `handle_event(event) -> bool` — hit test + dispatch to children (front to back)
   - `draw(ctx)` — draw self, then children
   - `compute_layout()` — recursively compute positions based on anchor/layout
   - Hit testing: point-in-rect check in logical coordinates

3. `ui/theme.py`:
   - `Style` dataclass: `font_size`, `font`, `text_color`, `background_color`,
     `background_image`, `padding`, `border_color`, `border_width`
   - `Theme` class: default styles for each component type (button_style,
     label_style, panel_style). Components inherit from theme unless overridden.
   - Game owns a theme: `game.theme`

4. `ui/components.py` — initial set:
   - `Label(text, style=None)` — draw text at computed position.
     Needs backend text rendering. Extend backend protocol:
     - `load_font(name, size) -> FontHandle`
     - `draw_text(text, font_handle, x, y, color, ...)` with scale-factor-aware
       sizing (see BACKEND.md "Text rendering")
   - `Button(text, on_click=None, style=None)` — Label + background + hover/press
     states. On hover: change background. On click: fire callback. Track mouse
     state (normal / hovered / pressed) and pick style accordingly.
   - `Panel(anchor=None, width=None, height=None, layout=None, spacing=0,
     style=None, children=None)` — container. Has background (color or image).
     Arranges children per layout. Supports both `panel.add(child)` and
     `Panel(children=[...])` constructor style.

5. Scene gets a `self.ui` — a root Component that covers the full logical screen.
   `self.ui.add(panel)` adds to the scene's UI tree. The game loop draws the UI
   tree after drawing the scene, and dispatches input to UI before the scene.

6. Extend `__init__.py` re-exports for UI classes.

**Validation — write and run `tests/test_stage8.py`:**
```python
from easygame import Game, Scene
from easygame.ui import Panel, Label, Button, Anchor, Layout, Style

class MenuTest(Scene):
    def on_enter(self):
        panel = Panel(anchor=Anchor.CENTER, layout=Layout.VERTICAL, spacing=16)
        panel.add(Label("EasyGame Menu Test", style=Style(font_size=48)))
        panel.add(Button("Button 1", on_click=lambda: print("Clicked 1")))
        panel.add(Button("Button 2", on_click=lambda: print("Clicked 2")))
        panel.add(Button("Quit", on_click=self.game.quit))
        self.ui.add(panel)

game = Game("Stage 8 Test", fullscreen=False)
game.run(MenuTest())
```

**Done when:** Window shows a centered panel with a title and 3 buttons stacked
vertically. Hovering a button changes its appearance. Clicking "Quit" exits. Clicking
buttons 1 and 2 prints to console. Resizing the window keeps the panel centered
(anchor works). Text is sharp (not blurry from incorrect scaling).

**This is the critical milestone.** After this stage, `desired_examples/menu_desired.py`
should work (minus music and scene transitions). If the API feels wrong at this point,
fix it before proceeding.

---

## Stage 9 — UI Widgets and Text

**Goal:** Complete the widget set. TextBox with typewriter. ImageBox, List, Grid,
ProgressBar, Tooltip, TabGroup, DataTable.

**Depends on:** Stage 8 (UI foundation)

**What to implement:**

See DESIGN.md "Standard Components" table for the full list. Implement in this order
(each builds on the last):

1. `ImageBox(image_name, width, height)` — display an image in the UI tree
2. `ProgressBar(value, max_value, ...)` — filled bar (health, mana)
3. `TextBox(text, typewriter_speed=None, auto_scroll_speed=None)` — multi-line text
   with word wrapping. Typewriter: reveal characters gradually (see DESIGN.md
   "Text Effects"). Uses timer from Stage 4 internally.
4. `List(items, on_select)` — scrollable list of selectable items. Keyboard nav
   with up/down arrows.
5. `Grid(columns, rows, cell_size)` — grid of cells, each can hold a component.
   Click to select cell.
6. `Tooltip(text)` — appears on hover after a short delay, follows mouse, always
   renders on top of everything.
7. `TabGroup(tabs)` — tabbed container, each tab is a Panel.
8. `DataTable(columns, rows)` — rows + columns with headers.

Do not try to implement all at once. Implement each, test it in isolation, then move on.

**Validation:** For each widget, write a small test scene that shows it working.
The key integration test is `desired_examples/ui_dialog_desired.py` — after this
stage, a simplified version of it should work (Panel with ImageBox + TextBox + Buttons).

**Done when:** All widgets render correctly, respond to input, and respect the theme.
TextBox typewriter effect reveals characters gradually. List scrolls and selects. Grid
cells are clickable.

---

## Stage 10 — Actions

**Goal:** Composable action sequences: Sequence, Parallel, Delay, Do, PlayAnim,
MoveTo, FadeOut, FadeIn, Remove, Repeat.

**Depends on:** Stage 3 (animation), Stage 4 (tweens, timers)

**Files to create:**
```
easygame/
    actions.py
```

**What to implement:**

See DESIGN.md "Composable Actions" for the full API.

1. Base `Action` class with:
   - `start(sprite)` — called when the action begins on a sprite
   - `update(dt) -> bool` — called each frame, return True when done
   - `stop()` — called when cancelled

2. Concrete actions:
   - `Sequence(*actions)` — run in order. Start first, when done start second, etc.
   - `Parallel(*actions)` — run simultaneously, done when ALL are done.
   - `Delay(seconds)` — timer countdown
   - `Do(callable)` — call function immediately, done instantly
   - `PlayAnim(anim_def)` — play animation on the sprite, done when non-looping
     animation completes. For looping anims, never finishes (use in Parallel with
     something that does finish, like MoveTo).
   - `MoveTo(position, speed)` — tween x and y, done on arrival
   - `FadeOut(duration)` — tween opacity to 0
   - `FadeIn(duration)` — tween opacity to 255
   - `Remove()` — call sprite.remove(), done instantly
   - `Repeat(action, times=None)` — repeat N times, or forever if times is None

3. Add to Sprite:
   - `do(action)` — start an action sequence on this sprite. Cancels any current action.
   - `stop_actions()` — cancel current action
   - Active action's `update(dt)` is called each frame (alongside animation updates)

**Validation — write and run `tests/test_stage10.py`:**
```python
from easygame import Game, Scene, Sprite, AnimationDef
from easygame.actions import Sequence, Parallel, Delay, Do, PlayAnim, MoveTo, FadeOut, Remove

idle = AnimationDef(frames="sprites/knight_idle", frame_duration=0.2, loop=True)
walk = AnimationDef(frames="sprites/knight_walk", frame_duration=0.15, loop=True)

class ActionTest(Scene):
    def on_enter(self):
        self.knight = Sprite("sprites/knight_idle_01", position=(100, 400))
        self.knight.do(Sequence(
            Parallel(PlayAnim(walk), MoveTo((700, 400), speed=150)),
            Delay(0.5),
            Parallel(PlayAnim(walk), MoveTo((100, 400), speed=150)),
            PlayAnim(idle),
            Delay(1.0),
            Do(lambda: print("Sequence complete!")),
        ))

game = Game("Stage 10 Test", fullscreen=False)
game.run(ActionTest())
```

**Done when:** Knight walks right (walk anim + movement simultaneously), pauses,
walks back, idles, waits 1 second, prints "Sequence complete!". Nested compositions
work (Sequence inside Parallel, Parallel inside Repeat). `stop_actions()` cancels
mid-sequence.

---

## Stage 11 — Remaining Rendering Features

**Goal:** Particles, color swaps, cursor management.

**Depends on:** Stage 2 (sprites), Stage 4 (timers)

**Files to create/modify:**
```
easygame/
    rendering/
        particles.py
        color_swap.py
    cursor.py
```

**What to implement:**

1. `rendering/particles.py` — ParticleEmitter (see DESIGN.md "Particle Emitter"):
   - `ParticleEmitter(image, position, count, speed, direction, lifetime, fade_out)`
   - `burst(count)` — spawn all at once
   - `continuous(rate)` — spawn N per second
   - `stop()` — stop spawning, let existing particles die
   - Particles are lightweight sprites on EFFECTS layer. Each has velocity + lifetime.
   - Emitter's `update(dt)` moves particles and removes dead ones.

2. `rendering/color_swap.py` — ColorSwap (see DESIGN.md "Color Swaps"):
   - `ColorSwap(source_colors, target_colors)` — pixel replacement
   - Uses Pillow (see BACKEND.md "Color Swap Implementation")
   - Cache per (image_path, color_swap) pair
   - Sprite constructor accepts `color_swap` or `team_palette` parameter

3. `cursor.py` — Cursor management (see DESIGN.md "Cursor"):
   - `game.cursor.set("default")`, `game.cursor.set("attack")`, etc.
   - Load cursor images from assets
   - Extend backend to support custom cursor setting (pyglet has cursor support)

**Validation:** Particle test: emitter at center, burst of 30 sparks flying outward
and fading. Continuous emitter producing smoke. Color swap: same knight sprite in red
and blue team colors side by side. Cursor: changes to crosshair when pressing C.

---

## Stage 12 — Drag-and-Drop and FSM

**Goal:** UI drag-and-drop system. Simple finite state machine utility.

**Depends on:** Stage 8 (UI components), Stage 5 (input)

**Files to create:**
```
easygame/
    ui/
        drag_drop.py
    util/
        fsm.py
```

**What to implement:**

1. `ui/drag_drop.py` (see DESIGN.md "Drag-and-Drop"):
   - Any component with `draggable=True` can be dragged
   - Ghost image follows cursor during drag (semi-transparent copy, rendered on top)
   - Drop targets: components with `drop_accept` predicate and `on_drop` callback
   - Visual feedback: target highlights green (valid) or red (invalid) during hover
   - Mouse tracking: on mouse_down on draggable, start drag. On mouse_up, check
     drop target at position. If valid, fire on_drop. If not, return to origin.

2. `util/fsm.py` — StateMachine (see DESIGN.md "State Machine"):
   - `StateMachine(states, initial, transitions, on_enter, on_exit)`
   - `trigger(event_name)` — transition if valid
   - `state` — current state
   - on_enter/on_exit callbacks per state

**Validation:** Drag-and-drop: grid of colored boxes, drag one to another slot. FSM:
unit state machine (idle→walking→attacking→idle) triggered by key presses, with
print on each state enter.

---

## Stage 13 — Convenience Screens and Save/Load

**Goal:** Pre-built screens (MessageScreen, ChoiceScreen, ConfirmDialog), save/load
system, settings screen, HUD layer.

**Depends on:** Stage 8-9 (UI), Stage 7 (audio for settings), Stage 5 (input for settings)

**Files to create:**
```
easygame/
    save.py
    ui/
        screens.py
        hud.py
```

**What to implement:**

1. `ui/screens.py` (see DESIGN.md "Convenience Screens"):
   - `MessageScreen(text, on_dismiss)` — full-screen text, press any key to continue
   - `ChoiceScreen(prompt, choices, on_choice)` — prompt with choice buttons
   - `ConfirmDialog(question, on_confirm, on_cancel)` — yes/no dialog
   - `SaveLoadScreen(mode="save"|"load")` — slot list with timestamps
   - `game.show_sequence(screens, on_complete)` — chain of MessageScreens

2. `save.py` (see DESIGN.md "Save/Load"):
   - `game.save(slot)` — calls `scene.get_save_state()`, writes JSON to
     `saves/slot_{n}.json` with metadata (timestamp, schema version)
   - `game.load(slot)` — reads JSON, calls `scene.load_save_state(data)`
   - Save directory: platform-appropriate (use `platformdirs` or `~/.gamename/saves/`)
   - Slot listing for SaveLoadScreen

3. `ui/hud.py` (see DESIGN.md "Persistent HUD Layer"):
   - `game.hud` — a UI container that renders above scenes, below modals
   - Scenes can suppress it: `show_hud = False`

4. Settings screen:
   - `game.push_settings()` — built-in scene with volume sliders and key rebinding
   - Volume controls: sliders for master, music, sfx, ui
   - Key rebinding: list of actions, click to rebind, press new key
   - This is the integration test for UI + Audio + Input all working together

**Validation:** `desired_examples/menu_desired.py` should now work completely:
title screen with buttons, push settings, push save/load, message screen with
dismiss, scene replacement. This is the final integration test.

**Done when:** The Standard Game Flow Example from DESIGN.md runs exactly as written.

---

## Stage Summary

| Stage | What | Depends on | Key deliverable |
|---|---|---|---|
| 1 | Window, loop, scenes | — | Running window, scene push/pop |
| 2 | Assets, sprites | 1 | Sprites on screen with layers |
| 3 | Animation | 2 | Frame animation with callbacks |
| 4 | Timers, tweens | 1 | Smooth movement, delayed callbacks |
| 5 | Input | 1 | Action mapping, logical mouse coords |
| 6 | Camera | 2, 4, 5 | Scrolling world, edge scroll |
| 7 | Audio | 1, 2 | Music crossfade, sound pools |
| 8 | UI foundation | 2, 5 | Centered menu with buttons |
| 9 | UI widgets | 8 | TextBox, List, Grid, etc. |
| 10 | Actions | 3, 4 | Composable sequences |
| 11 | Particles, color swap, cursor | 2, 4 | Spell effects, team colors |
| 12 | Drag-drop, FSM | 8, 5 | Inventory drag, entity states |
| 13 | Convenience screens, save/load | 8, 7, 5 | Full menu_desired.py works |

**Parallel opportunities:** Stages 7 (audio) and 6 (camera) are independent of each
other and of 8 (UI). Stage 10 (actions) is independent of 8-9 (UI). Stage 11
(particles, color swap) is independent of everything after stage 4.

**The critical path is:** 1 → 2 → 3+4+5 (parallel) → 8 → 9 → 13.
Everything else can be woven in around this path.
