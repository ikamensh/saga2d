# Decision proposal: three linked shards

Status: preferred design for implementation review, **not implemented**. Builds on
G01/G03/G12/G13 in `early-access-criteria.md`, the v6 themed worlds, and research's
pending v7 Pin/relic increment. Reserve **v8** for this work after v7 is stable.
The existing standalone shard remains unchanged.

## The run

A new **Linked campaign** begins in Frontier with the selected class and seed.
The player establishes a realm, chooses a second challenge, then chooses how to
finish the campaign in the remaining theme. There is one recovery expedition
for the entire run. No astral map, persistent empire economy or framework
campaign engine is needed.

| Stage | Offered challenge and concrete objective | Pressure and payoff |
| --- | --- | --- |
| 1 — Westwatch | Frontier; existing capture-Duskspire victory. | Existing forgiving opening. Learn the build, acquire relics, select a traveling retinue. |
| 2A — Rootward | Elderwild. Clear its Border Watch through hold **or rout**, then capture Duskspire. The Watch unlocks the final assault; it is no longer an optional detour in this contract. | The dry road offers income and merchant recruitment; the seal lies on the opposite flank. Moving between them exposes the realm to the finite rival. |
| 2B — The Foundries | Ruins. Control both marked foundry provinces `(0,-1)` and `(0,1)` simultaneously when beginning the assault on Duskspire. | The player must hold a broad front, choose which factory to take first, and protect the more vulnerable approach. Foundries retain ordinary income/garrison rules; no new currency. |
| 3A — Break the Throne | The unused theme. Capture its stronghold by routing the seven-unit final garrison. | No short tactical deadline: attrition, spells and careful recovery are valid. |
| 3B — Seal the Gate | The same unused theme and same-strength final garrison, with a separately authored capital battlefield: hold its seal for two consecutive uncontested enemy phases by round 8, **or rout before that deadline**. | An early objective victory can preserve troops; slow fighting risks deadline retreat. The player chooses this contract knowing the deadline and layout. |

After stage 1, offer exactly **Rootward or The Foundries**. After stage 2, offer
exactly **Break the Throne or Seal the Gate** in the unvisited theme. Thus every
completed run visits all three themes, while the middle objective and the final
battle contract are player decisions. Show both complete briefs before departure:
seed, theme, prerequisites, initial rival strength/treasury/countdown, final
objective and carryover preview. Seeds/offers are generated once and saved;
reloading a departure screen never rerolls them.

Stage 2 starts the usual finite six-soldier expedition with 80 gold and a two-turn
first warning. Stage 3 starts four Guards and two Archers, 90 gold and a two-turn
warning. These are disclosed scenario starting forces; subsequent reinforcement,
healing, casualties and counterattack windows keep the existing paid rules.
At stage 2B, prefer an exposed foundry as a rival occupation target when it is
reachable without the existing suicidal-attack exception. Use one game-specific
priority in the existing planner, not a new opponent policy abstraction.

Prerequisites are checked on **entry to** the capital battle. Losing a foundry
later does not invalidate an already running battle. Failed prerequisites reject
travel with a precise reason and spend nothing. All ordinary conquest/site
retreats retain their current wounds and losses; the campaign progresses only
when the shard actually reaches `status='victory'`.

## Carryover: identity survives, finished economies do not

These are linked-mode rules, visible from the first shard rather than applied
retroactively at its exit:

- Hero rank ceilings are **3 / 4 / 5** by stage. Keep earned class, level, XP and
  every chosen skill rank. At the ceiling, freeze XP until the next stage; do not
  bank overflow or erase existing XP. This gives four advancement decisions over
  the run and prevents both skill paths automatically converging before the end.
- Troop rank ceiling is **3** throughout this initial linked campaign. Promotion
  stops visibly at that rank; no exported soldier is secretly demoted.
- Choose up to **two living troops**, preserving their IDs, kind, rank and XP.
  Fill empty places to a three-troop starting army with fresh local Militia.
  The player rebuilds the rest of the army locally; unselected survivors remain
  as the liberated shard's garrison and appear in its completion record.
- Choose up to **two owned relics**, keeping their capabilities unchanged and one
  equipped. Skills and relic knowledge are not replaced with flat bonuses.
- Begin the next shard with **100 + min(40, exit gold)** and
  **4 + min(2, exit crystals)**. Buildings, provinces and recurring income stay
  behind. Display what transfers before confirming departure; there is no
  incentive to grind hundreds of gold for export.
- Restore traveling hero/troops to full health and mana. Recompute maximum mana
  from class and retained level; a local Mage Tower's +4 mana does not stack
  across shards. Future permanent bonuses must have an explicit provenance,
  rather than being inferred by subtracting arbitrary amounts from a total.

This sacrifices a large traveling army in exchange for a fresh local economy
and clear balance bounds. It retains the actual hero build and selected veterans;
resetting their learned choices would undermine G03. Caps are tuning candidates
requiring play evidence, not claims that this configuration is already balanced.

## Defeat, recovery and ending

The first loss of a capital offers **one recovery expedition or end the run**.
Recovery returns to the same stage and exact initial world/contract, consumes the
run's sole recovery, and begins with 60 gold and two crystals. Keep the defeated
hero's earned level/XP/skill choices, choose up to two *surviving* troops and two
owned relics, and fill the local Militia levy to three troops. Restore health;
dead soldiers remain dead. Local holdings/buildings reset. The progression ceiling
remains the same, so this cannot farm unlimited levels or resources.

