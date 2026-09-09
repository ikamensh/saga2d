# Tribes — release pack (0.1.0-preview.1)

The [Tribes page](https://games.tachyon-ai.eu/tribes/) offers the current
downloads with installation steps; the same files are on the published
[preview.1 release](https://github.com/ikamensh/saga2d/releases/tag/tribes-v0.1.0-preview.1):
the [Windows installer](https://github.com/ikamensh/saga2d/releases/download/tribes-v0.1.0-preview.1/Tribes-0.1.0-preview.1-windows-x64-setup.exe)
and [Apple Silicon Mac app](https://github.com/ikamensh/saga2d/releases/download/tribes-v0.1.0-preview.1/Tribes-0.1.0-preview.1-darwin-arm64-app.zip),
built from `ea5a2a2ece444885edb29034ce34f029cce664d9` with the shared recipe in
`tools/package.py` (the shared `saga2d.packaging` recipe). Online play follows the [online multiplayer guide](online-multiplayer.md):
Multiplayer → Create room → Copy invite link; the partner pastes the code and
joins. Saves, settings and generated sounds live in `~/.tribes` (Windows:
`%USERPROFILE%\.tribes`).

## Acceptance: preview.1

[Windows CI run 34230860523](https://github.com/ikamensh/saga2d/actions/runs/34230860523)
passed the scoped regression tests and the extracted, installed, public TLS and
native (test-only Mesa) package checks: create/join, a rejected out-of-turn
order, authoritative turns, private seat reconnection, native clipboard join,
the invite-link button and a native End turn exchange; Start menu shortcut
creation and uninstall passed, then the release was published. The Mac
portable executable passed the same loopback and native checks on Apple M4 with
all seven frames inspected. All three public downloads were fetched without
authentication and matched the manifests.
Evidence: [tribes-distribution-2026-09-08](evidence/tribes-distribution-2026-09-08/).

| File | SHA-256 |
|---|---|
| `Tribes-0.1.0-preview.1-windows-x64-setup.exe` | `0c9a62f91945386082e403724ed8c62efd0f79b37949ae7cd62976f70eef741c` |
| `Tribes-0.1.0-preview.1-windows-x64-portable.zip` | `61916911c7de4de7620ca13255c367d4afcd638108e63fd17dc9a1acc86befb0` |
| `Tribes-0.1.0-preview.1-darwin-arm64-app.zip` | `ef17781416632574b0f87668dd9057eeca62005394e0cd1a2a6a53b2bd0f8daf` |

## Known limits

- The installer is unsigned and the Mac app is ad-hoc signed without
  notarization; the website explains the first-launch prompts.
- Physical Windows GPU/audio quality and a complete human-versus-human match
  remain outside the automated acceptance.
- English only.
