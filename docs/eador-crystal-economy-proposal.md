# Optional crystal preparation: bounded evidence and decision

The accepted increment is **Tower infusion only**: spend 3 crystals and one
campaign action to restore up to 8 mana in a supplied, owned camp. A Mage Tower is
required. Battle, pending rewards, ended campaigns, full mana, insufficient funds
or actions, and encircled Westwatch block it. Passive recovery and all recorded
difficulty profiles remain unchanged. **HP treatment is not accepted for the game.**

This does not resolve G07. The purpose is an optional earlier-attack decision,
not a routine fee to drain surplus. No zero-action version is proposed: abundant
late funds would make that a largely automatic preparation click.

## Two hypotheses, before adding game rules

The read-only observer quoted Tower infusion (3 crystals / 8 mana), targeted
treatment (2 crystals / 12 HP per living combatant), and a competing party treatment
(4 crystals / 24 HP total, at most 12 each, most-wounded first). It executed neither
service. Quotes retained remaining actions and the rival's visible order.

The final bounded comparison uses seed 0 × 3 modes × 3 themes × 4 classes × 3 routes
× 5 paid plans: **540 campaigns**, all following unchanged orders. An earlier
5,400-run final-recovery-only observation is also retained; it is demand data,
not service-outcome evidence. Repeat seed-zero direct plans preserve all baseline
results, purchases and final-save hashes.

At the first affordable post-battle quote, 405/540 campaigns have one action left;
135 Scouts have two. In 48 cases, the one remaining action can reach an adjacent
rival. A one-action service therefore changes actual movement/interception timing.
At final recovery, actions have usually reset: an infusion can consume a spare
action and still permit the next attack. These different timings matter more
than whether a quote can technically be afforded.

Party treatment often has poor value at these measured points. Its first
post-battle quotes restore about 11–12 HP on average, against a 24-HP budget; the
same effect usually needs only 1.5–1.7 targeted orders. In the scattered-wounds
example below it eliminates five clicks, but it also bundles healing already
available from ordinary rest. Neither observation justifies shipping a healing bill.

## Concrete saved decisions

All examples come from actual paid campaign routes, with complete saved inputs in
[the retained examples](evidence/crystal-service-comparison.examples.json).

- **Pre-assault:** Standard Commander / Spells, turn 11 at `(1,0)`: 336 gold,
  35 crystals, full six-troop army, 6/18 mana and two actions. Infusion reaches the
  former 14-mana reserve and leaves an action for Duskspire. Its financial cost is
  modest; the decision is whether to attack sooner with less complete recovery.
- **Pursuit:** Accessible Commander / Economy, turn 6 at `(1,0)`: 172 gold,
  23 crystals, one action; adjacent rival at `(1,-1)` will attack `(0,0)` in one
  turn. The camp has Temple, not Tower. Building Tower costs 75 gold / 2 crystals
  and immediately adds 4 mana and Bolt access. Infusing afterward consumes the
  interception action, so that investment and its follow-up are distinct decisions.
- **Scattered wounds:** Accessible Economy turn 7 has five damaged combatants.
  Party treatment restores 24 HP for 4 crystals, versus five targeted orders for
  10 crystals. Ordinary rest can restore at least those same amounts. A party
  button would reduce clicks, but this is not evidence that buying it is wise.
- **Small wound:** An earlier turn-3 camp has one troop missing 8 HP. The party
  quote costs twice the targeted quote and free recovery can restore all eight.

## Executed non-production comparisons

The prototype applies the proposed service only to a cloned, validated save
payload. All subsequent building, waiting, travel and explicit automatic combat
use actual public game commands. Each of the **11 branches repeats exactly**.
There is no production HP-service implementation. Resting can change enemy timing
and battle terrain; the tables report complete outcomes rather than attributing
every difference solely to restored mana.

Pre-assault results, from the same saved army:

