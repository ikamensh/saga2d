# Current paid investment reproduction

Model source: clean **4c555b252255073e25ff42de347c5ab8650a0b90**, 2026-09-06.
This resumes the bounded research described in
[the investment comparison](../../eador-authored-investment-comparison.md).
It does not complete G04/G07 or justify a general economy change.

Commands, executed serially from the investment worktree:

```sh
uv run --extra dev python tools/prototype_eador_early_conversion.py --authored --repeat --report /tmp/earned-investment-current.json.gz
uv run --extra dev python tools/prototype_eador_early_conversion.py --tactical-control-from /tmp/earned-investment-current.json.gz --report /tmp/earned-smoke-control-current.json.gz
```

Both exited 0. The default selection is one Standard Commander/Ruins seed-zero
window, and both reports record the cooperative 25% CPU allowance. The repeated
pilot retains **ten branches**; the Smoke/Guard command now writes its final
report successfully, including the exact serialized Smoke-result assertion.
The same 12/23 wound totals remain. The old large interrupted matrix was not run.

The original pilot's model result is in `authored-commander.json.gz`. The fresh
explicit timing choice is in `smoke-guard.json.gz`; these use the current tool
report schema, distinct from the historical exploratory Smoke/Guard payload.

Native command:

```sh
caffeinate -diu uv run --extra dev python tools/verify_eador_investment_choice.py --input-report docs/evidence/earned-specialist-investment-4c555b2/smoke-guard.json.gz --output /tmp/earned-smoke-ui-native --backend pyglet
```

It exited 0 on macOS 26.6.2 / Apple M4 at 1280×800 logical, 2560×1600 physical
pixels. A mock-input invocation also passed before it. The native report names
parent `4c555b2`, because the verifier itself was newly written; its complete
recorded source hashes are retained and verified against the committed verifier.
No game, framework, data or save-schema code changed.

| First order | Native inputs | Exact UI reloads | Result | Living missing HP |
|---|---:|---:|---|---:|
| Smoke at (3,-2) | 33 | 4 | R4 victory, no deaths, 2 mana | 12 |
| Guard | 18 | 3 | R4 victory, no deaths, 2 mana | 23 |

Both begin by loading an **unedited earned round-three campaign save** through
F9, issue the one deliberate choice, then use ordinary automatic rounds and
visible Finish playback. The native first-order state, tactical result and final
campaign State exactly equal the corresponding model continuation. Both save and
reload through real controls. Guard can still use Smoke later; the comparison
concerns timing. This is not native preparation, optimal manual play or human
playtesting. Three actual PNGs were opened: Smoke forecast and both outcomes.
Windows and awake helpers closed after verification.

Audit regressions:

```sh
uv run --extra dev python -m pytest tests/tools/test_investment_budget.py tests/tools/test_investment_targets.py tests/tools/test_cpu_budget.py -q
```

**14 passed in 2.15s.** The first regression checks that CPU checkpoints preserve
the complete paid baseline outcome. The target regression begins with the retained
real Ruins camp, pays for a Sapper and approaches Sealed Vault. It failed before
the correction because the defensive rest moved the hero away and the target was
not explored. It now returns to the actual target before entering. The tests also
retain the existing CPU budget behavior checks.
