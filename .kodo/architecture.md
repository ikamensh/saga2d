# EasyGame Architecture

## Overview

EasyGame is a 2D sprite-based Python game framework. The backend protocol isolates all rendering/audio/input behind an interface so tests run headlessly. The mock backend and pytest fixtures enable frame-by-frame deterministic testing without a window.

## Progress

- **Stage 0: COMPLETE** (19→26 tests) — Mock backend, test harness, Game, Scene, SceneStack
- **Stage 1: COMPLETE** (26 tests pass) — PygletBackend, real window, game loop, transparency culling, run() cleanup
- **Stage 2: COMPLETE** (81 tests pass: 26 stages 0-1 + 13 asset + 42 sprite) — Assets & Sprites
- **Stage 3: COMPLETE** (131 tests pass: 81 prior + 26 animation + 21 sprite-animation + 3 new asset) — Animation
- **Stage 4+5: COMPLETE** (186 tests pass: 131 prior + 10 timer + 14 tween + 30 input + 1 visual) — Timers, Tweens & Input
- **Stage 6: COMPLETE** (217 tests pass: 186 prior + 31 battle vignette) — Battle Vignette Demo
- **Stage 7: COMPLETE** (219 tests pass: 217 prior + 2 refinement) — Demo Retrospective & Framework Refinements

## Implemented File Structure

```
easy_game/
  easygame/
    __init__.py              # Re-exports: Game, Scene, Sprite, AnimationDef, RenderLayer,
                             #   SpriteAnchor, AssetManager, AssetNotFoundError, Ease, tween,
                             #   InputEvent, Event types
    game.py                  # Game class, owns backend + scene stack + assets + timers + tweens + input + animated sprites
    scene.py                 # Scene base class, SceneStack with transparency culling
    animation.py             # AnimationDef (public), AnimationPlayer (internal)
    assets.py                # AssetManager: convention-based loading, caching, @2x variants, frames()
    input.py                 # InputEvent (public), InputManager (internal, game.input)
    util/
      __init__.py            # Package docstring
      timer.py               # TimerManager (internal, game.after/every/cancel)
      tween.py               # TweenManager (internal), tween() (public), Ease enum (public)
    rendering/
      __init__.py            # Re-exports: Sprite, RenderLayer, SpriteAnchor
      layers.py              # RenderLayer (IntEnum), SpriteAnchor (Enum)
      sprite.py              # Sprite class (position, opacity, layer, anchor, animation, move_to, backend sync)
    backends/
      __init__.py            # Re-exports Protocol, events, handles, MockBackend
      base.py                # Backend Protocol, event dataclasses, opaque handle types
      mock_backend.py        # Records all operations, injects events, no rendering
      pyglet_backend.py      # GPU-accelerated rendering via pyglet 2.x
  tests/
    __init__.py
    conftest.py              # pytest fixtures: mock_game, mock_backend; collect_ignore=["tests/visual"]
    test_scene.py            # 19 tests: lifecycle, deferred ops, transparency culling
    test_game.py             # 7 tests: input dispatch, quit, tick, run loop, window close
    test_assets.py           # 16 tests: loading, caching, @2x variants, errors, Game.assets, frames()
    test_sprite.py           # 42 tests: creation, anchors, position, y-sort, opacity, removal
    test_animation.py        # 26 tests: AnimationDef, AnimationPlayer construction/update/loop/oneshot
    test_sprite_animation.py # 21 tests: play/queue/stop, auto-update, queue chaining, removal cleanup
    test_timer.py            # 10 tests: after, every, cancel, cancel_during_callback, nested creation
    test_tween.py            # 14 tests: tween basics, easing, sprite integration, move_to
    test_input.py            # 30 tests: InputEvent, defaults, translate, bind/unbind, game integration
    test_battle_vignette.py  # 31 tests: headless battle demo choreography, selection, death, multi-round
    visual/
      __init__.py
      test_stage1_visual.py  # Manual visual test: scene push/pop with colored backgrounds
      test_stage3_visual.py  # Manual visual test: animated sprite playback
      test_stage45_visual.py # Manual visual test: sliding/fading, click-to-move, action bindings, timer
  examples/
    battle_vignette/
      battle_demo.py         # Runnable 3v3 battle demo (BattleScene, Unit, _FloatingNumber)
      generate_assets.py     # Pillow-generated sprites for warriors, skeletons, selection ring
      README.md              # Controls and observation notes
      assets/images/sprites/ # 20 PNGs (warrior/skeleton anims + select_ring)
```

## Key Decisions

### 1. Backend Protocol — Structural Subtyping (`backends/base.py`)

`typing.Protocol`, not ABC. Backends don't inherit — they implement the same method signatures. Full protocol defined upfront in Stage 0; MockBackend and PygletBackend both implement all methods.

### 2. Event Types — Frozen Dataclasses

```python
KeyEvent(type: str, key: str)              # "key_press"/"key_release"
MouseEvent(type: str, x, y, button, dx, dy)  # "click"/"release"/"move"/"drag"/"scroll"
WindowEvent(type: str)                     # "close"/"resize"
Event = KeyEvent | MouseEvent | WindowEvent
```

**Stage 1 addition:** `MouseEvent.type` now includes `"release"` (mouse button up), added for PygletBackend's `on_mouse_release` handler. The docstring and type comment in `base.py` were updated.

### 3. Opaque Handle Types

`ImageHandle = Any`, `SoundHandle = Any`, `FontHandle = Any`. Mock uses string IDs; pyglet uses real pyglet objects.

### 4. Game.tick() — Three-Phase Deferred Flush

```
tick(dt):
  events = backend.poll_events()
  filter out WindowEvent("close") → game.quit()                  # Stage 4+5
  input_events = input_manager.translate(non_window_events)      # Stage 4+5
  begin_tick → handle_input(InputEvent) for each event → flush_pending_ops
  begin_tick → scene_stack.update(dt) → flush_pending_ops
  _timer_manager.update(dt)                                      # Stage 4+5
  _tween_manager.update(dt)                                      # Stage 4+5
  _update_animations(dt)                                         # Stage 3
  backend.begin_frame() → scene_stack.draw() → backend.end_frame()
```

WindowEvent("close") is intercepted by the framework and calls `game.quit()` before scene dispatch.

### 5. Game.run() Calls backend.quit() on Exit

`run()` pushes the start scene, loops `tick()` while `self.running`, then calls `self._backend.quit()` to tear down the window. This ensures pyglet window is closed and resources released even if the scene forgets to clean up.

### 6. SceneStack.draw() — Transparency Culling (Stage 1)

Walks the stack from top downward. Stops at the first opaque scene (`transparent=False`, the default). Draws from that scene upward. Opaque scenes below the topmost opaque scene are never drawn.

```python
start = len(self._stack) - 1
while start > 0 and self._stack[start].transparent:
    start -= 1
for i in range(start, len(self._stack)):
    self._stack[i].draw()
```

Symmetric with `update()` which already did the same walk for `pause_below`.

### 7. Scene.draw() Has No Args

Kept `draw(self)` with no DrawContext parameter. Scenes access drawing through `self.game.backend` directly. DESIGN.md shows `draw(self, ctx: DrawContext)` — we intentionally departed from this because there's no DrawContext needed yet.

### 8. on_exit Fires on Both Pop AND Cover

`push(B)` while A is top → `A.on_exit()`. `pop()` of B → `B.on_exit()`. No separate `on_pause` hook.

### 9. Deferred Pyglet Imports

PygletBackend defers all `import pyglet` calls into method bodies or `if TYPE_CHECKING` blocks. This prevents pyglet from creating a shadow window on import (pyglet initializes OpenGL context on first import of certain modules). Tests that use `backend="mock"` never trigger any pyglet import.

### 10. Visual Tests Excluded from pytest Collection

`conftest.py` sets `collect_ignore = ["tests/visual"]` so `pytest tests/` never tries to import pyglet. Visual tests live in `tests/visual/` and are run manually:

```bash
PYTHONPATH=. python tests/visual/test_stage1_visual.py
```

### 11. Module-Level `_current_game` for Sprite → Game Linkage (Stage 2)

`Sprite` needs access to `game.backend` and `game.assets` at construction time, but the public API is `Sprite("name", position=(...))` with no explicit `game` parameter.

Solution: `rendering/sprite.py` has a module-level `_current_game: Any = None`. `Game.__init__()` sets it:

```python
import easygame.rendering.sprite as _sprite_mod
_sprite_mod._current_game = self
```

Sprite's `__init__` reads this reference once and caches `self._backend = game.backend`. Raises `RuntimeError("No active Game")` if called before any Game is created.

**Why module-level, not `easygame._current_game`:** Avoids circular imports. The `game.py` module imports `easygame.rendering.sprite` (a leaf module) — safe. If it set `easygame._current_game` instead, that would create an import cycle through `__init__.py`.

### 12. Y-Sort Draw Order Formula (Stage 2)

```python
order = layer.value * 100_000 + int(y)
```

- `RenderLayer` is an `IntEnum` (BACKGROUND=0, OBJECTS=1, UNITS=2, EFFECTS=3, UI_WORLD=4).
- Multiplying by 100,000 guarantees layer separation (supports y values up to 99,999).
- Higher y (further down screen) → larger order → drawn later → appears in front. Correct for top-down 2D games.
- Called at Sprite creation and on every position change via `backend.set_sprite_order()`.

### 13. Anchor Offset Computation (Stage 2)

