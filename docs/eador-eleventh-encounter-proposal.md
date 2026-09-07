# Eleventh encounter candidate: Relief Column, revised

This is the historical detached proposal. The accepted production integration
and earned campaign evidence are recorded in [Relief Column](eador-relief.md).
The superseded prototype runner and its three dedicated budget tests have been
removed from current tooling. Its old displacement experiment assumes historical
fixed site locations; it is not the current production placement audit. The
[retirement record](evidence/relief-prototype-retirement/README.md) identifies the
removed checks. Both original reports remain unchanged, including the source
witnesses still used by production compatibility tests.

The original corner proposal is **rejected**. Independent review found that
four original units, after only the ordinary 60-gold Market preparation, won
round two with four moves followed by Guard. It did not require recruitment,
Pin, attacking or spells. The previous [compressed report](evidence/relief-prototype-2026-09-06.json.gz)
remains provenance for that rejected geometry, not acceptance evidence.

The revision moves the signal inward and pairs enemy **Rally with flight**.
It has paid manual holds for both assemblies and a smaller Scout army. A costly
seven-body passive enclosure remains a valid alternative and is retained as a
counterexample. No production site, reward, schema, battle rule or framework
interface changes are made. Independent review of this revision is still a gate.

## Distinction and its limits

Watch and Gate teach occupying and screening a seal; Observatory changes both
sides' sight lines. Crossing, Cache and Vault use escorted extraction; Explorer
starts with a separated carrier. Hunt divides ground pressure, Screen uses
Smoke and rescue, and Aerie introduces airborne access and counter-sorties.
See the [roadmap](eador-encounter-roadmap.md).

Relief's proposed decision is whether to **intercept support before slowing its
flyer, absorb the landing and displace the next contester, or pay for enough
bodies to close every landing cell**. Leaving a Militia at one or two HP matters:
it can Rally away Pin before the Skyrider moves over the front screen. A
stronger Archer's full shot must finish that support while a weaker Archer
provides Pin. This support/control interaction is directly played and differs
from merely shooting or bracing Aerie's airborne attackers.

The overlap is real: the hold objective is familiar, and Aerie already combines
flight, Pin and Repulse. This should become an eleventh family only if players
actually notice and use the support/landing decision. If it reads as another
Watch with an Aerie flyer, reuse the result as a variant of an existing family.
The number of encounters does not establish G05 depth or release quality.

## Proposed board

A radius-three board, 37 cells, has a **plains signal at `(0,-2)`**, with all six
adjacent cells present. Hold it for two consecutive uncontested enemy phases
by the end of round four. Rout remains an alternative; hero death loses.

Marsh is at `(-1,-2)`, `(1,-3)`, `(-2,-1)`, `(-1,-1)`, `(-1,0)`, `(-1,1)` and
`(-1,2)`; everything else is plains. Both assemblies retain exactly that terrain
and the same finite roster: Skyrider `(3,0)`, Militia `(3,-1)`, Archer `(1,2)`,
Dread Guard `(2,1)`. Neither approach charges a fee.

| Assembly | Hero, then army in actual saved roster order |
|---|---|
| Western staging | `(-3,0), (-2,0), (-3,1), (-2,-1), (-1,-2), (-2,1), (-3,2)` |
| Forward interception | `(-1,-1), (0,-1), (-2,-1), (0,-2), (-1,-2), (-2,0), (-1,0)` |

Forward can reach and finish the support before it Rallies. Western receives
the first landing, then has to clear/displace contesters before the last two
scoring phases. Actual army markers and those consequences must be visible
before entry; no troop capability is inferred from an army-slot number.

## Paid manual plans

All purchases come from ordinary Standard seed-seven play through
`prepare_control_watch`; the original campaign remains exact while the
proposed battle is played separately. Commander buys Pikeman/Warden/Adept
(317 gold, four crystals including prerequisite buildings; seven bodies,
level two, turn six). Scout buys Pikeman/Archer (235 gold, no crystals; six
bodies, level two, turn four). The original two Militia and veteran Archer
remain. These are complete preparation costs, not just the last recruit price.

| Same prepared party where indicated | Win | Missing HP | Mana spent |
|---|---:|---:|---:|
| Commander, forward | Hold round 2 | 50 | 4 |
| Commander, forward with Heal | Hold round 2 | 28 | 8 |
| Commander, western | Hold round 4 | 50 | 8 |
| Commander, western with Heal | Hold round 4 | 28 | 12 |
| Scout, forward | Hold round 2 | 44 | 0 |
| Commander, complete passive enclosure | Hold round 2 | 40 | 0 |

All these plans retain every arriving unit and leave enemies alive. Forward
uses Pin on the Skyrider and Bolt/Militia/Adept damage to finish its support,
then kills the slowed flyer. Its optional Heal repairs the exposed Militia.
Western uses Brace to receive the landing, eliminates the Skyrider and support,
then moves the wounded Pike off the signal. The Adept enters the signal and
Repulses the remaining Guard; the other units close its ground routes. A
last-phase Heal restores 22 HP to the Pike.

The two healed Commander routes end with 28 wounds, but distribute them
differently. Forward ends with Pike 18 HP and Adept 10 HP; both Militia, Warden
and hero remain full. Western ends with Pike 24, Militia 18/20, Warden 32 and
full Adept/hero. Western spends four more mana and two more battle phases;
there is **no claim that it is equally efficient or universally preferable**.
It is an alternate deployment demanding a different solution, with a healthier
Adept afterward. Actual campaign recovery costs are not measured by this
detached prototype.

Scout uses the fresh Archer's Pin and the veteran's stronger full shot to
finish the Militia. Its veteran takes the Guard's attack while the fresh
shooter survives the flyer. On turn two, the fresh Archer and Militia rotate
into the exposed flank; three ranged shots finish the Skyrider. It needs no
spell or seventh unit.

