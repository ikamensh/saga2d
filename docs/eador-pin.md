# Pin and relic capabilities

This bounded increment adds Archer Pin, the hero's Watch Bell/Storm Quiver
capabilities, and discoverable sources. It moves the
[tactical plan](eador-tactics-design.md) forward; it does not complete
G04/G05/G08. There are still five recruits and four active capabilities
(Bolt, Heal, Brace, Pin), plus the ordinary Guard order. Eight relics and
eight site definitions are not evidence of eight authored encounter
patterns: Explorer's Camp uses the existing seeded rout battlefield and
has no entry decision.

## Tactical contract

A fresh Archer can Pin an unpinned enemy within three hexes. Pin uses its
attack action, including the ordinary rule that consumes remaining
movement unless the actor has Skirmisher. Damage is normal attack damage
after defense/cover, halved and rounded up, then capped to remaining HP.
The target loses two movement, to a minimum of one, during its next own
turn. It can still attack, cast and Guard. Pin cannot stack or extend an
existing Pin. It expires after the target's own turn.

The shooter cannot Pin on its following turn; it can Pin again on the turn
after that. A ranged basic attack, moving, casting or Guard remains
available during the cooldown. Pin is a ranged action even for a melee
hero: it does not trigger Brace. An adjacent target without Brace retains
the ordinary ranged-contact retaliation rule. The forecast uses the same
damage/reaction calculation as the command, including lethal damage.

The enemy and automatic player use Pin when slowing a target prevents its
next approach to the nearest living ally. They retain full damage when
that target is already engaged with another ally, when a normal hit kills,
or when a seal holder needs to be attacked. This rule arose from a tested
failure: slowing an enemy beside the frontline halved damage without
preventing any attack and broke otherwise sound campaign strategies.

## Public game interface

- `Battle.pin(unit_id, target_id)` issues the order.
- `pin_targets(unit_id)` lists legal targets now, including capability,
  cooldown, action, range and existing-status restrictions.
- `pin_preview(unit_id, target_id)` returns actual target/attacker HP loss
  without mutation. Invalid orders and previews raise `RuleError`.
- `BattleUnit.can_pin` and `can_brace` describe capabilities; they do not
  mean the unit still has an action. Existing `guard()` chooses Brace
  through `can_brace`, including an eligible hero.
- `effective_move_range` includes Pin; `move_range` remains the base stat.
- Saved `abilities` is a tuple of game capability IDs. `pinned` is a boolean.
  `pin_cooldown` is 2 immediately after use, 1 on the shooter's next turn,
  and 0 when ready again. It decreases at the start of each own turn.

A Watch Bell hero can Brace through Guard and uses its own normal attack
for the pre-emptive strike. A Storm Quiver hero can Pin at range three,
independent of its basic attack range. Only one relic is equipped, so these
capabilities compete with healing, damage, movement and economy relics.

## Sources and saves

New shards of every theme guarantee Wolf Den at `(-2, 2)` with Storm
Quiver, Explorer's Camp at `(-1, 2)` with Wayfarer Boots, and the existing
theme-specific Border Watch with Watch Bell. The Camp's goblin/wolf roster
and Boots reward keep the previous Den relic discoverable. Home Shrine and
the seed-7 direct tutorial route remain intact. Registry additions do not
alter the fixed six-ID seeded site pool or draw more random numbers.

Schema 7 stores capabilities, Pin status and cooldown. Loading versions
1–6 preserves the recorded province arrays, rewards, inventory and equipped
relic; it does not regenerate the world or replace an old Den's Boots or
Watch's Oak Standard. Active older armies gain no new Pin capability,
preserving their exact tactical continuation. New battles created after
that encounter use current unit/relic capabilities. Pikemen retain their
intrinsic Brace. All transient statuses and cooldowns start fresh in a new
battle.

## Evidence and limits

The complete suite passes **628 tests**. Twenty Pin tests cover both teams,
movement/attack/Guard choices, no stacking or extension, cooldown boundaries,
exact lethal/retaliation forecasts, ranged Brace counterplay, malformed
saves, and a genuine v6 battle's unchanged continued result and log.

Public campaign journeys acquire all three new source rewards through
travel, fighting and choices in Frontier, Elderwild and Ruins, then equip,
save/reload and activate both earned hero capabilities. A normal Shrine
battle saves after Pin and at both cooldown boundaries. Sixty generated
shards check source placement and graph reachability.

[The retained route audit](evidence/shardbound-pin-routes-2026-09-06.json)
completed **720/720 victories**: 20 seeds, four
heroes, three themes and three itineraries. That demonstrates the existing
investment/interception policy remains viable; it does not establish
optimal play, balanced army diversity, or human difficulty. UI controls,
codex descriptions, markers and native screenshots are root integration
work, separate from these game-rule checks.

[The clean-source stress run](evidence/shardbound-pin-stress-2026-09-06.json)
completed 300 model campaigns (100 per theme), 20 scene runs and 10,005
random input activations in 151.6 seconds. It checked 249 accepted manual
Pin orders and 2,420 rejected ones, including matching saved continuations
and forecasts. All reported game/framework/harness hashes match `c21124e`;
no source changed during the run. These are model Pin commands; native Pin
input is not claimed before root connects its UI.
