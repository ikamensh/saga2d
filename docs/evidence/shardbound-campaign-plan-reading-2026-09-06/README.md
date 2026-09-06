# Current campaign plan reading evidence — 2026-09-06

Source `d14033f70a5a8b17e3174e37f732068709efc01d` passed the full suite and
native matrix. [Provenance](provenance.json) records the platform, command and
source/artifact hashes. Six retained native frames were inspected:

- One actually held Foundry at [100%](foundries-held-1-100.png) and [125%](foundries-held-1-125.png).
- [Cleared Border Watch](rootward-watch-cleared-125.png), including the now-open assault.
- [Spent recovery](foundries-recovery-spent-125.png) after losing the capital and beginning the public recovery expedition.
- [The earned final Gate](gate-arrival-125.png), with its full objective and correct campaign-completion wording.
- [Challenge opening](opening-challenge-125.png), with actual stage limits and recovery funding.

The [matrix](matrix.json) passed **66 layouts / 530 input activations**:
11 saved states at 100% and 125%, in 1280×720, 1280×800 and 1920×1080 windows.
The cases cover all five contracts, all three mode openings, zero/one/two held
Foundries, cleared Border Watch, both earned finales and spent recovery.
States came from public purchases, battles, travel, advancement, capital loss
and recovery; no progress, inventory or experience was inserted.

Each target was located through its visible keyboard shortcut at 100% and
actual button bounds at 125%. Full state JSON stayed identical. The verifier
also exercised Settings Cancel/Apply/restart, Hero return and exact save/load.
Native font measurement caught an initially over-tall layout before this
source: putting each target, status and Locate button in one measured row
kept all objectives and rules visible without reducing the requested type size.

At this same source, **1,091 tests passed in 96.96 seconds**. Tribes passed
60 AI games and 20 input-monkey runs at seed 17. The [linked Shardbound fuzz
report](linked-fuzz.json) passed 60 model campaigns and 20 scene runs with
3,724 input activations. All random campaign policies ended in defeat; these
checks exercise command/state invariants rather than winning play or balance.

This covers the current **Campaign / J** plan. Transition, retinue, ending,
map and battle layouts are outside this reading slice. The native evidence
is for this macOS host and fixed 1280×800 logical canvas; it does not establish
cross-platform visual readiness or global UI scaling. See the
[implementation note](../../eador-campaign-plan-reading.md) for the interface
and reproducible verifier.
