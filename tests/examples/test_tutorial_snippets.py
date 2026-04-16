"""Every code snippet in ``tutorials/declarative/tutorial.md`` is tested here.

A tutorial with broken samples is worse than no tutorial. Each ``Step
N`` section in the markdown is mirrored by a test below. If a snippet
drifts from the API it will fail in CI before a reader hits it.
"""

from __future__ import annotations

import random

import pytest

from saga2d import (
    Anchor,
    Game,
    InputEvent,
    Label,
    Row,
    Scene,
    TextStyle,
    Theme,
)


@pytest.fixture
def game():
    g = Game(
        "tutorial-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _press(key: str | None = None, action: str | None = None) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action)


# ======================================================================
# Step 1 — the empty Scene
# ======================================================================


def test_step1_empty_scene_runs(game: Game) -> None:
    class GuessScene(Scene):
        background_color = (18, 20, 30, 255)

    game._scene_stack.push(GuessScene())
    game.tick(dt=1 / 60)  # does not crash


# ======================================================================
# Step 2 — add state
# ======================================================================


class _Step2GuessScene(Scene):
    background_color = (18, 20, 30, 255)

    def __init__(self) -> None:
        super().__init__()
        self.target = random.randint(1, 100)
        self.current = 50
        self.guesses = 0
        self.hint = ""


def test_step2_state_initialised(game: Game) -> None:
    scene = _Step2GuessScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    assert 1 <= scene.target <= 100
    assert scene.current == 50
    assert scene.guesses == 0
    assert scene.hint == ""


# ======================================================================
# Step 3 — declarative controls
# ======================================================================


class _Step3GuessScene(Scene):
    background_color = (18, 20, 30, 255)
    controls = {
        ("up", "w"):          "bump_up",
        ("down", "s"):        "bump_down",
        ("confirm", "space"): "guess",
    }

    def __init__(self) -> None:
        super().__init__()
        self.target = 50
        self.current = 50
        self.guesses = 0
        self.hint = ""

    def bump_up(self) -> None:    self.current = min(100, self.current + 1)
    def bump_down(self) -> None:  self.current = max(1, self.current - 1)

    def guess(self) -> None:
        self.guesses += 1
        if self.current == self.target: self.hint = "Correct!"
        elif self.current < self.target: self.hint = "Higher"
        else:                            self.hint = "Lower"


def test_step3_up_w_both_bump_up(game: Game) -> None:
    scene = _Step3GuessScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene._dispatch_key_bindings(_press(key="up"))
    scene._dispatch_key_bindings(_press(key="w"))
    assert scene.current == 52


def test_step3_down_s_both_bump_down(game: Game) -> None:
    scene = _Step3GuessScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene._dispatch_key_bindings(_press(key="down"))
    scene._dispatch_key_bindings(_press(key="s"))
    assert scene.current == 48


def test_step3_guess_reports_correctly(game: Game) -> None:
    scene = _Step3GuessScene()
    scene.current = 50
    scene.target = 50
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.hint == "Correct!"
    assert scene.guesses == 1

    scene.current = 30
    scene._dispatch_key_bindings(_press(key="space"))
    assert scene.hint == "Higher"

    scene.current = 80
    scene._dispatch_key_bindings(_press(action="confirm"))
    assert scene.hint == "Lower"


def test_step3_bump_clamps_at_bounds(game: Game) -> None:
    scene = _Step3GuessScene()
    scene.current = 100
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene._dispatch_key_bindings(_press(key="up"))
    assert scene.current == 100  # clamped


# ======================================================================
# Step 4 — reactive HUD
# ======================================================================


class _Step4GuessScene(_Step3GuessScene):
    def on_enter(self) -> None:
        self.ui.add(Label("Guess 1–100",
                          anchor=Anchor.TOP_CENTER, margin=20))
        self.ui.add(Label(lambda: str(self.current),
                          anchor=Anchor.CENTER, font_size=48))
        self.ui.add(Row(
            Label(lambda: f"Guesses {self.guesses}"),
            Label(lambda: self.hint),
            anchor=Anchor.BOTTOM_CENTER, margin=20,
        ))


def test_step4_reactive_labels_reflect_state(game: Game) -> None:
    scene = _Step4GuessScene()
    scene.target = 50
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)

    # Current-number display label.
    current_label = scene.ui.find(
        lambda c: isinstance(c, Label) and c.text == "50"
    )
    assert current_label is not None

    # Bump up and verify label updates on next tick.
    scene._dispatch_key_bindings(_press(key="up"))
    game.tick(dt=1 / 60)
    assert current_label.text == "51"


def test_step4_guesses_and_hint_update_in_row(game: Game) -> None:
    scene = _Step4GuessScene()
    scene.target = 70
    scene.current = 50
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)

    scene._dispatch_key_bindings(_press(action="confirm"))
    game.tick(dt=1 / 60)

    labels = scene.ui.find_all(lambda c: isinstance(c, Label))
    texts = {l.text for l in labels}
    assert "Guesses 1" in texts
    assert "Higher" in texts


# ======================================================================
# Step 5 — theme
# ======================================================================


def _step5_theme() -> Theme:
    return Theme(text_styles={
        "title":   TextStyle(font_size=26, color=(255, 215, 100, 255)),
        "display": TextStyle(font_size=56, color=(245, 245, 250, 255)),
        "hud":     TextStyle(font_size=16, color=(200, 200, 220, 255)),
    })


class _Step5GuessScene(_Step3GuessScene):
    def on_enter(self) -> None:
        self.ui.add(Label("Guess 1–100", text_style="title",
                          anchor=Anchor.TOP_CENTER, margin=20))
        self.ui.add(Label(lambda: str(self.current), text_style="display",
                          anchor=Anchor.CENTER))
        self.ui.add(Row(
            Label(lambda: f"Guesses {self.guesses}", text_style="hud"),
            Label(lambda: self.hint, text_style="hud"),
            anchor=Anchor.BOTTOM_CENTER, margin=20,
        ))


def test_step5_theme_resolves_text_styles() -> None:
    """The tutorial's build_theme() registers three styles and the
    Scene's Labels pull font_size / color from the matching name."""
    game = Game(
        "tutorial-theme-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=_step5_theme(),
    )
    try:
        scene = _Step5GuessScene()
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)

        title_label = scene.ui.find(
            lambda c: isinstance(c, Label) and c.text == "Guess 1–100"
        )
        assert title_label is not None
        resolved = title_label._resolve_style()
        assert resolved.font_size == 26
        assert resolved.text_color == (255, 215, 100, 255)
    finally:
        game._teardown()


# ======================================================================
# Bonus — scene.summary() output shape
# ======================================================================


def test_summary_output_shape(game: Game) -> None:
    """The summary block shown in the tutorial should contain each
    declarative element: controls line with aliases, one literal Label,
    one '← callable' marker for reactive bindings, one nested Row with
    indented children."""
    scene = _Step4GuessScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)

    out = scene.summary()
    assert "Scene: _Step4GuessScene" in out
    assert "controls:" in out
    # Controls with aliases grouped.
    assert "up" in out and "w" in out and "bump_up" in out
    # At least one literal label + one reactive marker.
    assert '"Guess 1–100"' in out
    assert "← callable" in out
    # Row present, children indented deeper than the Row itself.
    lines = out.splitlines()
    row_line = next(l for l in lines if "Row" in l)
    row_indent = len(row_line) - len(row_line.lstrip())
    # Any line after row with deeper indent should be a child Label.
    row_idx = lines.index(row_line)
    child = lines[row_idx + 1]
    assert len(child) - len(child.lstrip()) > row_indent
