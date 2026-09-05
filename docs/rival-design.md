# Shardbound: finite rival expeditions

The rival owns a treasury and a single persistent expedition. It chooses an
operation, publishes its next destination and countdown, then executes the
operation when campaign turns pass. This replaces the old scheduled province
flips. These rules are game content in `eador/rival.py`; Saga2D supplies hex
geometry and route finding, with no strategy-game opponent abstraction.

## Public state and player commands

`state.rival` exposes `gold`, `pos`, `army`, `intent`, `target`, and
`turns_until_action`. Each army member has a stable `id`, `kind`, `hp`, and
`max_hp`. The target is the next operation's destination, not a promised final
campaign objective. Countdown means campaign end-turns until execution.
`income(state)` and `upkeep` explain its next treasury change.

| Intent | Meaning |
|---|---|
| `attack` | Enter an adjacent hostile province after the announced delay. |
| `march` | Move to an adjacent controlled province. |
| `return` | Bring depleted survivors back toward Duskspire. |
| `recover` | At Duskspire, spend one gold for each restored health point. |
| `recruit` | At Duskspire, pay for one replacement soldier. |
| `watch` | Wait for money or a worthwhile route; reassess after the countdown. |
| `defeated` | Duskspire has fallen and the campaign is complete. |

Existing player commands suffice. `travel(rival.pos)` starts an `intercept`
battle. If the expedition reaches the hero, an ordinary `defense` battle
starts. Beating an expedition stationed over a garrison leaves that separate
garrison to defeat; the result says so and the hero stays in the origin
province. Garrison conquest and site exploration also retain enemy casualties
when the player retreats.

## Resources and consequences

The opening expedition has six soldiers: three guards, two archers and a
brigand. It begins at the rival outpost with 60 gold. Its initial three-turn
warning gives the player time to begin realm development. Army upkeep costs
two gold per soldier; controlled province income funds replacements. Guards
cost 45, archers 35, brigands 20. Capturing a rival province removes its income.

Expeditions fight neutral garrisons with `Battle.clash`, a hero-free entry point
into the same tactical movement, terrain, attack, retaliation and AI rules.
Casualties and wounds persist. A newly occupied province may receive one
surviving soldier transferred from the expedition; occupation never clones a
garrison. The expedition returns along routes that prefer controlled land
when reduced below three soldiers or below 45% total health. Healing and
recruitment occur only at Duskspire and debit actual treasury funds.

Destroying the expedition clears its soldiers and opens a four-turn interval
before the first paid replacement appears at Duskspire. A replacement gets a
new identity. Victory therefore creates a practical counterattack window;
it does not immediately restore another full army.

After losing an expedition, the rival checks an intended encounter against
the hero with the existing deterministic battle rules. It avoids a predicted
losing hero assault, excludes that province from the whole route, and seeks
other territory. This prevents both repeated safe experience rewards and a
route loop where it repeatedly approaches a target it will refuse to attack.
It is a compact AI decision rule, not an assurance that auto-play predicts
optimal human tactics.

## Encirclement and unpaid upkeep

`state.encircled` is true while Westwatch is player-owned and all three of its
neighboring provinces are rival-owned. Capturing the last open neighbor logs
the warning; reclaiming any neighbor logs restored supply. The income and
recovery effects apply on the player's next end-turn, allowing a breakout
before another bill falls due.

Encirclement stops Westwatch's gold and crystal production, including the
Marketplace bonus. `income` and `crystal_income` expose effective production;
other controlled provinces continue producing. A hero inside encircled
Westwatch receives no army/hero health or mana recovery, including Temple,
relic and skill recovery bonuses. Recovery outside Westwatch continues.

`upkeep_shortfall` reports how much of the next army bill cannot be covered
by current gold plus effective income. If the player ends that turn without
restoring supply or earning funds, troops desert until the remaining army's
upkeep is affordable. Departures prioritize lowest level, then lowest XP,
then highest upkeep, then newest identity. Each departure is logged, and
the remaining bill is paid normally. The treasury never becomes negative
and is not silently clamped. These are derived rules; no save fields or
schema version change are needed.

A passive Marketplace camper now loses production, exhausts its treasury,
suffers lasting desertions, and can lose to the rival's real expedition.
Winning a breakout restores production and recovery. The rival still avoids
a well-funded army it expects to lose against; taking other land creates
the pressure rather than free reinforcements or automatic health damage.

## Persistence and evidence

Save schema 3 records treasury, plans, countdowns, stable soldier identities,
and remaining garrison/site health. Versions 1 and 2 migrate explicitly.
Legacy pending defenses preserve their exact tactical units, health, movement
flags and continuation; the newly introduced expedition is placed at a
consistent neighboring origin. Unsupported versions and inconsistent operation
or soldier identities raise `SaveFormatError` before loading a live campaign.

Public-command regressions in `tests/eador/test_rival.py` cover neutral
attrition, saved interception/retreat/reengagement, paid return/recovery,
replacement identities, defense counterattack windows, legacy pending choices
and battles, and damaged saves. A funded fortified-capital save from the
pre-pressure rules isolates the routing regression: while its treasury
lasts, it earns no repeat defense reward and the rival conquers the other
provinces before watching. The existing 32 seeded economic campaigns across all
four classes still win by exploring, investing and intercepting the announced
threat; leaving Westwatch undefended still loses. Those are bounded regression
strategies, not a claim of broad balance or release readiness.

The final client suite at `915dd40`, including main `643648a`, passed 431 tests.
The updated stress driver passed 100 model campaigns and 12 scene runs: 11,730
model state checks, 2,096 paired saved battle rounds, 511 saved choices, 3,092
unchanged rejected commands, and 2,153 random scene inputs. Forced cleanup
departures are counted separately because the rival deliberately avoids
repeatedly attacking an unbeatable camper. The source fingerprint and actual
metrics are in `docs/evidence/shardbound-rival-stress-2026-09-05.json`.

At pressure source `2f6451a`, the full suite passed 437 tests. The pressure
regressions play blockade, Marketplace starvation, an injured breakout,
remaining outpost production, saved shortfall/departures, and capital defeat.
The existing economic journey also completed 400 victories (seeds 0–99 across
all four classes). That is one proactive policy across four classes, not
three distinct economic strategies or a complete G07 balance audit. Reproduce
with `runpy.run_path('tests/eador/test_model.py')` and call
`test_each_hero_can_complete_a_campaign_by_exploring_and_investing(seed, hero_class)`
for those seeds/classes.

A fresh pressure stress run passed 100 random model campaigns and 12 scene
runs, including 2,088 random scene inputs, saved decisions/battle continuations,
and separately counted forced cleanup. Its source hashes and actual metrics
are in `docs/evidence/shardbound-pressure-stress-2026-09-05.json`. Root-owned
UI still needs the pressure/shortfall warning and real-input breakout check.
These increments advance G06/G13; they do not complete the Early Access
criteria or replace the previous baseline's larger stress evidence.
