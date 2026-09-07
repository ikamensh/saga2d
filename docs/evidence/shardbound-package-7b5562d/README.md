# Current Mac development build — 2026-09-07

Clean source **7b5562d1b76b5d16863d121efc9fff5288942f2a** is preserved under
`dist/shardbound-checkpoints/7b5562d1b76b/` in the main workspace, with
`Shardbound.app`, `Shardbound-macos-arm64.zip` and `build-manifest.json`.
This includes the painted environment and hero portraits, illustrated terrain,
role miniatures, icon toolbars/statistics, richer sound, compact battle controls,
varied saved adventure locations, and the existing shared-realm implementation.
The two latest player-facing fixes clarify ready evacuation and singular foe text.
**This is a development checkpoint; all G01–G19 remain incomplete.**

The ZIP is **49,259,991 bytes**, SHA-256
`4bf1e0e8ba8e77698e91621a4baee6931d1740263e1807b75836413f29ef559b`.
It was built on macOS arm64 with locked CPython 3.13.2, PyInstaller 6.22.2 and
hooks-contrib 2026.7. The [full manifest](build-manifest.json.gz) records all
runtime versions, 235 snapshotted input hashes, 116 package-data files and the
240-entry installed inventory. The [retention receipt](retention.json) verifies
207 corresponding current source/asset/recipe files and exact inventories of
both the second extraction and the retained application.

## Source checks and build

The separate [ordinary validation record](../shardbound-candidate-validation/README.md)
reconciles **1,542 current test cases** across seven staged tranches and two
display tests. The 110 game/framework/cross-game Python files match throughout;
test-route repairs and removal of four superseded prototype tests are explicit.
All six initial failures remain recorded. **159 expensive cases were deferred**;
the two packaged-campaign mock cases among them passed separately. This was not
one full-suite invocation on the final commit. A separate small model audit
completed **24/24 linked journeys**, 16 direct and eight recovered, on seed 0
Standard across four heroes and branch choices. It uses the existing economic
policy and explicit autoplay, not independent manual strategies.

The exact build command, run as the sole expensive local job, was:

```sh
/usr/bin/caffeinate -du -t 1200 /Users/ikamen/.local/bin/uv run --locked --isolated --python 3.13.2 --with-requirements packaging/requirements.txt python tools/build_eador.py --check-campaign --forecast-save /tmp/shardbound-candidate-control-forecast.json
```

The forecast input is the unchanged `commands[80].before` State in
`docs/evidence/shardbound-army-plans-cd351a9/control.json.gz`. The external plain
file's SHA-256 is `4eb6076224527ed7a1240f030e8cc0c4f4902af7814eb58813b86277375b72e1`.
The builder copied it outside the archive and checked its exact bytes. The
[build log](build.log) and all installed-process receipts are retained here.

## Actual extracted application

The builder extracted its ZIP outside the repository, removed Python environment
overrides and used an OS-only executable search path. The frozen smoke passed
native input, exact campaign/battle saves, Guard restoration, About identity,
guide return, Codex/rival inspection, settings apply/cancel/restart, all **18
installed WAVs** and live audio mix/cleanup. The earned 125% casualty forecast
kept State unchanged and reloaded it exactly. Playback used the native silent
driver; this is asset/runtime validation, not an artistic listening review.

Two full seed-7 Commander Standard campaigns then used the same extracted app:

| Journey | App processes | Native inputs | UI save/reloads | Exact process joins | Completed shard turns |
|---|---:|---:|---:|---:|---|
| Direct, Rootward → Gate | 4 | 467 | 8 | 3 | 13 / 13 / 11 |
| Lost-capital recovery, Rootward → Gate | 5 | 509 | 9 | 4 | 13 / 33 / 11 |

All nine process IDs are distinct. Each departure, actual recovery decision and
completed ending restores the entire previous checkpoint; both final processes
return to title. Reading size stays at 125%. Every changing order uses the
existing native input proxy, including visible automatic rounds and Finish
playback. These are campaign/save regressions, not human or manual-tactics runs.
Full checkpoints, events, settings, saves and frames are under `campaign/`.

The phase bodies total **148.560 seconds wall / 39.536 seconds CPU**, about
**26.61% of one core**. Their requested allowance is 25%, with native input capped
at 30 FPS. These timings exclude process imports/startup, report writing and
cleanup; short phases may exceed the allowance. PyInstaller itself is uncapped.
Normal game caps remain 60 FPS active and 15 FPS inactive. All expensive jobs
ran serially; no cancelled matrix or soak was restarted.

## Visual review, launch and limits

An independent internal agent inspected all ten smoke images and all 25 unique
images represented by the 43 campaign PNGs. The [visual review](visual-review.json.gz)
maps every filename to its exact hash and, for duplicates, the viewed
representative. It found no blocking clipping, overlap, missing icons or visible
funding/readiness contradiction. Root also viewed the title, map, battle,
casualty warning, capital-loss selection and completed ending. These are the
actual packaged frames, not source-mode substitutes or mock renders.

A [second extraction](second-extraction.json.gz) passes local ad-hoc signature
verification and all 23 bundle symlinks resolve. The retained app was copied
from that extraction, matches the complete build inventory and passes the same
signature check. No signing identity, notarization or distribution approval was
used. LaunchServices (`open -W -n … --smoke-image …`) also passed: the frozen app
ran with working directory `/` and loaded its own bundled assets. Eight of its
nine frames are byte-identical to already reviewed smoke frames; root separately
viewed the About page with its different temporary data path.

The [ordinary launch attempt](normal-launch.json.gz) started with its own
`--data-dir` profile. Computer use reported a locked Mac before observing the
game. The user was asked to unlock it; no controls or co-op journey were exercised.
The single owned process was terminated and its launcher exited. Normal
interactive quit/relaunch, co-op connectivity in this artifact, Windows,
clean-account testing, human playtests/listening and current sustained acceptance
remain unverified. The manual-only [Windows workflow and handoff](../../windows-shardbound.md)
are prepared locally; no push, dispatch, upload or publication occurred.

`originals.json` maps 99 byte-preserved originals to their retained files;
JSON is losslessly compressed. `SHA256SUMS` authenticates this record. The
retention script is kept as `retain-candidate.py.txt`. Later evidence-only
commits do not change the packaged application's source or assets.
