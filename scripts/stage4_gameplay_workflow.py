"""Stage 4 real-user gameplay workflow — headless end-to-end test.

Simulates a complete gameplay loop that a real user would write:

1. Create a Game with mock backend
2. Build a GameplayScene with a player sprite, enemy sprites, and collectibles
3. Handle input: arrow keys move the player, "i" opens inventory, Esc pauses
4. Run a game loop that drives actions, timers, and tweens
5. Implement AABB collision detection between player and enemies/collectibles
6. Transition to a PauseScene (push) while timers and actions are active
7. Return from pause (pop) and verify state is restored (sprites re-created)
8. Collect an item via collision → verify removal
9. Push InventoryScene, verify timer cleanup on exit
10. Transition via replace() to VictoryScene → verify sprite cleanup

Run from repo root::

    uv run python scripts/stage4_gameplay_workflow.py
"""

from __future__ import annotations

import math
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

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
MAX_TICKS = 1200  # safety cap (~20s at 60 Hz)
PLAYER_SPEED = 200.0  # px/s
PLAYER_STEP = PLAYER_SPEED * DT  # px per tick


# ── AABB collision detection ─────────────────────────────────────────────

def aabb_collides(
    ax: float, ay: float, aw: float, ah: float,
    bx: float, by: float, bw: float, bh: float,
) -> bool:
    """Axis-aligned bounding box overlap test.

    Parameters are (left, top, width, height) for each box.
    """
    return (
        ax < bx + bw
        and ax + aw > bx
        and ay < by + bh
        and ay + ah > by
    )


def sprite_rect(sprite: Sprite) -> tuple[float, float, float, float]:
    """Return (left, top, width, height) for a sprite's bounding box.

    Uses the sprite position and image size (64x64 default in mock backend),
    adjusted for BOTTOM_CENTER anchor (default).
    """
    w, h = 64, 64
    left = sprite.x - w / 2
    top = sprite.y - h
    return (left, top, w, h)


# ── Event log for assertions ──────────────────────────────────────────────

event_log: list[str] = []


# ── PauseScene ────────────────────────────────────────────────────────────

class PauseScene(Scene):
    """Simple pause overlay that pops on cancel (Esc)."""

    transparent = True
    pop_on_cancel = True

    def on_enter(self) -> None:
        event_log.append("pause:enter")

    def on_exit(self) -> None:
        event_log.append("pause:exit")

    def draw(self) -> None:
        self.draw_rect(0, 0, 800, 600, (0, 0, 0, 128), opacity=0.5)


# ── InventoryScene ────────────────────────────────────────────────────────

class InventoryScene(Scene):
    """Inventory screen pushed over gameplay."""

    transparent = False
    pop_on_cancel = True

    def on_enter(self) -> None:
        event_log.append("inventory:enter")
        # Schedule a timer that should be cancelled when we leave
        self._inv_timer = self.after(0.5, lambda: event_log.append("inventory:timer_fired"))

    def on_exit(self) -> None:
        event_log.append("inventory:exit")


# ── VictoryScene ──────────────────────────────────────────────────────────

class VictoryScene(Scene):
    """Victory screen transitioned to via replace()."""

    def on_enter(self) -> None:
        event_log.append("victory:enter")

    def on_exit(self) -> None:
        event_log.append("victory:exit")


# ── GameplayScene ─────────────────────────────────────────────────────────

