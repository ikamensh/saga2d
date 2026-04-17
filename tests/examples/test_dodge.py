"""Properties of the iter-43 ``dodge`` example.

The example was added to exercise saga2d's sprite + action subsystems
end-to-end (they shipped iter-24..26 but no runnable example used them
until iter-43). These tests check:

*   Structural snapshot of the scene tree (iter-15 pattern).
*   Game state after N ticks: time advances, rocks spawn, game_over
    stays False until a collision.
*   A contrived collision forces game_over to flip True.
*   Restart resets state without rebuilding the scene.
*   Held-key set drives continuous player motion.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from saga2d import Game
from saga2d.testing import assert_scene_matches_snapshot

from examples.dodge.dodge import DodgeScene, build_theme


SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


@pytest.fixture
def game():
    g = Game(
        "dodge-test",
        resolution=(600, 800),
        fullscreen=False,
        backend="mock",
        visible=False,
        theme=build_theme(),
    )
    yield g
    g._teardown()


# ---------------------------------------------------------------------------
# Structural snapshot
# ---------------------------------------------------------------------------


def test_dodge_scene_structure_stable(game: Game) -> None:
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    assert_scene_matches_snapshot(scene, "dodge", SNAPSHOT_DIR)


# ---------------------------------------------------------------------------
# Game state properties
# ---------------------------------------------------------------------------


def test_time_advances_with_ticks(game: Game) -> None:
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    assert scene.time_survived == 0.0
    for _ in range(10):
        game.tick(dt=0.1)
    # 10 ticks of 0.1 = 1 second (approximately).
    assert scene.time_survived == pytest.approx(1.0)


def test_rocks_spawn_over_time(game: Game) -> None:
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    # Over 5 seconds, the rock spawn interval (starts at 1.2s) should
    # give at least two spawns.
    for _ in range(100):
        game.tick(dt=0.05)
    assert len(scene._rocks) >= 1, "rocks should have spawned by 5 seconds"


def test_game_over_defaults_false(game: Game) -> None:
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    assert scene.game_over is False


def test_collision_triggers_game_over(game: Game) -> None:
    """Force a rock to share coordinates with the player and verify
    the collision check fires on the next tick."""
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)  # spawn player

    # Spawn one rock and place it directly on top of the player.
    scene._spawn_rock()
    rock = scene._rocks[-1]
    rock.stop_actions()  # freeze it
    rock.position = scene._player.position

    game.tick(dt=1 / 60)
    assert scene.game_over is True


def test_restart_resets_state(game: Game) -> None:
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene.time_survived = 12.3
    scene.game_over = True
    scene.restart()
    assert scene.time_survived == 0.0
    assert scene.game_over is False
    assert scene._player is not None


def test_high_score_tracked_across_restarts(game: Game) -> None:
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    scene.time_survived = 7.5
    scene._end_run()
    assert scene.high_score == 7.5
    scene.restart()
    assert scene.time_survived == 0.0
    assert scene.high_score == 7.5


# ---------------------------------------------------------------------------
# Input — continuous held-key motion, via iter-44's level-triggered API
# ---------------------------------------------------------------------------


def test_held_d_moves_player_right(game: Game) -> None:
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    start_x = scene._player.x
    game.backend.inject_key("d", type="key_press")
    for _ in range(10):
        game.tick(dt=0.05)
    assert scene._player.x > start_x


def test_held_a_moves_player_left(game: Game) -> None:
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    start_x = scene._player.x
    game.backend.inject_key("a", type="key_press")
    for _ in range(10):
        game.tick(dt=0.05)
    assert scene._player.x < start_x


def test_release_stops_movement(game: Game) -> None:
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    game.backend.inject_key("d", type="key_press")
    game.tick(dt=0.1)
    x_after_move = scene._player.x
    game.backend.inject_key("d", type="key_release")
    for _ in range(10):
        game.tick(dt=0.05)
    assert scene._player.x == pytest.approx(x_after_move)


def test_player_clamped_to_canvas(game: Game) -> None:
    """The player can't walk off either edge of the playfield."""
    scene = DodgeScene(seed=0)
    game._scene_stack.push(scene)
    game.tick(dt=1 / 60)
    game.backend.inject_key("a", type="key_press")
    for _ in range(200):  # way more than needed to reach the left edge
        game.tick(dt=0.05)
    w, _ = game.resolution
    assert scene._player.x >= 48 / 2, "player clamped to left edge"
    assert scene._player.x <= w - 48 / 2, "player clamped to right edge"
