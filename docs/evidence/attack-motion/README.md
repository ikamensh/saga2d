# Attack and hit motion — 2026-09-07

[Native preview](gameplay.mp4): 16.83 seconds, 505 frames at 30 FPS. Four cases
show a Commander melee attack and retaliation, a Wizard army arrow, an earned
final arrow, and reduced-motion melee. Audio is reconstructed from actual emitted
cues, shipping WAVs and effective gains; it is not hardware-recorded sound.

Attacks move toward the target and return, with a smaller ranged lean. Damage
causes recoil after contact. Picking and health/status plaques stay at the hex.
A defeated miniature briefly completes its visible reaction; authoritative
damage and persistence remain immediate. Reduced motion disables these offsets
and lingering figures. Local direct orders and turn playback share the code.
Online co-op snapshot presentation is unchanged.

## Evidence

- `native.json.gz` and `mock.json.gz`: real inputs, before/after states, four exact
  UI save/load round trips per backend, audio events, source hashes and cleanup.
- Four retained native PNGs were visually inspected: melee lunge, melee recoil,
  final-arrow recoil and reduced-motion recoil time.
- `encoder.log` records the completed single-thread encoder; `sha256.json`
  fingerprints the retained files. The receipts also name unretained chapter
  frames and the source audio mix from the temporary capture directory.

The Commander setup uses public campaign commands and automatic preparation
battles; the shown attacks are manual. The final arrow reuses authenticated
order 13 from the existing gameplay-movie receipt, with its origin hash checked.
This is a focused presentation check, not independent campaign playtesting.

The related motion/playback/audio/final-blow suite passed 53 tests. After adding
the lethal-retaliation casualty regression, all seven motion tests passed on
the final source. Mock and native journeys then passed without source changes.
No broad suite was rerun for the wrap.

Native capture took 95.92 seconds wall / 24.12 seconds CPU, including preparation
and audio mixing; separately paced encoding followed. Both requested a 25% CPU
allowance, and the Game closed. This fixed-clock capture is not a runtime battery
measurement. Normal game caps remain 60 FPS active / 15 FPS inactive.

Reproduce with an empty output directory:

```sh
.venv/bin/python tools/verify_eador_attack_motion.py --backend mock --output /tmp/new-motion-mock
.venv/bin/python tools/verify_eador_attack_motion.py --output /tmp/new-motion-native --ffmpeg /absolute/path/to/ffmpeg
```

Human listening and playtesting remain open. The existing floating damage
numbers can briefly cover faces; their timing was outside this change.