The anchor determines the offset from the sprite's logical position to the top-left draw corner passed to the backend:

```python
# For BOTTOM_CENTER with a 64x64 image at position (400, 300):
# dx = 32 (half width), dy = 64 (full height)
# draw_x = 400 - 32 = 368, draw_y = 300 - 64 = 236
backend.update_sprite(sid, 368, 236)
```

The Sprite class caches image dimensions from `backend.get_image_size()` at creation time and calls `_anchor_offset()` on every sync. Both backends receive **anchor-adjusted logical coords** — PygletBackend then applies its own `_to_physical()` y-flip and scaling.

### 14. AssetManager — Lazy Creation, Convention-Based Loading (Stage 2)

`Game.assets` is a lazy property that creates `AssetManager(backend, base_path=Path("assets"), scale_factor=...)` on first access. Can be overridden via setter (useful in tests to point at `tmp_path`).

AssetManager resolves names by convention:
- `image("sprites/knight")` → `<base_path>/images/sprites/knight.png`
- `.png` appended automatically if no extension given.
- Explicit extensions work too: `image("backgrounds/forest.jpg")`.

**@2x variant support:** When `scale_factor >= 1.5`, tries `knight@2x.png` first; falls back to `knight.png` if not found. Implemented via `_make_2x_path()` using `Path.with_stem()`.

**Caching:** `_image_cache: dict[str, Any]` keyed by asset name (not path). Same name always returns the same handle.

**Error handling:** `AssetNotFoundError(FileNotFoundError)` with a message listing all attempted paths.

### 15. Sprite Property Setters Auto-Sync to Backend (Stage 2)

Every visual property setter on `Sprite` immediately pushes state to the backend:

```python
sprite.position = (500, 350)  # → _sync_to_backend() + set_sprite_order()
sprite.opacity = 128          # → _sync_to_backend()
sprite.visible = False        # → _sync_to_backend()
```

`_sync_to_backend()` is guarded by `if self._removed: return` so updates after removal are no-ops. The `position` setter additionally calls `set_sprite_order()` (also guarded) to update y-sort order.

`sprite.remove()` calls `backend.remove_sprite()` once, sets `self._removed = True`, and is safe to call multiple times.

## Existing Backend Protocol (`backends/base.py`)

The full protocol is defined. Key method groups:

**Lifecycle** (Stage 0-1, exercised):
- `create_window(width, height, title, fullscreen)` → None
- `begin_frame()` / `end_frame()` → None
- `poll_events()` → list[Event]
- `get_display_info()` → (int, int)
- `get_dt()` → float
- `quit()` → None

**Sprite rendering** (Stage 2, exercised):
- `load_image(path: str)` → ImageHandle
- `create_sprite(image_handle, layer_order: int)` → sprite_id (Any)
- `update_sprite(sprite_id, x, y, *, image=None, opacity=255, visible=True)` → None
- `remove_sprite(sprite_id)` → None
- `get_image_size(image_handle)` → (int, int) — **added in Stage 2**
- `set_sprite_order(sprite_id, order: int)` → None — **added in Stage 2**

**Text rendering** (defined, both implement):
- `load_font(name, size)` → FontHandle
- `draw_text(text, font_handle, x, y, color, *, width=None, align="left")` → None

**Audio** (defined, both implement):
- `load_sound(path)` / `play_sound(handle, volume=1.0)` → None
- `load_music(path)` / `play_music(handle, *, loop=True, volume=1.0)` → player_id
- `set_player_volume(player_id, volume)` / `stop_player(player_id)` → None

## How MockBackend Records Operations

MockBackend stores all state as plain dicts/lists for test assertions:

- `self.sprites: dict[str, dict]` — `sprite_id → {"image", "x", "y", "opacity", "visible", "layer"}`
- `self.texts: list[dict]` — per-frame text draw calls (cleared on `begin_frame()`)
- `self.frame_count: int` — incremented on `end_frame()`
- `self.sounds_played: list[str]` — cumulative sound play log
- `self.music_playing: str | None` — current music handle
- `self._loaded_images: dict[str, str]` — path → handle cache
- `self._next_id: int` — monotonic counter for `_make_id(prefix)` → `"sprite_7"`, `"img_3"`, etc.

**Stage 2 additions:**
- `self._default_image_size: tuple[int, int] = (64, 64)` — default for `get_image_size()`
- `self._image_sizes: dict[str, tuple[int, int]]` — per-handle overrides
- `get_image_size(handle)` → returns override or default `(64, 64)`
- `set_sprite_order(sprite_id, order)` → updates `sprites[id]["layer"]` (the "layer" key stores the *computed order*, not the RenderLayer enum value)
- `set_image_size(handle, w, h)` — test helper to control dimensions for anchor math tests

Event injection helpers: `inject_key()`, `inject_click()`, `inject_mouse_move()`, `inject_scroll()`, `inject_drag()`, `inject_window_event()`, `inject_event()`.

## How PygletBackend Is Structured

- **Persistent batch:** `self.batch = pyglet.graphics.Batch()` — created once in `create_window()`, never recreated.
- **Sprites:** `self._sprites: dict[int, pyglet.sprite.Sprite]` — persistent pyglet Sprite objects living in the batch. Each has a `pyglet.graphics.Group(order=layer_order)` for draw ordering.
- **Text labels:** `self._text_labels: list[pyglet.text.Label]` — per-frame. Created in `draw_text()`, deleted in next `begin_frame()`.
- **Coordinate conversion:** `_to_physical(lx, ly)` for all draw calls (y-flip + scale + offset). `_to_logical(px, py)` for all mouse events. `_compute_viewport()` handles letterbox/pillarbox.
- **`create_sprite()` uses `pyglet.graphics.Group(order=layer_order)`** — the `order` parameter determines draw sequence within the batch.
- **Non-protocol helper:** `create_solid_color_image(r, g, b, a, width, height)` — for visual demos only.

**Stage 2 additions:**
- `get_image_size(handle)` → `(handle.width, handle.height)` — pyglet images have native `.width`/`.height`.
- `set_sprite_order(sprite_id, order)` → creates new `pyglet.graphics.Group(order=order)` and reassigns to sprite. Group.order is not mutated in-place because pyglet Group immutability varies by version.

### Coordinate System

**Y-axis flip** (pyglet = bottom-left origin, framework = top-left origin) + **scale + offset** (logical → physical with letterbox/pillarbox).

```python
def _to_physical(self, lx, ly):
    px = lx * self.scale_factor + self.offset_x
    py = (self.logical_height - ly) * self.scale_factor + self.offset_y
    return px, py

def _to_logical(self, px, py):
    lx = (px - self.offset_x) / self.scale_factor
    ly = self.logical_height - (py - self.offset_y) / self.scale_factor
    return int(lx), int(ly)
```

**Important:** PygletBackend.update_sprite() calls `_to_physical()` on the x,y it receives (pyglet_backend.py line 365). MockBackend stores raw x,y (mock_backend.py line 190-191). The Sprite class passes **anchor-adjusted logical** coords to `backend.update_sprite()` — both backends accept logical coords.

### Event Handlers

Registered once in `create_window()`. Key symbols converted via `pyglet.window.key.symbol_string(symbol).lower()` with manual overrides (digit keys → `"0"`-`"9"`, `ENTER` → `"return"`). Mouse buttons via constant comparison (`LEFT`→`"left"`, etc.). Drag events use `_buttons_to_name()` bitmask decoder.

**on_close** returns `pyglet.event.EVENT_HANDLED` to prevent pyglet from destroying the window. The framework handles quit through the event queue → `Game.quit()` path.

### 16. AnimationDef at `easygame/animation.py` (Stage 3)

Placed at package top-level, not inside `rendering/`. AnimationDef is a public API class (re-exported from `easygame`), like Game and Scene. AnimationPlayer is internal but co-located for cohesion. Import: `from easygame.animation import AnimationDef`.

### 17. Game-Owned Automatic Animation Updates (Stage 3)

`Game._animated_sprites: set` tracks all sprites with active animations. `Sprite.play()` registers; `stop_animation()` and `remove()` deregister. `Game._update_animations(dt)` iterates a `list()` copy (mutation-safe) and calls `sprite.update_animation(dt)` on each. Placed in `tick()` between scene update flush and draw phase.

### 18. Sprite Caches `_assets` and `_game` References (Stage 3)

`Sprite.__init__` now caches `self._assets = game.assets` and `self._game = game` in addition to `self._backend`. `_assets` is needed for frame name resolution in `play()`. `_game` is needed for `_animated_sprites` registration/deregistration.

### 19. AssetManager.frames() — Discovery vs. Loading Separation (Stage 3)

`frames(prefix)` discovers numbered files via glob (`{prefix}_*.png`), sorts by numeric suffix, and returns `list[str]` (asset names). Does NOT return handles — caller uses `image(name)`. Cached in `_frames_cache: dict[str, list[str]]`. Raises `AssetNotFoundError` if no files match.

## Component Boundaries

