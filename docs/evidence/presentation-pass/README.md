# Shardbound presentation checkpoint — 2026-09-07

Visual and audio work takes priority over the separately preserved adventure-route branch.
This checkpoint retains the presentation pass on baseline `1524c48`, including media
commit `46a5ded` and the integration committed alongside this evidence. It closes no
Early Access gate.

## What changed

An original generated landscape painting replaces the procedural star field. Forty-eight
original offline terrain illustrations provide six materials at province and battlefield
detail. Ground pigment is quieter; castles and miniatures have shaded faces and tabletop
bases. Actual battle orders now show arrows, blade arcs, magic, healing and displacement.
Ground effects sit beneath units, and transient numbers fit their hex without hiding
neighboring health. A quick Heal replaces the earlier damage number at the same hex.

Fourteen layered cues and two newly voiced original music loops use ordinary shipped
WAV playback. No artwork or audio synthesis runs during play. The game retains its
60 FPS active / 15 FPS inactive cap. Development builds and visual input use cooperative
25% CPU pacing, with native input capped at 30 FPS. These measurements are scoped to
the tools below and do not establish runtime battery life.

## Retained checks

- [Initial scene/settings/asset/packaging selection](scene-assets-tests.txt): 66 passed
  in 33.15s, before the final ground and damage-label refinements.
- [Final battle feedback, game audio and reduced-motion selection](battle-feedback-tests.txt):
  23 passed in 6.84s. Public orders check visible feedback, unblocked saves/commands,
  unchanged authoritative state, synchronized playback cues and health-label separation.
- [Final terrain and packaging selection](terrain-package-tests.txt): 6 passed in 2.67s,
  including relocated catalogue decoding and rejection of changed bytes.
- [Audio composition/build selection](audio-tests.txt): 6 passed in 6.81s, including
  exact paced/unpaced PCM, sampler content, loop seams and finite/headroom properties.
- [Native audio](audio-native.txt): every cue completed, both tracks crossed a complete
  loop, and live mute/mix and cleanup passed. 93.85s wall / 2.32s CPU, silent driver.
- [Audio build](audio-build.txt), [resource measurement](audio-build-time.txt): sixteen
  shipping WAVs, 9.46s wall / 2.35s CPU.
- [Final terrain build](terrain-build.txt): 48 verified PNGs, 10.41s wall / 2.58s CPU.
  The [exact comparison](terrain-comparison.json) confirms all 24 province illustrations
  stayed byte-identical while the 24 ground illustrations received quieter pigment.

The final native visual reports and bounded fuzz receipts below record their actual
source hashes. Earlier intermediate visual iterations exposed health-label collisions;
the retained final images include the fixes. Screenshots under `before/` were captured
at the baseline; the baseline battle uses Commander while the new home-battle captures
use Wizard, so this is an illustration of the presentation change, not a matched combat
or performance comparison.

## Scope and artistic review

The static journey opens all three worlds at native resolution, checks normal and larger
reading size, and exercises exact save/load joins. The effects journey starts with a fresh
Wizard home site and a Commander Observatory army prepared through public model commands.
That preparation includes autoplay; only the demonstrated site entry and battle orders are
native input. Each captured effect frame preserves the already-resolved state. This is a
presentation check, not an independent first run or evidence of full campaign depth.

The [49-second sound sampler](../shardbound-cue-sampler.wav) includes every cue, campaign
music from 15.71s and battle music from 32.46s. Technical sample and silent-driver checks
cannot establish perceived quality or fatigue. Audible artistic review remains open.
[Artwork provenance](../../../eador/assets/VISUAL-PROVENANCE.md) retains the exact image
prompt and the original game-owned terrain sources. The [design note](../../eador-presentation.md)
records the framework/game boundary and next presentation work.

## Final native images and bounded checks

[Static report](static/report.json): nine screenshots, nineteen native inputs,
four exact reloads. All nine PNGs are retained under `static/` and were inspected.
[Title](static/title-frontier.png), [Frontier map](static/campaign-frontier.png),
[Elderwild map](static/campaign-elderwild.png),
[larger-text battle](static/battle-reading-125.png).

[Effects report](effects/verification.json.gz): six actual effect cases, 91 native
inputs, six exact reloads; 35.12s wall / 8.80s CPU (25.06% of one core).
All nineteen native captures were inspected. Eight representative PNGs are
retained here; the report also records eleven additional observed frames that
are not copied into the repository. The preserved contact examples include
[arrow](effects/arrow-20.png), [Bolt](effects/bolt-20.png),
[melee](effects/melee-20.png), [Heal](effects/heal-20.png),
[Swap](effects/swap-20.png) and [Smoke](effects/smoke-20.png).
The report's full source/manifest hash set stayed unchanged throughout the run.

[Final Shardbound fuzz](eador-fuzz.json), [console](eador-fuzz.txt): two model
campaigns and three scene runs at seeds 41–43, 100 steps each, 25% CPU allowance.
470 input events and 640 model/scene invariant checks passed in 13.0s. No
source files changed during the run. This deliberately small regression check
does not replace the outstanding release-candidate stress work.

[Required bounded Tribes regression](tribes-fuzz.txt): two AI games and two
600-event random-input runs at seed 41, with 25% CPU pacing; zero failures.
All owned test and native game processes exited. No cancelled stress matrix or
soak was restarted.

`artifact-manifest.json` hashes every retained file in this checkpoint except
itself. Shipped art/audio manifests and the sampler remain at their ordinary
project paths rather than being duplicated here.

The effects report is losslessly gzip-compressed to keep full before/after states
out of ordinary source diffs. Decompression restores the original native receipt.
