# Relief production evidence

Frozen source: `c6093de99e468e360561922b231fa7df9205a8a3`, including root HUD
`ef9a67f`. The working tree was clean throughout verification; only this evidence
and the accompanying report were added afterward.

- `model-orders.json.gz`: 30 genuinely purchased arriving parties, 60 manual
  holds, 1,740 complete-State order reloads, exact post-reward states, and a
  natural missed-support defeat plus fresh paid Pikeman/automatic finite retry.
- `native-journeys.json.gz`: all seven actual input journeys, source hashes,
  event streams, purchases, outcomes and complete final saves. 1,202 input
  activations and 71 exact reloads; native screenshot filenames identify the
  inspected states. The failed retry's three automatic rounds are explicit.
- `standalone-fuzz.json`: 300 model campaigns and 20 scene runs, including
  10,009 random input activations. Rejections and continuation checks are
  counted separately from setup/cleanup.
- `linked-fuzz.json`: 60 linked, stage-distributed model runs and exact saved
  continuations. Random play does not establish a campaign-winning policy.
- `tests.txt`: 1,168 full-suite tests passed. Existing Pillow deprecation warnings
  are retained in the output.
- `tribes-fuzz.txt`: 60 AI games and 20 monkey-input runs passed.
- `provenance.json`: artifact checksums, source ID and the inspected-image list.

The [production report](../../eador-relief.md) explains the actual paid costs,
ordinary reward witnesses, passive alternative, failures and limits. Original
and revised detached prototype evidence stays separately retained; these are
not interchangeable source states. This establishes 11/12 authored patterns,
not G05 completion, all-class coverage, optimal play or balanced difficulty.
