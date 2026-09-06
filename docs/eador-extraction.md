# Carry and escape: the first two adventures

Game rules and reusable verification routes are implemented at `93b5cf8`.
This is a bounded G05 increment: two authored extraction layouts and their
entry decisions. A layout's two approaches do not count as two patterns.
The third proposed Ruins vault, more encounters, and completion of the release
gates remain future work. Native approach controls, exit markers and result
presentation belong to the following UI integration checkpoint.

## Decisions with consequences

| Adventure | Arrival and exits | Entry decision |
|---|---|---|
| Courier's Crossing, Frontier `(0, 2)` | A western deployment faces a Pikeman, Archer and Brigand. Two separated eastern exits permit route selection. | Direct is free. Guided costs 20 gold and deploys the same army on the covered southern flank. Both face the same finite defender roster and award the saved 50 gold, two crystals and Merchant Seal by default. |
| Supply Cache, Elderwild `(-1, -1)` | Central deployment is surrounded by three Wolves and a Goblin. Opposing western and northeastern exits ask which flank to clear. | Light has normal movement and the saved 40 gold/two crystals/Oak Standard reward. Full adds 40 gold on success and subtracts one hero battle movement, minimum one. |

Both are placed deliberately on new worlds. Westwatch's Shrine, the required
Border Watch, Wolf Den and Explorer's Camp sources, capitals, existing terrain,
income and the six-entry random site pool remain intact. Loaded province arrays
are preserved; the new sites are not retroactively inserted into an old shard.

Only the hero carries cargo. It must stand on a marked exit with an unspent
action and no living adjacent enemy, including ranged enemies, then explicitly
**Evacuate**. Moving or swapping onto the exit does not end the battle. A Warden
can deliver a hero without spending the hero's action. Casting or attacking
with that hero consumes the current opportunity; Pin limits its movement but
never disables evacuation itself. Cargo is a saved battle-unit penalty and
never edits the persistent hero's movement or progression.

Hero death loses immediately. The eighth enemy phase ends an unfinished escape
in defeat. Rout remains an alternative: eliminate every defender to recover the
same recorded cargo safely. Successful escape may leave defenders alive. The
existing victory XP is an encounter reward, not a claim those survivors died.

Enemy policy protects an exit or closes on the carrier's shortest currently
open route, using actual terrain and occupancy costs. A lethal carrier attack
takes priority; useful Pin can delay its approach. A wounded Ranger away from
the route does not lure defenders off it. An enemy Ranger already contesting an
exit retains that position after firing. This is a local tactical policy, not
an optimal opponent. Automatic player play evacuates when legal or immediately
reachable; its fallback may still rout the opposition.

## Small game-owned API

```python
options = state.adventure_approaches(destination)  # None means current province.
# AdventureApproach: id, title, description, encounter, gold_cost,
# crystals_cost, cargo_penalty, bonus_gold. Ordinary sites return ().
state.explore(approach='guided')  # No argument selects the free/default approach.

reason = state.battle.evacuation_blocked_reason  # Specific text, or None.
if reason is None:
    state.battle.evacuate()
```

`ENCOUNTERS[option.encounter]` provides the selected terrain, deployment and
exit coordinates for a pre-entry view. `State.battle_encounter` reflects the
chosen approach. The active `battle_adventure` records `approach`, `encounter`,
actual `gold`, `crystals`, `relic` and `cargo_penalty`. Entry fees have already
been deducted; these gold/crystal fields are rewards, not charges.

`Battle.objective` gains `kind='extract'` and explicit `exits`; its deadline is
eight, target is `None`, and hold counters are zero. `outcome_reason='escape'`
distinguishes evacuation from rout, hero death and deadline defeat. Current
movement displays should use `BattleUnit.effective_move_range`, which includes
both Pin and cargo. The rules live entirely in Shardbound. Saga2D's existing
HexGrid handles layout, costs and reachability; no tactical DSL or new framework
strategy subsystem is introduced.

## Save, retry and reward invariants

Schema 10 explicitly adds neutral exit/cargo/attempt metadata to older saves.
An actual active v9 support battle continues to the same complete campaign
result, aside from the schema tag and new empty attempt field. Prior recorded
v8, v7 and earlier continuation regressions remain passing.

Invalid or unaffordable approaches leave the complete state unchanged. A valid
entry spends one campaign action and its fee once. Loading does not spend it
again. Retreat or deadline failure keeps the spent fee and the existing defeat
loss; it grants no victory XP or reward. The site's surviving defender kinds
and HP remain finite across retries, including when a later attempt picks a
different approach. Victory marks the site explored before queuing its relic
choice, pays the attempt's recorded reward once, and prevents another entry.

