# Aerie Raid

Aerie adds an airborne rout to the authored encounter families. Flyers cross
marsh and occupied ground, commit to an empty landing, then fight under the
ordinary melee/Brace rules. The two free assemblies keep the same terrain,
four finite guards and reward. No battle rules, save schema or Saga2D API change.

New Ruins shards place it at `(0,0)`, replacing that checkpoint's ordinary
Barrow. The guaranteed Barrow at `(1,0)` retains Iron Crown. Shrine, either
Watch, Den, Explorer's Camp, Muster Yard, Crossing, Vault, Observatory, Explorer,
Screen and the western `(-2,1)` fallback retain their locations. The province's
existing garrison, terrain, income and ownership stay unchanged. Success grants
60 gold, two crystals and Watch Bell; the original Watch remains a Bell source.

The discarded `(0,-1)` location preserved reward IDs but removed the weaker
northern road's Tower. Keeping that road intact better preserves the existing
Ruins route decision. A complete comparison with 300 historical generated worlds
(100 seeds per theme) changed only the new site's seven stored content fields
in Ruins; every world's previously available relic set remains available.

## Actual purchased plans

`tools/eador_aerie_campaign.py` accepts an ordinary State or the native input
adapter in `prepare_aerie(state=...)`. Preparation resolves prior conquest with
the explicit auto command, purchases its buildings/troops and travels to the
real unexplored Aerie. Encounter routes use only manual orders and accept an
`orders_type`; no resources, positions, XP or statistics are injected.

| Standard seed seven | Paid buildings + troops | Arrival | Route | Rout round | Missing HP | Mana used |
|---|---|---|---|---|---|---|
| Commander, Pike/Adept/Skyrider | 395 gold + 7 crystals | Turn 8, level 3, seven bodies | Western reserve | 4 | 53 | 4 |
| Same complete prepared save | Same | Same | Western with Heal | 4 | 45 | 8 |
| Same complete prepared save | Same | Same | Northern perch | 3 | 34 | 8 |
| Scout, Pike/Warden | 200 gold, no crystals | Turn 5, level 2, six bodies | Western ground escort | 5 | 27 | 4 |

All four retain every soldier in the encounter. The Commander cost includes
Market, Barracks, Mage Tower and Temple; its earned Quartermaster discounts
purchases. The Scout has only Market/Barracks and spends 95 gold on its two new
troops. These are paid preparations, not equivalent-strength armies or universal
policies. The expensive army is not a necessary purchase to clear the site.

Western Commander lets the raid land behind its line. Archer fire weakens the
rear flyer; the Adept moves around it and uses Repulse to put it beside the
Pikeman's new braced position. The Militia occupies the vacated caster hex.
Only then does the player's Skyrider cross to the eastern bow. A query with the
same base movement but only `fly` removed cannot reach that landing. The query
is a counterfactual, not a modified unit used in the actual plan.

Northern Commander instead kills the nearby flyer with focused attacks and
Bolt before the first enemy phase. The remaining flyer attacks the rear Archer.
The second Militia opens the rear corridor; the player's flyer vacates the
hero's retreat hex, then the hero moves and heals the forward Pike, freeing the
Adept's ground path to finish the rear raider. The flyer's different hill
landing lets it engage the eastern bow. Repulse remains unspent. This is a
preemptive concentration and ordered corridor opening, rather than the western
reaction trap. It spends four more mana than the western reserve to win a phase earlier
with fewer wounds. Western can also spend that mana on Heal for eight fewer
missing HP. These are measured decisions, not an optimality claim for other parties.

The smaller Scout has no flight or Repulse. Its Warden absorbs the two landings
while the army concentrates on one flyer at a time. Warden Swap then pulls a
wounded Militia away from the spear front. A heal and staged ground advance
close on the Archer. The plan also exposes the ordinary enemy Pin, without
inventing a special anti-flight ability or new terrain exception.

The existing linked six-body Gate demonstration also encounters this optional
site during preparation. Aerie attrition can replace its veteran screen Archer
with a fresh recruit. The Warrior/Scout demonstration now permanently retires
a rear Swordsman and pays 45 gold plus one campaign action for an Acolyte before the final assault. Its second
shared-mana Heal keeps that fresh screening troop alive while the hero heals the other
Archer. The original round-two hold and all-combatants-alive assertions remain;
no battle statistic or deadline was weakened. Wizard retains the original plan.

## Persistence and failure evidence

The deliberately premature western sortie loses the actual purchased Skyrider
on the first enemy phase. Continuing to Guard without advancing toward the
surviving bow eventually loses the hero at round 56. This artificial refusal to
advance is persistence evidence, not representative encounter pacing. Five
soldiers die; the wounded Pikeman survives. Existing loss rules remove 20 gold
and award no XP or site reward. The stored site contains only an Archer at
12 HP; all three dead enemies stay dead.

After saving that loss, a replacement Skyrider costs 60 gold and three crystals.
The other free assembly contains exactly the wounded Archer. A single Bolt
finishes the saved retry and grants the reward once. Retrying or resolving again
is rejected without altering state. The replacement purchase is recorded for
accounting; the final Bolt does not require that replacement to win.

`v12_pre_aerie_barrow_battle.json` and its result fixture were produced using
actual source `0745f6c` in an isolated archive before Aerie content existed.
The new public preparation helper was copied into that archive only to supply
ordinary purchases/travel; no old game file was changed. It explored the real
Barrow at `(0,0)`, guarded through one enemy phase, then recorded the active
save and its completed auto/reward continuation. Current loading preserves the
entire initial payload and exact completed result, including the old world.
Unentered future shards use current generation under the existing
[saved-world policy](eador-save-continuation.md).

Run the production audit with:

```sh
PYTHONPATH=. python tools/audit_eador_aerie.py --output /tmp/aerie-production.json.gz
PYTHONPATH=. python -m pytest -q tests/eador/test_aerie.py
```

The audit checks exact attack, spell and Repulse forecasts, reloads complete
campaign state after every order, records purchases and final reward rejection,
and saves compressed snapshots with source hashes. The shared guidance matrix
includes both actual assemblies at 100/125% and all three supported window
sizes. Native full-plan integration and broader release judgments remain
separate acceptance work. This pattern's count alone does not satisfy G05.

The [earlier detached prototype](eador-tenth-encounter-proposal.md) remains as
compressed historical evidence. Its temporary tool is absorbed by the real-site
preparation and production audit; its original source commit remains replayable.
