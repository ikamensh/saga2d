# Pack Hunt: an authored rout with a paid approach

Pack Hunt adds one adventure family to new Elderwild shards at `(-1, 1)`.
Its forest divider separates a compact army from eastern wolves while a
second group threatens the rear. The free approach preserves that central
deployment. Paying **20 gold** positions the same army north of the divider,
where it can concentrate fire before the pack closes. Both approaches face
the same six finite Wolves and award the recorded 55 gold, one crystal and
Storm Quiver by default. The two deployments count as one authored pattern.

There is no seal, escape action or short objective deadline: win by routing
the pack while keeping the hero alive. The existing rout exhaustion rule
still ends a battle after 80 rounds. The approach fee remains spent after a
retreat; the surviving pack keeps its wounds on the next attempt, even if
the player changes approaches. Victory pays exactly once.

The old Wolf Den keeps its own content ID, mechanics and guaranteed source
at `(-2, 2)`. Home Shrine, Border Watch, Supply Cache and Explorer's Camp are
preserved. A 100-seed Elderwild check verifies one Hunt and the required
sources. Generation inserts only the new site; saved province arrays are
never regenerated. This is the sixth authored battlefield family, not
completion of G05 or the twelve-pattern content floor.

## A small game-owned contract change

`EncounterSpec.objective` now states `rout`, `hold` or `extract` explicitly.
`Battle.create` constructs the corresponding existing `BattleObjective`;
it rejects an unknown authored kind. `AdventureApproach` and
`AdventureAttempt` continue to hold the selected deployment, costs and actual
reward. No new campaign-time, guard-removal or save fields were added, so
the existing schema 11 representation remains sufficient.

Approach validation follows the selected encounter's objective instead of
assuming every approach means extraction. It still requires the controlled,
unexplored origin, the hero's matching campaign position, the saved reward,
the finite defender roster and non-increasing enemy HP. Extraction's exits,
cargo and deadline remain checked. The same contract can represent a hold
approach when a later authored pattern actually needs one; none is added here.
Saga2D receives no strategy rules or scenario abstraction.

The retained real v11 Wolf Den fixture was generated from archived source
`53adf40`, played through its first enemy phase, then continued using that
actual source to record the expected result. It keeps the old Den and reaches
the identical complete campaign result after loading in the new model.
The existing real v10 Ruins/Tower fixture also continues exactly, excluding
only the schema tag. These are prior-code continuations, not current saves
relabeled with an older version number.

## Three purchased manual plans

The source and native verifiers use `tools/eador_hunt_campaign.py`:
`prepare_pack_hunt(state=None)` and `hunt_route(state, approach, orders_type=...)`
replay the same Commander army; `prepare_hunt_spears(state=None)` and
`spear_hunt_route` provide a distinct Warrior plan. Preparation uses ordinary
build, recruit, conquest and rest commands. A State-like input adapter buys
the same troops through visible controls; it injects no resources or units.

| Measured seed-seven plan | Commander, free | Commander, lure | Warrior, free spears |
|---|---:|---:|---:|
| Campaign arrival turn | 5 | 5 | 4 |
| Building gold spent | 100 | 100 | 45 |
| Recruitment gold spent | 98 | 98 | 80 |
| Additional entry fee | 0 | 20 | 0 |
| Rout round | 3 | 2 | 3 |
| Missing player HP before rewards | 20 | 16 | 39 |
| Mana spent | 0 | 0 | 0 |
| Player units lost | 0 | 0 | 0 |

The Commander has two veteran Militia, an Archer, a Warden and a Ranger. Free
play removes the rear pack first, then moves the Ranger around the forest's
blocked sight line to support the next focus target. The lured formation
removes two eastern wolves before contact, uses Guard on the remaining front,
and finishes the wounded pack with concentrated shots. The 20-gold fee buys
one fewer enemy phase and four HP in this pair. That is a modest benefit;
the free approach remains viable and retains money for realm development.
It is not evidence that paying is always optimal or safer for every army.

The Warrior replaces both support purchases with two Pikemen and needs only
the Barracks. Its earned Duelist attack finishes a wolf outright, while the
army uses spear positions, Brace and paired melee/ranged damage. It arrives
earlier and saves 73 preparation gold relative to the Commander army, but
finishes with 19 more missing HP than the Commander's free plan. Both are
complete public-command victories; neither is a whole-campaign balance claim.

Model journeys check each immediate attack forecast and roundtrip the entire
campaign after every order. Additional regressions cover a paid failed attempt
with one killed and one wounded wolf, a saved free retry against exactly those
survivors, no second reward, and rejection of altered objectives, origin,
hero position, missing attempt or missing defender data.

## Real controls and reliability evidence

`tools/verify_eador_pack_hunt.py` reuses the existing `PlayerOrders` rather than
implementing a second battle driver. It compares and cancels the briefing,
accepts the selected fee, executes each manual order through keyboard/mouse,
checks exact forecasts and save reloads, returns through the result/reward
flow and attempts a rejected repeat exploration. It records actual purchase
totals, wounds, commands, inputs, backend, source hashes and environment.

| Native plan | Input activations | Exact save/reloads |
|---|---:|---:|
| Commander, compact | 106 | 4 |
| Commander, lure | 95 | 3 |
| Warrior, spears | 102 | 4 |

All three Pyglet journeys ran at 1280×800 logical resolution on macOS 26.6.2
arm64, Python 3.13.2. Their briefings, deployments, post-enemy formations and
results were rendered and inspected. These scripted journeys are not human
first-run playtests.

The combined source checkpoint `e420797` passes **873 full tests**. Its
300 randomized campaigns cover 100 per theme, including 17 compact and nine
lured Hunt entries, with 47,373 state checks and 12,544 unchanged-state command
rejections. Twenty scene runs add 10,003 random input events, 20 battle reloads,
19 choice reloads and 45 result reloads. Seven victories and 293 defeats are
outcomes of this random robustness policy, not a difficulty verdict. Source
hashes remained unchanged throughout each run.

```sh
python -m pytest tests/eador/test_pack_hunt.py tests/eador/test_hunt_journey_scene.py -q
python tools/verify_eador_pack_hunt.py --plan compact --output /tmp/hunt-free
python tools/verify_eador_pack_hunt.py --plan lure --output /tmp/hunt-paid
python tools/verify_eador_pack_hunt.py --plan spears --output /tmp/hunt-spears
python tools/fuzz_eador.py --campaigns 300 --scenes 20 --events 10000 --steps 180 --report /tmp/hunt-fuzz.json
```

This tranche stops at Pack Hunt. Broken Observatory and the remaining
[adventure roadmap](eador-encounter-roadmap.md) are future work. No newer
package, long soak or release-readiness claim follows from these tests.
