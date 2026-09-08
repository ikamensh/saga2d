# Standalone Shardbound builds

This is the packaging foundation for G14/G18, not a release-readiness claim.
The local macOS arm64 artifact starts without a repository, installed Python,
uv or a terminal window. Windows remains an untested build target.

The current preserved Mac development build is clean source **7b5562d**:
[artifact identity, packaged campaigns and visual review](evidence/shardbound-package-7b5562d/README.md).
It includes the current portraits, icons, terrain, sound and varied site placement.
The extracted archive passes direct/recovery campaigns across nine app processes,
LaunchServices smoke and local ad-hoc signature verification. Its ordinary UI-only
check stopped at the locked Mac; this does not establish clean-account, Windows,
human playtest/listening or co-op connectivity acceptance.

## Installed local copy

`/Applications/Shardbound.app` is the extracted `Shardbound-macos-arm64.zip`
from clean source `5ba80b8`, installed 2026-09-08. The installed executable
hash matches the dist build and manifest, `codesign --verify --deep --strict`
passes for the ad-hoc signature, and the installed app passed the full packaged
smoke journey launched through LaunchServices from `/Applications`. To update
it, rebuild, extract the new archive and replace the app in Finder; saves and
settings live in the game's data directory and are preserved.

## Build locally

From the repository root, with uv installed:

```bash
uv run --locked --isolated --python 3.13.2 --with-requirements packaging/requirements.txt python tools/build_eador.py
```

A release build names its version and refuses a modified tree; on Windows it
also compiles the per-user installer from the shared `packaging/game.iss`:

```bash
uv run --locked --isolated --python 3.13.2 --with-requirements packaging/requirements.txt python tools/build_eador.py --version 0.1.0-preview.1 --require-clean
uv run python tools/verify_shardbound_package.py dist/shardbound          # extracted app: smoke journey + online co-op diagnostic
```

Artifacts are versioned: `Shardbound-<version>-darwin-arm64-app.zip` on a Mac,
`Shardbound-<version>-windows-x64-portable.zip` and
`Shardbound-<version>-windows-x64-setup.exe` on Windows, listed with hashes in
`build-manifest.json` (`artifacts`) and `SHA256SUMS`. The frozen entry's
`--online-smoke REPORT --endpoint URL` mode creates a co-op room, joins it,
applies a build and an exploration from both seats and reclaims the creator's
seat; the verifier runs it against a loopback server and, on Windows with
`--public-server`, from the installed executable against the live service.
The [Windows workflow](../.github/workflows/shardbound-windows.yml) runs the
smoke journey under a test-only Mesa driver, installs and uninstalls the
installer, and publishes `shardbound-v*` tags as GitHub releases; the website
lists accepted releases from `releases/catalog.json`.

Add `--check-campaign` to exercise two complete linked campaigns in the extracted
app. The direct journey uses four separate app processes; the recovery journey
uses five, including a restart at the lost-capital recovery decision. Every
changing order uses native player input. Tactical battles use the visible
automatic-round control; this is campaign/save verification, not manual tactics
or a human playtest. The final process restores the completed chronicle and
returns to title. Settings persist at 125% reading size throughout.
The campaign policies share the existing 25% cooperative CPU allowance and
native input is paced at 30 FPS. Phase receipts record both wall and CPU time;
each invocation closes its Game. PyInstaller itself is not CPU-throttled, so
the build remains the sole expensive local job.

The check writes complete state checkpoints, event records and screenshots under
`dist/shardbound/campaign-verification/`, isolated from player saves. Each fresh
process loads through the title's quickload control and compares the entire saved
State with the preceding process. These reports supplement the quick smoke check;
they do not establish clean-account, Windows or human playtest acceptance.

Generate shipping audio explicitly before packaging when composition or
synthesis source changes:

```bash
uv run python tools/build_eador_audio.py
```

Generated WAVs and their manifest are committed inputs. Packaging rejects
missing, changed or unrecorded WAVs and stale generator-source hashes; it never
generates or caches audio at application launch.

The packaging command installs locked runtime dependencies in an isolated environment,
adds the pinned packaging tools, snapshots the game/framework sources, entry
point, spec and audio generator, builds the native artifact, archives it,
extracts the archive outside the repository,
and runs its hidden-window smoke check. An awake graphical desktop is required
for that final real-pyglet check. `--skip-smoke` builds an explicitly unverified
artifact when only a build machine is available.

