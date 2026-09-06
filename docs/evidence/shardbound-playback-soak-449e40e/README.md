# Paced playback integration probe

Source **449e40e42f88948c1016b6b1a02348e55de49196**, with game/framework
last changed at **0319186**, passed a **90.150-second** real Pyglet probe on
macOS 26.6.2, Apple M4 / Mac16,13. This is a preliminary integration check,
not the two-hour candidate soak, a complete campaign or a human playtest.

The soak driver now waits for ordinary rendered playback to finish before
issuing another battle order. It verifies that full authoritative State stays
unchanged during those waits. A public-input regression first reproduced the
old driver counting ignored auto-round keys as orders; the corrected generator
completes four hero openings at both reading sizes. All nine modal/soak tests
passed before this probe.

The native run completed two full journeys and started a third, with 4,891
frames, 14 naturally watched playbacks, five settled battles, six exact battle
reloads and two save-browser round trips. There were 157 native activations
(137 keys, 15 coordinate clicks, five button clicks); the 1,313 wait steps and
three prepared title restarts are counted separately. The three retained
screenshots were opened and inspected.

Game.tick p50/p95/p99 were 13.35/20.71/55.39 ms (maximum 172.66 ms). Other
verification jobs were running concurrently; this is not an isolated benchmark.
The three RSS samples are insufficient to establish a memory trend. Source
hashes remained unchanged, every game module came from the frozen snapshot,
and window, temporary saves and awake-helper cleanup all passed.

The initial attempt found an asleep display and rendered zero frames; its
failure report is retained separately. The successful probe followed a display
wake and uses the same source. Neither report establishes CUA desktop access
or a first-run walkthrough.

```sh
uv run python tools/soak_eador.py --revision 449e40e \
  --seconds 90 --input-interval .05 --output /tmp/playback-probe-new
```

`manifest.json` identifies each source input; `report.json` retains counters,
hardware, timing, memory and cleanup. `latency-ms.f64` contains every measured
tick, in the byte order recorded in the report. Later playback/content changes
need their own candidate verification.
