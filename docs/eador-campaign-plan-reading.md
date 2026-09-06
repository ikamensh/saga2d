# Reading the current campaign plan

The map's **Campaign / J** view uses the existing shared 100% / 125% Reading
size. Its current objective, numbered province names, completion status,
assault prerequisites, carryover rules, rank limits and recovery funding all
scale and reflow. The existing large campaign title and control text keep
their normal sizes. This covers the current plan only: challenge offers,
retinue selection, departure/recovery transitions and ending scenes retain
their existing layouts.

Each complete objective appears alongside its status and **Locate** button.
Number keys preserve the map marker order; locating a province selects it and
returns to the map without moving, spending an action or changing progress.
**Text size / T** opens the existing Settings row. Apply/Cancel, a restarted
preference and return from Hero preserve the plan and its current targets.

Wrapped Labels and ordinary Columns/Rows determine the layout. The carryover
and rank/recovery columns have measured equal heights. The plan neither
shrinks prose nor removes or pages away objectives. No framework API,
preference key or campaign-save field was added. Its final-stage wording now
correctly says victory completes the three-shard campaign, rather than
promising a further departure.

`tools/verify_eador_campaign_plan.py` prepares real saved states with public
purchases, battles, travel, advancement, capital loss and recovery. Eleven
cases cover all five contracts, all three mode openings, zero/one/two held
Foundries, cleared Border Watch, both earned finales and spent recovery.
The matrix checks all of them at both reading sizes and 1280×720, 1280×800,
1920×1080 windows, using actual keyboard and mouse Locate actions and comparing
full state JSON to prove that reading and locating do not change the campaign.

```sh
uv run python tools/verify_eador_campaign_plan.py --output /tmp/shardbound-campaign-plan-reading
uv run python -m pytest tests/eador/test_campaign_plan_reading.py tests/eador/test_campaign_scene.py -q
```

This is a complete current-plan reading slice toward G10, not a claim that
all campaign screens or the map/battle HUD scale. The matrix verifies layout,
input and saved progress; it does not assess campaign balance.

[Retained native evidence](evidence/shardbound-campaign-plan-reading-2026-09-06/README.md)
contains the source-attributed matrix, six inspected screenshots and exact
full-suite/fuzz outcomes.
