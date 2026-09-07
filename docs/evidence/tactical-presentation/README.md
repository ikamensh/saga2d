# Compact tactical controls and seal feedback — 2026-09-07

Implementation: `2c81343`, built on `dc8df68`. Auto-play, Retreat and Battle Log use the existing icons,
A/T/L keycaps and full hover explanations, including when disabled. The footer
shows the latest event and full-width order guidance; L opens all events, and
M opens a message that cannot fit. A fixed 96px footer and tighter header leave
more vertical room for the existing board without moving its cells after an
order. Objectives, primary orders and consequences keep text.

Two original short cues and ground rings announce recorded nonterminal seal
progress gain/loss. Terminal results retain their existing cue, and unchanged
progress stays quiet. Skipping unseen playback or loading discards pending
feedback. Reduced motion holds the rings stationary. All sixteen previous
WAVs are unchanged; see [audio comparison](audio-comparison.json) and the
[audio receipt](objective-feedback.txt). There are no new framework APIs, rules
or save fields; the game uses existing UI, image, drawing and audio primitives.

## Rendered verification

The final [native receipt](native/verification.json.gz) records actual Pyglet
input, screenshots, resolved states, source/asset hashes and physical window
sizes. The logical canvas remains 1280×800; physical windows cover 1280×720,
1280×800 and 1920×1080, with 100% and 125% reading sizes. Screenshots on this
Retina display have twice the physical window dimensions.

All eight final frames were inspected. The run records 104 inputs, three exact
save/load pairs and unchanged source/asset hashes, taking 57.83 seconds wall
and 14.35 seconds CPU (24.8% of one core). Fresh native radius is 44.55px at
100% and 43.91px at 125%; crowded hold is 40.18px and extraction is 40px. Each
of these retained boards has 37 cells; the finite-board fit remains unchanged.

- [Fresh battle at 100%](native/fresh-100.png) and [contact at 125%](native/fresh-contact-125.png).
- [Eleven-unit hold battle](native/earned-hold-125.png).
- [Blocked extraction](native/earned-extraction-entry-125.png) and [ready evacuation](native/earned-extraction-ready-125.png).
- [Seal gain and disabled Auto-play explanation](native/seal-gain-125.png) and [loss and disabled Retreat explanation](native/seal-loss-125.png).
- [Complete failed-save message](native/complete-message-125.png).

Checks cover stable cell centers across selection, orders, overlays and saves;
health inside the occupied hex and above transient effects; full log access by
click and L; exact A/T click and key results; exact evacuation; and a real failed
save caused by a temporary backup-directory collision. The full error remains
readable through M, while the prior save and current state remain unchanged.

The crowded cases come from fixed retained paid/earned hold and Scout journals;
seal transitions come from the recorded Relief plan. Their exact archive hashes
and locations are in the receipt. Historical preparation included autoplay.
No new campaign preparation or saved-field edits ran. Two explicit auto-round
control checks are restored through F9. These are presentation/input checks,
not independent campaign wins or evidence of build balance.

## Regression and build receipts

The layout tracer [first failed](layout-red.txt.gz) with a fresh 125% mock radius
of 37.818px against the 42px minimum, then [passed](layout-green.txt.gz).
Source review found disabled icon tooltips dropping their action names;
[rendered-hover RED](tooltip-red.txt.gz) and [GREEN](tooltip-green.txt.gz) retain
that regression. The seal tracer likewise records [RED](objective-red.txt.gz).
Its [ten focused checks](objective-focused.txt.gz) cover actual gain/loss,
unchanged/terminal objectives, skip/load cancellation, reduced motion, health
layering and audio catalogue integration.

The [initial integrated selection](focused-first.txt.gz) passed 37 tests. Its
shared visual journey failed because the verifier was edited during the source
fingerprint window; this was a coordination failure, with no failed gameplay
assertion. The [corrected frozen journey](journey-final.txt.gz) passes in 12.30
seconds, completing that 38-test selection. Passing tests
cover forecasts, icon controls, keyboard tactics, health footprints, playback,
manual attack contacts and exact packaging inputs. The raw selection is logged.

The [default audio build](audio-build.txt.gz) wrote eighteen WAVs in 13.39 seconds
wall and 3.34 seconds CPU (24.9% of one core). No synthesis runs during play.
Normal game caps remain 60 FPS active / 15 inactive. Native input uses 30 FPS;
verification and bounded fuzzing use the default cooperative 25% CPU allowance.
Expensive jobs run serially and close their games.

[Bounded Shardbound fuzzing](fuzz-eador.json) runs two model campaigns and two
100-step scene runs at seeds 83–84: 317 scene inputs, 307 scene state checks
and 230 model state checks pass in 10.2 seconds. Both model campaigns end in
defeat. This checks invariants and executability, not player success or depth.
The [Tribes check](fuzz-tribes.txt.gz) also passes two AI games and two random
input runs at seed 83. All 196 native source/asset hashes match the final files.

No release package, long acceptance matrix or audio soak was repeated. Silent
playback and sample checks are technical evidence; human listening/playtest
feedback remains outstanding. **G01–G19 remain incomplete.**