The checkpoint supplies the recorded world and starting rival; it does not roll
new terrain or revive the old army. Recovery is distinct from loading a manual
save. A second capital loss ends the campaign. A player may always start a new
run or load an existing manual slot; this is not an ironman restriction.

Stage-three victory ends the run after pending rewards are resolved. Show all
three shard records, the two challenge decisions, retained build, losses and
elapsed turns/play duration. The conclusion distinguishes liberation without a
recovery, liberation after rebuilding, and a lost expedition. Do not call stage
one's local victory the campaign ending.

## Minimal implementation and save contract

Keep `State` as the active shard and add optional game-owned `State.campaign`
metadata in `eador/campaign.py`. Prefer three commands in addition to current
play commands:

```python
State.new_campaign(seed=7, hero_class='Commander')
state.advance(offer_id, troop_ids=(...), relic_ids=(...))
state.recover(troop_ids=(...), relic_ids=(...))
```

`advance` and `recover` validate the complete request before replacing active
shard data atomically; bad IDs, duplicates, excess selections or wrong phase
raise `RuleError` without mutation. Existing travel/build/battle/choice commands
remain the play interface. A read-only offered-challenge record contains
`id, title, description, seed, theme, contract`. The metadata contains master
seed, stage, phase (`playing/departure/recovery/completed/lost`), recovery used,
completed shard summaries, recorded offers, and the current stage's entry-world
checkpoint. UI derives screen priority from phase plus existing battle/choice.

Serialize all of this in **v8**. Versions 1–7 migrate to `campaign=None` and keep
their exact standalone state; never opt an old save into a linked run. Validate
stage/phase/contract/theme history, unique carried IDs, capped linked progression,
choice legality and result consistency at load. Future versions fail clearly.

The entry checkpoint records the generated province array and starting rival
plus the stage contract. It does **not** contain another campaign, previous
checkpoint, active battle, or arbitrary nested State. Recovery constructs fresh
local play data from these records and the current survivor/build selections.
Past shards retain compact outcome summaries, not live worlds. This keeps saves
bounded while preserving exact world data across generator changes.

The local victory result and all pending skill/relic choices are resolved before
the departure phase freezes offers. The old finished shard stays intact while
choosing a retinue. Snapshot/autosave **before** risky departure/recovery, then
again after constructing the new shard. If the first write fails, stay at the
choice; if the second fails, keep the new in-memory state and report that the
previous transition snapshot is still recoverable. Save timing remains game UI
policy; Saga2D's SaveManager only supplies safe file I/O.

## Evidence before accepting G01

1. Public-command journeys for all four classes and both middle/final contracts:
   first battle → shard victory → final pending reward → departure selections →
   new shard → final ending. Check that retained skills/relic capabilities and
   troop identities produce their normal effects, and local bonuses do not stack.
2. Save/restart in terminal combat, pending reward, departure, immediately after
   advance, recovery offer, immediately after recovery, and both final endings.
   Identical subsequent commands must yield identical results. Reject duplicate
   departures and invalid survivor selections without spending/replacing state.
3. Demonstrate Rootward's hold and rout routes, foundry capture/loss/recapture,
   both final contracts and a failed seal deadline with surviving defenders.
   Include at least one meaningful manual improvement over automatic combat.
4. Lose stage 2, keep its newly earned hero choice through recovery, finish;
   separately lose twice and reach the loss ending. Save old v7 standalone
   battles and verify their full continuation remains unchanged in v8.
5. Record complete native-input campaigns, including a restarted transition and
   recovery. Measure duration, repeated actions and actual decisions; aim for
   roughly 45–90 minutes initially, but reject padding rather than stretching
   play to fit a number. This plus human evaluation, not unit tests, gates G01.

## Independent balance critique

The [world audit](eador-worlds.md) found **720/720** victories for one deliberately
competent economic policy. Typical finishes have a level-four hero, level-three
veterans and 375–867 gold. Unrestricted carryover would remove recruitment and
recovery decisions; exporting a trained Wizard with rank-three Channeling also
makes cheap spells a much larger advantage than raw treasury. The proposed caps
must be tested across both hero paths and relic plans, not only the existing
Temple/Swordsman/first-skill policy.

Flanks currently add around three turns while saving roughly one soldier and
30–40 recruitment gold. Export caps will reduce the value of their surplus cash;
retaining selected veterans and relics must keep them worthwhile. Foundry gates
could turn meaningful detours into mandatory chores, and the fixed northern rival
already makes north/south asymmetric. Accept that contract only if defending or
retaking a foundry produces a decision; do not count extra travel as depth.

Seven defenders can make a two-turn uncontested seal impossible without routing
most of them; conversely a ring of Guards can make holding too easy. Test the
actual final formation and both contract win paths before tuning HP. The single
recovery preserves learning without unlimited resource farming, but the reduced
restart budget could punish a struggling player twice; recovery must have a
verified viable opening for every class and an honest preview of what is lost.

Preferred next implementation slice: the saved three-stage transition and capped
retinue first, then the middle/final contracts. Do not ship an interim threefold
repeat of standalone shards as completion of G01.
