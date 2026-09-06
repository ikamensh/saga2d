# Earned decision reading evidence — 2026-09-06

Source `89782c220b99edf2ced068f86cf5a0abbd7ffb40` includes the integrated
Hero and Result conversions and the separate SaveManager diagnostic fix.
[Provenance](provenance.json) records the command, platform and source/artifact
hashes. All six retained native frames were inspected:

- Veil Censer's complete consequence at [100%](censer-100.png) and [125%](censer-125.png).
- [Wizard discipline alternatives](wizard-disciplines-125.png) and [one remaining discipline](single-discipline-125.png).
- [An actually earned duplicate relic](duplicate-125.png).
- [A final applied decision whose checkpoint failed](applied-save-error-125.png).

The [matrix](matrix.json) passed 42 earned/reloaded decisions across 252 layouts:
both reading sizes and 1280×720, 1280×800, 1920×1080 windows. Every relic,
all four hero classes, late ranks and duplicate offers are represented. The
native run used 925 input activations, compared each offered choice's full
result against the public model through both keyboard and mouse, and exercised
Settings Apply/Cancel/restart, overlay return, save/load and preserved corrupt
autosaves. The single-discipline image additionally checks that its absent
second choice cannot be triggered by pressing 2.

The combined full suite passed **1,077 tests**. Earlier in the same isolated
increment, with the same Choice behavior but before the parser diagnostic fix
and Result merge, Tribes passed 60 AI games plus 20 input-monkey runs at seed17.
The [linked Shardbound fuzz report](linked-fuzz.json) passed 60 model campaigns
and 20 scene runs with 3,724 input activations. Those random policies all ended
in defeat; their purpose is command/state invariants, not winning play.

This is measured layout, input and persistence evidence for this source and
native platform. It is not a global UI scaling or campaign balance claim.
See [the implementation note](../../eador-choice-reading.md) for scope and
the reproducible verifier.
