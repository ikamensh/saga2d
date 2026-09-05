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
optimal human tactics. A fortified capital can still accumulate a small
positive net income while the rival watches; siege pressure or paid rival
army development remains necessary before claiming G06's economic-farm
requirement is met.

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
and battles, and damaged saves. A 120-turn fortified-capital scenario earns
only its first defense reward while the rival conquers the other provinces
and eventually watches. The existing 32 seeded economic campaigns across all
four classes still win by exploring, investing and intercepting the announced
threat; leaving Westwatch undefended still loses. Those are bounded regression
strategies, not a claim of broad balance or release readiness.

The full client suite after merging main `00ca6cf` passed 429 tests. Root-owned
UI work must still communicate the expedition, target, countdown and resource
changes clearly, and validate manual interception/counterattack through real
input. This increment advances G06/G13; it does not complete the Early Access
acceptance criteria or replace the previous baseline's stress evidence.
