# Screen native evidence, 2026-09-06

All five reports measure clean source **493d16e** after integrating Hero UI
20de559. Every hashed source matched at the end of its run. This evidence commit
retains reports and selected original PNGs; it changes no measured source.
The full suite passed **1,071 tests in 84.20 seconds** at that source.

The actual Pyglet backend received keyboard and mouse events through
`PlayerInput`, `PlayerState` and `ControlOrders`. Paid preparation uses ordinary
campaign purchases, travel, recovery and previous battles; only those earlier
preparation battles use auto. All Screen tactical orders are manual. No army,
resources, experience, position or result is injected.

| Standard seed seven plan | Native inputs | Exact F5/F9 reloads | Successful attempt round | Missing HP | Mana spent |
|---|---:|---:|---:|---:|---:|
| Western Commander | 178 | 7 | 4 | 62 | 0 |
| Western Commander with Heal | 185 | 8 | 5 | 44 | 4 |
| Northern Commander | 208 | 10 | 5 | 43 | 8 |
| Smaller Scout | 193 | 10 | 6 | 55 | 8 |
| Scout loss, paid recovery, western retry | 309 | 23 | 3 | 6 | 0 |

Totals: **1,073 input activations, 58 exact complete-State saves/reloads and 233
tactical orders**. Each report retains its input log, public orders, source
hashes, costs and survivor HP. Both approaches are free. Buildings cost 100 gold;
the Commander recruits cost 98, the Scout recruits 105. The retry spends another
180 gold. These are purchased demonstration parties, not optimal balance plans.

The failed attempt is retained separately inside `failed-retry/journey.json`:
the Scout kills the Sapper, then guards until real hero death at round 13. Three
soldiers die, the army loses 20 gold, and no XP or site reward is granted. A save
preserves the sole surviving Archer at 20 HP. Four ordinary Swordsmen cost 180
gold during recovery; dead soldier IDs do not return. The player cancels both
retry briefings without changing state, selects the other assembly, and manually
routs that Archer in three rounds. The report's zero deaths and six missing HP
refer to this successful retry, not the earlier lost attempt. The 60 gold, two
crystals and Veil Censer reward is granted once, saved, and cannot be farmed by
pressing Explore again.

Inspected retained frames include both 125% briefings and actual deployments,
the enemy Smoke cloud on the western Ranger, the Codex explanation, the northern
Rally forecast and its resulting still-unused movement, the subsequent flank,
the Scout killing the Sapper before its charge, and the cloud-free next phase.
Defeat, reduced-roster retry, victory and the kept reward were also inspected.
The preview and current defender list remain readable at 125%; dead Sapper,
Warden and Guard advice disappears on retry. The briefings return through Codex
and Settings without spending an action or losing campaign state.

The machine was an Apple M4, Mac16,13, 24 GiB RAM, macOS 26.6.2 arm64; Python
3.13.2, Pyglet 2.1.13. Logical/window size was 1280×800, with a 2560×1600 native
framebuffer. `caffeinate -u` woke the display before `caffeinate -d -i` kept it
awake during the runs. A hidden real GPU window rendered the frames; saves lived
in temporary directories and the game was torn down after each run.

Reproduce from the measured source using its installed development dependencies:

```sh
caffeinate -u -t 5
PYTHONPATH=. caffeinate -d -i python tools/verify_eador_screen.py --plan western --output /tmp/screen/western
PYTHONPATH=. caffeinate -d -i python tools/verify_eador_screen.py --plan western-heal --output /tmp/screen/western-heal
PYTHONPATH=. caffeinate -d -i python tools/verify_eador_screen.py --plan northern --output /tmp/screen/northern
PYTHONPATH=. caffeinate -d -i python tools/verify_eador_screen.py --plan scout --output /tmp/screen/scout
PYTHONPATH=. caffeinate -d -i python tools/verify_eador_screen.py --plan failed-retry --output /tmp/screen/failed-retry
python -m pytest -q
```

The five new integration tests invoke this same verifier with the mock backend.
The earlier [model evidence](../shardbound-screen-2026-09-06/README.md) separately
records broader seed/source audits, exact old-world continuations and randomized
robustness checks. Native evidence here covers these five Standard seed-seven
journeys on the recorded Mac. It is not a human playtest, Windows validation,
cross-mode balance approval or completion of a release gate.
