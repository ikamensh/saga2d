# CPU and frame pacing — 2026-09-06

The user's report of simultaneous Python processes consuming whole CPU cores
changed the work order. Heavy jobs were stopped. The current source adds a small
framework frame limiter and separate test-tool allowances.

`Game.run(scene, fps=60)` sleeps between frames and caps inactive/hidden windows
at 15 FPS. Explicit `tick(dt)` stays unpaced. Native `PlayerInput` caps every tick
at 30 FPS, including its 110-frame screenshot settling loop. Both model fuzz CLIs
default to a cooperative 25% allowance of one core; `--cpu-percent 100` is an
explicit stress override. Work is yielded at about 50 ms CPU checkpoints; one
atomic command can overrun that allowance. Heavy jobs should run serially.

## Observed native CPU reduction

One hidden Pyglet window rendered the actual seed-7 Shardbound map on macOS
26.6.2 / Apple M4, at 1280×800 logical / 2560×1600 physical pixels. Synthetic
native activation/deactivation/show/hide callbacks exercised each mode for
roughly two seconds, including a keyboard input per phase and exact elapsed
game time. CPU percent is process CPU time divided by elapsed wall time,
expressed as a fraction of one core. Screenshots and warmup are included.

| Native mode | Before: FPS / CPU | After: FPS / CPU |
|---|---:|---:|
| Active | 165.2 / 90.1% | 53.8 / 38.8% |
| Unfocused | 174.0 / 91.0% | 15.1 / 23.9% |
| Hidden, even if activated | 178.9 / 89.6% | 14.7 / 27.8% |
| Shown and focused again | 176.9 / 89.0% | 53.7 / 35.6% |

The before report names archived source `219bcf9`. Final after/example/input checks
use clean source `069f79c` and retain source hashes. The source hashes remained
unchanged during the complete frame probe. These short runs prove bounded frame
work and a measured CPU reduction; they do not establish battery lifetime,
visible-window VSync behavior on every OS, or release performance gates.

The independent moving-circle example also passes active/inactive/restored
pacing and four native keyboard commands. Real native mouse/key input starts a
Shardbound battle, Guards and exactly reloads it. Its 110 settling ticks take
3.85 seconds at 24.0% CPU, preserve explicit dt=1/60 and leave the complete saved
State unchanged. All these windows close. The source for that bounded input
probe is retained here; it uses a fresh test directory under /tmp.

Native display regression passes nine resize/fullscreen/startup/restoration
states, including world and UI hit tests and letterbox pixels. Four retained
screenshots were opened and inspected: restored map, native battle, independent
circle and fullscreen-start restoration. No rendering defect was observed.

Before the fix, the minimal public Game.run regression produced 81,030 frames
in 0.2 seconds. After the fix, 311 framework/Tribes/Shardbound scene integration
tests pass, including nine pacing regressions. Fourteen focused tool tests pass.
The combined source also passes 12 linked model campaigns, 12 scene runs and
3,004 random inputs (327 playback inputs verified inert), with unchanged hashes
and the default 25% CPU allowance. Tribes passes 60 AI games and 20 random-input
runs under the same default. One live Tribes sample after 142 seconds showed
24.5% CPU; the allowance remains cooperative rather than an OS quota.
Independent read-only review found no blocker in the cap, initial native event
ordering, cleanup, exact timestep behavior or framework/game split.

## Cancelled long-run evidence

The earlier `219bcf9` soak was deliberately interrupted in response to the user's
CPU/battery concern: **583.25 seconds, 31,064 frames and 14 opening journeys**,
exit 130, status `cancelled`. The window, temporary saves and awake helper cleaned
up, and source remained unchanged. Its report is retained without claiming the
two-hour gate. The 1,000-campaign/100,000-input job also ended with exit 143 before
a final report; it is not counted as a successful stress run. Neither job was
restarted. The earlier packaged ZIP remains unchanged and predates these caps.
