# Ninth encounter: develop the Smuggler Screen

Design probe, 2026-09-06. The accepted direction is a rout against an enemy
Sapper, two Archers, a Warden and a Dread Guard. This document records the
comparison before production content, approaches or campaign consequences.
It does not establish a ninth accepted pattern or complete G05.

| Candidate | Actual decisions and counterplay | Measured limitation |
|---|---|---|
| Caravan Anchor | Two Pikemen, Archer and Warden on a hill/forest approach. An actual braced Pikeman forecasts four damage taken before a melee hit; the Ranger can shoot it for four without taking damage. | The successful main plan simply focuses the first approaching pike and ignores the other one's temporary Brace. It remains too close to ordinary focus fire and Pack Hunt's deployment choice. Discard this production direction. |
| **Smuggler Screen** | The Sapper spends its one Smoke charge on our Ranger's hex. The Ranger must relocate to restore sight while a Dread Guard presses that position. Two bowmen punish an exposed relocation, and the enemy Warden rescues a damaged Sapper if focus fire stops early. | The tested army is earned, but moderately developed. A second approach and a smaller/different-class party still need complete manual proofs. Do not infer broad balance from these one-seed plans. |

A proposed field-hospital alternative was rejected at the rules check: enemy
Acolytes cannot currently cast Heal or spend player mana. A hospital would need
a new enemy resource system, which is outside this content increment.

## Reproduce the pure model comparison

`tools/prototype_eador_screen.py` is deliberately throwaway. It temporarily
registers a local `EncounterSpec` during ordinary `Battle.create`, removes it,
then uses public manual commands. Every attack/Heal checks its exact immediate
forecast; every command serializes and reloads the whole Battle. The ordinary
campaign preparation remains unchanged after these detached battles.

```sh
PYTHONPATH=. python tools/prototype_eador_screen.py --output /tmp/screen.json
```

The party comes from `prepare_explorer()` using actual Standard seed-seven
purchases, conquests and recovery. It reaches campaign turn eight with a
level-three Commander, two level-three Militia, a level-three Archer, a
level-three Warden and a level-two Ranger. Barracks/Archery cost 100 gold;
Warden/Ranger cost 98 after the earned recruitment discount. It has ten mana,
Heal and an equipped Moonstone. No stat, resource, army or experience injections
occur. The report records the actual purchase calls and complete prepared save.
This is an earned party demonstration, not the proposed site's travel route.

| Same earned party | Outcome / round | Soldier deaths | Missing HP, including dead units | Mana spent | Public commands |
|---|---|---|---|---|---|
| Anchor manual | Rout / 4 | 0 | 23 | 4 | 33 |
| Anchor auto | Rout / 3 | 0 | 35 | 0 | 3 |
| Screen manual, finish now | Rout / 4 | 0 | 62 | 0 | 37 |
| Screen manual, Heal before finishing | Rout / 5 | 0 | 44 | 4 | 39 |
| Screen auto | Rout / 5 | 1 | 54 | 8 | 5 |

The two candidate rosters have different enemies and sizes; these totals are
not a controlled claim that one is harder or better. The paired Screen plans
are directly comparable: replacing the final hero attack with Heal spends four
mana and one battle round to finish with eighteen fewer wounds. No campaign
turn elapses merely because that battle uses an extra round. Auto is a baseline
policy, not a prediction of human play.

## Concrete Screen geometry and orders

The current prototype uses the existing radius-three, 37-hex board. Forest is
at `(-1,-1)`, `(0,1)` and `(1,-2)`; hills at `(1,0)` and `(2,-1)`; other hexes are
plains. Player positions in ordinary hero/army order are `(-3,0)`, `(-2,0)`,
`(-3,1)`, `(-2,-1)`, `(-3,2)`, `(-2,1)` and the optional seventh `(-3,3)`.
The Sapper starts `(1,0)`, Archers `(2,-1)` and `(1,-1)`, Warden `(2,0)` and
Dread Guard `(1,1)`. There is no seal, extraction exit or special deadline.

The completed manual line has four understandable phases:

1. Guard the formation and let the first advance reveal the cloud. The Sapper
   actually screens the Ranger's occupied `(-2,1)` endpoint, so its target list
   becomes empty; an Archer Pins a Militia. This waiting opening is a tested
   option, not an assertion that aggressive openings cannot work.
2. Move the Ranger around the cloud to `(-1,3)` and fire at the advancing Guard.
   Warden and Militia clear the southern road and engage that Guard; the hero
   joins them. Keep our Archer back to shoot the northern enemy bowman. An
   otherwise identical Ranger relocation to `(-1,1)` dies under the enemy's
   concentrated next phase: restoring sight alone does not make a position safe.
3. Finish the northern Archer. Ranger plus hero focus the wounded Sapper before
   it can be rescued; Warden finishes the one-HP Guard. Militia engage the enemy
   Warden while the Ranger moves around the forest. In a saved counterprobe,
   stopping after the Ranger's Sapper shot lets the enemy Warden swap its wounded
   ally from `(-1,0)` to `(0,0)` on the next enemy phase.
4. Reposition both bow units for sight and finish the Warden; Militia wounds the
   last Archer. Either the hero finishes immediately or uses Heal and accepts one
   further enemy phase. Both are legal, complete wins without casualties.

Smoke persists until its ordinary expiry even if the Sapper dies. Neither the
prototype nor the proposal gives enemies free new charges, healing mana or
special scripted orders. Enemy control and rescue use the current battle AI.

## Bounded production direction

Develop **Smuggler Screen**, provisionally at Elderwild `(0,-1)`. Keep the
existing Shrine, Watch, Cache, Hunt, Den, Explorer's Camp and western Grove
fallback. A plausible reward is 60 gold, two crystals and Veil Censer: earning
the same finite ability the defenders demonstrate, while preserving the
original Crossing/Censer source. These are proposed metadata, not yet changed.

Compare the tested western column with a **free northern assembly** of the
combined army. The latter should challenge bowmen earlier but expose support to
more direct fire. Actual paired manual orders must determine the final positions
and whether this creates a useful choice. Do not add a nominal paid shortcut,
a split-carrier objective or a terrain-opening option copied from Observatory.

Before production handoff, add ordinary paid preparation at the real site, both
approaches with the same party, at least one smaller/different-class party,
visible pre-entry finite abilities, exact old-world continuations, and a saved
failed attempt/retry with persistent wounds and one reward. Audit required
sources across 100 seeds and replay through native controls. Absorb/delete the
prototype once the accepted content has these public journeys; retain its
source-specific evidence as a historical design comparison.
