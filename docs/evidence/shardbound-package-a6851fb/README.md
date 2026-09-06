# Build information and isolated profiles — 2026-09-06

Preserved development source: **a6851fb65df5abcd1c923ab2c736921300a12ea6**,
clean at packaging. The archive includes the CPU caps, twelve authored encounter
patterns and ordered battle playback, plus the new About screen and isolated
launch profile. **All Early Access gates remain incomplete.**

Archive: `dist/shardbound-checkpoints/a6851fb65df5/Shardbound-macos-arm64.zip`

- Size: **32,792,562 bytes**.
- SHA-256: `fcb92ef1a01be9d52168ae8b1ffb655c1ab95c1447e7b6fe1ef8c01f46abec27`.
- Host: macOS 26.6.2, Apple M4 / arm64, CPython 3.13.2.
- Recipe: locked runtime and pinned PyInstaller 6.22.2 / hooks 2026.7.

## What changed

**A / About this build** on the title and Field Guide shows build identity,
current scope, unfinished work, controls, credits, local feedback instructions
and the actual saves/settings directory. Frozen builds read their own bundled
manifest; source launches say `source checkout`. Both use the same version
constant. `--data-dir PATH` configures a separate profile for ordinary launches.
The shipped CLI and package check share `create_session`, which uses existing
save/settings configuration. No Saga2D API or game schema was added.

The existing measured, paginated message screen handles About and its reading
size. Independent read-only review found no blocker and identified one unused
import, which was removed. [Local store-description draft](../../shardbound-store-draft.md)
and the packaged player guide describe current behavior and development limits.
The draft remains unpublished and its complete candidate/media audit is open.

## Verification and limits

- **11 focused integration tests pass** on clean `a6851fb`: title choices,
  About navigation, isolated profile preferences and exact campaign reload,
  title reading, packaging inputs and phased campaign verifier behavior.
- Native title verification passes **216 configurations, 15 About pages across
  six size/reading combinations, and 372 inputs**. Window sizes: 1280×720,
  1280×800 and 1920×1080; reading sizes: 100/125. The report names its parent
  `6a2ef31` because it ran before the change was committed; every recorded
  game/framework/tool source hash was checked against `a6851fb` and matches.
- The extracted frozen app, outside the repository, passes title and Guide
  About navigation with exact manifest identity, isolated data directory,
  campaign/battle/Guard saves, Codex/rival, settings Apply/Cancel/restart and
  all fourteen installed audio files with native playback/mix/cleanup.
- The same native smoke passes through LaunchServices with working directory
  `/`. Local ad-hoc `codesign --verify --deep --strict` passes. This does not
  establish downloaded-distribution Gatekeeper or notarization acceptance.
- Six actual packaged frames were opened: title, both About pages, Guide,
  shard and battle. Three native source About pages at 125% were also opened.
  Text and controls fit the inspected frames. Source-level layout checks are
  distinct from the packaged 1280×800 / 100% smoke.
- An ordinary extracted executable launch with the isolated profile stayed
  running for 27 seconds; a live process sample was 20.4% CPU. It was then
  deliberately closed. This is a bounded launch observation, not a benchmark
  or playthrough. The native smoke now yields between frames at ≤30 FPS.

The independent UI-only opening attempt returned exactly: “The Mac is locked
and automatic unlock could not unlock it. Ask the user to unlock the Mac
manually before continuing.” It produced **zero game observations, screenshots
or gameplay inputs** and supplies no G09 walkthrough or human-playtest credit.
An earlier unguarded LaunchServices ordinary launch did not remain running;
the awake native launch and LaunchServices smoke above succeeded. No cause for
that first exit is asserted. All test/game processes were terminal afterward.

This archive has **not** repeated the earlier `219bcf9` full frozen campaigns,
1,207-test suite, or the cancelled large stress/soak jobs. Historical evidence
keeps its own source identity. Human/listening review, Windows and clean-account
execution, remaining strategic balance, full content/display acceptance and
sustained candidate testing remain open. Heavy work continues one job at a time;
the large cancelled jobs were not restarted.
