# Goal: Add Visual Juice to Battle Demo

## Context

The battle demo (`examples/battle_vignette/battle_demo.py`) is a functional 4v4 tactical battle game. It has units, movement, attacks, AI, and win/lose conditions. But it feels flat — attacks have no weight, there's no feedback beyond floating numbers, and transitions are abrupt.

## Objective

Add visual juice effects that make the battle feel impactful and alive. These are all visual-only changes in the example code — do NOT modify the saga2d/ framework.

## Requirements

### 1. Particle Burst on Hit
When a unit takes damage, spawn a burst of particles at the impact point.
- Use saga2d's ParticleEmitter (imported from saga2d)
- White/yellow sparks for warriors, green/purple for skeleton hits
- 8-15 particles, short lifetime (0.3-0.5s), spreading outward
- Add this in `battle_unit.py` `take_damage()` method

### 2. Screen Flash on Critical Hits
When damage exceeds 20, briefly flash the screen white (or red for player hits).
- Draw a full-screen semi-transparent rect that fades out over 0.2s
- Use the scene's draw_rect in the draw() method with a fading alpha

### 3. Unit Death Effect
When a unit dies, in addition to the current fade-out:
- Spawn a larger particle burst (20-30 particles)
- Briefly make the screen flash darker
- The particle colors should match the unit's team (blue for warriors, red for skeletons)

### 4. Turn Transition Animation
When switching between player turn and AI turn:
- Animate the turn label text with a scale-in or slide effect
- Add a brief 0.3s dimming of the screen during transition
- This gives visual separation between turns

### 5. Idle Animation Bounce
Make idle units bob up and down very slightly (2-3 pixels) on a slow sine wave.
- Use the tween system to oscillate sprite y position
- Different phase per unit so they don't all sync
- Subtle enough to feel alive without being distracting

### 6. Attack Anticipation
Before the attack animation plays, add a brief "pull back" — the unit moves 10px away from the target, pauses 0.1s, then rushes in.
- Modify the attack choreography in `battle_unit.py` `get_attack_action()`
- Adds "weight" to the attack windup

## Technical Constraints

- Do NOT modify saga2d/ framework code
- All changes in examples/battle_vignette/ only
- All existing tests must pass: `uv run python -m pytest tests/ -v`
- The demo must still import and run correctly

## Acceptance Criteria

1. `uv run python -m pytest tests/ -v` passes
2. `python -c "from examples.battle_vignette.battle_demo import BattleScene; print('OK')"` works
3. ParticleEmitter is used for hit effects in take_damage()
4. Attack choreography includes the pull-back anticipation
5. Idle units have a subtle bobbing motion
