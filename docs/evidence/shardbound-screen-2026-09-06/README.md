# Screen model evidence, 2026-09-06

Measured production source: **783f8d6**. The later evidence commit changes only
retained artifacts, documentation and removal of the absorbed throwaway
prototype; no game rules, catalogue, routes or save expectations changed.

- Full suite: **1,048 passed**, 70.50 seconds. It includes seven new Screen
  integration tests, exact real old Grove/Caravan continuations, paid failed
  recovery/retry, required-source audit over 100 seeds, and all guidance sizes.
- `paid-orders.json`: four actual paid Standard seed-seven plans, **160 public
  tactical commands and 160 exact full-State reloads**, including exact immediate
  attack/Heal forecasts. Complete prepared/terminal saves, purchase costs, public
  commands and source hashes are retained. No player dies during these four
  encounter plans. The smaller Scout preparation had already lost one Militia
  in earlier conquest; the report does not hide that prior casualty.
- Strict route results: western Commander round 4 / 62 wounds / 0 mana; western Heal
  round 5 / 44 wounds / 4 mana; northern round 5 / 43 wounds / 8 mana; smaller Scout
  round 6 / 55 wounds / 8 mana. These are demonstrations, not optimized policies.
- The same report retains a separate 45-case exploratory fixed-script probe
  over three modes and seeds 0/1/2/7/19: 24 completed routs, 17 command sequences
  requiring adaptation, and four unfinished sequences. A changed veteran level
  or a different earlier casualty changes exact damage/army order. These are
  **not** counted as 45 wins, nor automatically labelled gameplay defects. Both
  Commander scripts won all ten Standard/Accessible preparations (20 runs).
- `fuzz.json`: **300 randomized campaigns**, 100 per theme, and **20 mock scene
  runs**, with **10,003 random input activations**. It exercised Screen entry
  16 times west and 15 north. There were 36,572 model-state checks and 10,413 scene
  state checks. Random cleanup ended in one victory and 299 defeats; this is
  robustness evidence, not a successful strategy sample. Sources did not change
  during either measurement.

The future-world comparison helper is restricted to historically recorded
Rootward **advance outputs**. It constructs expected new province arrays from
current generation while comparing every other recorded field exactly. Fixture
bytes/provenance, loaded old worlds, active battles, rest and recovery remain
unchanged. See [the policy](../../eador-save-continuation.md).

Reproduce from an isolated checkout of source 783f8d6, with this retained harness:

```sh
PYTHONPATH=. python docs/evidence/shardbound-screen-2026-09-06/audit.py /tmp/paid-orders.json
PYTHONPATH=. python tools/fuzz_eador.py --campaigns 300 --scenes 20 --events 10000 --report /tmp/fuzz.json
python -m pytest -q
```

The harness file is an evidence artifact copied into the source checkout for
replay; its SHA-256 is included in the report. No native interaction, screenshot
approval, content-wide balance, human playtest or release gate completion is
claimed here. Root owns the native Screen integration.
