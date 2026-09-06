# Reading the next run

The title screen shares the 100/125 reading preference. T opens its setting;
the ordinary O entry still opens all settings. Hero/world/difficulty headings,
complete descriptions, seed/launch explanation and actual load errors use
measured wrapped Labels. The existing illustration, logo and navigation keep
their ordinary sizes. `Scene.measure` budgets the configuration column before
attachment; all options remain visible together at both sizes.

Settings, resizing, hero/world/difficulty selection and New seed do not create
a campaign or alter saved progress. Enter starts the selected single shard;
L starts the linked Frontier campaign with the selected hero and difficulty.
Failed quickloads preserve those choices and show the full error in the left
illustration area. The regular illustration returns when no error is present.
If a valid long file path makes that diagnostic taller than the available area,
PageUp/PageDown and visible Previous/Next buttons page every character of it.
The game-owned text helper keeps the error intact; world selection still uses
Left/Right. Reflow keeps the currently read position visible.
Saves still owns explicit backup recovery. No launch rules or save format change.

```bash
uv run python tools/verify_eador_title.py --backend mock
uv run python tools/verify_eador_title.py --backend pyglet
```

The public-input verifier covers every hero/world/difficulty combination at
both reading sizes in three native windows (216 layouts). It exercises
Settings Apply/Cancel/restart, keyboard and mouse selection, a changed seed,
both launch modes, invalid-version and real directory quickload failures,
explicit backup recovery, and a previous saved run whose rules differ from
the new title choices. The read-only matrix preserves every campaign file.
Native captures require visual inspection before retaining an evidence claim.
