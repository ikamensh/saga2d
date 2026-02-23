"""Tests for Sprite animation integration: play, queue, stop, game-loop updates."""

from pathlib import Path

import pytest

from easygame import Game, Sprite
from easygame.animation import AnimationDef
from easygame.assets import AssetManager
from easygame.backends.mock_backend import MockBackend
from easygame.rendering.layers import SpriteAnchor


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------

@pytest.fixture
def asset_dir(tmp_path: Path) -> Path:
    """Temp asset dir with walk (4 frames) and idle (2 frames) animations."""
    images = tmp_path / "images" / "sprites"
    images.mkdir(parents=True)
    # Static image for sprite creation.
    (images / "knight.png").write_bytes(b"png")
    # Walk animation: 4 frames.
    for i in range(1, 5):
        (images / f"walk_{i:02d}.png").write_bytes(b"png")
    # Idle animation: 2 frames.
    (images / "idle_01.png").write_bytes(b"png")
    (images / "idle_02.png").write_bytes(b"png")
    # Attack animation: 3 frames.
    (images / "attack_01.png").write_bytes(b"png")
    (images / "attack_02.png").write_bytes(b"png")
    (images / "attack_03.png").write_bytes(b"png")
    return tmp_path


@pytest.fixture
def game(asset_dir: Path) -> Game:
    g = Game("Test", backend="mock", resolution=(800, 600))
    g.assets = AssetManager(g.backend, base_path=asset_dir)
    return g


@pytest.fixture
def backend(game: Game) -> MockBackend:
    return game.backend


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _walk_anim() -> AnimationDef:
    return AnimationDef(
        frames=[
            "sprites/walk_01",
            "sprites/walk_02",
            "sprites/walk_03",
            "sprites/walk_04",
        ],
        frame_duration=0.1,
        loop=True,
    )


def _idle_anim() -> AnimationDef:
    return AnimationDef(
        frames=["sprites/idle_01", "sprites/idle_02"],
        frame_duration=0.2,
        loop=True,
    )


def _attack_anim() -> AnimationDef:
    return AnimationDef(
        frames=[
            "sprites/attack_01",
            "sprites/attack_02",
            "sprites/attack_03",
        ],
        frame_duration=0.1,
        loop=False,
    )


# ------------------------------------------------------------------
# play() basics
# ------------------------------------------------------------------

def test_play_sets_first_frame_image(game: Game, backend: MockBackend) -> None:
    """play() immediately pushes the first frame's image to the backend."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    walk = _walk_anim()
    sprite.play(walk)

    record = backend.sprites[sprite.sprite_id]
    expected_handle = game.assets.image("sprites/walk_01")
    assert record["image"] == expected_handle


def test_play_registers_for_auto_update(game: Game) -> None:
    """play() adds the sprite to game._animated_sprites."""
    sprite = Sprite("sprites/knight", position=(100, 100))
    assert sprite not in game._animated_sprites

    sprite.play(_walk_anim())
    assert sprite in game._animated_sprites


def test_play_with_prefix_string(game: Game, backend: MockBackend) -> None:
    """play() works with AnimationDef using a prefix string."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    anim = AnimationDef(frames="sprites/walk", frame_duration=0.1, loop=True)
    sprite.play(anim)

    record = backend.sprites[sprite.sprite_id]
    expected_handle = game.assets.image("sprites/walk_01")
    assert record["image"] == expected_handle


# ------------------------------------------------------------------
# Frame advancement via update_animation
# ------------------------------------------------------------------

def test_frame_advances_after_duration(game: Game, backend: MockBackend) -> None:
    """After frame_duration seconds, the displayed frame changes."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    sprite.play(_walk_anim())

    sprite.update_animation(0.1)

    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/walk_02")
    assert record["image"] == expected


def test_no_advance_before_duration(game: Game, backend: MockBackend) -> None:
    """Frame stays the same when not enough time has elapsed."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    sprite.play(_walk_anim())

    sprite.update_animation(0.05)

    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/walk_01")
    assert record["image"] == expected


# ------------------------------------------------------------------
# Looping
# ------------------------------------------------------------------

