# Architecture Notes

## Stage 6 — Camera System (COMPLETE)

**Tests:** 290 unit tests pass (219 pre-existing + 71 camera). 4 screenshot
tests in `tests/screenshot/test_camera_screenshots.py` (excluded from normal
`pytest` — require pyglet + GPU).

---

### Camera Class: `easygame/rendering/camera.py`

Pure math, no backend dependency. Translates between world and screen (logical)
coordinates. Re-exported via `easygame.rendering` and `easygame.__init__`.

```python
camera = Camera(viewport_size=(1920, 1080), world_bounds=(left, top, right, bottom))
camera.center_on(x, y)                    # center viewport, clamp to bounds
camera.follow(sprite)                      # center on sprite each frame
camera.scroll(dx, dy)                      # manual scroll, cancels follow + pan
camera.enable_edge_scroll(margin, speed)   # scroll when mouse near edge
camera.disable_edge_scroll()
camera.screen_to_world(sx, sy)             # screen -> world coords
camera.world_to_screen(wx, wy)             # world -> screen coords
camera.pan_to(x, y, duration, easing)      # smooth tween via tween system
camera.update(dt, mouse_x, mouse_y)        # per-frame: follow + edge scroll
```

Key properties: `x`, `y` (read-only, top-left of viewport in world space),
`viewport_width`, `viewport_height`, `world_bounds` (read-write, re-clamps
on set).

**world_bounds** uses `(left, top, right, bottom)` — not `(width, height)`.
Supports non-zero-origin worlds.

**Conflict resolution:** `center_on()` and `scroll()` cancel active pan and
disable follow. `follow()` cancels active pan. `pan_to()` disables follow.
Each calls `_cancel_pan()` which cancels tween IDs via TweenManager.

**`_clamp()`** enforces viewport stays inside world_bounds after every
position change (center_on, scroll, follow update, edge scroll).

---

### Scene Integration: `easygame/scene.py`

```python
class Scene:
    camera: Camera | None = None   # None for UI-only scenes
```

World scenes set `self.camera = Camera(...)` in `on_enter()`. Game.tick()
reads `getattr(top_scene, "camera", None)` during the draw phase. Each scene
on the stack has its own independent camera.

---

### Game Integration: `easygame/game.py`

#### `Game._all_sprites: set`

All live Sprites register in `Sprite.__init__()` and deregister in
`Sprite.remove()`. This is the iteration target for the camera render-sync
pass. Parallel to the existing `Game._animated_sprites` (only tracks sprites
with active animations).

#### `Game._mouse_x`, `Game._mouse_y`

Updated from raw `MouseEvent` (type `"move"` or `"drag"`) during event
processing in `tick()`, before input translation. Logical screen coordinates.
Passed to `camera.update(dt, mouse_x, mouse_y)` for edge scroll.

#### Sync/Restore in `Game.tick()` Draw Phase

```python
# Draw phase in tick():
top = scene_stack.top()
camera = getattr(top, "camera", None) if top else None

if camera is not None:
    camera.update(dt, self._mouse_x, self._mouse_y)
    saved = self._sync_sprites_to_camera(camera)
else:
    saved = None

backend.begin_frame()
scene_stack.draw()
backend.end_frame()

if saved is not None:
    self._restore_sprites(saved)
```

**`_sync_sprites_to_camera(camera)`** — iterates `_all_sprites`. Per sprite:
1. Computes world-space draw corner: `world_pos - anchor_offset`
2. Applies camera offset: `screen_x = world_draw_x - camera._x`
3. Frustum culling: sprite rect outside viewport → `effective_visible = False`
4. Calls `backend.update_sprite(sprite_id, screen_x, screen_y, visible=...)`
5. Saves original `(sprite, orig_x, orig_y, orig_visible)` for restoration
6. Returns the saved list

**`_restore_sprites(saved)`** — after `end_frame()`, restores each sprite's
backend position to pre-camera world coordinates. Skips removed sprites.
Necessary because `Sprite._sync_to_backend()` eagerly pushes world positions
on every property change — leaving camera-adjusted positions would cause
double-offsetting on the next eager sync.

**Frustum culling** uses `sprite._img_w` / `sprite._img_h` as margin so
sprites don't pop at viewport edges.

---

### Coordinate Flow (full pipeline)

```
Sprite world pos (x, y)
  → _anchor_offset(anchor, img_w, img_h) → world draw corner
  → _sync_sprites_to_camera: subtract (camera._x, camera._y) → screen draw corner
  → backend.update_sprite(screen_x, screen_y)
  → [PygletBackend] _to_physical: y-flip + scale + offset → physical GPU coords
```

Without camera (Scene.camera is None): sprites render at world pos as if
world == screen — fully backward compatible with Stages 1-5.

---

### Mouse Input and Camera

Mouse events stay in **screen (logical) coordinates** in `InputEvent`. Game
code calls `camera.screen_to_world(event.x, event.y)` explicitly for world
coords. UI components (needing screen coords) work unchanged.

---

### What Did NOT Change

| File | Status |
|---|---|
| `backends/base.py` | Unchanged — no new protocol methods |
| `backends/mock_backend.py` | Unchanged — camera is pure framework math |
| `backends/pyglet_backend.py` | Unchanged — receives screen coords as before |
| `Sprite._sync_to_backend()` | Unchanged — handles anchor offset only |

---

### Files Changed/Created

| File | Change |
|---|---|
| `easygame/rendering/camera.py` | **NEW** — Camera class (313 lines) |
| `easygame/rendering/__init__.py` | Added `Camera` to re-exports |
| `easygame/__init__.py` | Added `Camera` to re-exports and `__all__` |
| `easygame/scene.py` | `camera: Camera | None = None` on Scene, TYPE_CHECKING import |
| `easygame/game.py` | `_all_sprites` set, `_mouse_x/_mouse_y`, `_sync_sprites_to_camera()`, `_restore_sprites()`, camera logic in `tick()` draw phase, `MouseEvent` import |
| `easygame/rendering/sprite.py` | `_game._all_sprites.add(self)` in `__init__`, `.discard(self)` in `remove()` |
| `tests/test_camera.py` | **NEW** — 71 unit tests |
| `tests/screenshot/test_camera_screenshots.py` | **NEW** — 4 screenshot tests |

---

### Lessons Learned

- **Sync/restore pattern** is correct for per-frame transforms layered on top
  of eagerly-synced sprite positions. Avoids double-offsetting and keeps Sprite
  camera-unaware.
- **`_all_sprites` registry** mirrors `_animated_sprites` — sprites self-register
  via the `_current_game` module-level singleton. Pattern works well.
- **`world_bounds` as `(left, top, right, bottom)`** is more flexible than
  `(width, height)` and handles non-zero-origin worlds cleanly.
- **Edge scroll needs explicit mouse position passing** — `camera.update(dt,
  mouse_x, mouse_y)` keeps Camera free of Game/InputManager dependencies.
- **Screenshot tests catch real rendering bugs** that mock-only tests miss
  (e.g. y-flip interactions with camera offset in pyglet backend), but require
  GPU context so are separated from the normal test run.
- **`_cancel_pan()` guards against missing TweenManager** — handles the case
  where Camera is constructed before Game init (tests) gracefully.

---
---

## Stage 7 — Audio System (COMPLETE)

### Overview

AudioManager (`easygame/audio.py`) — framework-level audio abstraction
that sits between game code and the backend audio protocol. Game code does
`game.audio.play_sound("sword_hit")`, never touches the backend directly.

**Key design principle:** AudioManager is pure framework logic (volume math,
pool selection, crossfade orchestration). All actual playback goes through
the backend protocol. This mirrors how Camera is pure math and Sprite
delegates to the backend for rendering.

---

### Backend Protocol Extensions Needed

The backend protocol in `backends/base.py` already declares 6 audio methods.
Both `MockBackend` and `PygletBackend` already implement them. **No new
backend protocol methods are needed.** The existing protocol is sufficient:

```
Already in base.py Backend protocol:
  load_sound(path) -> SoundHandle          # non-streaming SFX
  play_sound(handle, volume=1.0)           # fire-and-forget
  load_music(path) -> SoundHandle          # streaming music
  play_music(handle, loop=True, volume=1.0) -> player_id   # returns opaque player
  set_player_volume(player_id, volume)     # for crossfade volume tweening
  stop_player(player_id)                   # stop + dispose
```

Already implemented in `MockBackend`:
- `load_sound()` → returns `"sound_N"` string handles, caches by path
- `play_sound(handle, volume)` → appends to `sounds_played` list
- `load_music()` → returns `"music_N"` string handles
- `play_music()` → creates `"player_N"`, tracks in `_music_players` dict,
  sets `music_playing` and `music_volume` convenience fields
- `set_player_volume()` → updates player dict + convenience field
- `stop_player()` → marks player inactive, updates `music_playing` to
  next active player or `None`

Already implemented in `PygletBackend`:
- `load_sound()` → `pyglet.media.load(path, streaming=False)`
- `play_sound()` → `handle.play()` + sets `player.volume`
- `load_music()` → `pyglet.media.load(path, streaming=True)`
- `play_music()` → creates `pyglet.media.Player`, queues source, sets
  loop and volume, calls `play()`, returns the player object
- `set_player_volume()` → `player_id.volume = volume`
- `stop_player()` → `player_id.pause()` + `player_id.delete()`

**Decision:** The backend audio protocol is complete. AudioManager builds
entirely on these 6 methods. No backend changes for Stage 7.

---

### AssetManager Extensions

`AssetManager` (in `easygame/assets.py`) currently handles images only.
Add two methods:

```python
class AssetManager:
    # NEW in __init__:
    self._sound_cache: dict[str, SoundHandle] = {}
    self._music_cache: dict[str, SoundHandle] = {}

    def sound(self, name: str) -> SoundHandle:
        """Load a sound effect by name. Cached.

        Resolution: assets/sounds/{name}.wav, .ogg, .mp3
        Tries extensions in order: .wav, .ogg, .mp3.
        """

    def music(self, name: str) -> SoundHandle:
        """Load a music track by name (streaming). Cached.

        Resolution: assets/music/{name}.ogg, .wav, .mp3
        Tries extensions in order: .ogg, .wav, .mp3.
        (OGG preferred for music — smaller files, streaming-friendly.)
        """
```

**Extension search order decision:** Sound effects are often WAV (short,
uncompressed, low latency). Music is often OGG (long, compressed, streamed).
The asset manager tries the most likely extension first but accepts any.
This keeps the convention simple: `game.audio.play_sound("sword_hit")` —
no file extension needed.

**Why `.mp3` is last:** MP3 has licensing baggage and pyglet's MP3 support
varies. OGG is universally supported and patent-free. WAV is lossless and
instant-load for short clips. MP3 is a fallback only.

