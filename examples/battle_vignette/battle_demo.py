"""Tactical battle vignette — validates Stage 0–5 framework primitives.

Run from the project root::

    python examples/battle_vignette/battle_demo.py

Controls:
    Left-click a blue warrior   → select it
    Left-click a red skeleton   → attack with selected warrior
    Escape                      → quit

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
    """Single-screen tactical battle."""

    def on_enter(self) -> None:
        self.units: list[Unit] = []
        self.selected: Unit | None = None
        self.select_ring: Sprite | None = None
        self.busy = False  # True while an attack sequence is playing
        self.floaters: list[_FloatingNumber] = []
        self._font: Any = None

        self._spawn_units()

    # ------------------------------------------------------------------
    # Spawning
    # ------------------------------------------------------------------

    def _spawn_units(self) -> None:
        """Place warriors on the left, skeletons on the right."""
        # Warriors (blue) — staggered y for y-sort variety
        warrior_positions = [
            (300, 350),
            (250, 500),
            (300, 650),
        ]
        for pos in warrior_positions:
            sprite = Sprite(
                "sprites/warrior_idle_01",
                position=pos,
                layer=RenderLayer.UNITS,
                anchor=SpriteAnchor.BOTTOM_CENTER,
            )
            self.units.append(Unit(sprite, "friendly", pos))

        # Skeletons (red)
        skeleton_positions = [
            (1620, 350),
            (1670, 500),
            (1620, 650),
        ]
        for pos in skeleton_positions:
            sprite = Sprite(
                "sprites/skeleton_idle_01",
                position=pos,
                layer=RenderLayer.UNITS,
                anchor=SpriteAnchor.BOTTOM_CENTER,
            )
            self.units.append(Unit(sprite, "enemy", pos))

    # ------------------------------------------------------------------
    # Input
    # ------------------------------------------------------------------

    def handle_input(self, event: InputEvent) -> bool:
        if event.action == "cancel":
            self.game.quit()
            return True

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
    # Selection
    # ------------------------------------------------------------------

    def _select(self, unit: Unit) -> None:
        """Select a friendly unit, showing the golden ring."""
        self._deselect()
        self.selected = unit

        ux, uy = unit.sprite.position
        self.select_ring = Sprite(
            "sprites/select_ring",
            position=(ux, uy),
            layer=RenderLayer.UI_WORLD,
            anchor=SpriteAnchor.BOTTOM_CENTER,
        )

    def _deselect(self) -> None:
        """Remove selection ring."""
        if self.select_ring is not None:
            self.select_ring.remove()
            self.select_ring = None
        self.selected = None

    # ------------------------------------------------------------------
    # Attack choreography (6 phases via callbacks)
    # ------------------------------------------------------------------

    def _begin_attack(self, attacker: Unit, defender: Unit) -> None:
        """Phase 1: Walk toward the enemy."""
        self.busy = True
        self._deselect()

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
        """Attack sequence complete — back to idle."""
        attacker.sprite.play(WARRIOR_IDLE)
        self.busy = False

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
        """Draw floating damage numbers via the backend text API."""
        if self._font is None:
            self._font = self.game.backend.load_font("Arial", 24)

        for f in self.floaters:
            if not f.alive:
                continue
            alpha = max(0, min(255, int(f.opacity)))
            self.game.backend.draw_text(
                f.text,
                self._font,
                int(f.x),
                int(f.y),
                (255, 80, 80, alpha),
            )

        # Clean up dead floaters
        self.floaters = [f for f in self.floaters if f.alive]


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

    game.run(BattleScene())


if __name__ == "__main__":
    main()
