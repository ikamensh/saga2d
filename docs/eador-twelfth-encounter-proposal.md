# Twelfth encounter candidate: Runebound Causeway

**Follow-up:** [actual Ruins arrival and production proposal](eador-causeway-placement.md)
retains independent review's caster-priority bypass, fair healing comparisons
and the safe duplicate-source audit. That later evidence supersedes this
initial probe's unreviewed emphasis on the Repulse counter.

**Prototype, not production content or G05 completion.** The question is whether
an enemy Rune Adept can turn extraction into a choice between anchoring the
carrier, occupying the push landing, and approaching from a different angle.
The bounded model probe supports that direction. No battle rule, framework API,
schema, world placement or production registry changes are proposed here.

## Why this candidate

Two ideas were compared against the current ten families and revised Relief:

| Candidate | Decision | Assessment |
|---|---|---|
| Runebound Causeway, extraction | Guard against Repulse, block its required landing with another soldier so the hero can cast, or flank with a mobile ranged hero. The freed action and occupied soldier change who clears the exit Pike. | Stronger existing interaction to probe; implemented below. |
| Protected anchor convoy, rout | Shoot a braced Pikeman, wait for its stance to expire before Repulse, or flank its supporting Warden. | Too close to existing Brace counters, Screen rescue and Aerie flanking without another demonstrated consequence; no prototype or production entry added. |

Watch/Gate ask for seal control; Observatory changes bilateral sight. Crossing,
Cache and Vault compare escort routes, cargo and exits; Explorer separates the
carrier from its escorts. Hunt divides ground pressure, Screen uses enemy Smoke
and rescue, Aerie adds airborne access, and Relief makes support undo Pin.
Causeway instead makes an **empty cell behind the carrier** a resource. Filling
it denies the existing Repulse command while preserving the hero's action.
Guard offers the other legal counter but gives up that action. The same army
then has different soldiers and mana available to remove the exit blocker.

This shares extraction, Swap delivery and exit clearing with existing sites.
It earns a separate pattern only if players can read and use the displacement
decision. If it feels like another Courier Crossing after a rote opening,
reuse the layout as a Crossing variant rather than counting a twelfth family.

## One bounded layout

Radius three, 37 cells. Columns `q=0` and `q=1` are marsh except `(0,0)`;
all other cells are plains. Exit `(3,-3)` must be reached and explicitly
evacuated before the end of round five. Cargo reduces hero movement by one,
with the existing minimum; rout also wins and hero death loses.

| Side | Deployment, in actual saved roster order |
|---|---|
| Hero, then up to six troops | `(-3,0), (-2,-1), (-3,1), (-2,0), (-2,1), (-3,2), (-2,2)` |
| Rune Adept, Pikeman, Ranger, Dread Guard | `(0,0), (2,-1), (2,1), (-3,3)` |

There is one free assembly in this first probe. The alternatives are ordinary
manual control plans, not two names for identical deployments or a nominal paid
shortcut. A second entry choice remains a production design gate, if this
family is accepted. Neither a second terrain layout nor a new fee is justified
by the current evidence.

## Paid parties and manual results

Both preparations use actual Standard seed-seven campaigns, ordinary conquest,
recovery, earned skills and prerequisite purchases. Commander spends **279 gold
and two crystals**: Barracks 45, Warden 55, Temple 65, discounted Acolyte 39 and
Mage Tower 75 gold/two crystals. It arrives turn five at level three with six
bodies. Scout spends **175 gold and two crystals** on Barracks, Warden and Tower,
arrives turn five at level three with five bodies, and retains its original
two Militia and Archer. Both carry their earned Moonstone. The Scout follows
a different preparation itinerary; these are not isolated recruit-price tests.

| Plan | Outcome | Missing HP | Mana spent | Dead allies |
|---|---:|---:|---:|---:|
| Same Commander, occupied landing + early Bolt | Escape round 4 | 28 | 12 | 0 |
| Same Commander, Guard + advance the spare Militia | Escape round 4 | 34 | 8 | 0 |
| Smaller Scout, oblique ranged approach | Escape round 4 | 41 | 4 | 0 |

All three leave a living enemy Guard behind. Every order is manual and followed
by an exact full `State` save/reload. All attacks and spells compare the actual
HP change with the public forecast. Commander requires an explicit Warden
Swap and then Evacuate; swapping onto the exit alone does not finish the battle.
The Scout needs neither Swap nor hero Guard, and no Acolyte is a hidden slot
requirement. The Commander's Acolyte supplies ranged damage in these routes;
these results do not establish a need for its Heal capability.

The shared Commander opening places the hero at `(-1,0)` next to the Adept.
The Adept's push destination would be `(-2,0)`. The occupied-landing plan puts
Militia 2 there and spends the hero's action on Bolt. The Guard plan sends
that Militia toward `(0,-3)` and Guards the hero instead. Because the delayed
Militia cannot reach the exit Pike in time, the first line spends an additional
four mana to clear it. The advanced Militia in the second line takes a real
six-damage Brace hit and finishes the Pike.

