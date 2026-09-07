# Discovery migration review

These incremental checks ran in `/tmp/saga2d-adventure-variety-a7a6c50`, based on
`a7a6c5020232d539a7f4d616597942a47174b396`. They repair development policies and
their assertions after new site locations change the actual paid preparation.
No gameplay rule, character statistic, saved field or reward was edited.

The seven full follow-up logs retain every failure and **90 distinct passing
test executions**. Successful node IDs were excluded from subsequent runs.
`ledger.json` lists each attempt, failed node and actual passing node; the final
continuation passed **41 tests in 22.97 seconds**. This is an incremental result,
not a fresh full-suite run against the final combined source. Root's earlier
62-test run, eight passes before the first Aerie failure, and separate Scout
checks are retained elsewhere and are not added to this count.

`passed-nodeids.txt` is the runner's actual resume ledger: it also contains the
first Aerie test already passed by root, so its 91 entries must not be described
as 91 executions in these follow-ups. `serial-runner.py` records the final local
selection/resume mechanism, including that explicit prior pass. Its `/tmp`
paths describe the original execution environment.

## Actual failures and repairs

- **Aerie:** the changed route earns a rank-2, 32-HP Skyrider rather than rank 1
  with 28 HP. Enemy targeting changes, raising northern-route wounds from 34 to
  40 and leaving the bowman alive at 2 HP. The ready Pikeman now crosses the
  cleared northern lane and finishes that survivor in round 3. The failed
  sortie's stronger first attack leaves the saved bowman at 11 HP instead of 12.
  All five shared Aerie mock-input plans pass, including the actual paid retry.
- **Relief:** the varied route earns rank-3 Militia. Its retaliation deals seven
  damage instead of six, leaving the Guard at 35 HP rather than 36. The actual
  lost Pikeman, deadline failure, paid replacement and wounded retry remain;
  the shared failed-retry mock check passes.
- **Causeway:** Commander arrives on turn 8 rather than 9, retaining the same
  ten-mana entry, paid recovery and three-crystal infusion decisions. Scout now
  arrives on turn 6 with 14 mana; the old later-recovery/level-4 story no longer
  applies. Two routes resume the same actual rank-3 save: escape on round 4 with
  41 wounds, or spend four additional mana on Heal, survive another enemy phase
  and rout on round 5 with 27 wounds. No artificial rest or mana expenditure
  recreates the old entry. One intermediate test-edit failure read battle mana
  after reward resolution had cleared the battle; the comparison now precedes
  both normal reward checks.
- **Saved Codex:** longer recorded source descriptions move Mirror Badge off
  the final page. The test visits all pages and checks each missing-source
  entry, retaining exact saved-State equality. Root subsequently strengthens
  its rendered-body assertion separately; this ledger does not claim that
  later test revision was executed here.
- **Directed replay provenance:** an actual-input RED exposed the report's
  unconditional historical-autoplay wording for fresh campaigns. Fresh and
  earned journeys now receive different opening descriptions; existing input,
  save/reload and provenance checks pass.

The three diagnosis JSONs retain complete paid entries and actual tactical
results. Their `historical_world` branches load a genuine retained old world
and run the current preparation commands; they are not a claim to replay an
unchanged historical operator policy. These are bounded regression diagnoses,
not the separately declared fresh seed-5/12 manual journeys or balance evidence.

## Bounds and CPU

No native window, fresh manual route, build or new balance matrix ran here.
The following broad tests remain deferred:

- `test_each_theme_and_hero_can_finish_by_exploring_either_flank_or_the_direct_road`
- `test_all_heroes_can_win_opening_adventures_and_each_adjacent_conquest_in_every_theme`
- `test_purchased_active_passive_and_smaller_parties_hold_in_three_modes_and_five_worlds`

The 14,400-battle opening test **never started**: attempt 3 exited at Causeway
before reaching Worldgen, and the opening test was excluded before continuation.
There is no partial or cancelled matrix to count. The other two full crossproducts
were excluded throughout. Existing inexpensive generation/witness properties
remained in the narrow selection.

Jobs ran serially. The pytest runner uses `CpuBudget(25)` at test teardown and
the three model diagnoses checkpoint within preparation/orders. Existing atomic
test/verifier calls can exceed that allowance before yielding; this is not a
hard CPU quota or a battery-life measurement. All owned processes exited before
the execution slot passed to the Screen verifier repair.

The `.gz` files are lossless copies, verified against their original `/tmp`
files after decompression. `SHA256SUMS` authenticates the retained bytes.
