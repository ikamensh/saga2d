# Adventure placement and discovery evidence

The game now varies complete site packages within western and central bands.
Selecting an unconquered province reveals its saved site; the Codex records
site and relic source provinces and marks cleared sources. Game rules, rewards,
conquest defenders and historical saved maps retain their existing semantics.

## Generation and saved worlds

`world-audit.json` compares 300 fresh worlds with the exact historical baseline:
Frontier, Elderwild and Ruins, Commander/Standard, seeds 0–99. It verifies
determinism, 600 exact historical/current reloads, unchanged non-site facts,
complete reward/guard packages, progression bands, reserved sources, connected
sites and at least two ordinary adventures adjacent to home. Each theme has
four distance-sorted geometric placement orders, versus one historically.
These are geometric orders, not completed player itineraries.

`baseline-worlds.json.gz` is the original retained pre-change generation,
SHA256 `ce949cade506f8d341c74abe4c082cff719afadd13dafaeccb497ab78617a6e0`.
The baseline generator was byte-identical at `1524c48` and `a7a6c50`.
The implementation under test has generator SHA256
`07042bd83c96edfcbbd5dfd2941dcc332932b4bc47f942112af510b57cdf5690`.
No historical snapshot was recreated using the new generator.

The audit-backed test passed in 4.07 seconds. The separate CLI passed in
3.7804 seconds wall / 0.9263 seconds CPU at its default 25% allowance.
`placement-red.txt.gz` retains the expected failure against the actual
pre-change generator: the named Frontier adventures did not change location.

## Native reading and existing saves

[The discovery reader](discovery-reader/README.md) retains eight inspected
native frames from five worlds, 186 actual inputs and five exact F5/F9 pairs.
The shared input regression passed before native execution. Neutral locations,
historical unchanged locations and the cleared Caravan/owned Merchant Seal
remain readable at the captured 100%/125% sizes. Native execution took
30.026 seconds wall / 7.600 seconds CPU at 25% and 30 FPS.

`discovery-red.txt.gz` and `discovery-green.txt.gz` retain the selected-province
and Codex regression's failing and passing runs. Browsing does not spend a
campaign action or change the saved model. Source/asset manifests identify
the exact tested bytes, including changes not yet committed at execution.

## Earned army consequences

Existing paid regression preparations now travel to the recorded source. They
must actually arrive with actions and recovered troops before starting the
named adventure; intervening rival battles cannot silently leave them elsewhere.

The Aerie preparation illustrates why identical packages do not mean identical
tactics. The varied route reaches the site on turn 11 rather than 9 and earns
a level-2 Skyrider instead of level 1. Enemy targeting changes, leaving an
Archer alive after the old northern script. A ready Pikeman now finishes that
Archer; the actual round-3 rout has 40 wounds, versus 34 historically.

Causeway's Scout now arrives on turn 6 at level 3 with 14 mana. Its old story
about waiting to reach eight mana no longer applies. From the same earned save,
the revised comparison escapes in round 4 with 41 wounds, or spends four more
mana on Heal, survives another enemy phase and routs in round 5 with 27 wounds.
These preparations include the existing development autoplay policy; they are
regressions of earned-state behavior, not independent manual campaigns.

[The migration review](migration-review/README.md) retains 90 distinct passing
checks over incremental repairs, every failed run and three bounded diagnoses.
[Screen input](screen-mock/README.md) separately retains all five passing mock
journeys, including the real 53-round defeat and paid replacement retry.
The final strengthened old-save Codex body-rendering check passes in 0.11
seconds (`codex-rendered-green.txt.gz`). These are focused incremental checks;
the full campaign crossproducts were deferred and never started.

## Paid route declarations

[The original declaration](route-declarations.md), `route-candidates.json.gz`
and the two `zero-order/` journals predate all commands in the declared routes.
The declaration's generator hash matches this implementation. `director.py`
records explicit public commands, reasons, forecasts, exact saved joins and
rejected attempts without silently rewinding. It authenticates the same fresh
linked campaign origins before the first purchase. Autoplay is disallowed.

The two plans choose different nearby rewards, troop costs, equipment and
adventure approaches. Their actual outcomes must be assessed separately from
the structural audit; preserving reward packages does not establish equal
access cost or tactical difficulty. These local routes cannot establish three
successful full-campaign strategies, general balance or release readiness.

Both declared routes reached their endpoint: [seed 5](route-seed5-outcome.md)
finished five battles on T3 with one action and 112g/10c; [seed 12](seed12-outcome.md)
finished six battles on T3 with no actions and 121g/14c. All six troops survived
in both, with 11/15 remaining wounds. The Seal saved 19g before the 20g guided
fee; the Boots route paid full recruitment prices and gave up Heal for the
free northern rescue. Both escaped in round 2 using Warden Swap. No elective
recovery, retreat, defeat or rewind occurred. Each journal retains one rejected
move with exact state unchanged.

The final companion input selection passes 23 checks in 96.24 seconds, excluding
one already-passed Relief retry. Bounded linked fuzzing on seeds 97–98 passes
two model and two scene runs at 100 random steps, with 227 model and 305 scene
state checks, 314 input activations and both actual model defeats retained.
It completes in 12.8 seconds at the default CPU allowance. This small run is
regression evidence, not the release soak or large acceptance matrix.

## Actual route input and screenshots

[Manual-input receipts](manual-input/README.md) retain both accepted command
chains through fresh New Campaign input at 125% text size. Mock execution
reproduces 219 commands and exact reload pairs with 901 inputs. Native execution
reproduces the same 219 pairs with 903 inputs. All 18 native PNGs were inspected;
the compact toolbar/stat icons, objectives, exit readiness and cleared sources
remain readable. Both native receipts authenticate 82 unchanged source files.

Seed 5 takes 44.899 seconds wall / 11.503 CPU; seed 12 takes 45.284 seconds wall /
11.577 CPU. Native verification uses the existing 30 FPS pacing and cooperative
25% CPU allowance, with only one expensive process running at a time. Games
close after execution. These are agent-directed local routes and silent native
input replays; human playtesting, audible review and release acceptance remain
open.
