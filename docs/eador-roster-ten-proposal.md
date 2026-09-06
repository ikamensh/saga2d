# Three recruits after v10 extraction

Status: role direction accepted; **not playable content yet**. The independent
sight helper is being tested before battle integration. Reserve v11 after the
extraction schema stabilizes. No Saga2D tactical abstraction is needed.

| Recruit | Gate; price; upkeep | Initial combat profile | Distinct role and counter |
| --- | --- | --- | --- |
| Sapper | Marketplace; 60 gold + 1 crystal; 2 gold | 26 HP, attack 7, armor 2, move 3, melee | One Smoke charge per battle protects a crossing or screen from ranged fire. Smoke works both ways; opponents can move around it, approach in melee, or wait it out. |
| Rune Adept | Mage Tower; 65 gold + 2 crystals; 2 gold | 28 HP, attack 6, armor 2, move 3, range 2 | One Repulse charge pushes an adjacent enemy one clear hex directly away without damage or retaliation. Guard/Brace anchors the target; blocked destinations and board edges prevent the push. |
| Skyrider | Temple; 85 gold + 3 crystals; 3 gold | 28 HP, attack 10, armor 2, move 4, melee | Flight crosses occupied and rough hexes but must land on an empty hex. Pin still reduces movement; ranged focus and Brace punish its fragile melee approach. |

Numbers are tuning candidates. All three compete for existing army slots and
require actual purchases. Recruitment adds `State.recruit_crystal_cost(kind)`;
`recruit_cost` continues returning gold. Gold discounts do not reduce crystals.
The local Mage Tower plus a Skyrider costs five crystals before other purchases,
so obtaining a magical recruit can make a crystal site an immediate route goal.
This is a useful sink, not evidence that the whole crystal economy is solved.

## Rules and small public commands

- `Battle.smoke_targets(unit_id) -> set[Pos]`,
  `smoke_preview(unit_id, pos) -> SmokePreview(pos, expires_before_team)`, and
  `smoke(unit_id, pos)`. Range three and clear sight; any board cell without an
  existing cloud is a legal destination. Spend the Sapper's action and remaining
  move plus its one charge. One hex stays smoky until immediately before that
  team's next phase, independently of the Sapper surviving. The preview validates
  the same destination/charge conditions as the command and spends nothing.
- `Battle.repulse_targets(unit_id) -> list[BattleUnit]`,
  `repulse_preview(unit_id, target_id) -> Pos`, and
  `repulse(unit_id, target_id)`. Preview gives the exact legal landing hex. Spend
  the Adept's action/move and charge; preserve the displaced target's movement,
  action, retaliation and status flags. No diagonal guessing, collision damage,
  falling off the board or chained pushes. Objective progress still changes only
  at its normal checkpoint; displacement cannot implicitly evacuate a hero.
- Flight uses existing `reachable` and `move`, plus a read-only `can_fly` trait.
  It adds no active-order button and grants no second move or free attack.
- Rejected orders preserve the entire battle/save. Target and preview queries
  work for both teams; player commands retain the existing player-only rule.

`eador.sight.line_of_sight(terrain, source, target, smoke=())` owns geometry and
terrain policy. Intervening forests block a straight ray; endpoint forest keeps
its ordinary cover instead of becoming untargetable. Hills/marsh and unit bodies
do not obstruct sight. Either entire edge ray may be clear when a shot follows
a hex boundary. Smoke blocks endpoints and intermediate cells, so it never
creates one-way firing cover. A unit always sees its own cell.

New battles apply sight to ranged normal attacks, Pin and spell targeting;
ordinary melee ignores it. Moving to restore sight matters to Archer/Ranger
play, while a Sapper can also obstruct friendly healing and fire. Every target
query, immediate forecast and AI movement evaluation must use the same helper.
The current range-only AI movement score must account for legal sight, including
leaving smoke before shooting; merely rejecting its old shots would be an AI bug.

## Saves and AI

Use a recorded `sight_rules` value (`open` or `terrain`) for active battles.
Older v10 and earlier battles migrate to `open`, no smoke, and no newly granted
capabilities; their saved continuation stays exact. A subsequently created
battle uses terrain sight. Preserve province rosters, rewards and inventory on
load; do not insert new enemies into old worlds. Golden v9/v10 continuations must
cover Acolyte mana, Ranger post-shot movement, Warden Swap and extraction state.

A small `SmokeCloud(pos, expires_before_team)` record and a validated tuple of
spent once-per-battle ability IDs suffice. Known capability IDs, unique/in-board
cloud positions, phase ownership and charge use are validated before loading.
No callback registry, effect language or configurable status engine is needed.

AI uses the same finite charge and public-query rules as the player. Smoke only
when it blocks an actual threatening ranged lane without disabling the team's
more valuable immediate attack/escape. Repulse prioritizes freeing a required
objective/exit or extracting an endangered ally from adjacent pressure; it does
not push enemies toward the hero or onto an objective. Skyriders consider legal
landing exposure rather than crossing the nearest unit blindly. Preserve the
old policy exactly for old active battles without these mechanics.

## Paid encounter evidence before acceptance

1. Buy a Sapper through an ordinary economy, reach the Watch, then compare Smoke
   with the same saved turn using Guard: demonstrate reduced incoming ranged
   damage or mana use while retaining a surviving defender and a real hold win.
   Show the counter of stepping clear before shooting and friendly fire/healing
   blocked by the same cloud. Save while each team's cloud is active.
2. Buy an Adept and clear a Gate seal neighbor without killing it; independently
   show Guard/Brace and an occupied landing rejecting the push unchanged. For
   extraction, push an exit contester away, then use the hero's explicit
   evacuation action; moving the hero or foe alone must never end the encounter.
3. Buy a Skyrider, cross an occupied screen to reach an Archer/exit flank, and
   finish a real objective. A paired pinned case must reduce its available
   landing choices; flying never permits an occupied landing or avoids Brace.
4. Complete the linked campaign with the new control/flight plan as well as
   existing economic melee and support/ranged plans across heroes and themes.
   Record troop cost, crystal spending, losses, mana, turns and manual objective
   results. Demonstrations cannot substitute fixture-injected troops or compare
   only raw HP. Retain failure seeds and exact old-save continuations.

Extraction coordination: the carrier remains the hero, with two authored exits
and an explicit evacuation order. Smoke protects the route, Repulse clears an
exit's adjacent contest, and flight threatens the blocker without transporting
the carrier. No extra escort identity or obstacle-placement engine is required.
The tenth recruit and eighth active order are content floors, not proof of G04,
G07 or G08 balance, presentation, or release readiness.
