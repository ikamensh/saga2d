# Battle feedback — frozen source a27c473

All three native reports name clean source `a27c4739c413b4c0b48c3a928ac739aea7b3f2b6`,
with identical source hashes. Game and helper source stayed unchanged throughout
these captures, the full suite and stress run. This evidence-only commit follows
the source revision; no game rules, drawing or test helpers changed afterward.

- Full suite: **1,189 passed**, 440.21 seconds; compressed complete log retained.
  This overlapped the stress/native runs and is not an isolated performance benchmark.
- Model stress: **300 seeds**, 37,194 state checks, 5,607 paired traced/unobserved
  automatic rounds, **47,716 continuous events**, exact complete saved-state matches.
  Random policy outcomes and forced cleanup are separate counters; these are not
  300 demonstrated winning strategies.
- Scene stress: **20 runs**, **10,004 random inputs**, including **1,074 playback
  inputs** with unchanged authoritative state. Recruitment, replacement, spells,
  decisions, saves, linked transitions and ordinary battle controls remain exercised.
- Tribes regression fuzz: **60 AI games and 20 monkey runs**, no failures.
- Independent final review: **25 tests**, comprising 18 trace/modal regressions and
  seven separate public lifecycle probes. Its report and runnable probe are retained.

## Native capture

Every journey starts at Title and earns the real Commander Relief party through
ordinary campaign input. The watched commands use `finish_actions=False`; no
model mutations or private playback updates replace real UI input. Each viewing
tick compares the complete State to the already-resolved public command result.

| Journey | Inputs | Exact reloads | Watched batches | Native frame samples |
|---|---:|---:|---:|---:|
| Rally → flight → Brace → hit, 125% text | 126 | 2 | 1 | 159 |
| Same phase with reduced motion, 125% text | 128 | 2 | 1 | 159 |
| Paid passive hold through its pending result, 100% text | 139 | 3 | 2 | 319 |

Total: **393 inputs, seven reloads, four batches, 637 sampled native frames**.
The observed tick spans are 7.950, 7.950, 7.950 and 7.983 game seconds; the short
initial advance made by opening/closing the read-only overlays is outside these
sampled spans. Each complete batch is bounded by eight seconds. Settings/history
pause the scene. These are scripted offscreen Pyglet captures, not independent
human play or frame-rate/comprehension measurements.

`rally-flight-brace-hit.gif` contains 33 actual frames from the first 3.3 game
seconds, sampled at 10 fps. It has no added overlays, cropping or resizing; GIF
palette encoding is the only image conversion. `gif-samples.json` records the
original PNG names and hashes. The selected PNGs here are unaltered original
captures and were visually inspected: Rally, in-flight Skyrider, Brace for 9 HP before the attack,
subsequent hit for 7 HP, reduced-motion Brace, settings, history and the hold result.

The complete temporary PNG sequences were captured under
`/tmp/shardbound-feedback-a27c473/{rally,still,hold}/phase-*`; only the selected
images and compact clip are retained here. `rally-frame-timing.json` describes
the original full first sequence. Reproduce from the frozen revision with
`tools/verify_eador_battle_feedback.py`; each native JSON includes commands,
inputs, events, per-batch timing and source hashes.

## Findings resolved before freeze

The first native pass exposed an E keycap on Finish; the implementation now
creates the real Space button through a small inherited drawing hook. A moving
actor uses existing screen layers so it stays visible over crossed units and
their labels. The initial visual log is empty rather than leaking future events.
A real autosave-failure/F5 regression preserves the successful save message when
Finish returns to the ordinary battle. Two older verifier/test helpers now use
the visible Finish input, retaining all their previous outcomes and cooldown,
one-time reward and exact-save assertions.

This is a bounded G11 feedback increment. Direct player commands remain immediate;
long automatic batches use shorter event intervals within the fixed bound. It
does not establish human comprehension, all accessibility needs, release readiness,
or completion of any other gate. Root owns the separate native soak and final
packaged-build integration; those are not counted as this source's capture results.

The retained independent probe changes only its two temporary checkout paths to
this repository root; its assertions are unchanged. Run it explicitly with
`uv run pytest -q docs/evidence/battle-feedback-a27c473/review_playback_lifecycle.py`
from a checkout containing the frozen source.
