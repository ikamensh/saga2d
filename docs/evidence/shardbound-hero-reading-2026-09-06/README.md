# Hero reading and playable infusion — 2026-09-06

Development source **20de5598c4a46de76b36b151bb6cf9c28b5c6b2b**, macOS ARM64,
Pyglet on the host Retina display. The native run began on its preceding Git
base with the final source edits present. Every one of the 66 recorded source
and fixture hashes matches the committed checkpoint exactly; provenance keeps
the actual run base instead of rewriting it. No packaged-build or human
playtest claim is made for these changes.

- Full suite: **1,059 passed in 75.36 seconds**. Tribes: 60 AI games and 20
  random-input scene runs, zero failures.
- Linked Shardbound stress: 12 model campaigns and 12 mock scene runs,
  **2,194 input activations**, 10 accepted and 118 refused model infusions.
  Exact source hashes and the complete metrics are in `linked-fuzz.json`.
- Native Hero: **182 complete pages**, **610 input activations**, two exact
  quicksave/reloads, and a fresh Game restoring the 125% reading preference.
  The keyboard and mouse infusion branches use the identical paid Wizard
  checkpoint, spending three crystals and one action for its capped four-mana
  deficit. Disabled repeated input changes neither state nor save files.
- Forty-eight read-only collection traversals cover eight actual states at
  100/125% in 1280×720, 1280×800 and 1920×1080 windows. These include all twelve
  relics, both earned disciplines for each hero class, an actual defeated run,
  the historical v11 collection and an empty new hero. Actual backing sizes are
  2560×1440, 2560×1600 and 3840×2160. Completed-state panels are opened through
  the public Scene API for layout inspection, not claimed as campaign navigation.
- Native purchase catalogs pass **33 complete pages** after adding the Tower's
  full infusion explanation; purchases and reading Apply/Cancel/restart pass.
  The Guide, Settings and paid Observatory tracer pass six records with the
  updated in-game guidance. Their matrices are included.

All six retained PNGs were inspected. They show the exact quote and result,
two learned disciplines and full relic text, a real equipment autosave failure,
the Tower's purchase description and the in-game teaching path. The failure
keeps the already-applied equipment change in memory, preserves damaged files,
and immediately tells the player to use a manual slot.

The existing relic-art verifier also passed public mock and native input after
replacing fixed groups of four with visible relic IDs. It earned/reloaded all
four newer active relics and verified that repeated Equipped activation does
not rotate saves. That separate earlier run is not included in the 610 inputs.

The changes reuse Saga2D's existing wrapped Labels, Rows, Columns, button-owned
shortcuts and save I/O. Recovery rules, infusion eligibility, whole-relic paging
and the reading preference remain in the game. Resource surpluses and complete
screen scaling remain open; no release gate is marked complete by this tranche.
