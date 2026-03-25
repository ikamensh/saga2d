"""Stage 4 real-user gameplay workflow — pytest version.

Exercises the full gameplay loop that a real saga2d user would write:
- Game creation, scene lifecycle, sprite ownership, input handling
- Update loop with movement, AABB collision detection, score tracking
- Scene transitions (push/pop PauseScene, push/pop InventoryScene, replace VictoryScene)
- Timer/action behavior across scene transitions
- Sprite re-creation on on_reveal (framework design: owned sprites removed on push-over)
"""

from __future__ import annotations

import math
from typing import Any

import pytest

from saga2d import (
    Delay,
    Do,
    FadeIn,
    FadeOut,
    Game,
    MoveTo,
    Parallel,
    Repeat,
    Scene,
    Sequence,
    Sprite,
)
from saga2d.rendering.camera import Camera
from saga2d.rendering.layers import RenderLayer

# ── Configuration ────────────────────────────────────────────────────────

RESOLUTION = (800, 600)
DT = 1 / 60
PLAYER_SPEED = 200.0
PLAYER_STEP = PLAYER_SPEED * DT


# ── AABB collision helpers ───────────────────────────────────────────────

def aabb_collides(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, by: float, bw: float, bh: float,
) -> bool:
    return ax < bx + bw and ax + aw > bx and ay < by + bh and ay + ah > by


def sprite_rect(sprite: Sprite) -> tuple[float, float, float, float]:
    w, h = 64, 64  # mock backend default
    left = sprite.x - w / 2
    top = sprite.y - h
    return (left, top, w, h)


# ── Scene definitions ────────────────────────────────────────────────────

class PauseScene(Scene):
    transparent = True
    pop_on_cancel = True

    def on_enter(self):
        self.entered = True

    def on_exit(self):
        self.exited = True

    def draw(self):
        self.draw_rect(0, 0, 800, 600, (0, 0, 0, 128), opacity=0.5)


class InventoryScene(Scene):
    transparent = False
    pop_on_cancel = True

    def __init__(self):
        super().__init__()
        self.timer_fired = False

    def on_enter(self):
        self._inv_timer = self.after(0.5, self._on_timer)

    def _on_timer(self):
        self.timer_fired = True

    def on_exit(self):
        self.exited = True


class VictoryScene(Scene):
    def on_enter(self):
        self.entered = True


