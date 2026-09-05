# Real-backend soak

`tools/soak_eador.py` produces reproducible sustained-rendering evidence for
G15 in [the release criteria](early-access-criteria.md). A successful short
run validates the harness. Only a completed run with at least 7,200 measured
seconds satisfies the two-hour duration requirement; G15 also requires the
campaign/input matrix, acceptable latency, and an explained memory trend.

## Run and monitor

Run on an awake macOS desktop with the project dependencies installed:

```sh
# Fast integration check; 60 Hz rendering, accelerated inputs.
uv run python tools/soak_eador.py --revision 31a2c88 --seconds 65 --input-interval .05 --output dist/soak/check

# Two hours; one logical input every 250 ms.
uv run python tools/soak_eador.py --revision 31a2c88 --seconds 7200 --output dist/soak/baseline-31a2c88
```

Output directories must be new, so earlier evidence cannot be overwritten.
The default revision is `HEAD`. `git archive` copies the committed `eador/`
and `saga2d/` packages and dependency manifests. The current harness is also
copied and hashed. The worker starts from that snapshot before importing
either package: later working-tree changes cannot enter the running soak.
`manifest.json` identifies the game revision, every source SHA-256, Python
executable/version, and installed dependency versions. The final report also
checks the snapshot hashes and the paths of all loaded game modules.

The process prints a line every minute. `progress.json` is atomically
replaced at startup, each minute, and termination. It contains the PID,
elapsed time, frame counts, scene mix, action counts, recent actions, and all
RSS samples. `minutes.jsonl` retains each emitted sampling record.

```sh
cat dist/soak/baseline-31a2c88/progress.json
```

Stop with Ctrl-C in its terminal or send SIGTERM to the PID in that progress
file. Both produce a cancelled `report.json`, close the window, remove the
temporary save directory, and stop this process's `caffeinate` child. The
handler is installed after Pyglet creates the window because Cocoa's event
loop installs its own SIGTERM handler during initialization. SIGKILL cannot
run Python cleanup; an old `running` progress file without a live PID is an
interrupted run, not a pass.

## Workload

One hidden Pyglet window and one `Game` remain alive throughout the run.
Rendering and updates continue between inputs. Repeated journeys cycle
through seeds 7–14 and the four hero classes in eight fixed pairings:

1. Open the title, choose a hero, build a Barracks, recruit a Swordsman.
2. Explore the home site, save and reload an unfinished battle, select and
   move the hero with the mouse, attack when a legal target is available,
   and finish through real `A` auto-round keyboard input.
3. Save and reload pending reward choices, retain the relic, equip it, and
   rest through campaign input.
4. Invade the adjacent province and repeat tactical/save/result flows;
   choose a hero discipline when earned.
5. Save and load Manual 2 through the save browser. Open the guide, use
   Save & title, write Manual 3, and reach the title again.

The next journey uses `Game.clear_and_push(TitleScene(seed))` to select its
fixture seed; that reset is counted separately from real input. All other
actions use Pyglet window keyboard and mouse events, including physical
coordinate conversion and button bounds. Input press/release pairs enter
the same event path as player input. Save files are real files in a fresh
temporary directory and remain there across journeys. A battle that fails
to finish/win within its bounded driver, a wrong scene, or a changed saved
state fails the run with its recent action history.

This workload stresses scene replacement, overlapping UI, retained render
resources, changing text, tactical updates, repeated construction and
recruitment, choices, equipment, autosaves, and manual saves/loads. It does
not cover complete campaigns, all 32 seed/class combinations, every spell,
damaged-file recovery, audio, visible-window interaction, or human choices.
Those require separate evidence. Optional manual attack counts must be read
from the report; automatic rounds also execute normal combat rules.

## Timing and memory interpretation

- The measured duration uses `time.monotonic()` after window setup and
  before cleanup. There is a 60 Hz cap with no catch-up bursts. Each frame
  updates with a fixed `1/60` game delta; the report's duration is actual
  elapsed wall time, independent of the number of frames.
- `latency` contains p50/p95/p99 and maximum elapsed `Game.tick()` time.
  This includes queued input dispatch, updates, synchronous saves invoked
  by input, drawing, and the backend's frame presentation. It excludes
  pacing sleeps, driver setup/assertions, screenshot capture, and report
  writing. Report the entire measured distribution; do not discard slow
  input or save frames to improve the number. G15 targets p95 below 33 ms.
- Every tick duration is streamed as a native-endian float64 millisecond
  value to `latency-ms.f64`; endianness is recorded. The live measurement
  buffer contains at most one minute, so a growing latency list does not
  masquerade as a game memory leak. Final quantiles are calculated after
  the run and after the memory samples are complete.
- `ps` samples current process RSS at startup, each minute, and completion.
  `memory` compares the first five post-startup samples with the last five,
  includes their timestamps, and reports byte/percentage growth. Short
  checks have overlapping windows and explicitly report that limitation.
  A two-hour report should be assessed from the whole minute series:
  startup caches, periodic collection, and a steadily rising baseline are
  different patterns. No arbitrary threshold automatically declares a
  memory trend acceptable.
- Both sampled peak RSS and macOS `ru_maxrss` are recorded. The latter is
  captured before allocating the final quantile array. Measurements cover
  the harness process and driver overhead along with the game; graphics
  memory retained by the OS/driver is not separately measured.
- Hardware model, CPU, RAM, OS, architecture, GL vendor/renderer/version,
  logical resolution and actual window pixel dimensions accompany the
  report. Concurrent work on the host can affect the timings.

Screenshots are saved on the first rendered frame of every scene type,
every ten minutes, and completion. Open and inspect the milestone images
before accepting the report. An assertion or exception produces a failed
report and a nonzero process result. A completed duration alone is not a
release-readiness claim, and the evidence applies only to the recorded
snapshot.

## Harness checks performed

On Apple M4 / Mac16,13 / 24 GiB RAM, macOS 26.6.2, Python 3.13.2,
Pyglet 2.1.13, at 1280×800 logical / 2560×1600 physical pixels:

- A 30.07-second real run completed 10 journeys and 1,736 frames across all
  nine scene types. Tick p50/p95/p99 was 5.06/14.03/23.94 ms. Battle, choice,
  relic and save-browser captures were inspected.
- A 65.07-second run completed 22 journeys and 3,806 frames. It produced a
  minute RSS sample and a final sample, retained unchanged source hashes,
  and verified that all game modules loaded from its source snapshot.
- A cancellation check exposed Pyglet's replacement SIGTERM handler; the
  harness now installs its handler after window creation. The corrected
  check stopped at 74.7 seconds with exit 130 and a cancelled final report;
  the worker and its caffeinate child exited. Cleanup outcomes are also
  recorded in subsequent reports.

These checks validate the harness; they are not the two-hour G15 result.