---

### AudioManager Class Design

```python
class AudioManager:
    """Framework-level audio system. Owned by Game as `game.audio`.

    Manages channels, volume hierarchy, music playback with crossfade,
    sound effects, and sound pools.
    """

    def __init__(self, backend, assets: AssetManager) -> None:
        self._backend = backend
        self._assets = assets

        # Channel volumes (0.0–1.0)
        self._volumes: dict[str, float] = {
            "master": 1.0,
            "music": 1.0,
            "sfx": 1.0,
            "ui": 1.0,
        }

        # Current music state
        self._current_player_id: Any | None = None
        self._current_music_name: str | None = None
        self._current_player_base_volume: float = 1.0  # pre-channel volume

        # Crossfade state
        self._crossfade_old_player: Any | None = None
        self._crossfade_tween_ids: list[int] = []

        # Sound pools
        self._pools: dict[str, list[str]] = {}       # pool_name -> [sound_names]
        self._pool_last: dict[str, int] = {}          # pool_name -> last played index

    # --- Public API ---

    def play_sound(self, name: str, *, channel: str = "sfx") -> None:
    def play_music(self, name: str, *, loop: bool = True) -> None:
    def stop_music(self) -> None:
    def crossfade_music(self, name: str, duration: float = 1.0, *, loop: bool = True) -> None:
    def set_volume(self, channel: str, level: float) -> None:
    def get_volume(self, channel: str) -> float:
    def register_pool(self, name: str, sound_names: list[str]) -> None:
    def play_pool(self, name: str) -> None:
```

---

### Channel Volume Hierarchy

**Four channels:** `master`, `music`, `sfx`, `ui`.

**Volume multiplication rule:**
```
effective_volume = master_volume × channel_volume
```

Example: master=0.8, sfx=0.5 → effective SFX volume = 0.4.

**Where volume is applied:**
- `play_sound(name, channel="sfx")` → computes
  `effective = _volumes["master"] * _volumes[channel]` and passes it to
  `backend.play_sound(handle, volume=effective)`.
- `play_music(name)` → computes `effective = _volumes["master"] * _volumes["music"]`
  and passes it to `backend.play_music(handle, volume=effective)`. Also
  stores `_current_player_base_volume = 1.0` (the un-channeled volume,
  used as the basis when channel volumes change later).
- `set_volume(channel, level)` → updates `_volumes[channel]`, then
  re-applies to the current music player if channel is "master" or "music".
  Sound effects are fire-and-forget — volume changes only affect future plays.

**Reapply logic for music when volume changes:**
```python
def set_volume(self, channel: str, level: float) -> None:
    self._volumes[channel] = max(0.0, min(1.0, level))
    # Re-apply to current music player if relevant
    if channel in ("master", "music") and self._current_player_id is not None:
        effective = (self._volumes["master"] * self._volumes["music"]
                     * self._current_player_base_volume)
        self._backend.set_player_volume(self._current_player_id, effective)
```

**Why no per-player channel tracking for SFX:** Sound effects are fire-and-forget
(`backend.play_sound` has no return value to control). Changing SFX volume mid-play
is not needed for our target games. Keeping it simple.

**Why `ui` channel exists:** UI click sounds, hover sounds, notification sounds
should have independent volume from in-game SFX. Players expect this separation
in settings.

---

### Music Playback

```python
def play_music(self, name: str, *, loop: bool = True) -> None:
    """Stop any current music and start playing `name`.

    No crossfade — immediate switch. Use crossfade_music() for
    smooth transitions.
    """
    # Stop current music (if any)
    self.stop_music()

    handle = self._assets.music(name)
    effective = self._volumes["master"] * self._volumes["music"]
    player_id = self._backend.play_music(handle, loop=loop, volume=effective)

    self._current_player_id = player_id
    self._current_music_name = name
    self._current_player_base_volume = 1.0

def stop_music(self) -> None:
    """Stop the current music track."""
    self._cancel_crossfade()
    if self._current_player_id is not None:
        self._backend.stop_player(self._current_player_id)
        self._current_player_id = None
        self._current_music_name = None
```

---

### Crossfade Mechanics Using the Tween System

**Crossfade = two simultaneous music players, one fading out and one fading in,
orchestrated by the existing tween system.**

```python
def crossfade_music(
    self, name: str, duration: float = 1.0, *, loop: bool = True,
) -> None:
    """Crossfade from current music to `name` over `duration` seconds.

    If no music is playing, equivalent to play_music().
    If same track is already playing, no-op.
    """
    if self._current_music_name == name:
        return
    if self._current_player_id is None:
        self.play_music(name, loop=loop)
        return

    # Cancel any in-progress crossfade first
    self._cancel_crossfade()

    # The current player becomes the "old" player (fading out)
    old_player = self._current_player_id
    old_base_volume = self._current_player_base_volume

    # Create the new player (fading in), start at volume 0
    handle = self._assets.music(name)
    new_player = self._backend.play_music(handle, loop=loop, volume=0.0)

    # Update current state to the new player
    self._current_player_id = new_player
    self._current_music_name = name
    self._current_player_base_volume = 1.0

    # Store old player for cleanup
    self._crossfade_old_player = old_player

    # Use a proxy object for tweening (tween system sets attributes)
    fade = _CrossfadeProxy(self, old_player, new_player, old_base_volume)

    from easygame.util.tween import Ease, tween

    # Tween old volume from 1.0 → 0.0
    tid_out = tween(
        fade, "old_volume", old_base_volume, 0.0, duration,
        ease=Ease.LINEAR,
    )
    # Tween new volume from 0.0 → 1.0, on_complete cleans up old player
    tid_in = tween(
        fade, "new_volume", 0.0, 1.0, duration,
        ease=Ease.LINEAR,
        on_complete=lambda: self._finish_crossfade(old_player),
    )
    self._crossfade_tween_ids = [tid_out, tid_in]
```

**Proxy object for crossfade volume tweening:**

The tween system calls `setattr(target, prop, value)`. AudioManager can't be
the target directly because two independent volume properties need to drive
two separate `set_player_volume` calls through the channel hierarchy.

```python
class _CrossfadeProxy:
    """Tween target that forwards volume changes to backend players.

    The tween system sets `old_volume` and `new_volume` each frame.
    The proxy multiplies by master × music channel volume before
    passing to the backend.
    """

    def __init__(self, audio_mgr, old_player_id, new_player_id, old_base):
        self._audio = audio_mgr
        self._old_player = old_player_id
        self._new_player = new_player_id
        self._old_base = old_base  # starting base volume of old player
        self._old_vol = old_base
        self._new_vol = 0.0

    @property
    def old_volume(self) -> float:
        return self._old_vol

    @old_volume.setter
    def old_volume(self, val: float) -> None:
        self._old_vol = val
        effective = (self._audio._volumes["master"]
                     * self._audio._volumes["music"] * val)
        self._audio._backend.set_player_volume(self._old_player, effective)

    @property
    def new_volume(self) -> float:
        return self._new_vol

    @new_volume.setter
    def new_volume(self, val: float) -> None:
        self._new_vol = val
        effective = (self._audio._volumes["master"]
                     * self._audio._volumes["music"] * val)
        self._audio._backend.set_player_volume(self._new_player, effective)
        # Also update AudioManager's tracked base volume for the current player
        self._audio._current_player_base_volume = val
```

**Crossfade cleanup:**
```python
def _finish_crossfade(self, old_player_id) -> None:
    """Called when crossfade completes. Stop the old player."""
    self._backend.stop_player(old_player_id)
    self._crossfade_old_player = None
    self._crossfade_tween_ids.clear()

def _cancel_crossfade(self) -> None:
    """Cancel an in-progress crossfade. Stop the old player immediately."""
    from easygame.util import tween as tween_mod
    mgr = tween_mod._tween_manager
    if mgr is not None:
        for tid in self._crossfade_tween_ids:
            mgr.cancel(tid)
    self._crossfade_tween_ids.clear()
    if self._crossfade_old_player is not None:
        self._backend.stop_player(self._crossfade_old_player)
        self._crossfade_old_player = None
```

**Why LINEAR easing for crossfade:** Audio volume perception is logarithmic,
but for short crossfades (1-2 seconds) linear produces an acceptable result.
Non-linear easing would cause a "dip" in the middle where total volume drops.
Linear keeps total perceived loudness roughly constant during the transition.

**Why proxy object instead of direct tween on AudioManager:** The tween system
calls `setattr(target, prop, val)`. We need each `setattr` to trigger a
`backend.set_player_volume()` call with the channel-adjusted volume. Using
properties on a proxy achieves this cleanly without polluting AudioManager's
namespace.

**Crossfade interruption:** If `crossfade_music("battle")` is called while
a previous crossfade is still in progress, `_cancel_crossfade()` kills the
old tweens and stops the old fading-out player immediately. Then a new
crossfade starts from the current player. This prevents accumulating zombie
players.

---

### Sound Pool Logic

```python
def register_pool(self, name: str, sound_names: list[str]) -> None:
    """Register a named pool of sounds for randomized playback.

    Example:
        game.audio.register_pool("knight_ack",
            ["knight_ack_01", "knight_ack_02", "knight_ack_03"])
    """
    self._pools[name] = list(sound_names)
    self._pool_last[name] = -1  # no previous play

def play_pool(self, name: str) -> None:
    """Play a random sound from the named pool.

    Avoids immediate repetition: if the pool has N>1 sounds, the same
    sound won't play twice in a row.

    Raises KeyError if pool name is not registered.
    """
    sounds = self._pools[name]
    if not sounds:
        return
    if len(sounds) == 1:
        idx = 0
    else:
        import random
        last = self._pool_last[name]
        # Pick from all indices except the last-played one
        candidates = [i for i in range(len(sounds)) if i != last]
        idx = random.choice(candidates)

    self._pool_last[name] = idx
    self.play_sound(sounds[idx])
```

**No-repeat logic:** For pools with N>1 entries, exclude the last-played
index from the random selection. For pools with exactly 1 entry, always play
that one (no choice). For empty pools, silently no-op.

**Why random.choice over random.shuffle:** Shuffle would guarantee full
rotation before repeats, but games don't need that — they need "doesn't
sound repetitive." Excluding only the last index is sufficient and simpler.
A pool of 3 sounds can play A-B-A-C-B (no immediate repeats) which sounds
natural.

---

### Game Integration

```python
# In Game.__init__():
from easygame.audio import AudioManager
self._audio = AudioManager(self._backend, self.assets)

# Public property:
@property
def audio(self) -> AudioManager:
    return self._audio
```

