# Three paid army-plan pilots

These are three serial model-command runs on 6 September 2026, one Standard
seed-7 linked campaign per plan, through Foundries then Throne. Each used the
default cooperative 25% allowance for one CPU core. All processes finished.

## Source identity and retained scope

The reports were generated with the new audit tool still uncommitted on base
`2d775de99dd1699d8f71e34e9cf63e4c4e57cda2`. Their `source_commit` field correctly
records that base; it must not be mistaken for a clean build containing the tool.
The executable tool was subsequently committed, unchanged, as
`cd351a93137c4eb77150ba6dfb552beead8bb3be`.

All **32 recorded source hashes in each report** were independently compared
with the corresponding `git show cd351a9:<path>` contents and matched. These
hashes cover `eador/**/*.py`, `tools/audit_eador_army_plans.py`,
`tools/audit_eador_economy.py` and `tools/cpu_budget.py`. They do not cover
`saga2d/**/*.py`, `tools/eador_campaign.py`, dependencies or the Python runtime;
these pilots do not constitute a packaged-candidate certificate. The reports'
source-unchanged checks apply to their recorded file set only.

`sha256.json` records the sizes and hashes of the three unmodified gzip reports
and this README. The compressed reports together occupy **842,874 bytes**.
Each contains complete before/after state journals, actual purchase and
replacement costs, selected skills/equipment/retinues, and tactical outcomes.
The next command actually resumed from the saved result of the previous command.

## Commands and outcomes

```sh
uv run --extra dev python -m pytest tests/eador/test_army_plan_journey.py -q
uv run python tools/audit_eador_army_plans.py --plan sustain --output /tmp/shardbound-army-sustain-pilot.json.gz
uv run python tools/audit_eador_army_plans.py --plan mobile --output /tmp/shardbound-army-mobile-pilot.json.gz
uv run python tools/audit_eador_army_plans.py --plan control --output /tmp/shardbound-army-control-pilot.json.gz
```

The Commander tracer passed: **1 integration test in 3.14 seconds**. Each CLI
attempt completed the three shards. These commands describe independent serial
runs, not a batch to launch concurrently.

| Report | Total shard turns | Fallen troops | Tactical defeats | Recruitment gold | Recruitment crystals | Full target formation at battle entry | Saved commands |
|---|---:|---:|---:|---:|---:|---:|---:|
| `sustain.json.gz` | 35 | 4 | 0 | 345 | 0 | 26 / 33 | 230 |
| `mobile.json.gz` | 44 | 32 | 2 | 1,250 | 0 | 33 / 37 | 299 |
| `control.json.gz` | 82 | 22 | 1 | 1,365 | 33 | 24 / 41 | 368 |

Sustain made one paid retirement; Mobile one; Control three. Tactical casualties
were replaced through the disclosed role priorities instead of converging on
Swordsmen. The large Mobile losses and Control's 46-turn opening shard are
limitations of these policies, not hidden failed runs. **Control lost every
troop in the final battle**, while its hero still completed the campaign.

## Acceptance limits

No manually selected tactical orders, native input, screenshot, player
understanding or human playtest credit is claimed. Every tactical round used
explicit autoplay. No capital was lost, so the tool's real recovery branch was
not exercised. These are one-seed executable purchase/continuation examples,
not evidence that all three formations are balanced, enjoyable or robust.

G04 remains incomplete. The next work is deliberate manual decisions and
counter-scenarios using the earned states, especially protecting mobile troops
and determining when specialist orders justify their cost. See
[the plan descriptions](../../eador-army-plans.md).
