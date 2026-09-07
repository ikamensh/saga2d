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

Four original painted hero portraits appear with class selection and in the
Hero panel. The selected class controls both views; no portrait choice alters
the campaign. The game owns their small measured frame composition and the
asset paths, using Saga2D's existing `Image` and layout primitives. Complete
text-only generation prompts and exact output hashes are in the
[portrait provenance](../eador/assets/hero-portrait-provenance.json).

All fourteen troop miniatures and four heroes now have shaded cloth, metal and
leather, distinct headgear, faces and role equipment. The Wizard's silver hair,
book and staff, Scout's hood and bow, Warrior's braids and armor, and Commander's
ochre cloak match their portraits. Bows, pikes, tower shields, rune casting,
smoke equipment and eagle wings distinguish troop roles at battle and retinue
sizes. Every stroke scales with the miniature, within the existing cell bounds.

## Icons and readable values

The campaign toolbar uses pictograms for Guide, Hero, Codex, text size, Save
and Load. Settings and repeated text-size controls use the same symbols across
screens. Keyboard keycaps remain visible; hovering gives the full control name.
Save and Load explain the difference between browsing slots and the quicksave.

Gold, crystals, income, upkeep, level, experience, actions, health and mana use
icons beside their exact numeric values. Battle attack, defense, movement,
flight and range do the same. Hovering either the symbol or its value reveals
the meaning; tooltips follow the 100% or 125% reading preference across scenes.
The Hero panel also uses level, health and mana icons beside exact values.
Battle Auto-play, Retreat and Log use compact icons with A/T/L keycaps and
hover explanations. The footer shows the latest event; L opens its full history.
Order guidance spans the board, with an M reader for unusually long messages.
Its fixed height prevents the board shifting under a pointer after an order.
Together with a tighter header, this leaves more room for the miniatures.
Unavailable battle orders and spells explain the missing action, cooldown,
charge, learned spell, mana or legal target.

The 34 original geometric icons share the ink, brass and verdigris palette.
They are prebuilt transparent PNGs with distinct silhouettes at small sizes;
their [provenance](../eador/assets/VISUAL-PROVENANCE.md) and hash manifest ship
with the game. Primary actions, objectives, costs, order consumption and
consequences retain clear text.

## Sound and action feedback

The two original music loops now use bowed voices, lute figures, breathed flute,
skin drums and stereo room reflections. Sixteen effects distinguish wood,
metal, footsteps, magic, bow release, heavy contact and seal progress. The
[51-second sampler](evidence/shardbound-cue-sampler.wav) contains every cue,
then campaign music at 17.70 seconds and battle music at 34.45 seconds.

Player orders produce brief projectiles, blade arcs, impacts, healing marks,
Smoke blooms and Swap/Repulse rings. They use detached facts from the same
resolved command, remain nonmodal, and do not delay another order or save.
Enemy playback uses the same drawing, with approach motion and contact sounds
timed to its visible state change. Reduced motion keeps stationary feedback.
Damage and recovery labels fit within their hex; a fresh change replaces an
older number at the same position. Ground rings remain beneath miniatures and
persistent health labels.
Starting an enemy phase clears the preceding manual damage numbers, so they
cannot remain above an empty hex after a unit moves.

Gaining hold progress gives the seal a brief teal pulse and rising chime; losing
it gives a red pulse and falling resonance. The rings remain below the holder
and health label. Unchanged progress stays quiet; final victory keeps its own
result cue. Reduced motion keeps these rings stationary.

Manual attacks now play each recorded contact, including Brace and retaliation.
Arrows have a release followed by impact; Wizard, Rune Adept and Acolyte ranged
attacks share a blue arcane projectile and magic contact. A new accepted order
finishes pending contacts from the preceding attack, while leaving or loading
discards them. No sound queue delays an order or changes saved state. Manual
orders and turn playback share game-owned weapon classification and cue mapping.

The [audio catalogue](eador-audio.md) records musical choices, provenance and
technical checks. Audible artistic review is still needed; silent native
playback and sample checks cannot establish whether music is enjoyable over a
long play session.

## Framework and cost

Saga2D's image cache, drawing layers, scene input, audio manager and synthesis
primitives support the artwork and audio. The icon pass adds ordinary layout
images, optional button icons and shared reactive hover explanations through
[small reusable UI interfaces](framework-icon-controls.md). The game owns
compositions, artwork, icon meanings, asset builds and placement.

Asset builders default to the existing 25% CPU allowance. Nothing is
generated while playing. The normal 60 FPS active / 15 FPS inactive cap remains;
native verification uses 30 FPS and cooperative 25% CPU pacing. The audio
generator 3 build measured 13.39 seconds wall time and 3.34 seconds CPU. This is a build
measurement, not a runtime battery measurement.

## Verification

Run the compact visual journeys with:

```bash
uv run python tools/verify_eador_presentation.py --output /tmp/shardbound-presentation
uv run python tools/verify_eador_effects.py --output /tmp/shardbound-effects
uv run python tools/verify_eador_icons.py --output /tmp/shardbound-icons
uv run python tools/verify_eador_characters.py --output /tmp/shardbound-characters
uv run python tools/verify_eador_tactical_layout.py --output /tmp/shardbound-tactics
```

The static journey opens all three worlds through native controls, checks
100% and 125% reading sizes, and checks four exact save/load round trips.
The effect journey uses a fresh Wizard home battle and a legally prepared
Observatory army, records the actual orders, and checks that every observed
frame leaves resolved campaign state unchanged. It is a presentation check,
not an independent first run or a campaign-depth demonstration.

The icon journey starts a fresh Wizard shard, visits utilities by pointer and
keyboard, checks numeric readouts, applies larger reading size, tries disabled
orders, makes a legal Archer move/attack and compares two exact save/load
round trips. It captures ten native frames. The separate framework demo
exercises the same primitives without a Shardbound asset or model dependency.

The focused checks cover audio export/decoding and loop seams, deterministic
terrain builds, exact packaging inputs, title/theme/settings controls, battle
feedback, read-only playback and persistence. Final screenshots and receipts
are retained in the [presentation evidence](evidence/presentation-pass/README.md).

The Early Access gates remain open. The
[character verification](evidence/character-presentation/README.md) covers all
four portraits, specialist miniatures, equipment pages and manual hit feedback.
The [tactical verification](evidence/tactical-presentation/README.md) adds crowded
earned hold/extraction cases, compact controls and seal feedback at both reading
sizes and physical 720p, 800p and 1080p windows.
Human listening and playtest feedback remain part of assessing the game's
presentation quality.