**No per-frame update needed.** AudioManager has no `update(dt)` method.
Crossfade is driven entirely by the tween system (which already updates
in `Game.tick()`). Music and SFX playback are fire-and-forget calls to
the backend. This keeps the game loop unchanged.

**Game.tick() order stays the same** — audio doesn't add a new phase.
The tween phase already handles crossfade volume interpolation.

---

### Public API Exports

In `easygame/__init__.py`, add `AudioManager` to imports and `__all__`:
```python
from easygame.audio import AudioManager
```

Game code accesses audio through `game.audio`, but `AudioManager` should
be importable for type hints:
```python
from easygame import AudioManager  # for type annotations
```

---

### Mock Backend Testing Strategy

The mock backend already tracks:
- `sounds_played: list[str]` — every `play_sound()` call
- `music_playing: str | None` — current music handle
- `music_volume: float` — current player volume
- `_music_players: dict[str, dict]` — all players with `{handle, volume, loop, playing}`

**Test patterns:**
```python
# Test play_sound
game.audio.play_sound("sword_hit")
assert len(backend.sounds_played) == 1

# Test play_music
game.audio.play_music("exploration")
assert backend.music_playing is not None

# Test crossfade
game.audio.play_music("exploration")
game.audio.crossfade_music("battle", duration=1.0)
# Tick past the crossfade duration
for _ in range(70):  # 70 × 0.016 ≈ 1.12s
    game.tick(dt=0.016)
# Old player stopped, new player at full volume
assert backend.music_playing == <battle_handle>

# Test volume hierarchy
game.audio.set_volume("master", 0.5)
game.audio.set_volume("sfx", 0.8)
game.audio.play_sound("click")
# Effective volume passed to backend = 0.5 × 0.8 = 0.4

# Test sound pool no-repeat
game.audio.register_pool("hit", ["hit_01", "hit_02", "hit_03"])
results = set()
for _ in range(20):
    game.audio.play_pool("hit")
# Verify no two consecutive plays are the same handle
```

**Volume assertion on play_sound:** The mock's `play_sound()` currently
appends the handle but doesn't record the volume. Consider extending to
`sounds_played: list[tuple[str, float]]` or `list[dict]` to enable
assertions on effective volume. This is a minor mock enhancement, not a
protocol change.

---

### AssetManager — Audio File Discovery

**Sound effects:** Search `assets/sounds/{name}.wav`, then `.ogg`, then `.mp3`.
**Music:** Search `assets/music/{name}.ogg`, then `.wav`, then `.mp3`.

```python
_SOUND_EXTENSIONS = [".wav", ".ogg", ".mp3"]
_MUSIC_EXTENSIONS = [".ogg", ".wav", ".mp3"]

def sound(self, name: str) -> SoundHandle:
    if name in self._sound_cache:
        return self._sound_cache[name]
    sounds_dir = self._base_path / "sounds"
    handle = self._load_audio(name, sounds_dir, _SOUND_EXTENSIONS, "sound")
    self._sound_cache[name] = handle
    return handle

def music(self, name: str) -> SoundHandle:
    if name in self._music_cache:
        return self._music_cache[name]
    music_dir = self._base_path / "music"
    handle = self._load_audio(name, music_dir, _MUSIC_EXTENSIONS, "music")
    self._music_cache[name] = handle
    return handle

def _load_audio(self, name, base_dir, extensions, kind) -> Any:
    """Try extensions in order, return first match. Raise AssetNotFoundError."""
    tried = []
    for ext in extensions:
        path = base_dir / (name + ext)
        tried.append(str(path))
        if path.exists():
            load_fn = (self._backend.load_sound if kind == "sound"
                       else self._backend.load_music)
            return load_fn(str(path))
    raise AssetNotFoundError(
        f"{kind.title()} asset '{name}' not found. Looked in: {', '.join(tried)}"
    )
```

**Decision:** If the name already has an extension (contains `.`), use it
directly without trying alternatives. Same pattern as `image()` uses for
`"background/forest.jpg"`.

---

### Files to Create/Modify

| File | Change |
|---|---|
| `easygame/audio.py` | **NEW** — AudioManager, _CrossfadeProxy |
| `easygame/assets.py` | Add `sound()`, `music()`, `_sound_cache`, `_music_cache`, `_load_audio()` |
| `easygame/game.py` | Add `self._audio = AudioManager(...)`, `audio` property |
| `easygame/__init__.py` | Add `AudioManager` to imports and `__all__` |
| `backends/base.py` | **Unchanged** — protocol already has all 6 audio methods |
| `backends/mock_backend.py` | Minor: consider recording volume in `sounds_played` for assertions |
| `backends/pyglet_backend.py` | **Unchanged** — already implements all 6 audio methods |
| `tests/test_audio.py` | **NEW** — comprehensive unit tests |
| `tests/visual/test_audio_visual.py` | **NEW** — optional pyglet audio test script |

---

### Critical Design Decisions

1. **AudioManager does NOT have an `update(dt)` method.** Crossfade volume
   interpolation is handled by the tween system, which already runs in
   `Game.tick()`. This avoids adding another phase to the game loop.

2. **Crossfade uses a proxy object as the tween target** instead of tweening
   AudioManager attributes directly. This keeps the tween→backend volume
   pipeline clean and applies channel volume correctly on every frame.

3. **Sound effects are fire-and-forget.** `play_sound()` calls
   `backend.play_sound()` and does not return a handle. No ability to stop
   a playing SFX or change its volume mid-play. This matches DESIGN.md
   (`"fire and forget"`) and simplifies the API significantly.

4. **Music has exactly one logical "current track."** `play_music()` stops
   the old track. `crossfade_music()` manages two players temporarily.
   There's no concept of multiple simultaneous music layers.

5. **`play_sound` accepts an optional `channel` parameter** (default `"sfx"`).
   This allows `play_sound("click", channel="ui")` for UI sounds at a
   different volume than game SFX. DESIGN.md mentions a `ui` channel.

6. **Crossfade to the same track is a no-op.** Prevents accidentally
   restarting the current music.

7. **`_cancel_crossfade()` follows the same pattern as Camera's
   `_cancel_pan()`.** Access `_tween_manager` via the module global,
   guard against `None`, cancel tween IDs, clean up old player. Proven
   pattern from Stage 6.

8. **No streaming reload for pyglet.** Pyglet's `load(streaming=True)`
   returns a source that can only be queued into one player. For crossfade,
   we load the new track fresh each time (caching returns a new streaming
   source). If this is a problem, the cache for music can be a factory
   instead. Verify during implementation whether pyglet allows reusing a
   streaming source across multiple players. If not, music cache should
   call `load_music` each time (no caching for streaming sources).

   **UPDATE: This is a known pyglet limitation.** Streaming sources CANNOT
   be reused across players. The `_music_cache` should NOT cache streaming
   sources. Instead, cache the file path and call `backend.load_music(path)`
   fresh each time. This ensures each player gets its own streaming source.

   Revised approach:
   ```python
   def music(self, name: str) -> SoundHandle:
       """Load a music track. Returns a fresh streaming source each time.

       Unlike sound(), music is NOT cached because pyglet streaming
       sources can only be used by one player at a time.
       """
       # Still resolve the path (which IS cached)
       path = self._resolve_music_path(name)
       return self._backend.load_music(path)
   ```

---

### Implementation Status

**Tests:** 369 total pass (290 pre-existing + 79 new audio). Zero regressions.

### Lessons Learned

- **Lazy `game.audio` property** is better than eager init in `Game.__init__()` — avoids
  creating AudioManager when audio isn't needed (e.g. headless tests, non-audio scenes).
- **`_music_path_cache` (not handle cache)** correctly handles pyglet streaming source limitation.
  Each `music()` call returns a fresh handle from `backend.load_music(path)`.
- **Crossfade proxy pattern** works well with the tween system — no special-casing needed.
  Tween system sets attributes, proxy properties forward to backend with channel math.
- **`_cancel_crossfade()` pattern** mirrors Camera's `_cancel_pan()` — access tween manager
  via module global, guard `None`, cancel IDs, clean up resources. Reusable pattern.
- **Mock backend `sounds_played` recording volume** enables precise effective-volume assertions
  in tests. Simple enhancement to the mock that pays off across many tests.

---
---

## Stage 8 — UI Foundation (COMPLETE)

### Overview

`easygame/ui/` package with component tree, layout system, theming, and three
foundational widgets: Label, Button, Panel. The `desired_examples/menu_desired.py`
API pattern works (minus music and scene transitions from Stage 13).

**Tests:** 448 total pass (369 pre-existing + 67 test_ui + 12 test_theme).
4 screenshot tests + 1 visual test (excluded from normal pytest — require pyglet + GPU).

---

### Files Created

| File | Lines | Purpose |
|---|---|---|
| `easygame/ui/__init__.py` | 18 | Re-exports: Component, Label, Button, Panel, Anchor, Layout, Style, Theme |
| `easygame/ui/layout.py` | 131 | Anchor/Layout enums + pure math (`compute_anchor_position`, `compute_flow_layout`, `compute_content_size`) |
| `easygame/ui/theme.py` | 157 | Style dataclass, ResolvedStyle dataclass, Theme class with 3 resolve methods |
| `easygame/ui/component.py` | 324 | Base Component (tree, layout, hit test, input dispatch, draw) + _UIRoot |
| `easygame/ui/components.py` | 473 | Label, Button, Panel + `_estimate_text_width()` heuristic |
| `tests/test_ui.py` | — | 67 unit tests covering layout math, components, tree ops, integration |
| `tests/test_theme.py` | — | 12 tests for Style, Theme, resolve methods |
| `tests/screenshot/test_ui_screenshots.py` | — | 4 screenshot tests (main menu, horizontal buttons, styled label, nested panels) |

### Files Modified

| File | Change |
|---|---|
| `easygame/backends/base.py` | Added `draw_rect(x, y, width, height, color, *, opacity=1.0)`, revised `draw_text(text, x, y, font_size, color, *, font=None, anchor_x="left", anchor_y="baseline")`, revised `load_font(name, path=None)` |
| `easygame/backends/mock_backend.py` | Added `draw_rect` recording + `self.rects` list + `rects.clear()` in `begin_frame()` |
| `easygame/backends/pyglet_backend.py` | Added `draw_rect` implementation |
| `easygame/scene.py` | Added `_ui: _UIRoot | None = None` class attr + `ui` lazy property |
| `easygame/game.py` | Added `_theme` init, `theme` lazy property, UI input dispatch in tick (before scene), UI draw via SceneStack |
| `easygame/__init__.py` | Added UI re-exports (Anchor, Button, Component, Label, Layout, Panel, Style, Theme) |
| `easygame/scene.py` (SceneStack.draw) | After each scene's `draw()`, draws scene's `_ui` tree if it exists |

