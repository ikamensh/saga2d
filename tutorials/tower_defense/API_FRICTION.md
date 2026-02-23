# API Friction Log — Tower Defense Tutorial (Chapters 1–3)

This document records concrete friction points discovered while building
`ch1_title_screen.py`, `ch2_game_map.py`, and `ch3_tower_placement.py`
against the EasyGame framework.  Each entry includes the awkward code,
why it hurts, and a proposed fix.

---

## 1. Scene background color requires raw backend calls

### The awkward code

Every scene that wants a solid background color must drop down to the
backend's low-level API — `create_solid_color_image`, `create_sprite`,
`update_sprite` — then manually clean it up in `on_exit`:

```python
# ch1, ch2, ch3 — identical boilerplate in every TitleScene.on_enter()
backend = self.game.backend
bg_image = backend.create_solid_color_image(
    BG_COLOR[0], BG_COLOR[1], BG_COLOR[2], BG_COLOR[3],
    SCREEN_W, SCREEN_H,
)
self._bg_sprite_id = backend.create_sprite(
    bg_image,
    RenderLayer.BACKGROUND.value * 100_000,
)
backend.update_sprite(self._bg_sprite_id, 0, 0)
```

```python
# ... and the cleanup in on_exit()
def on_exit(self) -> None:
    if self._bg_sprite_id is not None:
        self.game.backend.remove_sprite(self._bg_sprite_id)
        self._bg_sprite_id = None
```

### Why it's friction

This is 10 lines of backend plumbing (plus cleanup) for the most common
thing a scene needs to do.  It also requires importing `RenderLayer` and
knowing the `layer.value * 100_000` ordering formula.  A first-time user
shouldn't need to understand render layer arithmetic just to set a
background color.

### Proposed fix

Add a `background_color` class attribute (or `on_enter` parameter) to
`Scene` that the framework handles automatically:

```python
class TitleScene(Scene):
    background_color = (25, 30, 40, 255)  # handled by framework
```

The `SceneStack` would create and destroy the background sprite around
the `on_enter`/`on_exit` lifecycle, so game code never touches the
backend directly for this.

---

## 2. Manual sprite cleanup is error-prone and tedious

### The awkward code

Every scene that creates sprites must track them in lists/dicts and
explicitly `.remove()` each one in `on_exit()`:

```python
# ch3 GameScene.on_exit() — 15 lines of cleanup
def on_exit(self) -> None:
    for sprite in self._tile_sprites:
        sprite.remove()
    self._tile_sprites.clear()

    for sprite in self._slot_sprites.values():
        sprite.remove()
    self._slot_sprites.clear()

    for sprite in self._tower_sprites:
        sprite.remove()
    self._tower_sprites.clear()

    if self._range_indicator is not None:
        self._range_indicator.remove()
        self._range_indicator = None

    self._placed_towers.clear()
    self._scroll_dx = 0.0
    self._scroll_dy = 0.0
```

ch2's `on_exit` has the same pattern with `_tile_sprites` and
`_slot_sprites`.  Every new sprite collection adds another for-loop.

### Why it's friction

Forgetting to remove even one sprite causes visual ghosts.  As the
scene gains more sprite types (enemies, projectiles, effects), the
cleanup block grows linearly and each addition is a potential bug.
The framework knows which sprites exist in the backend batch — the
game code shouldn't have to mirror that bookkeeping.

### Proposed fix

Add a `Scene.add_sprite()` method (or `Sprite(... scene=self)`) that
registers the sprite with the scene.  On `on_exit`, the framework
auto-removes all sprites owned by the scene:

```python
# Game code — no manual cleanup needed
sprite = self.add_sprite("grass", position=(x, y), layer=RenderLayer.BACKGROUND)

# Or: sprites created while a scene is active are auto-owned by it
sprite = Sprite("grass", position=(x, y))  # implicitly owned by active scene
```

The framework could use the existing `Game._all_sprites` set, partitioned
per scene, to remove sprites when a scene exits.  Individual early removal
via `sprite.remove()` would still work.

---

## 3. AssetManager must be constructed separately from Game

### The awkward code

Every tutorial file repeats this same three-step setup:

