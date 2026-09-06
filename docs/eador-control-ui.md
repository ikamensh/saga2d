# Finite control orders through player input

The v11 model checkpoint `c8f9fa4` adds Sapper Smoke, Rune Adept Repulse,
Skyrider flight and Militia Rally, plus forest/smoke sight queries. Original
troop silhouettes are `3fd1212`; the paid combined formation and manual Watch
route are `7d42eba`. These increments raise the roster to ten recruit roles
and eight distinct combat abilities: Bolt, Heal, Brace, Pin, Swap, Smoke,
Repulse and Rally. Ordinary movement, Guard and evacuation do not inflate that
count. Twelve relics, broader viable builds and whole-campaign balance remain
unfinished release work.

The UI selects the action from the unit's saved capabilities. Q Rallies, D
places Smoke on a hex and R Repulses an enemy. F cycles legal targets; Enter
commits and Esc cancels without spending. Rally highlights the target's actual
post-clear reachable set. Repulse marks its exact empty landing. Smoke shows
legal hexes, a persistent cloud badge and its finite charge. Spending a charge
or action disables its button and shortcut with a contextual explanation.
Sight failures explain why a ranged order cannot reach the hovered unit.

Recruitment retains pages of five, displays both currencies, and checks both
before enabling a purchase. Focused valid-save fixtures verify that gold alone
cannot activate a crystal-funded recruit and that a funded purchase deducts
both amounts exactly. They isolate affordability; the journeys below earn
their buildings, resources and armies through actual campaign controls.

## Executable and native evidence

`tools/verify_eador_control.py` runs the same ordinary mouse/keyboard journeys
against mock or native Pyglet input. The completed macOS native checks use the
shipping 1280×800 logical canvas:

| Journey | Input activations | Exact save/reloads | Verified result |
|---|---:|---:|---|
| Paid Sapper | 24 | 1 | Hex targeting/cancel, saved Smoke, expiry without recharging |
| Real Pinned carrier + Militia | 106 | 4 | Actual enemy Pin, free preview/cancel, exact restored reach and unchanged carrier order flags |
| Paid Rune Adept | 26 | 1 | Exact landing, no target HP/order changes, spent charge retained |
| Paid Sapper/Adept/Skyrider Watch | 158 | 8 | Round-three hold, all seven allies alive, enemy Archer alive, once-only reward |

The last journey buys the army, enters the briefing and uses Smoke on the
approaching Archer's lane, Repulse from the seal, and flight across the occupied
formation. The helper's paired model route substitutes Guard for Smoke and
still wins with two fewer retained HP. This shows a modest concrete benefit;
it does not establish optimal tactics or a universally better purchase.

Native captures were inspected for recruitment, each target preview, spent
charges, flight reach, crowded formations and the final result. Inspection
caught Smoke instructions running into End Round; the explanation now fits
two lines. A second review caught a Skyrider wing and Pikeman spear crossing
adjacent HP labels. Status/HP drawing now uses `screen_layer(1)`, with floating
feedback on layer 2, above ordinary pieces. The corrected Watch formation was
rendered and inspected. No framework modification was needed.

The integrated source passes **843 full tests**, including the merged Vault
regressions. Both ordinary fuzz drivers passed after the control changes:
Tribes ran 60 AI games and 20 random-input runs; Shardbound ran twelve linked
model and twelve scene journeys (2,227 inputs, 1,852 randomized). The verifier
records source hashes, revision, dirty paths, runtime/platform and exact inputs,
and refuses to report success if source changes during its run.

```sh
uv run python tools/verify_eador_control.py --scenario smoke --output /tmp/control-smoke
uv run python tools/verify_eador_control.py --scenario rally --output /tmp/control-rally
uv run python tools/verify_eador_control.py --scenario repulse --output /tmp/control-repulse
uv run python tools/verify_eador_control.py --scenario watch --output /tmp/control-watch
uv run python -m pytest tests/eador/test_roster_scene.py -q
```

The game retains the small action-name/button mapping and its visual forecasts.
Saga2D supplies existing controls, geometry, save files and screen composition;
it acquires no Smoke, army, terrain-sight or adventure policy. Older active
campaign fixtures retain their recorded capability tuples and open-sight mode.
Ability-aware automatic play and broader v11 balance evidence are a separate
model tranche; historical v9 economy and older package/soak reports are not
current-candidate acceptance.
