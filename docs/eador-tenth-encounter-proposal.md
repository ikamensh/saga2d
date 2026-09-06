# Tenth encounter proposal: Aerie Raid

Recommend a bounded **Aerie Raid** production tracer after review. The prototype
answers whether flying raiders force a different formation decision using the
current rules. It demonstrates three complete manual plans from two genuinely
purchased parties, a costly failed opening and an explicit control counterprobe.
It changes no production content, placement, save schema or framework API.
This is a proposed tenth family, not an accepted tenth pattern or G05 completion.

## What the current nine already do

| Existing family | Established tactical problem | Guaranteed current source |
|---|---|---|
| Border Watch | Reach and hold a contested seal; screen its adjacent cells. | Watch on every theme; Watch Bell. |
| Last Gate | Maintain a broad formation under the linked finale deadline. | Third-stage Duskspire; campaign ending. |
| Courier's Crossing | Escort the hero across a defended approach to an exit. | Frontier `(0,2)`; Veil Censer. |
| Supply Cache | Choose cargo burden, then break out of surrounding pressure. | Elderwild `(-1,-1)`; Porter's Rune. |
| Sealed Vault | Pay to open another escape route through separated crossfire. | Ruins `(-1,1)`; Mirror Badge. |
| Pack Hunt | Handle two ground flanks divided by forest; optional lured assembly. | Elderwild `(-1,1)`; Storm Quiver. |
| Broken Observatory | Open or retain a forest lane that changes both armies' sight. | Ruins `(-1,0)`; Ember Lens. |
| Stranded Explorer | Regroup a split hero/escort across marsh to the return exit. | Frontier `(0,-1)`; Wayfarer Boots. |
| Smuggler Screen | Relocate around enemy Smoke; stop or accommodate Warden rescue. | Elderwild `(0,-1)`; Veil Censer. |

The protected home Shrine/Moonstone, fixed Den/Storm Quiver, Explorer's
Camp/Boots, Frontier Muster Yard/Drum and western Caravan/Grove fallbacks remain.
Old Barrow/Crown, Tower/Lens, Caravan/Seal and Grove/Oak sources also matter.
The prototype audits the **unchanged** generator for 100 seeds per theme: fixed
sites and Watch remain, and each three-theme union supplies all twelve relics.
This does not promise every relic in each individual shard or authorize a new
placement. No replacement site or new reward is installed by this proposal.

## Two alternatives, one prototype

| Candidate | New decision it could create | Assessment |
|---|---|---|
| Rear-seal Cliff Beacon | Breach rough/occupied ground using flight, or push open an escort route with Repulse. | Defer. Relocating the seal risks repeating Watch/Gate formation control or the Observatory's approach. It needs more than a distant objective to become distinct. No prototype or production content was added. |
| **Aerie Raid** | Draw flying raiders away before launching a flanker; redirect a rear attacker into a braced reserve, or fund a ground rescue and concentrated fire. | Prototype shows actual airborne landings across the rough belt, a failed premature sortie, and viable ground and control alternatives. The expensive control army has costs as well as benefits. |

The raid uses ordinary rout. It has no split carrier, seal, extraction exit,
forest opening, Smoke event, infinite spawn or special AI script. The enemy
Skyriders use the existing landing/exposure score and ordinary low-HP targeting.
Flight does not inherently target the rear: the measured geometry actually
produces that landing. A same-unit query with only `fly` removed cannot reach
the recorded enemy landing or the player's eastern sortie.

## Concrete prototype and paid results

The radius-three board has 37 hexes. Both columns `q=-1` and `q=0` are marsh,
except `(-1,0)`; `(1,0)` and `(1,1)` are marsh too. Hills are `(1,-1)` and
`(2,-1)`; other cells are plains. The extra eastern marsh makes the sortie
require actual flight instead of merely the Skyrider's four movement points.

Hero/army positions are `(-3,0),(-1,0),(-2,0),(-3,1),(-3,2),(-2,2),(-1,1)`.
Two enemy Skyriders begin at `(1,-2)` and `(1,1)`, an Archer at `(2,-1)`, and
a Pikeman at `(1,-1)`. One Militia anchors the forward ground contact while
the raiders can reach the support's flank. There is no isolated hero.

`prepare_control_watch(kinds=...)` buys the actual parties through normal
campaign commands. Their ordinary Watch departure state is retained unchanged;
the prototype creates a **detached proposed battle**, not a new-world site or
campaign reward. Both are Standard seed-seven level-two Commander parties with
the original two Militia and Archer. Neither has injected stats or resources.

| Purchased additions | Actual funding and arrival | Manual result | Missing HP | Mana spent | Orders |
|---|---|---|---:|---:|---:|
| Pikeman, Rune Adept, Skyrider | 408 gold + 7 crystals; turn 9; 16 mana | Control/flight rout, round 4, no deaths | 46 | 8 | 34 |
| Same exact paid party | Same | Sustain before finishing, round 4, no deaths | 39 | 12 | 30 |
| Pikeman, Warden, another Archer | 271 gold; turn 4; 12 mana | Ground escort rout, round 4, no deaths | 20 | 12 | 38 |

