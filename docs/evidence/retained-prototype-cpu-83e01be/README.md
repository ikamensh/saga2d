# Retained prototype CPU allowance

Recorded on 2026-09-06 in the isolated checkout at `83e01be3174b5a31f186af3343ed77cb4a4dbf92`
plus the CPU changes committed with this note. `source.sha256` identifies the four
changed tools, their budget helper, and the focused regression source. The probe
also records the game and preparation source hashes it used.

The late-realm, veteran-upkeep, departure-cargo, and camp-service prototype CLIs
now each use one shared `CpuBudget(25)` by default. Preparation, paired saved
comparisons, recovery, and continuation helpers receive that same allowance.
`--cpu-percent 100` explicitly bypasses cooperative sleeping. Reports record the
allowance and hash `tools/cpu_budget.py`. Experimental game rules and the default
sample matrices are unchanged.

## Focused integration checks

Each regression first failed because its public helper did not accept `budget`;
the four `red-*.txt` files retain those failures. After the corresponding change,
the complete focused selection passed: **4 passed in 0.32 seconds** (`tests.txt`).

```sh
uv run --extra dev python -m pytest tests/tools/test_retained_prototype_budget.py -q
```

The tests use fake process/wall clocks only to observe cooperative sleeping. They
run actual paid campaign preparation, recovered-shard waits, a cargo continuation,
and an infusion followed by battle. Default-paced and explicit-100 executions
must produce identical results. Preparation and later loops are observed
separately where both exist, so preparation sleeps cannot mask an unpaced
continuation.

## One real-clock probe

`probe.py` runs one retained `swords/chest/magic` cargo continuation with a real
25% allowance. From the repository root, the recorded command was:

```sh
/usr/bin/time -l uv run --extra dev python /tmp/saga2d-retained-prototype-cpu-probe.py > /tmp/saga2d-retained-prototype-cpu-probe.json 2> /tmp/saga2d-retained-prototype-cpu-time.txt
```

`probe.py`, `probe.json`, and `time.txt` are copies of those actual files. To
repeat this bounded probe, use the retained `probe.py` path in that command.

The helper completed **12 battle pairs**, reached victory on turn 14 with
544 gold and 27 crystals, and left its input unchanged. The helper plus result
serialization took **0.2277588 seconds wall time and 0.065486 seconds process CPU**,
or **28.7523% of one core**. Imports and source hashing are outside that measured
interval. Whole-command timing was 0.31 seconds real, 0.12 user, and 0.01 system.

This short run demonstrates yielding with real clocks. The existing allowance
checks after accumulated CPU work (50 ms by default), so its unfinished tail can
raise a short interval above 25%; it is not an operating-system quota or a
battery-life measurement. The campaign outcome is a regression check, not new
balance evidence.

All checks ran serially under the team's sole execution lease. No native window,
default prototype matrix, or full suite was launched. All owned processes were
terminal before the lease was returned.
