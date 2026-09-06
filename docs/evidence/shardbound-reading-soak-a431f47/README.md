# Short native reading/performance check

Frozen game/framework source **a431f47**, Apple M4 (Mac16,13), native Pyglet,
1280×800 logical canvas / HiDPI window, silent audio driver. The harness calls
the shipped `create_game` configuration and alternates 100/125 reading through
real Settings controls. Every battle also opens F2, changes the preview and
cancels, preserving the exact saved state and aim.

The completed run lasted **180.08 seconds**, **10,246 frames**, **54 repeated
opening journeys**, across eight seeds and all four hero classes. It completed
109 battle reloads/settings cancellations, 108 pending-choice reloads and 54
save-browser round trips. [Complete report](report.json) and [frozen manifest](manifest.json)
retain source/module hashes, hardware, inputs and cleanup.

`Game.tick` p50 **6.92 ms**, p95 **20.32 ms**, p99 **35.90 ms**, maximum **77.41 ms**.
These measure input processing/update/draw, excluding pacing, driver setup and
screenshots. Other development/check processes were active; this is a bounded
responsiveness check, not an isolated benchmark or a candidate-wide performance
claim. [Raw timing samples](latency-ms.f64) and [minute samples](minutes.jsonl)
are retained.

The three sampled minute RSS values fluctuate, with sampled peak **311.2 MiB**.
There are too few disjoint observation windows to infer long-term memory growth;
the report explicitly marks its comparison windows as overlapping. Its reported
zero difference between those identical windows is **not leak evidence**.

All imports came from the frozen snapshot, which stayed unchanged. Window,
caffeinate helper and temporary saves were cleaned up. Both retained screenshots
were opened and inspected. Earlier short probes exposed two removed imports in
the harness's first-minute check; restoring them precedes this completed run.
Those harness failures were not game defects.

```sh
uv run python tools/soak_eador.py --seconds 180 --input-interval .05 --revision a431f47 --output /tmp/shardbound-reading-soak
```

This is neither the required two-hour soak, a full linked campaign, a human
playtest, nor the newer objective/HUD implementation. G15 remains incomplete.
