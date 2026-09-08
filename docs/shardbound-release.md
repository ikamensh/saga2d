# Shardbound — release pack (0.1.0-preview.1)

The [Shardbound page](https://games.tachyon-ai.eu/shardbound/) offers the
current downloads with installation steps; the same files are on the published
[preview.1 release](https://github.com/ikamensh/saga2d/releases/tag/shardbound-v0.1.0-preview.1):
the [Windows installer](https://github.com/ikamensh/saga2d/releases/download/shardbound-v0.1.0-preview.1/Shardbound-0.1.0-preview.1-windows-x64-setup.exe)
and [Apple Silicon Mac app](https://github.com/ikamensh/saga2d/releases/download/shardbound-v0.1.0-preview.1/Shardbound-0.1.0-preview.1-darwin-arm64-app.zip),
built from `184584007ac3071dcb901e323a16bcd727877c14` with `tools/build_eador.py`. This is a
development preview of the game described in the [player guide](../eador/README.md);
the Early Access gates in [early-access-criteria.md](early-access-criteria.md)
remain separate and the build manifest keeps `release_ready: false`.

Online co-op: **Co-op → Create room → Copy invite link**; the partner pastes the
code and joins. Both players command one shared realm. Campaign rooms are kept
for seven days without both players, so a co-op campaign can continue on another
day through **Rejoin last room**. Saves and settings live in `~/.shardbound`
(Windows: `%USERPROFILE%\.shardbound`).

## Acceptance: preview.1

[Windows CI run 34232824100](https://github.com/ikamensh/saga2d/actions/runs/34232824100)
built the installer and portable ZIP, ran the frozen smoke journey (title,
About, settings, shard, codex, rival, battle, saves and the audio catalogue) in
the extracted and installed applications under a test-only Mesa driver, ran the
online co-op diagnostic against a loopback authority and, from the installed
executable, against `wss://games.tachyon-ai.eu/play`, then checked Start menu
shortcut creation and uninstall before publishing. A first attempt of the same
run failed only because the live server was at its former 16-room limit from
automated test rooms; the limit is now 32 and the rerun passed.

The Mac app was built from a clean worktree at the tag on Apple M4; its build
ran the same smoke journey, the verifier repeated it with the loopback co-op
diagnostic, and the installed `/Applications/Shardbound.app` passed the co-op
diagnostic against the live service. All three public downloads were fetched
without authentication and matched the manifests.
Evidence: [shardbound-distribution-2026-09-08](evidence/shardbound-distribution-2026-09-08/).

| File | SHA-256 |
|---|---|
| `Shardbound-0.1.0-preview.1-windows-x64-portable.zip` | `ad9e87ca2fe2591a080380f76050ecca7ab2dd365537cfea11db0eddecaed6a4` |
| `Shardbound-0.1.0-preview.1-windows-x64-setup.exe` | `34bf23da4d5be088d6b35a20e93d38320b01dc87cc43dc509574fd36ba8d4fdc` |
| `Shardbound-0.1.0-preview.1-darwin-arm64-app.zip` | `0fcff24640abba882b8ee32b87345809246bf23d51d80c853dab345cd56a6376` |

## Known limits

- The installer is unsigned and the Mac app is ad-hoc signed without
  notarization; the website explains the first-launch prompts. The app still
  uses a development icon and system fonts.
- Balance, onboarding and presentation are still under evaluation; human
  playtests and listening review remain outstanding.
- CI's native checks use a software GL driver; physical Windows GPU and audio
  quality are unverified.
- English only.
