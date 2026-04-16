# The declarative Scene — saga2d in 5 steps

This tutorial builds a tiny guess-the-number game from scratch, introducing
one declarative saga2d API per step. The whole finished scene is under 40
lines. Every snippet below is exercised by
`tests/examples/test_tutorial_snippets.py` — if a snippet breaks, CI
catches it.

If you know Keras, this is the saga2d equivalent of the
`model = Sequential([Dense(128), Dense(10)])` / `model.compile()` /
`model.fit()` tutorial — the shape of an idiomatic saga2d scene, shown in
one progression.

## Step 1 — the empty Scene

A Scene is a Python class. That's it. Override `background_color` to
clear to a colour each frame. No `__init__` override needed yet.

```python
from saga2d import Scene

class GuessScene(Scene):
    background_color = (18, 20, 30, 255)
```

Instantiate, push, tick — the scene runs. This exact class (with a dummy
`Game(..., backend="mock")`) passes the first tutorial test.

## Step 2 — add state

State is plain Python attributes. No observables, no decorators, no
frameworks. Put them in `__init__`.

```python
import random

class GuessScene(Scene):
    background_color = (18, 20, 30, 255)

    def __init__(self):
        super().__init__()
        self.target = random.randint(1, 100)
        self.current = 50
        self.guesses = 0
        self.hint = ""
```

## Step 3 — declarative controls

Input binding is a **class-level dict**, not imperative `bind_key` calls
inside `on_enter`. Method names resolve via `getattr(self, name)` at
dispatch time. Typos raise `AttributeError` at import, not at first
keypress.

```python
class GuessScene(Scene):
    background_color = (18, 20, 30, 255)
    controls = {
        ("up", "w"):          "bump_up",
        ("down", "s"):        "bump_down",
        ("confirm", "space"): "guess",
    }

    def __init__(self):
        super().__init__()
        self.target = 50  # fixed for the test — random in real game
        self.current = 50
        self.guesses = 0
        self.hint = ""

    def bump_up(self):    self.current = min(100, self.current + 1)
    def bump_down(self):  self.current = max(1, self.current - 1)

    def guess(self):
        self.guesses += 1
        if self.current == self.target: self.hint = "Correct!"
        elif self.current < self.target: self.hint = "Higher"
        else:                            self.hint = "Lower"
```

**Tuple keys are aliases** — `("up", "w")` binds both arrow-up and W to
`bump_up`. A single-string key is fine too (`"cancel": "abandon"`).

## Step 4 — reactive HUD

The HUD reads from scene state via `Label(text=callable)`. The callable
is re-evaluated each frame, so mutating `self.current` anywhere updates
the label. No `label.text = …` wiring.

```python
from saga2d import Anchor, Label, Row

class GuessScene(Scene):
    background_color = (18, 20, 30, 255)
    controls = {
        ("up", "w"):          "bump_up",
        ("down", "s"):        "bump_down",
        ("confirm", "space"): "guess",
    }

    def __init__(self):
        super().__init__()
        self.target = 50
        self.current = 50
        self.guesses = 0
        self.hint = ""

    def bump_up(self):    self.current = min(100, self.current + 1)
    def bump_down(self):  self.current = max(1, self.current - 1)

    def guess(self):
        self.guesses += 1
        if self.current == self.target: self.hint = "Correct!"
        elif self.current < self.target: self.hint = "Higher"
        else:                            self.hint = "Lower"

    def on_enter(self):
        self.ui.add(Label("Guess 1–100",
                          anchor=Anchor.TOP_CENTER, margin=20))
        self.ui.add(Label(lambda: str(self.current),
                          anchor=Anchor.CENTER, font_size=48))
        self.ui.add(Row(
            Label(lambda: f"Guesses {self.guesses}"),
            Label(lambda: self.hint),
            anchor=Anchor.BOTTOM_CENTER, margin=20,
        ))
```

The central number is a single `Label(lambda: str(self.current))`. The
`Row` at the bottom stacks two more reactive labels horizontally with
zero container boilerplate — `Row` is transparent by default.

## Step 5 — theme the text

Centralise appearance in a `Theme`. Labels say `text_style="hud"` and
the theme decides what that looks like.

```python
from saga2d import Game, TextStyle, Theme

def build_theme():
    return Theme(text_styles={
        "title":   TextStyle(font_size=26, color=(255, 215, 100, 255)),
        "display": TextStyle(font_size=56, color=(245, 245, 250, 255)),
        "hud":     TextStyle(font_size=16, color=(200, 200, 220, 255)),
    })
```

Then in the scene, replace `font_size=…` with `text_style="…"`:

```python
    def on_enter(self):
        self.ui.add(Label("Guess 1–100", text_style="title",
                          anchor=Anchor.TOP_CENTER, margin=20))
        self.ui.add(Label(lambda: str(self.current), text_style="display",
                          anchor=Anchor.CENTER))
        self.ui.add(Row(
            Label(lambda: f"Guesses {self.guesses}", text_style="hud"),
            Label(lambda: self.hint, text_style="hud"),
            anchor=Anchor.BOTTOM_CENTER, margin=20,
        ))
```

And pass the theme to `Game`:

```python
game = Game("Guess", resolution=(800, 600), theme=build_theme())
game.run(GuessScene())
```

## Bonus — introspect with `scene.summary()`

You can dump the scene's declared structure at any time:

```python
scene = GuessScene()
# ... push to a game, tick once, then:
print(scene.summary())
```

Output:

```
Scene: GuessScene
  background_color: (18, 20, 30, 255)
  controls:
    confirm, space  → guess
    down, s  → bump_down
    up, w  → bump_up
  ui:
    Label "Guess 1–100", text_style=title, anchor=TOP, margin=20
    Label ← callable, text_style=display, anchor=CENTER
    Row anchor=BOTTOM, margin=20
      Label ← callable, text_style=hud
      Label ← callable, text_style=hud
```

If a `controls` binding didn't take (typo in method name), the scene
refuses to load. If a Label is accidentally static when you wanted
reactive, `← callable` vs. `"literal"` in the summary tells you
immediately.

## What's declarative

The five steps above cover saga2d's declarative vocabulary:

| Role | Declarative form |
|------|------------------|
| State | plain Python attributes |
| Controls | class-level `controls` dict — validated at import |
| HUD text | `Label(lambda: …)` — re-evaluated each frame |
| Layout | `Row(...)` / `Column(...)` — transparent flow containers |
| Typography | `text_style="hud"` + `Theme(text_styles={...})` |

Imperative alternatives for each still exist (`bind_key`, `label.text =
…`, a Panel with explicit styles, manual `draw_text` calls). The
declarative forms are the idiomatic path — they compose, they validate
at import time, and `scene.summary()` shows what you actually wired up.
