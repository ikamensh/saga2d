# Next tactical increment: take and hold

Proposal, 2026-09-05. Inspected main at `643648a`, including the current
content, campaign generation, battle commands and codex. The finite rival
branch is a prerequisite for integration, not part of this document's
implementation. This is design toward G04/G05/G08 in
[the acceptance criteria](early-access-criteria.md); none of those gates
passes by accepting this proposal or reaching its content counts.

## What the code currently supports

- [model.py](../eador/model.py) owns four recruits, five buildings and
  `State.new` world generation. The 19 province coordinates, capital
  positions and eastward guard bands are fixed. Seeds vary terrain,
  income and site assignment; there is no separate campaign map generator.
- [content.py](../eador/content.py) defines six sites, six relics and two
  rankable disciplines per hero. Site choices currently happen **after**
  victory: keep/sell a relic or select a skill. There are no pre-battle
  adventure decisions or alternative tactical objectives.
- [battle.py](../eador/battle.py) owns movement, occupancy, range, cover,
  retaliation, two spells and automatic play. Its 37-hex battlefield has
  fixed deployment and seeded terrain. Forest/marsh slow movement;
  forest/hills reduce incoming attack damage. Neither terrain nor troops
  block ranged line of sight. Acolytes currently improve campaign recovery
  and have a ranged basic attack; they cannot heal during battle.
- `reachable`, `targets`, `preview`, `move`, `attack`, `cast` and `end_turn`
  form the useful battle interface. `preview` returns target/attacker HP
  loss. A battle ends when the hero dies, all enemies die, or round 81 is
  reached. `resolve_battle` and save validation assume those conditions.
- The finite rival branch adds persistent enemy health, hero-free clashes
  and expedition identities. New tactics must work for both teams without
  assuming a hero exists, and retain that persistence.

The next change should make **where and when to fight** matter. More troops
using the existing nearest-target attack routine would mostly enlarge the
catalogue while preserving the swordsman rush decision.

## Small first increment

Implement these as three reviewable steps, each playable before adding the
next. Initial numbers below are tuning hypotheses, not balance evidence.

1. **Guard and spear defense.** All combatants can Guard: spend their remaining
   movement/action for +2 defense until their next team turn begins. Add a
   Barracks Pikeman (suggested 40 gold, 2 upkeep, 28 HP, 9 attack, 3 defense,
   movement 2, range 1). Brace spends the same movement/action without the
   defense bonus: the first adjacent melee attacker takes one normal spear
   hit **before** its own attack;
   if killed, it deals no damage. The reaction is consumed once and expires
   at the Pikeman's next turn. Ranged attacks and waiting out the stance
   counter it. No reaction to intermediate movement hexes in this step.
2. **One hold objective with an opponent that contests it.** A marked seal
   must be occupied by a living player soldier or hero, with no adjacent
   enemy, at the end of two consecutive enemy turns. Losing control resets
   progress. Hold succeeds even with surviving enemies; eliminating all
   enemies also succeeds. Failure to complete by the end of round 8 loses
   the encounter; hero death still loses immediately. Enemy AI approaches,
   contests and attacks the holder rather than chasing an irrelevant low-HP
   target. Surface progress, deadline and contest rules before entry and
   throughout combat.
3. **Pin and two authored adventures.** Archer Pin uses its action within
   three hexes: half normal attack damage, rounded up, and -2 movement during
   the target's next team turn, never below 1. It cannot be reused on the
   shooter's following turn; reuse is allowed on the turn after that.
   Pin does not prevent attacking or guarding, stack, or extend an existing
   Pin. Add a hold encounter and a contrasting rout encounter, plus two
   discoverable relics granting Brace or Pin to the hero. Both adventures
   need an entry decision with a visible cost/consequence, not only loot.

Suggested pair: **Border Watch** offers a direct approach (better loot,
exposed route to the seal) or a paid scout route (less loot, side deployment
behind cover); **Wolf Den** offers an immediate fight or spending one
campaign action to lure the pack away from protective terrain. Do not
replace the dependable home shrine tutorial with these experiments.

This increment reaches five recruits, four distinct active capabilities
(Bolt, Heal, Brace, Pin), eight relics and two objective types. Guard,
movement, basic attacks, ranked variants and the end-turn/wait decision do
not inflate the eight-capability target. It deliberately does not claim
the full content floor, line of sight, or twelve completed adventures.

## Target roster: ten roles, with counters

These are the complete proposed ten recruitable roles, including the four
existing recruits. A role may use an existing ability; a unique name or a
higher stat alone does not establish a role.

