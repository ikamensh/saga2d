# Smuggler Screen

The ninth authored-family direction is a rout against a finite Sapper, two
Archers, Warden and Dread Guard. It adds game content and public development
journeys; no battle rules, save schema or Saga2D API changed. Final native
presentation and broader release gates remain separate acceptance work.

New Elderwild shards place the site at `(0,-1)`. Success grants 60 gold, two
crystals and Veil Censer, which grants the hero the same one-charge Smoke order
seen in the encounter. The original Frontier Crossing/Censer source remains.
Shrine, Watch, Cache, Hunt, Den, Explorer's Camp, Muster Yard, Observatory, Vault
and all other fixed relic sources remain; Elderwild's Grove fallback preserves
Oak Standard if this replacement removes its last procedural source.

Both approaches are free and keep the same terrain, finite enemy roster and
reward. **Western column** puts the combined army behind its front marksman;
**northern assembly** brings the support toward the northern firing lane. There
is no isolated carrier, escape action, central seal, extra fee or bonus.

The ordinary radius-three board has forest at `(-1,-1)`, `(0,1)`, `(1,-2)` and
hills at `(1,0)`, `(2,-1)`. The remaining 32 hexes are plains. Enemy positions in
roster order are `(1,0)`, `(2,-1)`, `(1,-1)`, `(2,0)`, `(1,1)`. Western player
positions in hero/army order are `(-3,0)`, `(-2,0)`, `(-3,1)`, `(-2,-1)`, `(-3,2)`,
`(-2,1)`, `(-3,3)`; northern positions are `(-3,0)`, `(-2,-1)`, `(-2,0)`, `(-1,-2)`,
`(-3,1)`, `(0,-3)`, `(-3,2)`. Smaller armies use the same normal ordered slots.

## Earned manual plans

`tools/eador_screen_campaign.py` prepares the actual site through ordinary
purchases, conquests and recovery. `prepare_screen(state=...)` accepts the same
State-like native input adapter as the existing adventure preparations. The
route functions accept `orders_type=...`; they never invoke auto during the
encounter. Auto is used only for the prior campaign's ordinary preparation.

| Standard seed seven | Arrival | Encounter plan | Rout / round | Soldier deaths in encounter | Missing party HP | Tactical mana spent |
|---|---|---|---|---|---|---|
| Commander, Warden and Ranger | Turn 8, level 3, six bodies | `screen_western_route` | 4 | 0 | 62 | 0 |
| Same exact Commander save | Same | Western, `heal=True` | 5 | 0 | 44 | 4 |
| Same exact Commander save | Same | `screen_northern_route` | 5 | 0 | 43 | 8 |
| Scout, Warden and Ranger | Turn 9, level 3, five bodies | `screen_scout_route` | 6 | 0 | 55 | 8 |

The Scout preparation has already lost an original Militia in prior conquest;
this is an actual smaller purchased army, not a removed unit in a tactical
fixture. Neither demonstration injects army stats, resources or experience.
These are reproducible plans, not optimal policies or a claim that a northern
approach always saves resources.

Western Commander lets the first advance expose the cloud on its Ranger's
hex. The Ranger moves south around Smoke before firing; Warden, Militia and
hero handle the Guard, while our Archer stays back to remove the northern
bowman. Finishing the wounded Sapper denies the enemy Warden a rescue. A saved
counterprobe in the preceding design evidence shows that leaving the Sapper
wounded lets the Warden swap it behind the line. Moving the Ranger forward
around Smoke instead of south caused its death in that paired probe.

Northern Commander gets an interior cloud and a Pinned Ranger. The Ranger
shoots, then a Militia moves into Rally range and clears Pin without refreshing
its spent attack. This restores the Ranger's still-unused movement for a flank
that was out of reach while slowed. The party handles the northern bowman
before the Guard; the Ranger then shoots and withdraws into Heal sight while
the Warden holds the southern pressure. Two heals support the two fronts.
These orders cannot be exchanged for the western retreat merely by changing
one destination or accepting different damage totals.

The smaller Scout uses a third plan: Militia, Ranger, Archer and ranged hero
focus the Sapper on round one, killing it before the charge. It withdraws the
Ranger and sustains the Militia while finishing the bowmen and armoured guards.
This demonstrates denial of the finite order through target priority, not a
new special counter or an assumed free enemy healing resource.

## Persistence and limits

Every public test order checks exact attack/Heal forecasts and reloads the
complete campaign state. Retreat after the Scout opening preserves the dead
Sapper and four surviving guards at HP `20,4,34,42` when selecting the other
assembly. A separate real hero-death outcome at round 13 loses three soldiers
and leaves one enemy Archer. Four paid Swordsmen cost 180 gold during recovery;
the saved western retry contains only that surviving Archer and awards the
site once. Loss grants no XP or site reward; dead soldier IDs do not return.

Each surviving Sapper receives its ordinary one charge when a new battle is
created. Its charge and cloud lifetime are saved during that battle; retreat
does not create a replacement for a dead Sapper. Enemy losses and wounds remain
in the site's stored roster. This uses the existing per-battle capability rule,
not a new campaign-persistent charge resource.

Actual old Grove and Caravan snapshots from source `0e27175` preserve their
recorded site identities and exact battle/reward continuations. New worlds get
the Screen; existing worlds are never rerolled. An unentered future linked shard
uses current content, as documented in [saved-world policy](eador-save-continuation.md).
The original historical difficulty fixture bytes remain untouched.

The fixed manual scripts are Standard seed-seven demonstrations. Both Commander
scripts also won the five tested Standard and Accessible seeds `0,1,2,7,19`.
Some Challenge preparations produce different veteran levels, and the smaller
Scout's exact ordered roster varies across seeds. Those scripts need adaptation
for such arrivals; do not present them as universal difficulty policies. Normal
commands and automatic play remain available independently of these dev scripts.

The shared guidance matrix includes real paid Commander, smaller Scout and
wounded retry preparations at 100/125% reading sizes and three supported window
sizes. Its mock geometry/nonmutation checks pass. Root's native verifier and
screenshots are still pending; no visual approval is claimed here.
