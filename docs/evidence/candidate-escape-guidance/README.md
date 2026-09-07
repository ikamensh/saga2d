# Escape guidance and singular defender text

The default battle footer now advertises a ready evacuation before the selected
unit's ordinary ability hint. After the paid Warden delivers the hero, the Warden
still reads **Spent** and Swap remains disabled with its reason. Explicit command
messages and active targeting retain priority. The header uses **1 foe** for one
living defender.

## Verification

Both regressions failed on their original text, then passed. The final focused
selection passed **4 tests in 0.18 seconds**: these two regressions plus existing
compact-footer/log and disabled-playback-icon checks. Exact logs are alongside
this README.

`verify.py` loads two unchanged checkpoints from the retained, manually played
seed5 journal, authenticated by SHA-256
`cdccd3ef5ae9750098d371b6c31de7c97196aaa4091c2b7f56bebe564ccda846`:

- `commands[102].before`: issue the recorded Warden Swap through native input,
  inspect the spent Warden and ready evacuation, F5/F9, then V. Both resulting
  states exactly match the original journal.
- `commands[12].after`: inspect the Shrine's one remaining defender and F5/F9
  without changing its campaign state.

The original route executed at `37a4e6056196f13ef125664ddd1c4601ee0719f8`.
This bounded native check ran at `ebcb1323bc037557eb5b446e96ba301a3d5d45c4`
with the two scene edits uncommitted. Its receipt fingerprints all **194** scoped
source, asset, verifier and journal files; they remained unchanged during the run.
The captured `eador/scene.py` SHA-256 is
`6672d6e0691333fd96e8783062654c365b092b437d102a80678de0126eb4152b`.

Native result: **2 PNGs, 15 inputs, 2 exact reload pairs; 16.172 seconds wall /
4.090 seconds CPU** at requested 25% CPU and 30 FPS. Both windows were 1280×800
with 125% reading; native framebuffer PNGs are 2560×1600. Each game closes in
`finally`, and the bounded `caffeinate` child is terminated and waited for.

## Viewed frames

- [Ready after Swap](native/ready-after-swap-125.png): footer and objective agree
  that V evacuates; selected Warden remains Spent, disabled Swap/Guard remain
  legible, and all persistent HP labels are readable.
- [One foe](native/one-foe-125.png): **5 allies · 1 foe · Tab selects** fits, with
  the board, commands and footer readable.

No blocking overlap or clipping was observed. The receipt is compressed
losslessly at `native/verification.json.gz`; PNGs and logs are exact copies.
This is a focused automated native regression, not an independent first-run or
full-campaign test. No campaign preparation, autoplay or full replay ran here.