def test_looping_cycles_back_to_first_frame(
    game: Game, backend: MockBackend,
) -> None:
    """After the last frame, a looping animation wraps to frame 0."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    walk = _walk_anim()  # 4 frames × 0.1s
    sprite.play(walk)

    # Advance through all 4 frames and wrap.
    sprite.update_animation(0.1)  # → frame 1 (walk_02)
    sprite.update_animation(0.1)  # → frame 2 (walk_03)
    sprite.update_animation(0.1)  # → frame 3 (walk_04)
    sprite.update_animation(0.1)  # → frame 0 (walk_01, wrap)

    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/walk_01")
    assert record["image"] == expected


# ------------------------------------------------------------------
# One-shot (non-looping) with on_complete
# ------------------------------------------------------------------

def test_oneshot_completes_after_correct_time(
    game: Game, backend: MockBackend,
) -> None:
    """A 3-frame × 0.1s non-looping animation finishes at 0.3s."""
    attack = _attack_anim()  # 3 frames × 0.1s, loop=False
    completed = []

    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    sprite.play(attack, on_complete=lambda: completed.append(True))

    # Frame 0 → 1.
    sprite.update_animation(0.1)
    assert len(completed) == 0
    # Frame 1 → 2.
    sprite.update_animation(0.1)
    assert len(completed) == 0
    # Frame 2 → finish (stays on frame 2, fires callback).
    sprite.update_animation(0.1)
    assert len(completed) == 1

    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/attack_03")
    assert record["image"] == expected


def test_oneshot_stays_on_last_frame(game: Game, backend: MockBackend) -> None:
    """After finishing, further updates don't change the frame."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    sprite.play(_attack_anim())

    # Run through all frames + extra.
    for _ in range(10):
        sprite.update_animation(0.1)

    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/attack_03")
    assert record["image"] == expected


# ------------------------------------------------------------------
# play() interrupts current animation
# ------------------------------------------------------------------

def test_play_interrupts_current(game: Game, backend: MockBackend) -> None:
    """Calling play() mid-animation replaces the current animation."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    sprite.play(_walk_anim())
    sprite.update_animation(0.1)  # advance walk to frame 1

    # Interrupt with attack.
    sprite.play(_attack_anim())

    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/attack_01")
    assert record["image"] == expected


def test_play_clears_queue(game: Game) -> None:
    """play() clears any queued animations."""
    sprite = Sprite("sprites/knight", position=(100, 100))
    sprite.play(_attack_anim())
    sprite.queue(_idle_anim())
    sprite.queue(_walk_anim())

    # play() replaces everything.
    sprite.play(_walk_anim())
    assert len(sprite._anim_queue) == 0


# ------------------------------------------------------------------
# queue()
# ------------------------------------------------------------------

def test_queue_plays_after_current_finishes(
    game: Game, backend: MockBackend,
) -> None:
    """Queued animation starts after the current one-shot finishes."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    attack = _attack_anim()  # 3 frames × 0.1s, loop=False
    idle = _idle_anim()

    sprite.play(attack)
    sprite.queue(idle)

    # Play through attack: frames 0→1→2→finish → idle starts.
    sprite.update_animation(0.1)  # attack frame 1
    sprite.update_animation(0.1)  # attack frame 2
    sprite.update_animation(0.1)  # attack finish → idle starts at frame 0

    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/idle_01")
    assert record["image"] == expected


def test_queue_when_nothing_playing_starts_immediately(
    game: Game, backend: MockBackend,
) -> None:
    """queue() with no current animation starts immediately (like play)."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    sprite.queue(_walk_anim())

    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/walk_01")
    assert record["image"] == expected


def test_queue_chain_three_animations(
    game: Game, backend: MockBackend,
) -> None:
    """Queue multiple animations: attack → idle starts after attack completes."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    attack = _attack_anim()  # 3 frames, loop=False
    idle = _idle_anim()      # loop=True

    callback_fired = []
    sprite.play(attack, on_complete=lambda: callback_fired.append("attack"))
    sprite.queue(idle, on_complete=lambda: callback_fired.append("idle"))

    # Play through attack.
    sprite.update_animation(0.1)  # attack frame 1
    sprite.update_animation(0.1)  # attack frame 2
    sprite.update_animation(0.1)  # attack finish → callback → idle starts

    # Attack callback should have fired.
    assert "attack" in callback_fired

    # Idle should now be playing.
    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/idle_01")
    assert record["image"] == expected