Funding includes all preparation buildings and recruits. The expensive party
pays for a Tower and Temple as well as the two roles; it arrives five campaign
turns later and has more future recovery/spell infrastructure. It is **not** a
controlled claim that a Skyrider alone costs 137 more gold or that flight is
universally stronger. The ground escort is cheaper and less wounded here. The
control line preserves four more mana; its same-party sustain alternative spends
those four mana to remove seven additional wounds. These are demonstrated plans,
not optimal policies or a difficulty-wide recommendation.

The control line first waits for the raiders to commit. The rear Skyrider lands
at `(-2,3)` and wounds the Adept. An Archer shoots it; the Adept circles to
`(-3,3)` and Repulses it to `(-1,3)`. The Pikeman occupies the vacated `(-2,3)`
and Braces, while a Militia fills the caster's old place. The raider now attacks
the Pike and takes its pre-hit; the Adept stays at 22 HP. The player Skyrider can
then cross the rough ground to `(2,0)` and hit the distant Archer while ground
units finish the raiders. The lower-mana finish repositions the hero for Bolt;
the sustain finish spends another Heal before resolving the remaining pressure.

The ground party instead rescues its eight-HP exposed Archer with a moved Warden
Swap. Militia, Pike and the rear Archer kill the southern raider; the hero steps
forward to bring Heal into range. The Warden then advances through the ground
opening while both Archers concentrate fire. A final Heal preserves the front
Militia. This uses the ground corridor and shared healing rather than an Adept
redirect and a flying sortie.

## What the failed and alternate orders show

- **Premature sortie:** send the paid Skyrider to `(2,0)` and attack immediately.
  Both enemy flyers converge; their attacks plus the Archer kill it in the first
  enemy phase. The recruit actually cost **73 gold and three crystals** after
  the earned discount. This is a real troop loss in an ongoing battle, not a
  fabricated whole-campaign defeat.
- **No Repulse:** keep the Adept in place and Brace a Pike beside the original
  raider landing. The raider attacks the lower-HP Adept instead; it falls to 16 HP
  while the Pike remains full. Repulse creates the hex the Pike occupies and
  changes the raider's available adjacent target. The full control line takes
  one more total wound in that phase, so it protects the caster by moving the
  damage rather than promising less damage everywhere.
- **Rejected Pin assumption:** an earlier probe used Pin before the redirect.
  The AI attacks the adjacent braced Pike either way; slow adds no necessary
  control to this line. The final route uses the stronger ordinary shot. Do not
  describe this as a demonstrated Pin lock or invent smarter enemy targeting.

Automatic baselines are explicitly separate: the flight party routs in three
rounds with 40 wounds / 12 mana and no deaths; the ground party routs in four rounds
with 46 wounds / 8 mana and one dead Militia. Manual ground play saves that casualty
for four extra mana. The control line's mana saving does not make it faster or
less wounded than auto.

## Why pursue it, and what would reject it

The distinct problem is **airborne access to the rear and the timing of a
counter-sortie**. A ground front alone does not control the available landings;
Repulse can redirect an already-landed raider into a reserve's reaction. This
uses flight/Repulse where their exact positions matter, rather than adding new
stats to Pack Hunt's wolves or moving another seal. The cheaper ground party
also prevents a hidden mandatory Skyrider requirement.

Before counting a production family, prove two useful pre-entry assemblies with
the same paid party, a smaller/different-class army, visible flight/Brace advice,
finite failed retry/reward once, actual prior-save continuation and native input.
Keep both assemblies free unless measured benefit justifies a fee. Do not assign
another role's source or the western fallback to make room. A duplicate Watch
Bell could connect the reward to the displayed melee counter, but reward and
placement remain untested proposals.

Reject or redesign it if the new assembly is cosmetic, the rear landing remains
ground-reachable, every viable plan requires the seventh slot, or a basic ground
party can ignore the airborne threat without a relevant cost. Also reject claims
of general balance from these two arrivals: the control investment is currently
expensive and its benefits are situational. Passing this prototype does not
establish first-time readability, enjoyment, replay variety or G05 completion.

## Reproduce and retire

```sh
PYTHONPATH=. python tools/prototype_eador_aerie.py --output /tmp/aerie.json.gz
PYTHONPATH=. python tools/prototype_eador_aerie.py --interactive flight
```

The interactive mode accepts public JSON commands and prints state after every
order. Every scripted manual command checks relevant immediate forecasts and
serializes/reloads the complete **Battle**. Whole campaign validation is not
claimed for the detached proposed battle; its ordinary prepared campaign remains
byte-identical. The retained report records that campaign, purchases, terrain,
all intermediate battles, failures and source hashes. Delete/absorb this named
throwaway tool after the design is accepted into production or rejected.

The [retained report](evidence/aerie-prototype-2026-09-06.json.gz) records clean
prototype source `78254e7`. The three completed manual plans contain 102 public
orders with 102 exact Battle reloads; failed/partial probes and the seven
automatic phases are recorded separately. All source hashes matched after the
run; 25 existing control, sight and public-route tests also passed. These are
pure model observations, with no native presentation or production-site claim.

The gzip archive preserves the original report bytes exactly; inspect it with
`gzip -dc docs/evidence/aerie-prototype-2026-09-06.json.gz`. Compression changes
no measured source, orders, snapshots or findings.
