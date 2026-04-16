"""Properties of :meth:`Scene.summary_json` — structured form of the
iter-20 summary. Keras's ``Model.to_json`` serves the same role for
model architecture; same primitive for saga2d scenes.

The key promise is that :meth:`summary` and :meth:`summary_json` can
never drift — they share the same data model internally. Tests check
*shape*, not pixel-perfect keys, so the schema can evolve.
"""

from __future__ import annotations

import json

import pytest

from saga2d import (
    Anchor,
    Game,
    Label,
    ProgressBar,
    Row,
    Scene,
)


@pytest.fixture
def game():
    g = Game(
        "summary-json-test",
        resolution=(200, 200),
        fullscreen=False,
        backend="mock",
        visible=False,
    )
    yield g
    g._teardown()


def _push(game: Game, scene: Scene) -> Scene:
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    return scene


def test_output_is_json_serialisable(game: Game) -> None:
    """Every field summary_json returns must round-trip through
    json.dumps — if it doesn't, tooling can't consume it."""

    class S(Scene):
        background_color = (10, 20, 30, 255)
        controls = {"space": "jump"}

        def jump(self) -> None: pass

        def on_enter(self) -> None:
            self.ui.add(Label("Hello", text_style="hud",
                              anchor=Anchor.CENTER, margin=8))

    scene = _push(game, S())
    data = scene.summary_json()
    # Must not raise.
    encoded = json.dumps(data)
    # Round-trip should preserve the essential keys.
    decoded = json.loads(encoded)
    assert decoded["scene"] == "S"


def test_scene_field_always_present(game: Game) -> None:
    class S(Scene): pass
    scene = _push(game, S())
    data = scene.summary_json()
    assert data["scene"] == "S"


def test_background_color_as_list(game: Game) -> None:
    """Tuples round-trip poorly through JSON; the schema promises
    the colour as a list of ints."""

    class S(Scene):
        background_color = (10, 20, 30, 255)

    data = _push(game, S()).summary_json()
    assert data["background_color"] == [10, 20, 30, 255]


def test_background_color_absent_when_unset(game: Game) -> None:
    class S(Scene): pass
    data = _push(game, S()).summary_json()
    assert "background_color" not in data


def test_controls_are_list_of_key_groups(game: Game) -> None:
    """Each controls entry is a ``{"keys": [...], "method": "..."}``
    object with aliases grouped together — same shape summary()
    uses for the human-readable line."""

    class S(Scene):
        controls = {
            ("right", "d"): "cw",
            ("left", "a"): "ccw",
        }
        def cw(self) -> None: pass
        def ccw(self) -> None: pass

    data = _push(game, S()).summary_json()
    assert "controls" in data
    methods = {entry["method"] for entry in data["controls"]}
    assert methods == {"cw", "ccw"}
    cw_entry = next(e for e in data["controls"] if e["method"] == "cw")
    assert set(cw_entry["keys"]) == {"right", "d"}


def test_ui_tree_includes_root_and_nested_children(game: Game) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Row(Label("inner1"), Label("inner2")))

    data = _push(game, S()).summary_json()
    ui = data["ui"]
    assert ui["type"] == "_UIRoot"
    assert len(ui["children"]) == 1
    row = ui["children"][0]
    assert row["type"] == "Row"
    assert len(row["children"]) == 2
    assert {c["type"] for c in row["children"]} == {"Label"}


def test_label_text_reactive_flag(game: Game) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("literal"))
            self.ui.add(Label(lambda: "dynamic"))

    data = _push(game, S()).summary_json()
    labels = [c for c in data["ui"]["children"] if c["type"] == "Label"]
    literal, reactive = labels[0], labels[1]
    assert literal["text"]["reactive"] is False
    assert literal["text"]["value"] == "literal"
    assert reactive["text"]["reactive"] is True
    # Reactive entries intentionally omit the "value" key so snapshot
    # diffs ignore the per-frame drift.
    assert "value" not in reactive["text"]


def test_progressbar_reactive_value(game: Game) -> None:
    class S(Scene):
        hp = 5

        def on_enter(self) -> None:
            self.ui.add(ProgressBar(
                value=lambda: self.hp,
                max_value=10,
            ))

    data = _push(game, S()).summary_json()
    bar = data["ui"]["children"][0]
    assert bar["type"] == "ProgressBar"
    assert bar["value"]["reactive"] is True


def test_text_style_tag_present_when_set(game: Game) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("X", text_style="hud"))
            self.ui.add(Label("Y"))  # no text_style

    data = _push(game, S()).summary_json()
    labels = data["ui"]["children"]
    assert labels[0]["text_style"] == "hud"
    assert "text_style" not in labels[1]


def test_anchor_and_margin(game: Game) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("A",
                              anchor=Anchor.BOTTOM_RIGHT, margin=24))

    data = _push(game, S()).summary_json()
    label = data["ui"]["children"][0]
    assert label["anchor"] == "BOTTOM_RIGHT"
    assert label["margin"] == 24


def test_summary_and_summary_json_never_drift(game: Game) -> None:
    """The documented promise: :meth:`summary` formats from the same
    data :meth:`summary_json` produces. Every concept exposed in the
    JSON should have a corresponding hint in the string.
    """

    class S(Scene):
        background_color = (10, 20, 30, 255)
        controls = {("r", "confirm"): "reset"}

        def reset(self) -> None: pass

        def on_enter(self) -> None:
            self.ui.add(Row(Label("hi", text_style="hud")))

    scene = _push(game, S())
    data = scene.summary_json()
    text = scene.summary()

    # Scene class
    assert data["scene"] in text
    # Background colour
    assert str(tuple(data["background_color"])) in text
    # Method name from the controls list
    assert data["controls"][0]["method"] in text
    # Every text_style value in the JSON appears somewhere in the string
    def _styles(node):
        if "text_style" in node:
            yield node["text_style"]
        for c in node.get("children", []):
            yield from _styles(c)
    for style_name in _styles(data["ui"]):
        assert f"text_style={style_name}" in text


def test_empty_scene_returns_minimal_dict(game: Game) -> None:
    class S(Scene): pass

    data = _push(game, S()).summary_json()
    # Only "scene" + "ui" (ui present because .ui was accessed if
    # on_enter added anything; here it wasn't, but _UIRoot may still
    # be created lazily). At minimum: scene present, no controls
    # key.
    assert "scene" in data
    assert "controls" not in data
