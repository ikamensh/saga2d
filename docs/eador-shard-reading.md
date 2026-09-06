# Campaign map reading

ShardScene uses the existing **Reading size 100% / 125%** preference. Its visible **Text size / F2** control opens the same Settings Apply/Cancel/restart path as the reading screens. No campaign save fields or game rules change.

Treasury, income/upkeep, gold-yield rules, supply warnings, hero health/mana/experience/actions and location remain visible above the map. The right panel preserves the selected province, complete defenders, travel/explore guidance and stronghold commands. Objective/rival guidance and every surviving troop's role, level and health remain visible together. Settings, resizing and read-only overlays preserve the selected province; Enter still acts on it.

The layout uses measured game-owned Labels and Columns. The logical canvas remains 1280×800. Small hex names remain orientation aids at their existing size, wrapping within their own map columns; selecting any hex gives its full name and details at the selected reading size. The title and command buttons retain their existing sizes. This is not a claim that every label throughout the game now scales.

Messages are never shortened with an ellipsis. A message that exceeds the bottom line has an explicit **Read message / D** control, opening the existing read-only measured diagnostic scene under the accurate title **Complete campaign message**. It preserves the exact text, selected province and current state, including after real long-path save errors. Returning cannot execute a queued underlying travel command.

The art helper's optional `name_label=False` allows this map to lay out names separately. Its default rendering remains unchanged. No framework layout API or strategy widget was introduced.

## Verification

`tests/eador/test_shard_reading.py` exercises Settings Apply/Cancel, actual selected-province invasion, real long-path file errors, immediate post-command autosave errors, and earned/historical states through public Game input. The existing Aerie verifier now checks the full measured map layout rather than assuming the first Label is a hint at a fixed y coordinate; all earned route and reward assertions remain.

Run `python tools/verify_eador_shard_reading.py --output /tmp/shard-reading`. It checks every selected province across three actual window sizes and both reading sizes, including all current difficulty modes, a paid full control army, old saved rules, encirclement and zero gold/crystals/actions. It also executes the actual map invasion/retreat/end-turn controls, exact reloads, restart, and complete filesystem diagnostics. Native screenshots are required in addition to the mock checks.

The [retained source-attributed matrix and seven inspected screenshots](evidence/shardbound-hud-0bd713b/README.md) cover production `0bd713b`: 2,394 native layouts, 4,685 input activations, 127 exact reloads, full 1,152-test suite and both fuzzers. These checks establish readability and command/save consistency for this slice; they do not establish artistic approval, game balance or full release readiness.
