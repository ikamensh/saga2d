# Atomic troop replacement: model contract

**Implemented in the game model and playable through a reviewed purchase flow.** The
[bounded experiment](eador-late-investment-review.md) supports optional role
access after the army fills, not a solution to surplus gold.

## Public surface

```python
State.replacement_preview(outgoing_id: int, kind: str) -> ReplacementPreview
State.replace_troop(outgoing_id: int, kind: str) -> None
```

The read-only preview is a frozen game-owned record:

- `outgoing`, `incoming`: frozen `TroopSnapshot` records with `id`, `kind`,
  `hp`, `max_hp`, `level`, `xp`. The incoming snapshot uses the next fresh ID,
  base HP, level 1 and XP 0. These are detached snapshots, not mutable army objects.
- `gold`, `crystals`, `actions`: the current ordinary recruitment quote and
  exactly one campaign action.
- `upkeep_before`, `upkeep_after`: total army upkeep computed by the model.
- `blocked_reason`: an expected readiness, camp, prerequisite or affordability
  refusal; otherwise `None`.

Unknown troop IDs or unrecruitable kinds raise `RuleError` before a quote is
constructed. Known but unavailable selections still show their price and lost
veteran data, with a clear blocked reason. Neither call accepts a previously
calculated price; the command recomputes and validates against current state.

## One order, one permanent consequence

Between battles and pending choices, while playing in owned land, the player
selects a living troop and a recruitable kind. The normal building prerequisite,
discounted gold price and crystal price apply. Replacement spends one action,
permanently removes that troop, and inserts a fresh paid recruit at its existing
army/formation index. Allocate a new ID; never reuse the retired ID.

There is no refund, reserve, transferred XP, added upkeep rule, action refresh or
extra fee on ordinary recruitment. The army size stays the same. Full capacity
does not block replacement; an empty slot does not prohibit an explicit retirement.
Same-kind replacement remains allowed and clearly shows the lost rank/XP; the
experiment retains its weak outcomes instead of disguising it as an upgrade.
Owned-camp eligibility matches ordinary recruiting, including its existing
blockade behavior. Passive rest is unchanged.

## Minimal implementation seam

Share the existing recruitment readiness, kind, ownership, prerequisite and funds
validation in one small private helper. Normal recruit keeps its current capacity
check and zero action cost. Replacement substitutes a valid outgoing identity for
the capacity check and requires one action. Preserve normal recruit's existing
refusal order, prices and logs; explicitly regress those behaviors.

Both paths reuse `recruit_cost`, `recruit_crystal_cost`, `UNITS` and one private
fresh-troop purchase operation for payment, base HP and monotonically increasing
IDs. Do not remove the veteran and then call public `recruit`: a later refusal
would make that sequence non-atomic. Validate and locate the army index first;
only then pay, replace the slot, spend the action and append the explicit log.

The preview and command share validation and quote calculations. There is no
generic transaction engine, campaign abstraction, separate reserve manager or
new persistence object. Existing troop, treasury, action, next-ID and log fields
already represent the result, so no schema bump is needed. Active old battles
and their capability arrays cannot be edited by a camp-only command.

## UI condition before shipping

The UI must show the selected named troop's current HP and **rank/XP permanently
lost**, the fresh incoming role/HP/rank, exact gold/crystal/action costs, and old
and new upkeep before an explicit Replace button. Keep the selection visible
when explaining refusal. Use the preview; do not copy price or upkeep arithmetic
into scene code. Recompute after selection changes and before committing.

The first native acceptance should start from the retained paid full army, buy
its remaining buildings normally, select a healthy veteran and preview a Warden.
Cancel must leave the save unchanged. Confirm, save/reload, enter the same assault
and issue a legal manual Swap. The before/after comparison must count retirement
separately from battlefield deaths and preserve ordinary rest as an alternative.

## Public integration checks

