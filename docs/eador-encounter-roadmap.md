# From five authored battlefields to twelve adventures

Design after the Sealed Vault tranche, 2026-09-06, updated after Pack Hunt and
the Observatory model plans. The remaining rows are proposals, not shipped
content or G05 completion. The original tactics proposal predates the current
roster and objectives; this plan uses the implemented commands.

## Current foundation and the next useful seam

Border Watch, Last Gate, Courier's Crossing, Supply Cache and Sealed Vault are
five authored battlefield families. The three extraction adventures have
pre-entry approach selectors. Watch still lacks its proposed strategic entry
choice; the Gate's linked contract decision changes the campaign. Counting
their approaches, seeds or different guard HP as additional patterns would
overstate the content.

Pack Hunt subsequently became the sixth family. Broken Observatory has a
seventh family's complete model plans; native acceptance is tracked in its
own evidence. Neither change adds an objective type.

The existing game model supports rout, uncontested hold and explicit hero
extraction. Pin/Rally, Guard/Brace, shared-mana Heal, Warden Swap, Ranger
reposition, Smoke, Repulse and flight provide enough tactical vocabulary for
the next tranche. The task is to give those commands different problems to
solve, rather than invent a fourth objective or seven more abilities.

`EncounterSpec` already owns terrain, deployments, seal, exits and deadline.
`AdventureApproach` owns entry costs, selected layout and reward/burden changes;
`AdventureAttempt` records the committed choice. Pack Hunt implemented two
narrow game changes, with public regressions, also used by the Observatory:

1. `EncounterSpec.objective` explicitly selects rout, hold or extraction in
   `Battle.create`.
2. Save validation checks an attempt against that selected objective, preserving
   extraction legality, finite roster and once-only reward checks.

These are changes to the Shardbound adventure contract, not a Saga2D scenario
engine. Do not introduce an event graph, callback registry or tactical DSL.
Extra costs that alter guards or spend campaign time should be added only in
the particular tranche that needs them, with atomic commit/retry semantics.

## Seven proposed patterns

Each row needs an authored layout, distinct defended problem and a consequential
choice. Enemy counts and fees below are design hypotheses to test with paid
armies. A proposed variant should receive its own content ID so old saved
ordinary sites keep their old rules; the dependable home Shrine stays intact.

| Pattern / theme / objective | Player decision and intended counterplay | Consequence to record |
|---|---|---|
| Pack Hunt / Elderwild / rout — implemented | Wolves start on both sides of a forest divider. Fight with a compact formation, or buy a lured deployment. The measured Commander plans differ from the Warrior's two-Pikeman plan. See `eador-pack-hunt.md`. | The actual implemented lure costs 20 gold and preserves the same finite pack and reward. It neither spends extra campaign time nor restores survivors. |
| Broken Observatory / Ruins / hold — model and manual plans verified | A central hill is covered by separated ranged positions. Keep the dividing forest and stage a Rune Adept control plan, or open a lane for a Sapper-supported advance. Clearing also opens enemy sight. See `eador-observatory.md`. | The actual implemented fee is two crystals for terrain only. Both approaches keep the same guards and reward; the cost and finite wounds survive retreat. No marksman is removed before entry. |
| Caravan Ambush / Frontier / rout | A narrow escort route is anchored by a Pikeman beside an Archer, with a Warden behind them. Attack the anchor using ranged fire, wait out Brace for Repulse, or send a mobile flanker around the convoy. | Paying a raider before entry removes that specific guard permanently and reduces net profit. A free assault retains the full reward. The paid removal is recorded once, not repeated on load. |
| Royal Barrow / Ruins / rout | Two offset chambers separate the reserve from a front-line guard. Clear the outer tomb, or open the inner chamber for a larger reward and a second threatened direction. Shared mana spent on early damage is unavailable to sustain the enlarged fight. | Opening adds a finite, identified reserve once. Retrying cannot close the chamber to erase survivors or reopen it to farm new troops/rewards. This needs an explicit committed site state before implementation. |
| Living Grove / Elderwild / hold | A forest ring shelters a seal but offers only two clear firing lanes. Hold under ranged pressure with healing/rotation, or open a lane that lets both armies shoot through the grove. Flight reaches a flank; it does not remove the need to contest safely. | Opening the lane changes the saved selected terrain and surrenders some crystal loot. This is a bilateral sight change, not a flat defense penalty or strictly better paid route. |
| Stranded Explorer / Frontier / extract | The hero and one escort begin beyond a marsh belt, separated from the main army. Select a northern regroup route or a southern rendezvous; neither option simply shortens every unit's path. Smoke covers the isolated carrier while a Warden or flying reinforcement reaches it. | The chosen initial split is shown before entry and saved exactly. Extraction keeps ordinary hero identity and army survival rules; no new captive or escort-unit persistence subsystem. |
| Pilgrim's Shrine / Elderwild / hold | An optional shrine beyond the home province has a seal near the army and a broad enemy approach. Carry a valuable offering while holding, or spend it to restore battle mana before the first phase. The decision trades an economy reward against shared healing/control capacity. | Restored mana is capped and recorded at entry; the surrendered reward stays surrendered on retreat. It cannot be repeatedly converted into campaign mana or replace the guaranteed home healing-stone opening. |

The Observatory now implements the bilateral lane-opening decision originally
proposed for Living Grove. Rework the Grove's defended problem before building
it; a forest palette and different seal position alone would not earn another
pattern. The five remaining proposals are a work queue, not a count guarantee.

The retained ordinary Den, Tower, Caravan, Barrow, Grove and Camp IDs need not
be silently rewritten into these variants. New-world theme pools can place
their authored successors deliberately while continuing to load old content.
Wolf Den/Storm Quiver and Explorer's Camp/Boots must remain discoverable, as
must all four additional relic sources. Document whether a new variant shares
or changes those sources. Mirror Badge is now the new-world Vault reward;
older saved Vault Iron Crown rewards remain preserved.

## Build in small, measured tranches

First implement **Pack Hunt and Broken Observatory** plus a bounded entry
decision for the existing Watch. This establishes authored rout and hold
choices, and gives Smoke a reason to exist beyond an empty test arena. Keep
the initial variants' costs expressible by clear fields and ordinary commands.
If campaign-time or named-guard removal materially complicates that first
step, ship one pattern with its full consequence before starting the other.

Next implement **Caravan Ambush and Royal Barrow**, exercising finite roster
changes and paid/free tactical alternatives. Finally implement **Living Grove,
Stranded Explorer and Pilgrim's Shrine**, after the earlier sight, split-army
and resource experiments demonstrate what actually creates different plans.
Do not fill an allocation with a weaker reskin merely to reach twelve.

For each pattern, acceptance requires at least one complete paid manual plan,
both entry choices, a failure/reload/retry and an alternative army or hero that
changes actual orders. Compare mana, wounds, casualties, time and campaign
spending; record cases where a seemingly favorable choice is worse. Show its
briefing, actionable forecasts and result through real input. Preserve a real
prior-save continuation. Broader seeded campaigns must then vary the order in
which these adventures become useful, while keeping required sources reachable.

Twelve such patterns would satisfy the content floor only. G05 still requires
visible consequences and varied sequences, while G04/G07/G08 require viable
whole-campaign plans, resource tradeoffs and manual tactical advantage.
