"""Properties of :meth:`InputManager.is_pressed` and
:meth:`InputManager.pressed_keys` (iter-44).

Before iter-44, saga2d's :class:`InputManager` only emitted edge-
triggered events (key_press, key_release) — game code that wanted
level-triggered "is this key currently held?" had to track press/
release events in its own ``handle_input``. Every motion-driven
example (dodge, and any future platformer) would need to re-implement
this block. iter-44 centralises it on the InputManager.

Properties verified:

*   A key is not held until a key_press event arrives.
*   A held key reports is_pressed=True through every subsequent tick.
*   A key_release clears the held state.
*   Multiple keys can be held simultaneously.
*   :meth:`pressed_keys` returns a frozen snapshot — mutating it
    doesn't mutate the internal set.
*   :meth:`_clear_pressed` releases all.
*   Event streams still emit normally — adding is_pressed did not
    break the existing edge-triggered dispatch.
"""

from __future__ import annotations

import pytest

from saga2d import Game


@pytest.fixture
def game():
    g = Game("input-test", resolution=(100, 100),
             fullscreen=False, backend="mock", visible=False)
    yield g
    g._teardown()


def test_no_keys_pressed_initially(game: Game) -> None:
    assert game.input.is_pressed("a") is False
    assert game.input.pressed_keys() == frozenset()


def test_key_press_marks_key_held(game: Game) -> None:
    game.backend.inject_key("a", type="key_press")
    game.tick(dt=1 / 60)
    assert game.input.is_pressed("a") is True


def test_held_key_stays_held_across_ticks(game: Game) -> None:
    """Property: a key press without a matching release keeps
    is_pressed=True for every subsequent tick."""
    game.backend.inject_key("a", type="key_press")
    for _ in range(20):
        game.tick(dt=1 / 60)
        assert game.input.is_pressed("a") is True


def test_key_release_clears_held_state(game: Game) -> None:
    game.backend.inject_key("d", type="key_press")
    game.tick(dt=1 / 60)
    assert game.input.is_pressed("d") is True
    game.backend.inject_key("d", type="key_release")
    game.tick(dt=1 / 60)
    assert game.input.is_pressed("d") is False


def test_multiple_keys_tracked_independently(game: Game) -> None:
    game.backend.inject_key("a", type="key_press")
    game.backend.inject_key("w", type="key_press")
    game.tick(dt=1 / 60)
    assert game.input.is_pressed("a") is True
    assert game.input.is_pressed("w") is True
    assert game.input.is_pressed("s") is False


def test_pressed_keys_returns_frozen_snapshot(game: Game) -> None:
    game.backend.inject_key("a", type="key_press")
    game.tick(dt=1 / 60)
    snap = game.input.pressed_keys()
    assert isinstance(snap, frozenset)
    # A frozen set can't be mutated — attempting raises. The real
    # invariant we care about: modifying the returned object (even
    # via a copy) can't leak back into the InputManager's state.
    with pytest.raises(AttributeError):
        snap.add("w")  # type: ignore[attr-defined]


def test_pressed_keys_snapshot_is_stable_across_new_presses(game: Game) -> None:
    """A snapshot taken before a subsequent press isn't retroactively
    updated — each call returns a fresh frozenset."""
    game.backend.inject_key("a", type="key_press")
    game.tick(dt=1 / 60)
    snap_before = game.input.pressed_keys()
    game.backend.inject_key("w", type="key_press")
    game.tick(dt=1 / 60)
    snap_after = game.input.pressed_keys()
    assert "w" in snap_after
    assert "w" not in snap_before  # the old snapshot didn't get updated


def test_release_without_prior_press_is_noop(game: Game) -> None:
    """A stray release event without a matching press doesn't error
    out — it's just a no-op on the held set."""
    game.backend.inject_key("z", type="key_release")
    game.tick(dt=1 / 60)
    assert game.input.is_pressed("z") is False


def test_clear_pressed_releases_everything(game: Game) -> None:
    """``_clear_pressed`` is the focus-loss / teardown escape hatch."""
    game.backend.inject_key("a", type="key_press")
    game.backend.inject_key("w", type="key_press")
    game.tick(dt=1 / 60)
    assert len(game.input.pressed_keys()) == 2
    game.input._clear_pressed()
    assert game.input.pressed_keys() == frozenset()


def test_edge_triggered_events_still_work(game: Game) -> None:
    """Adding level-triggered state didn't break the InputEvent stream.

    Inject a key press; the next tick should produce an InputEvent
    via the existing dispatch path — verify by binding a control
    method and checking it fires."""
    from saga2d import Scene

    fired: list[str] = []

    class S(Scene):
        controls = {"j": "jump"}

        def jump(self) -> None:
            fired.append("jump")

    game._scene_stack.push(S())
    game.backend.inject_key("j", type="key_press")
    game.tick(dt=1 / 60)
    assert fired == ["jump"]