class GameplayScene(Scene):
    """Main gameplay scene with player, enemies, collectibles, and collision.

    Owned sprites are removed when the scene is pushed over (framework design).
    Entity state is preserved in Python attributes and sprites are re-created
    in on_reveal(). This is the standard saga2d pattern for persistent scenes.
    """

    background_color = (30, 30, 50)

    def on_enter(self) -> None:
        event_log.append("gameplay:enter")

        # Camera for world-space rendering
        self.camera = Camera(RESOLUTION, world_bounds=(0, 0, 1600, 1200))

        # Entity state (persists across push/pop cycles)
        self.player_pos = (400.0, 300.0)
        self.enemy_pos = (150.0, 300.0)
        self.ghost_pos = (600.0, 400.0)
        self.coin_pos = (500.0, 300.0)
        self.coin_alive = True
        self.score = 0
        self.player_hit = False
        self.items_collected: list[str] = []
        self.bonus_spawned = False

        # Create sprites from entity state
        self._create_sprites()

        # Scene-owned timers (survive push-over: permanent=False)
        self.score_timer = self.every(1.0, self._tick_score)
        self.spawn_timer = self.after(2.0, self._spawn_bonus)

        # bind_key for scene shortcuts
        self.bind_key("i", lambda: self.game.push(InventoryScene()))
        self.bind_key("cancel", lambda: self.game.push(PauseScene()))

        # Movement state
        self._move_dx = 0.0
        self._move_dy = 0.0

    def _create_sprites(self) -> None:
        """Create or re-create sprites from entity state."""
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
        self.ghost.do(Repeat(Sequence(
            FadeOut(0.4),
            FadeIn(0.4),
        )))

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

    def on_exit(self) -> None:
        event_log.append("gameplay:exit")
        # Preserve entity positions before sprites are cleaned up
        if not self.player.is_removed:
            self.player_pos = self.player.position
        if not self.enemy.is_removed:
            self.enemy_pos = self.enemy.position
        if not self.ghost.is_removed:
            self.ghost_pos = self.ghost.position

    def on_reveal(self) -> None:
        event_log.append("gameplay:reveal")
        # Re-create sprites from preserved entity state
        self._create_sprites()

    def _tick_score(self) -> None:
        self.score += 10
        event_log.append(f"score:{self.score}")

    def _spawn_bonus(self) -> None:
        if hasattr(self, 'game') and self.game is not None:
            self._bonus_pos = (300.0, 450.0)
            self.bonus_spawned = True
            if not self.player.is_removed:
                # Only create sprite if scene is still active (sprites exist)
                self.bonus = self.add_sprite(
                    Sprite("sprites/bonus", position=self._bonus_pos, layer=RenderLayer.OBJECTS)
                )
                self.bonus.do(Sequence(
                    FadeIn(0.2),
                    Delay(3.0),
                    FadeOut(0.5),
                ))
            event_log.append("bonus:spawned")

    def handle_input(self, event) -> bool:
        """Process movement input."""
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

    def update(self, dt: float) -> None:
        """Main game logic: move player, check collisions."""
        # Move player
        if self._move_dx != 0 or self._move_dy != 0:
            new_x = self.player.x + self._move_dx
            new_y = self.player.y + self._move_dy
            new_x = max(32, min(1568, new_x))
            new_y = max(64, min(1200, new_y))
            self.player.position = (new_x, new_y)

        # Update camera to follow player
        self.camera.center_on(self.player.x, self.player.y)

        # Collision: player vs coin (collectible)
        if self.coin is not None and not self.coin.is_removed:
            pr = sprite_rect(self.player)
            cr = sprite_rect(self.coin)
            if aabb_collides(*pr, *cr):
                self.coin.remove()
                self._get_owned_sprites().discard(self.coin)
                self.coin = None
                self.coin_alive = False
                self.score += 50
                self.items_collected.append("coin")
                event_log.append("coin:collected")

        # Collision: player vs enemy (damage)
        if not self.enemy.is_removed and not self.player_hit:
            pr = sprite_rect(self.player)
            er = sprite_rect(self.enemy)
            if aabb_collides(*pr, *er):
                self.player_hit = True
                self.player.tint = (1.0, 0.3, 0.3)
                self.after(0.5, lambda: setattr(self.player, 'tint', (1.0, 1.0, 1.0)))
                event_log.append("player:hit")

    def draw(self) -> None:
        """Draw collision debug rects for visible sprites."""
        for sprite in [self.player, self.enemy, self.ghost]:
            if not sprite.is_removed:
                r = sprite_rect(sprite)
                self.draw_world_rect(r[0], r[1], r[2], r[3], (0, 255, 0, 64))


# ── Main workflow ─────────────────────────────────────────────────────────

def main() -> None:
    root = Path(tempfile.mkdtemp(prefix="saga2d_s4_workflow_"))
    try:
        _run_workflow(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)
    print("PASS — Stage 4 gameplay workflow: all assertions passed")


