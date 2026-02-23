# Stage 7 Demo Retrospective — Battle Vignette

The battle vignette demo (`examples/battle_vignette/battle_demo.py`) is the first
real integration test of the framework.  It exercises Stages 0 through 5 in concert:
mock backend, sprites, animation, tweens, timers, input, and scene lifecycle.  This
document records what worked, what didn't, what we fixed, and what Stage 10 (Actions)
will improve.

---

## 1. What the Demo Exercised

### AnimationDef (Stage 3)

Both declaration styles work cleanly:

```python
# Explicit frame list — single-frame "animation" for idle poses
WARRIOR_IDLE = AnimationDef(
    frames=["sprites/warrior_idle_01"],
    frame_duration=1.0,
    loop=True,
)

# Prefix discovery — finds warrior_walk_01.png .. warrior_walk_04.png on disk
WARRIOR_WALK = AnimationDef(
    frames="sprites/warrior_walk",
    frame_duration=0.12,
    loop=True,
)
```

**Verdict:** Clean separation between definition (data) and playback (runtime state).
Definitions can be module-level constants because they hold names, not handles.  Prefix
discovery (`frames="sprites/warrior_walk"`) is the right default for numbered sprite
sheets.  No issues found.

### Sprite.play / Sprite.move_to (Stages 2-3)

The compound animation pattern — play a walk animation while moving — works exactly as
designed:

```python
attacker.sprite.play(WARRIOR_WALK)
attacker.sprite.move_to(
    (target_x, dy),
    speed=MOVE_SPEED,
    on_arrive=lambda: self._phase_attack_anim(attacker, defender),
)
```

`play()` swaps frame animation immediately.  `move_to()` tweens position.  They compose
because they operate on independent state (animation player vs. position tweens).  The
`on_arrive` callback fires exactly once when the move completes.

**Verdict:** The primitive-level API is solid.  The _composition_ of primitives into
multi-step sequences is where friction appears (see Section 2).

### tween() (Stage 4)

Used for fade-out on death and floating damage numbers:

```python
tween(
    defender.sprite, "opacity",
    255.0, 0.0, 0.5,
    ease=Ease.EASE_OUT,
    on_complete=lambda: self._phase_cleanup_dead(attacker, defender),
)
```

**Verdict:** Works correctly.  The `from_val` requirement is friction (see Section 2).

### game.after() (Stage 4)

Used for the 0.3-second delay between attack animation finishing and the hit reaction
starting:

```python
self.game.after(
    0.3,
    lambda: self._phase_hit_reaction(attacker, defender),
)
```

**Verdict:** Simple and correct.  The timer fires once after the delay, no issues.

### InputEvent / handle_input (Stage 5)

```python
def handle_input(self, event: InputEvent) -> bool:
    if event.action == "cancel":
        self.game.quit()
        return True

    if event.type == "click" and event.button == "left":
        self._handle_click(event.x, event.y)
        return True

    return False
```

**Verdict:** Action mapping (`"cancel"` for Escape) and raw mouse events coexist
naturally.  The `return True` consumption pattern prevents events from leaking through
to scenes below.  Clean.

### Scene lifecycle (Stage 1)

`on_enter` initializes all state, `game.push()` starts the scene.  The demo uses a
single scene so `on_exit` / `on_reveal` are untested here, but `on_enter` timing is
correct — state is initialized before the first `tick()`.

### Mock backend (Stage 0) — testability

The mock backend proved its worth.  The 31-test headless suite runs in 0.07 seconds
and validates the entire 6-phase attack choreography without opening a window:

```python
game = Game("Battle Test", backend="mock", resolution=(1920, 1080))
game.assets = AssetManager(game.backend, base_path=ASSET_DIR)

scene = BattleScene()
game.push(scene)
game.tick(dt=0.0)

# Inject input and tick deterministically
backend.inject_click(300, 350)   # click warrior
game.tick(dt=0.0)
backend.inject_click(1620, 350)  # click skeleton
game.tick(dt=0.0)

# Tick through the full attack sequence
for _ in range(15 * 60):
    game.tick(dt=1/60)
    if not scene.busy:
        break
```

