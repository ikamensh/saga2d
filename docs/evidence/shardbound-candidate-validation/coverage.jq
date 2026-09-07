# Read-only accounting: input is the seven chronological tranche reports.
# --slurpfile native_nodes supplies PASSED node IDs from the native log.
# --slurpfile campaign supplies the separate bounded model report.
. as $reports
| ($reports[0].selected | unique) as $initial
| ($reports[-1] | (.selected + .deselected) | unique) as $final_collection
| ($initial - $final_collection) as $removed
| ([$reports[].results[] | select(.phase == "call" and .outcome == "passed") | .node] | unique) as $historical
| ($historical - $removed) as $current_mock
| ($native_nodes[0] | unique) as $native
| (($current_mock + $native) | unique) as $current_passed
| ($initial - $removed) as $expected
| ($reports[0].deselected | unique) as $deferred
| ($reports | map(.source_sha256 | with_entries(select(.key | test("^(eador|saga2d|tribes|warband)/"))))) as $runtime
| {
    tranche_sources: [$reports[].source_commit],
    initial_ordinary: ($initial | length),
    final_collected: ($final_collection | length),
    removed_nodes: $removed,
    removed_historical_passes: ($historical - $current_mock),
    historical_passed: ($historical | length),
    current_mock_passed: ($current_mock | length),
    native_passed_nodes: $native,
    current_unique_passed: ($current_passed | length),
    explicitly_deferred: ($deferred | length),
    missing_expected_passes: ($expected - $current_passed),
    unexpected_passes: ($current_passed - $expected),
    current_unaccounted_nodes: ($final_collection - $current_passed - $deferred),
    deferred_not_in_final_collection: ($deferred - $final_collection),
    failure_stops: ([$reports[].results[] | select(.outcome == "failed")] | length),
    all_scoped_sources_unchanged: ($reports | all(.source_unchanged)),
    identical_runtime_files: ($runtime[0] | length),
    runtime_maps_identical: ($runtime | all(. == $runtime[0])),
    tranche_wall_seconds: ([$reports[].elapsed_seconds] | add),
    tranche_cpu_seconds: ([$reports[].cpu_seconds] | add),
    bounded_campaign: {
      completed: $campaign[0].completed,
      direct: ([$campaign[0].runs[] | select(.recovery == false)] | length),
      recovery: $campaign[0].recovery_runs,
      shard_records: ([$campaign[0].runs[].stages | length] | add),
      source_files: ($campaign[0].source_sha256 | length),
      hashes_match_final_tranche: ($campaign[0].source_sha256 | to_entries | all(. as $entry | $reports[-1].source_sha256[$entry.key] == $entry.value))
    }
  }
| if (.initial_ordinary == 1546 and (.removed_nodes | length) == 4
      and .historical_passed == 1541 and .current_mock_passed == 1540
      and (.native_passed_nodes | length) == 2 and .current_unique_passed == 1542
      and .explicitly_deferred == 159 and .final_collected == 1701
      and .missing_expected_passes == [] and .unexpected_passes == []
      and .current_unaccounted_nodes == [] and .deferred_not_in_final_collection == []
      and .failure_stops == 6 and .all_scoped_sources_unchanged
      and .identical_runtime_files == 110 and .runtime_maps_identical
      and .bounded_campaign.hashes_match_final_tranche)
  then . else error("Candidate coverage does not reconcile with the final live collection") end
