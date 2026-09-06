# Build and Recruit reading evidence — 2026-09-06

Source `91f89c7fb04fa6c418da4a07e8193dfc99fe881c`. The
[provenance](provenance.json) records source/artifact hashes and the exact native
command. Four final frames were visually inspected:

- Build [100%](build-100.png) and [125%](build-125.png).
- [Recruit costs and blockers at 125%](recruit-prices-125.png).
- [Restarted Recruit at 125%](recruit-restarted-125.png).

The [native matrix](matrix.json) passed 30 complete pages at 100/125 across
1280×720, 1280×800 and 1920×1080 windows. Every building/recruit appears once in
order per traversal. Real mouse/keyboard input buys a Barracks and Swordsman,
checks disabled repeat buying, keeps the first item through Settings Apply/Cancel,
and restarts with the saved preference. The game canvas stays 1280×800.

The isolated full suite passed 1,046 tests. Public purchase tests additionally
cover full armies, prerequisites, crystal-only shortages using valid funded saves,
and damaged-autosave errors with preserved bytes. Existing paid campaign journeys
continue to buy by visible item ID rather than a fixed page length. The
[Shardbound fuzz report](eador-fuzz.json) covers 60 model campaigns and 20 scene
runs (3,716 input activations); Tribes' 60-game/20-monkey run also passed.

These checks establish layout and input behavior on this source snapshot; they
do not claim every game screen scales or certify fonts on other platforms.
