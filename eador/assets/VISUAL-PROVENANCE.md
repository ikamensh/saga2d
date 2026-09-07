# Shardbound presentation artwork

`images/shard-atmosphere.png` is an original environment painting generated
with Codex's built-in image-generation tool on 2026-09-06. No Eador artwork,
screenshots, external artist references or other input images were supplied.
The selected output is shipped unchanged. It is decorative; province positions,
terrain, ownership and tactical information are drawn separately by the game.

Generation prompt:

> Use case: stylized-concept. Asset type: production background painting for an original turn-based dark fantasy strategy game, Shardbound. Create a single wide 16:10 landscape painting, no text, no logos, no UI, no grids, no borders. Hand-painted gouache and fine oil-glaze storybook environment, restrained and sophisticated rather than cartoon. A broken world suspended above an abyss: distant floating land fragments, fir forests and an ancient small stone citadel on a crag in the far lower-left, faint waterfalls descending into blue-green fog, distant ragged peaks. Layout supports an existing game menu and hex board: large low-contrast dark negative space through the center, entire upper quarter, and entire right half. The only focal cluster of land/castle is around the leftmost quarter and lower-middle; very distant details, not giant foreground props. Color palette ink navy, deep teal, muted moss, cold slate, with a restrained touch of old gold dawn lighting from upper left. Painterly brush textures and volumetric layered mist give depth. Atmospheric, quiet, mysterious and believable, no bright sun or moon, no stars, no glowing neon, no characters, no generic ornate UI. The painting will sit behind cream/gold typography and a tactical board, so keep overall value dark and contrast restrained. Highest quality actual environment artwork, not a screenshot or UI mockup.

The terrain atlas is generated from original game-owned drawing code in
`eador/landscape.py`, through `tools/build_eador_art.py`; its manifest records
the source and output hashes. No image generation or synthesis runs during play.
Unit silhouettes, castles, relics and all tactical overlays remain original
code-native art in `eador/art.py` and the battle presentation modules.
