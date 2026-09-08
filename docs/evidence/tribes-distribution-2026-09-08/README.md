# Tribes 0.1.0-preview.1 distribution acceptance

Source `ea5a2a2ece444885edb29034ce34f029cce664d9`, tagged `tribes-v0.1.0-preview.1`; the first standalone Tribes release.

- `windows-package/`: `build-manifest.json` and `verification.json` from
  [Windows CI run 34230860523](https://github.com/ikamensh/saga2d/actions/runs/34230860523):
  extracted, installed, public TLS and native (test-only Mesa) checks with the
  shared recipe, Start menu shortcut creation and uninstall.
- `mac-package/`: the Apple M4 build manifest, loopback `portable.json`, native
  `native.json` with its seven inspected frames (title, multiplayer menu, room
  code with the invite-link button, pasted code, live online match after the
  partner's turn, pause menu, offline map).
- `published-release.json`: sizes and SHA-256 of the three public downloads,
  fetched without authentication.

The website at https://games.tachyon-ai.eu/tribes/ lists these packages from
`releases/catalog.json`. Physical Windows GPU/audio and a complete
human-versus-human match remain outside this automated acceptance.
