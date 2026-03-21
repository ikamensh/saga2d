# Goal: Procedural Sprite Art Pipeline — From Programmer Art to Polished

## Context

The `assetgen/` module generates 20 battle sprites (warriors + skeletons) procedurally using Pillow. Currently they look like programmer art — blue stick figures and red diamonds with googly eyes. The framework (Saga2D) targets games inspired by Heroes of Might and Magic 2, Disciples, and similar 90s strategy games.

## Objective

Overhaul `assetgen/battle_sprites.py` to produce **visually appealing 64x64 sprites** using purely procedural Python rendering. No external art files, no AI image generation APIs — just Pillow, numpy, and math.

The target aesthetic: **stylized pixel art with depth** — think clean shapes with proper shading, rim lighting, subtle glow effects, and considered color palettes. Not photorealistic, but something that looks intentionally designed rather than placeholder.

## Specific Requirements

### 1. Rendering Techniques (add to `assetgen/primitives.py` or new modules as needed)
- **Gradient shading**: Bodies should have light-to-dark gradients suggesting volume (top-lit)
- **Rim/edge lighting**: Subtle bright edge on one side to separate sprite from background
- **Anti-aliased drawing**: Use supersampling (render at 2-4x, downsample with bicubic) for smooth edges
- **Glow effects**: Weapons, gems, magical elements should have soft glow (gaussian blur on bright layer, composite)
- **Texture/noise overlays**: Subtle noise on surfaces for material feel (metal, cloth, bone)
- **Drop shadows**: Small soft shadow beneath each sprite for grounding

### 2. Warrior Sprites (8 frames)
- Recognizable humanoid silhouette with helmet, armor torso, sword, shield
- Blue/steel color scheme with proper metallic shading
- Shield gem should glow (not just wireframe octahedron)
- Sword blade should have a metallic gradient and slight glow on the edge
- Walk cycle should show natural weight shift
- Attack frames should show weapon arc with motion trail/blur

### 3. Skeleton Sprites (11 frames)
- Recognizable undead silhouette — skull, ribcage, bony limbs
- Bone-white with warm/cool color temperature variation
- Glowing red eyes (not just dots)
- Death animation should show crumbling/dissolving effect
- Overall spookier and more distinct from warrior

### 4. Selection Ring
- Pulsing glow effect (rendered as multiple opacity levels that the game can cycle through)
- More polished than a simple yellow ellipse

### 5. Technical Constraints
- All sprites remain 64x64 RGBA PNG
- `generate(output_dir)` API stays the same
- Pure Python + Pillow + numpy (add numpy to deps if needed, it's fine)
- Existing tests should still pass
- Generated files go to same locations as before
- Must run via `python generate_assets.py` from project root

## Acceptance Criteria

1. Run `python generate_assets.py` — produces all 20 sprites without errors
2. Open warrior_idle_01.png — recognizable armored humanoid with visible shading/depth, not a flat blob
3. Open skeleton_idle_01.png — recognizable skeleton with glowing eyes, not a red diamond
4. Warrior and skeleton are visually distinct at a glance (different silhouettes, not just color swaps)
5. At least 3 of these techniques are visibly present: gradient shading, rim lighting, glow effects, anti-aliasing, texture noise
6. All existing tests pass (`pytest tests/`)
7. The sprites look like they belong in a real indie game, not a debug visualization