class GameplayScene(Scene):
    background_color = (30, 30, 50)

    def on_enter(self):
        self.camera = Camera(RESOLUTION, world_bounds=(0, 0, 1600, 1200))
        self.player_pos = (400.0, 300.0)
        self.enemy_pos = (150.0, 300.0)
        self.ghost_pos = (600.0, 400.0)
        self.coin_pos = (500.0, 300.0)
        self.coin_alive = True
        self.score = 0
        self.player_hit = False
        self.items_collected = []
        self.bonus_spawned = False
        self.exit_count = 0
        self.reveal_count = 0
        self._create_sprites()
        self.score_timer = self.every(1.0, self._tick_score)
        self.spawn_timer = self.after(2.0, self._spawn_bonus)
        self.bind_key("i", lambda: self.game.push(InventoryScene()))
        self.bind_key("cancel", lambda: self.game.push(PauseScene()))
        self._move_dx = 0.0
        self._move_dy = 0.0

    def _create_sprites(self):
        self.camera.center_on(*self.player_pos)
        self.player = self.add_sprite(
            Sprite("sprites/player", position=self.player_pos, layer=RenderLayer.UNITS)
        )
        self.enemy = self.add_sprite(
            Sprite("sprites/enemy", position=self.enemy_pos, layer=RenderLayer.UNITS)
        )
        self.enemy.do(Repeat(Sequence(
            MoveTo((300, 300), speed=80),
            Delay(0.5),
            MoveTo((150, 300), speed=80),
            Delay(0.5),
        )))
        self.ghost = self.add_sprite(
            Sprite("sprites/ghost", position=self.ghost_pos, layer=RenderLayer.EFFECTS)
        )
        self.ghost.do(Repeat(Sequence(FadeOut(0.4), FadeIn(0.4))))
        if self.coin_alive:
            self.coin = self.add_sprite(
                Sprite("sprites/coin", position=self.coin_pos, layer=RenderLayer.OBJECTS)
            )
            self.coin.do(Repeat(Sequence(FadeOut(0.3), FadeIn(0.3))))
        else:
            self.coin = None
        if self.bonus_spawned and hasattr(self, '_bonus_pos'):
            self.bonus = self.add_sprite(
                Sprite("sprites/bonus", position=self._bonus_pos, layer=RenderLayer.OBJECTS)
            )

    def on_exit(self):
        self.exit_count += 1
        if not self.player.is_removed:
            self.player_pos = self.player.position
        if not self.enemy.is_removed:
            self.enemy_pos = self.enemy.position
        if not self.ghost.is_removed:
            self.ghost_pos = self.ghost.position

    def on_reveal(self):
        self.reveal_count += 1
        self._create_sprites()

    def _tick_score(self):
        self.score += 10

    def _spawn_bonus(self):
        if hasattr(self, 'game') and self.game is not None:
            self._bonus_pos = (300.0, 450.0)
            self.bonus_spawned = True
            if not self.player.is_removed:
                self.bonus = self.add_sprite(
                    Sprite("sprites/bonus", position=self._bonus_pos, layer=RenderLayer.OBJECTS)
                )

    def handle_input(self, event):
        if event.type == "key_press":
            if event.action == "up":
                self._move_dy = -PLAYER_STEP
                return True
            elif event.action == "down":
                self._move_dy = PLAYER_STEP
                return True
            elif event.action == "left":
                self._move_dx = -PLAYER_STEP
                return True
            elif event.action == "right":
                self._move_dx = PLAYER_STEP
                return True
        elif event.type == "key_release":
            if event.action in ("up", "down"):
                self._move_dy = 0.0
                return True
            elif event.action in ("left", "right"):
                self._move_dx = 0.0
                return True
        return False

    def update(self, dt):
        if self._move_dx != 0 or self._move_dy != 0:
            new_x = max(32, min(1568, self.player.x + self._move_dx))
            new_y = max(64, min(1200, self.player.y + self._move_dy))
            self.player.position = (new_x, new_y)
        self.camera.center_on(self.player.x, self.player.y)
        if self.coin is not None and not self.coin.is_removed:
            if aabb_collides(*sprite_rect(self.player), *sprite_rect(self.coin)):
                self.coin.remove()
                self._get_owned_sprites().discard(self.coin)
                self.coin = None
                self.coin_alive = False
                self.score += 50
                self.items_collected.append("coin")
        if not self.enemy.is_removed and not self.player_hit:
            if aabb_collides(*sprite_rect(self.player), *sprite_rect(self.enemy)):
                self.player_hit = True
                self.player.tint = (1.0, 0.3, 0.3)
                self.after(0.5, lambda: setattr(self.player, 'tint', (1.0, 1.0, 1.0)))

    def draw(self):
        for sprite in [self.player, self.enemy, self.ghost]:
            if not sprite.is_removed:
                r = sprite_rect(sprite)
                self.draw_world_rect(r[0], r[1], r[2], r[3], (0, 255, 0, 64))


# ── Fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def game_env(tmp_path):
    """Provide a game with sprite asset stubs and custom asset_path."""
    img_dir = tmp_path / "images" / "sprites"
    img_dir.mkdir(parents=True)
    for name in ("player", "enemy", "ghost", "coin", "bonus"):
        (img_dir / f"{name}.png").write_bytes(b"png")
    game = Game("WorkflowTest", backend="mock", resolution=RESOLUTION, asset_path=tmp_path)
    yield game
    game._teardown()


# ── Tests ────────────────────────────────────────────────────────────────

