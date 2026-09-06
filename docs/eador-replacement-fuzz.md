# Replacement model and input stress

The model policy in `tools/fuzz_eador.py` exercises the public replacement
command alongside ordinary recruiting. The first tranche below changed no game
rules or scene input adapter; the later input tranche is recorded separately. The model interface is documented in
[the replacement contract](eador-army-replacement-interface.md).

## What each sampled order checks

Half the camp samples seek an available replacement role. The other half include
unknown or retired IDs, unrecruitable kinds, missing prerequisites and insufficient
resources/actions. Additional samples attempt replacement during battle, pending
rewards and ended states. These are deliberately mixed legal/illegal commands,
not a competent investment policy.

Each quote leaves the complete save unchanged. A refused command must produce the
same reason before and after reload and leave both saves exact. Each accepted
command verifies the outgoing snapshot, fresh ID, level 1 / XP 0 incoming troop,
normal price, exactly one action, formation index, unchanged army size and total
upkeep. Comparing the entire saved object permits only the specified army slot,
treasury, action, next-ID and appended log changes. Independent saved execution
must match exactly. Retired IDs cannot reappear on that shard; a new expedition
or recovery starts a new identity scope.

When replacement spends the last action, travel must refuse without mutation.
Two copies then execute a real end turn and compare exact saved consequences,
including rival operations and upkeep. These **copied next-turn probes do not
advance the live random policy**. Territory losses and defenses in those copies
are reported separately; they do not prove that every loss could have been
prevented by spending the action differently. The specific preventable Heartwood
interception remains a separate public integration scenario.

## Retained run

Clean source **6ffdd7e** ran 120 standalone seeds 0–119 and 60 linked seeds 0–59,
with up to 240 random policy steps each. These are Standard games. Standalone
themes are evenly distributed; all four hero classes are included. Linked runs
start 20 times at each stage, using actual completed earlier shards for setup.
Every run completed without a failed invariant or unexpected exception.

| Check or action | Standalone | Linked | Total |
|---|---:|---:|---:|
| Paid replacements | 490 | 313 | **803** |
| Ordinary recruits | 518 | 279 | **797** |
| Full-army replacements | 213 | 125 | 338 |
| Rank-2-or-higher troops retired | 272 | 201 | 473 |
| Refused replacements, both saves unchanged | 2,050 | 1,189 | **3,239** |
| Paired saved next-turn probes | 190 | 113 | 303 |
| Territory losses in copied probes | 17 | 10 | 27 |
| Defenses started in copied probes | 5 | 0 | 5 |
| Random-prefix battle troop losses | 293 | 135 | 428 |
| Main-loop / cleanup state checks | 24,187 | 14,621 | 38,808 |
| Paired tactical rounds | 3,511 | 1,970 | 5,481 |

All ten recruitable incoming roles were exercised. Replacement payments total
31,401 gold / 310 crystals; no refund is applied. The report records outgoing
rank totals and current XP separately from battle losses, rather than treating
voluntary retirement as combat attrition. There were 36 exact paired linked
recoveries.

Random-prefix outcomes are not balance evidence: standalone prefixes end with
53 defeats and 67 still playing; linked prefixes end with 7 losses, 52 still
playing and 1 completed victory. The existing bounded cleanup deliberately
finishes remaining runs, and its forced waits, retreats and declined recoveries
remain separate metrics. No replacement UI or native-input claim is made.

Both reports begin from a clean checkout and verify all 64 recorded game,
framework and policy-helper source files remained unchanged during the runs:
[standalone evidence](evidence/eador-replacement-model-fuzz.json),
[linked evidence](evidence/eador-replacement-linked-fuzz.json).

```sh
uv run python tools/fuzz_eador.py --campaigns 120 --scenes 0 --steps 240 --report /tmp/replacement-model.json
uv run python tools/fuzz_eador.py --linked --campaigns 60 --scenes 0 --steps 240 --report /tmp/replacement-linked.json
```

## Input adapter and measured follow-up

The strict `PlayerState` adapter now exposes the read-only `replacement_preview`
query and drives `replace_troop` through Recruit → Replace troop → visible veteran
→ visible catalog role → explicit review confirmation → Return to shard. Both
pickers use their actual visible items and page counts. The displayed quote must
match the public query, browsing must leave the complete campaign unchanged, and
the confirmed result must equal the public command executed on an independent
copy. Returning to the shard must not repeat the purchase. The live campaign is
changed only by UI input. The adapter does not issue quicksave/load; callers own
that choice, just as with ordinary recruitment, building and equipment.

Three new public input tests use the retained paid army and pursuit states. They
exercise two consecutive replacements at 125% reading with fresh IDs in the same
formation slot, refused policy orders without input, ordinary recruitment after
replacement exhausts the actions, and exact caller-owned save/reload. In the
last-action case the hero cannot intercept, and the warned Heartwood is actually
lost on the following turn. A separate native adapter run passed both paid
replacements in 33 real input activations with two caller-owned reloads; the
125% Warden review image was inspected. This supplements the broader production
UI verifier described in the [replacement contract](eador-army-replacement-interface.md).

The scene fuzzer randomly navigates visible troop/role pages, cancels reviews,
opens Settings/Codex/Saves, confirms permitted quotes and attempts blocked Enter.
Draft and applied quicksave/load must recover the exact campaign; a draft choice
itself is intentionally not saved. Numeric inputs on an applied acknowledgement
cannot repeat its purchase, and Return/Esc must clear the old catalogs. Ordinary
recruit input remains in the same policy.

Clean source **a354961** completed 60 linked model runs and 60 scene runs with
**30,018 random input activations** in 153.2 seconds. All 65 recorded game,
framework and policy-helper files stayed unchanged. Linked model setup again
starts twenty real campaigns per stage; scene setup alternates standalone and
linked title starts and uses the Standard default. Setup and forced outcome
cleanup are excluded from the random-input count.

| Check or action | Model policy | Scene input |
|---|---:|---:|
| Confirmed replacements | 317 | 3 |
| Ordinary recruits | 284 | 67 |
| Experienced troops retired | 206 | 2 |
| Replacement refusals, exact unchanged state | 1,189 | 36 blocked Enters |
| Visible outgoing selections / final reviews | — | 69 / 49 |
| Canceled reviews | — | 16 |
| Exact draft / applied reloads | — | 53 / 2 |
| Paired replacement next-turn probes | 113 | — |
| Territory losses in those copied probes | 10 | — |
| Complete state checks | 14,622 | 31,336 |

Only three randomized UI orders reached confirmation: most reviewed replacements
were unavailable or canceled. The 30,018-input total is not a claim of 30,018
replacement decisions. The focused paid input tests and native journey cover
successful consequences directly. Likewise, these random outcomes do not assess
investment value or solve the late-economy balance gap. Model battle losses
(143) remain separate from voluntary retirements and copied rival probes.

The full combined suite passed **1,111 tests**; the independent Tribes fuzzer
passed 60 AI games and 20 random-input runs. The retained
[combined report](evidence/eador-replacement-input-fuzz.json) includes exact
counts, source hashes, platform and run limits.

```sh
uv run pytest tests/eador/test_replacement_input.py -q
uv run python tools/fuzz_eador.py --linked --campaigns 60 --scenes 60 --steps 240 --events 30000 --report /tmp/replacement-input.json
```