## Counterexamples are part of the result

- The exact old four-body corner orders now fail for all four hero classes:
  Commander, Scout and Wizard lose their hero in round four; Warrior reaches
  the deadline without scoring. The only purchase in those preparations is
  the 60-gold Market.
- Moving the signal inward **without** the flyer also failed design review:
  four bodies still blocked the sole ground approach. That intermediate board
  is discarded; it is not a second successful prototype.
- Seven bodies can still occupy the signal and all six adjacent cells before
  the first phase. The retained explicit plan wins round two with 40 wounds
  and no mana. This is valid paid counterplay, not prohibited by a special
  rule. A bounded search also finds a 36-wound passive win. The healed active
  line buys fewer wounds for eight mana; the unhealed active line is worse
  than that passive alternative on the measured totals.
- With exactly the same first Commander Pin, omitting the final two damage
  leaves the support alive. It Rallies the Skyrider, which lands at `(1,-2)`
  and prevents the first score. Continuing only to Guard loses the deadline
  and the Pike. Switching to automatic play instead routs at round four but
  still loses the Pike; the initial mistake does not force defeat.
- Swapping the Scout Archers' jobs leaves the Militia at one HP. It Rallies
  the flyer and breaks the expected first score. This is an exact damage and
  control allocation difference, not disabled enemy abilities.
- Omitting western Repulse and the moves it enables misses the deadline
  without losing a troop. The contester remains beside the signal; survival
  alone does not satisfy the objective.

The deterministic passive search samples 1,000 initial assembly/movement orders
for each of four four-body hero parties, paid Scout and paid Commander, in both
approaches: **12,000 trials**, then Guard through the actual terminal result.
There are no wins in the four-body or Scout samples. Commander forward wins
29/1,000 (36–69 wounds); all other samples lose. It permits static Guard and
ordinary retaliations, but never attacks, casts, Pins or repositions on later
turns. This is a bounded countersearch, not proof of minimum army size or an
optimal strategy. The best sampled win and its exact moves are retained.

Automatic baselines are reported separately. Commander forward routs in round
four with 63 wounds, 16 mana and two troop deaths; western routs in round four
with 50 wounds, 12 mana and one death. Scout routs in round four with 43 wounds,
eight mana and one death. Manual control changes survivors as well as outcome
and resource use. These are one prepared seed per party, not a balance matrix.

## Safe source proposal

Do **not** replace a fixed Frontier coordinate unconditionally. In seed two,
central `(0,0)` is the only ordinary Tower route to Ember Lens. Keeping that
reward behind a harder Relief would preserve the relic set but remove its
existing cheaper encounter route.

Instead, consider only ordinary Frontier cells at `q >= 0`, in sorted coordinate
order, excluding every fixed site, capital and the western fallback `(-2,1)`.
Choose the first candidate with another unchanged province that has the same
site kind and exact `(gold, crystals, relic)` reward, lies no farther east, and
has a subset of the original site's guard multiset. Inherit the replaced
province's exact reward. Its province guards, terrain, income, ownership and
conquest routes remain unchanged; exploration stays optional.

Across 1,000 seeds this selects `(0,0)` 674 times, `(0,1)` 218, `(1,-2)` 93,
`(1,-1)` 14, and `(1,0)` once, with no gaps. Every selection retains a recorded
ordinary duplicate with no larger site roster. Eight eligible cells draw from
six ordinary kinds, so a duplicate exists under the current generator; choosing
the eastern member also accounts for the extra eastern Guard. This protects an
ordinary reward alternative, not a claim of identical optimal travel costs.
All fixed sources and the twelve-relic three-theme union also pass 1,000 seeds.

Production would install exactly the four proven defenders, avoiding `_site`'s
extra eastern Guard. Existing loaded province arrays and reward values must
remain exact. The briefing and Codex must describe the **saved variable reward**,
not promise a fixed Drum from `SiteSpec`. The prototype installs no location.

## Historical reproduction and acceptance at that snapshot

Reproduce the original experiment only in its isolated historical checkout:

```sh
git worktree add --detach /tmp/shardbound-relief-4608d1e 4608d1e988bd630b0c302712160c97ad9a913584
cd /tmp/shardbound-relief-4608d1e
uv run --extra dev python tools/prototype_eador_relief.py --output /tmp/relief-revised.json.gz
uv run --extra dev python tools/prototype_eador_relief.py --interactive scout
```

This is an explicitly scheduled historical experiment, not a candidate test.
The original runner predates its later CPU-budget change and includes the full
12,000-trial search. It was not rerun when retiring the superseded tool.

The report contains purchased campaign snapshots, orders and complete Battle
reloads, immediate attack/Pin/spell/Repulse forecast checks, passive
counterexamples and source-selection witnesses. At this snapshot, remaining
acceptance included independent review, production finite retry/reward-once/old-save tests, actual paid
travel to the selected source, alternate seeds/modes and native pre-entry/input
verification. Their later production implementation is linked above; the
12,000 static-screen trials did not substitute for those checks.

The [revised retained report](evidence/relief-revised-prototype-2026-09-06.json.gz)
was produced from clean source `4608d1e988bd630b0c302712160c97ad9a913584`. All
80 recorded source hashes match that commit. It retains 415 explicit
manual orders and exact Battle reloads, 15 separately labeled automatic
phases (including recovery after missed support), 12,000 bounded static-screen
trials and all 1,000 source-selection witnesses. The 75 existing control, Pin
and objective regressions pass on the merged source. The 59,249-byte
gzip has SHA-256
`f12a78c3a9ac1e0737d1c0b4561f6986353c1c208f13da7a088908c8524167c9`.
No native or installed-site acceptance is claimed.
