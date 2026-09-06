# Tactical forecast reading

Battle **Text size / F2** opens the shared 100/125 reading setting. Returning from
Apply or Cancel retains the exact selected unit, cursor, hovered hex and queued
order. **T** keeps its existing Retreat action.

The target's name and health, damage/retaliation, healing, Pin movement effect,
Swap consequences, Rally movement/reachable count, Repulse destination, Smoke
duration/charge, shared mana cost and sight explanations now use wrapped Labels.
They use the same live Battle queries as before; no rules or save fields change.
Current terrain sight and saved older open sight retain their own explanations.

The sidebar drops a redundant title and shifts its controls upward to reserve
167 logical pixels above End battle round. The game measures complete forecasts
with `Scene.measure`, then lets a Column place the lines. An oversized future
forecast raises a clear layout error. There is no text shortening, smaller-font
fallback, paging of an immediate consequence, or new framework abstraction.

This increment covers forecast reading. Selected-unit HUD values, objective text,
in-board guidance and the battle log still need separate readable layouts. G10
and the other early-access criteria remain open.

## Verification

```sh
uv run pytest tests/eador/test_forecast_reading.py tests/eador/test_scene.py -q
uv run python tools/verify_eador_forecast.py
```

The regression uses the shipped controls to aim a Wizard's Bolt, Cancel and Apply
the reading setting, then spend that exact order with the shown damage and mana
cost. Existing result-acceptance tests cover the two queued scene pops after the
Battle has already been resolved.

The executable native verifier pauses real paid Control Watch, Sunken Crossing,
Smoke, Repulse and Wizard routes. Its first encountered forecast/status categories
are checked at 100/125 in 1280×720, 1280×800 and 1920×1080 windows. Every reading
pause preserves the complete saved state and aimed order; all labels stay within
the canvas and clear of each other and buttons. The original route adapters check
the actual attacks, healing, displacement, Pin removal, Smoke expiration and exact
save/reloads. The older open-sight fixture also executes its real attack. This is
scripted native verification, not a human playtest.
