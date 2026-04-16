"""Properties of the iter-28 ``include_bounds`` flag on
``Scene.summary`` / ``Scene.summary_json``.

When set, each UI node carries its computed rect. Off by default so
existing snapshots stay resolution-independent.
"""

from __future__ import annotations

import pytest

from saga2d import Anchor, Game, Label, Row, Scene


@pytest.fixture
def game():
    g = Game(
        "summary-bounds-test",
        resolution=(800, 600),
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


def test_bounds_absent_by_default(game: Game) -> None:
    """The default ``summary_json()`` output (snapshot-friendly) must
    not contain a ``bounds`` key — bounds depend on viewport size
    and would make snapshots resolution-coupled."""

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("X", anchor=Anchor.CENTER))

    scene = _push(game, S())
    data = scene.summary_json()
    ui = data["ui"]
    assert "bounds" not in ui
    label = ui["children"][0]
    assert "bounds" not in label


def test_bounds_present_when_requested(game: Game) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("X", anchor=Anchor.CENTER))

    scene = _push(game, S())
    data = scene.summary_json(include_bounds=True)
    ui = data["ui"]
    assert "bounds" in ui
    # Root covers the viewport.
    assert ui["bounds"] == [0, 0, 800, 600]
    # Label inherits the layout compute.
    label = ui["children"][0]
    assert "bounds" in label
    assert len(label["bounds"]) == 4
    assert all(isinstance(v, int) for v in label["bounds"])


def test_bounds_propagates_through_containers(game: Game) -> None:
    """Every depth in the tree should carry bounds when the flag is on."""

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Row(Label("a"), Label("b"), anchor=Anchor.TOP_LEFT))

    scene = _push(game, S())
    data = scene.summary_json(include_bounds=True)
    row = data["ui"]["children"][0]
    assert "bounds" in row
    for child in row["children"]:
        assert "bounds" in child


def test_bounds_json_serialisable(game: Game) -> None:
    """The bounds field must be a JSON-serialisable list of ints, not
    some private tuple type — tooling consumes the dict as JSON."""
    import json

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("X", anchor=Anchor.CENTER))

    scene = _push(game, S())
    data = scene.summary_json(include_bounds=True)
    # Must round-trip cleanly through json.
    encoded = json.dumps(data)
    decoded = json.loads(encoded)
    assert decoded["ui"]["bounds"] == [0, 0, 800, 600]


def test_summary_string_shows_bounds_when_requested(game: Game) -> None:
    """Each visible UI node gets a bounds tag in the formatted string.
    The invisible ``_UIRoot`` wrapper doesn't appear in the formatted
    output (only its children do), but every rendered child carries
    ``bounds=[x,y WxH]``."""

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("X", anchor=Anchor.CENTER))
            self.ui.add(Label("Y", anchor=Anchor.TOP_LEFT, margin=10))

    scene = _push(game, S())
    text = scene.summary(include_bounds=True)
    label_lines = [l for l in text.splitlines() if "Label" in l]
    assert len(label_lines) == 2
    for line in label_lines:
        assert "bounds=" in line


def test_summary_string_default_has_no_bounds(game: Game) -> None:
    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("X", anchor=Anchor.CENTER))

    scene = _push(game, S())
    text = scene.summary()
    assert "bounds=" not in text


def test_bounds_snapshot_would_drift_by_resolution() -> None:
    """Regression check on the documented reason bounds default off:
    two Games at different resolutions produce different bounds
    output for the same scene. Caller opting into include_bounds
    accepts this coupling.

    Games are created sequentially because saga2d enforces one
    Game per process — they would clash if alive at once.
    """
    from saga2d import Game as GameCls

    class S(Scene):
        def on_enter(self) -> None:
            self.ui.add(Label("X", anchor=Anchor.CENTER))

    g1 = GameCls("g1", resolution=(400, 300), fullscreen=False,
                 backend="mock", visible=False)
    try:
        scene1 = S()
        g1._scene_stack.push(scene1)
        g1.tick(dt=1 / 60)
        bounds_small = scene1.summary_json(include_bounds=True)["ui"]["bounds"]
    finally:
        g1._teardown()

    g2 = GameCls("g2", resolution=(800, 600), fullscreen=False,
                 backend="mock", visible=False)
    try:
        scene2 = S()
        g2._scene_stack.push(scene2)
        g2.tick(dt=1 / 60)
        bounds_large = scene2.summary_json(include_bounds=True)["ui"]["bounds"]
    finally:
        g2._teardown()

    assert bounds_small != bounds_large
    assert bounds_small[2:] == [400, 300]
    assert bounds_large[2:] == [800, 600]
