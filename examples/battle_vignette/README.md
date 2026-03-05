# Battle Vignette Demo

A playable tactical battle game showcasing the Saga2D framework's capabilities:
- Turn-based grid combat with FSM-driven game flow
- Rich unit system with stats (HP, ATK, DEF, MOV, RNG)
- BFS pathfinding and Chebyshev attack range
- AI opponent with move/attack logic
- Procedurally generated terrain tiles
- Health bars, floating damage numbers, selection rings
- Actions-based animation choreography

## Generate Assets

From the project root:

```bash
python generate_assets.py
```

This generates:
- 20 battle sprites (warriors, skeletons, select ring)
- 8 tile assets (grass, dirt, stone, obstacle rock, move/attack overlays, health bars)

## Run

From the project root:

```bash
python examples/battle_vignette/battle_demo.py
```

## Controls

**Player Turn:**
- **Left-click** a warrior to select it
- **Left-click** a blue cell to move (or current cell to stay)
- **Left-click** a red cell to attack an enemy
- **Right-click** or **Escape** to cancel selection
- **E** or **End Turn button** to finish your turn

**Enemy Turn:**
- Watch as the AI moves and attacks with each skeleton

**Game Over:**
- **Enter** to restart
- **Escape** to quit

## Features

- **8×6 grid** with procedurally generated terrain (grass, stone, dirt)
- **3-5 random obstacles** (grey rocks) blocking movement and creating tactical chokepoints
- **4 warriors** (120 HP / 25 ATK / 10 DEF / 3 MOV / 1 RNG)
- **4 skeletons** (80 HP / 20 ATK / 5 DEF / 4 MOV / 2 RNG)
- **Movement highlights** (blue) show reachable cells
- **Attack highlights** (red) show valid targets
- **Health bars** above each unit (green → red when low)
- **Floating damage numbers** with tween animations
- **Victory/defeat** detection with game-over screen