1. A full actual paid army still refuses ordinary recruitment unchanged. Preview
   is immutable/read-only; replacement matches every quoted field, preserves
   formation order and unrelated troops, loses rank/XP, and never reuses IDs.
2. Unknown/retired IDs, unknown kinds, missing prerequisite, insufficient gold or
   crystals, zero actions, battle, pending choice and ended state all reject
   without changing the complete save. Normal recruiting still works with zero
   actions when a slot and ordinary funds are available.
3. A replacement save/reload continues exactly through battle and reward; a real
   old save can make the new camp order without changing its existing contents
   before that order. Repeated replacements charge each new order and each action;
   they cannot refund or recover retired XP.
4. The all-buildings assault and last-action Heartwood pursuit retain explicit
   timing, lost veteran and rival consequences. Demonstrate a manual specialist
   action through UI before calling the feature usable; automated casualty
   differences alone do not establish that acceptance.

## Model checkpoint

The implementation is confined to `eador/model.py`; the framework, combat rules,
save schema and ordinary recruiting commands are unchanged. Thirteen public
integration cases in `tests/eador/test_replacement.py` cover the contract above.
The complete suite passes **1,072 tests**. Existing regression fuzzers pass
60 Tribes AI games / 20 random-input runs and 12 Shardbound campaigns / 12 scene
runs. Those existing fuzz policies do not issue the new replacement command;
the new public integration cases provide its direct acceptance coverage.

The paid manual model journey supplies a concrete UI replay: load the retained
`late_full_roster`, buy Archery and Mage Tower, replace troop 1 with Warden, then
travel to Duskspire. Three explicit automatic rounds reach a wounded Swordsman
on the flank. On round 4, Warden 7 can Swap with Swordsman 5 (7 HP), bringing it
into the hero's Heal targets. Manual Swap followed by Heal restores 22 HP and
keeps that veteran alive through victory on turn 11. The complete saved and
uninterrupted continuations match. These are model orders; native controls and
the visible retirement/cost confirmation still need their own verification.

## Playable review and native verification

Recruit → Replace troop (`R`, `M`) lists the actual living troops with formation
slot, identity, health, rank and XP. Choose one, then review a recruit from the
existing measured catalog. Unavailable recruits still offer Review and explain
their blocker. The final Replace control stays disabled until the model quote
permits the command. The screen shows the permanent retirement, ordinary price,
one-action cost, fresh rank-one identity, role and upkeep before/after. Canceling
or opening Codex/Settings/Saves changes no campaign data.

Confirmation keeps an applied acknowledgement with no repeated purchase control.
A failed checkpoint leaves that result and the full error visible; manual Saves
can retain it without overwriting damaged autosaves. The reading preference is
shared at 100/125%. Whole-row roster paging reserves space for measured errors;
only the visible troops own numbered keys. This fixes a real native case where
a save path that was a directory overflowed the six-troop picker. In the review,
an error replaces the optional resting hint; identity, rank/XP, retirement, cost,
upkeep and blockers remain visible. This and measured spacing accommodate the
same error with the longest Skyrider description. No error or quote text is
truncated or shrunk and no framework API was added.

`tools/verify_eador_replacement.py` runs the same public input journey with mock
or native Pyglet. It starts from the retained paid full army, purchases Archery
and Tower through controls, reviews/cancels/confirms the Warden with keyboard and
mouse, checks exact reloads, then drives the saved Swap → Heal assault described
above. Three preparatory rounds and the final cleanup are explicitly automatic;
the rescue is two manually aimed orders. The sacrificed veteran is counted as a
retirement, separate from battle casualties. It is optional role access, not a
claim that replacement is universally preferable to keeping or resting an army.

The verifier also checks every one of ten roles from funded and opening armies
at both sizes in three native windows: 120 complete reviews. Real directory and
damaged-file errors, disabled actions, manual recovery, the complete paged roster
and settings restart are exercised. Native screenshots still require inspection.
This checkpoint does not establish Windows behavior or close G07/G10.
