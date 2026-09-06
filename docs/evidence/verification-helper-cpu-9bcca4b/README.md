# Verification preparation and backend cleanup — 2026-09-06

Source **9bcca4b4a57255c6d911f313fface4c2fce5ad50** extends the existing CPU
allowance to three older development tools. Save and result verification now
share one budget through earned campaign/battle preparation. The Relief
prototype shares it through paid preparation, orders, static searches and world
searches. Defaults target 25% of one core; explicit `--cpu-percent 100` disables
sleeping. Small `--trials` and `--world-seeds` selectors preserve the existing
1,000 defaults while allowing bounded development checks.

Both verifiers now close their initial and restarted rendering backends in
`finally` blocks, including when scene teardown raises. Their old cleanup only
removed scenes. The native shifted save-slot input also uses the existing 30 FPS
helper. No game rules, rendering layout or Saga2D API changed.

**Nine focused integration checks pass in 5.24 seconds.** They exercise actual
saved phases, battle results, detached orders, CLI searches and verifier restart
journeys. Controlled clocks isolate yielding without changing game decisions;
paced and unrestricted results remain equal. The search and world loops each
have an independent yielding assertion. Both real mock-backend journeys first
failed because their initial and restarted backends remained running, then
passed after cleanup was added. The test log includes the existing two native
frame-timing checks.

One real CLI check ran with `--trials 4 --world-seeds 2` at the default allowance:
14 detached authored plans, four automatic branches, 48 search trials and two
world seeds per theme. It completed in **1.11 seconds wall / 0.47 seconds CPU**,
about **42% of one core including startup and report writing**. That short-run
ratio is not a 25% operating-system ceiling. The allowance sleeps cooperatively
between work blocks; atomic commands and fixed startup costs can exceed it.

The report was produced on working source with HEAD `16a52f9`; all 86 recorded
source hashes were subsequently verified against committed `9bcca4b`.
`verification.json` retains that identity, scope and timing; raw reports and
logs are unchanged. All jobs ran serially and ended. No native window, large
matrix, full-suite repeat, soak, battery-life or release-acceptance claim is made.

The game's previously verified caps remain 60 FPS active / 15 inactive, and
native test input remains capped at 30 FPS. Game/framework bytes still match
the [autoplay checkpoint d643410](../autoplay-survival-d643410/README.md).
