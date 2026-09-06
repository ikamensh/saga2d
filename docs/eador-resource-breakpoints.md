# Resource attribution and investment breakpoints

This bounded diagnosis identifies a narrower G07 issue than “large final treasury.”
The established plans finish buying their buildings and fill the army while real
alternative investments still compete for money. Later, income and rewards continue
but those policies buy almost nothing except casualty replacements. Crystals become
particularly detached from these policies: most come from automatic province yield,
while these three plans use only the Tower's two-crystal construction cost.

I recommend testing one purposeful **multi-role investment at the earlier breakpoint**
before changing gold rules. The quoted costs still require a choice there. A second,
conditional direction is new-world crystal-source specialization; it needs evidence
that a player actually wants the magic investment before relocating its supply.
No new tax, production mechanic, profile, save field or currency rule is implemented.

## Sample and what “affordable” means

Source **2e34e61**. Seed 0 Commander, direct route, economy/sustain/spells, all three
themes and all three current modes: **27 campaigns**. All win on turns 9–14. Each
observer output equals its unobserved `DifficultyTrial` output, including purchases,
turns, casualties and final-save hash. This is a representative first sample, not a
new hundred-seed balance matrix or evidence about all hero classes. Commander also
earns recruitment discounts; the quoted prices are his actual current prices.

The [observer](../tools/audit_eador_resource_breakpoints.py) reconciles every gold and
crystal change. End-turn production is captured **before** rival movement changes
ownership, then actual surviving-army upkeep is separated. Battle rewards, paid
approaches, duplicate relics, sales, services and replacement purchases have separate
categories. Empty categories mean these policies did not execute that purchase;
they do not imply the feature is missing or useless.

At every settled public command, detached saved copies try the actual offered
orders: unbuilt buildings, a missing-role recruit or replacement including its
building prerequisite, needed infusion and a local paid approach. Each rejected
command leaves its copy exact. The real campaign stays unchanged. At capacity, the
replacement quote uses the lowest-rank/XP/ID survivor and records its lost rank/HP;
this is a price quote, not a recommendation to discard that troop.

Two distinct breakpoints avoid conflating affordability with strategic value:

- **Individual orders:** after the last money refusal, every currently available
  quoted option is individually affordable for the rest of this executed policy.
  Action and other nonfinancial blocks are separate. This does not mean the player
  can buy every option together or wants every absent role.
- **Catalogue upper bound:** all remaining buildings **plus** the most expensive
  absent role can be bought together, with a legal action available if replacement
  is required. This deliberately generous bundle is a financial bound, not an
  asserted desirable build.

| Theme | Individual orders stop meeting funds refusals | Catalogue upper bound | Actual victory |
|---|---:|---:|---:|
| Frontier | turns 5–6 | turns 7–9, all 9 cases | turns 9–14 |
| Elderwild | turns 5–8 | turns 8–11, 8 of 9 cases | turns 10–14 |
| Ruins | turns 5–6 | turns 7–8, all 9 cases | turns 10–13 |

The exception matters: Standard Elderwild Sustain wins on turn 11 with 232 gold,
but never has enough at a legal action point for its 250-gold upper-bound bundle.
Gold is not globally irrelevant just because the ending has unused money.

## Where the resources came from

Totals below cover the 27 actual runs. Both currencies reconcile exactly.

| Source or expenditure | Gold | Crystals |
|---|---:|---:|
| Initial grants | +2,880 | +108 |
| Recurring province/Market income, gross | +9,411 | +778 |
| Site rewards | +5,085 | +216 |
| Conquest rewards | +3,075 | 0 |
| Expedition/defense rewards | +1,025 | 0 |
| Duplicate relic conversion | 0 | +72 |
| Markets, economic investment | −540 | 0 |
| Barracks, military infrastructure | −1,215 | 0 |
| Temples, support/healing infrastructure | −1,755 | 0 |
| Towers, magical infrastructure | −675 | −18 |
| Troop recruitment | −4,373 | 0 |
| Actual upkeep | −2,389 | 0 |
| **Remaining treasury** | **10,529** | **1,156** |

Gross earned gold, excluding starting funds, is **51% recurring income and 49%
finite rewards**. After deducting upkeep from recurring income, its share of net
earned gold is **43%**. A blanket province-income diagnosis would miss nearly half
the gross proceeds and more than half the net proceeds from actual fights/sites.

Crystals differ: **73% recurring yield, 20% site rewards, 7% duplicate relics**.
The only crystal expenditure in these policies is nine Towers. They never buy a
crystal-priced troop, take a paid approach, infuse or replace a troop. Existing
[earned infusion](eador-crystal-economy-proposal.md) and [replacement](eador-army-replacement-interface.md) evidence
already demonstrates those choices can matter tactically; absence from this policy
is not evidence against those results.

