# Goal: Playable Tactical Battle Demo

## Context

The `examples/battle_vignette/` demo currently showcases attack animations on a static screen — click a unit, click an enemy, watch the attack play out. There's no game here, just a visual test. The Saga2D framework already provides all the building blocks: sprites with y-sort, composable actions, particle emitters, FSM, UI widgets, audio channels, and a camera. Time to wire them into an actual playable game.

## Objective

Transform the battle_vignette into a **complete turn-based tactical battle** — a 4v4 (warriors vs skeletons) combat on a grid, with movement, attacks, health bars, enemy AI, and a win/lose screen. Think the tactical combat layer of Heroes of Might and Magic 2 or Fire Emblem, but simplified to fit a demo.

## Architecture

Build the game logic as a new module inside `examples/battle_vignette/` (e.g. `battle_logic.py`, `battle_grid.py`, `battle_ai.py`). Do NOT modify the saga2d framework — layer game logic on top of it.

## Requirements

### 1. Grid System (`battle_grid.py`)
- Simple square grid, approximately 8x6 tiles
- Each cell can be: empty, occupied by a unit, or blocked (obstacle)
- Procedurally generated terrain: generate tile background sprites in `assetgen/` — grass base with a few stone/dirt variations for visual interest
- Grid renders as a tiled background beneath units
- Highlight cells: blue for valid moves, red for valid attacks, when a unit is selected

### 2. Unit System
- Unit class with: HP, attack power, defense, movement range (in cells), attack range
- Warriors: 120 HP, 25 atk, 10 def, 3 move, 1 range (melee)
- Skeletons: 80 HP, 20 atk, 5 def, 4 move, 2 range (can attack 2 cells away)
- Health bars floating above each unit (small colored bar, green→yellow→red)
- Units face the direction they last moved (flip sprite horizontally)

### 3. Turn System
- Alternating team turns (all warriors move, then all skeletons)
- Each unit gets ONE action per turn: move, attack, or move-then-attack
- Turn indicator UI at top of screen ("Your Turn" / "Enemy Turn")
- Click a friendly unit to select → show move range → click cell to move → show attack range → click enemy to attack (or click elsewhere to skip attack)
- "End Turn" button to pass remaining units
- After a unit acts, dim it slightly to show it's spent

### 4. Combat
- Damage = attacker.atk - defender.def (minimum 1)
- Use the existing attack choreography (walk toward, swing, damage number, walk back)
- When a unit dies, play death animation then remove from grid
- Particle burst on hit (use ParticleEmitter — white/yellow sparks)

### 5. Enemy AI (`battle_ai.py`)
- For each skeleton on its turn:
  - If an enemy is in attack range, attack the lowest-HP target
  - Otherwise, move toward the nearest enemy, then attack if now in range
  - Simple greedy pathfinding (BFS on grid) is sufficient
- Brief delay between AI actions so the player can follow what's happening

### 6. Win/Lose
- All skeletons dead → Victory screen (use saga2d MessageScreen or simple overlay)
- All warriors dead → Defeat screen
- Show battle summary: turns taken, damage dealt

### 7. Visual Polish
- Use the camera for slight zoom or centering on the grid
- Grid lines or subtle cell borders so the grid is visible but not distracting
- Existing procedural sprites from assetgen/ are used (warrior_idle, skeleton_idle, etc.)
- Background behind grid: simple dark gradient or tiled ground

### 8. Audio (if time allows — lowest priority)
- Framework audio system exists but no sound files — skip if it would block progress, OR generate simple beep/click sounds procedurally using numpy (sine waves saved as .wav)

## Technical Constraints
- Do NOT modify saga2d/ framework code — this is a demo that proves the framework works
- All battle logic lives in `examples/battle_vignette/`
- Asset generation additions go in `assetgen/` (new tile sprites, etc.)
- Must run from project root: `python -m examples.battle_vignette.battle_demo` (or similar)
- All existing tests must pass (`pytest tests/`)

## Acceptance Criteria

1. Launch the demo — see a grid with 4 warriors on the left, 4 skeletons on the right
2. Click a warrior → blue cells show valid moves, red cells show valid attacks
3. Move a warrior to a cell → unit walks there with animation
4. Attack a skeleton → full attack choreography plays, damage number appears, HP bar decreases
5. After all warriors act (or End Turn pressed), skeletons move and attack autonomously via AI
6. Kill all skeletons → victory screen appears
7. Lose all warriors → defeat screen appears
8. `pytest tests/` still passes (no framework regressions)
9. The game is actually playable and responds to clicks correctly — not just a scripted animation
