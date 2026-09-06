# Stranded Explorer source evidence

Source: `5cdb39e`. Production content/helper checkpoint: `e041337`; the later
commit adds the actual deadline-loss/replacement regression. Both JSON reports
record source hashes; no source file changed during either run. Exact Python
and platform metadata are retained in the files.

`paid-mode-routes.json` contains 60 ordinary purchased preparations and manual
escapes: Accessible/Standard/Challenge, seeds 0/1/2/7/19, Commander north/south,
Warrior with Acolyte, and smaller Scout without an escort. Every manual order
reloads exactly, relevant immediate forecasts match effects, every player
survives, and each reward is checked once. Four Standard seed-seven examples
retain complete orders, tactical logs and terminal battles. The same prepared
armies' 60 automatic battles all win by rout, with actual wounds, mana and
casualties recorded. These are reproducible policies, not optimality claims.

`fuzz.json` covers 300 randomized model campaigns (100/theme) and 20 mock scene
runs with 10,003 random inputs. Both Explorer assemblies occur: 15 north and
seven south. Random play plus cleanup ends in one victory and 299 defeats;
that is a robustness result, not a winning strategy benchmark.

The full suite passed 959 tests at `e041337`; all ten Explorer tests pass at
`5cdb39e`, including the subsequently added deadline case. Their real prior
Caravan fixture was generated with source `11797b8`; complete old v12 world
and continuation data stay exact. The Camp-first test reaches both actual
duplicate Boots choices through earned play and verifies saved once-only
conversion. The site, required Frontier sources and all twelve relics across
the themes are checked over 100 seeds.

Reproduce the behavior checks and randomized run:

```sh
PYTHONPATH=. python -m pytest -q tests/eador/test_stranded_explorer.py
PYTHONPATH=. python tools/fuzz_eador.py --campaigns 300 --scenes 20 --events 10000 --steps 120 --report /tmp/explorer-fuzz.json
```

For the mode matrix, construct `State.new(seed, hero_class, difficulty=mode)`,
pass it to `prepare_explorer(state=..., support=...)`, and replay the helper
named in `eador-stranded-explorer.md` using the saved `Journey` adapter from
`tests/eador/test_extraction_journeys.py`. The report names every input and
records actual preparation costs, levels and arrival turns. Native input and
briefing-fit evidence are tracked separately by root; these two reports are
model/mock evidence only, and do not complete G05 or a release gate.