Spending by plan is also different. Across each plan's nine runs, Economy spends
1,530 gold on buildings and 1,530 on troops; Sustain spends 990 and 1,434; Spells
spends 1,665 and 1,409. Sustain's lower building bill leaves the highest aggregate
ending gold (3,895 versus Economy 3,454 and Spells 3,180), despite its higher upkeep.
There is no universal “Market explains the whole surplus” result here.

After the **individual-order** breakpoints, the combined remaining game produces:

- 5,831 gold recurring income, minus 1,476 upkeep;
- 3,270 gold from site/capture/expedition rewards;
- 562 gold spent on troops and **no more building purchases**;
- 559 recurring crystals, 26 site crystals, 16 duplicate crystals, **zero crystal
  spending**. Recurring yield is 93% of those late crystal receipts.

The problem is therefore both continuing inflow and absent desired purchases. These
data do not justify adding a fee merely to consume the 7,063 additional gold kept
after that breakpoint.

## Three concrete states

**Frontier, Standard, Economy.** Temple is purchased on turn 3 from 67 gold,
leaving **2**. The initial full army is reached on turn 5 at **46** gold. The
individual-option breakpoint is turn 6 at **144 gold / 21 crystals**, after claiming
the eastern province, with **one action** left. A Sapper/Adept/Skyrider conversion
would still require **223 gold / 8 crystals / three replacement actions**, including
the missing Tower. The player cannot simply buy that whole army now. All remaining
buildings plus one absent role become affordable only on turn 8 at 218 gold.
The realm ends turn 12 at 487 gold: 100 start + 370 recurring income after upkeep
+ 185 sites + 100 conquests + 25 expedition − 170 buildings − 123 recruitment.

**Elderwild, Standard, Sustain.** Turn 6 has **134 gold / 16 crystals**, five troops
and one action. Individual new roles are affordable, but the complete unused
building/role bundle never is. The plan actually spends 219 gold on troops over the
shard and ends with 232. This is a useful scarcity control against claims that every
late purchase is trivial.

**Ruins, Standard, Sustain.** Turn 5 has **161 gold / 19 crystals** after the Aerie
reward. Two captured core provinces already produce **24 gold and 4 crystals per
turn**, in addition to Westwatch's 16 gold; no Marketplace is involved. On turn 7,
251 gold can cover the 250-gold catalogue bundle. The run eventually receives 48
recurring crystals, against 8 site crystals, and spends none. Ruins' three direct
checkpoints each have a guaranteed 12-gold/2-crystal yield, so the ordinary conquest
route buys both kinds of production together. Across all nine Ruins runs, recurring
crystals total 384, versus Frontier 201 and Elderwild 193.

## At most two targeted next experiments

1. **Test an intended multi-role army at turn 5–6, using existing rules.** The
   Frontier example still lacks 79 gold and two actions for the complete control
   conversion. Compare a purposefully chosen smaller conversion, waiting to fund
   all three roles, and keeping the veteran army through the same next objective
   and visible rival operation. Use an encounter where Smoke, Repulse or flight
   actually changes the plan; preserve normal prices, retirements and recovery.
   The question is whether existing scarce money already forces a worthwhile
   military/magical choice once the policy wants more than replacement Swordsmen.
   Reject it as an economy answer if the bundle has no tactical value, or waiting
   always buys everything without an opportunity cost. This is the recommended
   next bounded public-command comparison, not a new spending feature.
2. **Only if paid magic demand is established, test source specialization in new
   Ruins worlds.** Preserve the home and early western opening, all fixed sites,
   ordinary rest, gold yield and the world's total crystal-production potential.
   Move a bounded portion of guaranteed central crystal production to a guarded
   off-road magic location, rather than the already weak safe flank. The proposed
   choice is a productive gold route versus obtaining crystals for an actually
   useful paid army/infusion plan. Old province arrays must remain exact on load.
   Reject the experiment if it merely reduces unused inventory, makes the detour
   compulsory for all viable plans, or removes the reason to brave the core guards.
   No world-generation edit or counterfactual outcome is claimed in this report.

The existing [rejected remittance/outpost](eador-late-realm-proposal.md),
[rank-wage](eador-veteran-upkeep-proposal.md) and [deferred cargo](eador-departure-cargo-proposal.md)
results remain relevant. None establishes that another global tax would improve
the decisions observed here. G07 remains open; neither this sample's 27 wins nor
its accounting closes the full acceptance criterion.

## Reproduce and inspect

```sh
uv run python tools/audit_eador_resource_breakpoints.py
```

The [summary](evidence/resource-breakpoints.json) records source hashes, aggregate
flows and all modes/themes/plans. Its linked compressed rows retain each public
command delta, point-in-time quote, rejection reason, complete breakpoint save and
unchanged baseline outcome. All 30 recorded source files remained unchanged during
the measured run. There are no unsupported accounting residuals, no invented gold
recovery, and no live-game mutations from the quote probes.
