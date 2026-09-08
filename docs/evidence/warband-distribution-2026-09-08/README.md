# Warband 0.1.0-preview.4 distribution acceptance

Source `6f58eca12b7f4a969a063227267637256413c8ae`, tagged `warband-v0.1.0-preview.4`.

- `windows-package/`: the `build-manifest.json` and `verification.json` published
  by [Windows CI run 34229830340](https://github.com/ikamensh/saga2d/actions/runs/34229830340):
  extracted, installed, public TLS and native checks, shortcut creation and uninstall.
- `mac-package/`: the local Apple M4 build manifest, loopback `portable.json`,
  native `native.json` with its nine inspected frames (the room-code frame shows
  the new invite-link button), and `installed-public-server.json` from
  `/Applications/Warband.app` against `wss://games.tachyon-ai.eu/play`.
- `published-release.json`: sizes and SHA-256 of the three public downloads,
  fetched without authentication, and the installed executable hash.

The website at https://games.tachyon-ai.eu/warband/ lists these packages from
`releases/catalog.json`. Physical Windows GPU/audio and a complete
human-versus-human match remain outside this automated acceptance.
