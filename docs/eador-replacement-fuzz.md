# Replacement-aware model stress

The model policy in `tools/fuzz_eador.py` now exercises the public replacement
command alongside ordinary recruiting. No game rules or scene input adapter
changed in this tranche. The model interface is documented in
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

Input coverage follows after the replacement UI publishes its controls. It must
use explicit visible outgoing/incoming selection and confirmation through
`PlayerState`, rather than falling through to a direct model mutation.
