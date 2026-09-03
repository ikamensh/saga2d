# Saga2D — Project Instructions

Framework in `saga2d/`, reference game in `tribes/`, tests in `tests/`.
Read `DESIGN.md` before changing the framework.

## Commands

```bash
uv run python -m pytest tests -q        # headless suite (mock backend)
uv run python -m tribes --seed 7        # play
```

## Visual changes must be looked at

Mock tests prove logic, not pixels.  After any change to rendering, the
pyglet backend, UI components or the Tribes scene, render a real frame
and open the PNG:

```python
from saga2d.testing import render_scene

def setup(game):
    game.push(MyScene())

render_scene(setup, resolution=(1280, 800), tick_count=3).save("/tmp/check.png")
```

Ask "would a game developer ship this?" before marking the task done.
Real input can be exercised through pyglet's dispatch on the hidden
window: `game.backend.window.dispatch_event("on_key_press", key.TAB, 0)`.
Never rely on the mock path alone for event handling — pyglet handlers
must return `True` or ESC closes the window.

The display must be awake for pyglet to open windows; a
`get_default_screen` IndexError means it is asleep.

## Testing conventions

- `Game("t", backend="mock")`, `game.tick(dt)`, `backend.inject_key(...)`,
  `backend.inject_click(x, y)`; assert on `backend.texts/rects/sprites`
  and on model state.
- Tests exercise public behaviour through `Game`/`Scene`/`World`; no
  mocking of internals.  Add a regression test for every bug found.
- `tribes/model.py` has no saga2d dependency — test rules there directly.

## Style

- Clear exceptions over silent fallbacks.  Delete rather than deprecate.
- Game code imports from `saga2d` only; never from `saga2d.backends`.
- Commit each working increment.
