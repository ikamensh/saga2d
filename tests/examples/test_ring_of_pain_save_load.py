"""Save/load round-trip for the Ring of Pain example.

iter-29: exercises saga2d's save subsystem end-to-end. The subsystem
has been in the framework since iter-1 but no example used it. This
test verifies the full round-trip through the mock backend:

1. Start a scene, mutate state (take damage, gain coins, defeat a node)
2. Call ``game.save(slot)`` — writes JSON via the SaveManager
3. Create a fresh scene with the same seed, push to a new Game
4. Call ``game.load(slot)`` — restores the mutated state
5. Assert every persisted field matches the pre-save snapshot

Also verifies that reactive HUD Labels bound to the restored state
produce the right text without extra wiring — the iter-4 reactive
pattern composes cleanly with save/load.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from examples.ring_of_pain.ring_of_pain import RingOfPainScene, build_theme
from saga2d import Game, InputEvent, Label


def _make_game(save_dir: Path) -> Game:
    return Game(
        "ring-of-pain-save-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
        save_dir=save_dir,
    )


def _press(key: str | None = None, action: str | None = None) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action)


def test_save_load_round_trip_preserves_state(tmp_path: Path) -> None:
    """The full persisted-state surface survives a save/load round trip
    through the JSON SaveManager."""
    # --- session 1: mutate state, save ------------------------------------
    game = _make_game(tmp_path)
    scene = RingOfPainScene(ring_size=8, seed=7)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)

    # Interact with a couple of nodes to produce varied state.
    scene._dispatch_key_bindings(_press(action="confirm"))  # act on node 0
    scene._dispatch_key_bindings(_press(key="right"))
    scene._dispatch_key_bindings(_press(action="confirm"))  # act on node 1

    snapshot = {
        "player_idx": scene.player_idx,
        "max_hp": scene.max_hp,
        "hp": scene.hp,
        "coins": scene.coins,
        "level": scene.level,
        "message": scene.message,
        "ring_size": scene.ring_size,
        "nodes": [
            {"type": n.type, "data": dict(n.data), "alive": n.alive}
            for n in scene.nodes
        ],
    }

    game.save(slot=1)
    game._teardown()

    # --- session 2: load into a fresh scene -------------------------------
    game = _make_game(tmp_path)
    restored = RingOfPainScene(ring_size=8, seed=99)  # different seed
    # Before load the fresh scene has different state by construction.
    assert restored.player_idx == 0
    game._scene_stack.push(restored)
    game.tick(dt=1 / 60)

    data = game.load(slot=1)
    assert data is not None, "save slot 1 should have data from session 1"
    assert data["scene_class"] == "RingOfPainScene"

    # Every persisted field matches.
    assert restored.player_idx == snapshot["player_idx"]
    assert restored.hp == snapshot["hp"]
    assert restored.max_hp == snapshot["max_hp"]
    assert restored.coins == snapshot["coins"]
    assert restored.level == snapshot["level"]
    assert restored.message == snapshot["message"]
    assert len(restored.nodes) == len(snapshot["nodes"])
    for restored_node, snap_node in zip(restored.nodes, snapshot["nodes"]):
        assert restored_node.type == snap_node["type"]
        assert restored_node.alive == snap_node["alive"]
        assert restored_node.data == snap_node["data"]

    game._teardown()


def test_reactive_hud_picks_up_loaded_state(tmp_path: Path) -> None:
    """After ``game.load(...)`` the reactive HP/Coins labels should show
    the loaded values on the next tick — no manual UI refresh needed."""
    # Save state from session 1.
    game = _make_game(tmp_path)
    scene = RingOfPainScene(ring_size=8, seed=7)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene.hp = 3
    scene.coins = 42
    game.save(slot=2)
    game._teardown()

    # New session, load.
    game = _make_game(tmp_path)
    restored = RingOfPainScene(ring_size=8, seed=7)
    game._scene_stack.push(restored)
    game.tick(dt=1 / 60)
    game.load(slot=2)
    game.tick(dt=1 / 60)  # reactive labels refresh here

    labels = restored.ui.find_all(lambda c: isinstance(c, Label))
    texts = {l.text for l in labels}
    # Reactive binding (iter-4) automatically renders the loaded value.
    assert any("3/" in t for t in texts), f"HP label did not refresh: {texts}"
    assert any("42" in t for t in texts), f"Coins label did not refresh: {texts}"
    game._teardown()


def test_missing_slot_returns_none(tmp_path: Path) -> None:
    """Loading a slot that was never saved returns None and doesn't raise."""
    game = _make_game(tmp_path)
    scene = RingOfPainScene()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    result = game.load(slot=99)
    assert result is None
    game._teardown()
