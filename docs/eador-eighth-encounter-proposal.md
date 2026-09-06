# Eighth encounter: prefer a split rescue

Design probe, 2026-09-06. This is a proposal using the current rules, not a new
registered site or a G05 completion claim. The release criteria require useful
decisions, visible consequences and complete alternatives; another seal with
a different forest lane would repeat the Observatory's problem.

| Candidate | Decision and existing rules | Counterplay / pacing | Public route feasibility |
|---|---|---|---|
| **Stranded Explorer — extraction** | Hero and an escort start beyond a marsh belt; the main army assembles north or south of the return exit. Choose how the two groups reconnect, or rout the enemy. Reuses authored deployments, existing extraction, Ranger reposition and Warden Swap. | Ranged pressure threatens the isolated pair while a guard and Warden approach the rear force. The two player groups initially have different jobs. A three-round rescue can preserve resources without a faster win. | One earned six-body manual escape now works; both deployments have automatic rout baselines. The second manual route and other escort/hero combinations remain acceptance work. |
| Caravan Anchor — rout | Free head-on assault against Pikeman/Archer/Warden, or pay for flank deployment. Ranged focus avoids Brace; waiting can reopen Repulse; Warden movement disrupts focus fire. No named-guard removal, which would need new saved state. | Strong formation puzzle with a useful enemy combination, but another bought deployment risks repeating Pack Hunt. Rout may become ordinary focus fire after one anchor dies. | Easy to fund through Barracks/Archery and compare; needs a demonstrably different flank plan before it earns another pattern. Worth keeping next in the queue. |
| Pilgrim's Vigil — hold | Near-seal deployment for base reward, or a farther start for an explicit bonus using the existing `bonus_gold` and selected layout. No mana-restoration entry effect: that does not exist yet. | A tempo-versus-loot decision is expressible now, but a stronger army could erase the distance cost and produce a dominant bonus choice. It overlaps Watch/Gate unless timing remains consequential. | Public paid armies can test it, but this needs more design work than a new seal coordinate. Do not implement merely to fill a hold allocation. |

Choose **Stranded Explorer**. Cache currently surrounds a combined army;
Crossing and Vault send a combined army toward a distant exit. This candidate
separates the carrier from its main force, makes the safe exit a defended
regrouping point, and gives mobile fire a concrete road-clearing job.

## Concrete prototype

`tools/prototype_eador_rescue.py` is a throwaway pure-model experiment. It
temporarily registers an in-memory `EncounterSpec` only while calling ordinary
`Battle.create`, then removes it. It uses existing public Battle commands and
checks exact Battle serialization after each one. It does not test production
State adventure validation, fees, rewards, world placement or native input.
Delete or absorb it after the design decision; do not make it a new engine.

The battlefield uses the existing radius-three, 37-hex board:

- Hero starts at `(3,-1)`; the fifth troop, when present, starts at `(2,-1)`.
  The other four deployed troops begin west of the marsh. The prototype's
  fifth troop is a purchased Ranger. That positional identity must be explained
  before entry and tested with other armies before production acceptance.
- Northern main formation: `(-3,0)`, `(-3,1)`, `(-2,-1)`, `(-2,0)`.
  Southern alternative: `(-2,3)`, `(-1,3)`, `(-2,2)`, `(-2,1)`.
  The optional seventh body has a western starting slot in either layout.
- Marsh: `(0,-1)`, `(0,0)`, `(0,1)`, `(-1,0)`. Forest: `(-1,-1)`, `(1,1)`,
  `(-2,2)`. All other cells are plains; approaches do not change terrain.
- Pikeman `(1,0)`, Archer `(1,-2)`, Dread Guard `(0,2)`, Warden `(-1,2)`.
  Both layouts keep these same four defenders, their ordinary stats and HP.
- One western exit at `(-3,1)`, explicit hero evacuation, adjacent enemies
  contest, deadline six; rout remains an alternative and hero death loses.

The prototype keeps both assembly choices free. Their consequence is where
the main force meets the guards, not a hidden modifier. Do not price one until
manual comparison justifies what the fee buys. A possible later source is a
new Frontier site at `(0,-1)`, creating a northern alternative to the southern
Crossing while preserving Shrine/Watch/Den/Camp/Muster Yard. Placement and
rewards are hypotheses, not changed production data.

## Measured plans and what they establish

Preparation uses `prepare_adventure(support='ranger')` with real seed-seven
Standard commands. It spends 100 gold on Barracks/Archery and 98 gold on a
Warden/Ranger. After ordinary conquests and recovery it arrives on campaign
turn six with a level-three Commander, four level-three starting/earlier
troops, a level-two Ranger and 14 mana. No army/resource/stat injections occur.
This is an earned mid-shard army, not a new-game starting-party demonstration.

| Same prepared army | Outcome / round | Player deaths | Missing player HP | Mana spent | Surviving enemies |
|---|---|---|---|---|---|
| Northern manual rescue, 30 public orders | Escape / 3 | 0 | 22 | 0 | 2 |
| Northern automatic play | Rout / 3 | 0 | 34 | 4 | 0 |
| Southern automatic play | Rout / 3 | 0 | 32 | 8 | 0 |

The manual rescue saves twelve HP and four mana against this exact auto
baseline without saving a round. Southern auto spends four more mana to save
two wounds compared with northern auto. The latter is a feasibility signal,
not proof that humans face the same trade or that either approach dominates.

The 30-order rescue has three understandable phases:

1. The Ranger shoots the isolated northern Archer; the hero finishes it. That
   occupied hex initially blocks the Ranger's short road west. The kill opens
   it, and the Ranger still has its move after shooting. The western Archer
   wounds the Pikeman while Militia and Warden begin screening the return.
2. The Ranger vacates the next road segment before the hero crosses it. The
   Militia cover the southern approach and the Warden occupies the exit. The
   player does not pursue the guard. The enemy Warden uses its actual Swap
   behavior to rotate with that guard; it is not a stationary target fixture.
3. The Ranger shoots the wounded spear and clears the road again. The hero
   reaches `(-3,0)`, the Warden swaps it onto the exit, and the player explicitly
   evacuates. Two defenders remain alive; the hero is unwounded.

An earlier Pin order was removed: body screening already prevented that
guard's approach, so slowing it was unnecessary. The final plan uses an
ordinary shot there. Do not advertise Pin or a new role as necessary when the
demonstrated geometry does not require it.

The full layout, ending units, battle logs, public orders and source hashes are
in `docs/evidence/stranded-explorer-prototype.json`, from `dcb626a` after merging
main's Standard-compatible schema v12. Run:

```sh
PYTHONPATH=. python tools/prototype_eador_rescue.py --verbose --report /tmp/rescue-prototype.json
```

## Before this could become an accepted eighth pattern

Implement only after root reviews the design. Preserve one finite defender
roster and one reward across attempts, and add the new site ID without changing
old saved Camp/Caravan identity. First prove a southern manual alternative and
a different hero/escort army; no requirement for a particular fifth-slot
recruit should be hidden from the player. Demonstrate ordinary attack, rescue
and a failed retreat/save/retry through the State command boundary, then real
input with an explicit split-deployment briefing and exact forecasts. Check
100-seed required sources and current difficulties before a content claim.

The prototype answers whether existing rules can support this distinct
problem. It does not yet establish broad balance, complete approaches, campaign
consequences, onboarding clarity, native usability or G05 acceptance.
