"""Sprite integration for Ring of Pain — iter-33.

Exercises saga2d's sprite / image-loading subsystem via the
procedurally-generated ``assets/images/player_token.png``. The PNG
is produced by ``scripts/generate_sprites.py`` (same editorial
pattern as iter-32's WAV generator).

The mock backend tracks ``draw_image`` via its ``images_drawn``
list — each tick records every image blit with handle + position
+ size. Tests assert the player token appears at the expected
coordinates for each player-index value.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from examples.ring_of_pain.ring_of_pain import RingOfPainScene, build_theme
from saga2d import Game


SPRITE_PATH = (
    Path(__file__).resolve().parents[2]
    / "assets" / "images" / "player_token.png"
)


def _make_game() -> Game:
    return Game(
        "rop-sprite-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
    )


def test_player_token_png_is_bundled() -> None:
    """Prerequisite: the procedurally-generated sprite is in the repo."""
    assert SPRITE_PATH.exists(), (
        f"Run scripts/generate_sprites.py to produce {SPRITE_PATH}"
    )


def test_asset_manager_loads_player_token() -> None:
    """``game.assets.image("player_token")`` resolves to the generated
    PNG and returns a valid handle."""
    game = _make_game()
    try:
        handle = game.assets.image("player_token")
        assert handle is not None
    finally:
        game._teardown()


def test_ring_of_pain_caches_handle_in_on_enter() -> None:
    """iter-33: the scene loads the sprite handle once in ``on_enter``
    rather than per-frame, which would re-hit the AssetManager cache
    but still adds bookkeeping. Cache is verified by checking the
    attribute is set after push + tick."""
    game = _make_game()
    try:
        scene = RingOfPainScene()
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)
        assert scene._player_token_handle is not None
    finally:
        game._teardown()


def test_draw_image_fires_during_scene_draw() -> None:
    """Per-tick draw produces at least one image blit via the backend's
    draw_image pathway — the iter-33 replacement for the three
    draw_circle calls that used to render the pip."""
    game = _make_game()
    try:
        scene = RingOfPainScene(ring_size=8, seed=7)
        game._scene_stack.push(scene)
        # First tick pushes on_enter + one draw frame.
        game.tick(dt=1 / 60)
        # Mock backend records image blits as dicts with "handle", "x",
        # "y", "width", "height".
        blits = game.backend.images
        assert len(blits) >= 1, "expected at least one player-token blit"
        # The blit should reference the handle we cached on the scene.
        handles_drawn = {b["image"] for b in blits}
        assert scene._player_token_handle in handles_drawn
    finally:
        game._teardown()


def test_token_follows_player_index() -> None:
    """Moving the player to a different node should reposition the
    blit. The exact coordinates depend on ring geometry but we can
    assert the position changes."""
    game = _make_game()
    try:
        scene = RingOfPainScene(ring_size=8, seed=7)
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)

        # Capture the first tick's blit position (player_idx = 0).
        first_pos = next(
            (b["x"], b["y"]) for b in game.backend.images
            if b["image"] == scene._player_token_handle
        )

        # Rotate CW three times and draw again.
        for _ in range(3):
            scene.rotate_cw()
        game.backend.images.clear()
        game.tick(dt=1 / 60)

        second_pos = next(
            (b["x"], b["y"]) for b in game.backend.images
            if b["image"] == scene._player_token_handle
        )
        assert first_pos != second_pos
    finally:
        game._teardown()


def test_missing_sprite_falls_back_to_procedural_pip(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A stripped-down deploy without the PNG still runs — the scene
    catches AssetNotFoundError in on_enter and leaves
    ``_player_token_handle`` at ``None``. ``draw`` then falls through
    to the original draw_circle pip."""
    # Point AssetManager at an empty directory for this test.
    game = Game(
        "rop-sprite-fallback-test",
        resolution=(800, 600),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
        asset_path=tmp_path,
    )
    try:
        scene = RingOfPainScene()
        game._scene_stack.push(scene)
        game.tick(dt=1 / 60)
        assert scene._player_token_handle is None
        # No image blits — the fallback procedural pip uses draw_circle.
        assert game.backend.images == []
    finally:
        game._teardown()
