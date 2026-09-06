# Older audit CLI CPU limits — 6 September 2026

Commit `8312c84` closes a gap left after the framework frame limiter and fuzz
allowance: nine older standalone audit/stress commands still bypassed CPU
pacing. Economy, difficulty, crystal demand, worlds, linked campaigns,
disciplines, control, roles and relics now share one `CpuBudget(25)` throughout
their work, including repeats, earned preparation, recovery and tactical orders.
`--cpu-percent 100` explicitly disables sleeping. No game or framework code changed.

Existing matrix selections are preserved. Economy, difficulty and crystal
demand additionally accept hero/theme/plan filters for small probes. Heavy local
jobs run serially; per-process allowances add together. Direct tests and `tick`
remain unpaced. The previously cancelled large matrix and soak were not restarted.

## Verification

The focused integration command passed **62 tests in 5.71 seconds**:

```sh
uv run --extra dev python -m pytest tests/framework/test_frame_pacing.py tests/tools/test_player_input_pacing.py tests/tools/test_cpu_budget.py tests/tools/test_investment_budget.py tests/tools/test_investment_targets.py tests/tools/test_audit_cli_budget.py tests/tools/test_campaign_audit_budget.py tests/tools/test_stress_budget.py tests/eador/test_active_relics.py tests/eador/test_extraction_journeys.py tests/eador/test_discipline_journeys.py tests/eador/test_army_decisions.py -q
```

The last test is the separate paid-decision tracer committed as `474b41a`.
Pacing tests compare actual campaign rows, complete saved states and random
tactical outputs with and without yielding. Clock-controlled tests verify the
yield itself without relying on machine speed. The new tracers were observed
failing before the missing entry-point/helper arguments were implemented.

Two small, serial CLI checks also passed at their default allowance:

```sh
/usr/bin/time -p uv run --extra dev python tools/audit_eador_difficulty.py --seeds 10 --heroes Commander --themes ruins --plans economy --modes standard --routes direct --report /tmp/shardbound-paced-difficulty.json
uv run --extra dev python tools/stress_eador_relics.py --policies 1 --report /tmp/shardbound-paced-relics.json
```

The difficulty check completed ten campaigns. Whole-command timing, including
startup, was 0.79 seconds wall / 0.26 user / 0.03 system: about 37% of one core
over this short interval. This does not imply a hard 25% OS quota. The cooperative
allowance yields around 50 ms work blocks; startup and an unfinished block can
exceed the target over short measurements. The relic check completed one policy
for each of four earned checkpoints, with 176 complete campaign-save checks
and four resolution checks. These are bounded executability checks, not balance
or sustained-performance acceptance.

Both reports were produced before committing on base `1aab5b7`; their original
revision fields are retained. All 34 difficulty and 83 relic source hashes match
the committed files at `474b41a`, as recorded in `source-verification.json`.
Independent read-only review found no missing propagation or changed decisions.
All Saga2D processes ended. The busy `gleaner-backfill` process belonged to a
different project and was left running. No battery lifetime measurement is claimed.
