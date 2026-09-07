# Declared route input verification

These receipts reproduce the exact accepted commands in the original
[seed 5](../route-seed5-outcome.md) and [seed 12](../seed12-outcome.md) journals.
Both begin through Title → New Campaign input, then use actual keyboard/click
controls with 125% text size. Each command's saved result and subsequent F5/F9
reload must match the journal. No prepared army replaces the fresh origin.

| Replay | Accepted commands / exact reload pairs | Inputs | Wall / CPU seconds |
| --- | --- | --- | --- |
| Mock seed 5 | 107 / 107 | 439 | 12.463 / 3.115 |
| Mock seed 12 | 112 / 112 | 462 | 12.961 / 3.217 |
| Native seed 5 | 107 / 107 | 440 | 44.899 / 11.503 |
| Native seed 12 | 112 / 112 | 463 | 45.284 / 11.577 |

Each directory contains the losslessly compressed original verification JSON.
Native directories also retain all nine original PNGs and the process log.
The receipt's `captures` array lists eight per route; the ninth is an automatic
encounter briefing capture. All eighteen actual PNGs were inspected. The root
also inspected entry, ready evacuation and final-world frames in both routes.
Icons, health, objectives and evacuation status are readable at this size; the
six-troop row's Swordsman/Archer labels are close but do not overlap.

Seed 5's post-Swap frame has a minor guidance conflict: the selected, spent
Warden's footer suggests ending the round while the objective correctly reports
ready evacuation. Selecting the Commander in the next frame removes the
conflict; evacuation succeeds. This is retained as a presentation follow-up.

All four receipts authenticate 82 unchanged Python sources, including the input
adapter. Native execution used commit `212a60b`; original model execution began
on `37a4e60` for seed 5 and `51d4e11` for seed 12. The runtime bytes did not change
between those executions. These receipts hash source files; asset provenance is
separately retained by the [discovery reader](../discovery-reader/README.md).

## Execution and scope

The original journals preserve reasons, forecasts and each route's rejected
move. Replays exercise the accepted command chain; they do not replay those
two rejected attempts. Agent operators chose explicit commands, using model
observations and forecasts. They did not use autoplay, injected resources or
rewinds. Native reproduction is verification of those routes, not another
independent strategy or human playtest. Audio was silent.

`serial-director.py` is the exact temporary scheduling wrapper used once the
two operators worked alongside one another. It holds an OS file lock for each
whole director process. `processes.jsonl` retains 40 nonoverlapping execution
intervals: 11 seed-5 requests, 28 seed-12 requests and one companion-test run.
This log covers work after that wrapper was introduced, not earlier commands.
One seed-12 request exits 1 for the retained blocked Commander move after
command 32. Its preceding accepted orders remain saved; only the rejected
order leaves state unchanged. The other process exits are zero.

Mock and native replays then ran serially, followed by no remaining game job.
Native input is paced at 30 FPS and uses the cooperative 25% CPU allowance;
measured CPU averages are approximately 25.6% of one core. This allowance is
not an operating-system hard quota. Each verifier closes its Game in `finally`,
and its process-bound display wake assertion ends with it. The game retains
its existing 60 FPS active / 15 FPS inactive caps.

Two local expeditions do not establish general balance, complete campaign
strategies, human usability or release readiness. Companion tests and bounded
fuzzing are linked from the parent evidence document; the large release matrix
and soak were not run for this increment.