The foundation pins CPython 3.13.2, PyInstaller 6.22.2 and hooks-contrib 2026.7.
Runtime versions come from `uv.lock`; build-tool transitive versions and hashes
are in `packaging/requirements.txt`. Upgrade both PyInstaller packages together,
as recommended by the [official installation guide](https://pyinstaller.org/en/stable/installation.html).

To regenerate the packaging lock after an intentional tool upgrade:

```bash
uv pip compile packaging/requirements.in --universal --python-version 3.13 --generate-hashes --output-file packaging/requirements.txt
```

Update the matching tool-version check in `tools/build_eador.py` and rerun
the complete build and package checks. Pins make build inputs repeatable;
the recipe does not promise byte-identical archives across builds. Build
timestamps, platform tooling and binary signing can affect output hashes.

## Outputs and verification

All generated files stay under ignored `build/shardbound/` and
`dist/shardbound/`. On macOS:

| Output | Purpose |
|---|---|
| `Shardbound.app` | Normal windowed application; open it in Finder |
| `Shardbound-<version>-darwin-arm64-app.zip` | Archive preserving bundle symbolic links |
| `build-manifest.json` | Source and package-data hashes, commit/dirty status, versions, platform, file inventory, archive hash and smoke result |
| `packaged-smoke.png` | Real title-screen capture from the extracted archive |
| `packaged-smoke-shard.png` | Real campaign-screen capture from the extracted archive |
| `packaged-smoke-codex.png` / `-rival.png` | Rules reference and finite expedition inspection |
| `packaged-smoke-settings.png` | Native settings preview before Apply |
| `packaged-smoke-battle.png` | Tactical battle with Guard restored from a save |
| `packaged-smoke.json` | Runtime, settings/save restoration, installed audio hashes and native playback verification |

The app includes a Python runtime and runtime libraries. The source snapshot's
`package-data.json` freezes the exact ordered collection; the snapshotted spec
consumes that list. Every collected file has a byte count and SHA-256 in the
build manifest's `package_data` map. This includes every shipping sound cue and
music loop, `eador/assets/audio-manifest.json`, audio provenance, and other package
data. The review-only cue sampler under `docs/evidence/` is not shipped.
Current art includes the generated environment and hero portraits, offline
terrain illustrations, original icons and procedural miniatures. Their exact
assets and provenance are collected with the game. Bundled
`Contents/Resources/release/` contains a player guide, credits, original license
texts found in dependency distributions, the runtime lock and build metadata.
No change to the Saga2D framework wheel is needed: the game is an application
that consumes the framework.

The smoke launcher uses temporary settings and saves, and writes its result to
the requested path. Assets resolve from the installed `eador` module, independent
of the working directory. Native key events apply and cancel settings edits,
start a game, save/reload campaign state, inspect the codex and rival, locate the
expedition, invade a province, Guard, play an automatic battle round, restore
the guarded battle and retreat. A fresh Game reloads the saved sound settings.
The smoke renders title, settings, shard, codex, rival and battle screens.

All shipping WAVs are decoded in full and checked against the audio
manifest. The native silent driver plays every effect to completion and briefly
starts each looping track, checking live mute/channel gains and player cleanup.
The builder compares the reported WAV hashes with the frozen input collection
and requires the asset root to reside inside the extracted archive. This quick
playback check does not establish listening quality or full-loop continuity;
the dedicated `tools/build_eador_audio.py --verify-native` checks complete loops,
and human listening remains required. The
builder checks that the process is frozen and is the extracted executable,
with Python environment overrides removed and an OS-only executable search
path. Its temporary working directory is outside the repository. Inspect the
PNGs after a build; successful execution alone does not establish visual quality.

For a source-mode preflight without building a frozen artifact, run the same
entry point from an unrelated working directory with the repository on
`PYTHONPATH`:

```bash
cd /tmp
PYTHONPATH=/absolute/path/to/saga2d /absolute/path/to/saga2d/.venv/bin/python /absolute/path/to/saga2d/packaging/entry.py --smoke-image /tmp/shardbound-source-smoke.png
```

That report correctly records `frozen: false`. It verifies the recipe's journey
but cannot pass the standalone executable gate.

You can also exercise the macOS app-launch path without opening a terminal
window for the application:

```bash
open -W -n dist/shardbound/Shardbound.app --args --smoke-image /tmp/shardbound-launch-check.png
```

Without smoke arguments, `Shardbound.app` runs the game's ordinary entry point.
For an independent playtest with separate saves and settings:

```bash
open -n dist/shardbound/Shardbound.app --args --data-dir /tmp/shardbound-playtest
```

**A / About this build** on the title and Field Guide shows the recorded version,
source commit, development scope, credits, feedback instructions and actual data
directory. Source launches identify themselves as a source checkout; frozen
builds read their bundled manifest and identify modified source when applicable.
The smoke check exercises this ordinary launch configuration with an isolated
profile, reads every About page and checks its identity against the manifest.
The short native smoke yields between frames at no more than 30 FPS; longer
campaign verification uses the same paced native input driver as source checks.

Normal player saves retain the game's configured location; smoke mode never
uses those saves. The special flag is packaging verification, not a player
feature or a substitute for a complete packaged campaign test.

The separate `--campaign-check OUTPUT --phase N` verification entry runs one
phase of the journey above; add `--recovery` consistently for all five recovery
phases. Phase one requires a new output directory. The build snapshots only the
three existing public-input policy helpers it needs, alongside the verifier;
the frozen app does not import them from a source checkout. Normal launches do
not execute these verification paths. The build manifest fingerprints their
exact sources along with the application and packaging recipe.

## Evidence from the first local artifact

Verified on 2026-09-05: macOS 26.6.2, Apple Silicon arm64, CPython 3.13.2;
NumPy 2.4.2, Pillow 12.1.1 and pyglet 2.1.13. The extracted app rendered both
screens, passed save/load, and was inspected visually. The `.app` also passed
the same smoke check through macOS LaunchServices, which set its working
directory to `/`. A normal no-argument launch remained running; native UI
automation timed out, so a normal interactive packaged playthrough remains
unverified. The test process was closed afterward.

The initial archive was 20,268,428 bytes, SHA-256
`fd6c807ebd5c5cb0a05709743b15fdeaf44b6c20c08d47bab95f8250377bff37`.
Its manifest records source commit `bb21793` with a dirty working tree and
hashes the actual snapshotted files. It is development evidence, not a named
release candidate. Rebuilding replaces these local outputs; consult the new
manifest for the current archive hash and exact inputs.

`codesign --verify --deep --strict` passed for the local ad-hoc signature,
and every bundle symlink resolved. No signing identity or certificate was
used, and no notarization or distribution approval was performed.

## Refreshed playable checkpoint — 2026-09-06

Source `b061ea8` was rebuilt with the codex, progression/save browser and
finite rival. The extracted frozen app passed the expanded native input
journey: new campaign, campaign save/load, codex and rival inspection,
province location, invasion, automatic battle round, battle restoration
and retreat. The same journey passed through macOS LaunchServices with
working directory `/`. Packaged rival and battle screenshots were inspected;
local ad-hoc signature verification passed.

The archive is **20,329,496 bytes**, SHA-256
`e907254c311f4a6629fd0164eb58a95e57b8ca3b011574994a4be274e4a693f3`.
[The retained evidence](evidence/shardbound-package-2026-09-06.json) records
source hashes, runtime versions, extracted/LaunchServices reports and
screenshot hashes. The manifest's dirty flag reflects unrelated `.gitignore`
work; game/framework/packaging sources were committed at the named snapshot.
This is a development checkpoint on the same macOS host. The clean-account,
Windows and full packaged-campaign gates remain open.

This historical archive predates the Guard/settings/audio packaging checks
above. Updating the recipe or passing a source-mode smoke does not update that
artifact or its evidence. Build and inspect a new frozen candidate only after
the intended game and audio integration commits are assembled.

## First-playtest checkpoint — 2026-09-06

The preserved local archive at
`dist/shardbound-checkpoints/f63aa6f2806c/Shardbound-macos-arm64.zip`
contains source `f63aa6f2806cfa47395b27cd89d531dce67ec7bf`. It is
**32,670,210 bytes**, SHA-256
`f7a94054783ae42d5cbed66232512cb663c233eba9b1201e3509c8490def6b96`.
The [retained manifest](evidence/shardbound-playtest-f63aa6f-build.json)
records the exact inputs and extracted frozen application checks: native
input, campaign/battle/Guard saves, settings Apply/Cancel/restart, Codex/rival
rendering, and all fourteen installed audio assets with live mix/cleanup.

This archive includes the control/flight roster, audio/display settings and
initial Pack Hunt. It predates the final Pack Hunt deployment tuning, the
four new active relics, and wrapped Labels. It remains a development build
(`release_ready: false`), preserved separately from subsequent build output.
The dirty flag reflects unrelated `.gitignore` work; snapshotted source hashes
are recorded. Windows, a clean account and a full packaged campaign remain
unverified. See [the playtest log](eador-playtests.md) for feedback status.

## Integrated playable checkpoint — 2026-09-06

The previous integrated Mac checkpoint is source `0e271756d35d` at
`dist/shardbound-checkpoints/0e271756d35d/Shardbound-macos-arm64.zip`:
**32,693,078 bytes**, SHA-256
`c182ef2e1daf00633e0381441dfc02eeb4f95d6193fbdc2ef52dc05a6577a21c`.
It includes Challenge-2, the eighth authored adventure and larger guidance
text, with an updated player guide. [Manifest, launch report and inspected frames](evidence/shardbound-integrated-0e27175/README.md)
retain the extracted frozen and LaunchServices checks. The earlier playtest
archive is unchanged. This remains local development evidence; the native
source campaign matrix is not a full packaged campaign test.

## Ten-family development checkpoint — 2026-09-06

The latest preserved Mac checkpoint is source `56f1ffb1036b` at
`dist/shardbound-checkpoints/56f1ffb1036b/Shardbound-macos-arm64.zip`:
**32,734,895 bytes**, SHA-256
`c8a8a2a5bb3c9fe7f026dd7dccfddd3e03a2d237496502dc5357678f8165d3e1`.
It includes Aerie Raid, Smuggler Screen, troop replacement, Tower infusion and
larger title, purchase, Hero, reward/result, save, rival and campaign reading.
[Manifest, launch checks and inspected frames](evidence/shardbound-package-56f1ffb/README.md)
record extracted-runtime and LaunchServices smoke with isolated saves/settings,
all shipping audio and a local ad-hoc signature. This is a development checkpoint;
full packaged-campaign, Windows, clean-account and human checks remain open.
Earlier archives and the original pending playtest are unchanged.

## Windows x64 plan — untested

Build on a Windows x64 host using x64 CPython 3.13.2. Run the same uv build
command above from PowerShell. It produces `Shardbound/Shardbound.exe` and
`Shardbound-<version>-windows-x64-portable.zip`. Preserve the entire application folder; the
executable alone is not the package. PyInstaller requires separate native
builds for each operating system. [Official multi-platform guidance](https://pyinstaller.org/en/stable/usage.html#supporting-multiple-operating-systems)

The [manual Windows workflow](../.github/workflows/shardbound-windows.yml)
checks out an exact source commit, installs pinned tools and runs the recipe
with `--skip-smoke`. It has no push, pull-request or scheduled trigger. It has
not been dispatched, and no Windows artifact has been uploaded. Building on
a runner does not verify an interactive installation.

The [Windows handoff](windows-shardbound.md) describes the concrete dispatch
and artifact checks, followed by clean-account launch, save/restart, display,
audio and complete campaign checks. Record the host, archive hash and results.
Neither build success nor this prepared workflow passes the Windows runtime
gate.

## Remaining release work

Only the current macOS host was tested; compatibility with older macOS,
Intel Macs, Windows or Linux is unverified. Build on the oldest intended
supported macOS before claiming that compatibility. [PyInstaller requirements](https://pyinstaller.org/en/stable/requirements.html)

G14 still needs clean-account/platform validation, a full packaged game
journey, and verification of all final assets, fonts, audio and saves.
The game currently requests system Verdana/Georgia and uses a development
app icon. G11/G18 still need suitable bundled fonts, a product icon, final
asset/license provenance review, current player documentation, product
versioning and support information. A local ad-hoc signature does not establish
Gatekeeper acceptance of a downloaded distribution. Publishing and identity
signing remain separate decisions.

The bundle uses PyInstaller's recommended one-folder macOS app structure,
and `ditto` preserves the symbolic links it requires. [App bundle guidance](https://pyinstaller.org/en/stable/usage.html#building-macos-app-bundles),
[symbolic-link requirements](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#requirements-imposed-by-symbolic-links-in-frozen-application)