| Recruit | Decision and role | Counter / opportunity cost | Access direction |
|---|---|---|---|
| Militia | Cheap reserve; Rally clears Pin/Root from an adjacent ally instead of attacking. | Low durability; spending a slot on support reduces damage. | No building. |
| Swordsman | Holds a choke; Guard also protects adjacent allies with +1 defense while the swordsman remains beside them. | Flanks, ranged focus and objectives requiring speed. | Barracks. |
| Archer | Sustained ranged pressure or Pin to delay a contesting enemy. | Cover, later line-of-sight obstacles, fast melee. | Archery Range. |
| Acolyte | Heal through the troop's action, preserving the hero's action. Uses the same finite army mana reserve as hero magic. | Fragile; healing competes with control/damage spells and recruitment slots. | Temple. |
| Pikeman | Brace protects a holder from melee approaches. | Ranged pressure or delaying the attack until the stance expires. | Barracks. |
| Ranger | Shoot then move; rough-ground mobility. Reuse the existing skirmisher/terrain-walk traits. | Weak sustained holding power; must leave space to retreat. | Archery Range plus a wilderness adventure unlock. |
| Knight | Reaches exposed ranged units; charge bonus requires an unobstructed approach of at least two hexes before attacking. | Brace, rough ground, Pin and blocked approaches. | Military upgrade with a meaningful gold/upkeep premium. |
| Hexbinder | Root removes movement for the next turn; attacks remain available. Control competes for shared mana. | Rally, ranged enemies, baiting casts on expendable troops. | Mage Tower and crystal investment. |
| Warden | Interpose swaps with an adjacent ally, spending its own action to extract the vulnerable holder. | Both hexes must be legal; the Warden takes the dangerous position. | Temple plus a protection adventure unlock. |
| Sapper | Breach destroys one destructible obstacle or removes a seal's protective ward. Opens an alternate route rather than maximizing damage. | Needs approach time and protection; weak on open rout maps. | Barracks plus a ruins adventure unlock. |

The later Knight needs an actual chosen movement path before a charge can
be previewed; straight-line distance alone must not award a charge through
occupied or obstructed hexes. Do not implement it prematurely in step one.

Three army plans to demonstrate, not merely label: **hold and sustain**
(Swordsman/Pikeman/Acolyte), **range and reposition** (Archer/Ranger/Warden),
and **control and breach** (Hexbinder/Sapper/Knight). Each must have a
scenario where it saves casualties or meets an objective the others
struggle with, and a counter-scenario requiring a changed tactic or recruit.
They must also complete campaigns; success on a bespoke arena alone is
insufficient. Commander troop protection, Scout mobility, Warrior holding
and Wizard mana choices should alter decisions within these plans.

## Eight active capabilities and twelve relics

The eight distinct capabilities are **Arcane Bolt, Heal, Rally, Pin, Brace,
Interpose, Root and Breach**. Magical actions spend the existing shared mana
reserve even when a troop casts them. Physical abilities use explicit
turn cooldowns where needed; Brace lasts only until the next own turn.
Avoid a second resource pool in this increment. Guard is a universal
defensive command and is not counted toward eight.

Keep the six current relics and their identities: Wayfarer Boots, Oak
Standard, Ember Lens, Moonstone, Iron Crown and Merchant Seal. Add six that
grant the hero a tactical option rather than another small stat increase:

| Proposed relic | Grants | Equipment choice it creates |
|---|---|---|
| Watch Bell | Brace | Hold with the hero instead of using Iron Crown to attack safely. |
| Storm Quiver | Pin | Spend the hero action delaying a target instead of dealing full damage. |
| Vanguard Drum | Rally | Free an ally's movement instead of healing or attacking. |
| Mirror Badge | Interpose | Extract an ally by putting the hero in its exposed place. |
| Tether Charm | Root | Spend shared mana on position control instead of Bolt/Heal. |
| Siege Key | Breach | Open a route without recruiting a Sapper, at the cost of the equipped slot and hero action. |

Retain one equipped relic and the current keep/sell/duplicate decision.
Each new relic needs a guaranteed discoverable source among the authored
patterns, exact codex rules, and a relevant demonstrated use. First ship
Watch Bell and Storm Quiver with the two new adventures; later items wait
for their abilities. Reachability must be tested across an entire campaign,
not assumed because an ID exists in a table.

## Twelve adventures across three themes and objectives

Each row is a target authored pattern: a roster, deployment/terrain layout,
objective, entry decision and consequence. Names alone do not count. The
three objective families are **rout**, **hold**, and **extract**. Extract
requires moving a designated living carrier to an exit; hero loss, carrier
death and an announced deadline lose, so eliminating enemies is not its
only decision. Extraction, obstacles and line of sight are later work.

