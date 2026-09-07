# Candidate validation: completed ordinary selection

**All 1,542 current ordinary cases passed**, across seven regression tranches and
the separate two-test native display check. **159 cases remain explicitly deferred
from this ordinary selection.** This is scoped coverage across successive test/tool
revisions, not one full-suite invocation or a claim that the deferred matrices ran.

The exact accounting is **1,546 initially selected − 4 retired = 1,542 current
cases**. Historical mock passes total 1,541, including one subsequently removed
Relief-prototype test: **1,540 current mock passes + 2 native passes = 1,542**.
`coverage.jq` verifies set equality against the final collection, not just matching
counts; `coverage.json.gz` retains its result. There are no missing or unexpected
current ordinary nodes. The final collection contains 1,701 cases including the
159 explicit deferrals.

| Actual source / stored directory | Additional mock passes | Cumulative historical mock passes | Display skips | First failure | Wall / CPU seconds |
| --- | ---: | ---: | ---: | --- | ---: |
| `03a5044` | 301 | 301 | 0 | Paid briefing preparation | 283.051 / 70.222 |
| `3f4e59f` | 133 | 434 | 0 | Earned Pin relic sources, Frontier | 65.110 / 16.234 |
| `7a29510` | 201 | 635 | 0 | Complete saved-victory input journey | 133.263 / 33.243 |
| `e5840c7` | 486 | 1,121 | 2 | Retained cargo-prototype preparation | 178.842 / 43.098 |
| `4094c85` | 4 | 1,125 | 2 | Vault continuation's old source coordinate | 3.069 / 0.819 |
| `6c51f22` / `b2e3120` | 8 | 1,133 | 2 | Superseded detached Relief prototype | 43.213 / 10.846 |
| `8bf2eb2` / `final` | 408 | 1,541 | 2 | None; exit 0 | 116.980 / 28.780 |

The first six tranches exited **1** at their first failure; the seventh exited
**0**. All seven report unchanged scoped source hashes during their own run.
Their **110 game/framework Python files under eador, saga2d, tribes and warband
are byte-identical across all seven receipts**. Total measured tranche time was
**823.528 seconds wall / 203.241 seconds CPU**. The final pytest console reports
116.80 seconds; its enclosing receipt measures 116.980 seconds.
The continuation runner excludes previously passed nodes and authenticates its
immediate predecessor report by SHA-256; all six links match the retained
originals. The counts above deduplicate passed call-phase node IDs across the
seven receipts. Repeated display skips are only two unique nodes. Focused reruns
below overlap this coverage and are not added again. The sixth directory's name
`b2e3120` is not its execution source: the receipt identifies **6c51f22**.

The initial selection contained 1,546 ordinary cases, with 159 cases explicitly
excluded by 12 named test families. The retained runner lists the exclusions:
large world/hero/policy/linked-campaign matrices and two packaged-campaign cases.
Those two package cases were checked separately. Pacing requested 25% CPU through
the shared `CpuBudget`, cooperatively between tests; an atomic test can exceed
that allowance. This archive does not establish a full-suite or packaged-app pass.

Both skips were display-dependent framework tests:
`test_immediate_images_show_where_this_frame_drew_them_and_nowhere_else` and
`test_control_click_is_a_right_click_on_a_mac`. Their module requires an available
display for a hidden pyglet window. They were skipped at setup in the tranches,
then both **passed in 0.51 seconds** after waking the display with bounded
`caffeinate`; see `native-framework/pytest.log`. The run owner recorded clean
**7b5562d** as their launch source. That revision only updates evidence wording
relative to the final tranche's **8bf2eb2** runtime.

## Six first failures and their disposition

1. **Paid briefing preparation** —
   `tests/eador/test_guidance_reading.py::test_all_paid_briefings_and_wounded_retries_fit_both_sizes_without_committing`.
   The moved Crossing was reached with 80 gold. The old preparation bought Archery
   for 55, then tried an unaffordable Marketplace. Commit `3f4e59f` instead uses
   the affordable Archery purchase, pays the existing 20-gold guide fee and
   retreats. Actual balances are **80 → 25 → 5 → 0**: retreat loses the last five
   gold and does not refund the guide fee. The separate accounting RED retains an
   incorrect expected final five gold; the final runner corrects that expectation.
   Both reading sizes still test the free approach as available and the guide as
   blocked. Four focused checks passed in **11.82 seconds**. The measured runner
   receipt records 11.903 seconds wall / 3.207 seconds CPU. This changed paid
   verification preparation and assertions, not game prices or rules.

2. **Pin relic source lookup** —
   `tests/eador/test_pin.py::test_real_adventures_award_equip_and_activate_both_relic_capabilities[frontier]`.
   Old coordinates no longer supplied Wayfarer Boots. Commit `7a29510` finds the
   recorded Den, Explorer's Camp and Border Watch, builds the party through the
   existing paid travel/battle helpers, and retains the earned-relic capability
   and save assertions. All three theme cases passed in **0.31 seconds**; the
   focused runner measured 0.586 seconds wall / 0.144 seconds CPU. This is a test
   route migration, not a relocated or freely granted reward. The original
   filename says `3f4e59f`, but the focused receipt's actual source is **33638bf**;
   use its exact hashes and source field for attribution.

