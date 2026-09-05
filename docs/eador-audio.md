# Shardbound audio catalogue, generator 1

The shipping catalogue contains twelve original cues and two stereo loops.
`eador/sound.py` owns compositions: note sequences, voicings, timing, balance
and deterministic noise seeds. `saga2d.synth` supplies synthesis and PCM
encoding. No recorded samples, borrowed Eador assets or externally sourced
melodies were used. Source and generated assets use the repository MIT license.
The exact files, source hashes, generator version and runtime versions are in
`eador/assets/audio-manifest.json`; assets have no first-launch generation or
cache dependency.

## Musical choices

The shard motif is **E–F#–B–G**. The campaign's 48-second form uses twelve
slow 4/4 bars (60 BPM): six overlapping harmonic fields around E minor,
C major, G major, D major, A minor and suspended B. Low reed-like voices
carry the harmony, while sparse panned glass notes answer the motif and
quiet seeded air textures vary each field. Notes cross the loop boundary
by wrapping their tails into the beginning, rather than fading the entire
track in and out.

The 32-second battle loop uses sixteen 4/4 bars at 120 BPM, felt in half-time.
It follows E minor, A minor, C major and suspended B with low tom patterns,
spaced upper answers and fewer sustained upper voices. Its activity comes
from rhythmic placement, not a louder master level.

Music peaks are 0.16 (campaign) and 0.18 (battle); cue peaks range from 0.38
to 0.62. Existing Shardbound preference gains further reduce music relative
to effects. These are file-level headroom choices; arbitrary overlapping
runtime cues can still add together, so event routing should remain deliberate.

## Runtime integration

Configure `Game(asset_path=...)` to point at the shipped `eador/assets` root.
Load/apply preferences before starting audio. Cues play through the existing
manager, and `set_music` avoids restarting the current selection:

```python
from eador.sound import set_music

game.audio.play_sound("attack_hit")
set_music(game, "campaign")
set_music(game, "battle")
set_music(game, None)
```

`CUES` and `TRACKS` are composition factories for build/verification tools;
calling `set_music` never generates samples or creates another AudioManager.
The runtime has no cache or synthesis requirement. Trigger cues from confirmed
commands/outcomes; drawing, refreshing menus and reopening overlays should not
replay them. Scene hooks, asset paths and packaging are root-owned integration
work and are not added by this composition increment.

## Listening review

**Artistic/listening approval remains outstanding.** Waveform checks and silent
native playback establish technical properties, not pleasant timbre, fatigue,
cue recognition, dramatic suitability or perceived looping. No audible
listening judgement is claimed. A human should review the sampler and both
loops at the player's default settings, then at low and high practical volumes.

The separated cue sampler is `docs/evidence/shardbound-cue-sampler.wav`
(13.88 seconds). Its timeline is:

| Start | Cue | Intent |
|---|---|---|
| 0.25s | `confirm` | A brief E–B answering chime. |
| 0.87s | `refuse` | A muted descending semitone. |
| 1.51s | `move` | Two gravel bootfalls. |
| 2.18s | `attack_hit` | Short edged impact and low body. |
| 2.78s | `guard` | Hollow shield knock and muted ring. |
| 3.60s | `bolt` | Rising electric streak and spark. |
| 4.36s | `heal` | Soft opening minor triad and breath. |
| 5.51s | `reward` | Three lightly struck upper notes. |
| 6.53s | `level_up` | A longer, wider ascent. |
| 8.09s | `victory` | Shard motif settling into an open minor-add-nine chord. |
| 10.61s | `defeat` | Slow descent ending on unresolved B. |
| 12.68s | `end_turn` | Wooden tick and downward fifth. |

## Rebuilding and verification

```bash
uv run python tools/build_eador_audio.py
uv run python tools/build_eador_audio.py --verify-native
uv run python -m pytest tests/eador/test_shardbound_sound.py -q
```

The generator writes ordinary 44.1 kHz, 16-bit PCM WAVs before packaging.
Repeated generation on the recorded Python/NumPy runtime is byte-identical;
source hashes make changes reviewable. The builder does not silently regenerate
anything during play. The sampler is a review artifact, separate from shipping
sounds/music.

Public integration checks compose, export, decode and route the catalogue
through `Game.audio`; verify deterministic regeneration and manifest hashes;
check finite samples, sensible duration, stereo content, headroom and cue edges;
and inspect loop seam steps and neighboring samples. The optional native
checker plays every cue to completion and each music stream through one full
loop with Pyglet's silent driver. It exercises live mute/mix, unchanged track
selection and teardown of a still-active music player.
