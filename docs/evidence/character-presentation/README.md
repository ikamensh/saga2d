# Character and contact presentation — 2026-09-07

Implementation **de91293**, integrated with current main in **38f770e**. Four
original painted portraits use ordinary Saga2D images and measured layout.
Hero level, health and mana use existing icons and exact values. Fourteen troop
miniatures and four heroes have distinct equipment and shaded materials.
[Portrait prompts and exact hashes](../../../eador/assets/hero-portrait-provenance.json)
ship with the assets. This increment adds no framework API or game rules.

Manual attacks play release/contact sounds for every recorded hit, Brace and
retaliation. Wizard, Rune Adept and Acolyte basic ranged attacks share magic
classification for sound and blue projectiles. New orders finish pending
contacts; load/retreat/exit discard them. Enemy phases clear prior damage numbers.

## Final native verification

[The complete receipt](native/verification.json.gz) records **18 captures,
59 input activations and two exact reloads**, with unchanged source hashes.
The run took **22.01 seconds wall time and 5.50 seconds CPU** at the requested
25% allowance and 30 FPS native cap. Its game and window closed on completion.

The fresh Wizard route checks all four title selections, 100%/125% text, Hero
icons, an Archer move/attack, one ordinary enemy phase and a Wizard basic shot.
The specialty battle and eight-relic inventory load fixed historically earned
saves; their preparation included autoplay and is documented in the receipt.
Four inventory pages show each relic once. These are directed presentation
checks, not independent first-run or campaign-depth evidence.

Key frames: [class selection](native/title-warrior.png),
[Hero at 125%](native/hero-wizard-125.png),
[specialty battle](native/earned-specialists-125.png),
[all miniatures](native/miniature-contact-sheet.png), and
[Wizard projectile](native/wizard-basic-projectile-125.png).

An earlier native review exposed a covered Brigand eye opening and an old
damage number at an empty hex after playback. Both were corrected before the
final capture and inspected in the final sheet and Wizard-shot frame.
All eighteen final frames were viewed across root and independent QA review;
no clipping, control overlap or persistent health-label obstruction was found.

## Integration and scope

[The final focused run](checks/integrated-tests.txt) passes **45 tests in
10.35 seconds**, paced between tests at 25%. It covers class identity, layout,
exact asset packaging, uniform miniature scaling, sound timing, scene lifetime,
preferences, saves, playback and real local socket co-op orders. The damage
transition and miniature scaling regressions first failed; their raw RED logs
are retained losslessly under [checks](checks/).

[Bounded Shardbound fuzzing](fuzz.json.gz) passes two model campaigns and two
scene runs with **297 scene inputs, 290 scene state checks and 210 model state
checks**, in 6.9 seconds at 25%. Both random campaigns end in defeat. No campaign
matrix, soak or packaged build was repeated. The separate
[Tribes check](checks/tribes-fuzz.txt) passes two AI games and two random-input
runs with no failures. Every test/native job ran serially and ended. This does
not establish audio
artistic approval, battery life, platform acceptance or release readiness.
**All G01–G19 remain incomplete.**