Validation rejects mismatched approach/cargo/deadline/exits/rewards, an already
explored or uncontrolled origin, a displaced carrier, altered defender roster,
regained defender HP, or replacement of an extraction objective with rout.
The attempt's reward is checked against the **saved province** plus its selected
bonus, not a newly generated world or the registry's current base loot. Future
changes to an approach's mechanics require explicit save compatibility work.
An independent model-agent review reproduced the context failures before their
fix, rechecked their rejection, and found no further concrete blocker.

## Measured paid journeys

[The retained manual report](evidence/shardbound-extraction-manual-2026-09-06.json)
records 18 complete seed-seven escapes, with actual purchase totals, every order,
rounds, mana, wounds and surviving enemies. All use public campaign preparation
and ordinary battle commands. All four heroes complete both approaches at both
sites without losing a player unit. These are explicit prepared plans, not a
human playtest or a broad optimal-policy win rate.

- The same seven-body Commander army pays 165 gold for buildings and 137 for
  recruits. Direct escapes in round three; Guided pays another 20 gold and
  escapes in round two. Both spend four mana and leave two defenders alive.
  Guided ends with four missing army HP versus Direct's one: the measured
  benefit is speed, not universal safety. The direct carrier is genuinely
  Pinned; the guided plan combines Pin, Acolyte healing, Ranger fire followed
  by movement, and Warden delivery.
- Six-body Crossing plans use Warden/Ranger for Direct and Warden/Acolyte for
  Guided. All four classes escape in rounds three and two respectively; the
  report separates their preparation costs and campaign arrival turns.
- Matching Cache armies clear the western contester. Commander, Warrior and
  Wizard take one round with Light and two with Full; the additional phase
  costs wounds and four healing mana, while the Warden delivers the carrier.
  Scout's acquired Pathfinder skill permits both loads to escape in round
  one. The skill mitigates the burden through existing movement rules. All
  Cache routes leave three defenders alive.

The executable tests check actual attack/Pin/Heal forecasts and roundtrip the
entire campaign after every recorded manual order, including terminal escape
and pending reward choices. Additional cases cover blocking adjacency, a spent
healing action, Warden delivery, enemy bait/counter behavior, unaffordable input,
paid deadline failure, wounded-defender retry and duplicate-reward prevention.

The merged source passes **781 tests**. Further clean `93b5cf8` reports retain
source hashes, Python/platform and elapsed time, with no source changes:

- [1,200 randomized battle fixtures](evidence/shardbound-extraction-battles-2026-09-06.json): 400 extraction fixtures plus hold/rout/hero-free cases; 5,926 exact forecasts, 7,403 roundtrip checks, 1,205 Swaps, 959 Heals, 282 Ranger shot-then-moves and 39 escapes. These deliberately vary armies and wounds rather than reproduce site rosters.
- [300 randomized campaigns](evidence/shardbound-extraction-campaigns-2026-09-06.json): 100 per theme, 46,258 state checks, 12,569 unchanged-state command rejections and extraction approach/evacuation handling. Five victories and 295 defeats describe the random robustness policy, not balance acceptance.
- [60 linked randomized runs](evidence/shardbound-extraction-linked-2026-09-06.json): 20 begin at each linked stage after real prior-stage preparation; 11,390 state checks and 29 recovery transitions. The cleanup policy declines remaining recovery offers. Its two victories and 58 defeats are not a linked-campaign difficulty claim.

Reproduce from the checkout with:

```sh
python -m pytest tests/eador/test_extraction.py tests/eador/test_extraction_journeys.py -q
python tools/audit_eador_extraction.py --report /tmp/extraction-manual.json
python tools/stress_eador_roles.py --cases 1200 --report /tmp/extraction-battles.json
python tools/fuzz_eador.py --campaigns 300 --scenes 0 --steps 180 --report /tmp/extraction-campaigns.json
python tools/fuzz_eador.py --linked --campaigns 60 --scenes 0 --steps 180 --report /tmp/extraction-linked.json
```

`tools/eador_extraction_campaign.py` exposes `prepared_crossing(state=None)`
and `prepare_adventure(..., state=None)` for a real-input State adapter. Its
`crossing_route` and `cache_route` accept `orders_type`; a native verifier can
subclass `AdventureOrders.do` to dispatch the same orders through controls.
The source-only evidence above does not establish native UI quality, revised
packaging or a soak of this newer candidate.