| Theme | Pattern / objective | Distinguishing decision |
|---|---|---|
| Frontier | Lost Caravan / rout | Free a captive ally first or attack the raider leader immediately. |
| Frontier | Border Watch / hold | Pay for covered side deployment or keep the full reward and cross the open approach. |
| Frontier | Prison Road / extract | Short exposed exit or longer protected route for the rescued carrier. |
| Frontier | Supply Train / extract | Carry heavy supplies for a better realm reward or abandon weight to move faster. |
| Elderwild | Wolf Den / rout | Spend campaign time drawing wolves into open ground or fight immediately. |
| Elderwild | Elder Grove / hold | Contest the central seal or clear a flanking ranged threat before committing. |
| Elderwild | Thorn Passage / extract | Clear a blocked shortcut or escort the carrier around it. |
| Elderwild | Moon Pool / hold | Spend crystals to remove a Root hazard or bring Rally/mobility support. |
| Ruins | Old Barrow / rout | Open the relic chamber for extra defenders/reward or secure the outer tomb only. |
| Ruins | Fallen Tower / hold | Breach an approach or contest through the defended entrance. |
| Ruins | Sealed Vault / extract | Take a valuable slow carrier burden or a lighter reward. |
| Ruins | Observatory / hold | Disable a protecting ward with Breach or defeat its ranged attendants first. |

Named map themes must change layouts, encounter mixes and travel decisions
when G02 is implemented. Randomly relabeling the current guard bands will
not satisfy this design. Seeded variants of one authored pattern do not
count as additional patterns.

## Implementation seam and acceptance evidence

Keep `Battle` as the game-owned rules module. Add ordinary commands for
Guard and abilities; put legality and a structured consequence preview in
that module so mouse, keyboard, codex and auto-play read the same rules.
Extend the existing exact preview to report pre-attack reactions, status,
resource cost and affected hexes; do not duplicate those formulas in scenes.
Use one turn-transition implementation for status expiry and cooldowns.
Only durable IDs, counters, positions and effects belong in saved state;
no framework timers or serialized callbacks.

An authored encounter definition should supply deployment, terrain and a
small explicit objective description when `State._start_battle` creates a
battle. Resolve the entry choice first, save it, and preserve its selected
layout/reward on reload. Add a game-owned `eador/encounters.py` once those
definitions earn a separate module. Ordinary data plus a few objective
branches are sufficient; a general event language or strategy engine is
not required. `State.new` assigns valid patterns by region/theme and keeps
an opening that does not require an unavailable counter.

Objective victory must carry a reason through `Battle`, `resolve_battle`,
result presentation and save validation. A hold victory leaves living
defenders; do not report them killed, grant repeated rewards on re-entry,
or accidentally erase an unrelated expedition. The finite rival's ordinary
clashes remain rout battles until another objective is deliberately added.
Current-save migrations default existing battles to rout and must preserve
their exact subsequent commands and results.

Use Saga2D's existing `HexGrid`, scene ownership, input, measured paragraphs,
buttons and save I/O. There is no demonstrated need for a framework ability,
status, faction, objective or encounter abstraction. Later, implement any
line-of-sight geometry in Shardbound first; promote a small geometric
primitive only after a concrete independent caller demonstrates its value.

Before calling the first increment done, record these public behaviors:

1. A matched attack/Brace case shows the manual survival advantage, a ranged
   counter, one-use reaction and correct expiry. Preview equals actual HP
   change, including the attacker dying before it can strike.
2. Pin changes reachable cells without disabling attacks, stacking or
   refreshing itself; save/reload at every phase preserves its duration.
3. Hold wins with enemies alive, is interrupted by a contesting enemy,
   fails at the deadline and survives save/reload one turn before success.
   Results, site completion and rewards occur exactly once.
4. The same prepared army can win a relevant objective manually where the
   baseline nearest-target auto policy loses or suffers greater casualties.
   The updated automatic opponent responds to the objective and abilities;
   it must not pass the test simply by refusing to contest.
5. Both adventures are entered, their alternative choices are exercised,
   their relics obtained and used, and each ability has a complete keyboard
   and mouse path. Inspect real screenshots showing stance, status, target
   preview, objective progress and outcome at supported display sizes.
6. Replay across deterministic terrain seeds, all four heroes and the
   finite-rival journeys; preserve migration and damaged-save tests.
   Expand to the full three army plans/content floor only after this small
   increment demonstrates decisions beyond the original swordsman opening.