class TestGameplayWorkflow:
    """Full gameplay workflow: create scene, input, collisions, transitions."""

    def test_scene_enter_creates_sprites(self, game_env):
        game = game_env
        scene = GameplayScene()
        game.push(scene)
        assert not scene.player.is_removed
        assert not scene.enemy.is_removed
        assert not scene.ghost.is_removed
        assert scene.coin is not None and not scene.coin.is_removed

    def test_enemy_patrol_action_runs(self, game_env):
        game = game_env
        scene = GameplayScene()
        game.push(scene)
        initial_x = scene.enemy.x
        for _ in range(40):
            game.tick(dt=DT)
        assert scene.enemy.x != initial_x, "Enemy patrol action not running"

    def test_player_movement_via_input(self, game_env):
        game = game_env
        backend = game.backend
        scene = GameplayScene()
        game.push(scene)
        initial_x = scene.player.x
        backend.inject_key("right", type="key_press")
        for _ in range(20):
            game.tick(dt=DT)
        backend.inject_key("right", type="key_release")
        game.tick(dt=DT)
        assert scene.player.x > initial_x, "Player didn't move right"

    def test_coin_collision_collection(self, game_env):
        game = game_env
        backend = game.backend
        scene = GameplayScene()
        game.push(scene)
        # Move right toward coin at (500, 300)
        backend.inject_key("right", type="key_press")
        for _ in range(200):
            game.tick(dt=DT)
            if not scene.coin_alive:
                break
        assert not scene.coin_alive, "Coin was not collected"
        assert "coin" in scene.items_collected
        assert scene.score >= 50

    def test_enemy_collision_detection(self, game_env):
        game = game_env
        backend = game.backend
        scene = GameplayScene()
        game.push(scene)
        # Move left toward enemy at (150, 300)
        backend.inject_key("left", type="key_press")
        for _ in range(300):
            game.tick(dt=DT)
            if scene.player_hit:
                break
        backend.inject_key("left", type="key_release")
        game.tick(dt=DT)
        assert scene.player_hit, "Enemy collision not detected"

    def test_score_timer_fires(self, game_env):
        game = game_env
        scene = GameplayScene()
        game.push(scene)
        assert scene.score == 0
        # Run 1.1s worth of ticks
        for _ in range(70):
            game.tick(dt=DT)
        assert scene.score >= 10, f"Score timer didn't fire: score={scene.score}"

    def test_bonus_spawn_timer(self, game_env):
        game = game_env
        scene = GameplayScene()
        game.push(scene)
        assert not scene.bonus_spawned
        # Run 2.1s worth of ticks
        for _ in range(130):
            game.tick(dt=DT)
        assert scene.bonus_spawned, "Bonus spawn timer didn't fire"

    def test_pause_push_pop_lifecycle(self, game_env):
        game = game_env
        backend = game.backend
        scene = GameplayScene()
        game.push(scene)
        for _ in range(10):
            game.tick(dt=DT)
        player_pos = scene.player.position

        # Push pause
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)
        assert scene.exit_count == 1, "on_exit not called on push"
        assert scene.player.is_removed, "Sprites should be cleaned up on push"

        # Pop pause
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)
        assert scene.reveal_count == 1, "on_reveal not called on pop"
        assert not scene.player.is_removed, "Sprites not re-created on reveal"
        assert abs(scene.player.x - player_pos[0]) < 1.0, "Position not preserved"

    def test_sprites_removed_during_push_recreated_on_reveal(self, game_env):
        game = game_env
        backend = game.backend
        scene = GameplayScene()
        game.push(scene)
        for _ in range(10):
            game.tick(dt=DT)

        # Collect coin first
        backend.inject_key("right", type="key_press")
        for _ in range(200):
            game.tick(dt=DT)
            if not scene.coin_alive:
                break
        backend.inject_key("right", type="key_release")
        game.tick(dt=DT)
        assert not scene.coin_alive

        # Push and pop
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)

        # Coin should NOT reappear
        assert scene.coin is None, "Collected coin should not be recreated"
        # Other sprites should be back
        assert not scene.player.is_removed
        assert not scene.enemy.is_removed

    def test_inventory_timer_cancelled_on_exit(self, game_env):
        game = game_env
        backend = game.backend
        scene = GameplayScene()
        game.push(scene)
        for _ in range(5):
            game.tick(dt=DT)

        # Push inventory
        backend.inject_key("i", type="key_press")
        game.tick(dt=DT)
        inv = game._scene_stack.top()
        assert isinstance(inv, InventoryScene)
        assert not inv.timer_fired

        # Run a few ticks (not enough for 0.5s timer)
        for _ in range(10):
            game.tick(dt=DT)

        # Pop inventory
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)
        assert hasattr(inv, 'exited') and inv.exited

        # Run enough ticks for the timer to have fired (if not cancelled)
        for _ in range(60):
            game.tick(dt=DT)
        assert not inv.timer_fired, "Inventory timer should be cancelled on exit"

    def test_ghost_action_continues_after_reveal(self, game_env):
        game = game_env
        backend = game.backend
        scene = GameplayScene()
        game.push(scene)
        for _ in range(10):
            game.tick(dt=DT)

        # Push and pop pause
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)

        # Ghost should have varying opacity (action re-created)
        opacities = set()
        for _ in range(30):
            game.tick(dt=DT)
            opacities.add(scene.ghost.opacity)
        assert len(opacities) > 1, f"Ghost fade action not running: {opacities}"

    def test_replace_cleans_up_all_sprites(self, game_env):
        game = game_env
        scene = GameplayScene()
        game.push(scene)
        for _ in range(10):
            game.tick(dt=DT)

        player_ref = scene.player
        enemy_ref = scene.enemy

        victory = VictoryScene()
        game.replace(victory)
        assert player_ref.is_removed, "Player not cleaned up on replace"
        assert enemy_ref.is_removed, "Enemy not cleaned up on replace"
        assert victory.entered

    def test_movement_resumes_after_pause_pop(self, game_env):
        game = game_env
        backend = game.backend
        scene = GameplayScene()
        game.push(scene)
        for _ in range(10):
            game.tick(dt=DT)

        # Push and pop pause
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)

        # Now move down
        y_before = scene.player.y
        backend.inject_key("down", type="key_press")
        for _ in range(20):
            game.tick(dt=DT)
        backend.inject_key("down", type="key_release")
        game.tick(dt=DT)
        assert scene.player.y > y_before, "Player didn't move after unpause"

    def test_multiple_transitions_lifecycle_counts(self, game_env):
        game = game_env
        backend = game.backend
        scene = GameplayScene()
        game.push(scene)
        for _ in range(5):
            game.tick(dt=DT)

        # Pause -> unpause
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)

        # Inventory -> close
        backend.inject_key("i", type="key_press")
        game.tick(dt=DT)
        backend.inject_key("escape", type="key_press")
        game.tick(dt=DT)

        # Replace with victory
        game.replace(VictoryScene())

        assert scene.exit_count == 3, f"Expected 3 exits, got {scene.exit_count}"
        assert scene.reveal_count == 2, f"Expected 2 reveals, got {scene.reveal_count}"

    def test_draw_world_rects_during_gameplay(self, game_env):
        game = game_env
        scene = GameplayScene()
        game.push(scene)
        game.tick(dt=DT)
        # Check that debug rects were drawn (3 sprites × 1 rect each)
        backend = game.backend
        # Rects are drawn in draw(), which happens during tick
        assert len(backend.rects) >= 3, (
            f"Expected ≥3 debug rects, got {len(backend.rects)}"
        )

    def test_camera_follows_player(self, game_env):
        game = game_env
        backend = game.backend
        scene = GameplayScene()
        game.push(scene)
        game.tick(dt=DT)
        cam_x_before = scene.camera._x

        # Move player right
        backend.inject_key("right", type="key_press")
        for _ in range(30):
            game.tick(dt=DT)
        backend.inject_key("right", type="key_release")
        game.tick(dt=DT)

        assert scene.camera._x != cam_x_before, "Camera didn't follow player"


class TestAABBCollision:
    """Unit tests for the AABB collision detection helper."""

    def test_overlapping_boxes(self):
        assert aabb_collides(0, 0, 10, 10, 5, 5, 10, 10)

    def test_non_overlapping_boxes(self):
        assert not aabb_collides(0, 0, 10, 10, 20, 20, 10, 10)

    def test_touching_edges_no_overlap(self):
        assert not aabb_collides(0, 0, 10, 10, 10, 0, 10, 10)

    def test_contained_box(self):
        assert aabb_collides(0, 0, 20, 20, 5, 5, 5, 5)

    def test_identical_boxes(self):
        assert aabb_collides(0, 0, 10, 10, 0, 0, 10, 10)

    def test_horizontal_gap(self):
        assert not aabb_collides(0, 0, 10, 10, 15, 0, 10, 10)

    def test_vertical_gap(self):
        assert not aabb_collides(0, 0, 10, 10, 0, 15, 10, 10)

    def test_partial_overlap_vertical(self):
        assert aabb_collides(0, 0, 10, 10, 0, 5, 10, 10)
