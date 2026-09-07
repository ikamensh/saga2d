# Contact feedback — 2026-09-07

Native movies at [100%](gameplay-100.mp4) and [125%](gameplay-125.mp4) reading
size show four real attack cases each: melee with retaliation, an arrow paused
under Help, an earned final arrow, and reduced-motion melee. Each movie is
18.03 seconds / 541 frames, with 18 damage-label observations and four exact UI
save/load round trips. Both captures and the 125% mock journey passed.

Attack damage labels now arrive at each recorded contact instead of announcing
retaliation during wind-up. Smaller labels clear the figures' faces and leave
space beside upper-neighbor health plaques. Notices retain up to 1.6 seconds of
readability across playback events and natural completion. A newer hit replaces
the recipient's earlier label; moving or swapping a recipient removes its old
label instead of attaching damage to another occupant. Explicit playback skip
clears the presentation. Reduced motion keeps the label stationary.

Help/Saves now pause pending direct-attack sounds rather than discarding them
(commit `1e15c1e`). The movie opens Help before an arrow lands, verifies that
the covered battle clock and impact count remain unchanged, then observes
exactly one impact after returning. Loading a save still discards old feedback.

## Verification and limits

The sound regression first failed for Help and Saves return; loading passed.
All 20 manual-audio tests passed after the lifetime fix. Contact timing,
playback readability, natural completion, stale Swap labels and face clearance
each failed their regression before being fixed. A 64-test focused run passed;
after the final natural-completion change, all 30 motion/playback tests passed.
The final native journeys then passed with source fingerprints unchanged.

The four retained PNGs were inspected: melee at both text sizes, the final
arrow and reduced motion at 125%. Receipts retain input, state, sound and draw
observations plus source and original capture hashes. Unretained chapter PNGs
and WAV mixes are named in the receipts. `sha256.json` hashes retained files.

Preparation is the same disclosed public-command Observatory setup and
authenticated earned final arrow as the [previous preview](../attack-motion/README.md).
This is presentation verification, not independent campaign playtesting.
Audio is reconstructed from emitted cues and shipping WAVs, not recorded from
the output device or reviewed by a human listener. Games and the separately
paced single-thread encoders closed; 30 FPS / 25% CPU allowances were retained.
Capture timing is not a runtime battery measurement.

Health, combat rules and saves still resolve immediately. Direct spell/heal
cues retain their earlier timing; online co-op remains snapshot presentation.
No framework API or package rebuild is part of this increment.

```sh
.venv/bin/python tools/verify_eador_attack_motion.py --backend mock --reading-scale 125 --output /tmp/new-feedback-mock
.venv/bin/python tools/verify_eador_attack_motion.py --reading-scale 125 --output /tmp/new-feedback-native --ffmpeg /absolute/path/to/ffmpeg
```