```python
game = Game(
    "Tower Defense — Chapter 3",
    resolution=(SCREEN_W, SCREEN_H),
    fullscreen=False,
    backend="pyglet",
)

game.assets = AssetManager(
    game.backend,         # must pass game.backend manually
    base_path=_asset_dir, # must pass the path
)

game.theme = Theme(...)
```

The `AssetManager` constructor requires `game.backend` as its first
argument, which means the user must know about the backend object even
though they just told `Game` which backend to use.

### Why it's friction

The user already told `Game` which backend to use.  Having to fish out
`game.backend` and pass it to `AssetManager` is a leaky abstraction.
Most games only need to say "my assets are here".

### Proposed fix

Accept `asset_path` as a `Game` constructor parameter:

```python
game = Game(
    "Tower Defense — Chapter 3",
    resolution=(SCREEN_W, SCREEN_H),
    asset_path=_asset_dir,          # one line instead of three
    backend="pyglet",
)
```

The `Game` would construct the `AssetManager` internally, using its own
backend reference.  The explicit `game.assets = AssetManager(...)` form
would still work for advanced use cases (custom scale factor, etc.).

---

## 4. No visual feedback for disabled buttons

### The awkward code

In ch3, Buy buttons are disabled when the player can't afford a tower:

```python
def _refresh_buy_buttons(self) -> None:
    for i, tdef in enumerate(TOWER_DEFS):
        can_afford = self._gold >= tdef["cost"]
        self._buy_buttons[i].enabled = can_afford
```

Setting `enabled = False` blocks input correctly (the framework handles
that), but **the button looks identical to an enabled one**.  There is no
visual distinction — no greyed-out text, no dimmed background.

### Why it's friction

The `Component` docstring says disabled components "draw (greyed out) but
skip input", but the actual `Button.on_draw()` always resolves the
`"normal"` state style when not hovered/pressed — it never checks
`self.enabled`.  The user either gets confusingly invisible feedback or
must add their own style-swapping logic.

### Proposed fix

The `Button.on_draw()` should respect `self.enabled`.  When disabled,
resolve a `"disabled"` state that applies lower opacity or a muted color.
Theme could gain `button_disabled_color` and `button_disabled_text_color`
fields:

```python
# In Button.on_draw():
if not self.enabled:
    resolved = self._resolve_style("disabled")
else:
    resolved = self._resolve_style(self._state)
```

```python
# In Theme:
button_disabled_color=(40, 42, 55, 200),
button_disabled_text_color=(100, 100, 110, 200),
```

---

## 5. Arrow-key scrolling requires manual key_press/key_release tracking

### The awkward code

Both ch2 and ch3 duplicate this 20-line pattern to scroll the camera
with arrow keys:

```python
# In handle_input — track held directions
if event.type == "key_press":
    if event.action == "left":
        self._scroll_dx = -speed
        return True
    elif event.action == "right":
        self._scroll_dx = speed
        return True
    elif event.action == "up":
        self._scroll_dy = -speed
        return True
    elif event.action == "down":
        self._scroll_dy = speed
        return True

if event.type == "key_release":
    if event.action in ("left", "right"):
        self._scroll_dx = 0.0
        return True
    elif event.action in ("up", "down"):
        self._scroll_dy = 0.0
        return True
```

```python
# In update — apply scroll
def update(self, dt: float) -> None:
    if self._scroll_dx != 0.0 or self._scroll_dy != 0.0:
        self.camera.scroll(self._scroll_dx * dt, self._scroll_dy * dt)
```

Plus two instance variables (`_scroll_dx`, `_scroll_dy`) initialised in
`on_enter` and reset in `on_exit`.

### Why it's friction

Arrow-key camera scrolling is the most common camera interaction for any
2D game with a world larger than the screen.  Every scene that uses a
camera will copy-paste this pattern.  The camera already has
`enable_edge_scroll()` for mouse-based scrolling — keyboard scrolling
should be just as easy to enable.

### Proposed fix

Add `Camera.enable_key_scroll(speed)` that integrates with the input
system automatically:

