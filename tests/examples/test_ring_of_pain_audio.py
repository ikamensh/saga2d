"""Audio integration for Ring of Pain — iter-32.

Exercises saga2d's audio subsystem end-to-end. The framework's
AudioManager + mock backend let us verify that ``_interact`` fires
the right SFX for each node type, without needing an actual sound
card or the pyglet audio pipeline.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from examples.ring_of_pain.ring_of_pain import (
    RingOfPainScene,
    Node,
    build_theme,
    TYPE_ENEMY,
    TYPE_HEART,
    TYPE_PORTAL,
    TYPE_SHOP,
    TYPE_TREASURE,
)
from saga2d import Game, InputEvent


def _make_game() -> Game:
    return Game(
        "rop-audio-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
    )


def _press(key: str | None = None, action: str | None = None) -> InputEvent:
    return InputEvent(type="key_press", key=key, action=action)


# iter-32 generated these WAVs under assets/sounds/ — expected to exist
# in the repo (run ``python scripts/generate_sfx.py`` once to create).
SOUNDS_DIR = Path(__file__).resolve().parents[2] / "assets" / "sounds"


def test_wavs_are_bundled() -> None:
    """Prerequisite for audio tests: the three procedurally-generated
    WAVs should be present in the repo."""
    for name in ("hit.wav", "coin.wav", "heal.wav"):
        path = SOUNDS_DIR / name
        assert path.exists(), f"missing bundled sound: {path}"


def _force_node_and_play(scene: RingOfPainScene, node_type: str) -> None:
    """Replace the current node with a fresh node of *node_type*, then
    fire ``_interact`` — so the test controls which SFX path runs."""
    if node_type == TYPE_ENEMY:
        node = Node(type=TYPE_ENEMY, data={"hp": 2, "atk": 1})
    elif node_type == TYPE_TREASURE:
        node = Node(type=TYPE_TREASURE, data={"coins": 3})
    elif node_type == TYPE_HEART:
        node = Node(type=TYPE_HEART, data={"heal": 3})
    elif node_type == TYPE_SHOP:
        node = Node(type=TYPE_SHOP)
    elif node_type == TYPE_PORTAL:
        node = Node(type=TYPE_PORTAL)
    else:
        raise ValueError(node_type)
    scene.nodes[scene.player_idx] = node
    scene._interact()


def _played_sounds(game: Game, since: int) -> list[str]:
    """Return the asset file paths corresponding to every sound fired
    since index *since*. MockBackend returns opaque handles from
    ``load_sound``; resolve each handle back to its source path so
    tests can assert on filename substrings."""
    # Reverse the handle→path mapping on the mock backend.
    handle_to_path = {h: p for p, h in game.backend._loaded_sounds.items()}
    return [
        handle_to_path.get(s["handle"], "<unknown>")
        for s in game.backend.sounds_played[since:]
    ]


def test_enemy_interaction_plays_hit(game: Game = None) -> None:
    game = _make_game()
    try:
        scene = RingOfPainScene(ring_size=8, seed=7)
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)
        before = len(game.backend.sounds_played)
        _force_node_and_play(scene, TYPE_ENEMY)
        paths = _played_sounds(game, before)
        assert any("hit" in p for p in paths), (
            f"enemy interact should play hit; paths delta: {paths}"
        )
    finally:
        game._teardown()


def test_treasure_interaction_plays_coin() -> None:
    game = _make_game()
    try:
        scene = RingOfPainScene()
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)
        before = len(game.backend.sounds_played)
        _force_node_and_play(scene, TYPE_TREASURE)
        paths = _played_sounds(game, before)
        assert any("coin" in p for p in paths)
    finally:
        game._teardown()


def test_heart_interaction_plays_heal() -> None:
    game = _make_game()
    try:
        scene = RingOfPainScene()
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)
        # Make sure the player isn't at full HP (heal triggers gain>0
        # but _play fires regardless of gain).
        scene.hp = 5
        before = len(game.backend.sounds_played)
        _force_node_and_play(scene, TYPE_HEART)
        paths = _played_sounds(game, before)
        assert any("heal" in p for p in paths)
    finally:
        game._teardown()


def test_shop_interaction_is_silent() -> None:
    """Shop is NYI — interact should NOT play any SFX. Proves the
    _play calls are per-branch, not global."""
    game = _make_game()
    try:
        scene = RingOfPainScene()
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)
        before = len(game.backend.sounds_played)
        _force_node_and_play(scene, TYPE_SHOP)
        after = len(game.backend.sounds_played)
        assert after == before, "Shop interaction should not play audio"
    finally:
        game._teardown()


def test_dead_node_interaction_is_silent() -> None:
    """Interacting with a cleared node shouldn't fire any SFX — the
    early return precedes the _play calls."""
    game = _make_game()
    try:
        scene = RingOfPainScene()
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)
        scene.nodes[scene.player_idx].alive = False
        before = len(game.backend.sounds_played)
        scene._interact()
        after = len(game.backend.sounds_played)
        assert after == before
    finally:
        game._teardown()


def test_end_to_end_audio_fires_via_keypress() -> None:
    """Full dispatch chain: inject a keypress, scene.controls routes
    to _interact, _interact plays the right sound. No manual method
    invocation."""
    game = _make_game()
    try:
        scene = RingOfPainScene(ring_size=8, seed=7)
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)
        # Force a known node type at player position.
        scene.nodes[scene.player_idx] = Node(
            type=TYPE_TREASURE, data={"coins": 3},
        )
        before = len(game.backend.sounds_played)
        # Keypress through the scene's declarative Scene.controls map.
        game.backend.inject_key("space")
        game.tick(dt=1 / 60)
        paths = _played_sounds(game, before)
        assert any("coin" in p for p in paths)
    finally:
        game._teardown()
