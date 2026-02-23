"""Tactical battle vignette — validates Stage 0–5 framework primitives.

Run from the project root::

    python examples/battle_vignette/battle_demo.py

Controls — Title Screen:
    Enter                       → start battle
    Escape                      → quit

Controls — Battle:
    Left-click a blue warrior   → select it
    Left-click a red skeleton   → attack with selected warrior
    Escape                      → return to title screen

The demo places 3 warriors (left) vs 3 skeletons (right) on a 1920×1080
screen.  Selecting a warrior shows a golden ring beneath it.  Clicking an
enemy triggers a 6-phase attack choreography:

    1. Warrior walks toward skeleton (move_to + walk anim)
    2. Warrior plays attack animation
    3. Short delay (0.3 s)
    4. Skeleton plays hit reaction
    5. If HP <= 0 → death anim + fade-out + remove
    6. Warrior walks home and plays idle
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

# Ensure the project root is on sys.path so ``import easygame`` works
# when invoked as ``python examples/battle_vignette/battle_demo.py``.
_project_root = Path(__file__).resolve().parents[2]
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from easygame import (
    AnimationDef,
    AssetManager,
    Ease,
    Game,
    InputEvent,
    RenderLayer,
    Scene,
    Sprite,
    SpriteAnchor,
    tween,
)


# ======================================================================
# Animation definitions (reusable templates, no handles yet)
# ======================================================================

WARRIOR_IDLE = AnimationDef(
    frames=["sprites/warrior_idle_01"],
    frame_duration=1.0,
    loop=True,
)
WARRIOR_WALK = AnimationDef(
    frames="sprites/warrior_walk",
    frame_duration=0.12,
    loop=True,
)
WARRIOR_ATTACK = AnimationDef(
    frames="sprites/warrior_attack",
    frame_duration=0.1,
    loop=False,
)

SKELETON_IDLE = AnimationDef(
    frames=["sprites/skeleton_idle_01"],
    frame_duration=1.0,
    loop=True,
)
SKELETON_WALK = AnimationDef(
    frames="sprites/skeleton_walk",
    frame_duration=0.12,
    loop=True,
)
SKELETON_HIT = AnimationDef(
    frames="sprites/skeleton_hit",
    frame_duration=0.1,
    loop=False,
)
SKELETON_DEATH = AnimationDef(
    frames="sprites/skeleton_death",
    frame_duration=0.2,
    loop=False,
)


# ======================================================================
# TitleScene
# ======================================================================

# Screen dimensions (must match Game resolution)
SCREEN_W, SCREEN_H = 1920, 1080


class TitleScene(Scene):
    """Animated title screen with decorative sprites.

    ENTER → push BattleScene, ESC → quit.
    """

    def on_enter(self) -> None:
        self._sprites: list[Sprite] = []
        self._bg_sprite_id: int | None = None
        self._tween_ids: list[int] = []

        self._create_background()
        self._create_decorative_sprites()

    # ------------------------------------------------------------------
    # Background — solid colour via backend API (no PNG file needed)
    # ------------------------------------------------------------------

    def _create_background(self) -> None:
        """Create a dark slate background spanning the full screen."""
        backend = self.game.backend
        bg_image = backend.create_solid_color_image(25, 25, 40, 255, SCREEN_W, SCREEN_H)
        self._bg_sprite_id = backend.create_sprite(
            bg_image,
            RenderLayer.BACKGROUND.value * 100_000,
        )
        backend.update_sprite(self._bg_sprite_id, 0, 0)

    # ------------------------------------------------------------------
    # Decorative animated sprites
    # ------------------------------------------------------------------

    def _create_decorative_sprites(self) -> None:
        """Place warriors and skeletons as title-screen decoration."""
        # Warrior patrol — two warriors walking in place on the left side
        for i, (x, base_y) in enumerate([(400, 600), (550, 750)]):
            warrior = Sprite(
                "sprites/warrior_idle_01",
                position=(x, base_y),
                layer=RenderLayer.UNITS,
                anchor=SpriteAnchor.BOTTOM_CENTER,
            )
            warrior.play(WARRIOR_WALK)
            self._sprites.append(warrior)

            # Gentle floating bob — tween y up and down in a cycle
            tid = tween(
                warrior, "y",
                float(base_y), float(base_y - 12),
                1.2 + i * 0.3,
                ease=Ease.EASE_IN_OUT,
                on_complete=lambda s=warrior, by=base_y, d=1.2 + i * 0.3: (
                    self._tween_ids.append(
                        tween(s, "y", float(by - 12), float(by), d,
                              ease=Ease.EASE_IN_OUT,
                              on_complete=lambda: self._bounce(s, by, d))
                    )
                ),
            )
            self._tween_ids.append(tid)

        # Skeleton sentries — two skeletons on the right side
        for i, (x, base_y) in enumerate([(1370, 600), (1520, 750)]):
            skeleton = Sprite(
                "sprites/skeleton_idle_01",
                position=(x, base_y),
                layer=RenderLayer.UNITS,
                anchor=SpriteAnchor.BOTTOM_CENTER,
            )
            skeleton.play(SKELETON_WALK)
            self._sprites.append(skeleton)

            # Opacity pulse — gentle fade in and out
            tid = tween(
                skeleton, "opacity",
                255.0, 160.0,
                1.5 + i * 0.4,
                ease=Ease.EASE_IN_OUT,
                on_complete=lambda s=skeleton, d=1.5 + i * 0.4: (
                    self._tween_ids.append(
                        tween(s, "opacity", 160.0, 255.0, d,
                              ease=Ease.EASE_IN_OUT,
                              on_complete=lambda: self._pulse(s, d))
                    )
                ),
            )
            self._tween_ids.append(tid)

    def _bounce(self, sprite: Sprite, base_y: float, duration: float) -> None:
        """Continue the up-down bob cycle."""
        tid = tween(
            sprite, "y",
            float(base_y), float(base_y - 12),
            duration,
            ease=Ease.EASE_IN_OUT,
            on_complete=lambda: (
                self._tween_ids.append(
                    tween(sprite, "y", float(base_y - 12), float(base_y),
                          duration, ease=Ease.EASE_IN_OUT,
                          on_complete=lambda: self._bounce(sprite, base_y, duration))
                )
            ),
        )
        self._tween_ids.append(tid)

    def _pulse(self, sprite: Sprite, duration: float) -> None:
        """Continue the opacity pulse cycle."""
        tid = tween(
            sprite, "opacity",
            255.0, 160.0,
            duration,
            ease=Ease.EASE_IN_OUT,
            on_complete=lambda: (
                self._tween_ids.append(
                    tween(sprite, "opacity", 160.0, 255.0, duration,
                          ease=Ease.EASE_IN_OUT,
                          on_complete=lambda: self._pulse(sprite, duration))
                )
            ),
        )
        self._tween_ids.append(tid)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_input(self, event: InputEvent) -> bool:
        if event.action == "confirm":
            self.game.push(BattleScene())
            return True

        if event.action == "cancel":
            self.game.quit()
            return True

        return False

    # ------------------------------------------------------------------
    # Draw — text rendered via backend each frame
    # ------------------------------------------------------------------

    def draw(self) -> None:
        backend = self.game.backend

        # Title — centred near the top
        backend.draw_text(
            "BATTLE VIGNETTE",
            SCREEN_W // 2, 180,
            64,
            (255, 220, 80, 255),
            font="Arial",
            anchor_x="center",
            anchor_y="baseline",
        )

        # Instructions — centred below title
        backend.draw_text(
            "Press ENTER to start",
            SCREEN_W // 2, 320,
            28,
            (200, 200, 200, 255),
            font="Arial",
            anchor_x="center",
            anchor_y="baseline",
        )
        backend.draw_text(
            "Press ESC to quit",
            SCREEN_W // 2, 380,
            28,
            (160, 160, 160, 255),
            font="Arial",
            anchor_x="center",
            anchor_y="baseline",
        )

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def on_exit(self) -> None:
        """Remove all decorative sprites and cancel tweens."""
        for sprite in self._sprites:
            sprite.remove()
        self._sprites.clear()

        for tid in self._tween_ids:
            self.game.cancel_tween(tid)
        self._tween_ids.clear()

        if self._bg_sprite_id is not None:
            self.game.backend.remove_sprite(self._bg_sprite_id)
            self._bg_sprite_id = None


# ======================================================================
# Unit data holder
# ======================================================================

class Unit:
    """Simple data holder for a battlefield unit."""

    def __init__(
        self,
        sprite: Sprite,
        team: str,
        home_pos: tuple[float, float],
        hp: int = 100,
    ) -> None:
        self.sprite = sprite
        self.team = team
        self.home_pos = home_pos
        self.hp = hp
        self.alive = True


# ======================================================================
# Floating damage number
# ======================================================================

class _FloatingNumber:
    """A damage number that floats up and fades out.

    Tweened by the tween system (x, y, opacity are settable attributes).
    Drawn each frame by the scene's ``draw()`` via ``backend.draw_text()``.
    """

    def __init__(self, text: str, x: float, y: float) -> None:
        self.text = text
        self.x = x
        self.y = y
        self.opacity: float = 255.0
        self.alive = True


# ======================================================================
# BattleScene
# ======================================================================

MOVE_SPEED = 400  # pixels / second
ATTACK_DAMAGE = 40

# Sprite sizes (all 64×64 as generated)
SPRITE_W, SPRITE_H = 64, 64
HIT_RADIUS = SPRITE_W // 2 + 8  # generous click radius


class BattleScene(Scene):
    """Single-screen tactical battle with ground plane and idle animations."""

    def on_enter(self) -> None:
        self.units: list[Unit] = []
        self.selected: Unit | None = None
        self.select_ring: Sprite | None = None
        self._ring_tween_ids: list[int] = []
        self.busy = False  # True while an attack sequence is playing
        self.floaters: list[_FloatingNumber] = []

        # Background sprite id (backend-level, not a Sprite object)
        self._bg_sprite_id: int | None = None
        # Per-unit idle-breathing tween ids: unit → list of active tween ids
        self._idle_tween_ids: dict[int, list[int]] = {}

        # Victory state
        self._victory: bool = False
        self._victory_opacity: float = 0.0  # tweened 0→255 on win
        self._victory_timer_id: int | None = None

        self._create_background()
        self._spawn_units()

    def on_exit(self) -> None:
        """Remove all unit sprites, tweens, background, and selection ring."""
        self._deselect()

        # Cancel victory timer if still pending (e.g. ESC during countdown)
        if self._victory_timer_id is not None:
            self.game.cancel(self._victory_timer_id)
            self._victory_timer_id = None

        # Cancel all idle-breathing tweens
        for tween_list in self._idle_tween_ids.values():
            for tid in tween_list:
                self.game.cancel_tween(tid)
        self._idle_tween_ids.clear()

        for unit in self.units:
            if unit.alive:
                unit.sprite.remove()
        self.units.clear()
        self.floaters.clear()

        # Remove background
        if self._bg_sprite_id is not None:
            self.game.backend.remove_sprite(self._bg_sprite_id)
            self._bg_sprite_id = None

    # ------------------------------------------------------------------
    # Background — earthy ground plane
    # ------------------------------------------------------------------

    def _create_background(self) -> None:
        """Create an earthy green-brown ground plane spanning the screen."""
        backend = self.game.backend
        bg_image = backend.create_solid_color_image(
            72, 85, 48, 255,  # muted olive-green (earthy field tone)
            SCREEN_W, SCREEN_H,
        )
        self._bg_sprite_id = backend.create_sprite(
            bg_image,
            RenderLayer.BACKGROUND.value * 100_000,
        )
        backend.update_sprite(self._bg_sprite_id, 0, 0)

    # ------------------------------------------------------------------
    # Spawning
    # ------------------------------------------------------------------

    def _spawn_units(self) -> None:
        """Place warriors on the left, skeletons on the right.

        Y positions are staggered so units lower on screen draw in front
        (demonstrating y-sort draw ordering).  X positions are offset
        slightly per row to avoid a rigid column look.
        """
        # Warriors (blue) — three rows, staggered x and y
        warrior_positions = [
            (340, 340),   # top row — renders behind
            (280, 510),   # middle row
            (340, 680),   # bottom row — renders in front
        ]
        for pos in warrior_positions:
            sprite = Sprite(
                "sprites/warrior_idle_01",
                position=pos,
                layer=RenderLayer.UNITS,
                anchor=SpriteAnchor.BOTTOM_CENTER,
            )
            unit = Unit(sprite, "friendly", pos)
            self.units.append(unit)
            self._start_idle_breathing(unit)

        # Skeletons (red) — mirrored stagger on the right
        skeleton_positions = [
            (1580, 340),  # top row — renders behind
            (1640, 510),  # middle row
            (1580, 680),  # bottom row — renders in front
        ]
        for pos in skeleton_positions:
            sprite = Sprite(
                "sprites/skeleton_idle_01",
                position=pos,
                layer=RenderLayer.UNITS,
                anchor=SpriteAnchor.BOTTOM_CENTER,
            )
            unit = Unit(sprite, "enemy", pos)
            self.units.append(unit)
            self._start_idle_breathing(unit)

    # ------------------------------------------------------------------
    # Idle breathing — subtle y-bob tween loop
    # ------------------------------------------------------------------

    def _start_idle_breathing(self, unit: Unit) -> None:
        """Start a gentle up-down bob on an idle unit's sprite."""
        uid = id(unit)
        # Cancel any existing breathing tweens for this unit
        self._stop_idle_breathing(unit)

        base_y = float(unit.home_pos[1])
        bob_amount = 4.0     # pixels — subtle
        duration = 1.4       # seconds per half-cycle

        tid = tween(
            unit.sprite, "y",
            base_y, base_y - bob_amount,
            duration,
            ease=Ease.EASE_IN_OUT,
            on_complete=lambda: self._idle_bob_down(unit, base_y, bob_amount, duration),
        )
        self._idle_tween_ids.setdefault(uid, []).append(tid)

    def _idle_bob_down(self, unit: Unit, base_y: float, amount: float, duration: float) -> None:
        """Second half of the bob — return to base_y."""
        if not unit.alive:
            return
        uid = id(unit)
        tid = tween(
            unit.sprite, "y",
            base_y - amount, base_y,
            duration,
            ease=Ease.EASE_IN_OUT,
            on_complete=lambda: self._idle_bob_up(unit, base_y, amount, duration),
        )
        self._idle_tween_ids.setdefault(uid, []).append(tid)

    def _idle_bob_up(self, unit: Unit, base_y: float, amount: float, duration: float) -> None:
        """First half of the bob — move up from base_y."""
        if not unit.alive:
            return
        uid = id(unit)
        tid = tween(
            unit.sprite, "y",
            base_y, base_y - amount,
            duration,
            ease=Ease.EASE_IN_OUT,
            on_complete=lambda: self._idle_bob_down(unit, base_y, amount, duration),
        )
        self._idle_tween_ids.setdefault(uid, []).append(tid)

    def _stop_idle_breathing(self, unit: Unit) -> None:
        """Cancel all idle-breathing tweens for a unit."""
        uid = id(unit)
        for tid in self._idle_tween_ids.pop(uid, []):
            self.game.cancel_tween(tid)

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_input(self, event: InputEvent) -> bool:
        if event.action == "cancel" and not self._victory:
            self.game.pop()  # return to title screen
            return True

        if self._victory:
            return True  # consume all input during victory

        if event.type == "click" and event.button == "left":
            self._handle_click(event.x, event.y)
            return True

        return False

    def _handle_click(self, mx: int, my: int) -> None:
        """Handle a left-click at logical coordinates (mx, my)."""
        if self.busy:
            return  # ignore clicks during attack sequence

        # Check if clicking on a unit
        clicked_unit = self._unit_at(mx, my)
        if clicked_unit is None:
            # Deselect
            self._deselect()
            return

        if clicked_unit.team == "friendly":
            self._select(clicked_unit)
        elif clicked_unit.team == "enemy" and self.selected is not None:
            self._begin_attack(self.selected, clicked_unit)

    def _unit_at(self, mx: int, my: int) -> Unit | None:
        """Return the unit closest to (mx, my) within HIT_RADIUS, or None."""
        for unit in self.units:
            if not unit.alive:
                continue
            ux, uy = unit.sprite.position
            if abs(mx - ux) < HIT_RADIUS and abs(my - uy) < HIT_RADIUS:
                return unit
        return None

    # ------------------------------------------------------------------
    # Selection — ring with pulsing opacity
    # ------------------------------------------------------------------

    def _select(self, unit: Unit) -> None:
        """Select a friendly unit, showing a pulsing golden ring."""
        self._deselect()
        self.selected = unit

        ux, uy = unit.sprite.position
        self.select_ring = Sprite(
            "sprites/select_ring",
            position=(ux, uy),
            layer=RenderLayer.UI_WORLD,
            anchor=SpriteAnchor.BOTTOM_CENTER,
        )
        self._start_ring_pulse()

    def _deselect(self) -> None:
        """Remove selection ring and cancel its pulse tweens."""
        self._stop_ring_pulse()
        if self.select_ring is not None:
            self.select_ring.remove()
            self.select_ring = None
        self.selected = None

    def _start_ring_pulse(self) -> None:
        """Start a looping opacity pulse on the selection ring."""
        if self.select_ring is None:
            return
        tid = tween(
            self.select_ring, "opacity",
            255.0, 120.0,
            0.6,
            ease=Ease.EASE_IN_OUT,
            on_complete=self._ring_pulse_up,
        )
        self._ring_tween_ids.append(tid)

    def _ring_pulse_up(self) -> None:
        """Pulse ring opacity back to full."""
        if self.select_ring is None:
            return
        tid = tween(
            self.select_ring, "opacity",
            120.0, 255.0,
            0.6,
            ease=Ease.EASE_IN_OUT,
            on_complete=self._ring_pulse_down,
        )
        self._ring_tween_ids.append(tid)

    def _ring_pulse_down(self) -> None:
        """Pulse ring opacity back down."""
        if self.select_ring is None:
            return
        tid = tween(
            self.select_ring, "opacity",
            255.0, 120.0,
            0.6,
            ease=Ease.EASE_IN_OUT,
            on_complete=self._ring_pulse_up,
        )
        self._ring_tween_ids.append(tid)

    def _stop_ring_pulse(self) -> None:
        """Cancel all ring-pulse tweens."""
        for tid in self._ring_tween_ids:
            self.game.cancel_tween(tid)
        self._ring_tween_ids.clear()

    # ------------------------------------------------------------------
    # Attack choreography (6 phases via callbacks)
    # ------------------------------------------------------------------

    def _begin_attack(self, attacker: Unit, defender: Unit) -> None:
        """Phase 1: Walk toward the enemy."""
        self.busy = True
        self._deselect()

        # Stop idle breathing on the attacker — it's entering combat
        self._stop_idle_breathing(attacker)

        # Stop near the defender (offset by sprite width so they don't overlap)
        dx, dy = defender.sprite.position
        target_x = dx - 80 if attacker.home_pos[0] < dx else dx + 80

        attacker.sprite.play(WARRIOR_WALK)
        attacker.sprite.move_to(
            (target_x, dy),
            speed=MOVE_SPEED,
            on_arrive=lambda: self._phase_attack_anim(attacker, defender),
        )

    def _phase_attack_anim(self, attacker: Unit, defender: Unit) -> None:
        """Phase 2: Play the attack animation."""
        attacker.sprite.play(
            WARRIOR_ATTACK,
            on_complete=lambda: self._phase_delay(attacker, defender),
        )

    def _phase_delay(self, attacker: Unit, defender: Unit) -> None:
        """Phase 3: Short pause before the hit lands."""
        self.game.after(
            0.3,
            lambda: self._phase_hit_reaction(attacker, defender),
        )

    def _phase_hit_reaction(self, attacker: Unit, defender: Unit) -> None:
        """Phase 4: Defender takes the hit."""
        if not defender.alive:
            self._phase_walk_home(attacker)
            return

        defender.hp -= ATTACK_DAMAGE
        self._spawn_damage_number(defender)

        # Stop defender's idle breathing during hit reaction
        self._stop_idle_breathing(defender)

        if defender.hp <= 0:
            # Defender dies
            defender.sprite.play(
                SKELETON_HIT,
                on_complete=lambda: self._phase_death(attacker, defender),
            )
        else:
            # Defender survives — play hit reaction, then attacker walks home
            defender.sprite.play(
                SKELETON_HIT,
                on_complete=lambda: self._phase_defender_recover(
                    attacker, defender,
                ),
            )

    def _phase_defender_recover(self, attacker: Unit, defender: Unit) -> None:
        """Defender recovers to idle, attacker walks home."""
        defender.sprite.play(SKELETON_IDLE)
        # Resume idle breathing for the surviving defender
        self._start_idle_breathing(defender)
        self._phase_walk_home(attacker)

    def _phase_death(self, attacker: Unit, defender: Unit) -> None:
        """Phase 5: Defender death animation + fade-out."""
        defender.alive = False

        defender.sprite.play(
            SKELETON_DEATH,
            on_complete=lambda: self._phase_fade_and_remove(
                attacker, defender,
            ),
        )

    def _phase_fade_and_remove(self, attacker: Unit, defender: Unit) -> None:
        """Fade out the dead defender, then remove it."""
        tween(
            defender.sprite, "opacity",
            255.0, 0.0, 0.5,
            ease=Ease.EASE_OUT,
            on_complete=lambda: self._phase_cleanup_dead(attacker, defender),
        )

    def _phase_cleanup_dead(self, attacker: Unit, defender: Unit) -> None:
        """Remove the dead defender's sprite and walk attacker home."""
        defender.sprite.remove()
        self._phase_walk_home(attacker)

    def _phase_walk_home(self, attacker: Unit) -> None:
        """Phase 6: Warrior walks back to starting position."""
        attacker.sprite.play(WARRIOR_WALK)
        attacker.sprite.move_to(
            attacker.home_pos,
            speed=MOVE_SPEED,
            on_arrive=lambda: self._phase_done(attacker),
        )

    def _phase_done(self, attacker: Unit) -> None:
        """Attack sequence complete — back to idle with breathing."""
        attacker.sprite.play(WARRIOR_IDLE)
        self._start_idle_breathing(attacker)
        self.busy = False

        # Check victory: all enemies dead?
        if not self._victory and not any(
            u.alive for u in self.units if u.team == "enemy"
        ):
            self._trigger_victory()

    # ------------------------------------------------------------------
    # Victory
    # ------------------------------------------------------------------

    def _trigger_victory(self) -> None:
        """All enemies dead — show VICTORY text and auto-pop after 3s."""
        self._victory = True
        self._victory_opacity = 0.0

        # Fade the text in over 1 second
        tween(
            self, "_victory_opacity",
            0.0, 255.0,
            1.0,
            ease=Ease.EASE_OUT,
        )

        # After 3 seconds, return to the title screen
        self._victory_timer_id = self.game.after(
            3.0,
            self._victory_pop,
        )

    def _victory_pop(self) -> None:
        """Timer callback — pop back to title after victory delay."""
        self._victory_timer_id = None
        self.game.pop()

    # ------------------------------------------------------------------
    # Floating damage numbers
    # ------------------------------------------------------------------

    def _spawn_damage_number(self, target: Unit) -> None:
        """Spawn a floating "-40" above the defender."""
        tx, ty = target.sprite.position
        floater = _FloatingNumber(
            text=f"-{ATTACK_DAMAGE}",
            x=tx,
            y=ty - SPRITE_H,
        )
        self.floaters.append(floater)

        # Float upward and fade out
        tween(floater, "y", floater.y, floater.y - 60, 0.8, ease=Ease.EASE_OUT)
        tween(
            floater, "opacity",
            255.0, 0.0, 0.8,
            ease=Ease.EASE_IN,
            on_complete=lambda: self._remove_floater(floater),
        )

    def _remove_floater(self, floater: _FloatingNumber) -> None:
        floater.alive = False

    # ------------------------------------------------------------------
    # Draw
    # ------------------------------------------------------------------

    def draw(self) -> None:
        """Draw floating damage numbers and victory text via the backend."""
        backend = self.game.backend

        for f in self.floaters:
            if not f.alive:
                continue
            alpha = max(0, min(255, int(f.opacity)))
            backend.draw_text(
                f.text,
                int(f.x),
                int(f.y),
                24,
                (255, 80, 80, alpha),
                font="Arial",
            )

        # Clean up dead floaters
        self.floaters = [f for f in self.floaters if f.alive]

        # Victory overlay
        if self._victory:
            alpha = max(0, min(255, int(self._victory_opacity)))
            backend.draw_text(
                "VICTORY",
                SCREEN_W // 2, SCREEN_H // 2 - 48,
                96,
                (255, 230, 60, alpha),
                font="Arial",
                anchor_x="center",
                anchor_y="baseline",
            )


# ======================================================================
# Main
# ======================================================================

def main() -> None:
    asset_path = Path(__file__).resolve().parent / "assets"

    game = Game(
        "Battle Vignette",
        resolution=(1920, 1080),
        fullscreen=False,
        backend="pyglet",
    )
    game.assets = AssetManager(
        game.backend,
        base_path=asset_path,
    )

    game.run(TitleScene())


if __name__ == "__main__":
    main()
