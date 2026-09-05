# Border Watch: the first objective encounter

Stage 2 of [the tactical plan](eador-tactics-design.md) adds one authored
encounter. It supplies evidence toward G04/G05/G08; those release gates
remain incomplete. There is no Pin, pre-entry route choice, new relic, or
framework strategy engine in this increment.

Border Watch appears at `(0, -2)` in Frontier, away from the dependable
home Shrine. Its Pikeman, Archer and Brigand defend a fixed 37-hex layout
with a seal at `(0, 0)`. Complete two consecutive uncontested enemy phases
while a living player unit occupies the seal. Every living adjacent enemy
contests it, including ranged units. Empty or contested control resets the
count. The eighth enemy phase counts: completing the second hold there
wins before the deadline is checked. Killing every enemy is an alternative
victory; hero death loses immediately.

Defenders approach the seal even when an irrelevant wounded target is in
range, then prioritize its holder. A legal killing attack on the hero or
holder can take precedence over moving. A ranged defender cannot be kept
outside the seal merely by offering weak bait. Units, occupancy, cover,
Guard and Brace retain their ordinary rules.

## Game interface and persistence

- `SiteSpec.encounter` selects a game-owned definition in
  `eador/encounters.py`; the world generator only places the site.
- `Battle.create(..., encounter='border_watch')` uses its terrain,
  deployments and objective. Ordinary battles and finite rival clashes
  retain their seeded rout behavior.
- `battle.objective` exposes `kind`, `target`, `progress`, `required` and
  `deadline`. For rout, target/deadline are `None`, required/progress zero.
  Progress changes after enemy actions, before the next round begins.
- `battle.outcome_reason` is `None` until finished, then `rout`, `hold`,
  `hero_death`, `deadline` or `exhaustion`. The outcome remains the existing
  `player`/`enemy` value. Hero-free rout clashes also use reason `rout`.
- Save schema 5 stores the complete objective and outcome reason. Versions
  1–4 migrate active encounters as rout without regenerating terrain,
  deployment or army state. The recorded v4 Brace battle has an identical
  continued outcome, unit HP/positions/stances, mana and round.
- A hold victory keeps the surviving defenders' actual HP. Resolving it
  marks the site explored, awards its existing one-time gold/crystal/loot
  choice, and gives normal victory experience. The defeated site cannot
  be explored or resolved again. No province changes owner.
- Retreat or deadline failure preserves defender losses and wounds, gives
  no victory reward, and leaves the site unexplored. A later visit starts
  round 1 with zero hold progress and the surviving defenders.

The save validator accepts a terminal hold only with completed progress,
its living holder, no adjacent living enemy, and surviving defenders. A
saved rout still requires every defender dead. Corrupt terminal claims
are rejected before rewards can be collected. Mid-turn progress remains
historical: moving the previous holder does not reset it until the next
enemy phase evaluates control.

## Executable evidence

`tests/eador/test_objectives.py` contains 36 public model journeys and
boundary cases. The complete suite passed **544 tests** after merging the
current Guard UI and framework settings.

[The random stress report](evidence/shardbound-hold-stress-2026-09-06.json)
records 100 model campaigns and 20 scene runs, including 10,003 random
input activations and 113 defensive orders, in 78.3 seconds. No source
changed during execution. The report preserves the original dirty-at-start
metadata; every recorded game/framework/harness hash was subsequently
checked against clean commit `e03715d`. These random runs exercise general
state and UI stability; the public objective journeys below supply the
specific hold evidence.

A Commander journey builds Barracks/Swordsman, explores the home Shrine,
buys Temple, conquers `(-1, -1)` then `(0, -2)`, rests and fills the roster.
At the Watch it screens the approaches, weakens the forward Pikeman, then
finishes that Pikeman and rotates troops into the gap. Guarding the ring
holds the seal through two enemy phases and wins at round 3 with a living
Archer. The test saves after the first hold and after terminal victory,
collects the reward, saves each choice, and verifies repeated collection
and exploration are rejected without state change.

Sixteen seed/class prepared openings also win through the simpler rout
alternative before the deadline. A deployment-area Guard strategy reaches
round 8 with its hero alive, loses on the deadline, saves that result, and
resolves without a site reward. Other tests exercise broken consecutive
control, irrelevant ranged bait, immediate rout/hero death, last-turn
success, and preserving casualties through retreat and re-entry.

The Commander formation is a demonstrated tactic, not evidence that every
army composition can win by holding. Root integration supplies the visible
pre-entry explanation, seal marker, progress and result wording; native
UI verification is separate from these model checks. Wider encounter and
build diversity still needs subsequent authored content and playtesting.
