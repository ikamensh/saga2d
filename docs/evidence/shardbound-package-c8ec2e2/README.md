# Mac development checkpoint: full packaged campaign and recovery

Clean source **c8ec2e2657148beaee344ff5fa82d5830c1c62d7**, built in a detached
checkout on macOS 26.6.2 arm64 with CPython 3.13.2 and the locked build recipe.
This includes eleven encounter patterns, Relief's corrected retry advice,
the complete campaign/battle reading HUDs and the new process-restart verifier.
Causeway and ordered battle playback are not in this archive.

The local archive is
`dist/shardbound-checkpoints/c8ec2e265714/Shardbound-macos-arm64.zip`:
**32,772,362 bytes**, SHA-256
`f6167e993d5279985082049ad5c4136c55e0ee81c8f9c92a29d85f0522854e82`.
The older checkpoint remains preserved. No publication has occurred.

## What was exercised

- The extracted app runs outside the repository with Python environment overrides
  removed and an OS-only executable search path. Its installed asset path and
  actual frozen executable are checked. All fourteen shipping WAVs decode and
  complete the existing silent-driver playback/mix/lifetime check.
- The direct campaign uses four separate app processes: three complete linked
  shards and a final reload of the completed ending. It records 381 native inputs,
  eight exact UI save/reloads and three exact process restarts.
- The recovery campaign uses five processes and records 421 native inputs, nine
  UI save/reloads and four exact process restarts. The second process deliberately
  loses Westwatch through ordinary turns and retreats; the next loads that saved
  recovery decision before selecting its retinue. It then completes all shards.
- Every changing campaign order uses native key/click input. Battle orders use
  the visible automatic-round control. Both routes restore the entire saved
  State, retain 125% reading preferences, and return to title after the ending.
  Their accelerated durations are harness timings, not player playtime estimates.
- LaunchServices `open -W -n ... --args --smoke-image ...` succeeds. The local
  `codesign --verify --deep --strict` check succeeds for the ad-hoc signature.
- The full source suite passed **1,171 tests in 135.92 seconds** before the clean
  build. Independent review also reproduced both source-mode process journeys
  and confirmed the three helper modules' import closure stays in the snapshot.

## Retained evidence

`build-manifest.json` preserves the complete binary inventory, package-data and
source hashes, environment, clean revision and archive hash. `provenance.json`
matches 88 snapshotted game/framework/recipe/helper inputs back to that Git revision.
`packaged-smoke.json` and `launchservices-smoke.json` are the actual app receipts.
`campaign-processes.json.gz` preserves all nine complete phase reports, native
event streams and exact checkpoint states. The full output folders and saved
verification campaigns accompany the archive under its checkpoint directory.

Twelve actual packaged images were opened and inspected: the six quick-smoke
screens, Relief and final Gate briefings at 125%, the direct completed ending,
the restored recovery decision, the recovered ending, and LaunchServices title.
Source-mode preflight images are not substituted for these frozen app captures.

This is a local development checkpoint. It does not establish Windows or a
clean user account, Developer ID signing/notarization, human playtests/listening,
full manual/content coverage or the sustained release-candidate matrix. All
Early Access gates remain incomplete.

Reproduce with the [documented build command](../../packaging.md) and append
`--check-campaign`.
