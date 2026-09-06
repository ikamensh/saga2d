# Veteran upkeep: reject the rank tax

The bounded experiment does not support automatic veteran wages as a late-economy
repair. It changes early and recovery decisions before making the late treasury
scarce, and creates an incentive to retire healthy experienced troops for lower
wages. No production rule, frozen difficulty record or save schema changed.

## Tested rules and scope

Two coefficients were tested: normal upkeep plus **1** or **2 gold per rank above
one**, per troop per turn. Rank-one troops pay exactly their existing upkeep.
After both variants left late production profitable, one paired variant capped
raw realm gold at **40 before the existing mode percentage**, using the +2 wage.
There was no further coefficient or ceiling sweep.

The same nine selected paid cases from the
[prior study](eador-late-realm-proposal.md) run each variant: three paid plans in
Standard Commander/Frontier, Challenge Commander/Frontier, and Standard
Scout/Elderwild. These are 36 disclosed automatic campaigns, each repeated
exactly, not a broad balance matrix. The runtime experiment uses the production
desertion priority and discharges each deserter's complete experimental wage;
merely changing total upkeep while subtracting only its old base cost would
miscount bankruptcy. No game implementation was changed to do this.

## Where the costs land

Even **+1** delays the actual Standard Economy Temple from turn 3 to turn 4. The
original two-gold remainder cannot cover the unavoidable rank increases earned
by the initial battles. The three Standard plans still finish in the same
12/13/13 turns and with the same 2/3/1 combat deaths.

| Same selected cases | Gold remaining range | Changed completion turns |
|---|---:|---:|
| Ordinary | 252–494 | baseline |
| +1 per extra rank | 219–414 | none |
| +2 per extra rank | 186–341 | none |
| +2 and 40-gold production cap | 186–294 | none |

The stronger wage does affect one army outcome: Challenge Economy loses four
rather than three troops while still winning on turn 10. The report retains
actual changed purchases, rather than calling this a free budget improvement.
None of these fixed campaign policies deserted troops. This does not imply
that the new wages are safe for arbitrary recovery or spending plans.

## Actual recovery and bankruptcy choice

A publicly played campaign wins its first shard, deliberately loses Rootward
by neglecting the capital, and recovers with **60 gold, two rank-three Swordsmen
and one rank-one Militia**. No army or funds are injected. The following public
commands expose a real difference:

- Under ordinary Challenge rules, three rests raise enough money to buy Mage
  Tower, leaving 6 gold. With +1 wages the treasury reaches only 69; with +2 it
  falls to 57. Both therefore refuse the same purchase without mutation.
- Clearing the existing home Shrine first earns 45 gold. Every variant can then
  buy Tower immediately and retain 30 gold. The actual battle leaves the same
  three living troops and full hero HP. This is a viable proactive alternative,
  not a higher treasury supplied by the experiment.
- Buying Barracks for 45 and Militia for the actual discounted 14 instead leaves
  **1 gold**. With +2 wages, income 12 faces upkeep 14 and the next-turn preview
  warns of a one-gold shortfall. The new Militia deserts on the next turn and
  the original rookie on the following turn. The two veterans remain, billing
  exactly the capital's 12-gold income. After four turns: no gold, two troops.
- Shrine first, then those same purchases, keeps all four troops through the
  same four turns and leaves **38 gold**. Ordinary wages keep all four without
  the Shrine, leaving 25; +1 leaves 9. The paired ceiling does not affect this
  capital-only case.

This creates a comprehensible scarcity decision, but its force lands on an
already constrained recovery expedition. It does not explain why automatic
experience should finance the repair of a rich late realm. Ordinary rest remains
available; the experiment does not introduce a payment button or healing fee.

## Healthy-veteran retirement becomes a financial tactic

From the retained full paid army, compare keeping the first rank-three Militia
against the existing same-role replacement. Replacement costs **14 gold and one
action**, permanently discards its rank/XP, and changes maximum HP from **32 to
24**. Four following public idle turns have no intervening hero battle:

| Rule | Keep: gold after four turns | Replace: gold | Replacement difference |
|---|---:|---:|---:|
| Ordinary | 585 | 571 | −14 |
| +1 | 545 | 539 | −6 |
| +2 | 505 | 507 | +2 |
| +2 with cap | 461 | 463 | +2 |

The +2 salary pays back the entire purchase after four idle turns. This is **not
an infinite duplication exploit**: a fresh rank-one troop cannot be retired
again to obtain another wage reduction, and lost combat strength/actions remain
real. It is an undesirable new reward for discarding automatic progression if
cash is the objective. In the retained one-action pursuit state, replacement
still consumes the interception action and Heartwood is actually lost on the
following rival operation; lower wages do not remove that opportunity cost.

## Recommendation and concrete next design

Reject the rank tax and the paired cap as production candidates. Army capacity
and rank cap limit the number of recurring expenses, while captured territory
and ordinary recovery continue producing resources. Increasing a salary tied to
automatic XP reaches the vulnerable opening and recovery before it constrains
the wealthy late army. A smaller ending number alone is not a better economy,
and not every unused coin at a finite game's ending is a failure.

The next bounded design is **departure cargo**, already accepted for a prototype:
use one of the existing two troop carry slots for a paid gold chest instead of a
veteran. It could turn late wealth into next-shard funding while sacrificing
military carryover. Compare ordinary two veterans, one veteran without cargo,
and one veteran with cargo through actual later purchases and battles. One
transparent price/grant, explicit forfeited identity, and no extra carry slot;
no recurring clicks or automatic tax on earned XP. This is a hypothesis, not an
implemented order or a claim to solve standalone G07.

[Source](../tools/prototype_eador_veteran_upkeep.py) and
[retained evidence](evidence/veteran-upkeep-prototype.json) use clean source
**a0995fa** with unchanged game/helper fingerprints. They include both actual
recovery inputs, complete purchase records, saved retirement/scarcity branches,
visible shortfalls, exact costs and variant identities. Public checks repeat
all results; no native/UI or new production-save compatibility claim is made.

```sh
uv run python tools/prototype_eador_veteran_upkeep.py --report /tmp/veteran-upkeep.json
```
