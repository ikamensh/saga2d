# Support, mobile fire and extraction

The game-owned model at `79b2d49` adds tactical Acolyte healing and two new
recruits. This is progress toward G04/G08, not completion of either gate.
There are seven recruitable roles and eight relics. No new authored encounter,
entry choice, obstacle system or framework strategy abstraction is claimed.
Root-owned controls, descriptions and artwork are a separate integration step.

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
source checkout. UI/native verification and a soak of the later integrated
candidate remain separate release work.