`inject_click()` + deterministic `tick(dt=...)` makes the entire callback chain
testable.  No timing flakiness, no display dependency.

---

## 2. Friction Points

### 2.1 Callback Nesting Depth

The 6-phase attack choreography requires **8 separate methods**, each wiring the next
via a callback parameter:

```
_begin_attack          → on_arrive → _phase_attack_anim
_phase_attack_anim     → on_complete → _phase_delay
_phase_delay           → game.after → _phase_hit_reaction
_phase_hit_reaction    → on_complete → _phase_death OR _phase_defender_recover
_phase_death           → on_complete → _phase_fade_and_remove
_phase_fade_and_remove → on_complete → _phase_cleanup_dead
_phase_cleanup_dead    → (calls) → _phase_walk_home
_phase_walk_home       → on_arrive → _phase_done
```

Each method exists solely to chain to the next.  The control flow is invisible — you
can't see the sequence without reading all 8 methods and mentally tracing the callback
wiring.  Adding a step (e.g., a sound effect between phases 2 and 3) means inserting a
new method and re-wiring two callbacks.

This is the classic "callback hell" problem.  The framework's primitives are correct,
but composing them into a multi-step sequence produces code that's hard to read, hard
to modify, and easy to mis-wire.  This is exactly the motivation for the Actions system
(Stage 10) — see Section 5.

### 2.2 No Sprite.image Setter (fixed)

The demo creates sprites with initial images but never needed to swap images outside
of animation playback.  However, reviewing the API revealed that `Sprite` had no way
to change its displayed image by asset name after construction.  The only path was
through `play()` (which requires an `AnimationDef`) or the internal `_set_image()`
(which takes a raw handle).

A game developer would reasonably expect:

```python
# Swap a sprite's image (e.g., door_closed → door_open)
door.image = "sprites/door_open"
```

This was missing.  See Section 4 for the fix.

### 2.3 tween() Requires from_val

Every `tween()` call in the demo redundantly specifies the current value:

```python
tween(defender.sprite, "opacity", 255.0, 0.0, 0.5, ease=Ease.EASE_OUT, ...)
#                                 ^^^^^
#                                 We already know it's 255 — it's the current value
```

And in floating damage numbers:

```python
tween(floater, "y", floater.y, floater.y - 60, 0.8, ease=Ease.EASE_OUT)
#                    ^^^^^^^^^
#                    Reading the value we just set one line above
```

The caller almost always wants "from whatever it is now."  Forcing `from_val` as a
positional argument adds noise and creates a consistency hazard — if the property was
already modified, the `from_val` you pass may be stale.

This is a candidate for a future API improvement: making `from_val` optional and
defaulting to `getattr(target, prop)`.  Not fixed in this stage because it would change
the public `tween()` signature, but noted for consideration.

### 2.4 No TextSprite

Floating damage numbers require a custom `_FloatingNumber` class with manual `draw()`
calls through the raw backend text API:

```python
class _FloatingNumber:
    def __init__(self, text: str, x: float, y: float) -> None:
        self.text = text
        self.x = x
        self.y = y
        self.opacity: float = 255.0
        self.alive = True

# In draw():
self.game.backend.draw_text(
    f.text, self._font, int(f.x), int(f.y),
    (255, 80, 80, alpha),
)
```

