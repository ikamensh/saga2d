# Support, mobile fire and extraction

The game-owned model at `79b2d49` adds tactical Acolyte healing and two new
recruits. This is progress toward G04/G08, not completion of either gate.
There are seven recruitable roles and eight relics. No new authored encounter,
entry choice, obstacle system or framework strategy abstraction is claimed.
The model evidence below belongs to its original revision. The player-control
integration described at the end is a later checkpoint.

## Orders and costs

| Role | Access and base stats | Decision and counter |
|---|---|---|
| Acolyte | Existing Temple recruit, 45 gold / 2 upkeep; 22 HP, 7 attack, 2 defense, move 3, range 2. | Can spend its own order on Heal, freeing the hero to attack, control or Guard. Uses the same finite mana as hero magic; focus fire and mana exhaustion counter sustain. Existing resting recovery remains. |
| Ranger | Archery Range, 50 gold / 2 upkeep; 22 HP, 7 attack, 1 defense, move 3, range 3. | Shooting preserves unused movement. Moving first gives no second move. Its weaker shot and armor trade holding power for repositioning; Pin, blocked escape space and ranged pressure counter it. It has neither intrinsic Pin nor terrain-cost immunity. |
| Warden | Barracks, 55 gold / 2 upkeep; 38 HP, 8 attack, 4 defense, move 2, range 1. | Exchanges places with an adjacent ally, taking the exposed position. Both lose remaining movement; the Warden spends its action, while the ally retains any unspent action. It trades attack damage and speed for extraction. |

Ranger and Warden append to the existing five recruitment choices. These
accessible building gates deliberately precede the adventure-unlock ideas in
the longer [tactics proposal](eador-tactics-design.md). That proposal's later
Knight, Hexbinder, Sapper and additional relics remain unimplemented.

## Small public interface

```python
# Existing hero calls keep their meaning; None selects the hero.
battle.cast('heal', target_id)
# Acolyte orders use the same targeting, range, power and shared budget.
targets = battle.spell_targets('heal', caster_id=acolyte_id)
amount = battle.spell_preview('heal', target_id, caster_id=acolyte_id)
battle.cast('heal', target_id, caster_id=acolyte_id)

allies = battle.swap_targets(warden_id)
battle.swap(warden_id, ally_id)
# Ordinary Ranger attack/move commands; no second movement resource.
losses = battle.preview(ranger_id, enemy_id)
battle.attack(ranger_id, enemy_id)
remaining_cells = battle.reachable(ranger_id)
```

`BattleUnit.can_heal` and `can_swap` expose troop capabilities.
`spell_targets` returns an empty list when the caster cannot act.
`spell_preview` returns actual positive HP restored or removed, including the
maximum-health clamp; illegal forecasts and commands raise `RuleError` without
mutation. Heal reaches four hexes and uses current Restoration/Moonstone power
and cost. It spends the caster's remaining movement and action. Troop healing
does not require the hero to know Heal, so an Acolyte carried to a later shard
still functions before rebuilding a Temple. Hero-free armies have no mana
source, and enemy Acolytes cannot spend the player's reserve.

Swap permits an ally that already moved or acted, including a hero. It never
refreshes actions, erases Pin, changes Guard/Brace, targets an enemy, or moves
through an intermediate hex. A Warden may move into adjacency before swapping;
the exchange then consumes its remaining order. Forced movement is one adjacent
exchange, so Pin does not prevent it. Ranger movement uses the existing
`skirmisher`, `effective_move_range` and occupancy rules.

AI Acolytes heal substantially wounded allies when mana permits. Rangers use
unused movement after firing to reduce exposure; enemy Archers recognize their
escape and use Pin when a nonlethal slowing shot is useful. Rangers holding a
seal, and enemy Rangers contesting one, preserve the objective position.
Wardens can replace a more exposed, badly wounded ally. These are local battle
policies, not a new strategic engine or an optimal-play claim.

## Save continuity and evidence

Schema 9 accepts the new `heal` and `swap` capabilities only on their proper
troop kinds. Ranger uses the already-saved skirmisher flag; no new status field
or migration rewrite is needed. Loading an active v8 battle preserves all its
existing capabilities, action flags, province arrays and rewards. An older
active Acolyte therefore keeps its old non-casting continuation; newly created
battles use current troop definitions. A real v8 linked campaign with an active
Acolyte was recorded before the change and continues to the same full state,
excluding only the schema tag.

At `79b2d49`, 705 tests passed, including sixteen public role cases. A paid
seven-turn opening builds the necessary facilities, recruits all three roles,
and reaches Border Watch. Its manual formation uses a Ranger shot followed by
rotation, swaps the wounded seal holder with a Warden, heals the extracted
soldier with an Acolyte, and holds by round three with the enemy Archer alive.
Saves between each order preserve the continuation and the site rewards once.
A paired Watch case shows Pin delaying a ranged defender's arrival at the seal
while leaving its attack available. This demonstrates these plans on existing
content; it does not establish that each order is necessary for every victory.

