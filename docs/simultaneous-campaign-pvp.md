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
`eador.battle_results.apply_army_result` now applies one completed PvE battle's
wounds, casualties and advancement to a supplied hero, leaving the battle and
world unchanged. `State.resolve_battle` retains province/defender/site changes,
rewards, choices and encounter cleanup. The shared-world room still needs to
coordinate those changes against its claims.
Keep campaign PvP rules in `eador`; transport must not know heroes or battles.

The development `ConcurrentCampaign` now supports separate site and neutral
conquest battles on its single map. The ordinary `Battle` handles each realm's
`battle.*` commands. `Realm.apply_battle_progression`, `Realm.reward_site` and
`persist_province_defenders` share the same earned army, reward and survivor
rules with solo play. There is no copied solo world or second combat engine.

An active encounter claims its destination until its result is accepted.
A competing arrival is currently rejected with an explicit reason before any
action is spent; retreat persists defenders before releasing the claim.
Opponent-owned land and the other hero's occupied origin are also blocked
until human encounters are implemented. This does **not** yet implement the
pending army conflict described above. Earned choices block only their own
realm's Ready, and both realms must finish before the shared day advances.

[Current integration evidence](evidence/concurrent-pve/README.md) exercises
both active battles over loopback sockets, restores the authority from its
trusted checkpoint, resolves both rewards and crosses the Ready barrier.
This is model/transport evidence, not a selectable mode or a native UI playtest.

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
resume tokens and room expiry behavior are preserved. The new room model must
supply its own complete checkpoint representation when it is integrated.
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