3. **Saved-victory input journey** —
   `tests/eador/test_scene.py::test_complete_campaign_and_saved_victory_through_player_input`.
   The seed7 itinerary now opens Courier's Crossing at Heartwood and Stranded
   Explorer at Stonecross. The old test expected a battle immediately after X.
   Accepting the actual briefings cleared all five itinerary sites, but its old
   unconditional post-Barrow rest then caused a **real turn-10 capital loss**.
   That failed state and log are retained, not recast as a selector failure.
   Commit `e5840c7` applies the test's existing visible-rival threat check to every
   rest, including post-site recovery, and removes the old Relief-only skip.
   It wins the single shard on **turn 9**, with **412 gold / 23 crystals**, Commander
   **27/48 HP**, Archer #3 **28/28 HP** and Swordsman #6 **21/42 HP**. Militia #1/#2
   and Swordsmen #4/#5 died at Duskspire. No free resources, forced army, reroll or
   rule change was used. The journey uses public input, including its existing
   Auto-play one round control; it is not manual tactical play. F5, New shard and
   F9 restore this exact wounded victory and the original two-scene structure.
   The narrow check passed in **2.55 seconds**. This covers one shard, not a full
   three-shard campaign.

4. **Retained cargo prototype** —
   `tests/tools/test_retained_prototype_budget.py::test_cargo_earned_preparation_and_one_paid_continuation_each_yield`.
   The prototype assumed a particular earned Adept survived; current preparation
   did not retain that troop and raised `StopIteration`. Its owner subsequently
   retired the unshipped prototype and its dedicated test in **4094c85**, preserving
   the actual survivor record and earlier results. See the separate
   [cargo-retirement evidence](../departure-cargo-retirement/README.md). Retirement
   is maintenance of a stale proposal tool, not a passing result for that policy,
   a gameplay change, or permission to recreate the missing unit. The next
   ordinary tranche passed four further cases before the Vault assertion below.

5. **Vault continuation source assertion** —
   `tests/tools/test_vault_continuation.py::test_vault_approaches_share_an_earned_army_and_preserve_their_campaign_consequences`.
   The existing paid preparation and manual escape reached the saved Vault, but
   the audit still asserted that old coordinate `(-1, 1)` was cleared. Its owner
   repaired the audit/test to inspect the actual earned Vault province and made
   the production-route description independent of its changed adventure name.
   The paid army, both manual routes, prices, production target and continuation
   policy remain unchanged. Two focused checks passed in **1.22 seconds**; see
   the separate [Vault repair record](../vault-continuation-4094c85/README.md).
   Its current paid/free endpoints differ (turn 8 versus turn 13), so the old
   matched-endpoint net-benefit interpretation does not carry forward. Both
   existing audit tests subsequently passed in the sixth ordinary tranche.

6. **Superseded detached Relief prototype** —
   `tests/tools/test_verifier_preparation_budget.py::test_bounded_prototype_cli_preserves_search_and_world_results_with_default_pacing`.
   Its detached source audit still assumed the placement used by the original
   proposal. Production Relief and seeded placement had superseded that runner;
   there were no production callers. Commit **8bf2eb2** retires it and exactly
   three dedicated tests, preserving the historical evidence and production
   witnesses. See [Relief retirement](../relief-prototype-retirement/README.md).
   `test_prototype_paid_preparation_and_saved_orders_share_the_allowance` had
   passed in the sixth tranche and is explicitly subtracted from current coverage.
   The bounded CLI test failed; the detached-search test was not reached. Together
   with the retired cargo test, these are the four removed nodes recorded in
   `coverage.json.gz`. No production feature was removed and no missing survivor,
   reward or source was fabricated to make an old proposal pass.

## Separate bounded campaign model audit

`bounded-campaign/` retains the exact report and log for
`tools/audit_eador_campaign.py --seeds 1 --cpu-percent 25 --output /tmp/shardbound-current-campaign-audit.json`.
It completed **24/24 campaigns: 16 direct and 8 recovered, with 72 shard records**,
in **7.01 seconds** at the requested 25% allowance. This uses the existing explicit
tactical auto command and one seed index across the tool's configured paths;
it is not manual tactical play, a seed-diversity result or an additional 24 ordinary
test nodes. Its final phases are all `completed`.

The report has **no source_commit field**. The run owner recorded launch from clean
**7b5562d**; the report's **39 exact source hashes** are authoritative and match the
final tranche's source map. No separate measured CPU-seconds value is supplied.

## Other retained checks and file provenance

`packaging/campaign-mock.log` records **2 passed in 24.60 seconds** for the direct
and recovery packaged-campaign mock journeys. This is not a native packaged
executable run. The earlier product text fixes have their own
[viewed native evidence](../candidate-escape-guidance/README.md).

Each `tranches/<source>/` contains its exact stdout log plus losslessly compressed
`report.json` and `tests.jsonl`. `guidance-fee/` and `pin-sources/` retain diagnosis,
focused results and final runner bytes. `complete-journey/` retains both failures,
the narrow GREEN and exact saved loss/victory envelopes. Runner copies use
**`.py.txt`** so retaining evidence cannot expand the running sweep's tracked
Python-source fingerprint. The fee runner is the final corrected version; the
earlier incorrect accounting assertion is evidenced by its RED log.

`originals.tsv` maps all **42 original files** to their archive names and records
the SHA-256 of each original uncompressed file. Every copied file and every
decompressed JSON/JSONL was compared byte-for-byte with its original. No tests,
game/model preparation, native windows or builds ran while creating this archive.
