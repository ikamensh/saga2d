# Shardbound presentation pass

Visuals and sound are the current priority. The pending adventure-route work
is preserved separately; this pass changes presentation rather than world
generation or campaign rules.

## Art direction

The game now uses an original painted atmosphere behind its ink-and-brass
interface, with a quieter overlay during play. The title gives the painting
room and puts hero/world/difficulty controls on a measured dark panel.

Forty-eight prebuilt terrain illustrations cover six materials, four variants
and two scales of detail. Province tiles have overlapping tree masses, fields,
terraced hills, pools and mountains. Battlefield tiles leave their centers
and health-label areas open, with half-strength pigment variation so texture
does not compete with units. Castles and miniatures gain consistent lighting,
shaded cloth and metal, and shallow tabletop bases.

The hex grid still owns picking. Artwork occupies a fixed canvas around each
existing hex; ownership, selection, movement, site, seal and exit markers are
separate overlays. Encounter briefings use the same terrain textures as the
actual battlefield.

## Sound and action feedback

The two original music loops now use bowed voices, lute figures, breathed flute,
skin drums and stereo room reflections. Fourteen effects distinguish wood,
metal, footsteps, magic, bow release and heavy contact. The
[49-second sampler](evidence/shardbound-cue-sampler.wav) contains every cue,
then campaign music at 15.71 seconds and battle music at 32.46 seconds.

Player orders produce brief projectiles, blade arcs, impacts, healing marks,
Smoke blooms and Swap/Repulse rings. They use detached facts from the same
resolved command, remain nonmodal, and do not delay another order or save.
Enemy playback uses the same drawing, with approach motion and contact sounds
timed to its visible state change. Reduced motion keeps stationary feedback.
Damage and recovery labels fit within their hex; a fresh change replaces an
older number at the same position. Ground rings remain beneath miniatures and
persistent health labels.

The [audio catalogue](eador-audio.md) records musical choices, provenance and
technical checks. Audible artistic review is still needed; silent native
playback and sample checks cannot establish whether music is enjoyable over a
long play session.

## Framework and cost

Saga2D's existing image cache, drawing layers, scene input, audio manager and
synthesis primitives support this pass. The game owns the compositions,
artwork, asset builds, effect meanings and their placement. No framework
interface was added.

Both asset builders default to the existing 25% CPU allowance. Nothing is
generated while playing. The normal 60 FPS active / 15 FPS inactive cap remains;
native verification uses 30 FPS and cooperative 25% CPU pacing. The audio
build measured 9.46 seconds wall time and 2.35 seconds CPU. This is a build
measurement, not a runtime battery measurement.

## Verification

Run the compact visual journeys with:

```bash
uv run python tools/verify_eador_presentation.py --output /tmp/shardbound-presentation
uv run python tools/verify_eador_effects.py --output /tmp/shardbound-effects
```

The static journey opens all three worlds through native controls, checks
100% and 125% reading sizes, and checks four exact save/load round trips.
The effect journey uses a fresh Wizard home battle and a legally prepared
Observatory army, records the actual orders, and checks that every observed
frame leaves resolved campaign state unchanged. It is a presentation check,
not an independent first run or a campaign-depth demonstration.

The focused checks cover audio export/decoding and loop seams, deterministic
terrain builds, exact packaging inputs, title/theme/settings controls, battle
feedback, read-only playback and persistence. Final screenshots and receipts
are retained in the [presentation evidence](evidence/presentation-pass/README.md).

The Early Access gates remain open. Further visual work should deepen the
larger hero/troop artwork and test
readability across longer, crowded battles. Human listening and playtest
feedback remain part of assessing the game's presentation quality.
