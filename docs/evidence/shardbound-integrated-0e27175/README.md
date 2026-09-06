# Integrated development checkpoint — 2026-09-06

Source: **0e271756d35dc195ea359c7ec1127c3c9d317394**. This is a playable
development checkpoint, not an Early Access release candidate.

[Native evidence](native.json) records 119 source/fixture hashes checked before
and after the combined run, exact inputs and saved outcomes. No measured file
changed. The listed opening, continuation, linked and Explorer journeys total
**1,089 input activations and 47 exact save/reloads**:

| Journey | Inputs | Exact reloads | Result |
|---|---:|---:|---|
| Three mode openings | 97 | 3 | Paid support recovery; three additional fresh-Game restarts preserve mode/state |
| Original Challenge-1 continuations | 37 | 3 | Rest, next-shard funding and defeat recovery match actual earlier native snapshots |
| Challenge-2 linked campaign with recovery | 396 | 13 | Lose a realm, recover, then finish all three shards |
| Explorer Commander north / south | 151 / 154 | 7 / 8 | Round-three escapes, every ally alive |
| Explorer Warrior with Acolyte | 153 | 7 | Round-three escape, every ally alive |
| Explorer smaller Scout party | 101 | 6 | Round-two escape, every ally alive |

The same batch checks **132 approach views plus six guidance records** at
100/125 reading size and 1280×720, 1280×800 and 1920×1080 native windows on
macOS Retina. All 13 encounter definitions are covered, including the actual
Ranger/Acolyte/alone Explorer deployments, wounded retries and blocked fees.
It also verifies reading Apply/Cancel, resize, return from Codex and restart.
These layout records are separate from the input/reload totals above.

The retained native frames were inspected: [old recovery](challenge1-recovery.png),
[current recovery](challenge2-recovery.png), [completed recovery campaign](challenge2-completed.png),
[southern Swap](explorer-south-swap.png), [Acolyte Heal](explorer-acolyte-heal.png),
[Scout exit](explorer-scout-exit.png), and [larger briefing](explorer-ranger-125.png).
The briefing uses the actual army slot, finite defender counts/HP and current fee.

Before capture, the combined source passed **1,041 tests in 67.81 seconds**,
60 Tribes AI games plus 20 random scene runs, and 12 linked Shardbound model
campaigns plus 12 scene runs with 2,227 inputs. These are bounded development
checks. The native batch's 38.41-second scripted runtime is not human pacing.

## Preserved local application

`dist/shardbound-checkpoints/0e271756d35d/Shardbound-macos-arm64.zip`
is **32,693,078 bytes**, SHA-256
`c182ef2e1daf00633e0381441dfc02eeb4f95d6193fbdc2ef52dc05a6577a21c`.
The earlier `f63aa6f2806c` playtest archive remains unchanged.

[Build manifest](build-manifest.json) freezes the package inputs, runtime,
archive inventory and extracted executable checks. Its dirty flag reflects only
the unrelated `.gitignore` edit; the packaged sources and player guide were
committed. The extracted app ran outside the repository with Python environment
overrides removed. Native saves, guarded battle restoration, Codex/rival,
settings Apply/Cancel/restart and all fourteen installed WAVs passed.

[LaunchServices](launchservices.json) repeated that isolated-save smoke through
the macOS app launch path with working directory `/`. Local ad-hoc signature
verification passed. The packaged [title](package-title.png), settings and
[battle](package-battle.png) frames were inspected. No external publication,
identity signing or notarization occurred.

This does not establish a full packaged campaign, a clean-account launch,
Windows support, human comprehension, listening quality, candidate stress or
release readiness. G01–G19 remain open. Reading size still covers only Codex,
Guide and expedition briefings. The package predates subsequent infusion,
catalog reading and ninth-encounter work.

Reproduce the source journeys with `tools/verify_eador_difficulty.py`,
`tools/verify_eador_campaign.py --difficulty challenge --recovery`,
`tools/verify_eador_explorer.py --plan PLAN` for each of its four plans, and
`tools/verify_eador_guidance.py --matrix`. Use `uv run python` and distinct
`--output` directories. [Packaging commands](../../packaging.md) build and
check a new artifact; they do not modify this preserved checkpoint.
