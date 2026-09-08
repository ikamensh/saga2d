# Concurrent campaign PvP

User direction, 2026-09-07: simultaneous turns apply to the global campaign
map. Battles retain their normal alternating turns. Players spend most of their
time fighting the environment, so one player's PvE battle must not prevent
the other player from developing, exploring or fighting elsewhere.

This is an implementation target, not a currently playable mode. Existing
Shardbound multiplayer remains shared-realm co-op. The tactical simultaneous
planning proposal was discarded after this clarification.

## Player experience

Both players start a campaign day together. Each commands a separate hero,
army and realm on the same province map, spending their own resources and
campaign actions. They can fight different neutral encounters concurrently,
using the existing battle turn order, previews and playback. Neither player's
battle rounds advance the campaign date or the other player's battle.

Ready finishes that player's campaign activity. It grants no income, recovery
or fresh actions. When both players are ready and their battles and choices
are resolved, the server settles one global day and opens the next. An attack
involving a ready player's army must reopen their participation for defense.

Short map commands are validated and applied by the authority. An active
encounter claims its province/site: a competing arrival cannot duplicate the
guardians, collect the same reward, or overwrite its defender state. The
conflict becomes an explicit pending encounter, with ordinary alternating-turn
PvP when the two armies meet. Uninvolved activity can continue elsewhere.
The UI must explain the claim and what the waiting army has committed before
spending that army's action. This is concurrent campaign play, not a hidden
batch of global orders or simultaneous tactical damage.

## Model and integration

One authoritative campaign room owns the province map, global date,
encounter claims and pending army conflicts. Two Realm records own their
heroes, troops, treasuries, buildings, inventories, choices, action allowances,
readiness and active PvE battle state. Capital positions and ownership are
explicit per realm. Both views project the same map; two independent solo
campaigns followed by a merge would lose or duplicate encounter consequences.

`eador.economy.settle_realm` now owns upkeep and recovery for a supplied hero
and treasury quote, independently of date advancement, rival AI and linked
campaign bookkeeping. The existing solo `State.end_turn` applies that receipt
then advances the world in its original order.
`eador.battle_results.apply_army_result` applies a completed battle's wounds,
casualties and advancement to the supplied hero and team, leaving the battle
and world unchanged. Solo and concurrent campaigns share progression, site
rewards and defender persistence; each caller coordinates its own claims,
ownership, choices and encounter cleanup. Solo rival and linked-campaign
transitions remain in `State`.
Keep campaign PvP rules in `eador`; transport must not know heroes or battles.

The development `ConcurrentCampaign` now supports separate site and neutral
conquest battles on its single map. The ordinary `Battle` handles each realm's
`battle.*` commands. `Realm.apply_battle_progression`, `Realm.reward_site` and
`persist_province_defenders` share the same earned army, reward and survivor
rules with solo play. There is no copied solo world or second combat engine.

In **9d6a8ea**, an ordinary competing arrival is rejected before spending an
action. An explicit `challenge` instead spends one action and waits behind
the opposing army's PvE battle or earned choice. `withdraw` cancels that wait
without refunding the action. The incumbent's combat and rewards finish first.
The challenger then enters the reserved destination: it meets the incumbent
in a shared battle if still there, or enters the vacated province without
chasing the departed army. Retreat retains actual wounds and clears the claim.

The **96eb221** battle kernel gives both humans ordinary alternating turns,
their own hero and shared army mana, unique combat IDs and retained realm troop
IDs. The room authorizes each tactical order by seat and active team; a shared
order advances both realm revisions. Both armies' casualties and progression
are applied once. Attack reopens a ready defender's participation. Capital
capture ends the shard; an already finished PvE encounter pays its earned
reward, while unfinished combat retreats with actual wounds.

[Current backend evidence](evidence/concurrent-armies-9d6a8ea/README.md) contains
146 passing model, loopback and solo compatibility cases. Its socket journey
buys both armies, waits through conquest and a skill choice, enters a shared
human battle, closes both connections, reconstructs the authority during the
defender turn and reconnects before retreat. Checkpoint schema 2 retains the
pending/shared encounter and still reads the earlier development schema.
Corrupt waiting destinations and unsupported shared outcomes are rejected;
valid waits at a departed army's origin retain their exact continuation.

The [earlier independent-PvE evidence](evidence/concurrent-pve/README.md)
establishes the separate battle and Ready-barrier foundation. Neither set is a
native PvP playtest. Concurrent campaign screens, server catalog integration,
dedicated-server process restart and a refreshed packaged PvP build remain
unfinished. Selectable multiplayer is still shared-realm co-op.

The existing socket interfaces already accept commands without a global
revision precondition. New campaign commands should validate the global day,
the sender's own realm revision, and relevant shared claims. Unrelated enemy
activity must not invalidate a player's battle order. Transport revision still
orders delivered updates. The new view should update independent parts of the
screen; current co-op's whole-scene replacement on every peer update would
interrupt local battle presentation and controls.

Player snapshots must contain only their entitled information. Trusted server
checkpoints must instead include both realms and active encounters.
`RoomStore.save` now uses the catalog's explicit `checkpoint_match(game, match)`
serializer, independently of player snapshots. Existing game formats, private
resume tokens and room expiry behavior are preserved. The concurrent model's
complete checkpoint is ready to connect to that catalog; the current loopback
test constructs `MatchHost` directly and does not register a hosted mode.
No public-server deployment is implied by source work.

## Acceptance criteria for the first playable increment

1. Two players own distinct heroes, armies, money, buildings and capitals on
   one consistent map. Forged ownership commands fail without mutation.
2. Both enter and manually resolve different PvE encounters concurrently over
   real sockets. One can remain in Help or a battle while the other plays.
3. Campaign readiness is per player. No day income, healing or action reset
   occurs before both are ready; duplicated packets cannot settle a day twice.
4. Competing province/site claims cannot duplicate defenders or rewards, erase
   casualties or grant an army a free move. Pending conflict is visible.
5. A direct army encounter is playable by both humans with ordinary battle turn
   order. Its casualties and ownership changes persist in the shared campaign.
6. Disconnect/rejoin and a server restart preserve both active battles,
   readiness, pending choices and encounter claims without leaking private
   state. Unrelated commands do not produce stale-order errors.
7. Native mouse/keyboard journeys cover concurrent PvE, Ready, conflict and
   reconnect, including text scaling and unchanged battle motion settings.
8. Victory/loss and the first supported campaign scope are explicit in the
   playable mode. Existing solo/co-op and framework integration checks pass.

A settlement extraction or network proof alone does not pass these criteria.
The original Early Access gates still apply to any release claim.
