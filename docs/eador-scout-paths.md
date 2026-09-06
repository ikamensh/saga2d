# Earned Scout paths

This comparison follows two declared Scout builds from the same earned first
skill choice: Pathfinder twice or Skirmisher twice. Both complete the same six
battles by turn 4, have no troop deaths, and spend the same 100 gold on two Rangers.
They demonstrate different usable orders; they do not establish which path is
stronger. Different agents chose different tactics within the shared itinerary.

## Starting state and scope

The anchor is `commands[14].before` in the preserved historical
`shardbound-army-plans-cd351a9/mobile.json.gz` journal: turn 2 at Silverford,
25 gold, 7 crystals, two actions, and a level-2 Scout awaiting the first skill.
The army contains two Militia, an Archer and a Warden. The Archer starts six HP
short; the other troops and hero are healthy. Barracks, Archery Range and an
equipped Moonstone are inherited. The historical opening used autoplay and
spent 155 gold on those buildings and the Warden; that cost is separate from
the new continuation's 100 gold.

Each continuation records explicit commands, reasons, complete before/after
saves and actual currency changes. Every subsequent command resumes from the
serialized result. There is no autoplay, injected resource, rewind or search
branch after the anchor. The validator accepts this particular historical file,
hash and checkpoint, including its pending skill choice; it does not accept a
journal-selected arbitrary starting save.

The fixed itinerary is Silverford's Shrine, a Ranger purchase, Briarwood,
mandatory rest, Militia replacement with a second Ranger, Raven Hill, Border
Watch, mandatory rest, Greenwater, and Stranded Explorer's north assembly.
Both retain Moonstone equipped and keep the earned Bell and Boots unequipped.
The declared turn-7 limit is not reached; neither needs extra recovery.

## Retained outcomes

| Observation | Pathfinder II | Skirmisher II |
|---|---:|---:|
| Explicit saved commands | 111 | 114 |
| Battles won / troop deaths | 6 / 0 | 6 / 0 |
| Sum of final battle round numbers | 11 | 12 |
| Enemy-phase commands | 6 | 7 |
| Mandatory rests / additional rests | 2 / 0 | 2 / 0 |
| New troop purchases | 100 gold | 100 gold |
| Hero Heal casts / mana spent | 1 / 4 | 0 / 0 |
| Final turn / available actions | 4 / 1 | 4 / 1 |
| Final gold / crystals / mana | 192 / 18 / 14 | 192 / 18 / 14 |
| Final missing army HP | 13 | 17 |
| Final missing hero HP | 0 | 4 |

Pathfinder finishes Briarwood in round 1; all other battles in both paths end
in round 2. The single Heal restores 11 Archer HP during Raven Hill. A later
mandatory rest restores the spent mana, so equal final mana does not mean equal
spell use. Final wounds also include earlier battles; they are not all damage
from Explorer. The retained summary distinguishes entry wounds and later damage.

Pathfinder lets the Warden cross rough ground onto Border Watch's seal in round
1. Enemies contest the seal, so the army still wins by routing defenders in
round 2. Skirmisher's hero attacks and then vacates the seal, allowing the Warden
to occupy it. That branch also wins by rout. Neither result claims a hold win.

At Explorer, Pathfinder lets the isolated hero cross forest to finish an enemy
Archer. Skirmisher instead uses the hero's attack-then-move order. Rangers can
already shoot and move in both builds; that shared troop trait is distinct from
the hero's skill. Friendly bodies and blocked ranged sight still require actual
repositioning in both branches.

Both evacuate in round 2 through the Warden's Swap and an unspent hero order.
Only the enemy Archer dies: the other three defenders withdraw after the escape.
The native capture immediately before Evacuate shows the hero on the exit,
no adjacent enemy, and the enabled command. These are extraction victories,
not four-defender routs. All wounds remain in the subsequent saved map state.

## Verification and remaining work

The [raw journals, native controls and inspected images](evidence/scout-paths-78cb545/README.md)
retain separate execution sources: Pathfinder `78cb545`, Skirmisher `36aaaa2`,
and both native replays `49d5b65`. Game/framework bytes remained unchanged;
the intervening commits change the validator and its tests.

The native replays match every command and F5/F9 save/load join: **225 commands,
225 reloads and 918 input events**. Both use the larger text setting and record
unchanged source hashes. Twenty-four focused validator tests pass. The native
runs take 46.29 and 39.58 seconds, averaging 25.38% and 25.30% of one core under
the cooperative development budget. They run sequentially and close their games.
The UI replay verifies state and controls; it is not a complete text audit of
every forecast displayed during play.

These are agent-directed partial campaigns, using one historical autoplay
opening. The matched itinerary controls purchases and opportunities, but the
different orders and operators prevent attributing all wound differences solely
to the skill choice. Broader seeds, alternative orders, full campaign viability,
player understanding and human feedback remain unproven. All G01–G19 remain
incomplete. No game-specific build or encounter policy was added to Saga2D.