The cheaper-mana Guard line leaves the hero at 16/44 HP and Militia 2 at 26/32.
The occupied-landing line leaves the hero at 30/44 and Militia 1 at 18/32.
Four more mana buys six fewer total wounds, distributes damage away from the
carrier and saves no battle round. This is a modest, measured tradeoff—not a
claim that the costlier line is universally better or recovers faster.

## Counterexamples and finite failure

- An exposed Commander casting the same early Bolt, with the landing cell
  empty, really is pushed to `(-2,0)`. The enemy's one Repulse charge is spent
  and preserved by the active-battle save. The initial formation matters.
- Guard is not mandatory. Blocking the destination works using ordinary
  occupancy, and Scout takes another angle. Current extraction AI pushes only
  the hero and only when the destination increases distance from the nearest
  exit. At the Scout's `(0,-1)` angle, a push to `(0,-2)` would not do so; the
  Adept attacks instead. This is measured current AI behavior, not a general
  geometric immunity or proof that every ranged hero survives.
- After denying the first Repulse, the enemy Adept moves toward the exit. This
  is an opening formation/action choice, not evidence that the player must
  Guard every round or that enemies repeatedly spend one charge.
- The explicit failed line kills the wounded Adept after being pushed, then
  deliberately Guards until the round-five deadline. It loses no troop but
  takes 31 wounds, spends four mana and pays the normal 20-gold retreat fee.
  It earns no XP, reward or choice. This is a persistence fixture, **not proof
  that the initial displacement forces defeat**; a recovery line may still win.
- After that loss, the site saves exactly Pikeman 28 HP, Ranger 22 HP and Guard
  28 HP. Three public recovery turns preserve the live rival and restore the
  party. The retry uses explicitly labeled automatic play and routs in round
  three, with 21 wounds and 12 mana spent. The dead Adept never reappears.
  Existing retry deployment packs survivors into the selected layout's first
  enemy slots; the probe does not promise their old tactical positions persist.
- Both escape and retry pay the inherited saved reward once. Repeating
  `explore` or `resolve_battle` after completion raises the normal `RuleError`
  without changing the complete saved state.

## Honest fixture and source scope

The throwaway process temporarily registers one `SiteSpec` and `EncounterSpec`,
copies each fully earned campaign, and changes only the current province's site
name/kind and finite defender kind/HP arrays. This installation is **authored
fixture setup**, not a player command. The original paid campaigns remain exact.
All exploration, battle orders, failed resolution, recovery and reward choices
then use the public production model, including its ordinary save validator.

Commander inherits the copied Crossing's actual 50-gold/two-crystal/Censer
reward; Scout inherits Explorer's 55-gold/one-crystal/Boots reward. Those are two
separate hypothetical fixtures, not proposed Causeway rewards or a change to
either guaranteed source. Neither original source is replaced in production.
There is no old-save migration claim: this prototype has no schema change or
persisted installed content, and temporary prototype saves require this tool's
registry context to load.

No fixed world coordinate is proposed. Production must first audit an optional
ordinary duplicate whose unchanged survivor retains the exact reward and no
harder guard route, excluding every fixed source and western fallback. Do not
replace a unique affordable route merely because its relic remains obtainable
behind the new encounter. A real paid trip to the chosen source, both entry
choices if added, difficulty/seed coverage, an actual prior-site continuation,
independent counterplay review and native forecast/retry journeys remain gates.

## Reproduce and review

This is archived prototype evidence, superseded by the
[production Causeway](eador-causeway.md). Its temporary registry/tool was absorbed
into the ordinary content and public route helper, then deleted. To reproduce
this historical report, use a detached checkout of the source below and run
`uv run python tools/prototype_eador_causeway.py`. The
default report is `/tmp/causeway-prototype.json.gz`; `--step` shows unit state,
resources, forecasts and each next order, advancing with Enter or quitting with
`q`. The [retained report](evidence/causeway-prototype-2026-09-06.json.gz) was
produced at source `f4cf6fb07bd261731b86fea48637cf276c4f500e`. It includes exact
paid campaigns and purchase bills, all 161 order/reload checkpoints and
settlement/recovery snapshots. All 44 recorded source hashes match that Git
revision; no production source changed. The compressed file is 30,156 bytes,
SHA-256 `f9b45f3c039b3390ca455dcfab24d4b6aeaadf8a557900e59e90d7ba8e0d1466`.
The prototype assertions and 78 existing public Guard/control/extraction tests
passed; the terminal step/quit path was also exercised. Independent review is
still pending. This is source-attributed model evidence, not native gameplay.

Reject or fold this into another family if independent play finds no meaningful
action/formation consequence, a cheap universal bypass makes the Repulse
decision irrelevant, it cannot be taught clearly, or safe placement destroys an
existing route. A cheaper flank is legitimate counterplay; it should be retained
and measured, not prohibited by a new tactical rule to protect the proposal.
