# Windows package acceptance — 8 September 2026

Warband `0.1.0-preview.2` passed Windows package acceptance at source commit
`02377270d59fcf2ee6e9b0eef897303c1a5c0903` in
[CI run 34208548272](https://github.com/ikamensh/saga2d/actions/runs/34208548272).
This exact run succeeded without a rerun. Its build job passed; the publication
job was skipped because publication was disabled. `ci-run.json` retains the
run identity, step conclusions and uploaded artifact identity.

The Windows regression result was **293 passed in 158.99 seconds** using
Python 3.13.2 and locked dependencies. It covered `tests/warband`,
`tests/framework/test_render3d.py`, `tests/framework/test_network.py`,
`tests/test_multiplayer_games.py` and `tests/test_online_menu.py`.
`regression-summary.txt` retains the exact command and result from the runner.
This is scoped Warband and transport coverage, not a whole-repository result.

## Installed and portable applications

The extracted portable EXE and installed EXE ran outside the checkout with
isolated profiles and no Python installation on their executable PATH.
`verification.json` and its four diagnostic receipts record:

- Bundled fonts, authoritative room creation/joining, accepted movement,
  rejected foreign orders, and private-seat reconnection.
- The installed EXE passing those networking checks over public TLS against
  `wss://games.tachyon-ai.eu/play`.
- Per-user installation, standard Start menu shortcut creation, and removal
  of the EXE and shortcut during uninstall. Full installer and uninstall
  logs are retained in `verification/`.
- Native title and Multiplayer navigation; creating a real room; copying its
  code; pasting through both the visible button and Ctrl+V; and joining it.
- A rendered online match, an F10 match menu with simulation continuing
  while open, and leaving the match back to the title.
- A separate local match rendering check and successful loading of all
  87 sound cues. Audio was muted for native acceptance.

Native menu checks used a loopback authority and a protocol peer. The public
TLS diagnostic was a separate installed-EXE check. These checks do not claim
a complete game between two human players.

All four diagnostic receipts identify the same version, source commit and
EXE SHA-256, independently matched to `Warband/Warband.exe` read from the
downloaded portable ZIP:
`437d4a2d0361f1db42727fedcbd13d0ff1be0dda0f3447b1ddffc2e0af4f5820`.
The ZIP's embedded build identity also matches the build manifest.

## Native screenshots inspected

All seven original PNGs were opened and visually inspected. The labels,
fields, controls, HUD and procedural assets render legibly without clipping.
The copied room code appears in the join field; the match menu explicitly
states that the match continues and gives the rejoin path.

| Capture | Visible evidence |
| --- | --- |
| `verification/native-title.png` | Title menu and procedural winter background. |
| `verification/native-multiplayer.png` | Online selected, Create/Join and Paste code controls. |
| `verification/native-room-code.png` | Shareable room code, partner instructions and Copied confirmation. |
| `verification/native-paste-code.png` | Pasted code, Join room and Rejoin last room controls. |
| `verification/native-online-match.png` | Joined Crimson seat, settlement, resources, HUD and minimap. |
| `verification/native-match-menu.png` | Live match menu, Return, Settings, Help, Leave and Quit. |
| `verification/native.png` | Local Azure opening, tutorial, settlement and HUD. |

The opening banners and fog in the early match captures are expected. The
online HUD footer still labels F3 as “pause”; the F10 panel correctly states
that online play continues. This minor wording issue does not invalidate the
recorded join, clipboard or live-menu behavior.

The runner used Mesa 26.2.0 for native CI only: `llvmpipe (LLVM 22.1.8, 256 bits)`
with OpenGL `4.6 (Compatibility Profile) Mesa 26.2.0 (git-aacd123e02)`.
`mesa-test-context.json` records its pinned source archive hash, while the
native receipt records both loaded DLL hashes. The driver was temporarily
added beside the installed EXE and removed after the check. Independent ZIP
inspection found neither `opengl32.dll` nor `libgallium_wgl.dll`; neither name
appears in the installer extraction log. The installer uses the same build
directory as the ZIP, before the test-only driver is added. These software
rendering checks do not establish every Windows GPU's behavior or subjective
audio quality.

## Downloaded artifact identity

[Artifact 10048970669](https://github.com/ikamensh/saga2d/actions/runs/34208548272/artifacts/10048970669)
was downloaded to `/tmp/warband-windows-ci-34208548272` after the run succeeded.
Both shipping hashes and byte sizes were independently recomputed and matched
`SHA256SUMS` and `build-manifest.json`. `artifact-validation.json` records those
checks and the exact EXE comparisons. Large release binaries remain in the
CI artifact rather than this evidence directory.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `Warband-0.1.0-preview.2-windows-x64-setup.exe` | 27,006,651 | `c4f749b167f1ed797487a08e8851f9f8ae31312e1bb6065366d76e4936f5f295` |
| `Warband-0.1.0-preview.2-windows-x64-portable.zip` | 37,285,395 | `766de3deb94e49a8781bee57e94d613daeff946aafd50aaa11f6f97a24955b9d` |

The runner image was `win25-vs2026`, version `20260824.214.3`.
`workflow-build.json` is retained unchanged, including its Inno Setup
`ProductVersion` value of `0.0.0.0`; the installer log identifies the runtime
as Inno Setup 6.7.1. The installer is unsigned.