| Component | Owns | Does NOT own |
|---|---|---|
| `Game` | backend, scene_stack, running flag, assets (lazy), timers, tweens, input, `_animated_sprites` set, tick/run | audio (later stages) |
| `SceneStack` | stack list, lifecycle dispatch, deferred ops, draw culling | update systems |
| `Scene` | its own state, lifecycle hooks | game reference (set externally) |
| `Sprite` | backend sprite_id, position/opacity/visible state, anchor offset, animation state (`_anim_player`, `_anim_queue`) | image data, batch membership (backend owns) |
| `AnimationDef` | frame names/prefix, frame_duration, loop flag | image handles (resolved at play time) |
| `AnimationPlayer` | per-sprite playback state (`_frame_index`, `_elapsed`, `_finished`), `on_complete` | sprite reference, asset resolution |
| `AssetManager` | image cache, frames cache, path resolution, @2x logic, `frames()` discovery | backend loading (delegates to backend) |
| `MockBackend` | recorded state, event queue, image size tracking | any real rendering |
| `PygletBackend` | pyglet window, batch, event handlers, coord conversion, sprite/label tracking | game logic, scene management |
| `base.py` | Protocol definition, Event dataclasses, handle type aliases | any implementation |

## Constraints & Gotchas

1. **No pyglet import at module level.** Deferred inside `if backend == "pyglet"` in Game and inside method bodies in PygletBackend.
2. **Scene.game must be set before on_enter().** SceneStack sets it during push().
3. **Empty stack is valid.** `tick()` doesn't crash — skips update/draw.
4. **`from __future__ import annotations`** used consistently in all files.
5. **Key name consistency.** Mock's `inject_key("space")` must match PygletBackend's `_symbol_to_name()` output. Mismatches cause silent input dispatch failures.
6. **Text labels are per-frame.** PygletBackend deletes them each `begin_frame()`. Sprites are persistent. This distinction matters for performance.
7. **on_close must not let pyglet close the window.** Must return `EVENT_HANDLED`. The framework owns the quit lifecycle.
8. **Public API re-exports from `easygame` and `easygame.ui` only.** Users never import from `easygame.backends` or internal modules. New public classes must be added to `easygame/__init__.py __all__`.
9. **MockBackend "layer" key stores computed order, not RenderLayer.** `sprites[id]["layer"]` holds `layer.value * 100_000 + int(y)`, not the `RenderLayer` enum. This is because `set_sprite_order()` overwrites the initial `layer_order` from `create_sprite()`. Tests assert on the computed value.
10. **Sprite removal guard pattern.** All Sprite setters go through `_sync_to_backend()` which checks `self._removed`. The position setter also guards `set_sprite_order()` separately. Double `remove()` is safe — only the first call has effect.
11. **AssetManager cache key is the asset name, not the resolved path.** `image("sprites/knight")` and `image("sprites/knight.png")` are different cache entries. This is intentional — callers should be consistent with names.
12. **`_current_game` is per-module, not per-thread.** Only one Game instance should exist at a time. Creating a second Game overwrites the reference. This is acceptable for single-window games.
13. **Animation `on_complete` fires at most once.** For looping animations, `on_complete` is never called (passed as `None` to AnimationPlayer). For one-shot, fires when last frame's duration elapses.
14. **`_animated_sprites` is a `set`.** `play()` calls `add()` — safe to call multiple times. `stop_animation()` and `remove()` call `discard()`. `_update_animations()` iterates a `list()` copy to handle mutation during iteration.
15. **`_sync_to_backend()` accepts optional `image` kwarg.** Animation frame changes pass `image=new_handle` through this method. Without the kwarg, image is not changed (regular position/opacity updates).
16. **`frames()` returns names, not handles.** `AssetManager.frames(prefix)` returns `list[str]` (asset names). Caller must use `image(name)` to get handles. This preserves the caching layer.
17. **`conftest.py` collect_ignore uses `"tests/visual"`** (not `"visual"`). The path is relative to the project root, not to the tests directory.

## Lessons Learned

### Stage 0

1. **Full protocol upfront was the right call.** Workers can call `backend.create_sprite()` / `backend.play_sound()` immediately.
2. **Two-phase deferred flush is subtle but correct.** Prevents spurious update after push during handle_input.
3. **`clear_and_push` calls on_exit in reverse order** (top-to-bottom).

### Stage 1

1. **Deferred pyglet imports are essential.** Early attempts imported pyglet at module level in `pyglet_backend.py`, which caused a shadow window to flash during import even when the mock backend was selected. Moving all imports into method bodies fixed this.
2. **`collect_ignore` for visual tests.** Without it, `pytest tests/` would try to import pyglet and fail in headless CI. Putting visual tests in `tests/visual/` with `collect_ignore = ["visual"]` keeps the test suite clean.
3. **PygletBackend rendering is already functional.** Even though Stage 1 only requires lifecycle/events, the rendering and audio stubs were implemented as real pyglet calls. This means Stage 2+ can use them immediately without touching `pyglet_backend.py` for basic sprite/text operations.
4. **`MouseEvent.type = "release"` was added.** Original Stage 0 only had "click" (press). PygletBackend's `on_mouse_release` handler needed a corresponding event type for completeness. The protocol docstring was updated.
5. **Transparency culling tests replaced the old `test_draw_calls_all_scenes_bottom_up` test** which asserted both scenes were drawn. Now 5 draw tests cover: opaque-only, transparent shows below, chain through transparent, all transparent, single scene.

### Stage 2 & 3

1. **Module-level `_current_game` reference works cleanly.** Avoids circular imports (game.py → rendering/sprite.py, a leaf module). Sprite tests that need to test "no game" temporarily set `_current_game = None` and restore it in a try/finally.
2. **Lazy `Game.assets` property was the right pattern.** Keeps `Game.__init__()` simple. Tests override `game.assets` with a custom `AssetManager` pointing at `tmp_path` — no real filesystem needed.
3. **`AssetManager.scale_factor` is keyword-only** (`*` in constructor). Prevents positional mixups. `Game.assets` getter reads `backend.scale_factor` via `getattr(..., 1.0)` for duck-type safety with custom backends.
4. **MockBackend default image size `(64, 64)` simplifies most tests.** Only tests that verify anchor math with non-square images use `set_image_size()`. The default makes simple creation/position tests work without setup.
5. **`set_sprite_order` creates a new Group in PygletBackend** rather than mutating `Group.order`. This avoids relying on pyglet internals about Group immutability.
6. **All 9 SpriteAnchor variants are tested.** Each gets its own unit test for offset math, plus integration tests verifying draw positions. This prevents anchor regressions when the formula changes.
7. **The `rendering/` package separates concerns.** `layers.py` (pure enums, no dependencies) is a leaf. `sprite.py` depends on `layers.py` and the backend. `__init__.py` re-exports everything. Later stages (Animation, Particles) will add files to `rendering/` without touching existing code.
8. **Sprite fixture pattern in tests:** The `game` fixture creates a `Game(backend="mock")`, then overrides `game.assets` with an `AssetManager` pointing at `tmp_path`. The `backend` fixture extracts `game.backend`. This keeps test setup minimal and consistent.
9. **`animation.py` at top-level, not in `rendering/`.** The plan said `easygame/rendering/animation.py`. Implementation placed it at `easygame/animation.py` instead. This makes more sense — AnimationDef is a public API concept (like Scene, Game), not a rendering internal. AnimationPlayer is co-located for cohesion.
10. **`_sync_to_backend(image=...)` was the right extension point.** Rather than having animation code call `backend.update_sprite()` directly, extending the existing sync method keeps all backend communication in one place and preserves the removal guard pattern.
11. **`conftest.py` collect_ignore path matters.** Changed from `["visual"]` to `["tests/visual"]` — the path is relative to the project root. Getting this wrong causes pytest to silently import pyglet test files.
12. **`frames()` returns names, not handles — correct separation.** Early plan drafts had it returning handles. Returning names (str) preserves the existing `image()` caching layer and keeps AssetManager's concerns clean: discovery vs. loading are separate operations.
13. **Queue drain via wrapped `on_complete` is elegant.** `play()` wraps the user's callback to call `_drain_queue()` after it fires. This makes queue chaining invisible to game code — no special "queue finished" event needed.

---

## Stage 3 — Animation (COMPLETE)

### What Was Built

Reusable animation templates (`AnimationDef`), per-sprite playback state (`AnimationPlayer`), sprite sheet frame discovery (`AssetManager.frames()`), and automatic game loop integration. 131 tests pass (50 new).

### Key Decisions

| Decision | Choice | Rationale |
|---|---|---|
| `animation.py` lives at `easygame/animation.py` | Top-level, not `rendering/` | AnimationDef is a public API class re-exported from `easygame`. AnimationPlayer is internal but co-located with AnimationDef for cohesion. |
| AnimationDef holds names, not handles | `frames: list[str] \| str` | Defs can be created before Game/assets exist. Handles resolved at `play()` time. |
| AnimationPlayer is internal | Not re-exported | Users interact via `Sprite.play()/queue()`. Player is implementation detail. |
| Animation updates are automatic | Game-owned `_animated_sprites: set` | `Sprite.play()` registers; `stop_animation()`/`remove()` deregister. No manual `update_animation()` call needed. |
| Animation phase after update, before draw | `tick()` order: input → update → **animate** → draw | Scene logic runs first (may trigger `play()`), then frames advance, then draw sees final state. |
| `frames()` returns names, not handles | `list[str]` | Preserves caching layer — caller uses `image(name)` to get handles. |
| `_sync_to_backend()` extended with `image` kwarg | `*, image: Any \| None = None` | Keeps all backend updates in one method. Animation frame changes pass `image=new_handle`. |
| `on_complete` wrapping for queue drain | Wrapped callback in `play()` | User callback fires first, then `_drain_queue()` auto-advances. Looping animations pass `on_complete=None` to AnimationPlayer. |

