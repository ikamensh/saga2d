# Shardbound icon controls — 2026-09-07

Recurring utility labels and resource/stat words are replaced with original
icons and numeric values. Primary orders, objectives, costs and consequences
remain in text. Shared Saga2D images, button icons and reactive tooltips support
the game-owned symbols and meanings.

## Native game check

[The complete receipt](native/verification.json) records a fresh seed-7 Wizard
journey: toolbar click/shortcut visits, icon/value hover, larger reading size,
disabled Heal and Pin, a legal Archer move/attack and two exact reloads. Its
104 recorded input events include pointer motion; 94 state checks, 46 tooltip
observations and 16 metric observations preserve exact game facts. The run
took 19.14 seconds wall time and 4.81 seconds CPU at the requested 25% allowance,
with the shared 30 FPS native verifier cap. The game was closed on completion.

All ten frames were inspected by the root and verification agents. The
[campaign](native/campaign-icons.png), [125% campaign](native/campaign-reading-125.png),
[battle](native/battle-icons.png), [disabled Heal](native/disabled-heal-tooltip.png)
and [disabled Pin](native/disabled-pin-tooltip.png) show legible values and
viewport-contained explanations. Hero and Save modal placements were also
inspected. Source hashes agree before/after capture and identify the runtime
bytes despite the worktree's uncommitted game changes at capture time.

A [supplementary native route](supplement/verification.json) opens the building
catalogue, autoplays the same fresh home battle and reaches its result and relic
choice. All three 125% panels were inspected. Its 12 key inputs took 5.44 seconds
wall time and 1.38 seconds CPU, and its screenshots preserve the resolved state.

## Regression checks

The shared journey caught two defects: scene entry reset larger tooltip text,
and an unavailable spell key entered aiming despite its disabled button. Both
were fixed, and the final mock journey passed. Disabled clicks and keys retain
both the campaign state and aiming state; tooltips remain 14/18 pixels at
100%/125% across scene changes.

The focused game/asset/packaging run passed 100 tests and found one old keyboard
test that expected unavailable Bolt to enter aiming. That test was migrated to
the new disabled-control behavior and passed separately in 0.13 seconds. Its
check that an invalid *available* spell target cannot become movement remains.
The original 101-case run and the final single-case result are retained in
[checks](checks/). The run used cooperative 25% pacing between tests.

The independent framework example passed native click, shortcut, disabled
input, modal ownership, reactive-name and image-cache checks; all four
[framework frames](framework/) were inspected. Forty-nine focused framework
tests passed. A subsequent regression caught body-style color being ignored;
the fix passes all four icon integration tests. Shardbound uses the same body
and default text colors, so this correction leaves its pixels unchanged.

The 34-icon build test checks repeatable output, transparent geometry, complete
package collection and corruption rejection. The [catalogue](icon-catalogue.png)
was inspected at 96 and 24 pixels. No icon composition runs during play.

The bounded Shardbound fuzz check passed two model campaigns and two scene
runs, with 294 scene inputs and 469 state checks. The two random campaigns end
in defeat; this is input/invariant evidence. The separate Tribes check passed
two AI games and two random-input runs with no failures. All expensive jobs
ran serially. No large matrix or soak was restarted.

This is directed development verification, not a human first run, balance
assessment, listening review or refreshed distributable. G01–G19 remain open.
