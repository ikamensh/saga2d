# Phase restart visual review

Read-only review of completed native output at `/tmp/shardbound-phase-restarts-native`; no game, test, capture or model job was run for this review.

## Viewed frames

- `campaign-restarted.png`: fresh Frontier7 Stage1, Turn1, 100 gold/4 crystals, three troops and the Duskspire objective are readable. Toolbar icons, province names and army health do not overlap.
- `battle-restarted.png`: actual opening Shrine fight, Round1, four allies/two foes, Commander36HP. Objective, six unit health plaques, selected-unit metrics, disabled spell icons and footer controls fit. No clipping or health occlusion found.
- `departure-restarted.png`: Stage1 departure offers show complete Rootward and Foundries objectives, their numbered choices and carryover consequences. This agrees with the loaded CampaignScene and departure phase.
- `completed-restarted.png`: all three completed shard records and the Return to title control fit; Stage3, Level5 and no recovery needed agree with the retained ending.
- `capital-loss-restarted.png`: Westwatch has fallen, Turn10/Level4 and the Saves/Codex/New shard controls are legible. The visible loss agrees with the standalone defeat ResultScene, rather than a linked recovery screen.
- `stage-1-earned-retinue.png`: both selected Swordsmen and Moonstone/Iron Crown are clearly marked; 2/2 selections, the focused Iron Crown outline, 140 gold/6 crystals funding and the departure action are readable.
- `stage-2-earned-arrival.png`: Rootward/Elderwild552616 Stage2 shows the expected 140 gold/6 crystals, two level3 Swordsmen restored to42HP and one fresh24HP Militia. The Watch-then-Duskspire objective and rival threat are readable. The two-line Old Causeway name stays within its province.

No material visual defect found in these seven frames. The other four restart frames were reviewed by root. There are11 PNGs in the output: nine restart frames plus the two departure continuation frames. The remaining case continuations have exact model/input receipts but no post-continuation screenshot; hover tooltips and125% reading are not independently covered by this review.

## Receipt correspondence

`verification.json` records source393359f62f6a13b3590b94a21287c2886e62e5b5, 197 unchanged source/asset/fixture fingerprints, writer PID37001 and distinct resume PID37256. Nine writer Games and nine resume Games closed. All nine cases report exact load, exact continuation and unchanged manual bytes. Actual run:76 input activations,81.772513375s wall,20.535762s combined writer/resume CPU, pyglet backend. This is fresh Python-process native input verification, not a newly launched packaged application or human playtest.

## Manual and backup byte scope

The helper's `_manual_files` includes exactly `save_1.json` through `save_3.json` and `save_1.backup.json` through `save_3.backup.json`. This matches `SaveManager._backup_path`, which uses `with_suffix('.backup.json')`; the suffix is correct.

Each isolated case writes its manual slot once. No existing manual backup is created by this journey. Consequently, the checks prove the primary manual save stays byte-identical and no backup is unexpectedly created during loading/continuation. They do not newly exercise preservation or recovery of an existing backup. Autosave files10–12 and their backups are intentionally outside this manual-byte invariant because valid continuations can update them.