An independent model-agent review found no concrete blocker in casting,
Swap, movement costs, AI, saved status or v8 continuation. Further retained
checks use clean source hashes from the same revision:

- [1,000 randomized battle fixtures](evidence/shardbound-roles-battles-2026-09-06.json): 250 each rout, Border Watch, Last Gate and hero-free clash; 5,297 exact damage/healing forecasts, 815 manual Heals, 1,029 Swaps, 101 Pins, 289 Ranger shot-then-moves, and 6,413 roundtrip checks. Both enemy and player policies run. Fixtures deliberately include wounded troops and are not campaign win-rate evidence.
- [300 randomized campaigns](evidence/shardbound-roles-campaigns-2026-09-06.json): 100 per theme, 46,348 state/roundtrip checks, 1,050 recruits, 12,494 rejected commands and 3,170 resolved battles. The random policy lost 296 and won four; this is robustness evidence, not a prepared-strategy acceptance result. No scene runs were included in this model-only check.

Reproduce with `python -m pytest tests/eador/test_roles.py -q`,
`python tools/stress_eador_roles.py --cases 1000 --report /tmp/roles.json`, and
`python tools/fuzz_eador.py --campaigns 300 --scenes 0 --steps 180` from the
source checkout. These reports do not include UI/native verification or a soak
of the later integrated candidate.

After merging the independent all-class final-seal journeys and display
primitives at `8f4d2da`, the combined suite passed 713 tests. The role game
rules were unchanged from the retained `79b2d49` stress snapshot.

## Player controls and presentation

Recruitment uses pages of five with mouse Previous/Next controls and Left/Right
keys. Numbered purchases always refer to the visible page. Ranger and Warden
occupy the second page; locked entries show their building requirement and
each role explains its distinct order. Their original vector pieces have
different silhouettes at battle and roster sizes; Acolytes have a rounded
vestment/staff treatment instead of the Wizard's pointed hat.

Selecting a Warden exposes **Swap ally / S**. Selecting a current Acolyte makes
**2** and the Heal button spend that unit's order; the label names the caster
and the panel shows shared mana. Hero Bolt retains its own caster. **F** cycles
legal targets for the chosen order, with friendly markers for Heal and Swap.
Healing previews use the actual clamped restoration, not the spell's maximum.
An acted Ranger with unused movement remains selectable with Tab and shows
**Can move** plus its reachable hexes. Reduced motion keeps the transient
damage/healing feedback still without changing combat or its display lifetime.

The retained `tools/verify_eador_roles.py` journey starts at the title, applies
reduced motion, purchases all facilities/troops and reaches Watch on turn seven
through real player controls. It shoots and repositions the Ranger, swaps the
wounded seal holder, then heals the extracted ally using the Acolyte. It wins
by holding the seal with all allies alive and defenders still standing. Six
save/reloads compare complete serialized states between orders and result;
claiming the site rewards it once. The shared opening policy lives in
`tools/eador_roles_campaign.py`, so native input and model checks use the same
paid preparation rather than separate hand-built winning fixtures.

Independent review also completed Swap and Heal with F → Enter, and exercised
page bounds, locked/invisible purchase keys, invalid Swap, cancellation and a
spent Warden's disabled shortcut before and after reload. Current and v8 Codex
pages were inspected: an older active Acolyte is explicitly identified as
noncasting, preserving the save's original capabilities. This establishes
usable controls for the existing manual plan; a human first-run evaluation,
broader build balance and release-candidate soak remain separate work.

The integrated native journey passed with 157 input activations and six exact
reloads. All six role screenshots were inspected, including a seven-HP Heal
forecast followed by the matching readable feedback. A clipped Swap hint was
shortened. The damage-pill overlap exposed a general draw-order limitation:
Saga2D's [screen-layer scope](framework-screen-layers.md) now lets its background
cover lower text, while effect timing, styling and motion preferences remain
in Shardbound. The independent framework demo verifies text/image coverage,
overlapping controls and modal isolation.

At this integration checkpoint, **765 tests passed**. The general native
input/save/window-size journey and 12 model + 12 linked scene fuzz runs also
passed (2,247 input events, 1,861 randomized). A separate Tribes fuzz run found
a pre-existing stale hover during quick-load; it reproduces before screen
layers. Separate fix `7148998` clears old hover targets before rebuilding the
loaded HUD. Its public regressions and native checks cover both a missing
resource and a smaller loaded map. All 60 AI and 20 random-input Tribes runs
subsequently passed; the fuzzer now seeds world generation as well as inputs.