---

### Actual API Signatures (as implemented)

**Backend protocol:**
```python
def draw_rect(self, x, y, width, height, color, *, opacity=1.0) -> None
def load_font(self, name: str, path: str | None = None) -> FontHandle
def draw_text(self, text, x, y, font_size, color, *, font=None, anchor_x="left", anchor_y="baseline") -> None
```

**Note:** `draw_text` uses positional args `(text, x, y, font_size, color)` with keyword
`font=handle` and `anchor_x`/`anchor_y` for alignment. `load_font` takes just a name
(not name+size). These differ slightly from the original architecture plan.

**Text size heuristic** (per-character, more accurate than plan's simple multiplier):
```python
def _estimate_text_width(text: str, font_size: int) -> int:
    # uppercase: font_size × 0.95, lowercase: × 0.65, digits: × 0.65
    # spaces: × 0.40, other: × 0.50
```

**Theme merging uses Python 3.12 type parameter syntax:**
```python
def _pick[T](explicit: T | None, default: T) -> T:
    return explicit if explicit is not None else default
```

---

### Key Architecture Decisions (preserved for future stages)

1. **UI renders with `draw_text()` + `draw_rect()`, NOT persistent sprites.**
   Avoids camera sync/restore interference. UI is screen-space, not world-space.

2. **`self.ui` is a lazy property on Scene** (`_ui: _UIRoot | None = None` class attr),
   created on first access. No SceneStack changes needed. Matches `game.audio` pattern.

3. **Input dispatch: UI first, then scene.** In `Game.tick()`, checks
   `top._ui is not None` (not `hasattr` — uses class attr default). UI consumes
   click/release events. Move events inform UI for hover but don't consume.

4. **SceneStack.draw() draws each scene's UI after that scene's draw().** All
   visible scenes (transparent stack) get their UI drawn. Only top scene's UI
   gets input.

5. **Layout is computed lazily** (dirty flag propagates upward). `_ensure_layout()`
   called before draw and before input dispatch.

6. **Content-fit sizing for Panels.** `compute_content_size()` measures children
   with spacing + padding. Panel without explicit dimensions auto-sizes.

7. **Theme + Style merging.** `Style` dataclass with all-optional fields. `Theme`
   class with `resolve_label_style()`, `resolve_button_style(style, state)`,
   `resolve_panel_style()`. Each returns a `ResolvedStyle` (all fields concrete).

8. **`ResolvedStyle` is a full dataclass** with fields: font, font_size, text_color,
   background_color, padding, border_color, border_width, hover_color, press_color.

9. **Button fires on_click on mouse press** (click event), not release. Game UI
   convention for immediate feedback.

10. **`_propagate_game()` is a static method on Component.** Recursively sets `_game`
    on component and all descendants. Called by `add()` and defensively by `_UIRoot.add()`.

11. **Button text draws centered** using `anchor_x="center", anchor_y="center"`.
    Background via `draw_rect`, text position computed as center of computed bounds.

12. **`draw_rect()` and `draw_text()` are per-frame, cleared in `begin_frame()`.**
    Mock records to `self.rects` and `self.texts` lists for test assertions.

13. **`game.theme` lazy property** (same pattern as `game.audio`, `game.assets`).
    Default Theme() if not set. Settable via `game.theme = Theme(...)`.

14. **`easygame/__init__.py` DOES re-export UI classes** (Anchor, Button, Component,
    Label, Layout, Panel, Style, Theme). Both `from easygame import Button` and
    `from easygame.ui import Button` work.

---

### Lessons Learned

- **Per-frame `draw_rect()` was the right call** over persistent sprites for UI
  backgrounds. Clean separation from camera system, no sprite registry pollution.
- **Per-character text width heuristic** (uppercase wider than lowercase) is more
  accurate than the planned simple `len × 0.6 × font_size` multiplier. Good enough
  for layout without needing `backend.measure_text()`.
- **Lazy `Scene.ui` property with `_ui = None` class attr** is cleaner than
  `hasattr` checks. Game.tick() can directly check `top._ui is not None`.
- **Python 3.12 `_pick[T]` generic** works well for theme merging — one-liner
  helper that replaces many if/else blocks.
- **`button_min_width` on Theme** (200px default) prevents buttons from being
  too narrow for short text. Accessed via `self._game.theme.button_min_width`.
- **Panel `Layout.NONE` fallback** to `(100, 100)` when no children and no
  explicit dimensions — prevents zero-size panels.
- **SceneStack handles UI draw** (not Game.tick). This keeps the draw ordering
  correct: each scene's UI draws directly after that scene's content, before
  the next scene in the transparent stack.

---

### What This Stage Does NOT Include

- ImageBox, List, Grid, ProgressBar, TextBox, Tooltip, TabGroup, DataTable (Stage 9)
- Drag-and-drop (Stage 12)
- HUD layer (Stage 13)
- Convenience screens — MessageScreen, ChoiceScreen, etc. (Stage 13)
- Background images for panels (solid colors only; image backgrounds in Stage 9)
- Transition animations for UI components (Stage 9+)
- Keyboard navigation of buttons (Stage 9 — need focus system)
- Border rendering (border_color/border_width fields exist in Style/ResolvedStyle but not rendered yet)

### Bug Fix Applied (review pass)

**Pyglet UI z-order fix** — `draw_rect()` and `draw_text()` in `pyglet_backend.py` were
creating shapes/labels without a `group` parameter, defaulting to order=0. Since sprites
use `Group(order=0..4)`, UI elements could render behind sprites. Fixed by adding a
shared `_ui_overlay_group = Group(order=100)` passed to all `Rectangle` and `Label`
constructors. This ensures UI always renders on top of all sprite layers.

**Button hover stale-state fix** — `Button.on_event` was consuming move events on
hover-enter (`return True`), which prevented sibling buttons from seeing the move.
When moving directly from button A to button B, A stayed stuck in "hovered" state.
Fixed by never consuming move events (`return False` always for moves). All siblings
now see every move and can properly un-hover. Hover is purely visual — no semantic
action is gated on move consumption.

---
---

## Stage 9 — UI Widgets and Text (COMPLETE)

**Tests:** 596 unit tests pass (448 pre-existing + 137 widget + 11 other). 8 new
screenshot tests in `tests/screenshot/test_widget_screenshots.py` (excluded from
normal `pytest` — require pyglet + GPU).

---

### Overview

All 8 DESIGN.md "Standard Components" widgets implemented in a single
`easygame/ui/widgets.py` (1685 lines). Backend extended with `draw_image()`.
Component base class extended with `update(dt)` lifecycle. Theme extended with
7 new resolve methods and 15+ new properties.

---

### Files Created

| File | Lines | Purpose |
|---|---|---|
| `easygame/ui/widgets.py` | 1685 | ImageBox, ProgressBar, TextBox, List, Grid, Tooltip, TabGroup, DataTable + `_word_wrap()` helper |
| `tests/test_widgets.py` | — | 137 unit tests covering all 8 widgets |
| `tests/screenshot/test_widget_screenshots.py` | — | 8 screenshot tests (one per widget) |

### Files Modified

| File | Change |
|---|---|
| `easygame/ui/component.py` | Added `update(dt)` method to Component (no-op default); added `_UIRoot._update_tree(dt)` recursive walk + `_update_recursive()` static method |
| `easygame/ui/theme.py` | Added 15+ Theme constructor params (progressbar, selected, tooltip, tab, datatable colors); added 7 new resolve methods; added 9 new properties |
| `easygame/ui/__init__.py` | Added re-exports for all 8 widgets + `__all__` |
| `easygame/__init__.py` | Added all 8 widgets to imports and `__all__` |
| `easygame/backends/base.py` | Added `draw_image(image_handle, x, y, width, height, *, opacity=1.0)` to Backend protocol |
| `easygame/backends/mock_backend.py` | Added `draw_image()` recording to `self.images` list, cleared in `begin_frame()` |
| `easygame/backends/pyglet_backend.py` | Added `draw_image()` — creates per-frame pyglet Sprite in UI overlay group with y-flip + scaling |
| `easygame/game.py` | Added `_UIRoot._update_tree(dt)` call in tick() update phase (after `scene_stack.update(dt)`, before `flush_pending_ops`) |

---

### Component.update(dt) Lifecycle

Added to `Component` base class as a no-op default. Any widget can override to
drive per-frame animations.

```python
# On Component:
def update(self, dt: float) -> None:
    """Per-frame update hook. Override for animation/typewriter/etc."""
    pass

# On _UIRoot:
def _update_tree(self, dt: float) -> None:
    self._update_recursive(self, dt)

@staticmethod
def _update_recursive(component: Component, dt: float) -> None:
    if not component.visible:
        return
    component.update(dt)
    for child in component._children:
        _UIRoot._update_recursive(child, dt)
```

**Game.tick() wiring** (in update phase, after scene stack update):
```python
top = self._scene_stack.top()
if top is not None and top._ui is not None:
    top._ui._update_tree(dt)
```

**Key detail:** `_update_recursive` skips invisible components. This means Tooltip
(which keeps `Component.visible=True` but uses its own `_visible_now` flag) still
gets `update()` called for its delay timer even while waiting to appear.

**Used by:** TextBox (typewriter reveal), Tooltip (delay timer).

---

### Backend Extension: `draw_image()`

```python
def draw_image(self, image_handle, x, y, width, height, *, opacity=1.0) -> None
```

Per-frame call, cleared each `begin_frame()`. Same lifecycle as `draw_rect()` / `draw_text()`.

- **MockBackend:** Records to `self.images` list (`{image, x, y, width, height, opacity}`).
- **PygletBackend:** Creates a `pyglet.sprite.Sprite` in `_ui_overlay_group`,
  converts logical→physical coords with y-flip, scales to fit. Sprite deleted in
  next `begin_frame()`.

**Why not `create_sprite`:** Persistent sprites participate in camera sync/restore
and live in `_all_sprites`. UI images are screen-space, per-frame — must not
pollute the world-space sprite registry.

---

### Theme Extensions

**7 new resolve methods:**
- `resolve_imagebox_style()` — padding, border only; transparent background
- `resolve_progressbar_style()` — track background from theme
- `resolve_list_style()` — panel background, inherits font/text from base
- `resolve_grid_style()` — panel background, cell layout
- `resolve_tooltip_style()` — dark bg, light text, smaller font (18), compact padding
- `resolve_tabgroup_style()` — tab font/text from dedicated theme params
- `resolve_datatable_style()` — panel background, base font

**9 new Theme properties:**
- `progressbar_color` / `progressbar_bg_color` — fill and track colors
- `selected_color` — shared highlight for List, Grid, DataTable
- `tab_active_color` / `tab_inactive_color` — TabGroup header backgrounds
- `datatable_header_bg_color` / `datatable_header_text_color` — DataTable header
- `datatable_row_bg_color` / `datatable_alt_row_bg_color` — alternating rows

**Theme property pattern:** Widget-specific colors that don't fit in `ResolvedStyle`
are exposed as Theme properties (read via `self._game.theme.progressbar_color`).
Colors that fit the generic `ResolvedStyle` fields (background, text, font) use
the resolve method merge pattern.

---

### Widget Implementation Summary

#### 1. ImageBox (37–91)
- Loads image lazily on first draw via `game.assets.image(image_name)`
- Image handle cached; invalidated on `image_name` setter change
- Uses `draw_image()` backend call
- Default size: 64×64

#### 2. ProgressBar (94–177)
- Two `draw_rect` calls: background track (full width) + fill bar (width × fraction)
- `bar_color`/`bg_color` constructor args with theme property fallbacks
- `fraction` property clamps to [0.0, 1.0]
- No input handling (display only)

#### 3. TextBox (221–435)
- **Word wrapping:** `_word_wrap()` helper splits on spaces, respects `\n`,
  uses `_estimate_text_width()` from components.py. Single word wider than
  max_width placed on its own line (no mid-word break).
- **Typewriter:** `update(dt)` increments `_revealed_count` by `typewriter_speed * dt`.
  `typewriter_speed=0` (default) → instant reveal. Character budget tracked across
  wrapped lines (each line consumes `len(line) + 1` for the separator).
- **Properties:** `revealed_count`, `is_complete`, `skip()`, `reset()`
- **Auto-height:** If no explicit height, sizes to `lines × line_height + 2×padding`
  where `line_height = int(font_size × 1.4)`.
- **Clipping:** Skips lines outside component bounds (no `set_clip_rect` needed).
- **Theme:** Uses `resolve_label_style()` (same as Label — text rendering component).

#### 4. List (442–681)
- Scrollable list with keyboard navigation (`up`/`down` actions) + mouse click
- `on_select: Callable[[int], Any]` callback on selection change
- Scroll via mouse `scroll` events (dy > 0 = scroll up)
- Auto-scroll to keep selected item visible (`_ensure_selected_visible`)
- `_visible_count()` = `computed_h // item_height`
- Draws: background rect → visible items only → selected highlight via `theme.selected_color`

#### 5. Grid (688–933)
- `set_cell(col, row, component)` / `get_cell(col, row)` — cells stored in
  `dict[tuple[int, int], Component]`, components added as children
- `_layout_children()` positions each cell's component in its cell bounds
- `_cell_at(x, y)` → `(col, row) | None` — accounts for spacing gaps
- Click-to-select fires `on_select(col, row)`
- Draws: overall background → cell slot backgrounds → selected cell highlight

#### 6. Tooltip (940–1118)
- **Manual show/hide API:** `show(x, y)` starts delay timer, `hide()` dismisses
- **Delay timer:** `update(dt)` increments `_timer`; `_visible_now = True` when
  `_timer >= delay`. Delay=0 shows immediately.
- **Dual visibility:** `Component.visible` stays True (so `update()` runs);
  drawing gated by `_visible_now` flag.
- **Position:** Offset +12,+16 from cursor, clamped to screen bounds.
- **Rendering order:** Tooltip is a standalone component — add to `_UIRoot` last
  for "on top" drawing. No special overlay pass.
- **No automatic hover-attachment** — manual show/hide only for Stage 9.

#### 7. TabGroup (1125–1367)
- `tabs: dict[str, Component]` maps labels to content components
- **Tab headers:** Drawn directly via `draw_rect` + `draw_text` in `on_draw()`.
  NOT internal Button children (simpler). Tab widths computed from text measurement.
- **Content switching:** `_sync_visibility()` sets `visible=True` on active tab's
  component, `False` on others. All content components are children of TabGroup.
- **Remaining header fill:** If tab headers don't span full width, remaining space
  filled with `tab_inactive_color`.
- **Layout:** `_layout_children()` positions all content components below tab bar.
  Even inactive tabs get layout (prevents stale values).

#### 8. DataTable (1374–1686)
- Column headers + data rows with alternating background colors
- `col_widths: list[int] | None` — explicit or auto-distributed evenly
- `add_row(row)`, `clear_rows()`, `rows` setter with clamp
- Scroll support for many rows (`_scroll_offset`, `_clamp_scroll`)
- Keyboard nav via `up`/`down` actions, mouse click selects row
- Draws: header row (theme header bg/text colors) → data rows (alternating
  `datatable_row_bg_color` / `datatable_alt_row_bg_color`) → selection highlight
  → cell text per column

---

### Architecture Decisions Made

1. **Single `widgets.py` file (1685 lines).** All 8 widgets in one file. It's large
   but cohesive — all follow the same pattern and share `_word_wrap()`. Not split
   because no single widget exceeds the file's readability threshold.

2. **`set_clip_rect` deferred.** TextBox clips by skipping lines outside bounds.
   List draws only visible items. Grid cells have fixed bounds. No backend scissor
   clipping needed for Stage 9.

3. **`fill=True` deferred.** The `desired_examples/ui_dialog_desired.py` needs
   `fill=True` on Panel, but this was not implemented in Stage 9. Deferred to a
   later stage (layout enhancement).

4. **TabGroup draws headers directly** (not via internal Button children). Simpler
   implementation — `on_draw()` computes tab widths from text measurement and draws
   rects + text directly. Click handling in `on_event()` computes which tab from
   x position.

5. **Tooltip uses dual visibility flags.** `Component.visible` stays True so the
   component receives `update(dt)` calls for its delay timer. Drawing is gated
   by the separate `_visible_now` flag. This avoids needing to modify the
   `_update_recursive` skip logic.

6. **TextBox typewriter tracks `_revealed_count` as float.** Allows fractional
   character accumulation across frames (e.g., speed=30 at 60fps reveals 0.5 chars
   per frame). The `revealed_count` property truncates to int.

7. **No auto_scroll_speed on TextBox.** Plan mentioned it, implementation used
   `typewriter_speed` only. Auto-scroll wasn't needed for the validation target.

8. **Grid cell contents are children.** `set_cell()` adds the component as a Grid
   child (via `self.add(component)`). The base `Component.draw()` tree walk handles
   drawing cell contents automatically after `Grid.on_draw()`.

---

### What This Stage Does NOT Include

- `fill=True` for Panel children in flow layout (needed for ui_dialog_desired.py)
- `set_clip_rect` / `clear_clip_rect` backend extension (clipping deferred)
- Automatic tooltip hover-attachment on components (manual show/hide only)
- Drag-and-drop (Stage 12)
- Keyboard navigation of buttons / focus system
- Border rendering (fields exist but not drawn)
- `auto_scroll_speed` on TextBox

---

### Lessons Learned

- **`_update_tree` skips invisible → Tooltip needs dual visibility.** The recursive
  update walk skips `component.visible == False`. Tooltip needs its `update()` called
  even while waiting for the delay. Solution: keep `Component.visible=True`, gate
  drawing on a separate `_visible_now` flag. This pattern will recur for any widget
  with invisible-state timers.

- **`_word_wrap` is reusable.** Standalone function in widgets.py that could serve
  future text widgets. Respects `\n` for explicit line breaks.

- **Tab headers as direct draw calls** (not Button children) is simpler and avoids
  the focus/hover complexity of embedded buttons. Trade-off: no hover feedback on
  tabs. Acceptable for Stage 9.

- **1685 lines in one file is manageable** when all widgets follow the same pattern:
  `__init__` → properties → `get_preferred_size` → `on_event` → `on_draw` →
  `_resolve_style`. The consistent structure makes navigation easy.

- **Per-frame `draw_image` mirrors `draw_rect`/`draw_text`.** Same lifecycle (created
  per frame, cleared in `begin_frame`). PygletBackend creates a pyglet Sprite with
  `_ui_overlay_group`, handles y-flip + scaling. Clean separation from persistent
  world-space sprites.

- **Theme property pattern works well for widget-specific colors.** ProgressBar's
  `bar_color`/`bg_color` constructor args with `theme.progressbar_color` fallback
  keeps the ResolvedStyle generic while still allowing per-widget theming.

---
---

## Stage 10 — Composable Actions (COMPLETE)

**Tests:** 680 total pass (596 pre-existing + 84 unit tests). 7 screenshot tests in
`tests/screenshot/test_action_screenshots.py` (excluded from normal `pytest` — require
pyglet + GPU).

---

### Overview

`easygame/actions.py` — Composable action system inspired by Cocos2d Python. Actions
orchestrate multi-step sprite sequences (walk + animate, delay, fade, remove) as flat,
readable declarations instead of callback nesting or state machines.

11 classes total: `Action` (base) + 10 concrete actions: `Sequence`, `Parallel`,
`Delay`, `Do`, `PlayAnim`, `MoveTo`, `FadeOut`, `FadeIn`, `Remove`, `Repeat`.

---

### Files Created

| File | Purpose |
|---|---|
| `easygame/actions.py` | Action base class + 10 concrete action implementations |
| `tests/test_actions.py` | 84 unit tests covering all action types, compositions, edge cases, and battle sequence integration |
| `tests/screenshot/test_action_screenshots.py` | 7 screenshot tests (walk start/mid, fadeout before/after, battle start/at-target/returning) |

### Files Modified

| File | Change |
|---|---|
| `easygame/rendering/sprite.py` | Added `_current_action`, `do(action)`, `stop_actions()`, `update_action(dt)`; extended `remove()` to stop actions + deregister from `_action_sprites` |
| `easygame/game.py` | Added `_action_sprites: set`, `_update_actions(dt)` method, new action phase in `tick()` between scene update and timers |
| `easygame/__init__.py` | Added re-exports for all 11 action classes + `__all__` entries |

---

### Action Protocol

```python
class Action:
    def start(self, sprite: Sprite) -> None: ...   # called once before first update
    def update(self, dt: float) -> bool: ...        # return True when done
    def stop(self) -> None: ...                     # cancel/cleanup (safe on unstarted)

    @property
    def is_finite(self) -> bool: ...                # True by default; False for looping
```

**Lifecycle:** `start()` → `update()` each frame → either `update()` returns True (done)
or `stop()` called (cancelled). `stop()` must be safe on unstarted actions (no-op).

---

### Game.tick() Integration

Action phase placed after scene update, before timers/tweens/animations:

```
1. poll_events → translate → handle_input → flush
2. scene_stack.update(dt) → UI._update_tree(dt) → flush
3. _update_actions(dt)              ← actions phase
4. _timer_manager.update(dt)
5. _tween_manager.update(dt)
6. _update_animations(dt)
7. camera → draw → restore
```

`_update_actions(dt)` iterates `list(self._action_sprites)` (copy for safe mutation)
and calls `sprite.update_action(dt)` on each. Mirrors `_animated_sprites` pattern.

**Why before timers/tweens:** PlayAnim.start() calls sprite.play() which registers in
`_animated_sprites` — the animation phase runs later in the same tick, so the first
frame updates correctly.

---

### Sprite Integration

```python
sprite.do(action)         # start action, cancels any current; registers in _action_sprites
sprite.stop_actions()     # cancel current action, deregisters from _action_sprites
sprite.update_action(dt)  # called by Game._update_actions; auto-deregisters on completion
```

`sprite.remove()` extended: calls `stop_actions()` before setting `_removed = True`,
then deregisters from `_action_sprites` (belt-and-suspenders after stop_actions).

---

### Key Design Decisions

1. **`update() -> bool`, no excess-dt carry-over.** One-frame error (≤16ms at 60fps)
   is imperceptible. Keeps protocol simple.

2. **Direct per-frame lerp for MoveTo/FadeOut/FadeIn** — NOT the tween system.
   Self-contained: no tween IDs to track, no interference with `_move_tween_ids`,
   clean `stop()` semantics (no-op, sprite stays at current value).

3. **PlayAnim delegates to existing `sprite.play()`** — no duplicate animation logic.
   Watches `on_complete` callback flag. `stop()` calls `sprite.stop_animation()`.
   Looping anims never finish (`is_finite = False`).

4. **`is_finite` property on Action** — Parallel finishes when all **finite** children
   are done, then `stop()`s infinite children. Solves the
   `Parallel(PlayAnim(walk_loop), MoveTo(...))` problem from DESIGN.md examples.

5. **`copy.deepcopy()` for Repeat iterations** — each repetition gets fresh action state
   without adding `reset()` API surface. Actions are lightweight data — deepcopy is cheap.

6. **Sequence chains instant actions in one frame** — `update()` loops: when a child
   finishes, starts the next child immediately and calls its `update(dt=0)`. Prevents
   `Sequence(Do(a), Do(b), Do(c))` from spreading across 3 frames.

7. **`sprite.do(action)` cancels current action** — no concurrent actions on a single
   sprite. Matches `sprite.play()` which replaces current animation.

8. **Parallel tracks `_done: list[bool]`** parallel to `_actions`. Skips `update()` on
   finished children. `stop()` only called on non-finished children.

---

### Lessons Learned

- **Direct lerp vs tween system** was the right call. Action-based movement and fading
  are self-contained — no external state to manage. The tween-based `sprite.move_to()`
  and action-based `MoveTo` can coexist without interference.

- **`is_finite` property** cleanly solves the infinite-inside-Parallel problem without
  special-casing in Parallel's logic. The done condition is simply:
  `all(done[i] or not action.is_finite for i, action in ...)`.

- **Action phase before timers/tweens/animations** ensures correct single-tick
  initialization: PlayAnim.start() → registers in _animated_sprites → animation
  phase updates the first frame in the same tick.

- **84 unit tests** cover: individual actions, nested compositions (Sequence inside
  Parallel, Parallel inside Sequence), edge cases (zero-duration Delay, already-at-target
  MoveTo, removed sprite), and full battle sequence integration matching DESIGN.md
  examples.

---
---

## Stage 11 — Particles, ColorSwap, Cursor (COMPLETE)

**Tests:** 786 unit tests + 42 screenshot tests, all passing. 106 new Stage 11 unit
tests (particles + color_swap + cursor). 13 new screenshot tests (5 particles,
4 color_swap, 4 cursor). Zero regressions.

---

### ParticleEmitter — `easygame/rendering/particles.py`

Managed short-lived `Sprite` particles with randomised velocity, lifetime, and fade.

```python
emitter = ParticleEmitter(
    image="sprites/spark",              # str | list[str] (variety)
    position=(500, 300),                # spawn point (world coords)
    count=30,                           # default burst count
    speed=(50, 200),                    # px/s range
    direction=(0, 360),                 # angle range (degrees, 0=right)
    lifetime=(0.3, 0.8),               # seconds range
    fade_out=True,                      # opacity lerp 255→0
    layer=RenderLayer.EFFECTS,          # default layer
)
emitter.burst(30)            # spawn batch at once
emitter.continuous(rate=20)  # spawn N/sec (accumulates fractional)
emitter.stop()               # halt spawning, let existing die
emitter.remove()             # kill all immediately + deregister
```

Internal `_Particle` dataclass: `sprite, vx, vy, remaining, total_lifetime, fade_out`.

**Game loop integration:** Auto-registers in `Game._particle_emitters` on construction.
`Game._update_particles(dt)` drives updates (after actions, before timers). Inactive
emitters (no particles alive, not spawning) auto-deregister.

**Particle sprites are real Sprites** — they register in `_all_sprites`, participate in
camera transforms and y-sort. Emitter manages lifecycle; calls `sprite.remove()` on death.

**Edge cases handled:** `burst(0)` = no-op; `burst()` after `stop()` re-registers;
`remove()` deregisters immediately; no Game = RuntimeError.

---

### ColorSwap — `easygame/rendering/color_swap.py`

Per-pixel color replacement at image load time. One-time Pillow cost, cached as GPU texture.

```python
swap = ColorSwap(
    source_colors=[(255, 0, 0), (200, 0, 0)],
    target_colors=[(0, 0, 255), (0, 0, 200)],
)
swap.apply(image_path) -> PIL.Image.Image   # load, replace, return
swap.cache_key() -> tuple                    # hashable for caching
```

**Validation:** `len(source_colors) != len(target_colors)` raises `ValueError`.
Alpha is preserved; unmatched pixels are unchanged.

**Palette registry** (global convenience):
```python
register_palette("blue", ColorSwap(...))
get_palette("blue") -> ColorSwap            # KeyError if not registered
```

**Sprite integration:** New constructor params `color_swap` and `team_palette`:
```python
Sprite("knight", color_swap=swap)           # explicit swap
Sprite("knight", team_palette="blue")       # registry lookup
# color_swap takes precedence over team_palette
```

**AssetManager integration:** `image_swapped(name, color_swap)` method caches per
`(name, swap.cache_key())`. Refactored `_resolve_image_path()` out of `_load_image()`
for path reuse.

---

### CursorManager — `easygame/cursor.py`

Named cursor registry with hotspot support.

```python
game.cursor.register("attack", "ui/cursor_attack", hotspot=(8, 8))
game.cursor.set("attack")
game.cursor.set("default")   # restore system cursor (no registration needed)
game.cursor.set_visible(False)
game.cursor.current           # -> "attack" or "default"
```

**Game integration:** Lazy property `game.cursor` (same pattern as `game.audio`,
`game.theme`). CursorManager stores `(image_handle, hotspot)` per name.

---

### Backend Protocol Extensions

Three new methods added to `Backend` protocol (`backends/base.py`):

| Method | Purpose |
|---|---|
| `load_image_from_pil(pil_image)` | PIL Image → backend texture handle (bridge for ColorSwap) |
| `set_cursor(image_handle, hotspot_x, hotspot_y)` | Set custom cursor; `None` restores system |
| `set_cursor_visible(visible)` | Show/hide mouse cursor |

**MockBackend:** `load_image_from_pil` returns `"pil_img_N"` handle, stores dimensions.
Cursor tracking fields: `cursor_image`, `cursor_hotspot`, `cursor_visible`.

**PygletBackend:** `load_image_from_pil` converts PIL → pyglet `ImageData` with negative
pitch (top-down → bottom-up). `set_cursor` creates `ImageMouseCursor` with y-flipped
hotspot (`hot_y = image_height - framework_hotspot_y`).

---

### Public API Exports

Added to `easygame/__init__.py` and `__all__`:
- `ParticleEmitter` (from `easygame.rendering.particles`)
- `ColorSwap` (from `easygame.rendering`)
- `register_palette`, `get_palette` (from `easygame.rendering`)
- `CursorManager` (from `easygame.cursor`)

Added to `easygame/rendering/__init__.py`:
- `ParticleEmitter`, `ColorSwap`, `get_palette`, `register_palette`

---

### Game Loop Order (updated)

```
1. poll_events → translate → handle_input → flush
2. scene_stack.update(dt) → UI._update_tree(dt) → flush
3. _update_actions(dt)
4. _update_particles(dt)          ← Stage 11
5. _timer_manager.update(dt)
6. _tween_manager.update(dt)
7. _update_animations(dt)
8. camera → draw → restore
```

---

### Files Created

| File | Contents |
|---|---|
| `easygame/rendering/particles.py` | `ParticleEmitter`, `_Particle` dataclass |
| `easygame/rendering/color_swap.py` | `ColorSwap`, `register_palette`, `get_palette`, `_TEAM_PALETTES` |
| `easygame/cursor.py` | `CursorManager` |
| `tests/test_particles.py` | Particle unit tests (burst, continuous, lifecycle, remove, integration) |
| `tests/test_color_swap.py` | ColorSwap unit tests (pixel swap, alpha, caching, sprite, palette) |
| `tests/test_cursor.py` | Cursor unit tests (register, set, visible, backend calls, game integration) |
| `tests/screenshot/test_particles_screenshots.py` | 5 screenshot tests (burst variants) |
| `tests/screenshot/test_color_swap_screenshots.py` | 4 screenshot tests (original vs swapped) |
| `tests/screenshot/test_cursor_screenshots.py` | 4 screenshot tests (default, custom, restore, visibility) |
| `tests/visual/test_stage11_visual.py` | Visual test (particles + color swap + cursor, pyglet) |

### Files Modified

| File | Change |
|---|---|
| `easygame/backends/base.py` | `load_image_from_pil()`, `set_cursor()`, `set_cursor_visible()` in protocol |
| `easygame/backends/mock_backend.py` | Implemented 3 new methods + cursor tracking fields |
| `easygame/backends/pyglet_backend.py` | Implemented 3 new methods (PIL→ImageData, ImageMouseCursor, mouse_visible) |
| `easygame/assets.py` | `_swapped_cache`, `image_swapped()`, `_resolve_image_path()` refactor |
| `easygame/rendering/sprite.py` | `color_swap` and `team_palette` constructor params |
| `easygame/game.py` | `_particle_emitters` set, `_update_particles(dt)`, `cursor` lazy property |
| `easygame/rendering/__init__.py` | Re-exports for `ColorSwap`, `ParticleEmitter`, `get_palette`, `register_palette` |
| `easygame/__init__.py` | Re-exports + `__all__` for all Stage 11 public API |

---

### Design Decisions (confirmed from plan)

1. **Particles are real Sprites** — participate in camera/y-sort. Emitter manages lifecycle.
   Appropriate at target scale (tens to low hundreds of particles).

2. **ParticleEmitter auto-registers with Game** — same pattern as animations/actions.
   Scene code doesn't need manual `emitter.update(dt)`.

3. **ColorSwap is load-time, not per-frame** — Pillow processes once, cached as texture.

4. **`load_image_from_pil()` bridges PIL↔backend** — generic enough for future procedural textures.

5. **Cursor hotspot y-flip in PygletBackend** — framework y-down → pyglet y-up conversion.

6. **`team_palette` is convenience sugar** — lookup into global `_TEAM_PALETTES` registry.

7. **Emitter auto-deregisters when inactive** — prevents dead emitters from wasting iteration.

---
---

## Stage 12 — Drag-and-Drop and FSM (COMPLETE)

**Tests:** 848 total (49 drag-drop + 13 FSM unit tests). 50 screenshot tests
(3 drag-drop + 5 FSM). Zero regressions.

---

### Part 1: DragManager — `easygame/ui/drag_drop.py` (286 lines)

Central coordinator for drag-and-drop sessions, owned lazily by `_UIRoot`.

```python
from easygame import DragManager  # or from easygame.ui import DragManager

# Any component can be a drag source
slot = ImageBox(icon, draggable=True, drag_data=item)

# Any container can be a drop target
grid = Grid(
    columns=4, rows=3,
    drop_accept=lambda data: isinstance(data, Item),
    on_drop=lambda comp, data: equip_item(comp, data),
)
```

#### Component Extensions (on base `Component`)

Four optional attrs added to `Component.__init__()` in `component.py`:
- `draggable: bool = False` — can this component be dragged?
- `drag_data: Any = None` — opaque payload from source to target
- `drop_accept: Callable[[Any], bool] | None = None` — if set, accepts drops
- `on_drop: Callable[[Component, Any], Any] | None = None` — fires on valid drop

**Why on Component, not a mixin:** Zero cost for non-drag components (False/None defaults),
any widget gets drag behavior via kwargs, no multiple inheritance.

#### Architecture: DragManager on _UIRoot

`_UIRoot` lazily creates a `DragManager` via `drag_manager` property. During an active
drag, `_UIRoot.handle_event()` routes ALL input to DragManager (bypassing normal tree
dispatch). `_UIRoot.draw()` calls `_draw_ghost()` after children for overlay rendering.

#### Event Flow

1. **Start:** Left `"click"` on `draggable=True` component — checked in
   `Component.handle_event()` BEFORE `on_event()` (ensures drag beats Button.on_click).
   Accesses DragManager via `self._game._scene_stack.top()._ui.drag_manager`.
2. **Move:** DragManager handles `"move"` and `"drag"` events — updates ghost position
   using absolute `event.x/y`, finds deepest drop target via `_walk_for_target()` tree
   walk, evaluates `drop_accept(data)` → sets `target_accepts`.
3. **Drop:** On `"release"`, re-evaluates target. If `target_accepts` and `on_drop` set,
   calls `target.on_drop(target, data)`. Clears session.
4. **Cancel:** Escape (`key_press` with `action="cancel"`) clears session.

#### Ghost and Target Highlight Rendering

Ghost drawn in `_draw_ghost()` after all children:
- ImageBox sources: `backend.draw_image(handle, ghost_x, ghost_y, w, h, opacity=theme.ghost_opacity)`
- Other sources: `backend.draw_rect(ghost_x, ghost_y, w, h, (180,180,180,128), opacity=theme.ghost_opacity)`

Drop target overlay (DragManager draws, not the target component):
- Valid: `theme.drop_accept_color` — default `(0, 180, 0, 80)` (green)
- Invalid: `theme.drop_reject_color` — default `(180, 0, 0, 80)` (red)

#### Theme Extensions (`theme.py`)

Three new `Theme.__init__` params and properties:
- `drop_accept_color: Color = (0, 180, 0, 80)` — green overlay
- `drop_reject_color: Color = (180, 0, 0, 80)` — red overlay
- `ghost_opacity: float = 0.5` — ghost transparency

---

### Part 2: StateMachine — `easygame/util/fsm.py` (88 lines)

Pure logic FSM, no game/backend dependency. Event-driven transitions with enter/exit callbacks.

```python
from easygame import StateMachine  # or from easygame.util import StateMachine

fsm = StateMachine(
    states=["idle", "walking", "attacking", "dead"],
    initial="idle",
    transitions={
        "idle": {"move": "walking", "attack": "attacking", "die": "dead"},
        "walking": {"arrive": "idle", "attack": "attacking", "die": "dead"},
        "attacking": {"done": "idle", "die": "dead"},
    },
    on_enter={"idle": lambda: sprite.play(idle_anim)},
    on_exit={"walking": lambda: stop_footsteps()},
)

fsm.state           # "idle"
fsm.trigger("move") # True — transitions to "walking", fires on_exit/on_enter
fsm.trigger("fly")  # False — no such transition, silent no-op
fsm.valid_events    # ["arrive", "attack", "die"]
```

#### Key Decisions

1. `trigger()` returns bool, never raises on invalid event (game-friendly)
2. No `update(dt)` — purely event-driven; use `game.after()` for timed transitions
3. `states` list validates `initial` and all transition targets at construction
4. `on_enter[initial]` fires immediately on construction; `on_exit` does NOT
5. Self-transitions allowed — both `on_exit` and `on_enter` fire
6. `transitions=None` → no transitions, stays in initial forever (state holder)
7. `dead` state with no entry in transitions → absorbing state

---

### Files Modified

| File | Change |
|---|---|
| `easygame/ui/drag_drop.py` | **NEW** — `DragManager`, `_DragSession` (286 lines) |
| `easygame/util/fsm.py` | **NEW** — `StateMachine` (88 lines) |
| `easygame/ui/component.py` | `Component.__init__`: 4 drag attrs. `handle_event`: drag-start before `on_event`. `_UIRoot`: lazy `drag_manager`, overridden `handle_event`/`draw` |
| `easygame/ui/theme.py` | `drop_accept_color`, `drop_reject_color`, `ghost_opacity` params + properties |
| `easygame/__init__.py` | Added `DragManager`, `StateMachine` to imports and `__all__` |
| `easygame/ui/__init__.py` | Added `DragManager` to re-exports |
| `easygame/util/__init__.py` | Added `StateMachine` to re-exports |
| `game.py`, `backends/*` | **No changes** — drag uses existing input/draw paths |

---

### Lessons Learned

1. **Drag-start in `handle_event` not `on_event`** — putting drag check before `on_event()` call ensures drag takes precedence over subclass click handlers (e.g. Button.on_click) without subclasses needing drag awareness.

2. **DragManager draws overlays, not components** — keeps existing widget `on_draw()` methods clean. No "am I being drag-hovered?" flag needed on Component.

3. **Both `"move"` and `"drag"` event types** — backend generates `"drag"` (with dx/dy) for held-button movement and `"move"` for no-button. DragManager handles both, using absolute x/y (not deltas) for ghost position.

4. **Lazy DragManager** — follows established pattern (game.audio, game.theme, scene.ui). No overhead for scenes that don't use drag-drop.

---
---

## Stage 13 — Convenience Screens, Save/Load, HUD, Settings (COMPLETE)

**Tests:** 1017 unit tests pass (848 pre-existing + 169 new). 56 screenshot tests
(50 pre-existing + 6 new in `tests/screenshot/test_stage13_screenshots.py`).

**Framework is feature-complete.** All 14 stages (0–13) from PLAN.md are implemented.

---

### Overview

Stage 13 adds convenience screens (MessageScreen, ChoiceScreen, ConfirmDialog,
SaveLoadScreen), the Save/Load system (SaveManager + Scene protocol), the HUD
layer, a built-in settings screen, and `game.show_sequence()`. All features are
pure framework composition — **no backend changes needed**.

---

### Files Created

| File | Lines | Purpose |
|---|---|---|
| `easygame/ui/screens.py` | 603 | MessageScreen, ChoiceScreen, ConfirmDialog, SaveLoadScreen, _SequenceRunner, _SettingsScene |
| `easygame/ui/hud.py` | 105 | HUD layer — persistent UI above base scenes, below overlays |
| `easygame/save.py` | 123 | SaveManager — JSON save files with slot system |
| `tests/test_screens.py` | — | Unit tests for all convenience screens |
| `tests/test_hud.py` | — | Unit tests for HUD layer |
| `tests/test_save.py` | — | Unit tests for SaveManager |
| `tests/screenshot/test_stage13_screenshots.py` | — | 6 screenshot tests |

### Files Modified

| File | Change |
|---|---|
| `easygame/scene.py` | Added `get_save_state() -> dict`, `load_save_state(state)` to Scene; rewrote `SceneStack.draw()` with HUD interleaving |
| `easygame/game.py` | Added `save_dir` constructor param, `save_manager`/`hud` lazy properties, `save()`/`load()`, `show_sequence()`, `push_settings()`; HUD input/update in `tick()` |
| `easygame/__init__.py` | Added re-exports: MessageScreen, ChoiceScreen, ConfirmDialog, SaveLoadScreen, HUD, SaveManager |
| `easygame/ui/__init__.py` | Added re-exports: HUD, MessageScreen, ChoiceScreen, ConfirmDialog, SaveLoadScreen |

---

### Convenience Screens — `easygame/ui/screens.py`

All screens are `Scene` subclasses with `transparent = True`, `show_hud = False`.
They build UI in `on_enter()` using existing components. All consume **all** events
(modal overlays — `handle_input` returns `True` for everything).

#### MessageScreen

```python
MessageScreen(text: str, *, on_dismiss: Callable | None = None)
```

- Dark semi-transparent `Panel(anchor=CENTER)` with centered text `Label` + "Press any key..." hint
- Dismisses on `key_press` or `click` (not move) → fires `on_dismiss()` → `game.pop()`
- No `style` parameter (simplified from spec) — uses hardcoded text colors

#### ChoiceScreen

```python
ChoiceScreen(prompt: str, choices: list[str], *, on_choice: Callable[[int], Any] | None = None)
```

- Vertical list of `Button` instances, one per choice
- **Number key shortcuts:** keys `1`–`9` select index `0`–`8` directly
- Escape pops without firing `on_choice` (cancels)
- Closure capture via `make_handler(index)` factory pattern

#### ConfirmDialog

```python
ConfirmDialog(question: str, *, on_confirm: Callable | None = None, on_cancel: Callable | None = None)
```

- "Yes" and "No" buttons in horizontal row
- Enter key → confirm, Escape key → cancel
- Both `on_confirm`/`on_cancel` fire before `game.pop()`

#### SaveLoadScreen

```python
SaveLoadScreen(
    mode: str = "load",  # "save" or "load"
    *,
    save_manager: SaveManager,  # required — not auto-discovered
    on_save: Callable[[int], Any] | None = None,
    on_load: Callable[[int, dict], Any] | None = None,
    slot_count: int = 10,
)
```

- Lists slots as buttons with timestamp metadata
- **Save mode:** walks the stack (`game._scene_stack._stack`) to find the first
  non-SaveLoadScreen scene and calls `target_scene.get_save_state()`. This ensures
  the overlay saves the *game* scene's state, not its own.
- **Load mode:** only acts on non-empty slots; fires `on_load(slot, data)` with full save dict
- Back button + Escape to dismiss

#### _SequenceRunner (internal)

```python
_SequenceRunner(screens: list[MessageScreen], on_complete: Callable | None = None)
```

- Sits below MessageScreens on the stack
- Uses `on_reveal()` lifecycle: when a screen is dismissed (popped), the runner
  gets `on_reveal()` and pushes the next screen
- When all screens shown → fires `on_complete()` → pops itself
- Empty screens list → fires `on_complete` immediately and pops

#### _SettingsScene (internal)

- **Volume controls:** 4 channels (master, music, sfx, ui), each with:
  - Channel name `Label(width=80)`
  - "−" `Button` → `_adjust_volume(channel, -0.1)`
  - `ProgressBar(value=vol*100, max_value=100, width=150, height=20)`
  - "+" `Button` → `_adjust_volume(channel, +0.1)`
  - Percentage `Label(width=50)` showing `"{int}%"`
- Stores `_volume_bars: dict[str, ProgressBar]` and `_volume_labels: dict[str, Label]`
  for live UI updates when buttons are clicked
- **Key rebinding:** reads `game.input.get_bindings()`, displays sorted action → key pairs
  - Click button → `_start_listening(action, button)` → button text becomes `"[...]"`
  - Next key press → `game.input.bind(action, key)` → button text updates to `"[KEY]"`
  - Escape during listening → cancels, restores original key display
  - Uses `_listening_action: str | None` and `_listening_button: Button | None` state
  - `btn_ref: list[Button | None]` closure trick for button self-reference
- Back button + Escape to dismiss

---

### Save/Load System — `easygame/save.py`

#### SaveManager

```python
class SaveManager:
    def __init__(self, save_dir: Path) -> None: ...
    def save(self, slot: int, state: dict, scene_class_name: str) -> None: ...
    def load(self, slot: int) -> dict | None: ...
    def list_slots(self, count: int = 10) -> list[dict | None]: ...
    def delete(self, slot: int) -> None: ...
```

- JSON format: `{"version": 1, "timestamp": "ISO-8601", "scene_class": "...", "state": {...}}`
- `list_slots()` adds a `"slot"` key to each entry for convenience
- Uses `datetime.now(tz=timezone.utc).isoformat()` for timestamps
- `save()` creates dir with `mkdir(parents=True, exist_ok=True)` on every save
- File naming: `save_{slot}.json`

#### Scene Protocol

```python
class Scene:
    def get_save_state(self) -> dict: ...        # returns {} by default
    def load_save_state(self, state: dict): ...  # no-op by default
```

#### Game Integration

```python
class Game:
    def __init__(self, ..., save_dir: Path | str | None = None): ...

    @property
    def save_manager(self) -> SaveManager:  # lazy; default dir: ~/.{slug}/saves/

    def save(self, slot: int) -> None:      # top scene's get_save_state() → SaveManager
    def load(self, slot: int) -> dict | None:  # returns raw data; game code reconstructs
```

- `save_dir` override parameter in Game constructor
- Default directory derived from title: `"My Game"` → `~/.my_game/saves/`
- **Framework does NOT auto-reconstruct scenes** — `load()` returns the dict,
  game code creates the scene and calls `scene.load_save_state(data["state"])`

---

### HUD Layer — `easygame/ui/hud.py`

```python
class HUD:
    def __init__(self, game: Game) -> None: ...
    visible: bool = True

    def add(self, component: Component) -> None: ...
    def remove(self, component: Component) -> None: ...
    def clear(self) -> None: ...

    # Internal (called by Game.tick and SceneStack.draw):
    def _should_draw(self, top_scene_show_hud: bool) -> bool: ...
    def _handle_event(self, event: InputEvent) -> bool: ...
    def _update(self, dt: float) -> None: ...
    def _draw(self) -> None: ...
```

- Wraps a `_UIRoot` internally
- Visibility: `hud.visible AND top_scene.show_hud` (both must be True)
- **Lazy property:** `game.hud` creates HUD on first access (same pattern as `game.audio`)

#### Draw Order (SceneStack.draw)

```
1. Base scene (lowest opaque) + its UI
2. HUD (if visible and top.show_hud)
3. Transparent overlay scenes + their UIs (bottom-up)
```

This ensures HUD renders above game content but below modals like ConfirmDialog.

#### Input Order (Game.tick)

```
1. HUD._handle_event(event) — first priority
2. Scene UI (top._ui.handle_event) — second
3. scene.handle_input(event) — last
```

HUD only receives input when `_should_draw()` is True (same visibility check).

#### Update Order (Game.tick)

```
1. scene_stack.update(dt) — scene logic
2. top._ui._update_tree(dt) — scene UI animations
3. hud._update(dt) — HUD UI animations (if visible)
```

---

### Game Convenience Methods

```python
def show_sequence(self, screens: list, *, on_complete: Callable | None = None) -> None:
    """Push a chain of screens that auto-advance via _SequenceRunner."""

def push_settings(self) -> None:
    """Push the built-in settings screen (_SettingsScene)."""
```

Both use lazy imports from `easygame.ui.screens`.

---

### Public API Exports

| Symbol | `easygame.__init__` | `easygame.ui.__init__` |
|---|---|---|
| `MessageScreen` | ✓ | ✓ |
| `ChoiceScreen` | ✓ | ✓ |
| `ConfirmDialog` | ✓ | ✓ |
| `SaveLoadScreen` | ✓ | ✓ |
| `HUD` | ✓ | ✓ |
| `SaveManager` | ✓ | — |

`_SequenceRunner` and `_SettingsScene` are **not exported** — internal only.

---

### Key Design Decisions

1. **All convenience screens are Scene subclasses** — no special infrastructure.
   They use `self.game`, `self.ui`, `self.game.push()/pop()` like any scene.

2. **Modal pattern:** All screens set `transparent = True`, `show_hud = False`,
   and return `True` from `handle_input` for all events. This creates clean modal
   behavior — the HUD hides, input is fully captured, but the scene below is visible.

3. **`_SequenceRunner` uses `on_reveal()` lifecycle** — elegant chaining without
   callbacks or timers. Each dismissed screen triggers the next push.

4. **SaveLoadScreen requires explicit `save_manager`** — not auto-discovered from
   `game.save_manager`. This keeps the screen decoupled and testable.

5. **Settings is internal (`_SettingsScene`)** — not customizable, not exported.
   Games that want a custom settings screen build their own.

6. **ProgressBar + buttons for volume** (not clickable ProgressBar) — keeps
   ProgressBar as display-only per DESIGN.md.

7. **Save directory default: `~/.{game_slug}/saves/`** — cross-platform via
   `Path.home()`. Overridable via `Game(save_dir=...)`.

8. **No backend changes needed** — all Stage 13 features use existing draw_rect,
   draw_text, component tree, and scene stack. Pure framework-level composition.

9. **SceneStack.draw() rewritten for HUD interleaving** — walks stack to find
   lowest visible scene, draws base → HUD → overlays. Clean separation of concerns.

---

### Lessons Learned

- **`on_reveal()` is the key to sequence chaining** — `_SequenceRunner` is only ~50
  lines because the scene stack lifecycle does all the work. No timers, no polling.

- **Stack walking for save target** — `SaveLoadScreen._on_slot_click` walks
  `game._scene_stack._stack` in reverse to find the first non-overlay scene. This
  accesses internal state but is the correct approach for an overlay that needs to
  save the scene below it.

- **`btn_ref` list trick for closures** — settings key rebinding needs the button
  reference inside its own click handler. Using `btn_ref: list[Button | None] = [None]`
  with deferred assignment avoids forward-reference issues.

- **Live UI updates via stored references** — `_volume_bars` and `_volume_labels`
  dicts allow instant ProgressBar/Label updates when volume buttons are clicked.
  Uses `Button.text` setter (marks layout dirty) and `ProgressBar.value` setter.

- **Lazy subsystem pattern proven at scale** — `game.hud`, `game.save_manager`
  follow the same lazy-property pattern as `game.audio`, `game.theme`, `game.cursor`.
  No overhead for scenes that don't use these features.

- **`show_hud = False` on overlay scenes** was already declared on Scene (default True)
  since Stage 8 but unused. Stage 13 activates it through `SceneStack.draw()` and
  `Game.tick()` HUD visibility checks.

---

### Deviations from Spec

1. **MessageScreen**: no `style` parameter (spec had optional Style for text label).
   Hardcoded text colors work fine for the 80% case.

2. **SaveLoadScreen**: uses Button-per-slot (not List widget). Simpler implementation
   that handles both save and load modes cleanly. Spec suggested List widget.

3. **HUD input dispatch**: uses `_should_draw()` check (same visibility gate as
   drawing). Spec mentioned "HUD gets events first" but didn't specify the visibility
   guard. Implementation correctly only dispatches events when HUD is visible.

---

### Architect Review — Bugs Fixed (Stage 13)

1. **SaveLoadScreen required `save_manager` kwarg** — DESIGN.md shows `SaveLoadScreen()`
   with no args (line 893, 917). Fixed: `save_manager` param is now optional, defaults
   to `self.game.save_manager` via a property. Tests still pass with explicit manager.

2. **`game.load(slot)` didn't call `scene.load_save_state()`** — DESIGN.md (line 892)
   and PLAN.md (line 1261) both specify that `game.load()` deserializes AND restores.
   The implementation only returned the dict. Fixed: now calls
   `top.load_save_state(data["state"])` on the current top scene, then returns data.
   Direct `save_manager.load()` is available for manual reconstruction.

3. **Type annotations** — `make_vol_handler` and `make_rebind_handler` in
   `_SettingsScene` had `-> None` return type but returned a `Callable`. Fixed to
   `-> Callable[[], None]`.

### Lessons Learned

- **Always diff implementation constructor signatures against DESIGN.md examples.**
  The Standard Game Flow Example is the ground truth for public API shapes.
- **"Framework handles" comments in DESIGN.md are binding** — if the spec says
  `game.load()` "deserializes and restores", the method must do both, not punt
  to game code. Provide a lower-level escape hatch (`save_manager.load()`) for
  advanced cases.