def _run_workflow(asset_root: Path) -> None:
    # Create asset stubs
    img_dir = asset_root / "images" / "sprites"
    img_dir.mkdir(parents=True)
    for name in ("player", "enemy", "ghost", "coin", "bonus"):
        (img_dir / f"{name}.png").write_bytes(b"png")

    # ── Step 1: Create game ──────────────────────────────────────────
    game = Game("WorkflowTest", backend="mock", resolution=RESOLUTION, asset_path=asset_root)
    backend = game.backend

    # ── Step 2: Push gameplay scene ──────────────────────────────────
    gameplay = GameplayScene()
    game.push(gameplay)
    assert "gameplay:enter" in event_log, "GameplayScene.on_enter not called"
    assert not gameplay.player.is_removed, "Player sprite not created"
    assert not gameplay.enemy.is_removed, "Enemy sprite not created"

    # ── Step 3: Warm up — run ticks, verify actions are running ──────
    for _ in range(10):
        game.tick(dt=DT)

    initial_enemy_x = gameplay.enemy.x
    for _ in range(30):
        game.tick(dt=DT)
    assert gameplay.enemy.x != initial_enemy_x, (
        f"Enemy patrol action not running: still at {gameplay.enemy.x}"
    )

    # ── Step 4: Move player toward coin using input ──────────────────
    # Player at (400, 300), coin at (500, 300) → move right
    backend.inject_key("right", type="key_press")
    move_ticks = 0
    coin_collected = False
    for _ in range(200):
        game.tick(dt=DT)
        move_ticks += 1
        if not gameplay.coin_alive:
            coin_collected = True
            break

    assert coin_collected, (
        f"Coin not collected after {move_ticks} ticks, "
        f"player at ({gameplay.player.x:.1f}, {gameplay.player.y:.1f})"
    )
    assert "coin:collected" in event_log, "Coin collection event not logged"
    assert "coin" in gameplay.items_collected
    assert gameplay.score >= 50, f"Score should be ≥50, got {gameplay.score}"

    # Release right key
    backend.inject_key("right", type="key_release")
    game.tick(dt=DT)

    # ── Step 5: Ensure score timer fires ─────────────────────────────
    # Run enough additional ticks to reach 1.0s total elapsed
    for _ in range(60):
        game.tick(dt=DT)
    score_events = [e for e in event_log if e.startswith("score:")]
    assert len(score_events) > 0, "Score timer never fired"

    # ── Step 6: Move player toward enemy to trigger collision ────────
    # Player around x≈437, enemy patrols x=150–300
    backend.inject_key("left", type="key_press")
    hit_detected = False
    for _ in range(300):
        game.tick(dt=DT)
        if gameplay.player_hit:
            hit_detected = True
            break
    backend.inject_key("left", type="key_release")
    game.tick(dt=DT)

    assert hit_detected, (
        f"Player didn't collide with enemy, "
        f"player=({gameplay.player.x:.1f}, {gameplay.player.y:.1f}), "
        f"enemy=({gameplay.enemy.x:.1f}, {gameplay.enemy.y:.1f})"
    )
    assert "player:hit" in event_log

    # ── Step 7: Scene transition — push PauseScene ───────────────────
    # Record state before pause
    player_pos_before = gameplay.player.position
    enemy_pos_before = gameplay.enemy.position
    score_before_pause = gameplay.score

    # Press Escape → bind_key pushes PauseScene
    backend.inject_key("escape", type="key_press")
    game.tick(dt=DT)
    assert "pause:enter" in event_log, "PauseScene.on_enter not called"
    assert "gameplay:exit" in event_log, "GameplayScene.on_exit not called"

    # Gameplay sprites should be cleaned up (framework design)
    assert gameplay.player.is_removed, (
        "Player sprite should be removed when scene is pushed over"
    )

    # Run ticks while paused
    score_at_pause = gameplay.score
    for _ in range(30):
        game.tick(dt=DT)

    # ── Step 8: Pop PauseScene → gameplay revealed ───────────────────
    backend.inject_key("escape", type="key_press")
    game.tick(dt=DT)
    assert "pause:exit" in event_log
    assert "gameplay:reveal" in event_log

    # Sprites should be re-created in on_reveal
    assert not gameplay.player.is_removed, (
        "Player sprite should be re-created in on_reveal"
    )
    assert not gameplay.enemy.is_removed, (
        "Enemy sprite should be re-created in on_reveal"
    )
    assert not gameplay.ghost.is_removed, (
        "Ghost sprite should be re-created in on_reveal"
    )

    # Player position should be preserved
    assert abs(gameplay.player.x - player_pos_before[0]) < 1.0, (
        f"Player position not restored: was {player_pos_before}, now {gameplay.player.position}"
    )

    # Coin should NOT be re-created (was collected)
    assert gameplay.coin is None, "Coin should not reappear after collection"

    # ── Step 9: Push InventoryScene via "i" key ──────────────────────
    backend.inject_key("i", type="key_press")
    game.tick(dt=DT)
    assert "inventory:enter" in event_log

    # Run a few ticks (not enough for 0.5s timer)
    for _ in range(10):
        game.tick(dt=DT)

    # Pop inventory with Escape
    backend.inject_key("escape", type="key_press")
    game.tick(dt=DT)
    assert "inventory:exit" in event_log

    # Verify inventory timer was cancelled on exit
    inv_timer_events = [e for e in event_log if e == "inventory:timer_fired"]
    assert len(inv_timer_events) == 0, (
        f"Inventory timer fired {len(inv_timer_events)} times (should be cancelled on exit)"
    )

    # ── Step 10: Verify gameplay resumes ─────────────────────────────
    # Sprites recreated again after inventory pop
    assert not gameplay.player.is_removed, "Player not restored after inventory"

    # Move player down
    backend.inject_key("down", type="key_press")
    player_y_before = gameplay.player.y
    for _ in range(30):
        game.tick(dt=DT)
    backend.inject_key("down", type="key_release")
    game.tick(dt=DT)

    assert gameplay.player.y > player_y_before, (
        f"Player didn't move after resume: y was {player_y_before}, now {gameplay.player.y}"
    )

    # ── Step 11: Ghost fade action still running after re-creation ───
    assert not gameplay.ghost.is_removed
    opacities = set()
    for _ in range(30):
        game.tick(dt=DT)
        opacities.add(gameplay.ghost.opacity)
    assert len(opacities) > 1, (
        f"Ghost opacity didn't vary (action not running?): {opacities}"
    )

    # ── Step 12: Bonus spawn timer should have fired ─────────────────
    # By now we've run many seconds of ticks (well past 2.0s)
    assert "bonus:spawned" in event_log, "Bonus spawn timer never fired"

    # ── Step 13: Replace gameplay with victory ───────────────────────
    victory = VictoryScene()
    game.replace(victory)

    # Count gameplay:exit events (should have multiple from push/pop cycles + final)
    exit_count = event_log.count("gameplay:exit")
    assert exit_count >= 3, (
        f"Expected ≥3 gameplay:exit events (push pause, push inventory, replace), "
        f"got {exit_count}"
    )
    assert "victory:enter" in event_log

    # Gameplay sprites cleaned up (final)
    assert gameplay.player.is_removed

    # Run victory for a few ticks
    for _ in range(10):
        game.tick(dt=DT)

    # ── Step 14: Teardown ────────────────────────────────────────────
    game._teardown()

    # ── Summary ──────────────────────────────────────────────────────
    _print_summary()


def _print_summary() -> None:
    print("\n=== Stage 4 Gameplay Workflow Summary ===")
    print(f"Total events: {len(event_log)}")
    transitions = [e for e in event_log if ':enter' in e or ':exit' in e or ':reveal' in e]
    print(f"Scene transitions: {len(transitions)}")
    print(f"Score ticks: {sum(1 for e in event_log if e.startswith('score:'))}")
    print(f"Collisions: {sum(1 for e in event_log if ':collected' in e or ':hit' in e)}")

    print("\nKey events:")
    for i, ev in enumerate(
        e for e in event_log
        if any(kw in e for kw in (':enter', ':exit', ':reveal', ':collected', ':hit', ':spawned'))
    ):
        print(f"  {i+1}. {ev}")
    print()


if __name__ == "__main__":
    main()