| Choice | Victory turn | Troops lost | Surviving army wounds | Hero HP | Crystals left |
|---|---:|---:|---:|---:|---:|
| Attack now | 11 | 5 | 25 | 34 | 35 |
| Infuse, then attack | 11 | 3 | 55 | 42 | 32 |
| Rest once, then attack | 12 | 2 | 55 | 18 | 38 |
| Rest to the old mana reserve | 13 | 1 | 69 | 48 | 41 |
| Party treatment, then attack | 11 | 4 | 48 | 40 | 31 |

Wound totals include only survivors: fewer wounds after losing five units is not
a better army. Infusion gives an earlier attack with intermediate attrition; it
does not dominate waiting. The party branch restores only six missing HP here.

Pursuit results, from the same saved army:

| Choice | Intercept turn | Troops lost | Surviving army wounds | Mana left | Crystals left |
|---|---:|---:|---:|---:|---:|
| Intercept immediately | 6 | 1 | 18 | 2 | 23 |
| Rest, then intercept | 7 | 0 | 19 | 8 | 26 |
| Build Tower, intercept now | 6 | 0 | 30 | 2 | 21 |
| Build Tower, rest, intercept | 7 | 0 | 19 | 12 | 24 |
| Build Tower, infuse, forced wait, intercept | 7 | 0 | 19 | 14 | 21 |
| Party treatment, forced wait, intercept | 7 | 0 | 15 | 8 | 22 |

Waiting yields `(0,0)` to the rival; the later successful interception recaptures
it. No permanent territorial loss is claimed at these endpoints. Infusing during
pursuit buys only two extra ending mana over Tower plus ordinary rest, with equal
casualties and wounds. Party treatment buys four fewer remaining army wounds over
ordinary rest. These are weak local purchases, demonstrating why the one-action
cost and an explicit preview matter.

## What remains scarce, and what does not

The late Economy example has **421 gold / 37 crystals** and six living troops.
A public attempt to recruit an affordable, unlocked Pikeman is rejected because
the army is full. There is currently no camp command to replace or release a
healthy troop. Most permanent building investments are already finished. Extra
gold cannot improve a full roster without losses, while carryover accepts only
two troops and bounded funds. Adding healing fees does not address that limitation.

After the opening, the observed scarce choices are movement/interception timing,
surviving veterans, army slots, equipment and linked contracts. Prices are often
not constraining. Site rewards plus territorial income can fund several hundred
gold by turn 8–11, and the [difficulty audit](eador-difficulty-candidate.md) still
finds large gold and crystal surpluses even with specialist replacement purchases.

A separate economy review should compare the value of a deliberate camp roster
replacement decision and the growth of site rewards/income against finite useful
investments. Do not add permanent stat purchases merely to consume a bank balance,
and do not silently retune gold growth inside this feature. Infusion is one optional
tempo purchase; it is not economic balance or player-enjoyment evidence.

## Implementation seam and validation

The bounded game interface is `State.infusion_preview()` returning a frozen
`InfusionPreview(mana, crystals, actions, blocked_reason)`, and `State.infuse()`
which consumes that quote or rejects with the same reason. `mana` is the capped
potential gain; a blocking reason must remain visible alongside it. This uses
existing HP/mana/currency/action fields, so it needs no new schema or framework
subsystem. Existing saves gain an optional command; their old passive rules and
non-infusion continuation remain unchanged.

Public tests cover earned Wizard and Scout purchases, capped restoration, exact
save continuation, an Adept competing for the same crystals, losing the last
travel action, battle/reward/blockade refusals, and the retained assault/pursuit
choices. The model does not claim native input coverage before root's UI work.

Evidence: [read-only comparison](evidence/crystal-service-comparison.json),
[exact comparison rows](evidence/crystal-service-comparison.rows.json.gz),
[executed prototype branches](evidence/crystal-service-prototype.json),
[earlier demand observation](evidence/crystal-service-demand.json).
The reports record distinct source hashes; historical prototype results are not
relabeled as outcomes of the later shipped command.

```sh
uv run python tools/audit_eador_crystal_demand.py --seeds 1 --report /tmp/crystal-service-comparison.json
uv run python tools/prototype_eador_camp_services.py --examples /tmp/crystal-service-comparison.examples.json --report /tmp/crystal-service-prototype.json
```
