# Stranded Explorer: recover a separated party

The new Frontier adventure at `(0,-1)` sends the hero across a marsh belt to
recover a trail kit. The fifth troop, if present, is isolated with the hero;
the other troops assemble north or south of the western return exit. Both
assemblies are free and preserve the same terrain, four finite defenders and
reward. A smaller party begins with the hero alone in the east.

Escape requires an explicit hero order at `(-3,1)`, with no adjacent enemy,
by round six. Rout remains an alternative; hero death or a missed deadline
loses. Success awards 55 gold, one crystal and Wayfarer Boots. The existing
Explorer's Camp remains a Boots source. If the player has already earned them,
the reward explicitly offers four crystals for distilling the duplicate or
35 gold for selling it; neither option adds a second copy.

This eighth-family tranche uses existing `EncounterSpec`, approaches, Battle
commands and saved attempts. It adds no tactical mechanic, schema field,
generic scenario system or Saga2D code. The throwaway prototype has been
absorbed into production content and the public campaign helper, then deleted.

## Paid, saved tactical evidence

`tools/eador_explorer_campaign.py` buys a Warden and optional escort, develops
the western road and reaches the actual northern site. It accepts a State-like
input adapter. No resources, troop levels, positions or battle statistics are
injected. These Standard seed-seven plans use earned level-three heroes:

| Party / assembly | Campaign arrival | Building / recruit gold | Manual rounds / wounds / mana | Same-party auto rounds / wounds / mana |
|---|---|---|---|---|
| Commander, Warden/Ranger; north | 8 | 100 / 98 | 3 / 22 / 0 | 3 / 34 / 4 |
| Same party; south | 8 | 100 / 98 | 3 / 25 / 0 | 3 / 32 / 8 |
| Warrior, Warden/Acolyte; north | 9 | 110 / 100 | 3 / 24 / 4 | 3 / 29 / 4 |
| Scout, Warden only; north | 5 | 45 / 55 | 2 / 10 / 0 | 4 / 47 / 4 |

All manual plans escape with every player alive and enemies remaining. All
four auto runs win by rout; the small Scout auto run loses one troop. The
Scout's five-body manual plan therefore saves a troop, two phases, 37 HP and
four mana in this paired comparison. These are specific paid plans, not
optimality or all-build balance claims.

The northern Ranger helps kill the bowman occupying its short road, then
uses its retained move to follow the hero west. The main force screens the
return exit while the enemy Warden uses its actual Swap behavior to rotate a
guard. In the southern plan the player Warden first extracts the exposed
Archer; on the next turn it returns to deliver the arriving hero. A direct
southern screen without that rescue took 33 wounds in the early probe; the
retained rescue plan takes 25. The assemblies remain free: the measurements
do not justify describing the southern one as a purchased upgrade.

The Warrior's earned Duelist build clears the bowman without Ranger fire; its
Acolyte heals the screen. The Scout begins alone across the marsh and uses
earned Pathfinder plus a rear Archer's support shot. Neither route depends
on a hidden Ranger escort. Pre-entry presentation must identify the actual
isolated bodies, including the hero-alone case.

Source `5cdb39e` retains **60 exact saved manual escapes** across Accessible,
Standard and Challenge; seeds 0, 1, 2, 7 and 19; and all four plans. No player
dies in those manual runs. The 60 paired automatic battles also win by rout.
Every manual order reloads exactly; attack and Heal forecasts match their
immediate effects, and rewards are verified once. See
`docs/evidence/shardbound-explorer-2026-09-06/paid-mode-routes.json` for actual
orders in the four Standard seed-seven plans, all measurements and hashes.

## Failure, source and compatibility checks

Ten public integration tests cover both assemblies and all party variants,
100 seeds, real retreat and deadline losses, paid replacements, saved retries,
duplicate conversion and exact prior-save continuation. Missing the deadline
kills a Militia in the retained plan and costs the ordinary 20-gold retreat
loss. Buying replacements and recovering permits a successful southern retry;
the dead troop does not respawn and the patrol keeps its surviving wounds.
Voluntary retreat likewise preserves a killed bowman and the remaining wounds.

The 100-seed audit keeps Frontier's Shrine, Watch, Den, Camp, Muster Yard and
Crossing, including their guaranteed rewards. All twelve relics remain
discoverable across the three themes. A real prior `11797b8` active Caravan
save at `(0,-1)` remains a Caravan and reaches the exact complete v12 result;
loaded world arrays are not regenerated. The only adjusted difficulty test
assertion had compared a freshly generated world to old v11 content. Exact
loaded before/after comparisons remain intact.

The full suite passed 959 tests at the production checkpoint `e041337`;
the subsequent deadline/replacement regression passes with all ten focused
Explorer tests at `5cdb39e`. Native plans and enlarged briefing layout are
verified separately by the root UI work. Model/mock reports here do not by
themselves establish native acceptance or completion of G05.

The same source passes 300 randomized campaigns and 20 mock scene runs with
10,003 random inputs. Both assemblies are exercised; source hashes remain
unchanged. This is robustness evidence, separate from the paid tactical plans.

To replay through a model or input adapter, use `prepare_explorer(...)` and
`explorer_route(..., 'north'|'south')`, `explorer_healer_route(...)`, or
`explorer_scout_route(...)`. Pass `support='healer'` for the Warrior plan and
`support=None` for the smaller Scout party. `collect_boots=True` also plays the
Camp first, reaching the actual duplicate reward choice. Each route accepts
`orders_type`; production helpers do not import tests.

## Integrated native acceptance

Source `0e27175` completes all four purchased manual plans through the shipped
controls: 559 input activations and 28 exact save/reloads, with every ally alive.
Commander north/south and Warrior/Acolyte escape in round three; the smaller
Scout party escapes in round two. Fees, once-only rewards and refusal to repeat
a cleared site are checked through the same input path.

The [retained native reports and inspected frames](evidence/shardbound-integrated-0e27175/README.md)
include Swap, Heal and evacuation forecasts. The complete guidance matrix also
covers both deployments and all three actual isolated-party compositions at
100/125 and three native window sizes. Counts and persistent defender HP no
longer collide with the footer. This completes the eighth authored family's
current development tranche; the twelve-family floor and wider G05 remain open.
