# Combined depth-tool integration — 2026-09-06

Source `64cfe7a` integrates the investment target correction, cooperative audit
budgets, native Smoke decision verifier and three persistent paid army policies.
Only unrelated `.gitignore` work was dirty. A direct diff against `a6851fb`
showed no changes in `eador/`, `saga2d/` or `packaging/`.

Executed in the repository root, after all native/pilot processes had ended:

```sh
uv run --extra dev python -m pytest tests/tools/test_investment_budget.py tests/tools/test_investment_targets.py tests/tools/test_cpu_budget.py tests/eador/test_army_plan_journey.py -q
```

Exec session `14362` ended with exit 0. Captured output:

```text
...............                                                          [100%]
15 passed in 3.86s
```

This checks the earned campaign budget equivalence, real rival-detour target
regression, existing CPU-budget behavior and Commander paid linked campaign
with exact per-command saved continuation. It does not rerun all game/framework
tests or establish balanced manual armies. The accompanying native comparison
and three model pilots retain their own source identities and limitations.
Final process inventory contained no game, native verifier, audit or pytest job.
