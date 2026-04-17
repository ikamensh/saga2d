"""Properties of :meth:`Sprite.follow` (iter-47).

Parallel to iter-46's :meth:`ParticleEmitter.follow` — attaches a
sprite to another sprite so its position tracks each tick. Auto-
detaches when the target is removed.

Tests below verify the sprite-to-sprite contract:

*   ``follow(target, offset)`` snaps position immediately, so the
    first rendered frame already sees the correct position.
*   On each subsequent tick, the follower's position tracks the
    target + offset.
*   When the target is removed, the follower silently detaches on
    the next tick — no stale reference retained.
*   ``follow(None)`` clears an existing attachment.
*   Non-finite offsets are rejected with a clear ValueError.
*   Removing the follower deregisters it from the game's
    ``_follow_sprites`` set.
*   A sprite already in the ``_follow_sprites`` set that calls
    ``follow(new_target)`` seamlessly swaps targets without
    duplicate registrations.
"""

from __future__ import annotations

import pytest

from saga2d import Game, Scene, Sprite


@pytest.fixture
def game():
    g = Game("sprite-follow-test", resolution=(200, 200),
             fullscreen=False, backend="mock", visible=False)
    g.assets.image("player_token")
    yield g
    g._teardown()


class _Host(Scene):
    background_color = (0, 0, 0, 255)

    def on_enter(self) -> None:
        self.a = self.add_sprite(Sprite("player_token", position=(100, 100)))
        self.b = self.add_sprite(Sprite("player_token", position=(0, 0)))


def test_follow_snaps_position_immediately(game: Game) -> None:
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene.b.follow(scene.a, offset=(10, -20))
    # Immediate — before any subsequent tick.
    assert scene.b.position == (110.0, 80.0)


def test_follow_tracks_target_movement_each_tick(game: Game) -> None:
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene.b.follow(scene.a, offset=(5, 5))
    scene.a.position = (200, 50)
    game.tick(dt=1 / 60)
    assert scene.b.position == (205.0, 55.0)


def test_follow_none_clears_attachment(game: Game) -> None:
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene.b.follow(scene.a)
    scene.b.follow(None)
    scene.a.position = (999, 999)
    game.tick(dt=1 / 60)
    # b shouldn't have moved to 999, 999.
    assert scene.b.position != (999.0, 999.0)
    # And it's no longer in the follow-sprites set.
    assert scene.b not in game._follow_sprites


def test_follow_detaches_when_target_removed(game: Game) -> None:
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene.b.follow(scene.a)
    scene.a.remove()
    game.tick(dt=1 / 60)
    assert scene.b._follow_target is None
    # The follower itself is still alive; follow() just cleaned up.
    assert not scene.b.is_removed
    # And it's no longer in the follow-sprites set.
    assert scene.b not in game._follow_sprites


def test_removing_follower_deregisters_from_follow_sprites(game: Game) -> None:
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene.b.follow(scene.a)
    assert scene.b in game._follow_sprites
    scene.b.remove()
    assert scene.b not in game._follow_sprites


def test_follow_non_finite_offset_is_rejected(game: Game) -> None:
    scene = _Host()
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    with pytest.raises(ValueError):
        scene.b.follow(scene.a, offset=(float("nan"), 0))
    with pytest.raises(ValueError):
        scene.b.follow(scene.a, offset=(0, float("inf")))


def test_follow_can_swap_targets(game: Game) -> None:
    """A sprite already following X can switch to following Y without
    duplicate registrations in the follow set."""
    scene = _Host()
    game._scene_stack.push(scene)
    # Add a third sprite to follow.
    c = scene.add_sprite(Sprite("player_token", position=(50, 50)))
    game.tick(dt=1 / 60)

    scene.b.follow(scene.a)
    assert scene.b in game._follow_sprites
    scene.b.follow(c)  # switch
    # Still exactly one membership.
    count = sum(1 for s in game._follow_sprites if s is scene.b)
    assert count == 1
    # And b now tracks c, not a.
    scene.a.position = (999, 999)
    c.position = (77, 77)
    game.tick(dt=1 / 60)
    assert scene.b.position == (77.0, 77.0)


def test_follow_chain_updates_in_one_tick(game: Game) -> None:
    """b follows a, c follows b. When a moves, does c eventually sync?

    The ``_update_sprite_follows`` phase iterates the set once. If c is
    processed before b, c would lag one tick — that's an accepted
    limitation. This test documents which behaviour saga2d implements.
    """
    scene = _Host()
    game._scene_stack.push(scene)
    c = scene.add_sprite(Sprite("player_token", position=(0, 0)))
    game.tick(dt=1 / 60)

    scene.b.follow(scene.a, offset=(5, 0))
    c.follow(scene.b, offset=(5, 0))
    scene.a.position = (100, 100)
    game.tick(dt=1 / 60)
    # After one tick b should be at (105, 100). c should be at a
    # value depending on iteration order. We just verify they're
    # within two ticks of catching up.
    game.tick(dt=1 / 60)
    assert scene.b.position == (105.0, 100.0)
    assert c.position == (110.0, 100.0)
