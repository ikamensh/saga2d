# Shardbound audio catalogue, generator 3

The shipping catalogue contains sixteen original cues and two stereo loops.
`eador/sound.py` owns the compositions and instrument voices: note sequences,
voicings, timing, stereo reflections, balance and deterministic noise seeds.
`saga2d.synth` supplies sample primitives and PCM encoding. No recorded samples,
borrowed Eador assets or externally sourced melodies were used. Source and
assets use the repository MIT license. The exact files, source hashes,
generator version and runtime versions are in `eador/assets/audio-manifest.json`.
There is no first-launch generation or synthesis cache.

## Musical choices

The shared shard motif is **E–F#–B–G**. The campaign's 48-second form uses twelve
slow 4/4 bars (60 BPM): six overlapping harmonic fields around E minor,
C major, G major, D major, A minor and suspended B. Bowed voices now combine
two slightly detuned harmonic sets, slow vibrato and quiet friction. Wooden
lute figures add a pick transient, damped upper harmonics and body resonance;
breathed flute phrases answer them. Soft skin drums mark the larger phrases,
with wind and stereo reflections giving the arrangement depth. Registers,
spacing and flute answers vary across the six fields.

The 32-second battle loop uses sixteen 4/4 bars at 120 BPM, felt in half-time.
It follows E minor, A minor, C major and suspended B. Short bowed low strings
carry an ostinato beneath layered membrane drums and dry rattles. Lute and
flute statements alternate, with restrained metallic accents at phrase ends.
The music's activity comes from articulation and rhythm as well as harmony.

Notes and room tails wrap across the loop boundary. Neither whole loop fades
to silence at its seam. File-level peaks remain 0.16 (campaign) and 0.18
(battle); existing player preference gains further reduce music relative to
effects. Cue peaks range from 0.38 to 0.64. These provide headroom, although
simultaneous runtime cues can still add together.

## Cue identity and timing

The effects use layered material sounds: gravel and leather footfalls, wood
and metal contacts, string plucks, breath and sparks:

| Cue | Sound and intended timing |
|---|---|
| `confirm`, `refuse` | Brief affirmative plucks or muted descending knocks. |
| `move` | Two weighted gravel footfalls. |
| `attack_arrow` | Bowstring release and feathered air; contains no impact. |
| `attack_hit` | Edged metal scrape, wooden crack and low contact, at impact. |
| `attack_heavy` | Deeper body and loose armour rattle, at heavy impact. |
| `guard` | Hollow shield knock with damped iron resonance. |
| `bolt` | Tearing air, branching sparks and a resonant crack. |
| `heal` | Opening flute triad and gently resonating strings. |
| `reward`, `level_up` | Hammered-string reward or a wider ascent into flute. |
| `victory`, `defeat` | Motif and bowed resolution, or an unresolved descent. |
| `end_turn` | Woodblock tick and muted lute answer. |
| `seal_gain`, `seal_loss` | Rising metal/flute resonance for hold progress; a falling, damped resonance when progress breaks. |

An arrow release can precede one separately timed ordinary/heavy contact.
Game scenes own event timing and weapon classification; composition factories
know nothing about units, battle state or scene transitions.

`eador/battle_audio.py` maps actual recorded actors to cues in manual orders and
turn playback. Direct attacks drain release/contact boundaries against the
existing visual trace clock, including Brace and retaliation. Ranged staff and
rune weapons use the composite `bolt` cue once at contact, with an arcane visual.
Another accepted order finishes pending contacts before its own cue; loading,
retreating and leaving discard them. Redraws do not replay sounds. The queue
stores only elapsed offsets and cue names, without timers, callbacks or model
ownership.

Recorded nonterminal hold-progress changes play `seal_gain` (0.71 seconds) or
`seal_loss` (0.58 seconds) once at their visible contact, accompanied by a ground
ring on the seal. Unchanged progress plays neither cue. Terminal objectives use
the existing victory/defeat result instead. Skipping unseen playback or loading
discards its pending feedback; drawing and reopening a scene cannot repeat it.

## Runtime integration

Configure `Game(asset_path=...)` for the shipped `eador/assets` root. Apply
preferences before starting audio. The ordinary game manager plays the WAVs:

