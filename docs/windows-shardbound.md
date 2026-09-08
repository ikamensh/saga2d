# Shardbound Windows x64 build and runtime handoff

The [Windows workflow](../.github/workflows/shardbound-windows.yml) builds the
portable ZIP and per-user installer, runs the frozen smoke journey and the online
co-op diagnostic in the extracted and installed applications (with a test-only
Mesa driver), uninstalls, and publishes a `shardbound-v*` tag as a GitHub
release. A `workflow_dispatch` with a version builds and verifies without
publishing unless `publish` is set and the tag exists at that commit.

## Prepare the build

The job checks out the exact commit, uses the x64 Windows runner, and runs:

```sh
uv run --locked --isolated --python 3.13.2 \
  --with-requirements packaging/requirements.txt \
  python tools/build_eador.py --version VERSION --skip-smoke --installer --require-clean
uv run python tools/verify_shardbound_package.py dist/shardbound --mesa-dir MESA --public-server wss://games.tachyon-ai.eu/play
```

CPython 3.13.2, uv 0.12.10 and the action revisions are pinned. Runtime packages
come from `uv.lock`; PyInstaller 6.22.2 and hooks 2026.7 come from the hashed
`packaging/requirements.txt`. Checkout preserves LF bytes so audio provenance
continues to identify the committed generators. The runner image can change;
its version is recorded, and identical archive hashes across builds are not
promised. The job has read-only repository access, no persistent cache, a
30-minute timeout and one active Windows build at a time.

After a successful build, download the workflow artifact before its 14-day
retention expires. Keep these files together:

- `Shardbound-VERSION-windows-x64-setup.exe` and `-portable.zip`: the installer
  and the application folder with its bundled runtime/assets.
- `build-manifest.json`: exact source, Python/build versions, asset inventory,
  file hashes and artifact identity; `release_ready` stays false because the
  Early Access gates are separate from distribution.
- `verification.json` and `verification/`: smoke frames, loopback and public
  online receipts, install and uninstall logs from the CI host.
- `workflow-build.json`, `SHA256SUMS` and `mesa-test-context.json`.

The Actions artifact wrapper has its own digest. Compare the **inner application
ZIP** with `SHA256SUMS` and `build-manifest.json`. In PowerShell, after extracting
the workflow download:

```powershell
Get-FileHash .\Shardbound-VERSION-windows-x64-setup.exe -Algorithm SHA256
```

A green job proves the build and the automated checks on the CI host with a
software GL driver. It does not establish clean interactive Windows
acceptance on real hardware, platform support or G14 completion.

## Clean interactive Windows check

Use a fresh standard account on the Windows x64 version being evaluated, with
no source checkout, Python or uv installed and a working interactive graphics
session. Record Windows edition/build, CPU/GPU/driver, display resolution/scaling,
test date, tester and the ZIP SHA-256. Do not generalize one tested configuration
to other Windows versions or hardware.

1. Extract the application ZIP with Explorer to a new ordinary user directory.
   Keep the complete `Shardbound` folder, including `_internal`. Record any
   security warning or launch refusal as an observation; do not silently bypass
   it or treat the unsigned development build as signed distribution evidence.
2. Double-click `Shardbound.exe` in Explorer. Confirm no terminal or developer
   tools are required. Open About and match its version/source prefix to the
   manifest. Capture Title and About, including the displayed save location.
3. Start a shard. Inspect map terrain/icons, a hero portrait, Codex and a battle.
   Check fonts, keyboard/mouse input and 100%/125% reading. Capture actual frames
   and record clipping, missing assets or unreadable controls.
4. Hear music and several battle cues through the real device. Check mute and
   channel volumes, Apply/Cancel and persistence after restarting. Distinguish
   audible playback from a complete listening-quality review.
5. Quicksave/load with F5/F9; use F6 for a separate manual slot. Preserve a save
   in a shard and battle, quit through the app, and confirm the owned process
   exits. Relaunch from Explorer and resume both saves; record the same visible
   turn, army, position, resources and battle phase. Retain the tested saves.
6. Record each result and any failure, with images/logs and exact build identity.
   Cover remaining campaign/choice/result transitions under the separate G12/G14
   journey checks before claiming their acceptance. Co-op is not exercised by
   this offline handoff; record any later local or online co-op test separately.

Passing these checks supplies evidence for the named Windows configuration;
it does not close the other Early Access gates. Keep the build receipt and
runtime report distinct in the evidence directory. Windows runtime remains
unverified until the actual clean-account results have been reviewed.

## Recipe references

Action inputs and runner syntax were checked against primary documentation:
[manual dispatch](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch),
[Windows runner labels](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[checkout 7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1),
[setup-uv 9.0.0](https://github.com/astral-sh/setup-uv/blob/v9.0.0/action.yml),
[uv 0.12.10](https://github.com/astral-sh/uv/releases/tag/0.12.10), and
[upload-artifact 7.0.1](https://github.com/actions/upload-artifact/blob/v7.0.1/action.yml).
