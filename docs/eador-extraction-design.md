# Proposed third objective: carry and escape

Design only, after the v9 support roles. This tranche should add two authored
extraction adventures, then a third after the first two prove distinct manual
plans. It does not complete G05's twelve-pattern requirement. The existing
hero carries the recovered item; no escort NPC, extra army slot, reinforcement
scheduler or Saga2D tactical language is needed.

## The evacuation decision

The hero must reach either marked exit and spend its unspent action to
**Evacuate**, with no living enemy adjacent. Moving or swapping onto an exit
never wins automatically. A Warden can deliver a hero who still has its action;
the hero's own attack, cast or Swap consumes that opportunity for this turn.
Pin restricts the carrier's approach but never disables evacuation itself.
All exits, the action cost, contest rule and deadline are visible before entry.

Hero death loses immediately. End of enemy phase eight loses if evacuation has
not happened. Rout remains a clearly announced alternative: clearing every
defender permits safe recovery of the cargo and ends the encounter immediately.
Successful evacuation may leave enemies alive; it is not a claim they were
killed. Existing finite rival clashes remain rout.

A small game-owned interface is sufficient:

- `Battle.evacuate()` validates the carrier, exit, enemy adjacency and action,
  spends the action and records `outcome_reason='escape'`.
- `Battle.evacuation_blocked_reason` returns the current specific reason or
  `None`, so the UI and automatic policy use the same rule.
- The saved objective gains an `extract` kind and explicit exit coordinates.
  The carrier is `battle.hero_id`; older rout/hold objectives retain their
  existing meaning. Any cargo movement penalty belongs to the battle unit,
  never to persistent `Hero` movement or troop statistics.

Enemy priorities are a legal lethal carrier attack, occupation/contestation of
an exit the carrier can approach, useful Pin against that approach, then other
attacks. A wounded Ranger away from the route must not pull the exit defenders
away. AI should use actual terrain/occupancy costs when judging escape distance,
not straight-line distance alone. Player automatic play must evacuate when
legally able; rout can remain its fallback without being counted as manual
escape evidence.

## Authored layouts and entry consequences

Each row is one proposed pattern. Approach variants of a row never count as
additional patterns. Exact hex coordinates and rosters are hypotheses until
played; keep at most seven units per team and use existing terrain costs.

| Pattern | Layout and opponent decision | Entry choice and consequence |
|---|---|---|
| **Courier's Crossing — Frontier** | Western player deployment, two separated eastern exits. A quick open road crosses Archer fire; forest cover costs movement. Pikeman and Brigand screen the approaches. Rangers can clear a blocker then reposition, while Wardens deliver a wounded carrier. | Direct approach keeps all gold; paying 20 gold gives covered side deployment. Both variants retain the same finite guards and fixed reward. The fee must save exposure or a turn in a paired public journey. |
| **Supply Cache — Elderwild** | Central player deployment, exits on opposing edges, wolves approaching from the outside and a ranged goblin. Choosing the escape direction changes which flank must be screened. A seven-body army initially needs to open space for its hero, making order and Swap useful. | Light supplies give the normal recorded reward. Full cargo lowers the carrier's battle movement by one, minimum one, and adds 40 gold on success. No penalty to attacks, spells or evacuation. The slower choice must be viable with sustain/control and measurably harder for an unsupported carrier. |
| **Sealed Vault — Ruins, second step** | Staggered ranged crossfire with a Warden rotating an injured defender. One guarded primary exit and a distant inactive secondary exit. It asks whether to fight through the screen or redirect the carrier. | Spend two crystals before entry to activate the secondary exit, or retain the crystals and accept the single route. This spends a currently underused campaign resource; neither option may be an automatic best choice across prepared armies. |

Start with Crossing and Cache. Add Vault only after escape timing, costs and
retreat persistence pass. Place each on a deliberate theme flank; preserve
Westwatch's Shrine, required Border Watches, Den/Camp relic sources, capitals
and the default Frontier tutorial route. Do not enlarge the old random site
pool or regenerate a loaded province array.

## Entry and persistence seam

Extend the existing pre-entry adventure view with two clear approaches. A
read-only state query supplies legal approaches, actual resource costs and
consequences. `State.explore(approach=...)` selects one atomically; existing
no-argument callers retain the free/default approach. Keep this out of the
post-victory skill/relic choice queue.

Save one game-owned adventure attempt alongside the active battle: selected
approach, actual gold/crystal/relic reward snapshot, and cargo choice. The
battle already saves terrain, deployment, units and wounds. Do not recompute a
selected reward from a future registry definition after loading. Fees and the
campaign action are spent once at entry; loading never spends them again.
Invalid selection or insufficient resources leaves the entire state unchanged.

Keep the same guard roster across one site's approaches. Retreat preserves
surviving enemy HP and fallen identities through the existing site arrays;
changing approach on a later attempt cannot create fresh soldiers. Entry fees
are not refunded. A failed attempt awards neither XP nor loot. A successful
escape or rout explores the site and rewards once; reopening it cannot farm
surviving defenders. A later attempt may choose a different approach and pays
its own fee. Older active v9 adventures default to the existing recorded reward
and have no extraction metadata or cargo penalty.

## Acceptance before additional content

1. Execute both approaches from paid campaign preparation, with saves before
   entry, after a failed selection, mid-cargo movement, before evacuation,
   after success and during final reward choice. Compare exact continuation.
2. Demonstrate at least two real escape plans on each first layout across all
   four heroes: screened movement/Swap, ranged rotation/Pin, or shared Heal.
   Show the action-cost trap: a hero that casts at the exit cannot evacuate
   that turn; a Warden-delivered hero with an action can.
3. In paired positions, adjacent enemies block evacuation, a pushed/removed
   blocker reopens it, Pin delays arrival, and the enemy contests the route
   rather than pursuing irrelevant wounded bait. Verify range and movement
   forecasts against the commands.
4. Prove the eighth-turn deadline, hero death, rout alternative, evacuation
   with living enemies, withdrawal losses, and one-time reward semantics.
   Reject malformed exits, carrier/cargo metadata and mismatched attempt
   rewards before loading a live state. Preserve actual v9 continuations.
5. Compare time, casualties, mana and total entry/recruitment cost for both
   approaches. Public policy victories are useful regression evidence;
   escape-specific manual journeys must establish the new objective itself.

The parallel role proposal's Smoke, Repulse and flight can later offer real
counterplay here: screen the carrier from ranged fire, clear an exit contester,
or flank a blocker. None is a prerequisite for the first two adventures, and
this design does not assume those abilities are implemented.
