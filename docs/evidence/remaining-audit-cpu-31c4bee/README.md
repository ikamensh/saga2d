# Remaining audit CPU limits — 2026-09-06

Source **31c4bee** closes additional development-tool gaps found while checking
the user's CPU/battery report. The game/framework bytes remain those in the
verified **32f354c** Mac archive.

Resource-breakpoint, Aerie and Relief audits now default to a cooperative 25%
allowance of one core. One shared budget reaches paid preparation, tactical
orders, failure/retry routes, and resource quotes plus their observed/baseline
campaigns. `--cpu-percent 100` explicitly disables these sleeps. The Pin native
verifier's earned Watch Bell preparation now uses the same allowance; its
existing 30 FPS rendering and playback completion are unchanged.

The resource audit accepts `--theme`, `--difficulty` and `--plan`, permitting a
single observed/baseline case without its default 27-case matrix. No new
framework API or game rules were introduced. Independent code review found no
actionable issue with command order, paid outcomes, budget forwarding or native
cleanup.

## Bounded verification

**56 focused integration tests pass in 7.68 seconds** ([output](focused-tests.txt)).
The five new cases first exposed missing quote, preparation and CLI pacing
interfaces, then passed. They compare real paid states, purchase histories and
complete recorded outcomes with pacing enabled and disabled, using a controlled
clock for sleep assertions. Pin reaches the same earned Brace battle.

Two real CLI runs then completed serially with the default allowance:

| Check | Scope | Wall time | CPU time | CPU / one core |
|---|---|---:|---:|---:|
| Resource breakpoint | One observed/baseline campaign pair; exact output match | 1.84 s | 0.53 s | 28.80% |
| Aerie | Six plans, 362 orders and exact reloads | 3.12 s | 0.87 s | 28.06% |

Measurements include interpreter startup and final report compression, which
can exceed the cooperative allowance. All 35 resource and 85 Aerie source hashes
were checked against the working files. [Measurement receipt](verification.json),
[resource report](resource.json), [resource rows](resource.rows.json.gz) and
[Aerie report](aerie.json.gz) retain the actual results.

No full Relief matrix or additional native window was run for this follow-up.
The cancelled campaign/input matrix and soak stayed stopped. These short checks
establish reduced tool CPU use and unchanged results, not battery life or a
completed Early Access gate. All check processes exited successfully.
