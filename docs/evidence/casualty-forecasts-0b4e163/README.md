# Visible casualty forecasts and earned orders — 6 September 2026

Source `0b4e163` makes lethal ordinary attacks and Pin explicit in the existing
forecast. It names a falling friendly unit or defeated enemy, explains hero loss,
and suggests switching units only when another ally has an unspent order.
A lethal Pin no longer promises movement on the defeated target's next turn.
The Field Guide explains ordinary retaliation and reading Deal / Take.

The exact model previews supply the numbers. This is a game-owned presentation
change using existing Saga2D labels and measured layout; combat, saves and the
framework interface are unchanged. The preserved `a6851fb` Mac archive predates
this UI change. No release-candidate or first-run acceptance is claimed.

## Tests and native evidence

**29 focused integration tests pass in 4.36 seconds**, covering the earned Adept
warning, safe selection without changing the save, all-other-units-spent hint,
earned lethal attack/Pin, reading controls, existing battle HUD and Field Guide:

```sh
uv run --extra dev python -m pytest tests/eador/test_attack_warnings.py tests/eador/test_forecast_reading.py tests/eador/test_guidance_reading.py tests/eador/test_scene.py tests/eador/test_battle_hud_reading.py -q
caffeinate -diu uv run --extra dev python tools/verify_eador_army_decisions.py --backend pyglet --output /tmp/shardbound-army-decisions-native
caffeinate -diu uv run --extra dev python docs/evidence/casualty-forecasts-0b4e163/pin_probe.py
```

The first native check loads the unmodified Control/Mobile paid-decision inputs
and executes both their manual and autoplay branches through ordinary controls.
All **18 commands** match their complete expected saved states, through actual
rewards and affordable recruitment. There are **24 forecast layouts, 144 inputs
and four exact UI save/reloads**. The additional earned Archer/Goblin Pin check
covers **six layouts, 26 inputs and one exact reload**, then confirms the target
actually dies. These are three window sizes × 100/125 reading size. Native input
is paced at 30 FPS, and jobs ran serially; all windows and task awake helpers ended.

The opened screenshots show the prior numeric-only Adept forecast, new Adept
and Warden casualty lines, lethal Pin and the revised 125% Field Guide. Text fits
without clipping. The main native report was generated on base `f50b077` with
the change still uncommitted; all 69 recorded source hashes match committed
`0b4e163` (see `source-verification.json`). The Pin probe fingerprints its own
retained script as well as the game/framework and input/layout helpers.

These continuations preserve the measured tradeoffs: protecting the Adept avoids
65 gold/2 crystals of replacement; withdrawing the Warden saves 35 replacement
gold while transferring the casualty to Militia and leaving four less living HP.
There is no native preparation or complete manual-campaign credit. G04/G08/G09
remain incomplete.

## Independent first-run attempt

A fresh agent was instructed to use visible UI only, with no source or guide
reading, against `/tmp/shardbound-playtest-a6851fb/Shardbound.app`. Its first
`cua.getApp` returned `Computer Use server error -10005: timeoutReached` after
5.6 seconds, with no screenshot or accessibility state. It did not explicitly
launch the app or make gameplay observations. The process list afterward showed
no Shardbound instance. Unlike the previous locked-Mac attempt, this error does
not establish that the Mac was locked. No independent or human playtest credit
is taken; native scripted checks above are separate evidence.