### Implementation Notes

- **AnimationDef uses `__slots__`** for memory efficiency (many defs may exist).
- **AnimationPlayer.update(dt)** uses a `while` loop to handle large dt values (multiple frame skips). Returns new handle only if frame index actually changed.
- **Sprite caches `self._assets` and `self._game`** in `__init__` (same pattern as `self._backend`). `_game` needed for `_animated_sprites` registration.
- **`_set_image(handle)`** recaches `_img_w, _img_h` from backend and calls `_sync_to_backend(image=handle)`. Ensures anchor offsets correct even if frames have different sizes.
- **`remove()` cleanup**: clears `_anim_player`, empties `_anim_queue`, calls `_game._animated_sprites.discard(self)`.
- **`frames()` discovery**: globs `{prefix}_*.png`, sorts by numeric suffix via `int(p.stem.rsplit("_", 1)[-1])`, caches in `_frames_cache: dict[str, list[str]]`.
- **No backend protocol changes needed.** `update_sprite(image=...)` kwarg already existed in both backends.

---

## Stage 4+5 — Timers, Tweens & Input (COMPLETE)

These three systems are parallel in the dependency graph (all depend on Stage 1's game loop, not on each other) so they form one implementation stage. Each is a self-contained module in `easygame/util/` (timers, tweens) or `easygame/` (input). The combined stage adds `game.after()`, `game.every()`, `game.cancel()`, `tween()`, `Sprite.move_to()`, and `game.input` with action mapping.

### Files to Create

```
easygame/
    util/
        __init__.py       # empty or re-exports
        timer.py          # TimerManager (internal), Timer namedtuple
        tween.py          # TweenManager (internal), tween(), Ease enum
    input.py              # InputManager, InputEvent
```

### Game Loop Integration — Updated `tick()` Order

```
tick(dt):
  events = backend.poll_events()
  translated_events = input_manager.translate(events)       # NEW: Stage 5
  begin_tick → handle_input(translated_events) → flush
  begin_tick → scene_stack.update(dt) → flush
  _update_timers(dt)                                        # NEW: Stage 4
  _update_tweens(dt)                                        # NEW: Stage 4
  _update_animations(dt)                                    # existing Stage 3
  backend.begin_frame() → scene_stack.draw() → backend.end_frame()
```

**Rationale for ordering:**
1. **Input translation happens first**, before event dispatch. The InputManager wraps raw `KeyEvent`/`MouseEvent` into `InputEvent` with `.action` field. Scene `handle_input()` receives `InputEvent` instead of raw events. Mouse events pass through with coordinates already in logical space (backend already converts).
2. **Timers update after scene update** — scene logic runs first (may create/cancel timers), then timer callbacks fire. This prevents a timer created during `update()` from firing in the same frame.
3. **Tweens update after timers** — timer callbacks may create tweens. Tweens update property values which may trigger backend syncs (e.g. sprite position). This must complete before animation updates re-cache image handles.
4. **Animations remain last** before draw — unchanged from Stage 3.

**All three update phases iterate copies** of their active collections. Callbacks may create/cancel timers, create/cancel tweens, or trigger animations during iteration.

---

### 20. TimerManager (`easygame/util/timer.py`)

**Location:** `easygame/util/timer.py`. Internal class — users interact via `game.after()`, `game.every()`, `game.cancel()`. Not re-exported from `easygame`.

**Timer ID type:** Opaque `int` from a monotonic counter (`_next_id`). Users receive it from `after()`/`every()` and pass it back to `cancel()`. No special TimerId type — plain `int` is sufficient and JSON-serializable (useful for save/load later).

```python
class TimerManager:
    def __init__(self) -> None:
        self._timers: dict[int, _Timer] = {}
        self._next_id: int = 0

    def after(self, delay: float, callback: Callable[[], Any]) -> int: ...
    def every(self, interval: float, callback: Callable[[], Any]) -> int: ...
    def cancel(self, timer_id: int) -> None: ...
    def update(self, dt: float) -> None: ...
    def cancel_all(self) -> None: ...
```

**`_Timer` internal dataclass:**
```python
@dataclass
class _Timer:
    callback: Callable[[], Any]
    remaining: float        # seconds until next fire
    interval: float | None  # None for one-shot, >0 for repeating
    cancelled: bool = False
```

**Safe iteration during update:**
- `update(dt)` iterates `list(self._timers.values())` — a snapshot copy.
- Fired one-shot timers are removed from `_timers` after the iteration completes.
- Callbacks that call `cancel()` on other timers mark them `cancelled=True` (checked before firing).
- Callbacks that call `after()`/`every()` add to `_timers` safely (new entries not in the snapshot).
- Repeating timers reset `remaining = interval` after firing, handling accumulated time (if `remaining` goes negative, fires once and carries the deficit forward — no multi-fire catch-up to avoid callback storms).

**Game integration:**
- `Game.__init__()` creates `self._timer_manager = TimerManager()`.
- `Game.after(delay, callback)` → delegates to `self._timer_manager.after(...)`.
- `Game.every(interval, callback)` → delegates to `self._timer_manager.every(...)`.
- `Game.cancel(timer_id)` → delegates to `self._timer_manager.cancel(...)`.
- `Game.tick()` calls `self._timer_manager.update(dt)` in the update phase.

**Why no `pause()`/`resume()` on timers:** YAGNI for now. Games can cancel and recreate. If needed later, add `_Timer.paused: bool` flag.

---

### 21. TweenManager and `tween()` (`easygame/util/tween.py`)

**Location:** `easygame/util/tween.py`. The module-level `tween()` function is the public API — re-exported from `easygame`. `TweenManager` and `Ease` enum are also public. `_Tween` internal dataclass is not exported.

**Public API:**
```python
class Ease(Enum):
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"

def tween(
    target: Any,
    prop: str,
    from_val: float,
    to_val: float,
    duration: float,
    *,
    ease: Ease = Ease.LINEAR,
    on_complete: Callable[[], Any] | None = None,
) -> int:
    """Create a tween. Returns tween_id for cancellation."""
```

**How `tween()` finds the TweenManager:** Same pattern as Sprite finding `_current_game`. Module-level `_tween_manager: TweenManager | None = None` set by `Game.__init__()`. The `tween()` function reads this reference. Raises `RuntimeError` if called before Game exists.

**Alternative considered: `game.tween()` method.** Rejected because DESIGN.md shows `tween(sprite, "x", ...)` as a free function, and the Actions system (Stage 10) will call `tween()` from `MoveTo`/`FadeOut` action classes that don't have a `game` reference. A module-level function with an implicit manager is cleaner than threading `game` through every action.

**Easing functions:** Quadratic for all four. Implemented as pure functions `_ease_linear(t)`, `_ease_in(t)`, `_ease_out(t)`, `_ease_in_out(t)` where `t` is 0.0..1.0 normalized progress. Map stored in a dict `_EASE_FNS: dict[Ease, Callable[[float], float]]`.

```python
def _ease_linear(t): return t
def _ease_in(t): return t * t
def _ease_out(t): return 1 - (1 - t) * (1 - t)
def _ease_in_out(t): return 2*t*t if t < 0.5 else 1 - (-2*t + 2)**2 / 2
```

**`_Tween` internal dataclass:**
```python
@dataclass
class _Tween:
    target: Any             # object whose property is being tweened
    prop: str               # attribute name (e.g. "x", "opacity")
    from_val: float
    to_val: float
    duration: float
    ease_fn: Callable[[float], float]
    on_complete: Callable[[], Any] | None
    elapsed: float = 0.0
    cancelled: bool = False
```

**TweenManager:**
```python
class TweenManager:
    def __init__(self) -> None:
        self._tweens: dict[int, _Tween] = {}
        self._next_id: int = 0

    def create(self, ...) -> int: ...
    def cancel(self, tween_id: int) -> None: ...
    def cancel_all(self) -> None: ...
    def update(self, dt: float) -> None: ...
```

**Safe iteration:** Same pattern as TimerManager — iterate `list(self._tweens.values())`, remove completed tweens after iteration. Callbacks may create new tweens or cancel existing ones.

**Property setting:** `setattr(tween.target, tween.prop, current_val)` each frame. This works because Sprite has property setters for `x`, `y`, `opacity` that auto-sync to the backend. When tweening `x`, the tween manager calls `sprite.x = new_val` which triggers `_sync_to_backend()` + `set_sprite_order()`.

**Completion:** When `elapsed >= duration`, clamp to `to_val`, set the property one final time, fire `on_complete`, and mark for removal.

**Game integration:**
- `Game.__init__()` creates `self._tween_manager = TweenManager()`.
- Sets module-level `_tween_manager` in `easygame/util/tween.py`.
- `Game.tick()` calls `self._tween_manager.update(dt)` in the update phase.
- `Game.cancel_tween(tween_id)` → delegates to `self._tween_manager.cancel(...)`.

---

### 22. `Sprite.move_to()` — Convenience Method

**Lives in:** `easygame/rendering/sprite.py` (extends Sprite class). Uses `tween()` internally.

```python
def move_to(
    self,
    target_pos: tuple[float, float],
    speed: float,
    *,
    ease: Ease = Ease.LINEAR,
    on_arrive: Callable[[], Any] | None = None,
) -> None:
```

**Implementation:**
1. Compute distance: `math.hypot(target_x - self._x, target_y - self._y)`.
2. Compute duration: `distance / speed`. If distance ≈ 0, fire `on_arrive` immediately and return.
3. Cancel any existing move tweens (tracked via `self._move_tween_ids: list[int]`).
4. Create two tweens: one for `x` (from current x to target x), one for `y` (from current y to target y), same duration and easing.
5. Only the y-tween gets `on_complete=on_arrive` (both tweens have the same duration, so the last one finishing triggers the callback). Alternative: use a counter — but since both tweens have identical duration, the y-tween always finishes at the same time or after the x-tween.
6. Store both tween IDs in `self._move_tween_ids` for cancellation.

**Why `speed` not `duration`:** DESIGN.md specifies `move_to(target_pos, speed=200)`. Speed is more intuitive for game code — a unit walks at 200 pixels/sec regardless of distance. Duration is computed internally.

**New move cancels previous move:** `move_to()` cancels `self._move_tween_ids` before creating new tweens. This prevents conflicting tweens on the same properties. The Sprite's `remove()` also cancels active move tweens.

**Sprite.remove() cleanup:** Must cancel move tweens via `_tween_manager.cancel()` in addition to existing animation cleanup.

---

### 23. InputManager (`easygame/input.py`)

**Location:** `easygame/input.py`. `InputManager` is internal (not re-exported). `InputEvent` is public — re-exported from `easygame`.

**InputEvent dataclass:**
```python
@dataclass(frozen=True)
class InputEvent:
    """Translated input event with optional action mapping.

    For keyboard events:
        type: "key_press" | "key_release"
        key: raw key string (e.g. "a", "space")
        action: mapped action string (e.g. "attack", "confirm") or None
    For mouse events:
        type: "click" | "release" | "move" | "drag" | "scroll"
        x, y: logical coordinates (already converted by backend)
        button: "left" | "right" | "middle" | None
        dx, dy: scroll/drag deltas
        action: None (mouse events don't map to actions)
    """
    type: str
    key: str | None = None
    action: str | None = None
    x: int = 0
    y: int = 0
    button: str | None = None
    dx: int = 0
    dy: int = 0
```

**Why a new event type instead of extending KeyEvent/MouseEvent:** KeyEvent and MouseEvent are frozen backend-level dataclasses. InputEvent is a framework-level concept that unifies keyboard and mouse into one type with an `.action` field. Scenes receive `InputEvent`, never raw `KeyEvent`/`MouseEvent`. This is a **breaking change to `Scene.handle_input()`** — the parameter type changes from `Event` (union) to `InputEvent`.

**Migration path:** Currently `Scene.handle_input(event: Event)` receives raw events. After Stage 5, it receives `InputEvent`. Existing scene code that checks `event.type == "key_press" and event.key == "a"` still works because `InputEvent` has both `.type` and `.key`. Code that checks `isinstance(event, KeyEvent)` must change to check `event.type`. This is acceptable — all existing tests use `.type` and `.key` checks, not `isinstance`.

**InputManager:**
```python
class InputManager:
    def __init__(self) -> None:
        self._key_to_action: dict[str, str] = {}   # key → action
        self._action_to_key: dict[str, str] = {}   # action → key (for display)
        self._setup_defaults()

    def bind(self, action: str, key: str) -> None: ...
    def unbind(self, action: str) -> None: ...
    def get_bindings(self) -> dict[str, str]: ...   # action → key
    def translate(self, events: list[Event]) -> list[InputEvent]: ...
```

**Default bindings** (from DESIGN.md):
```python
def _setup_defaults(self):
    self.bind("confirm", "return")
    self.bind("cancel", "escape")
    self.bind("up", "up")
    self.bind("down", "down")
    self.bind("left", "left")
    self.bind("right", "right")
```

**Note:** DESIGN.md says `"menu" → Escape` (same as cancel). We do NOT bind two actions to one key — that creates ambiguity. `"menu"` is omitted from defaults. Game code can `bind("menu", "escape")` if it wants, overriding cancel. Or use a different key.

**`translate()` method:**
- Iterates raw events from `backend.poll_events()`.
- `KeyEvent` → `InputEvent(type=event.type, key=event.key, action=self._key_to_action.get(event.key))`.
- `MouseEvent` → `InputEvent(type=event.type, x=event.x, y=event.y, button=event.button, dx=event.dx, dy=event.dy)`. Mouse coordinates are already in logical space (backend converts in `poll_events()`).
- `WindowEvent` → passed through as-is (NOT translated to InputEvent). `Game.tick()` still intercepts `WindowEvent("close")` before translation.

**Updated event dispatch in Game.tick():**
```python
# Input phase
raw_events = self._backend.poll_events()

# Intercept window events before translation
for event in raw_events:
    if isinstance(event, WindowEvent) and event.type == "close":
        self.quit()

# Translate remaining events
input_events = self._input.translate(
    [e for e in raw_events if not isinstance(e, WindowEvent)]
)

# Dispatch to scene
self._scene_stack.begin_tick()
for event in input_events:
    top = self._scene_stack.top()
    if top is not None:
        top.handle_input(event)
self._scene_stack.flush_pending_ops()
```

**Window events get filtered out before translation.** WindowEvent("close") is framework-handled. WindowEvent("resize") currently has no scene-level handler. When needed (Stage 8 UI), it can be translated into an InputEvent or handled by the framework directly.

**Game integration:**
- `Game.__init__()` creates `self._input = InputManager()`.
- `Game.input` property exposes it for `game.input.bind("attack", "a")`.
- `Game.tick()` translates events through InputManager before scene dispatch.

---

### 24. Public API Surface (Stage 4+5 Additions)

**`easygame` package (`__init__.py`):**
```python
# New exports:
from easygame.input import InputEvent
from easygame.util.tween import Ease, tween

# Updated __all__:
__all__ = [
    # ... existing ...
    "Ease",
    "InputEvent",
    "tween",
]
```

**What is NOT exported from `easygame`:**
- `TimerManager` — internal, accessed via `game.after()`/`game.every()`/`game.cancel()`.
- `TweenManager` — internal, accessed via `tween()` free function and `game.cancel_tween()`.
- `InputManager` — internal, accessed via `game.input` property.
- `_Timer`, `_Tween` — internal dataclasses.

**`easygame.ui` package:** No additions in this stage. `easygame.ui` does not exist yet (Stage 8).

**Game convenience methods (new):**
```python
game.after(delay, callback) -> int         # timer
game.every(interval, callback) -> int      # repeating timer
game.cancel(timer_id) -> None              # cancel timer
game.cancel_tween(tween_id) -> None        # cancel tween
game.input                                 # InputManager property
```

---

### 25. Scene.handle_input() Signature Change

**Before (Stages 0-3):**
```python
def handle_input(self, event: Event) -> bool:  # Event = KeyEvent | MouseEvent | WindowEvent
```

**After (Stage 5):**
```python
def handle_input(self, event: InputEvent) -> bool:  # InputEvent with .action field
```

This is backward-compatible in practice: existing code checks `event.type`, `event.key`, `event.x`, `event.y` — all present on `InputEvent`. No existing code uses `isinstance(event, KeyEvent)`. Type annotation changes in `scene.py` and `base.py` imports.

**Existing tests must be updated** to expect `InputEvent` instead of raw `KeyEvent`. Since `inject_key("space")` still injects a `KeyEvent` into the backend, and `Game.tick()` now translates it, tests that check `received_events[0].key == "space"` still work. Tests that inject events via `inject_key` continue to work unmodified.

---

### Component Boundaries (Stage 4+5 additions)

| Component | Owns | Does NOT own |
|---|---|---|
| `TimerManager` | timer dict, next_id counter, update iteration | game reference (Game owns the manager) |
| `TweenManager` | tween dict, next_id counter, easing functions, update iteration | target objects (weak reference pattern not needed — tweens removed when done) |
| `InputManager` | key→action bindings, event translation | event polling (backend owns), window events (Game intercepts) |
| `Sprite.move_to()` | move tween IDs, speed→duration conversion | TweenManager (accessed via module-level ref) |

---

### Constraints & Gotchas (Stage 4+5)

18. **`tween()` free function requires Game to exist.** Module-level `_tween_manager` is set by `Game.__init__()`. Calling `tween()` before creating a Game raises `RuntimeError`. Same pattern as Sprite construction.
19. **Timer callbacks run in insertion order within a frame.** `_timers` is a dict (Python 3.7+ insertion-ordered). Timers that fire in the same frame execute in the order they were created. This is deterministic.
20. **Repeating timers don't catch up.** If a repeating timer with `interval=0.1` gets `dt=0.5`, it fires once and resets `remaining` (no 5x catch-up). This prevents callback storms from large dt spikes (e.g. window drag on macOS pauses the loop).
21. **`cancel()` during callback is safe.** Cancelled timers/tweens are skipped by the iteration loop. The `cancelled` flag is checked before firing each callback.
22. **`Sprite.remove()` must cancel move tweens.** Added to the existing `remove()` cleanup chain: clear animation → cancel move tweens → remove from backend.
23. **`move_to()` on a removed sprite is a no-op.** Same guard pattern as `play()`.
24. **InputEvent is frozen (immutable).** Like KeyEvent/MouseEvent, InputEvent is a frozen dataclass. Scenes cannot mutate events.
25. **`bind()` is one-key-per-action.** Binding "attack" to "a" then "attack" to "b" replaces the binding. Binding "jump" to "a" while "attack" is already on "a" steals the key — "attack" becomes unbound. This prevents ambiguity.
26. **Module-level `_tween_manager` set via import-then-assign pattern** (same as `_current_game` in sprite.py). `Game.__init__()` does `import easygame.util.tween as _tw; _tw._tween_manager = self._tween_manager`. Avoids circular imports since `util/tween.py` is a leaf module.

---

### Testing Strategy (Stage 4+5)

**Timer tests (`tests/test_timer.py`):**
- `after()` fires callback after correct elapsed time (accumulate dt across ticks)
- `every()` fires repeatedly at correct intervals
- `cancel()` prevents future fires
- Cancel during callback is safe
- Callback that creates a new timer doesn't fire the new one in the same frame
- `cancel_all()` clears everything
- Timer with 0 delay fires on next update (not immediately)

**Tween tests (`tests/test_tween.py`):**
- `tween()` reaches target value after duration
- Intermediate values follow easing curve (spot-check at 50% for each ease)
- `on_complete` fires exactly once when done
- `cancel_tween()` stops interpolation at current value
- Tweening sprite.x updates backend (via property setter)
- Two tweens on different properties of same object work concurrently
- Creating a new tween on same target+property doesn't auto-cancel the old one (both run — game code must cancel manually, or use `move_to()` which does cancel)

**Sprite.move_to tests (`tests/test_sprite_move.py`):**
- Sprite reaches target position after distance/speed seconds
- `on_arrive` fires when movement completes
- New `move_to()` cancels previous movement
- `move_to()` with distance=0 fires `on_arrive` immediately
- `remove()` cancels active movement
- `move_to()` on removed sprite is no-op

**Input tests (`tests/test_input.py`):**
- Default "confirm" binding: Enter → action="confirm"
- Custom binding: `bind("attack", "a")` → pressing A produces action="attack"
- Unmapped key: action=None, key still available
- `unbind()` removes mapping
- Key stealing: binding a new action to an already-bound key unbinds the old action
- Mouse events pass through with logical coordinates and action=None
- `get_bindings()` returns current mapping
- Scene receives InputEvent, not raw KeyEvent

**Integration tests (`tests/test_game.py` additions):**
- `game.tick()` advances timers and tweens
- Timer + tween + animation all update in correct order within one tick
- `game.after(0.5, callback)` fires after 0.5s of accumulated ticks

### Lessons Learned (Stage 4+5)

1. **Module-level `_tween_manager` mirrors `_current_game` pattern.** Both are set in `Game.__init__()` via import-then-assign. Both raise `RuntimeError` if used before Game exists. Consistent patterns reduce cognitive load.
2. **`tween()` as a free function was the right choice over `game.tween()`.** DESIGN.md shows free-function style, and the upcoming Actions system (Stage 10) will need `tween()` from action classes without a `game` reference.
3. **Snapshot-copy iteration is the consistent safety pattern.** All three managers (timer, tween, animation) iterate `list(self._dict.items())` or `list(self._set)`. Callbacks can safely add/remove/cancel during iteration.
4. **InputEvent as a unified type works well.** Scenes check `event.type`, `event.key`, `event.action` without `isinstance` checks. The frozen dataclass with defaults keeps both keyboard and mouse events in one type cleanly.
5. **Window event interception before translation is clean.** `Game.tick()` pulls out `WindowEvent("close")` first, then passes only key/mouse events to `InputManager.translate()`. Scenes never see window events.
6. **`move_to()` only puts `on_complete` on the y-tween.** Since both x and y tweens have identical duration, only one needs the callback. Avoids double-fire or counter tracking.
7. **`Sprite.remove()` cleanup chain grew to 4 steps:** clear anim_player → clear anim_queue → cancel move tweens → remove from backend. Each stage adds cleanup — the guard pattern (`if self._removed: return`) at the top prevents double-execution.
8. **Timer/tween test fixtures are self-contained.** Each test file creates its own `Game(backend="mock")` fixture rather than sharing conftest's `mock_game`. This gives each test file control over resolution and asset setup.
9. **`game.input` property returns `object` type annotation** — intentionally avoids importing `InputManager` at module level in `game.py` to keep it behind `TYPE_CHECKING`. Users call `game.input.bind()` via duck typing.

---

## Stage 6 — Battle Vignette Demo (COMPLETE)

Validation stage — no new framework modules. The demo builds a single-screen tactical battle (1920×1080) using only Stage 0–5 primitives, proving the API composes correctly for real game choreography. 31 headless tests; 217 total tests pass.

### What Was Built

**Files:**
```
examples/battle_vignette/
  battle_demo.py              # ~430 lines — BattleScene, Unit, _FloatingNumber, main()
  generate_assets.py          # Pillow-generated colored rectangles + yellow ring
  README.md                   # Controls, run instructions, observation notes
  assets/images/sprites/      # 20 PNGs (warrior idle/walk/attack, skeleton idle/walk/hit/death, select_ring)
tests/
  test_battle_vignette.py     # 31 headless tests across 8 test classes
```

### Key Implementation Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Demo location | `examples/battle_vignette/` (not `tests/visual/`) | Cleaner separation of examples from test infrastructure |
| Unit data holder | `Unit` class with sprite, team, home_pos, hp, alive | Lightweight data object — not a framework class |
| Floating damage numbers | `_FloatingNumber` with tween-able x/y/opacity, drawn via `draw_text()` | Approach (c) from plan — any object with settable attrs works with `tween()` |
| Hit testing | Manual `abs(mx - ux) < HIT_RADIUS` in `_unit_at()` | Framework-agnostic — hit testing is game code per DESIGN.md boundary |
| Choreography pattern | 8 named methods per phase (not nested lambdas) | Readable, each phase is a clear method. Still shows callback awkwardness via the chain length |
| Resolution | 1920×1080 (not 800×600 from plan) | More room for 3v3 battle layout |

### What the Demo Validates

1. `Sprite.play()` + `on_complete` chaining (walk → attack → idle)
2. `Sprite.move_to()` + `on_arrive` (charge forward, walk back)
3. `tween()` on non-Sprite objects (`_FloatingNumber.y`, `.opacity`)
4. `game.after()` for inter-phase delays (0.3s before hit reaction)
5. `InputEvent` click handling with `event.button == "left"` and `event.action == "cancel"`
6. `Sprite.remove()` + opacity fade for death cleanup
7. Selection ring as separate sprite with `BOTTOM_CENTER` anchor at `UI_WORLD` layer
8. `self.busy` flag to block input during choreography

### API Concerns Surfaced

1. **No sprite hit-testing** — Demo needs manual `_unit_at()` helper. Acceptable (game code boundary), but common enough that a `Sprite.contains(x, y)` convenience may be worth adding later.
2. **No `Sprite.image` setter** — Selection uses a separate ring sprite rather than changing the unit's image. Works fine, but a public `image` setter would be cleaner for highlight effects.
3. **Callback chain depth** — 8 methods to choreograph a 6-phase attack. Each method is readable in isolation, but the control flow across `on_arrive → on_complete → game.after → on_complete → ...` is exactly the pain point that motivates the Actions system (Stage 10). The demo deliberately showcases this.
4. **No timer cancellation on scene exit** — `BattleScene` has no `on_exit()` cleanup. Pending `game.after()` timers referencing removed sprites are safe (removed-sprite methods are no-ops) but sloppy. A real game should track and cancel timer IDs, or the framework should auto-cancel scene-scoped timers.
5. **`draw_text()` requires manual alpha computation** — `_FloatingNumber.opacity` is a float tweened 255→0, must be `int()` clamped and inserted into `(r, g, b, a)` tuple each frame. Works but verbose.

### Lessons Learned (Stage 6)

1. **Named methods per phase >> nested lambdas.** The plan's pseudocode used nested `lambda: [...]` lists inside callbacks. The implementation used 8 separate named methods (`_begin_attack`, `_phase_attack_anim`, ..., `_phase_done`). Much more readable and debuggable, and equally demonstrates the callback-chain pain point.
2. **`_FloatingNumber` pattern generalizes.** Any object with settable attributes can be a tween target. This is a powerful pattern for game code — no framework Label/TextSprite class needed yet.
3. **Selection ring as separate sprite works cleanly.** Create on select, `.remove()` on deselect. No image-swapping needed.
4. **`_run_full_attack()` test helper is well-designed.** Ticking until `not scene.busy` with a 15-second safety bound is robust and avoids brittle frame-count assertions.
5. **Self-contained demo assets are the right call.** `generate_assets.py` lives in the example directory, not in test infrastructure. Examples should be fully self-contained.
6. **31 tests is thorough for a demo.** 8 test classes covering init, selection, reselection, attack start, full sequence, death, multiple rounds, and busy-state blocking. This gives high confidence the choreography is correct across all paths.

---

## Stage 7 — Demo Retrospective & Framework Refinements

This section is the systematic analysis of what the battle vignette demo taught us about the framework. Every observation below comes from concrete code in `examples/battle_vignette/battle_demo.py` and the framework modules it exercises.

### 1. Abstractions That Helped

**AnimationDef as reusable template (animation.py).** Module-level constants like `WARRIOR_WALK = AnimationDef(frames="sprites/warrior_walk", ...)` are created before `Game` exists. Multiple sprites share the same def. Frame discovery via prefix string (`frames="sprites/warrior_walk"` → discovers `_01.png` through `_04.png`) eliminated all manual frame listing. This was the right design — stateless defs, handles resolved lazily at play-time.

**Sprite.play() + on_complete chaining (sprite.py:253-294).** Readable one-liner per animation step: `attacker.sprite.play(WARRIOR_ATTACK, on_complete=lambda: ...)`. The wrapped-callback pattern (line 277-280) that drains the animation queue after the user callback fires is invisible to game code. Looping vs one-shot distinction (`loop=False` → fires on_complete) worked perfectly for the walk→attack→idle pattern.

**Sprite.move_to() with speed (sprite.py:323-365).** `move_to((target_x, dy), speed=MOVE_SPEED, on_arrive=...)` is exactly the right API. Speed-based (not duration-based) means the warrior walks at constant velocity regardless of distance. Internal tween cancellation on re-call prevents movement conflicts. The on_arrive callback chains naturally with play()'s on_complete.

**tween() on arbitrary objects (tween.py:155-176).** `_FloatingNumber` (battle_demo.py:115-127) is a plain Python object with `.x`, `.y`, `.opacity` attributes. `tween(floater, "y", ...)` and `tween(floater, "opacity", ...)` work via `setattr()` with zero framework coupling. This proves the tween system's generality — it doesn't need to know about Sprite at all. Any settable attribute on any object is tween-able.

**InputEvent with .action mapping (input.py).** `event.action == "cancel"` (battle_demo.py:196) is cleaner than `event.key == "escape"`. Mouse events pass through with `.type == "click"` and `.button == "left"` (line 200). The unified type avoids isinstance checks. Default `cancel→escape` binding meant zero input configuration code.

**Sprite.remove() safety (sprite.py:226-242).** Double-remove is safe. Removed sprites silently no-op on property sets, play(), move_to(). This matters in the death choreography where the defender's sprite is faded, removed, and may still receive stale tween callbacks. No defensive coding needed in game code.

**game.after() for delays (timer.py).** `self.game.after(0.3, lambda: ...)` at battle_demo.py:286-289 inserts a timing gap between attack animation and hit reaction with one line. Clean, readable, no manual timer tracking needed for fire-and-forget delays.

### 2. Friction Points & Awkwardness

**F1. Imports reach into internal modules (battle_demo.py:43-45).**
```python
from easygame.assets import AssetManager          # should be: from easygame import AssetManager ✓
from easygame.rendering.layers import RenderLayer, SpriteAnchor  # internal!
from easygame.util.tween import Ease, tween       # Ease/tween already in easygame ✓
```
`RenderLayer` and `SpriteAnchor` are re-exported from `easygame` (see `__init__.py:20`), but the demo imports from `easygame.rendering.layers`. `Ease` and `tween` are also in `easygame`. Only `AssetManager` is correctly in `easygame.__init__`. This reveals that the public API re-exports aren't obvious enough — or the demo was written without checking them.

**Decision:** Not a framework bug. The demo should be updated to use public imports only:
```python
from easygame import AnimationDef, Game, InputEvent, Scene, Sprite
from easygame import AssetManager, RenderLayer, SpriteAnchor, Ease, tween
```
This is a demo fix, not a framework change.

**F2. Three different callback naming conventions.**
- `move_to(..., on_arrive=...)` — Sprite method uses `on_arrive`
- `play(..., on_complete=...)` — Sprite method uses `on_complete`
- `tween(..., on_complete=...)` — Module function uses `on_complete`
- `game.after(delay, callback)` — Positional, no keyword name

The inconsistency between `on_arrive` and `on_complete` is minor but noticeable when chaining them. They mean the same thing: "call this when done."

**Decision: Keep as-is.** `on_arrive` is semantically distinct from `on_complete` — arrival is spatial, completion is temporal. The distinction helps readability: `move_to(pos, on_arrive=shoot)` reads better than `move_to(pos, on_complete=shoot)`. The Actions system will eliminate most callback usage anyway.

**F3. `tween()` requires explicit from_val (tween.py:155-164).**
```python
tween(defender.sprite, "opacity", 255.0, 0.0, 0.5, ease=Ease.EASE_OUT, on_complete=...)
```
The `from_val=255.0` is redundant — the sprite's current opacity is already 255. Every tween call in the demo specifies a from_val that matches the object's current state. A `tween_to()` variant or making `from_val` optional (defaulting to current value via `getattr`) would eliminate this redundancy.

**Decision: Add to refinements list for Stage 10.** When implementing Actions, `FadeOut(duration)` and `MoveTo(pos, speed)` will read current values internally. The low-level `tween()` function keeps explicit from/to for flexibility, but the high-level API should default from_val to current.

**F4. Floating damage numbers require custom draw() boilerplate (battle_demo.py:389-407).**
```python
def draw(self) -> None:
    if self._font is None:
        self._font = self.game.backend.load_font("Arial", 24)
    for f in self.floaters:
        if not f.alive:
            continue
        alpha = max(0, min(255, int(f.opacity)))
        self.game.backend.draw_text(...)
    self.floaters = [f for f in self.floaters if f.alive]
```
This is 18 lines of boilerplate for "show some text that fades out." The scene must manage a list, track alive/dead state, lazy-load fonts, clamp alpha, and clean up dead floaters. A framework `TextSprite` or `Label` class would reduce this to 2 lines: create it, tween it, remove it — same lifecycle as Sprite.

**Decision: TextSprite is a Stage 8 (UI) deliverable.** No framework change now. The `_FloatingNumber` pattern proves what the framework needs: a text equivalent of Sprite with position/opacity properties, auto-drawn by the batch, removable. This directly informs TextSprite design.

**F5. No Sprite.image setter — can't change a sprite's image at runtime (sprite.py).**
Sprite has `_set_image()` as internal (called by animation system) but no public `image` setter. To show a "highlighted" warrior, the demo creates a separate selection ring sprite rather than tinting or swapping the warrior's image. For hit-flash effects (white frame on hit), you'd need to play a 1-frame animation.

**Decision: Add `Sprite.image` property setter.** Simple change — expose `_set_image()` as a public setter. This enables image-swap effects (hit flash, state indicators) without abusing the animation system. The setter should accept an asset name (like the constructor), not a raw handle.

**F6. Sprite.opacity type is `int` but tween sets it to `float` (sprite.py:182-189, tween.py:137-138).**
```python
# sprite.py — opacity property
@property
def opacity(self) -> int:
    return self._opacity

@opacity.setter
def opacity(self, value: int) -> None:
    self._opacity = value          # stores whatever type tween passes
    self._sync_to_backend()
```
`tween()` calls `setattr(target, "opacity", 127.5)` — a float. The setter accepts it silently (no `int()` coercion). `_sync_to_backend()` then passes this float to the backend as `opacity=self._opacity`. MockBackend stores it as-is. PygletBackend may or may not handle float opacity correctly depending on pyglet version.

The getter declares `-> int` but returns whatever was stored, which after tweening is a `float`. This is a type lie.

**Decision: Coerce to int in the setter.** `self._opacity = int(value)` — one line change. The tween system's intermediate float values get rounded each frame, which is fine for 0-255 integer opacity. This fixes the type annotation lie and prevents float opacity from reaching the backend.

**F7. `_unit_at()` hit-test uses sprite logical position, not bounding box (battle_demo.py:223-231).**
```python
ux, uy = unit.sprite.position  # anchor point (BOTTOM_CENTER)
if abs(mx - ux) < HIT_RADIUS and abs(my - uy) < HIT_RADIUS:
```
This compares the click against the anchor point (bottom-center of the sprite), not the sprite's visual bounds. With BOTTOM_CENTER anchor, the click region is biased downward — clicking the top half of a sprite might miss if HIT_RADIUS is too small. The demo compensates with `HIT_RADIUS = 40` (generous), but this is a footgun.

**Decision: Consider `Sprite.contains(x, y)` convenience.** Uses anchor + cached image dimensions to compute the axis-aligned bounding box and test containment. This is ~5 lines of code, eliminates a common game-code mistake, and doesn't cross the "game code owns hit testing" boundary — it's just geometric containment on the sprite's own rect. Deferred to a later refinement pass.

### 3. Callback Nesting: The Core Pain Point

The attack choreography in `battle_demo.py:261-357` is 8 methods, ~100 lines, to express this linear sequence:

```
walk to enemy → attack anim → 0.3s delay → hit reaction
  → if dead: death anim → fade out → remove sprite
  → walk home → idle anim → set busy=False
```

**Structural analysis of the callback chain:**
```
_begin_attack
  └→ move_to(on_arrive=)
       └→ _phase_attack_anim
            └→ play(on_complete=)
                 └→ _phase_delay
                      └→ game.after(0.3, callback=)
                           └→ _phase_hit_reaction
                                ├→ [if alive] play(on_complete=)
                                │    └→ _phase_defender_recover
                                │         └→ _phase_walk_home
                                └→ [if dead] play(on_complete=)
                                     └→ _phase_death
                                          └→ play(on_complete=)
                                               └→ _phase_fade_and_remove
                                                    └→ tween(on_complete=)
                                                         └→ _phase_cleanup_dead
                                                              └→ _phase_walk_home
```

**Maximum nesting depth:** 7 callbacks deep (begin → move → attack → delay → hit → death → fade → cleanup).

**What makes this hard to reason about:**
1. **Control flow is invisible.** You can't read the sequence top-to-bottom. Each method ends with a callback registration that will fire later in a completely different call stack. Debugging requires mental unwinding of which callback fires when.
2. **Branching requires method duplication.** The "alive vs dead" branch at `_phase_hit_reaction` (lines 292-313) has two separate `play()` calls with different on_complete targets. Both paths eventually converge on `_phase_walk_home`, but you can't see the convergence without reading both branches fully.
3. **State must be threaded through every method.** `attacker` and `defender` are parameters on every single phase method (8 signatures × 2 params = 16 param declarations). This is pure boilerplate — the attack context never changes.
4. **No cancellation mechanism.** If the scene transitions during an attack, there's no way to cancel the in-flight callback chain. `game.after()` timers, tweens, and animation callbacks will keep firing into a stale scene. The guard `if not defender.alive` at line 293 is an ad-hoc workaround for one case, not a general solution.
5. **Interleaving is impossible.** What if we want the damage number to float up *while* the defender plays hit reaction, not after? With callbacks, you'd need to fire both from the same point and track two completion signals. The current code does this for the damage number by ignoring its completion (fire-and-forget tweens), but that only works because nothing depends on the number finishing.

### 4. Bugs and Edge Cases

**B1. Opacity type mismatch (identified in F6 above).** `Sprite.opacity` getter returns `float` after tweening despite `-> int` annotation. Fix: `self._opacity = int(value)` in setter.

**B2. Sprite.x and Sprite.y setters double-sync.** In sprite.py:
```python
@x.setter
def x(self, value: float) -> None:
    self.position = (value, self._y)  # calls position setter → _sync_to_backend + set_sprite_order
```
During `move_to()`, the tween system updates `x` and `y` independently each frame. Each setter call goes through the `position` setter, which calls `_sync_to_backend()` AND `set_sprite_order()`. So every frame during movement: 2 `_sync_to_backend()` calls + 2 `set_sprite_order()` calls = 4 backend calls per frame, when 1 of each would suffice.

**Impact:** Performance overhead during movement. Not a bug — it's correct, just wasteful. In the mock backend this is invisible; in PygletBackend it creates redundant Group objects.

**Decision: Note for future optimization.** A "batch update" or "dirty flag" pattern could coalesce multiple property changes into one sync. Low priority — not causing bugs, and pyglet's batch rendering absorbs redundant updates gracefully.

**B3. Dead floaters accumulate during draw() before cleanup (battle_demo.py:394-407).**
```python
for f in self.floaters:
    if not f.alive:
        continue          # skipped but still iterated
    ...
self.floaters = [f for f in self.floaters if f.alive]  # cleanup after draw
```
Dead floaters are drawn (skipped) for one frame after death before being cleaned up. Not a visual bug (they're invisible by then), but the list grows unboundedly if attacks happen faster than cleanup. In practice, the `busy` flag serializes attacks, so this never accumulates more than one dead floater at a time. Safe, but fragile if the busy lock were removed.

**Decision: No fix needed.** The pattern works correctly. A framework TextSprite would eliminate this entirely.

**B4. No scene cleanup on exit (battle_demo.py).** BattleScene has no `on_exit()`. If the scene were popped during an attack sequence, pending `game.after()` timers and tweens would keep firing. The Sprite removal guards prevent crashes, but the timers and tweens would run uselessly until they complete.

**Decision: Document as a best practice.** Scenes with active timers/tweens should cancel them in `on_exit()`. Consider framework support for scene-scoped timers (auto-cancel on exit) in a later stage. The Actions system partly solves this — `sprite.stop_actions()` in `on_exit()` cancels the entire sequence.

### 5. API Refinements to Reduce Friction

Based on the analysis above, these refinements are prioritized:

**R1. Add `Sprite.image` setter (do now).** Expose `_set_image()` publicly. Accepts asset name string, resolves through AssetManager, updates backend. Enables runtime image swapping for effects.

**R2. Coerce `Sprite.opacity` to int in setter (do now).** One-line fix: `self._opacity = int(value)`. Prevents float opacity from leaking to backend. Fixes type annotation lie.

**R3. Demo import cleanup (do now).** Change `battle_demo.py` to import from `easygame` public API only.

**R4. `Sprite.contains(x, y)` convenience (defer).** Geometric AABB containment test using position + anchor + image dimensions. Common enough to be worth framework support, but not urgent.

**R5. Scene-scoped timer auto-cancellation (defer).** Framework could track which timers/tweens were created while a scene is active and auto-cancel on `on_exit()`. Complex interaction with shared game-level timers. Deferred until more examples show the pattern is needed.

**R6. `tween()` optional from_val (defer to Actions).** Make `from_val` default to `getattr(target, prop)` when omitted. Low priority — the Actions system's `FadeOut(duration)` / `MoveTo(pos, speed)` will handle the common case. Changing the tween() signature now would break existing code.

### 6. How the Actions System Would Simplify the Choreography

The battle attack sequence from `battle_demo.py:261-357` (8 methods, ~100 lines, max 7 callbacks deep) would become:

```python
from easygame.actions import Sequence, Parallel, Delay, Do, PlayAnim, MoveTo, FadeOut, Remove

def _begin_attack(self, attacker: Unit, defender: Unit) -> None:
    self.busy = True
    self._deselect()

    dx, dy = defender.sprite.position
    target_x = dx - 80 if attacker.home_pos[0] < dx else dx + 80

    attacker.sprite.do(Sequence(
        # Phase 1-2: Walk to enemy + attack
        Parallel(PlayAnim(WARRIOR_WALK), MoveTo((target_x, dy), speed=MOVE_SPEED)),
        PlayAnim(WARRIOR_ATTACK),

        # Phase 3-4: Delay + hit reaction
        Delay(0.3),
        Do(lambda: self._apply_hit(attacker, defender)),

        # Phase 5-6: Walk home + idle
        Parallel(PlayAnim(WARRIOR_WALK), MoveTo(attacker.home_pos, speed=MOVE_SPEED)),
        PlayAnim(WARRIOR_IDLE),
        Do(lambda: setattr(self, 'busy', False)),
    ))

def _apply_hit(self, attacker: Unit, defender: Unit) -> None:
    """Apply damage and trigger defender reactions."""
    if not defender.alive:
        return
    defender.hp -= ATTACK_DAMAGE
    self._spawn_damage_number(defender)

    if defender.hp <= 0:
        defender.alive = False
        defender.sprite.do(Sequence(
            PlayAnim(SKELETON_HIT),
            PlayAnim(SKELETON_DEATH),
            FadeOut(0.5),
            Remove(),
        ))
    else:
        defender.sprite.do(Sequence(
            PlayAnim(SKELETON_HIT),
            PlayAnim(SKELETON_IDLE),
        ))
```

**Improvement metrics:**
- **8 methods → 2 methods** (67% reduction in method count)
- **~100 lines → ~40 lines** (60% reduction)
- **7 callbacks deep → 0 callbacks** (sequence is flat and readable top-to-bottom)
- **16 parameter declarations → 4** (state threading eliminated)
- **Branching is local.** The alive/dead branch is a simple if/else calling `defender.sprite.do()` with a different sequence — no separate method needed.
- **Cancellation is built-in.** `sprite.stop_actions()` cancels the entire in-flight sequence. Scene `on_exit()` can call this on all active sprites.
- **Parallel composition is explicit.** `Parallel(PlayAnim(WARRIOR_WALK), MoveTo(...))` expresses "animate and move simultaneously" — currently this requires calling both `play()` and `move_to()` separately and hoping they stay in sync.

**What Actions WON'T simplify:**
- The `_spawn_damage_number()` method stays the same — it's a fire-and-forget side effect.
- Selection/deselection logic stays the same — it's input handling, not choreography.
- The `busy` flag pattern still requires `Do(lambda: ...)` wrappers. A richer approach might be an `on_start`/`on_complete` callback on the top-level `do()` call.
- Hit testing and unit management are game logic, not sequencing.

### Key Refinement Decisions (Summary)

| ID | Refinement | When | Rationale |
|---|---|---|---|
| R1 | `Sprite.image` setter | Now (Stage 7) | Enables runtime image swap; trivial change |
| R2 | Coerce opacity to int | Now (Stage 7) | Fixes type lie; one-line fix |
| R3 | Demo import cleanup | Now (Stage 7) | Use public API imports only |
| R4 | `Sprite.contains(x, y)` | Later | Common but not blocking |
| R5 | Scene-scoped timer cleanup | Later | Complex; Actions partially solve it |
| R6 | `tween()` optional from_val | Stage 10 | Actions subsume the use case |
| R7 | `TextSprite` / `Label` | Stage 8 (UI) | Eliminates _FloatingNumber boilerplate |
| R8 | Actions system | Stage 10 | Eliminates callback nesting entirely |

### Lessons Learned (Stage 7)

1. **RETROSPECTIVE.md is a solid deliverable.** Comprehensive 593-line document covering all 5 acceptance criteria sections with concrete code examples. Documents friction that directly motivates future stages (Actions, UI).
2. **Refinements R1-R3 were already implemented before the retrospective was written.** `Sprite.image` setter (sprite.py:214-229), opacity int coercion (sprite.py:189-190), and demo import cleanup (battle_demo.py:36-47) were all in place. The retrospective documents what was done, not what needs doing.
3. **Two new tests validate the refinements.** `test_set_image_property` and `test_opacity_setter_coerces_float` provide regression coverage for the fixes.
4. **The demo successfully uses only public API imports.** Single `from easygame import (...)` block confirms `__init__.py` exports are complete for Stages 0-5.

---
*Last updated: Stage 7 (Demo Retrospective & Framework Refinements) COMPLETE. 219 tests pass. All acceptance criteria met.*
