# Mac checkpoint: twelve patterns and ordered battle playback

Clean source **219bcf94136db9cd0fe2ac81f7e8a636be657e60** combines Runebound
Causeway, ordered battle playback, the paced playback reliability driver and
updated player controls. No framework API or save schema was added by these
changes. Built on macOS 26.6.2 arm64 with CPython 3.13.2 and the locked recipe.

Preserved archive:
`dist/shardbound-checkpoints/219bcf94136d/Shardbound-macos-arm64.zip`

- **32,788,690 bytes**
- SHA-256 **2781921fcd858577159c7222e915e479b7af88345b6cf3bfe0144641cd4b7bd8**
- Full source suite: **1,207 passed in 380.08 seconds**.
- Combined linked fuzz: 12 model campaigns, 12 scene runs, 3,004 random inputs
  and 327 inputs verified inert during playback. This is bounded integration
  coverage; larger content-specific runs retain their separate source revisions.
- Tribes: 60 AI games and 20 random-input runs passed.

## Actual packaged journeys

The archive was extracted outside the repository. Nine fresh frozen processes
ran with Python environment overrides removed and an OS-only executable search
path. Each report identifies its actual executable, installed assets and PID.

| Route | Processes | Native inputs | UI save/reloads | Exact process joins |
|---|---:|---:|---:|---:|
| Direct three-shard campaign | 4 | 471 | 8 | 3 |
| Lost-capital recovery campaign | 5 | 513 | 9 | 4 |

Both routes finish three shards, restart at their completed ending and return
to title. Recovery additionally restarts at the saved recovery decision before
choosing a retinue. Every join restores the entire checkpoint exactly, and all
processes retain 125% reading preferences. These are public-input policies using
automatic rounds and the visible Finish playback control; they do not establish
manual tactics, natural playback timing, human comprehension or player duration.

The installed-asset/audio smoke, LaunchServices app launch and local strict
ad-hoc signature checks pass. Fourteen shipping WAVs decode and pass the existing
silent-driver playback, mix and resource-cleanup checks. Six actual package
screenshots were opened and inspected: battle, Codex, final Gate briefing,
completed campaign, restored recovery and LaunchServices title. Additional
captures are retained without being counted in that inspection.

## Retained records

`build-manifest.json` includes the complete binary inventory, package-data/source
hashes, clean revision, environment and archive identity. `provenance.json`
matches 90 game/framework/recipe/helper inputs to Git and names the six inspected
images. The build recipe's generated `tools/__init__.py` is checked separately.
`campaign-processes.json.gz` preserves all nine complete reports, event streams
and State checkpoints. Full output folders and verification saves accompany
the preserved archive. Smoke receipts, full-suite output and both integration
fuzz reports are retained here.

Natural playback, reduced motion, paid manual Causeway decisions and unchanged
pre-playback outcomes have separate [source evidence](../../eador-battle-feedback.md)
and [combined native journeys](../../eador-causeway-feedback-integration.md).
The earlier [90-second playback probe](../shardbound-playback-soak-449e40e/README.md)
is not a two-hour candidate soak.

This is a development checkpoint. Windows/clean-account execution, human
playtests/listening, remaining strategic balance and sustained candidate stress
are still open. All Early Access gates remain incomplete. Earlier archives are
preserved, and nothing has been published.

Reproduce with the [build command](../../packaging.md), adding `--check-campaign`.