```python
from eador.sound import set_music

game.audio.play_sound("attack_hit")
set_music(game, "campaign")
set_music(game, "battle")
set_music(game, None)
```

`set_music` does not restart an unchanged selection. Importing the catalogue,
playing an effect and selecting music never synthesizes samples. The richer
instrument work happens in the explicit asset build, with no additional
runtime synthesis cost. Confirmed events trigger cues; drawing and reopening
overlays should not replay them.

## Listening review

**Artistic/listening approval remains outstanding.** Waveform checks establish
finite samples, headroom and continuous seams, not perceived quality, fatigue,
recognition or dramatic suitability. No human listening judgement is claimed.

`docs/evidence/shardbound-cue-sampler.wav` contains every separated effect,
followed by sixteen seconds of the actual campaign arrangement and sixteen
seconds of the battle arrangement. Excerpt edges fade only in the review
sampler; the shipping loops retain their wrapped tails. Exact cue starts and
music source/excerpt times are recorded under `sampler` in the manifest.
The full loops are `eador/assets/music/campaign.wav` and `battle.wav`.

## Rebuilding and verification

```bash
uv run python tools/build_eador_audio.py
uv run python tools/build_eador_audio.py --cpu-percent 100
uv run python tools/build_eador_audio.py --verify-native
uv run python -m pytest tests/eador/test_shardbound_sound.py -q
```

The builder writes 44.1 kHz, 16-bit PCM WAVs before packaging. One cooperative
`CpuBudget(25)` spans the build, yielding between assets and musical voices;
`--cpu-percent 100` explicitly disables sleeping. This is an average allowance,
not a hard instantaneous cap: a single NumPy operation can exceed a checkpoint
interval. The manifest records the allowance and hashes its implementation.
No generation runs during play. Repeated generation on the recorded
Python/NumPy runtime produces the same PCM regardless of the allowance.

Public integration checks compose, export, decode and route the catalogue
through `Game.audio`; compare paced and unpaced regeneration; verify sampler
music against the shipping PCM; and check exact provenance, finite values,
durations, stereo content, cue edges and loop seams. The optional native
checker uses Pyglet's silent driver to play all effects to completion and
both streams through a full loop, including live mute/mix and cleanup. A
silent-driver check is a technical playback check, not an audible review.

Generator 3 adds two seal cues while preserving all sixteen previous WAVs byte
for byte. Its default build wrote eighteen files in **13.39 seconds wall time
and 3.34 seconds CPU** (about 24.9% of one core). Ten focused integration checks
pass, covering actual progress gain/loss, unchanged and terminal objectives,
skip/load cancellation, reduced motion, and the catalogue. See the
[tactical presentation evidence](evidence/tactical-presentation/README.md).

Generator 2's focused composition/build suite passed **6 tests in 6.81 seconds**.
The weapon tracer first failed on the missing `attack_arrow` cue; the build
tracer first failed because default generation never yielded. Both now pass,
including exact paced/unpaced PCM and sampler comparisons. One real default
build generated all sixteen shipping files in **9.46 seconds wall time and
2.35 seconds of user + system CPU** (about 24.8% of one core). That measurement
covers this build only; it is not a runtime game or battery measurement.
The subsequent presentation pass played all fourteen cues to completion and
both full loops with the native silent driver. Live volume/mute changes,
continuous streaming and player cleanup passed in **93.85 seconds wall time,
2.32 seconds CPU**. The retained receipt is
[audio-native.txt](evidence/presentation-pass/audio-native.txt). This checks
playback mechanics; audible artistic review remains outstanding.

## Historical generator 1 integration checkpoint — 2026-09-06

The launcher and scene verification adopted `eador.app.create_game`, returning
an ordinary Saga2D Game with the shipped asset root, theme and save location.
Title and campaign selected the campaign loop, battles selected battle music,
and terminal results stopped it. Confirmed actions, rewards and new battle
outcomes received cues, while saved terminal results did not replay victory.
Public input checks exercised volume/mute, manual commands, rewards and saves.
At that checkpoint, the complete suite passed 643 tests before an additional
manual-cue journey. Native Pin/Watch and source packaged-entry smoke checks
passed with the silent driver and the then-fourteen-file catalogue. No frozen
candidate was rebuilt in that step. Those dated checks describe generator 1;
they are not current proof of generator 3 or artistic listening approval.