```python
self.camera = Camera(
    (SCREEN_W, SCREEN_H),
    world_bounds=(0, 0, MAP_WIDTH_PX, MAP_HEIGHT_PX),
)
self.camera.enable_key_scroll(speed=200)  # handles press/release/update internally
```

The camera already receives updates via the game loop.  It could listen
for directional actions and apply scrolling in its own update step,
eliminating the need for `_scroll_dx`/`_scroll_dy` state, the
`handle_input` dispatch, and the `update` override in the scene.

---

## 6. Label styling requires a Style object even for just a color change

### The awkward code

Almost every label in the tutorials wraps a `Style(...)` just to set
one or two fields:

```python
Label(
    "Wave: 1",
    style=Style(font_size=20, text_color=HUD_TEXT_COLOR),
)

Label(
    "Arrow keys: scroll | ESC: menu",
    style=Style(font_size=14, text_color=(140, 140, 150, 255)),
)

Label(
    "Tower Defense",
    style=Style(font_size=48, text_color=TITLE_COLOR),
)
```

ch3's `_build_menu` alone creates 7 labels, each with
`style=Style(font_size=..., text_color=...)`.  The `Style` wrapper adds
noise for what is logically "display this text in this color at this
size".

### Why it's friction

Labels are the most commonly created UI component.  Requiring a `Style`
object for the two most common overrides (font_size, text_color) makes
label-heavy UIs verbose.  `Style` is valuable for complex customization,
but the 90% case is just size and color.

### Proposed fix

Accept `font_size` and `text_color` as direct keyword arguments on
`Label` (and `Button`), forwarded into `Style` internally:

```python
Label("Wave: 1", font_size=20, text_color=HUD_TEXT_COLOR)
Label("Tower Defense", font_size=48, text_color=TITLE_COLOR)
```

The explicit `style=Style(...)` form would still work for less common
fields (padding, background_color, border, etc.).

---

## 7. screen_to_world conversion is always needed but never automatic for mouse events

### The awkward code

In ch3, every mouse event handler must manually convert screen
coordinates to world coordinates:

```python
# Left-click placement
if event.type == "click" and event.button == "left":
    if self._placing_tower_def is not None:
        wx, wy = self.camera.screen_to_world(event.x, event.y)
        self._try_place_tower(wx, wy)

# Mouse movement
if event.type in ("move", "drag"):
    if self._placing_tower_def is not None:
        wx, wy = self.camera.screen_to_world(event.x, event.y)
        snap = self._snap_to_nearest_slot(wx, wy)
```

Every mouse handler that interacts with the game world (not UI) needs
this same `camera.screen_to_world(event.x, event.y)` call.

### Why it's friction

`InputEvent` arrives in screen space, but game logic (hit testing,
placement, selection, movement commands) almost always needs world space.
The conversion is trivial but forgetting it produces subtle bugs — the
game works until the camera scrolls, then clicks land in wrong positions.
This is a classic "works in testing, breaks in production" mistake.

### Proposed fix

Add `world_x` / `world_y` properties to `InputEvent` (or to the scene's
handle_input protocol) that auto-convert when a scene has a camera:

```python
# InputEvent gains world coords (None if no camera)
def handle_input(self, event: InputEvent) -> bool:
    if event.type == "click":
        self._try_place_tower(event.world_x, event.world_y)
```

The framework already knows the active scene's camera at dispatch time
(in `Game.tick`).  It could populate `world_x`/`world_y` before
dispatching to `handle_input`, or `InputEvent` could lazily compute them
from a camera reference.

---

## Summary

| # | Friction | Severity | Fix complexity |
|---|----------|----------|----------------|
| 1 | Background color requires backend calls | High | Low — class attr + lifecycle hook |
| 2 | Manual sprite cleanup in on_exit | High | Medium — scene-owned sprite tracking |
| 3 | AssetManager constructed separately | Medium | Low — Game constructor parameter |
| 4 | No visual feedback for disabled buttons | Medium | Low — "disabled" style state |
| 5 | Arrow-key scrolling boilerplate | Medium | Low — Camera.enable_key_scroll() |
| 6 | Label styling verbosity | Low | Low — forwarded kwargs |
| 7 | Manual screen-to-world conversion | Medium | Medium — auto-populated event fields |