# ------------------------------------------------------------------
# stop_animation()
# ------------------------------------------------------------------

def test_stop_animation_stops_playback(
    game: Game, backend: MockBackend,
) -> None:
    """stop_animation() stops the animation; frame stays as-is."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    sprite.play(_walk_anim())
    sprite.update_animation(0.1)  # → walk_02

    sprite.stop_animation()

    # Further updates don't change the frame.
    sprite.update_animation(0.5)
    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/walk_02")
    assert record["image"] == expected


def test_stop_animation_clears_queue(game: Game) -> None:
    """stop_animation() clears the animation queue."""
    sprite = Sprite("sprites/knight", position=(100, 100))
    sprite.play(_attack_anim())
    sprite.queue(_idle_anim())

    sprite.stop_animation()
    assert len(sprite._anim_queue) == 0


def test_stop_animation_deregisters(game: Game) -> None:
    """stop_animation() removes the sprite from game._animated_sprites."""
    sprite = Sprite("sprites/knight", position=(100, 100))
    sprite.play(_walk_anim())
    assert sprite in game._animated_sprites

    sprite.stop_animation()
    assert sprite not in game._animated_sprites


# ------------------------------------------------------------------
# remove() clears animation
# ------------------------------------------------------------------

def test_remove_deregisters_animation(game: Game) -> None:
    """remove() stops animation and deregisters from auto-update."""
    sprite = Sprite("sprites/knight", position=(100, 100))
    sprite.play(_walk_anim())
    assert sprite in game._animated_sprites

    sprite.remove()
    assert sprite not in game._animated_sprites


def test_play_on_removed_sprite_is_noop(game: Game) -> None:
    """play() on a removed sprite does nothing."""
    sprite = Sprite("sprites/knight", position=(100, 100))
    sprite.remove()
    sprite.play(_walk_anim())  # should not raise
    assert sprite not in game._animated_sprites


# ------------------------------------------------------------------
# Automatic update via game.tick()
# ------------------------------------------------------------------

def test_game_tick_advances_animation(game: Game, backend: MockBackend) -> None:
    """game.tick(dt) automatically advances sprite animation."""
    sprite = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    sprite.play(_walk_anim())

    # tick with dt=0.1 should advance to walk_02.
    game.tick(dt=0.1)

    record = backend.sprites[sprite.sprite_id]
    expected = game.assets.image("sprites/walk_02")
    assert record["image"] == expected


def test_game_tick_multiple_sprites(game: Game, backend: MockBackend) -> None:
    """game.tick() updates all animated sprites."""
    s1 = Sprite(
        "sprites/knight", position=(100, 100), anchor=SpriteAnchor.TOP_LEFT,
    )
    s2 = Sprite(
        "sprites/knight", position=(200, 200), anchor=SpriteAnchor.TOP_LEFT,
    )
    s1.play(_walk_anim())
    s2.play(_attack_anim())

    game.tick(dt=0.1)

    r1 = backend.sprites[s1.sprite_id]
    r2 = backend.sprites[s2.sprite_id]
    assert r1["image"] == game.assets.image("sprites/walk_02")
    assert r2["image"] == game.assets.image("sprites/attack_02")


def test_game_tick_oneshot_fires_callback(game: Game) -> None:
    """on_complete fires when animation finishes during game.tick()."""
    sprite = Sprite("sprites/knight", position=(100, 100))
    fired = []
    sprite.play(_attack_anim(), on_complete=lambda: fired.append(True))

    # 3 frames × 0.1s each — need 3 ticks to finish.
    game.tick(dt=0.1)
    game.tick(dt=0.1)
    game.tick(dt=0.1)

    assert len(fired) == 1
