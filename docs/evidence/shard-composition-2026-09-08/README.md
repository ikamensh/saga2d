# Shard composition: three critique and improvement cycles

Final code checkpoint: `87cd67af08ca711f25471c7eaa9a19546a6d0e2f`.
The retained run receipts' recorded source files match that commit exactly.

1. **Names obscured terrain.** The baseline Amber Fields hover was a tall,
   two-line block. Commit `5cbd1a9` uses a complete single-line caption along the
   lower province edge. Hover remains transparent to clicks; Tab still reveals
   the selected province in the inspector. Permanent names remain limited to
   capitals and the announced rival target.
2. **Branding and summaries squeezed the board.** Commit `1b0cb57` condenses the
   heading and treasury/hero summary. The full yield explanation sits beside
   province income; current location and progression sit above the army.
   Resources, warnings, objectives and commands retain their actual values.
3. **The island touched the army divider and had false internal cliffs.**
   Commit `87cd67a` reserves space below the shoreline and gives the perimeter
   a shallow stone rim. Explicit terrain depth prevents texture batching from
   painting rear sidewalls over nearer provinces. Markers remain above all
   terrain. A hero symbol clarifies whose level and experience are displayed.

Both solo and development concurrent maps share the frame. These are game
presentation changes using existing Saga2D layers, geometry and layout;
no new framework API, game rules or assets were needed.

## Verification

- **21 integration tests passed in 12.20 seconds.** The selection and measured
  wall/CPU times are in `summary.json`. Coverage includes mouse/keyboard names,
  terrain/marker ordering across all three themes, exact selected orders,
  reading settings, save errors, paid historical campaign states and real
  loopback concurrent scenes. This is a focused selection, not the full suite.
- **Solo native check:** seven states, 133 selections, 455 input activations,
  four exact public orders and 12 captures. Includes 100/125% text, long names,
  full army, exhausted actions, encirclement and the longest earned contract.
  Wall 41.017 s / CPU 10.346 s; window closed, inspected sources unchanged.
- **Concurrent native check:** seat 1 with a real socket peer, purchase,
  independent PvE, invalid-order refusal, Help, retreat, shared-day Ready and
  large text. Wall 13.726 s / CPU 3.470 s; closed successfully. Its receipt
  records all 13 captured stages; only the two map frames are retained here.
  Seat 0 was separately checked during pass 2.

Native checks ran sequentially with 30 FPS input pacing and a cooperative 25%
CPU allowance. Historical preparation in the solo verifier includes disclosed
public-command autoplay; this is directed verification, not human playtesting.
Audio was silent for these visual runs.

All 14 retained final PNGs were opened and reviewed: nine by the parent and
five by an independent agent. No blocking overlap or clipping was found.
Four earlier screenshots preserve the critique sequence. An independent
source review found no concrete correctness blocker.

Reproduce, one job at a time, with fresh output directories:

```sh
.venv/bin/python tools/verify_eador_shard_look.py --output /tmp/new-shard-review --cpu-percent 25
.venv/bin/python tools/verify_eador_concurrent_ui.py /tmp/new-shard-peer-review --seat 1
```

`manifest.json` records hashes of all retained files. Package rebuilding and
the remaining multiplayer feature work are outside this visual checkpoint.
