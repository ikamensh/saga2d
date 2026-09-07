# More icon controls — 2026-09-07

Product commit `660ce5e` replaces ten recurring map/battle action labels with
existing icons and adds level/health icons to each army miniature. Travel keeps
its changing verb; Brace, objectives, spell costs and caster ownership remain
explicit. This pass uses existing Saga2D components and prebuilt game artwork.

The [native receipt](native.json.gz) covers a fresh linked seed-7 Wizard opening:
199 input events (including hover), 170 unchanged-state observations, 87 tooltip
observations and three exact reloads. Build, Recruit, Rival and Campaign are
opened by icon and shortcut at both reading sizes. End turn, exploration,
Archer/hero movement, an attack and Guard are compared with public model
commands. Bolt icon/key aiming reaches the same targets; disabled Heal/Pin
cannot issue an order. No automatic battle policy runs.

The final native run took 24.675 seconds wall and 6.215 seconds CPU. It requested
25% cooperative CPU allowance, used the shared 30 FPS native input cap, and
closed the game in `finally`. Its source hashes still match the committed
runtime and verifier. Audio was silent. This is source-mode presentation/input
verification, not a rebuilt distributable or a human first-run review.

Root inspected the retained [100% map](campaign-icons.png),
[125% map](campaign-reading-125.png), [battle](battle-icons.png),
[Heal tooltip](disabled-heal-tooltip.png) and [reloaded battle](battle-reloaded.png).
Symbols, troop values, spell costs and keycaps remain readable; tooltips fit the
viewport. A separate [Brace frame](brace-125.png) uses a fresh Commander with
a legally purchased Barracks/Pikeman and Shrine encounter, then native selection
at 125%. Its word and icon remain readable. The earlier standalone map/battle
125% previews also received independent agent visual review with no blockers.

Regression results: 21 existing scene, map-reading and tactical-layout tests
passed in 20.41 seconds; the expanded icon journey passed in 2.93 seconds.
The former run excluded `earned_and_historical`, `victory` and `native_control`
matches; it used cooperative 25% pacing between tests. The icon journey paces
its own commands. These are 22 focused tests, not a full suite.

The [bounded random-input receipt](fuzz.json.gz) records two scene runs with
182 inputs and 177 state checks in 5.9 seconds, with no failure. All jobs ran
serially. No large matrix or soak was restarted.

Reproduce the focused icon check and native journey:

```sh
.venv/bin/python -m pytest tests/eador/test_icon_controls.py -q
.venv/bin/python tools/verify_eador_icons.py --output /tmp/shardbound-more-icons
.venv/bin/python tools/fuzz_eador.py --campaigns 0 --scenes 2 --steps 40
```

The retained media and raw receipts are authenticated by [sha256.json](sha256.json).