This works but requires:
- A custom class with position/opacity attributes (duplicating Sprite's interface)
- Manual lifecycle management (`alive` flag, list cleanup in `draw()`)
- Direct backend access (`self.game.backend.draw_text(...)`)
- Manual font loading and caching

A `TextSprite` or `Label` component at the framework level (planned for Stage 8 UI)
would let damage numbers be first-class sprites that participate in tweening, actions,
and y-sort ordering without any custom code.

### 2.5 Import Paths (fixed)

The original demo used deep internal import paths:

```python
from easygame.assets import AssetManager
from easygame.rendering.layers import RenderLayer, SpriteAnchor
from easygame.util.tween import Ease, tween
```

Game code shouldn't need to know the internal module structure.  A developer writing
`from easygame.rendering.layers import RenderLayer` has to know that layers live in
`easygame/rendering/layers.py` — implementation knowledge that should be hidden.
See Section 4 for the fix.

---

## 3. Bugs Found and Fixed

### 3.1 Opacity Float Leak

**Bug:** The tween system interpolates float values (e.g., opacity from 255.0 to 0.0).
The interpolated value is a float like `127.5`, which was passed directly to the
backend via `setattr(target, prop, val)`.  The `Sprite.opacity` setter stored this
float, but the `MockBackend.update_sprite()` and pyglet both expect `int` opacity.

**Symptom:** Backend sprite records could contain `opacity: 127.5` instead of
`opacity: 127`.  The tween itself doesn't crash, but downstream code doing
`int(sprite.opacity)` or backend integer comparisons could produce subtle errors.

**Fix:** The `Sprite.opacity` setter now coerces to `int`:

```python
# Before (sprite.py)
@opacity.setter
def opacity(self, value: int) -> None:
    self._opacity = value
    self._sync_to_backend()

# After (sprite.py)
@opacity.setter
def opacity(self, value: int | float) -> None:
    self._opacity = int(value)
    self._sync_to_backend()
```

The type hint was widened to `int | float` to document that float inputs are accepted
(tweens will produce them), and the stored value is always an integer.

A corresponding test was added:

```python
def test_opacity_setter_coerces_float(game: Game, backend: MockBackend) -> None:
    """Opacity setter coerces float to int (e.g. from tween)."""
    sprite = Sprite("sprites/knight", position=(100, 100))
    sprite.opacity = 127.5

    record = backend.sprites[sprite.sprite_id]
    assert record["opacity"] == 127
    assert sprite.opacity == 127
```

### 3.2 Missing Sprite.image Setter

**Bug:** `Sprite` had `image_handle` (read-only, returns the opaque backend handle) but
no way to swap the displayed image by asset name.  Game code that needed to change a
sprite's appearance (e.g., toggling a door between open/closed) had no public API path.

**Fix:** Added `Sprite.image` as a read/write property:

```python
@property
def image(self) -> str:
    """The current asset name."""
    return self._image_name

@image.setter
def image(self, name: str) -> None:
    if self._removed:
        return
    handle = self._assets.image(name)
    self._image_name = name
    self._set_image(handle)
```

This required adding `self._image_name = image` in `__init__` to track the asset name
alongside the opaque handle.

A corresponding test was added:

```python
def test_set_image_property(game: Game, backend: MockBackend) -> None:
    """Setting sprite.image swaps the displayed image and updates dimensions."""
    sprite = Sprite("sprites/knight", position=(100, 100))
    tree_handle = game.assets.image("sprites/tree")
    backend.set_image_size(tree_handle, 32, 48)

    sprite.image = "sprites/tree"

    record = backend.sprites[sprite.sprite_id]
    assert record["image"] == tree_handle
    assert sprite.image == "sprites/tree"
```

### 3.3 Demo Import Cleanup

**Bug:** The demo imported from internal module paths, bypassing the public
`easygame` namespace.

**Fix:** The demo's imports were consolidated to use the top-level package:

```python
# Before (battle_demo.py)
from easygame import AnimationDef, Game, InputEvent, Scene, Sprite
from easygame.assets import AssetManager
from easygame.rendering.layers import RenderLayer, SpriteAnchor
from easygame.util.tween import Ease, tween

# After (battle_demo.py)
from easygame import (
    AnimationDef,
    AssetManager,
    Ease,
    Game,
    InputEvent,
    RenderLayer,
    Scene,
    Sprite,
    SpriteAnchor,
    tween,
)
```

This confirmed that `easygame/__init__.py` exports everything game code needs.
The `Callable` import was also cleaned up (only `Any` is used from `typing` now that
the callback type hints were already in the codebase).

---

## 4. API Refinements — Before / After

### 4.1 Sprite.image Property

| | Code |
|---|---|
| **Before** | No public API to swap image.  Had to go through `play()` with a 1-frame `AnimationDef`, or use internal `_set_image()`. |
| **After** | `sprite.image = "sprites/door_open"` — reads the asset name, resolves through `AssetManager`, swaps the backend image, and re-caches dimensions for anchor math. |

### 4.2 Opacity Type Safety

| | Code |
|---|---|
| **Before** | `sprite.opacity = 127.5` stored `127.5`, leaked float to backend, type hint said `int` |
| **After** | `sprite.opacity = 127.5` stores `127`, backend always receives int, type hint says `int \| float` |

### 4.3 Demo Imports

| | Code |
|---|---|
| **Before** | 4 import lines from 4 different internal modules |
| **After** | 1 import block from `easygame` |

---

## 5. How the Actions System (Stage 10) Would Simplify This Demo

The battle vignette's 8-method callback chain is the textbook motivating example for
composable actions.  Here is how the same choreography would look with the Actions
system from DESIGN.md.

### Current Implementation: 8 Methods, ~100 Lines

The attack sequence is spread across 8 methods connected by callbacks.  Reading the
sequence requires tracing through:

```
_begin_attack → _phase_attack_anim → _phase_delay → _phase_hit_reaction
    → _phase_death → _phase_fade_and_remove → _phase_cleanup_dead
    → _phase_walk_home → _phase_done
```

Each method is small, but the _sequence_ is invisible.  Here are the key methods:

```python
def _begin_attack(self, attacker: Unit, defender: Unit) -> None:
    self.busy = True
    self._deselect()
    dx, dy = defender.sprite.position
    target_x = dx - 80 if attacker.home_pos[0] < dx else dx + 80
    attacker.sprite.play(WARRIOR_WALK)
    attacker.sprite.move_to(
        (target_x, dy), speed=MOVE_SPEED,
        on_arrive=lambda: self._phase_attack_anim(attacker, defender),
    )

def _phase_attack_anim(self, attacker: Unit, defender: Unit) -> None:
    attacker.sprite.play(
        WARRIOR_ATTACK,
        on_complete=lambda: self._phase_delay(attacker, defender),
    )

def _phase_delay(self, attacker: Unit, defender: Unit) -> None:
    self.game.after(0.3, lambda: self._phase_hit_reaction(attacker, defender))

def _phase_hit_reaction(self, attacker: Unit, defender: Unit) -> None:
    if not defender.alive:
        self._phase_walk_home(attacker)
        return
    defender.hp -= ATTACK_DAMAGE
    self._spawn_damage_number(defender)
    if defender.hp <= 0:
        defender.sprite.play(
            SKELETON_HIT,
            on_complete=lambda: self._phase_death(attacker, defender),
        )
    else:
        defender.sprite.play(
            SKELETON_HIT,
            on_complete=lambda: self._phase_defender_recover(attacker, defender),
        )

def _phase_defender_recover(self, attacker: Unit, defender: Unit) -> None:
    defender.sprite.play(SKELETON_IDLE)
    self._phase_walk_home(attacker)

def _phase_death(self, attacker: Unit, defender: Unit) -> None:
    defender.alive = False
    defender.sprite.play(
        SKELETON_DEATH,
        on_complete=lambda: self._phase_fade_and_remove(attacker, defender),
    )

def _phase_fade_and_remove(self, attacker: Unit, defender: Unit) -> None:
    tween(defender.sprite, "opacity", 255.0, 0.0, 0.5, ease=Ease.EASE_OUT,
           on_complete=lambda: self._phase_cleanup_dead(attacker, defender))

def _phase_cleanup_dead(self, attacker: Unit, defender: Unit) -> None:
    defender.sprite.remove()
    self._phase_walk_home(attacker)

def _phase_walk_home(self, attacker: Unit) -> None:
    attacker.sprite.play(WARRIOR_WALK)
    attacker.sprite.move_to(
        attacker.home_pos, speed=MOVE_SPEED,
        on_arrive=lambda: self._phase_done(attacker),
    )

def _phase_done(self, attacker: Unit) -> None:
    attacker.sprite.play(WARRIOR_IDLE)
    self.busy = False
```

### With Actions: 1 Method, ~40 Lines

```python
from easygame.actions import (
    Sequence, Parallel, Delay, Do, PlayAnim, MoveTo, FadeOut, Remove,
)

def _begin_attack(self, attacker: Unit, defender: Unit) -> None:
    self.busy = True
    self._deselect()

    dx, dy = defender.sprite.position
    target_x = dx - 80 if attacker.home_pos[0] < dx else dx + 80

    def apply_hit() -> None:
        """Deal damage and trigger the defender's reaction sequence."""
        if not defender.alive:
            return
        defender.hp -= ATTACK_DAMAGE
        self._spawn_damage_number(defender)
        if defender.hp <= 0:
            # Defender dies — play hit, death, fade, remove on their sprite
            defender.alive = False
            defender.sprite.do(Sequence(
                PlayAnim(SKELETON_HIT),
                PlayAnim(SKELETON_DEATH),
                FadeOut(0.5),
                Remove(),
            ))
        else:
            # Defender survives — play hit reaction, return to idle
            defender.sprite.do(Sequence(
                PlayAnim(SKELETON_HIT),
                PlayAnim(SKELETON_IDLE),
            ))

    # The attacker's full sequence — reads top to bottom
    attacker.sprite.do(Sequence(
        # Phase 1: walk to enemy
        Parallel(PlayAnim(WARRIOR_WALK), MoveTo((target_x, dy), speed=MOVE_SPEED)),
        # Phase 2: attack animation
        PlayAnim(WARRIOR_ATTACK),
        # Phase 3: delay before hit lands
        Delay(0.3),
        # Phase 4: deal damage + trigger defender reaction
        Do(apply_hit),
        # Phase 5-6: walk home
        Parallel(PlayAnim(WARRIOR_WALK), MoveTo(attacker.home_pos, speed=MOVE_SPEED)),
        # Done
        PlayAnim(WARRIOR_IDLE),
        Do(lambda: setattr(self, 'busy', False)),
    ))
```

Note how the defender's reaction runs on `defender.sprite.do(...)` — a separate action
sequence on a separate sprite, launched by `Do(apply_hit)`.  The attacker's sequence
continues independently (walking home) while the defender plays its hit/death animation.
This is the key insight: Actions compose _across sprites_ via `Do()` callbacks, not
just within a single sprite.

### What Changes

| Aspect | Callbacks (current) | Actions (Stage 10) |
|---|---|---|
| **Methods** | 8 methods, each wiring the next | 1 method with a flat `Sequence` |
| **Readability** | Sequence is invisible; must trace callbacks across methods | Sequence is literal — read top to bottom |
| **Adding a step** | Insert new method, re-wire two callbacks | Insert new action in the list |
| **Reordering** | Re-wire callbacks (error-prone) | Move lines within the `Sequence` |
| **Branching** | `if/else` in callback with different next-callbacks | `Do()` with conditional `sprite.do()` |
| **Parallel work** | Separate `play()` + `move_to()` calls, hope they stay in sync | `Parallel(PlayAnim(...), MoveTo(...))` — explicit |
| **Cancellation** | Must track and cancel timers, tweens, animations individually | `sprite.stop_actions()` cancels everything |

### Why the Callback Version Exists First

The callback approach is the **correct foundation**.  Actions are built _on top of_ the
same primitives: `PlayAnim` calls `sprite.play()`, `MoveTo` calls `sprite.move_to()`,
`Delay` uses `game.after()`, `FadeOut` uses `tween()`.  Building and testing the
primitives first (Stages 2-5) means the Actions layer (Stage 10) composes proven parts
rather than reimplementing movement, animation, and timing from scratch.

The battle vignette demo serves as the validation that all those primitives work
correctly in concert.  Once Actions land, the demo can be rewritten to use them — and
the headless test suite will confirm the behavior is identical.

---

## Summary

| Category | Finding |
|---|---|
| **Worked well** | AnimationDef, Sprite.play, Sprite.move_to, tween, timers, InputEvent, Scene lifecycle, mock backend testability |
| **Friction** | Callback nesting depth (8 methods for 1 sequence), tween requiring from_val, no TextSprite, deep import paths |
| **Bugs fixed** | Opacity float leak (tween → sprite), missing Sprite.image setter, demo import cleanup |
| **API refined** | Sprite.image property, opacity int coercion, top-level re-exports |
| **Future improvement** | Stage 10 Actions will collapse 8-method callback chains into flat declarative sequences |
