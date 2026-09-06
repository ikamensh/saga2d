# Aerie model checkpoint

Measured game/source: `d5b9a29`. Full suite: **1,111 passed**. Independent review
reproduced the fixed sources, prior Barrow continuation and finite failure/retry.

- `paid-orders.json.gz`: four actual purchased Standard seed-seven plans plus
  a failed sortie/passive defense and changed-assembly retry. All **362 manual
  commands** have exact full-campaign save/reloads. Relevant immediate attack,
  spell and Repulse forecasts match; flight-only landing queries are explicitly
  labelled counterfactuals. The compressed file retains every intermediate state.
- `randomized.json`: **300 model campaigns** (100 per theme), **20 mock scene
  runs**, **10,006 random input activations**, 58,547 model state checks and
  10,466 scene state checks. Recorded source hashes stayed unchanged. Most random
  policies lose; this is robustness evidence, not a strategy success rate.
- `script-scope.json`: unchanged literal development scripts on seeds
  `0,1,2,7,19` across all three difficulties. They need adaptation when earned
  soldiers, HP, mana or enemy landings differ. Counts of all-surviving routs
  (west/north/Scout, out of five): Standard `4/2/4`, Accessible `1/0/5`,
  Challenge `2/2/4`. An invalid scripted order is not evidence that the encounter
  is unwinnable. In particular, the cheaper-mana western plan spends fewer
  resources but is not robust to every weaker arrival.

A separate complete old/current world comparison used old source `0745f6c`:
all 300 generated province arrays were compared field-for-field after applying
only Aerie's seven site fields to Ruins `(0,0)`. All 100 Frontier and 100
Elderwild arrays were identical; only that site changed in each Ruins array.
Every old per-world relic availability set remains a subset of the new set.
The preserved source and actual old battle are executable public regressions in
`tests/eador/test_aerie.py`; the original saved fixture bytes remain unchanged.

Reproduce the paid audit with `tools/audit_eador_aerie.py --output /tmp/aerie.json.gz`.
Reproduce robustness with `tools/fuzz_eador.py --campaigns 300 --scenes 20 --steps 240
--events 10000 --report /tmp/aerie-fuzz.json` from this source, with `PYTHONPATH=.`.
No native route or human playtest claim belongs to this model checkpoint.
