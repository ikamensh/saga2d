# Realm settlement — 2026-09-07

`eador.economy.settle_realm` applies upkeep, desertion and recovery to one hero
and returns the settled treasury/actions/log. It cannot advance a world or
opponent. Solo `State.end_turn` uses it before the existing rival advance.

38 tests pass across `test_pressure.py`, `test_difficulty.py` and
`test_realm_settlement.py`. Paid public-command preparation reaches a wounded
army; standalone settlement leaves all other serialized state unchanged and
matches ordinary end-turn settlement. Exact save/reload continuation passes.
An independent source review found no behavior changes or blockers.

The retained bounded fuzz receipt covers four linked model campaigns and two
scene runs, 43 end turns, 517 model checks and 366 scene checks. All four model
campaigns finish in defeat; this is not a victory or release-readiness claim.

```sh
.venv/bin/python -m pytest tests/eador/test_pressure.py tests/eador/test_difficulty.py tests/eador/test_realm_settlement.py -q
.venv/bin/python tools/fuzz_eador.py --campaigns 4 --scenes 2 --steps 120 --linked --cpu-percent 25 --report /tmp/shardbound-realm-settlement-fuzz.json
```

The shared world, separate realms and campaign Ready barrier remain to be built.
