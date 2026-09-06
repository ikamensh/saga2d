# V9 development-plan audit

This is a read-only baseline at `cfaf982`, before extraction sites or the proposed
crystal-priced recruits. No rules, AI, existing campaign helpers or fuzzer were
changed. **G07 remains incomplete:** this is one conservative automated policy
per plan at the current difficulty, not proof of optimal play or three balanced
manual strategies. A fixed competent policy winning all runs establishes route
robustness, not difficulty balance or player enjoyment.

## Method

The [reproducible tool](../tools/audit_eador_economy.py) plays seeds 0–99 in all
three themes, all four classes and three plans: **3,600 complete single-shard
runs**. It calls actual State/Battle commands, follows the same direct itinerary
of four sites, explicitly uses tactical autoplay, intercepts a nearby visible
rival and makes the first offered reward/skill choice. It uses a recovered
Merchant Seal for later recruitment and restores the combat relic. Seed zero's
36 combinations are repeated and must produce identical records/save hashes.
All final states roundtrip through the real save parser.

The ordered plans are:

- **Economy:** Marketplace → Barracks → Swordsman → Temple.
- **Sustain:** Temple → paid Acolyte → Barracks → Swordsman.
- **Spells:** Mage Tower → Barracks → Swordsman → Temple.

After the ordered purchases, each fills empty slots with Swordsmen; sustain
keeps one Acolyte and replaces it when lost. The policy buys only when affordable
and never substitutes a different plan for a difficult seed. Before the final
approach it recovers to at most six missing health and within four mana of its
maximum. There is a 60-turn/40-assault-step safety bound; unfinished states would
be recorded, not called defeats or victories.

The [retained report](evidence/shardbound-economy-v9-2026-09-06.json) includes
source fingerprints, every purchase's turn and actual resource deduction,
recruitment counts, final roster/skills, upkeep, battle losses, mana, outcomes
and final save hashes. All source hashes stayed unchanged during the 33.89-second
run. No case reached the safety bound and no troops deserted.

## Results

Every plan won **1,200/1,200** runs. Means across matched seeds/classes/themes:

| Plan | Turns | Dead troops | Mana spent | Tactical retreats | Crystals spent / left |
| --- | ---: | ---: | ---: | ---: | ---: |
| Economy | 11.75 | 2.63 | 45.30 | 15 total | 0 / 43.56 |
| Sustain | 13.06 | 3.80 | 53.28 | 49 total | 0 / 47.90 |
| Spells | 13.53 | 2.47 | 68.04 | 1 total | 2 / 48.05 |

| Plan | Buildings, gold | Recruitment, gold | Upkeep, gold | Gold left |
| --- | ---: | ---: | ---: | ---: |
| Economy | 170.00 | 141.17 | 82.60 | 514.28 |
| Sustain | 110.00 | 159.82 | 95.35 | 525.39 |
| Spells | 185.00 | 138.45 | 96.02 | 495.22 |

Including retreat fees, total mean gold outlay was **394.02 / 365.99 / 419.49**.
The greater ending treasury of a slower plan includes extra income-producing
turns; it is not evidence that the plan generates more useful value.

On matched worlds, Economy finished sooner than Spells in **871/1,200** cases
(274 ties), but Spells lost fewer troops in 408 cases (521 ties). Economy was no
slower and lost no more troops than Sustain, with one strict improvement, in
**778/1,200** cases. It lost fewer troops than Sustain in 796 cases, but its
higher construction spending prevents claiming universal dominance.

The weakest measured combination was Wizard/Sustain: **18.58 turns and 4.00
losses**, versus Wizard/Economy's 14.50 and 2.78. Scout/Sustain was nearly as fast
as Scout/Economy (10.27 versus 10.25), but lost 4.64 versus 2.94 troops. The
Spells plan reduced losses most clearly for Scout (2.43); for Wizard it did not
beat Economy's losses (2.90 versus 2.78). Grouped results for every class and
theme are retained in the report.

## Findings and limits

**Crystals have no meaningful ongoing sink in v9.** Economy and Sustain spent
none; Spells spent exactly two in every run. All three finished with substantial
surpluses, up to 140 crystals. The model confirms that the Mage Tower is the only
crystal purchase. Future recruit prices may make an early crystal site useful,
but a handful of purchases alone will not necessarily consume this recurring
surplus. No balance change was made for this audit.

**Market-first is a strong measured speed plan, while Tower-first buys safety.**
The Tower plan's single tactical retreat and lower average casualties are a
concrete payoff, despite greater spending and time. The conservative mana
recovery threshold can penalize spell-heavy play, so these results do not show
that waiting this much is necessary for a competent player.

**Early support does not automatically buy sustain.** This plan pays for an
Acolyte before durable frontline troops and shares the hero's mana under the
current AI. It incurred more replacements and retreats. That does not isolate
the Acolyte's strength or disprove its [manual objective role](eador-roles.md);
build order, roster composition and automatic spell ordering are bundled here.
A useful next comparison would command support manually or change only its
purchase timing, keeping the other decisions fixed.

All plans eventually buy Barracks and Temple; the audit does not establish an
alternative to that military/healing core. It also excludes flank routes,
second skill paths, linked carryover, new extraction rewards and any future
difficulty choice. The roster and extraction increments should rerun relevant
comparisons on their own frozen candidate; these numbers must not be relabeled
as evidence for later schemas or release readiness.
