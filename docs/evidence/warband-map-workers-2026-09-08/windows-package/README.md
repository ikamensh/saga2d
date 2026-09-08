# Windows preview.3 acceptance — 8 September 2026

Warband `0.1.0-preview.3` passed Windows package acceptance in
[CI run 34216123836](https://github.com/ikamensh/saga2d/actions/runs/34216123836)
at exact frozen source `85becd0fda8493fffc14ad33baee32f4fccdee64`.
The build job succeeded and publication was disabled. `ci-run.json` records
the run, step results and artifact identity. This run was dispatched once.

The earlier run `34215610599`, at superseded source `9e8cadb…`, was cancelled
before packaging when native review exposed a camera reset beneath transparent
menus. The final source fixes that behavior and improves native mouse input
verification. The cancelled run is not acceptance evidence for this candidate.

The scoped Windows regression suite reported **357 passed in 190.53 seconds**
using Python 3.13.2 and locked dependencies. It covered `tests/warband`, shared
render3d and network tests, multiplayer game integration, and the online menu.
`regression-summary.txt` retains the exact command and runner result. This is
not a whole-repository test count.

## Frozen applications and online play

The extracted portable application and installed application ran outside the
checkout using isolated profiles, with no Python installation on their
executable PATH. The diagnostic receipts and `verification.json` record:

- Bundled fonts, authoritative room creation/joining, accepted movement,
  rejected foreign orders, and private-seat reconnection.
- Global production requests, automatic assignment of a blueprint builder,
  assembly points, and cancellation through ordinary validated commands.
- The installed EXE passing the same networking checks over public TLS at
  `wss://games.tachyon-ai.eu/play`.
- Per-user installation, Start menu shortcut creation, and removal of the
  EXE and shortcut during uninstall. Installer and uninstall logs are retained.
- Native room creation, copying its code, pasting through both the button
  and Ctrl+V, joining as the second seat, and returning to the title.
- Native empty-selection Train → Footman → Plans → Cancel, plus an F10
  match menu with the authoritative simulation continuing while open.

All four diagnostic receipts identify the same source, version and EXE SHA-256,
independently matched to `Warband/Warband.exe` read from the downloaded ZIP:
`3bf4924485503977cff21dc32797c6fa2449b313cd9fae3563239615f3c1c2f5`.
The ZIP's embedded build identity matches the build manifest.

## Native frames inspected

All nine original PNGs were opened and visually inspected. Labels, fields,
catalogue costs and plan controls are legible. The second seat's Crimson base
appears in the viewport and remains in place beneath Plans and the match menu.
The Settlement title has clear spacing, the tutorial avoids the resource bar,
and the empty command-card stub is absent. Early opening banners are expected.

| Capture in `verification/` | Visible evidence |
| --- | --- |
| `native-title.png` | Title controls, forest regions and distinct base assets. |
| `native-multiplayer.png` | Online/LAN choice, Create/Join and Paste code. |
| `native-room-code.png` | Shareable code and Copied confirmation. |
| `native-paste-code.png` | Pasted join code and Rejoin last room control. |
| `native-online-match.png` | Crimson seat, visible own base and Settlement row. |
| `native-settlement-train.png` | Global train catalogue and visible costs without selection. |
| `native-settlement-plans.png` | Footman waiting for a Barracks, cost and Cancel button. |
| `native-match-menu.png` | Live-menu notice, return/rejoin/leave controls and retained base camera. |
| `native.png` | Offline Azure opening, separated tutorial and Settlement HUD. |

Native menu checks used a loopback authority and a protocol peer. The public
TLS diagnostic was a separate installed-EXE check. These checks do not claim
a complete game between two human players.

Native CI used test-only Mesa 26.2.0, `llvmpipe (LLVM 22.1.8, 256 bits)`, with
OpenGL `4.6 (Compatibility Profile) Mesa 26.2.0 (git-aacd123e02)`.
`mesa-test-context.json` records the pinned archive hash; `native.json` records
the loaded DLL hashes. Neither `opengl32.dll` nor `libgallium_wgl.dll` appears
in the portable ZIP or installer extraction log. The installer uses the same
build directory as the ZIP before the test driver is added. The driver is
removed after native verification and is not part of the shipping packages.

All 87 sound cues loaded, but native acceptance was muted. These checks do
not establish subjective audio quality, every Windows GPU's behavior, or
Linux package support. The Windows installer is unsigned.

## Downloaded artifact identity

[Artifact 10052026640](https://github.com/ikamensh/saga2d/actions/runs/34216123836/artifacts/10052026640)
was downloaded to `/tmp/warband-windows-ci-34216123836`. Both shipping hashes
and byte sizes were independently recomputed against `SHA256SUMS` and
`build-manifest.json`; `artifact-validation.json` records the result.
Large binaries are staged in `dist/warband-release-0.1.0-preview.3` and retained
in the CI artifact rather than committed in this directory.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `Warband-0.1.0-preview.3-windows-x64-setup.exe` | 27,055,132 | `10a1a78748f9b2954fa3a18119dee359d8254d4e36efb8226032e1fd1d190a26` |
| `Warband-0.1.0-preview.3-windows-x64-portable.zip` | 37,340,330 | `945fcccc5055781d43c6c725b4c0da94bcff1ca406e90fa17ef8bb172bae2de7` |

The runner image was `win25-vs2026`, version `20260824.214.3`.
`workflow-build.json` is retained unchanged, including Inno Setup's reported
ProductVersion `0.0.0.0`; the installer log identifies Inno Setup 6.7.1.
