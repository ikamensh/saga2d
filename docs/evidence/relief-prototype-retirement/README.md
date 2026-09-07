# Superseded Relief prototype retirement

The candidate sweep stored as `b2e3120` (actual source `6c51f22`) stopped in the old detached prototype's
`source_audit()`, which assumed the fixed locations used when proposing Relief's
initial displacement. Production Relief and subsequent seeded placement have
superseded that experiment. Updating its displacement calculation to today's
generator would create a different proposal, not verify the shipped encounter.

The production `relief_column` definition, generated reward preservation,
forward/western assemblies, paid Commander/Scout/passive routes, finite failed
support/retry, saved outcomes and native verification remain in their existing
game, helper and test files. No production caller imported the prototype.
Only the obsolete runner and its three dedicated budget tests were removed.

All removed nodes belonged to `tests/tools/test_verifier_preparation_budget.py`:

| Removed test | Status in the original `b2e3120` sweep |
|---|---|
| `test_prototype_paid_preparation_and_saved_orders_share_the_allowance` | Passed; exclude this historical pass from current coverage |
| `test_bounded_prototype_cli_preserves_search_and_world_results_with_default_pacing` | Failed on the old fixed-site assertion |
| `test_detached_search_and_world_audit_each_yield_without_changing_results` | Not reached |

The [historical proposal](../../eador-eleventh-encounter-proposal.md) now gives
isolated reproduction at `4608d1e988bd630b0c302712160c97ad9a913584`. Its original
prototype SHA-256 is
`c450a4698cf345e0fb5afbeefc797176851b6a35ba1b998498e9f9d14414215e`, matching the
retained revised report. Both original compressed reports and later historical
CPU evidence remain unchanged. The revised report's 1,000 source witnesses remain
an input to `tests/eador/test_relief.py`; that evidence was not removed with the
runner. No detached search, new simulation or gameplay change was performed for
this retirement.

Post-removal collection of `tests/tools/test_verifier_preparation_budget.py`
found exactly eight remaining cases in 0.02 seconds ([raw output](collection.txt)).
No test bodies were rerun; the candidate sweep continues with the remaining
checks and subtracts the one removed pass identified above.
