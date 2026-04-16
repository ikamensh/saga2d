"""Verify the README Quick Start example actually works.

A README with a broken sample is worse than no README. This test
mirrors the Quick Start verbatim (minus the ``game.run()`` blocking
call, which we replace with mock-backend ticks) and checks that:

* the scene parses and instantiates
* the class-level ``controls`` dict validates at import time
* reactive HUD Labels produce the expected initial text
* each control method mutates state as promised
"""

from __future__ import annotations

import pytest

from saga2d import (
    Anchor, Game, InputEvent, Label, ProgressBar, Row, Scene,
    TextStyle, Theme,
)


# -- Verbatim from README Quick Start ------------------------------------

class GameScene(Scene):
    background_color = (18, 14, 28, 255)
    controls = {
        ("right", "d"):        "gain_coin",
        ("left", "a"):         "take_damage",
        ("confirm", "space"):  "reset",
    }

    def __init__(self):
        super().__init__()
        self.hp = 10
        self.coins = 0

    def gain_coin(self):    self.coins += 1
    def take_damage(self):  self.hp = max(0, self.hp - 1)
    def reset(self):        self.hp, self.coins = 10, 0

    def on_enter(self):
        self.ui.add(Label("My Game", text_style="title",
                          anchor=Anchor.TOP_LEFT, margin=20))
        self.ui.add(Row(
            Label(lambda: f"HP {self.hp}/10", text_style="hud"),
            ProgressBar(value=lambda: self.hp, max_value=10,
                        width=120, height=12),
            Label(lambda: f"Coins {self.coins}", text_style="hud"),
            spacing=16,
            anchor=Anchor.BOTTOM_LEFT, margin=16,
        ))


def _quickstart_theme() -> Theme:
    return Theme(text_styles={
        "title": TextStyle(28, (255, 215, 100, 255)),
        "hud":   TextStyle(18, (245, 245, 250, 255)),
    })


# -- Tests ---------------------------------------------------------------


@pytest.fixture
def game():
    g = Game(
        "readme-quickstart-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=_quickstart_theme(),
    )
    yield g
    g._teardown()


def _push(game: Game) -> GameScene:
    scene = GameScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    return scene


def test_scene_parses_and_ticks(game: Game) -> None:
    """README scene class loads (class-level controls validation
    passes) and survives one tick without raising."""
    scene = _push(game)
    assert scene.hp == 10
    assert scene.coins == 0


def test_reactive_hud_reflects_initial_state(game: Game) -> None:
    scene = _push(game)
    # Use the iter-19 public walk/find_all — no private reach.
    label_texts = [
        c.text for c in scene.ui.find_all(lambda c: isinstance(c, Label))
    ]
    assert "HP 10/10" in label_texts
    assert "Coins 0" in label_texts


def test_gain_coin_advances_state_and_hud(game: Game) -> None:
    scene = _push(game)
    scene._dispatch_key_bindings(
        InputEvent(type="key_press", key="right")
    )
    assert scene.coins == 1
    game.tick(dt=1 / 60)  # next tick refreshes the reactive Label
    coin_label = scene.ui.find(
        lambda c: isinstance(c, Label) and c.text.startswith("Coins")
    )
    assert coin_label is not None
    assert coin_label.text == "Coins 1"


def test_take_damage_floors_at_zero(game: Game) -> None:
    scene = _push(game)
    for _ in range(20):
        scene._dispatch_key_bindings(
            InputEvent(type="key_press", key="left")
        )
    assert scene.hp == 0


def test_reset_restores_initial_state(game: Game) -> None:
    scene = _push(game)
    scene._dispatch_key_bindings(InputEvent(type="key_press", key="left"))
    scene._dispatch_key_bindings(InputEvent(type="key_press", key="right"))
    scene._dispatch_key_bindings(InputEvent(type="key_press", action="confirm"))
    assert scene.hp == 10
    assert scene.coins == 0


def test_progressbar_fraction_tracks_hp(game: Game) -> None:
    """The reactive ProgressBar binding works across HP changes."""
    scene = _push(game)
    bar = scene.ui.find(lambda c: isinstance(c, ProgressBar))
    assert bar is not None
    assert bar.fraction == 1.0  # hp=10, max=10

    scene.take_damage()
    scene.take_damage()
    scene.take_damage()
    assert bar.fraction == pytest.approx(0.7, abs=1e-6)
