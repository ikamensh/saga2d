"""Properties of :meth:`ParticleEmitter.follow` (iter-46).

Before iter-46, attaching an emitter to a sprite required the scene to
push ``emitter.position = (sprite.x, sprite.y + ...)`` every tick in
its ``update`` method. :meth:`ParticleEmitter.follow` moves that
boilerplate into the emitter itself: the emitter tracks the target's
position each update, detaches automatically when the target is
removed, and supports an ``offset=(dx, dy)`` to position the emitter
relative to the target.

Properties verified:

*   After ``follow(target, offset)``, every call to
    :meth:`update` syncs the emitter's position from
    ``(target.x + dx, target.y + dy)``.
*   Moving the target changes the next-tick emitter position.
*   Removing the target detaches the follow silently on the next
    update — no exception, no stale reference retained.
*   ``follow(None)`` clears an existing attachment.
*   ``follow`` is a no-op for continuous spawning: particles spawned
    mid-track use the latest synced position, not the constructor
    one.
*   Finite-offset validation.
"""

from __future__ import annotations

import pytest

from saga2d import Game, Scene, Sprite
from saga2d.rendering.particles import ParticleEmitter


@pytest.fixture
def game():
    g = Game("follow-test", resolution=(200, 200),
             fullscreen=False, backend="mock", visible=False)
    g.assets.image("player_token")
    yield g
    g._teardown()


class _Host(Scene):
    """Minimal scene that owns one sprite so the test doesn't need
    to manually manage ownership."""
    background_color = (0, 0, 0, 255)

    def on_enter(self) -> None:
        self.target = self.add_sprite(Sprite(
            "player_token", position=(100, 100),
        ))


def test_follow_snaps_emitter_to_target_immediately(game: Game) -> None:
    """Calling follow() with a live target sets the emitter's position
    to the target's position + offset before any update runs."""
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    e = ParticleEmitter("player_token", position=(0, 0))
    e.follow(scene.target, offset=(0, 4))
    assert e.position == (100.0, 104.0)


def test_follow_tracks_target_movement(game: Game) -> None:
    """When the target moves, the emitter's position updates on the
    next tick — no scene-level bookkeeping."""
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    e = ParticleEmitter("player_token", position=(0, 0))
    e.follow(scene.target)
    scene.target.position = (150, 50)
    game.tick(dt=1 / 60)
    assert e.position == (150.0, 50.0)


def test_follow_offset_applied_each_tick(game: Game) -> None:
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    e = ParticleEmitter("player_token", position=(0, 0))
    e.follow(scene.target, offset=(10, -20))
    scene.target.position = (50, 80)
    game.tick(dt=1 / 60)
    assert e.position == (60.0, 60.0)


def test_follow_detaches_on_target_removal(game: Game) -> None:
    """When the followed sprite is removed, the next update silently
    drops the reference so we don't hold a stale Sprite alive."""
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    e = ParticleEmitter("player_token", position=(50, 50))
    e.follow(scene.target)
    scene.target.remove()
    game.tick(dt=1 / 60)
    assert e._follow_target is None
    # The emitter should not crash on subsequent ticks.
    game.tick(dt=1 / 60)


def test_follow_with_none_clears_attachment(game: Game) -> None:
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    e = ParticleEmitter("player_token", position=(0, 0))
    e.follow(scene.target)
    e.follow(None)
    assert e._follow_target is None
    # Subsequent movement of the ex-target should NOT move the emitter.
    scene.target.position = (999, 999)
    game.tick(dt=1 / 60)
    # The emitter position is whatever follow(scene.target) last set,
    # not the moved target position.
    assert e.position != (999.0, 999.0)


def test_follow_non_finite_offset_is_rejected(game: Game) -> None:
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    e = ParticleEmitter("player_token", position=(0, 0))
    with pytest.raises(ValueError):
        e.follow(scene.target, offset=(float("nan"), 0))
    with pytest.raises(ValueError):
        e.follow(scene.target, offset=(0, float("inf")))


def test_follow_continuous_spawns_use_synced_position(game: Game) -> None:
    """Continuous emitter with follow: particles spawned across ticks
    appear at the target's *current* position, not the constructor one."""
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    import random as _random
    e = ParticleEmitter(
        "player_token", position=(0, 0),
        speed=(0, 0), lifetime=(2.0, 2.0),  # stationary so we can check position
        rng=_random.Random(1),
    )
    e.follow(scene.target)
    e.continuous(rate=10)
    game.tick(dt=0.1)  # should spawn ~1 particle
    # Move the target and spawn more.
    scene.target.position = (200, 100)
    game.tick(dt=0.1)
    # Find the most recently spawned particle and check its position.
    assert len(e._particles) >= 1
    # Particles at (200, 100) should exist — the emitter followed the
    # target before spawning.
    latest = e._particles[-1]
    assert latest.sprite.x == 200
    assert latest.sprite.y == 100
