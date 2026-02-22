"""
Multi-step game sequence: Heroes 2-style battle attack turn.
Attacker walks forward, attacks, defender reacts, attacker walks back.
This is what you write TODAY with pygame — callback chains or state machines.
"""
import pygame
import math

pygame.init()
screen = pygame.display.set_mode((1024, 768))
clock = pygame.time.Clock()


# === You need the entire animation/movement system from sprite_animation_current.py ===
# (omitted here — assume AnimatedUnit class exists with play() and move_to())
# On top of that, you need to orchestrate a multi-step sequence.


# === Approach 1: Named callbacks (the common approach) ===

def execute_attack_turn(attacker, defender, on_complete):
    """
    Sequence: walk forward → attack anim → wait → defender hit → damage number →
    attacker walk back → idle.

    Each step is a named function that triggers the next.
    """
    original_x = attacker.x
    target_x = defender.x - 60

    def step1_walk():
        attacker.play(walk_frames, loop=True)
        attacker.move_to(target_x, attacker.y, on_arrive=step2_attack)

    def step2_attack():
        attacker.play(attack_frames, loop=False, on_complete=step3_wait)

    def step3_wait():
        schedule_after(0.3, step4_defender_hit)

    def step4_defender_hit():
        defender.play(hit_frames, loop=False, on_complete=step5_damage)

    def step5_damage():
        show_damage_number(defender.x, defender.y - 40, damage=25, on_done=step6_walk_back)

    def step6_walk_back():
        attacker.play(walk_frames, loop=True)
        attacker.move_to(original_x, attacker.y, on_arrive=step7_idle)

    def step7_idle():
        attacker.play(idle_frames, loop=True)
        on_complete()

    step1_walk()


# Readable, but:
# - Adding a step means renaming/renumbering everything below it
# - Reordering steps means rewiring all the callback references
# - No way to run two things in parallel (e.g. walk + animate simultaneously)
# - No way to cancel mid-sequence without adding a `cancelled` flag to every step
# - You need a separate schedule_after() timer system (not shown)
# - Each multi-step sequence is a pile of closures that reference each other


# === Approach 2: State machine (the "structured" way) ===

class AttackSequence:
    """State machine that advances through phases each frame."""
    def __init__(self, attacker, defender, on_complete):
        self.attacker = attacker
        self.defender = defender
        self.on_complete = on_complete
        self.phase = "walk_forward"
        self.timer = 0
        self.original_x = attacker.x
        self.target_x = defender.x - 60
        self.done = False

        # Start phase 1
        attacker.play(walk_frames, loop=True)
        attacker.move_to(self.target_x, attacker.y, on_arrive=self._arrived)
        self._arrived_flag = False
        self._anim_done_flag = False

    def _arrived(self):
        self._arrived_flag = True

    def _anim_done(self):
        self._anim_done_flag = True

    def update(self, dt):
        if self.done:
            return

        if self.phase == "walk_forward":
            if self._arrived_flag:
                self.phase = "attack"
                self._arrived_flag = False
                self.attacker.play(attack_frames, loop=False, on_complete=self._anim_done)
                self._anim_done_flag = False

        elif self.phase == "attack":
            if self._anim_done_flag:
                self.phase = "wait"
                self.timer = 0.3
                self._anim_done_flag = False

        elif self.phase == "wait":
            self.timer -= dt
            if self.timer <= 0:
                self.phase = "defender_hit"
                self.defender.play(hit_frames, loop=False, on_complete=self._anim_done)
                self._anim_done_flag = False

        elif self.phase == "defender_hit":
            if self._anim_done_flag:
                self.phase = "walk_back"
                self._arrived_flag = False
                self.attacker.play(walk_frames, loop=True)
                self.attacker.move_to(self.original_x, self.attacker.y,
                                      on_arrive=self._arrived)

        elif self.phase == "walk_back":
            if self._arrived_flag:
                self.phase = "idle"
                self.attacker.play(idle_frames, loop=True)
                self.done = True
                self.on_complete()


# Correct and cancellable (check self.done), but verbose:
# - ~55 lines for one sequence
# - Every phase needs flag management and phase transition boilerplate
# - Adding a step means a new elif block + new flag
# - "Parallel" (walk + animate at the same time) requires combining phases
# - A battle with 5 unit types × 3 attack types means many sequence classes
#
# The fundamental problem: neither approach lets you describe a sequence
# declaratively. You either chain callbacks (fragile to reorder) or write
# state machines (verbose). Both make "do A then B then C" harder than it
# should be.
