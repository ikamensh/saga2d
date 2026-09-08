# Windows package acceptance — 8 September 2026

Warband `0.1.0-preview.1` passed Windows package acceptance at source commit
`fd6e0c911fa68aa0355d4b56dd8e4f0885c739d8` in
[CI run 34202934123](https://github.com/ikamensh/saga2d/actions/runs/34202934123).
The build job succeeded; publication was intentionally disabled for this run.

The exact regression result was **285 passed in 156.05 seconds**. The command
covered `tests/warband`, `tests/framework/test_render3d.py`,
`tests/framework/test_network.py`, and `tests/test_multiplayer_games.py` with
Python 3.13.2 and the locked dependencies. `regression-summary.txt` preserves
the command and result from the runner log. This is the Windows Warband suite,
not a claim that every game in the repository passed.

## Installed and portable applications

`verification.json` records successful checks of the extracted portable EXE
and the installed EXE, launched outside the checkout with an isolated profile:

- Bundled fonts loaded without a Python installation on the executable PATH.
- Two clients created/joined an authoritative room over real sockets, observed
  accepted movement, rejected a foreign order, and rejoined a private seat.
- The installed EXE passed those same checks over public TLS against
  `wss://games.tachyon-ai.eu/play`.
- Per-user installation created the standard Start menu shortcut; uninstall
  removed the executable and shortcut.
- The installed EXE rendered the title, opened Multiplayer through native
  keyboard input, rendered a live match, and loaded all 87 sound cues.

All four diagnostic receipts contain the same source revision, version, and
EXE SHA-256, independently matched to `Warband/Warband.exe` extracted from the
downloaded portable ZIP:
`dace5f255e41f39746aa0cf69ad90f84faa4f63be2549a020342cd2f87b92b1c`.

## Native rendering evidence

The runner used the pinned, test-only Mesa 26.2.0 software WGL context:
`llvmpipe (LLVM 22.1.8, 256 bits)`, OpenGL
`4.6 (Compatibility Profile) Mesa 26.2.0 (git-aacd123e02)`.
`mesa-test-context.json` records the archive source/version/hash, and
`verification.json` records both loaded DLL hashes and the driver identity.
The driver was temporarily added beside the installed EXE for this check and
removed afterward. It is not part of the shipping ZIP or installer; the
downloaded ZIP was independently inspected for both DLL names.

All three PNGs were visually inspected: text and fonts are legible, menu
controls are intact, and game assets render correctly. The opening match
banner is expected. These are launch/input/render checks on the CI host;
they do not establish every Windows GPU's behavior or subjective audio quality.

- `verification/native-title.png` — title menu and procedural background.
- `verification/native-multiplayer.png` — online create/join controls.
- `verification/native.png` — live match, settlement, resources, HUD and minimap.

## Downloaded artifact identity

[Artifact 10046695851](https://github.com/ikamensh/saga2d/actions/runs/34202934123/artifacts/10046695851)
was downloaded after the successful run. Both shipping artifact hashes were
independently recomputed and matched `SHA256SUMS` and the build manifest.
`artifact-validation.json` records that comparison and EXE identity check.
The large binaries are retained in the CI artifact, not this evidence folder.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `Warband-0.1.0-preview.1-windows-x64-setup.exe` | 26,997,400 | `f2fcabad5bb14dde52630246005f900c37c0f80d2d46d12d433966c1e603500b` |
| `Warband-0.1.0-preview.1-windows-x64-portable.zip` | 37,277,059 | `65168d56f015a7caeaa5774d2ab6e50d62f34118375cc1f9645a0d7808675368` |

The runner image was `win25-vs2026`, version `20260824.214.3`.
`workflow-build.json` is retained unchanged, including its Inno Setup
`ProductVersion` value of `0.0.0.0`; the full CI installation log identifies
the actual compiler/runtime as Inno Setup 6.7.1.
